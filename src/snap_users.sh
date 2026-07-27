#!/usr/bin/env bash
# Snap Store install-base time series for ionosctl -> users.json  [{date, users}].
# Requires snapcraft store auth (you own the snap).
# The snapcraft CLI rejects null values, so range queries spanning a version's release fail.
# Workaround: sample ONE day per month (single-day queries only return versions present then).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
SNAP=ionosctl
# weekly_installed_base_* = weekly ACTIVE devices (users active that week)
METRIC="${1:-weekly_installed_base_by_version}"
OUT=$DATA/users.json
today=$(date +%F)
tmp=$(mktemp -d)

# month sample days from 2022-06 to today (snap first reported ~2022)
python3 - "$today" > "$tmp/days" <<'PY'
import sys, datetime
end=datetime.date.fromisoformat(sys.argv[1]); y,m=2022,6
while (y,m) <= (end.year,end.month):
    print(f"{y:04d}-{m:02d}-15"); m+=1
    if m>12: m=1; y+=1
PY

: > "$tmp/series"
while read -r day; do
  r=$(snapcraft metrics "$SNAP" --format json --name "$METRIC" --start "$day" --end "$day" 2>/dev/null)
  tot=$(printf '%s' "$r" | python3 -c "import sys,json
try:
 d=json.load(sys.stdin); print(sum((s['values'][0] or 0) for s in d.get('series',[])))
except Exception: print('')" 2>/dev/null)
  [ -n "$tot" ] && [ "$tot" != "0" ] && echo "$day $tot" >> "$tmp/series" && echo "  $day -> $tot users" >&2
done < "$tmp/days"

python3 - "$tmp/series" "$OUT" <<'PY'
import sys, json
rows=[]
for line in open(sys.argv[1]):
    d,u=line.split(); rows.append({"date":d,"users":int(u)})
json.dump(rows, open(sys.argv[2],"w"), indent=2)
print(f"wrote {sys.argv[2]}: {len(rows)} months, {rows[0]['date']}({rows[0]['users']}) -> {rows[-1]['date']}({rows[-1]['users']})" if rows else "no data")
PY
rm -rf "$tmp"
