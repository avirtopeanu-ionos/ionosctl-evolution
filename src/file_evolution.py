#!/usr/bin/env python3
"""LOC of a few representative product command implementations, per stable tag.
Buckets command-layer .go files by resource keyword in their path — robust to the
file/dir restructures across history (e.g. commands/datacenter.go -> commands/compute/datacenter/*.go).
Output: data/file_evo.csv  (tag + one LOC column per resource)."""
import subprocess, os, csv, collections, re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DATA = os.path.join(ROOT, "data"); os.makedirs(DATA, exist_ok=True)
REPO = os.environ.get("IONOSCTL_REPO", os.path.join(ROOT, "..", "workspace", "tools", "ionosctl"))

RESOURCES = ["datacenter", "server", "lan", "k8s"]
# match a resource only at a path-segment boundary so "lan" doesn't hit "ba(lan)cer"
RES_RE = {r: re.compile(rf'(^|/){re.escape(r)}([./_]|$)') for r in RESOURCES}

def sh(*a):
    return subprocess.run(a, cwd=REPO, capture_output=True, text=True).stdout

tags = [t for t in sh("git", "tag").split() if not any(x in t.lower() for x in ("beta", "rc", "alpha"))]
tags = [(sh("git", "log", "-1", "--format=%at", t).strip(), t) for t in tags]
tags = [t for _, t in sorted((int(a or 0), b) for a, b in tags)]

rows = []
for t in tags:
    # per-file line counts across the command layer (empty pattern matches every line)
    out = sh("git", "grep", "-I", "-c", "", t, "--", "commands/")
    buckets = collections.Counter()
    for line in out.splitlines():
        # format: <tag>:<path>:<count>
        parts = line.rsplit(":", 1)
        if len(parts) != 2:
            continue
        path, cnt = parts[0], parts[1]
        if not path.endswith(".go") or path.endswith("_test.go"):
            continue
        low = path.lower()
        # assign each file to ONE resource: the keyword that appears earliest in the path
        # (so commands/compute/k8s/nodepool/lan/... counts as k8s, not lan)
        best_r, best_pos = None, 1e9
        for r in RESOURCES:
            m = RES_RE[r].search(low)
            if m and m.start() < best_pos:
                best_r, best_pos = r, m.start()
        if best_r:
            buckets[best_r] += int(cnt)
    date = sh("git", "log", "-1", "--format=%ad", "--date=short", t).strip()
    rows.append((t, date, *[buckets[r] for r in RESOURCES]))

out_path = os.path.join(DATA, "file_evo.csv")
with open(out_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tag", "date", *RESOURCES])
    w.writerows(rows)
print(f"wrote {out_path}: {len(rows)} tags")
f0, fl = rows[0], rows[-1]
for i, r in enumerate(RESOURCES):
    print(f"  {r:11} {f0[2+i]:>5} -> {fl[2+i]:>5} LOC")
