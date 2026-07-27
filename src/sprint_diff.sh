#!/usr/bin/env bash
# Sprint delta: compare current HEAD vs a ref ~3 weeks ago (default: tag/commit arg or 21 days back).
# Usage: sprint_diff.sh [OLD_REF]   (OLD_REF defaults to HEAD@{3 weeks ago})
set -u
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
REPO="${IONOSCTL_REPO:-$ROOT/../workspace/tools/ionosctl}"
WT=/tmp/ionosctl-sprint
OLD="${1:-}"
if [[ -z "$OLD" ]]; then OLD=$(git -C "$REPO" rev-list -1 --before='3 weeks ago' HEAD); fi
NEW=$(git -C "$REPO" rev-parse HEAD)
echo "OLD=$OLD  NEW=$NEW"
git -C "$REPO" worktree add --force --detach "$WT" "$OLD" >/dev/null 2>&1
build(){ ( cd "$2" && GOTOOLCHAIN=auto GOFLAGS=-mod=mod go build -o "$1" . ) ; }
build /tmp/ictl-old "$WT"
build /tmp/ictl-new "$REPO"
git -C "$REPO" worktree remove --force "$WT" 2>/dev/null
python3 introspect.py /tmp/ictl-old OLD > /tmp/old.json
python3 introspect.py /tmp/ictl-new NEW > /tmp/new.json
python3 - <<'PY'
import json
o=json.load(open('/tmp/old.json')); n=json.load(open('/tmp/new.json'))
keys=[('total_commands','commands'),('leaf_commands','end-user cmds'),
      ('global_flags','global flags'),('capability_count','capabilities')]
print(f"{'metric':18}{'old':>8}{'new':>8}{'Δ':>8}")
for k,lab in keys:
    print(f"{lab:18}{o[k]:>8}{n[k]:>8}{n[k]-o[k]:>+8}")
PY
