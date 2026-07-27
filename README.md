# ionosctl-evolution

Measures how [ionosctl](https://github.com/ionos-cloud/ionosctl) changed across releases (2021 → 2026) and renders it as a self-contained HTML dashboard: command growth, developer friction, code health, capabilities, tests, release velocity, a live-API journey, and Snap install base.

## Use

```bash
make          # full pipeline: build every stable tag → introspect → health → assemble → dashboard.html
make regen    # rebuild data + dashboard from existing datasets (no recompiling)
make open     # open dashboard.html
```

Then open **`dashboard.html`** (self-contained; needs internet for the Chart.js CDN). The version selector at the top resamples every chart by month step and left-bound date.

Set `IONOSCTL_REPO=/path/to/ionosctl` if the checkout isn't at `../workspace/tools/ionosctl`.

## Layout

| path | role |
|---|---|
| `src/` | **sources** — scripts, nothing generated |
| `data/` | **generated** datasets (gitignored) |
| `bins/` | **generated** compiled release binaries (gitignored) |
| `dashboard.html` | **output**, committed and kept current |
| `Makefile` | pipeline entry point |

Flow: `src/*` read the ionosctl git history + built binaries → write `data/*` → `dashboard.html`.

## Targets

`make full` (all tags) · `make sampled` (quick 10-tag) · `make users` (Snap, needs store auth) · `make journey` (live API, needs `IONOS_TOKEN`) · `make sprint` (HEAD vs ~3 weeks ago).

Requires: Go (`GOTOOLCHAIN=auto`), Python 3, `dupl` + `gocyclo` (`go install`).
