#!/usr/bin/env python3
"""
Offline introspector for ionosctl binaries.
Recursively walks the cobra command tree via `--help` (no network, no token),
handling BOTH the old flat "AVAILABLE COMMANDS:" layout and the new grouped layout.
Emits one JSON metrics row for the binary.

Usage: introspect.py <path-to-binary> <version-label>
"""
import subprocess, sys, json, re, os

BIN = sys.argv[1]
LABEL = sys.argv[2] if len(sys.argv) > 2 else os.path.basename(BIN)

# commands we never recurse into (noise / slow / generators)
SKIP = {"help", "completion", "man", "shell", "version", "login", "logout"}

FLAG_RE = re.compile(r'^\s+(?:-[a-zA-Z], )?--([a-zA-Z][a-zA-Z0-9-]*)')
# a subcommand row: 2+ leading spaces, a bare word (no leading dash), 2+ spaces, description
SUBCMD_RE = re.compile(r'^\s{2,}([a-z][a-z0-9-]*)\s{2,}\S')

def run_help(path_parts):
    try:
        p = subprocess.run([BIN, *path_parts, "--help"],
                           capture_output=True, text=True, timeout=15)
        return (p.stdout or "") + "\n" + (p.stderr or "")
    except Exception:
        return ""

def parse(text):
    """Return (subcommands:list[str], local_flags:set[str], global_flags:set[str])."""
    subs, local_flags, global_flags = [], set(), set()
    # section state: None | 'cmds' | 'flags' | 'global'
    sect = None
    for line in text.splitlines():
        low = line.strip().lower()
        # section headers (old + new variants)
        if low.endswith("commands:") or low in ("cloud services:", "authentication & configuration:", "other:"):
            sect = "cmds"; continue
        if low == "global flags:":
            sect = "global"; continue
        if low == "flags:":
            sect = "flags"; continue
        if low in ("usage:", "aliases:", "examples:") or low.endswith("example:"):
            sect = None; continue
        if not line.strip():
            continue
        fm = FLAG_RE.match(line)
        if fm:
            (global_flags if sect == "global" else local_flags).add(fm.group(1))
            continue
        if sect == "cmds":
            sm = SUBCMD_RE.match(line)
            if sm:
                subs.append(sm.group(1))
    return subs, local_flags, global_flags

# BFS walk
root_text = run_help([])
_, _, _ = parse(root_text)
# root: its subcommands live under 'cmds', its flags under FLAGS (global)
root_subs, root_local, root_global = parse(root_text)
# root global flags = the persistent flags shown at root (local at root == global set)
GLOBAL_FLAGS = root_local | root_global

nodes = {}          # path tuple -> {"local_flags": set, "is_leaf": bool}
def walk(path_parts, subs):
    for s in subs:
        if s in SKIP:
            continue
        cp = (*path_parts, s)
        if cp in nodes:
            continue
        txt = run_help(list(cp))
        csubs, lflags, gflags = parse(txt)
        low = txt.lower()
        nodes[cp] = {
            "local_flags": lflags | gflags,   # effective (local + inherited) — for consistency checks
            "own_flags": lflags,              # pure command-specific flags — for surface metrics
            "is_leaf": len(csubs) == 0,
            "has_example": bool(re.search(r'(?im)^\s*examples?:\s*$', txt)),
            "deprecated": "deprecat" in low,
        }
        if csubs:
            walk(list(cp), csubs)

walk([], root_subs)

# ---- metrics ----
all_paths = list(nodes.keys())
total_cmds = len(all_paths)
leaves = [p for p, v in nodes.items() if v["is_leaf"]]
groups = [p for p, v in nodes.items() if not v["is_leaf"]]

# top-level product/service count (depth-1 non-leaf-ish, exclude skip)
top_level = sorted({p[0] for p in all_paths if p[0] not in SKIP})

def leaf_named(name):
    return [p for p in leaves if p[-1] == name]

del_cmds = leaf_named("delete")
list_cmds = leaf_named("list")

def frac_with_flag(cmd_paths, flag):
    if not cmd_paths: return None
    have = sum(1 for p in cmd_paths if flag in nodes[p]["local_flags"])
    return round(have / len(cmd_paths), 4)

# capability flags present anywhere (union of all local + global)
all_flags = set(GLOBAL_FLAGS)
for v in nodes.values():
    all_flags |= v["local_flags"]

caps = {
    "wait":        "wait" in all_flags,
    "query_jmespath": "query" in all_flags,
    "pagination":  ("limit" in all_flags and "offset" in all_flags),
    "filters":     "filters" in all_flags,
    "no_headers":  "no-headers" in all_flags,
    "order_by":    "order-by" in all_flags,
    "cols":        any("cols" in v["local_flags"] for v in nodes.values()),
    "depth":       "depth" in all_flags,
}

# --- surface / quality metrics ---
own_flag_total = sum(len(v["own_flags"]) for v in nodes.values())
leaf_own_flags = [len(nodes[p]["own_flags"]) for p in leaves]
avg_flags_leaf = round(sum(leaf_own_flags) / len(leaves), 2) if leaves else 0
tree_depth = max((len(p) for p in all_paths), default=0)
deprecated_count = sum(1 for v in nodes.values() if v["deprecated"])
leaves_with_example = sum(1 for p in leaves if nodes[p]["has_example"])
example_coverage = round(leaves_with_example / len(leaves), 4) if leaves else 0

row = {
    "version": LABEL,
    "total_commands": total_cmds,
    "leaf_commands": len(leaves),
    "command_groups": len(groups),
    "top_level_services": len(top_level),
    "top_level_list": top_level,
    "global_flags": len(GLOBAL_FLAGS),
    "global_flags_list": sorted(GLOBAL_FLAGS),
    "delete_cmds": len(del_cmds),
    "list_cmds": len(list_cmds),
    # consistency scores (0..1)
    "consistency_delete_all": frac_with_flag(del_cmds, "all"),
    "consistency_list_cols":  frac_with_flag(list_cmds, "cols"),
    "capabilities": caps,
    "capability_count": sum(1 for x in caps.values() if x),
    # surface / quality
    "own_flag_total": own_flag_total,
    "avg_flags_per_leaf": avg_flags_leaf,
    "tree_depth": tree_depth,
    "deprecated_count": deprecated_count,
    "example_coverage": example_coverage,
    "leaves_with_example": leaves_with_example,
    # full leaf-command paths, for diffing added/removed commands between releases
    "leaf_list": sorted(" ".join(p) for p in leaves),
}
print(json.dumps(row))
