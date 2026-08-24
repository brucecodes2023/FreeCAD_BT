# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# Part of FcBridge, a fork-only dev/test module. See ATTRIBUTION.md.
"""Threaded TCP JSON-RPC server that runs inside FreeCAD.

This server accepts JSON-RPC 2.0 requests over TCP and dispatches them
to handler functions that execute in FreeCAD's main (GUI) thread.

The threading model:
- The TCP socket server runs in a background daemon thread.
- Each connected client gets its own handler thread.
- A QTimer on the main thread polls a work queue every 50ms and executes
  pending handler calls. This avoids the pitfall of QTimer.singleShot from
  non-Qt threads, which doesn't reliably post to the main event loop.
- Results are passed back to socket threads via threading.Event.
"""

import json
import logging
import queue
import socket
import threading
import traceback
from typing import Any, Callable

logger = logging.getLogger("freecad_mcp.rpc_server")

# Default port — matches the convention used by existing FreeCAD MCP servers.
DEFAULT_PORT = 9876
DEFAULT_HOST = "127.0.0.1"

# Delimiter for framing JSON messages over TCP.
MSG_DELIMITER = b"\n"

# Maximum message size (16 MB — generous for large document graphs).
MAX_MSG_SIZE = 16 * 1024 * 1024

# Timeout for waiting on main-thread execution (seconds).
MAIN_THREAD_TIMEOUT = 60

# How often the main-thread timer checks for work (ms).
POLL_INTERVAL_MS = 50


class RPCServer:
    """TCP JSON-RPC server that dispatches calls to FreeCAD's main thread."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._handlers: dict[str, Callable] = {}
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False
        self._work_queue: queue.Queue = queue.Queue()
        self._poll_timer = None

        # Always register the built-in ping handler.
        self.register("ping", self._handle_ping)

    def register(self, method: str, handler: Callable) -> None:
        """Register a handler function for a JSON-RPC method name."""
        self._handlers[method] = handler

    def register_all(self, handlers: dict[str, Callable]) -> None:
        """Register multiple handlers at once."""
        self._handlers.update(handlers)

    def start(self) -> None:
        """Start the server in a background thread."""
        if self._running:
            logger.warning("RPC server is already running")
            return

        self._running = True

        # Start the main-thread poll timer.
        self._start_poll_timer()

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)  # So we can check _running periodically
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        logger.info("RPC server started on %s:%d", self.host, self.port)

    def stop(self) -> None:
        """Stop the server and close all connections."""
        self._running = False
        self._stop_poll_timer()
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("RPC server stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    # ── Main-thread poll timer ───────────────────────────────────────

    def _start_poll_timer(self) -> None:
        """Start a QTimer on the main thread that drains the work queue."""
        try:
            from PySide2 import QtCore
        except ImportError:
            from PySide6 import QtCore

        self._poll_timer = QtCore.QTimer()
        self._poll_timer.timeout.connect(self._drain_work_queue)
        self._poll_timer.start(POLL_INTERVAL_MS)

    def _stop_poll_timer(self) -> None:
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None

    def _drain_work_queue(self) -> None:
        """Called on the main thread by the poll timer. Executes all pending work."""
        while not self._work_queue.empty():
            try:
                func, params, result_holder, event = self._work_queue.get_nowait()
            except queue.Empty:
                break
            try:
                result_holder["result"] = func(**params) if params else func()
            except Exception as e:
                result_holder["error"] = f"{e}\n{traceback.format_exc()}"
            finally:
                event.set()

    # ── Accept loop (runs in background thread) ──────────────────────

    def _accept_loop(self) -> None:
        while self._running:
            try:
                client, addr = self._server_socket.accept()
                logger.info("Client connected from %s:%d", *addr)
                t = threading.Thread(
                    target=self._client_loop, args=(client, addr), daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.exception("Accept error")
                break

    # ── Client loop (one per connected client) ───────────────────────

    def _client_loop(self, client: socket.socket, addr: tuple) -> None:
        buffer = b""
        client.settimeout(None)  # Block until data arrives
        try:
            while self._running:
                data = client.recv(65536)
                if not data:
                    break
                buffer += data
                # Process all complete messages in the buffer.
                while MSG_DELIMITER in buffer:
                    line, buffer = buffer.split(MSG_DELIMITER, 1)
                    if len(line) > MAX_MSG_SIZE:
                        self._send_error(client, None, -32600, "Message too large")
                        continue
                    if not line.strip():
                        continue
                    response = self._handle_message(line)
                    if response is not None:
                        client.sendall(json.dumps(response).encode() + MSG_DELIMITER)
        except (ConnectionResetError, BrokenPipeError):
            pass
        except Exception:
            logger.exception("Error in client loop for %s:%d", *addr)
        finally:
            try:
                client.close()
            except OSError:
                pass
            logger.info("Client disconnected: %s:%d", *addr)

    # ── Message handling ─────────────────────────────────────────────

    def _handle_message(self, raw: bytes) -> dict | None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            return self._error_response(None, -32700, f"Parse error: {e}")

        if not isinstance(msg, dict):
            return self._error_response(None, -32600, "Invalid request")

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params", {})

        if not method or not isinstance(method, str):
            return self._error_response(req_id, -32600, "Missing or invalid method")

        handler = self._handlers.get(method)
        if handler is None:
            return self._error_response(
                req_id, -32601, f"Method not found: {method}"
            )

        # Execute on FreeCAD's main thread via the work queue.
        try:
            result = self._execute_on_main_thread(handler, params)
        except TimeoutError:
            return self._error_response(
                req_id, -32000, f"Timeout executing {method}"
            )
        except Exception as e:
            return self._error_response(
                req_id, -32000, f"Execution error: {e}\n{traceback.format_exc()}"
            )

        return {"jsonrpc": "2.0", "result": result, "id": req_id}

    def _execute_on_main_thread(self, func: Callable, params: dict) -> Any:
        """Queue a function call for the main thread and wait for the result.

        Puts (func, params, result_holder, event) on the work queue.
        The main-thread poll timer picks it up and executes it.
        """
        result_holder: dict[str, Any] = {}
        event = threading.Event()

        self._work_queue.put((func, params, result_holder, event))

        if not event.wait(timeout=MAIN_THREAD_TIMEOUT):
            raise TimeoutError(
                f"Main-thread execution timed out after {MAIN_THREAD_TIMEOUT}s"
            )

        if "error" in result_holder:
            raise RuntimeError(result_holder["error"])

        return result_holder.get("result")

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _handle_ping() -> dict:
        return {"status": "ok"}

    @staticmethod
    def _error_response(req_id: Any, code: int, message: str) -> dict:
        return {
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": req_id,
        }

    def _send_error(self, client: socket.socket, req_id: Any, code: int, msg: str):
        resp = self._error_response(req_id, code, msg)
        try:
            client.sendall(json.dumps(resp).encode() + MSG_DELIMITER)
        except OSError:
            pass
