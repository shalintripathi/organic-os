# Agent contributor guide

House rules for any coding agent working in this repo, condensed from
[CONTRIBUTING.md](CONTRIBUTING.md) (the full text wins on any conflict).

## The three gates

Run all three before and after any change. Every commit must leave them green.

```
python3 -m pytest tests -q        # expect: all tests passed, none skipped
./scripts/audit.sh                # expect: "audit: clean", exit 0
./scripts/verify-gates.sh         # expect: "verify-gates: all 8 probes behaved as designed", exit 0
```

Prerequisites: Python 3.9+, `python3 -m pip install --user pyyaml pytest`.
`verify-gates.sh` is not redundant with pytest: it builds a throwaway brain
repo in a temp dir and red-teams the approval gates.

## The data boundary (hard rule)

This repo is an engine, never a dataset. No business data - site profiles,
keyword lists, brand rulebooks, competitor lists, skillbook entries, signals -
lands here; it lives in a user's own private brain repo. Audit check 7 fails
the build on any file named `site-profile.yaml`, `skillbook.md`,
`tracking.yaml`, or `telegram-offset.json` outside
`plugin/lib/core/templates/`, and on any directory named `organic-hq*`,
`signals/`, or `reflections/`. If you were testing against a real brain
locally, move it outside this checkout.

## House style

- No em-dashes anywhere. Use a hyphen with spaces (` - `), a comma, or split
  the sentence. Audit check 3 enforces this byte-wise.
- No hype words. Audit check 4 blocks a list of marketing cliches (open
  `scripts/audit.sh` for the exact pattern). Rephrase; never extend an
  exclude list.
- Evidence discipline: every number, study result, or comparison carries a
  link to its primary source, the standard `plugin/docs/evidence.md` holds
  itself to. Never fabricate a stat or a citation.
- TDD for `plugin/lib/core`, `plugin/lib/hoo`, `plugin/lib/onsite`: write the
  failing test first; `tests/` shows the pattern per module.
- A fact quoted in more than one file gets a row in
  `docs/INFORMATION-MAP.md`, updated in the same commit that changes it.

## Module boundaries

`plugin/lib/core` (contracts, the only reader/writer of brain files),
`plugin/lib/hoo` (observe/decide), `plugin/lib/onsite` (CMS adapters).
Audit check 5 enforces: core imports neither module; hoo and onsite never
import each other. Approval gates live in core only - adapters never gate.
Hook scripts (`plugin/hooks/`) are stdlib plus PyYAML, fail open, and
nothing may assume a hook ran (harness support varies; see
`plugin/docs/hooks.md`).

## Commits

Sign every commit (DCO, not a CLA): `git commit -s` adds the
`Signed-off-by:` trailer from your git config. Granular commits, one
concern each. Releases (version bumps, tags) are cut by the maintainer,
never by a contributor agent.

## Where the docs live

- `README.md` - what the plugin is, install, personas, FAQ.
- `CONTRIBUTING.md` - full contribution guide, adapter contracts, release steps.
- `plugin/docs/` - user-facing docs shipped with the plugin (getting started,
  connectors, routines, approval channels, hooks, credentials).
- `docs/adr/` - architecture decision records; read the relevant ADR before
  reopening a decided question.
- `docs/INFORMATION-MAP.md` - canonical source for every cross-file fact.
- `THREAT-MODEL.md`, `SECURITY.md` - permissions, blast radius, reporting.
