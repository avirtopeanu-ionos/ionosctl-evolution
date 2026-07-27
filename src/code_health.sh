#!/usr/bin/env bash
# Per-tag code health: gocyclo avg, #funcs over 15, dupl clone groups (vendor excluded).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
REPO="${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
WT=/tmp/ionosctl-health
GB=$(go env GOPATH)/bin
OUT="$DATA/health.csv"
TAGS=(v6.0.0 v6.2.0 v6.4.0 v6.5.0 v6.7.0 v6.7.5 v6.7.8 v6.8.2 v6.9.0 v6.10.2)
echo "tag,gocyclo_avg,cyclo_over15,clone_groups" > "$OUT"
cd "$REPO"
git worktree add --force --detach "$WT" v6.0.0 >/dev/null 2>&1
for t in "${TAGS[@]}"; do
  git -C "$WT" checkout --force "$t" >/dev/null 2>&1
  pushd "$WT" >/dev/null
  mapfile -t GOFILES < <(find . -name '*.go' -not -path './vendor/*' -not -name '*_test.go')
  avg=$($GB/gocyclo -avg -ignore 'vendor/' . 2>/dev/null | awk -F': ' '/Average/{print $2}')
  over=$($GB/gocyclo -over 15 -ignore 'vendor/' . 2>/dev/null | wc -l | tr -d ' ')
  clones=$($GB/dupl -threshold 60 "${GOFILES[@]}" 2>/dev/null | awk -F'total ' '/Found total/{print $2}' | awk '{print $1}')
  clones=${clones:-0}
  popd >/dev/null
  echo "$t,${avg:-0},$over,$clones" >> "$OUT"
  echo "done $t: cyclo_avg=$avg over15=$over clones=$clones"
done
git worktree remove --force "$WT" >/dev/null 2>&1 || true
echo "=== HEALTH DONE ==="; cat "$OUT"
