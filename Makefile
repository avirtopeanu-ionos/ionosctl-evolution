# ionosctl evolution dashboard. Sources in src/, generated data in data/, dashboard.html at root.
.DEFAULT_GOAL := all
SHELL := /bin/bash

.PHONY: all sampled full cadence downloads commits users journey data dashboard dashboard-local regen sprint open clean distclean

## all: full-resolution pipeline (all stable tags) -> data -> dashboard
all: full cadence downloads commits data dashboard
	@echo "OPEN: file://$(CURDIR)/dashboard.html"

## downloads: GitHub release download counts -> data/downloads.json (public)
downloads:
	@bash src/gh_downloads.sh

## commits: commit-type mix per year -> data/commit_types.csv
commits:
	@bash src/commit_types.sh

## full: build+introspect+health for ALL stable tags -> data/rows_all.ndjson + data/meta_all.csv
full:
	@bash src/build_full.sh 2>&1 | tail -3

## cadence: releases-per-quarter across all tags -> data/cadence.json
cadence:
	@bash src/release_cadence.sh >/dev/null && echo "wrote data/cadence.json"

## users: Snap weekly-active + OS breakdown -> data/users.json + data/snap_os.json (owner-gated, local only)
users:
	@bash src/snap_users.sh
	@bash src/snap_breakdown.sh

## journey: live-API friction, old vs new binary -> data/journey.json (needs IONOS_TOKEN + `make sampled` bins)
journey:
	@bash src/layer_c.sh

## data: merge all datasets -> data/data.json (auto-detects full vs sampled)
data:
	@python3 src/assemble.py

## dashboard: render committed dashboard.html (no owner-gated Snap numbers)
dashboard:
	@python3 src/gen_dashboard.py

## dashboard-local: render dashboard.local.html WITH the Snap graph (gitignored, do not publish)
dashboard-local:
	@INCLUDE_SNAP=1 python3 src/gen_dashboard.py && echo "wrote dashboard.local.html (gitignored)"

## regen: rebuild data + dashboard from existing datasets (no rebuild of binaries/tags)
regen: cadence downloads commits data dashboard
	@echo "OPEN: file://$(CURDIR)/dashboard.html"

## sampled: quick 10-tag path (builds bins/, introspect, git metrics, health)
sampled:
	@bash src/build_all.sh
	@: > data/rows.ndjson
	@for b in bins/ionosctl-v*; do t=$$(basename $$b | sed 's/ionosctl-//'); \
	  python3 src/introspect.py "$$b" "$$t" >> data/rows.ndjson && echo "introspected $$t"; done
	@bash src/git_metrics.sh >/dev/null && echo "wrote data/git_metrics.csv"
	@bash src/code_health.sh >/dev/null && echo "wrote data/health.csv"

## sprint: delta of current ionosctl HEAD vs ~3 weeks ago (OLD=<ref> to override)
sprint:
	@bash src/sprint_diff.sh $(OLD)

## open: open the dashboard in a browser
open:
	@xdg-open "file://$(CURDIR)/dashboard.html" >/dev/null 2>&1 || echo "open dashboard.html manually"

## clean: remove generated data (keep compiled binaries and committed dashboard.html)
clean:
	@rm -rf data/* && echo "cleaned data/"

## distclean: also remove compiled binaries
distclean: clean
	@rm -rf bins/* && echo "removed binaries"
