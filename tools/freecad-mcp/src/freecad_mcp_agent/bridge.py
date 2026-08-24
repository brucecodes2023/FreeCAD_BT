# SPDX-License-Identifier: LGPL-2.1-or-later
# Vendored from theosib/FreeCAD-MCP-Server (LGPL-2.1-or-later).
# FcBridge stdio MCP bridge (fork-only dev/test). See ATTRIBUTION.md.
"""TCP client that connects to the FreeCAD addon's RPC server.

Translates Python method calls into JSON-RPC 2.0 requests sent over TCP,
waits for the response, and returns the result.
"""

import json
import os
import socket
import threading

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876
MSG_DELIMITER = b"\n"
RECV_BUFFER = 65536
CONNECT_TIMEOUT = 5.0
CALL_TIMEOUT = 120.0


class BridgeError(Exception):
    """Raised when the bridge encounters a communication or protocol error."""


class RPCError(Exception):
    """Raised when the FreeCAD addon returns a JSON-RPC error."""

    def __init__(self, code: int, message: str):
        self.code = code
        super().__init__(f"RPC error {code}: {message}")


class FreeCADBridge:
    """TCP client for communicating with the FreeCAD addon's RPC server."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
    ):
        self.host = host or os.environ.get("FREECAD_MCP_HOST", DEFAULT_HOST)
        self.port = port or int(os.environ.get("FREECAD_MCP_PORT", str(DEFAULT_PORT)))
        self._socket: socket.socket | None = None
        self._lock = threading.Lock()
        self._request_id = 0

    def connect(self) -> None:
        """Establish a TCP connection to the FreeCAD RPC server."""
        if self._socket is not None:
            return
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(CONNECT_TIMEOUT)
            sock.connect((self.host, self.port))
            sock.settimeout(CALL_TIMEOUT)
            self._socket = sock
        except (ConnectionRefusedError, OSError) as e:
            raise BridgeError(
                f"Cannot connect to FreeCAD RPC server at {self.host}:{self.port}. "
                f"Is FreeCAD running with the MCP addon's RPC server started? ({e})"
            ) from e

    def disconnect(self) -> None:
        """Close the TCP connection."""
        if self._socket:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def is_connected(self) -> bool:
        return self._socket is not None

    def call(self, method: str, params: dict | None = None) -> object:
        """Send a JSON-RPC request and return the result.

        Automatically connects if not already connected.
        Automatically reconnects once on connection failure.
        """
        for attempt in range(2):
            try:
                return self._do_call(method, params or {})
            except (BrokenPipeError, ConnectionResetError, OSError):
                if attempt == 0:
                    self.disconnect()
                    self.connect()
                else:
                    raise BridgeError(
                        f"Lost connection to FreeCAD RPC server during {method} call"
                    )

    def _do_call(self, method: str, params: dict) -> object:
        self.connect()

        with self._lock:
            self._request_id += 1
            req_id = self._request_id

            request = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
                "id": req_id,
            }

            raw = json.dumps(request).encode() + MSG_DELIMITER
            self._socket.sendall(raw)

            # Read response (may span multiple recv calls)
            buffer = b""
            while MSG_DELIMITER not in buffer:
                chunk = self._socket.recv(RECV_BUFFER)
                if not chunk:
                    raise BrokenPipeError("Connection closed by FreeCAD")
                buffer += chunk

            line, _ = buffer.split(MSG_DELIMITER, 1)
            response = json.loads(line)

        if "error" in response:
            err = response["error"]
            raise RPCError(err.get("code", -1), err.get("message", "Unknown error"))

        return response.get("result")

    def ping(self) -> bool:
        """Check if the FreeCAD RPC server is reachable."""
        try:
            result = self.call("ping")
            return result.get("status") == "ok"
        except Exception:
            return False
