#!/usr/bin/env bash
# Full-resolution dataset over ALL stable tags: one worktree checkout per tag serves
# build+introspect+gocyclo+dupl+git-metrics, streaming (binary removed after) to keep disk low.
# Outputs: rows_all.ndjson (introspect) + meta_all.csv (date + git + health).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/src"; DATA="$ROOT/data"; mkdir -p "$DATA"
REPO="${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
WT=/tmp/ionosctl-full
GB=$(go env GOPATH)/bin
ROWS=$DATA/rows_all.ndjson
META=$DATA/meta_all.csv
: > "$ROWS"
echo "tag,date,commands,own_loc,test_files,test_funcs,bats,cmd_loc,sdk_deps,go_version,contributors,gocyclo_avg,cyclo_over15,clone_groups" > "$META"

cd "$REPO"
# stable tags, chronological
mapfile -t TAGS < <(git tag | grep -viE 'beta|rc|alpha' | while read -r t; do echo "$(git log -1 --format=%at "$t") $t"; done | sort -n | awk '{print $2}')
echo "building ${#TAGS[@]} stable tags..." >&2
git worktree add --force --detach "$WT" "${TAGS[0]}" >/dev/null 2>&1

for t in "${TAGS[@]}"; do
  git -C "$WT" checkout --force "$t" >/dev/null 2>&1 || { echo "skip $t (checkout)" >&2; continue; }
  d=$(git -C "$WT" log -1 --format=%ad --date=short "$t")
  bin=/tmp/ionosctl-full-bin
  ( cd "$WT" && GOTOOLCHAIN=auto GOFLAGS=-mod=mod timeout 300 go build -o "$bin" . ) >/dev/null 2>&1
  if [[ ! -x "$bin" ]]; then echo "FAIL build $t" >&2; continue; fi

  # binary introspection
  cmds=$(python3 "$SRC/introspect.py" "$bin" "$t" | tee -a "$ROWS" | python3 -c "import sys,json;print(json.loads(sys.stdin.read())['total_commands'])")
  rm -f "$bin"

  pushd "$WT" >/dev/null
  own_loc=$(find . -name '*.go' -not -path './vendor/*' -print0 | xargs -0 cat 2>/dev/null | wc -l | tr -d ' ')
  test_files=$(find . -name '*_test.go' -not -path './vendor/*' | wc -l | tr -d ' ')
  test_funcs=$(grep -rhE '^func (Test|Example)' --include='*_test.go' $(find . -type d -not -path './vendor*' -maxdepth 4 2>/dev/null) 2>/dev/null | wc -l | tr -d ' ')
  bats=$(find . -name '*.bats' | wc -l | tr -d ' ')
  cmd_loc=$(find ./commands -name '*.go' 2>/dev/null -print0 | xargs -0 cat 2>/dev/null | wc -l | tr -d ' ')
  sdk_deps=$(grep -cE 'ionos-cloud/(sdk|ionos)' go.mod 2>/dev/null)
  go_version=$(grep -E '^go ' go.mod 2>/dev/null | head -1 | awk '{print $2}')
  contributors=$(git log --format='%ae' 2>/dev/null | sort -u | wc -l | tr -d ' ')
  gavg=$($GB/gocyclo -avg -ignore 'vendor/' . 2>/dev/null | awk -F': ' '/Average/{print $2}')
  gover=$($GB/gocyclo -over 15 -ignore 'vendor/' . 2>/dev/null | wc -l | tr -d ' ')
  mapfile -t GF < <(find . -name '*.go' -not -path './vendor/*' -not -name '*_test.go')
  clones=$($GB/dupl -threshold 60 "${GF[@]}" 2>/dev/null | awk -F'total ' '/Found total/{print $2}' | awk '{print $1}')
  popd >/dev/null

  echo "$t,$d,$cmds,$own_loc,$test_files,$test_funcs,$bats,$cmd_loc,$sdk_deps,${go_version:-},${contributors:-0},${gavg:-0},${gover:-0},${clones:-0}" >> "$META"
  echo "done $t ($d) cmds=$cmds own_loc=$own_loc sdk=$sdk_deps clones=${clones:-0}" >&2
done
git worktree remove --force "$WT" >/dev/null 2>&1 || true
echo "=== FULL DONE: $(wc -l < "$META") rows ===" >&2
