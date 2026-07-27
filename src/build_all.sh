#!/usr/bin/env bash
# Build ionosctl at each sampled tag into bins/<tag>. Idempotent: skips existing.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/data"; BINS="$ROOT/bins"; mkdir -p "$DATA" "$BINS"
REPO="${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
WT=/tmp/ionosctl-tt
LOG="$DATA/build.log"
: > "$LOG"

TAGS=(v6.0.0 v6.2.0 v6.4.0 v6.5.0 v6.7.0 v6.7.5 v6.7.8 v6.8.2 v6.9.0 v6.10.2)

cd "$REPO"
git worktree add --force --detach "$WT" v6.0.0 >>"$LOG" 2>&1

for t in "${TAGS[@]}"; do
  out="$BINS/ionosctl-$t"
  if [[ -x "$out" ]]; then echo "SKIP $t (exists)" | tee -a "$LOG"; continue; fi
  echo ">>> $t building..." | tee -a "$LOG"
  git -C "$WT" checkout --force "$t" >>"$LOG" 2>&1
  ( cd "$WT" && GOTOOLCHAIN=auto GOFLAGS=-mod=mod timeout 300 go build -o "$out" . ) >>"$LOG" 2>&1
  if [[ -x "$out" ]]; then echo "OK   $t -> $out" | tee -a "$LOG"; else echo "FAIL $t" | tee -a "$LOG"; fi
done
echo "=== BUILD DONE ===" | tee -a "$LOG"
git worktree remove --force "$WT" >>"$LOG" 2>&1 || true
