#!/usr/bin/env bash
# Releases per quarter across ALL tags (excludes pre-releases) -> cadence.json
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
cd "${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
OUT="$DATA/cadence.json" python3 - <<'PY'
import subprocess, json, collections, os
tags = subprocess.run(["git","tag"],capture_output=True,text=True).stdout.split()
q = collections.Counter()
for t in tags:
    if any(x in t.lower() for x in ("beta","rc","alpha")): continue
    d = subprocess.run(["git","log","-1","--format=%ad","--date=short",t],
                       capture_output=True,text=True).stdout.strip()
    if not d: continue
    y,m,_ = d.split("-"); quarter = f"{y}-Q{(int(m)-1)//3+1}"
    q[quarter]+=1
rows = [{"quarter":k,"releases":v} for k,v in sorted(q.items())]
out = os.environ["OUT"]
json.dump(rows, open(out,"w"), indent=2)
print("wrote", out, "-", sum(v['releases'] for v in rows), "stable releases across", len(rows), "quarters")
for r in rows: print(f"  {r['quarter']}  {'#'*r['releases']} {r['releases']}")
PY
