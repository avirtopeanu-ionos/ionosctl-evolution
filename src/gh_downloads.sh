#!/usr/bin/env bash
# GitHub release-asset download counts per release -> data/downloads.json  [{tag,date,downloads}]
# Public data. Requires gh auth.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
OUT="$DATA/downloads.json" SLUG="${IONOSCTL_SLUG:-ionos-cloud/ionosctl}" python3 - <<'PY'
import subprocess, json, os
slug = os.environ["SLUG"]
# --jq streams one JSON object per release (JSONL) — avoids paginated-array concat
out = subprocess.run(["gh","api",f"repos/{slug}/releases","--paginate","--jq",
    '.[] | {tag: .tag_name, date: .published_at, dl: ([.assets[].download_count] | add) }'],
    capture_output=True, text=True).stdout
rows = []
for line in out.splitlines():
    if not line.strip(): continue
    o = json.loads(line); t = o.get("tag") or ""
    if any(x in t.lower() for x in ("beta","rc","alpha")): continue
    rows.append({"tag": t, "date": (o.get("date") or "")[:10], "downloads": o.get("dl") or 0})
rows = [r for r in rows if r["date"]]
rows.sort(key=lambda x: x["date"])
json.dump(rows, open(os.environ["OUT"],"w"), indent=2)
print(f"wrote {os.environ['OUT']}: {len(rows)} releases, total downloads {sum(r['downloads'] for r in rows)}")
PY
