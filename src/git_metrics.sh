#!/usr/bin/env bash
# Dev-friction metrics straight from git history (no build needed).
# Per tag: Go LOC, Go files, test files, .bats integration tests, command-layer LOC.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; mkdir -p "$DATA"
cd "${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
TAGS=(v6.0.0 v6.2.0 v6.4.0 v6.5.0 v6.7.0 v6.7.5 v6.7.8 v6.8.2 v6.9.0 v6.10.2)
OUT="$DATA/git_metrics.csv"
echo "tag,date,go_files,go_loc,test_files,test_funcs,bats_files,cmd_dir_loc,own_loc,sdk_deps,go_version,contributors" > "$OUT"
for t in "${TAGS[@]}"; do
  d=$(git log -1 --format=%ad --date=short "$t")
  # bundled IONOS SDK modules wired in (products integrated)
  sdk_deps=$(git show "$t:go.mod" 2>/dev/null | grep -cE 'ionos-cloud/(sdk|ionos)')
  go_version=$(git show "$t:go.mod" 2>/dev/null | grep -E '^go ' | head -1 | awk '{print $2}')
  # cumulative unique contributors reachable from this tag
  contributors=$(git log "$t" --format='%ae' 2>/dev/null | sort -u | wc -l | tr -d ' ')
  # own-code go files (vendor excluded)
  go_files=$(git grep -I -l '' "$t" -- '*.go' ':(exclude)vendor/*' 2>/dev/null | wc -l)
  # own unit tests (vendor excluded): files + Test/Example func count
  test_files=$(git grep -I -l '' "$t" -- '*_test.go' ':(exclude)vendor/*' 2>/dev/null | wc -l)
  test_funcs=$(git grep -I -h -E '^func (Test|Example)' "$t" -- '*_test.go' ':(exclude)vendor/*' 2>/dev/null | wc -l)
  bats=$(git ls-tree -r --name-only "$t" | grep -c '\.bats$')
  # total go LOC: empty-pattern git grep counts every line of every matching file
  go_loc=$(git grep -I -c '' "$t" -- '*.go' 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
  # own-code LOC (vendor excluded)
  own_loc=$(git grep -I -c '' "$t" -- '*.go' ':(exclude)vendor/*' 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
  # command-layer LOC (commands/ dir dropped the old cloudapi-v6; use commands/ + services/)
  cmd_loc=$(git grep -I -c '' "$t" -- 'commands/*.go' 2>/dev/null | awk -F: '{s+=$NF} END{print s+0}')
  echo "$t,$d,$go_files,$go_loc,$test_files,$test_funcs,$bats,$cmd_loc,$own_loc,$sdk_deps,$go_version,$contributors" >> "$OUT"
  echo "done $t ($d): go_files=$go_files go_loc=$go_loc tests=$test_files bats=$bats"
done
echo "--- wrote $OUT ---"
cat "$OUT"
