# SPDX-License-Identifier: LGPL-2.1-or-later
"""Serial-chain graph helpers (FreeCAD-independent)."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, List, Sequence, Tuple


def order_serial_chain(
    edges: Sequence[Tuple[str, str, Any]],
) -> Tuple[List[Any], str, List[str]]:
    """Order undirected joint edges into a serial path when possible.

    ``edges`` items are ``(part1_name, part2_name, joint_token)``.
    Returns ``(ordered_joint_tokens, topology, messages)``.
    """
    messages: List[str] = []
    if not edges:
        return [], "empty", ["No motional joints with two distinct parts."]

    adj = defaultdict(list)
    degree = defaultdict(int)
    for a, b, joint in edges:
        adj[a].append((b, joint))
        adj[b].append((a, joint))
        degree[a] += 1
        degree[b] += 1

    branched = [n for n, d in degree.items() if d > 2]
    if branched:
        messages.append(
            "Branched topology at: {}. Using longest path "
            "(not a unique serial arm).".format(", ".join(sorted(branched)))
        )
        topology = "branched"
    else:
        topology = "serial"

    seen = set()
    components = []
    for start in adj:
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        comp = []
        while queue:
            node = queue.popleft()
            comp.append(node)
            for nxt, _joint in adj[node]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        components.append(comp)

    if len(components) > 1:
        messages.append(
            "Disconnected motional graph ({} components); using largest.".format(
                len(components)
            )
        )
        if topology == "serial":
            topology = "disconnected"

    best_comp = set(max(components, key=len))
    endpoints = [n for n in best_comp if degree[n] == 1] or list(best_comp)

    def bfs_farthest(src):
        prev = {src: (None, None)}
        queue = deque([src])
        last = src
        while queue:
            node = queue.popleft()
            last = node
            for nxt, joint in adj[node]:
                if nxt not in prev and nxt in best_comp:
                    prev[nxt] = (node, joint)
                    queue.append(nxt)
        path_joints = []
        cur = last
        while prev[cur][0] is not None:
            parent, joint = prev[cur]
            path_joints.append(joint)
            cur = parent
        path_joints.reverse()
        return last, path_joints

    far, _ = bfs_farthest(endpoints[0])
    _end, ordered = bfs_farthest(far)
    if not ordered:
        ordered = [edges[0][2]]
    return ordered, topology, messages


def pad_dh_rows(rows, count=6):
    """Pad / truncate to exactly ``count`` DH rows for Robot6Axis."""
    out = list(rows[:count])
    while len(out) < count:
        out.append((0.0, 0.0, 0.0, 0.0, 1.0, 180.0, -180.0, 90.0))
    return out


def write_kinematic_csv(path, rows):
    """Write Robot6Axis CSV (header + 6 axis rows). Returns path."""
    import csv
    import os

    rows6 = pad_dh_rows(list(rows), 6)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["a", "alpha", "d", "theta", "rotDir", "maxAngle", "minAngle", "velocity"]
        )
        for row in rows6:
            writer.writerow(["{:.6g}".format(v) for v in row])
    return path
