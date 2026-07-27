#!/usr/bin/env bash
# Conventional-commit type mix per year -> data/commit_types.csv
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
OUT="$DATA/commit_types.csv" REPO="${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}" python3 - <<'PY'
import subprocess, csv, collections, re, os
log = subprocess.run(["git","-C",os.environ["REPO"],"log","--pretty=%ad|%s","--date=format:%Y"],
                     capture_output=True, text=True).stdout
CAT = [("feature", r'^(feat|feature|enhancement)'), ("fix", r'^(fix|bug)'),
       ("refactor", r'^refactor'), ("test", r'^test'), ("docs", r'^docs?')]
per = collections.defaultdict(collections.Counter)
for line in log.splitlines():
    year, _, subj = line.partition("|")
    s = subj.strip().lower()
    cat = next((c for c, rx in CAT if re.match(rx, s)), "other")
    per[year.strip()][cat] += 1
cats = [c for c, _ in CAT] + ["other"]
with open(os.environ["OUT"], "w", newline="") as f:
    w = csv.writer(f); w.writerow(["year", *cats])
    for y in sorted(per):
        if y: w.writerow([y, *[per[y][c] for c in cats]])
print("wrote", os.environ["OUT"], "-", len([y for y in per if y]), "years")
PY
