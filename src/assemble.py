#!/usr/bin/env python3
"""Merge introspect rows (binary) + git metrics into data.json for the dashboard.
Prefers full-resolution datasets (rows_all.ndjson + meta_all.csv, ALL stable tags)
when present; otherwise falls back to the 10-tag sampled set."""
import json, csv, os
# inputs and outputs both live in ../data (all generated)
BASE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))
FULL = os.path.exists(os.path.join(BASE, "rows_all.ndjson")) and os.path.exists(os.path.join(BASE, "meta_all.csv"))

intro = {}
for l in open(os.path.join(BASE, "rows_all.ndjson" if FULL else "rows.ndjson")):
    if l.strip():
        r = json.loads(l); intro[r["version"]] = r

def load_csv(name, key="tag"):
    d = {}
    path = os.path.join(BASE, name)
    if not os.path.exists(path): return d
    with open(path) as f:
        for row in csv.DictReader(f):
            d[row[key]] = row
    return d

# representative product implementations' LOC (data/file_evo.csv), keyed by version
PRODUCTS = ["datacenter", "server", "lan", "k8s"]
file_evo = load_csv("file_evo.csv")

# normalized per-version metadata, regardless of source
meta = {}
if FULL:
    for v, r in load_csv("meta_all.csv").items():
        meta[v] = {"date":r["date"],"own_loc":int(r["own_loc"]),"test_files":int(r["test_files"]),
            "test_funcs":int(r["test_funcs"]),"bats":int(r["bats"]),"cmd_loc":int(r["cmd_loc"]),
            "sdk_deps":int(r["sdk_deps"]),"go_version":r["go_version"],"contributors":int(r["contributors"]),
            "gocyclo_avg":float(r["gocyclo_avg"] or 0),"cyclo_over15":int(r["cyclo_over15"] or 0),
            "clone_groups":int(r["clone_groups"] or 0)}
else:
    git = load_csv("git_metrics.csv"); health = load_csv("health.csv")
    for v, g in git.items():
        h = health.get(v, {})
        meta[v] = {"date":g["date"],"own_loc":int(g["own_loc"]),"test_files":int(g["test_files"]),
            "test_funcs":int(g["test_funcs"]),"bats":int(g["bats_files"]),"cmd_loc":int(g["cmd_dir_loc"]),
            "sdk_deps":int(g["sdk_deps"]),"go_version":g["go_version"],"contributors":int(g["contributors"]),
            "gocyclo_avg":float(h.get("gocyclo_avg",0) or 0),"cyclo_over15":int(h.get("cyclo_over15",0) or 0),
            "clone_groups":int(h.get("clone_groups",0) or 0)}

# only versions present in BOTH introspect and meta; sort chronologically
ORDER = sorted((v for v in intro if v in meta), key=lambda v: meta[v]["date"])
rows = []
prev_leaves = None   # for command churn: added / removed vs previous release
for v in ORDER:
    i = intro[v]; m = meta[v]
    own = m["own_loc"]; cmds = i["total_commands"]; clones = m["clone_groups"]
    # signature = last two path tokens (resource + verb) so top-level regrouping
    # (e.g. `datacenter list` -> `compute datacenter list`) is NOT counted as churn
    cur_leaves = set(" ".join(p.split()[-2:]) for p in i.get("leaf_list", []))
    if prev_leaves is None:
        added = removed = 0            # first release = baseline, no diff
    else:
        added = len(cur_leaves - prev_leaves)
        removed = len(prev_leaves - cur_leaves)
    prev_leaves = cur_leaves
    rows.append({
        "version": v,
        "date": m["date"],
        "commands": cmds,
        "leaf_commands": i["leaf_commands"],
        "groups": i["command_groups"],
        "services": i["top_level_services"],
        "global_flags": i["global_flags"],
        "capabilities": i["capability_count"],
        "cap_detail": i["capabilities"],
        "own_loc": own,
        "loc_per_command": round(own / cmds, 1) if cmds else 0,
        "bats": m["bats"],
        "unit_test_files": m["test_files"],
        "test_funcs": m["test_funcs"],
        "cmd_dir_loc": m["cmd_loc"],
        "sdk_deps": m["sdk_deps"],
        "go_version": m["go_version"],
        "contributors": m["contributors"],
        "own_flag_total": i["own_flag_total"],
        "deprecated_count": i["deprecated_count"],
        "tree_depth": i["tree_depth"],
        "example_coverage": i["example_coverage"],
        "gocyclo_avg": m["gocyclo_avg"],
        "cyclo_over15": m["cyclo_over15"],
        "clone_groups": clones,
        "clones_per_10k": round(clones / own * 10000, 1) if own else 0,
        "product_loc": {p: int(file_evo.get(v, {}).get(p, 0) or 0) for p in PRODUCTS},
        "cmds_added": added,
        "cmds_removed": removed,
        "test_ratio": round(i["leaf_commands"] and m["test_funcs"] / own * 1000, 1) if own else 0,
    })

print(f"source: {'FULL (all stable tags)' if FULL else 'sampled (10 tags)'} — {len(rows)} versions")

out = os.path.join(BASE, "data.json")
json.dump(rows, open(out, "w"), indent=2)
print("wrote", out)

# service first-appearance timeline: earliest date each current top-level service showed up
current = intro[ORDER[-1]].get("top_level_list", [])
services = []
for svc in current:
    for v in ORDER:
        if svc in intro[v].get("top_level_list", []):
            services.append({"service": svc, "version": v, "date": meta[v]["date"]})
            break
services.sort(key=lambda s: s["date"])
json.dump(services, open(os.path.join(BASE, "services.json"), "w"), indent=2)
print("wrote services.json -", len(services), "services")
# quick deltas
f, l = rows[0], rows[-1]
def d(k): return f"{f[k]} -> {l[k]}"
print("commands      ", d("commands"))
print("loc/command   ", d("loc_per_command"))
print("global_flags  ", d("global_flags"))
print("capabilities  ", d("capabilities"))
print("bats tests    ", d("bats"))
print("own_loc       ", d("own_loc"))
