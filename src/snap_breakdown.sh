#!/usr/bin/env bash
# Snap install base by OS (today) -> data/snap_os.json  (owner-gated, local only)
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
OUT="$DATA/snap_os.json" DAY="$(date -d '4 days ago' +%F)" python3 - <<'PY'
import subprocess, json, os
day = os.environ["DAY"]
out = subprocess.run(["snapcraft","metrics","ionosctl","--format","json",
    "--name","installed_base_by_operating_system","--start",day,"--end",day],
    capture_output=True, text=True).stdout
try:
    d = json.loads(out)
except Exception:
    d = {"series": []}
rows = [{"os": s["name"], "count": (s["values"][0] or 0)} for s in d.get("series", [])]
rows = sorted((r for r in rows if r["count"]), key=lambda r: -r["count"])
json.dump(rows, open(os.environ["OUT"], "w"), indent=2)
print("wrote", os.environ["OUT"], "-", len(rows), "OS buckets")
PY
