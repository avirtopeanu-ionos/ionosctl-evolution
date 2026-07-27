# CLAUDE.md

Context for anyone (human or agent) working on this repo.

## Goal

Quantify ionosctl's evolution over ~3.5 years to showcase lead-contributor impact — for both non-technical and developer audiences. Focus: reduced **developer friction** (cheaper to add products) and **user friction** (UX/consistency), not raw perf.

## Method

Two data sources, joined per release:
- **Binary introspection** (`introspect.py`): build each stable tag, recursively walk its `--help` tree offline. Handles both the old flat `AVAILABLE COMMANDS:` layout and the new grouped layout. Yields command counts, flag surface, capabilities, depth, deprecations, example coverage.
- **Git + tooling** (`git_metrics.sh`, `code_health.sh`, `build_full.sh`): vendor-excluded LOC, tests, bundled SDK count, contributors, gocyclo, dupl.

Plus: `release_cadence.sh` (releases/quarter), `layer_c.sh` (one live-API journey, old vs new binary), `snap_users.sh` (Snap install base). `assemble.py` merges to `data/data.json`; `gen_dashboard.py` renders `dashboard.html` with a client-side version selector.

## Must-know facts

- `make` = full resolution (all ~78 stable tags, back to v5.0.0/2021). `make sampled` = quick 10-tag path. `assemble.py` auto-detects which datasets exist.
- Old go.mod (1.16) builds under go1.25 via `GOTOOLCHAIN=auto GOFLAGS=-mod=mod`.
- `introspect.py` stores **own_flags** (command-specific) separately from **effective** (incl. inherited globals); consistency checks need the effective set.
- `snap_users.sh`: snapcraft CLI rejects null metric values, so range queries spanning a version release fail — workaround is one single-day query per month.
- `layer_c.sh` cleanup tracks created datacenter IDs in a **file**, not a bash array (functions run in `$(...)` subshells; array writes are lost → orphan resources).

## Honesty guards (do not "sell")

Notes on the dashboard are descriptions, not pitches.
- Services count 27→41 then drops to 14 at v6.10 = `compute` grouping, not loss.
- Unit tests fell (padding tests by a prior contributor were removed); real coverage moved to BATs integration.
- Live journey is **parity** on basic compute — old already had `--wait-for-request`. The real win is that global `--wait` is defined once and every command (current + future) inherits it, vs per-command duplication.
- `example_coverage` ≈100% throughout → stated as a fact, not charted.

## Boundaries

Public repo. No credentials in commits (`layer_c.sh`/`snap_users.sh` read auth from env / snapcraft login, never hardcoded). `data/` and `bins/` are gitignored.
