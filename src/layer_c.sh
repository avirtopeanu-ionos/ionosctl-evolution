#!/usr/bin/env bash
# Layer C: live-API journey friction, OLD vs NEW binary.
# Journey: create datacenter (wait) -> create LAN (wait). Free resources. Guaranteed teardown.
# Measures: command count, keystrokes (chars typed), wall-clock, wait mechanism.
# Requires IONOS_TOKEN in env.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; B="$ROOT/bins"; mkdir -p "$DATA"
export OUT="$DATA/journey.json"
: "${IONOS_TOKEN:?set IONOS_TOKEN}"
export IONOS_TOKEN
LOC=de/fra
CREATED_FILE=$(mktemp)   # datacenter ids to clean up (file survives $(...) subshells)

cleanup(){
  while read -r id; do
    [ -z "$id" ] && continue
    echo "  teardown datacenter $id" >&2
    $B/ionosctl-v6.10.2 compute datacenter delete --datacenter-id "$id" -f >/dev/null 2>&1
  done < "$CREATED_FILE"
  rm -f "$CREATED_FILE"
}
trap cleanup EXIT

# extract first UUID-looking id from json
getid(){ python3 -c "import sys,re;print(next(iter(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',sys.stdin.read())),''))"; }
now(){ python3 -c "import time;print(time.time())"; }
klen(){ printf '%s' "$1" | wc -c | tr -d ' '; }   # keystrokes

run_new(){
  local name="EVOL-new-$$" ks=0 n=0 t0 t1
  t0=$(now)
  local c1="ionosctl compute datacenter create --name $name --location $LOC --wait -o json"
  ks=$((ks+$(klen "$c1"))); n=$((n+1))
  local out; out=$($B/ionosctl-v6.10.2 ${c1#ionosctl } 2>/dev/null); local dc; dc=$(echo "$out" | getid)
  [ -n "$dc" ] && echo "$dc" >> "$CREATED_FILE"
  local c2="ionosctl compute lan create --datacenter-id $dc --name evol --public=false --wait -o json"
  ks=$((ks+$(klen "$c2"))); n=$((n+1))
  $B/ionosctl-v6.10.2 ${c2#ionosctl } >/dev/null 2>&1
  t1=$(now)
  python3 -c "print(f'NEW {$n} {$ks} {round($t1-$t0,1)} global---wait dc=$dc')"
}

run_old(){
  local name="EVOL-old-$$" ks=0 n=0 t0 t1
  t0=$(now)
  local c1="ionosctl datacenter create --name $name --location $LOC --wait-for-request -o json"
  ks=$((ks+$(klen "$c1"))); n=$((n+1))
  local out; out=$($B/ionosctl-v6.0.0 ${c1#ionosctl } 2>/dev/null); local dc; dc=$(echo "$out" | getid)
  [ -n "$dc" ] && echo "$dc" >> "$CREATED_FILE"
  local c2="ionosctl lan create --datacenter-id $dc --name evol --wait-for-request -o json"
  ks=$((ks+$(klen "$c2"))); n=$((n+1))
  $B/ionosctl-v6.0.0 ${c2#ionosctl } >/dev/null 2>&1
  t1=$(now)
  python3 -c "print(f'OLD {$n} {$ks} {round($t1-$t0,1)} per-cmd---wait-for-request dc=$dc')"
}

echo "running NEW journey..." >&2; NEW=$(run_new)
echo "running OLD journey..." >&2; OLD=$(run_old)
echo "$NEW"; echo "$OLD"

python3 - "$NEW" "$OLD" <<'PY'
import sys, json, os
def parse(s):
    p=s.split()
    return {"binary":p[0],"commands":int(p[1]),"keystrokes":int(p[2]),
            "wall_clock_s":float(p[3]),"wait_mechanism":p[4].replace('---','--')}
rows=[parse(sys.argv[1]),parse(sys.argv[2])]
json.dump(rows, open(os.environ["OUT"],"w"), indent=2)
print("wrote journey.json:", json.dumps(rows))
PY
