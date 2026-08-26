# SPDX-License-Identifier: LGPL-2.1-or-later

"""OpenFOAM dictionary text (no subprocess, no FreeCAD)."""

from __future__ import annotations

from typing import Any


def foam_file_header(*, cls: str, obj: str, location: str = "") -> str:
    body = {
        "version": "2.0",
        "format": "ascii",
        "class": cls,
        "object": obj,
    }
    if location:
        body["location"] = f'"{location}"'
    return "FoamFile\n" + dump_block(body) + "\n"


def dump_block(entries: dict[str, Any], indent: int = 0) -> str:
    pad = "    " * indent
    inner = "    " * (indent + 1)
    lines = ["{"]
    for key, value in entries.items():
        if isinstance(value, dict):
            lines.append(f"{inner}{key}")
            lines.append(dump_block(value, indent + 1) + ";")
        else:
            lines.append(f"{inner}{key}{ _spacer(key) }{dump_value(value, indent + 1)};")
    lines.append(f"{pad}}}")
    return "\n".join(lines)


def dump_value(value: Any, indent: int = 0) -> str:
    if isinstance(value, dict):
        return dump_block(value, indent)
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            raise TypeError("list of dicts is not a Foam value")
        return "( " + " ".join(dump_value(item, indent) for item in value) + " )"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.8g}"
    if isinstance(value, int):
        return str(value)
    return str(value)


def dump_dictionary(header: str, entries: dict[str, Any]) -> str:
    lines = [header.rstrip(), ""]
    for key, value in entries.items():
        if isinstance(value, dict):
            lines.append(f"{key}")
            lines.append(dump_block(value))
            lines.append("")
        else:
            lines.append(f"{key}{ _spacer(key) }{dump_value(value)};")
    lines.append("")
    return "\n".join(lines)


def _spacer(key: str) -> str:
    return " " * max(4, 16 - len(key))
