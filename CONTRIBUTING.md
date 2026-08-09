# Contributing to organic-os

Thanks for looking at this. organic-os is an engine, not a dataset - the
guidance below exists to keep it that way.

## What we welcome

- **Bug reports** with a repro: what you ran, what you expected, what
  happened. Include `python3 --version` and whether `python3 -c "import
  yaml"` succeeds.
- **Code fixes with tests.** `plugin/lib/core`, `plugin/lib/hoo`, and
  `plugin/lib/onsite` are plain Python covered by `tests/`. A fix without a
  regression test that would have caught it is a partial fix.
- **New skills or agents that read the site profile.** Anything under
  `plugin/skills/` or `plugin/agents/` that takes `site-profile.yaml` (or an
  equivalent generic input) and works for any site, not one business.
- **CMS or channel adapters.** A new CMS backend implements the
  `CmsAdapter` contract in `plugin/lib/onsite/cms.py` (see "Contributing
  a CMS adapter" below); a new approval channel lands alongside
  telegram/pr-merge/slack/email in `lib/core/approval.py`.
- **Docs.** Fixes, clarifications, missing setup steps.
- **Evidence updates, with primary sources.** A change to `plugin/docs/evidence.md`
  needs a real citation (a study, a vendor analysis with methodology, a
  controlled experiment) - not "I heard AI cites X more now."

## The data boundary (hard rule)

organic-os is an engine. Your business data - the contents of
`site-profile.yaml`, keyword lists, brand rulebooks, competitor lists,
skillbook entries, signals, screenshots with real data - lives in **your own
private brain repo**, never in this one.

Any PR to this repo that contains brain-shaped content is auto-rejected.
Concretely, CI runs `scripts/audit.sh`, whose check 7 fails the build if the
diff introduces:

- a file named `site-profile.yaml`, `skillbook.md`, `tracking.yaml`, or
  `telegram-offset.json` anywhere outside `plugin/lib/core/templates/`
- a directory named `organic-hq*`, `signals/`, or `reflections/` anywhere
  outside `.git`

Why this is a hard rule and not a style preference: every business's site
profile, keywords, and skillbook are different, and the engine has to stay
generic enough to serve all of them - the moment one contributor's real
brand rulebook or keyword list lands in this repo, the codebase starts
silently coupling to one business's specifics. It is also a privacy
guarantee: nobody's competitor list, traffic numbers, or approval history
should ever be one accidental `git add .` away from a public PR.

If your PR trips this check because you were testing against a real brain
repo locally, move the brain repo outside the organic-os checkout (the
default `organic-hq-<site>/` scaffolding already does this) and re-push.

## How to share learnings without data

Found a tactic that works? Open an issue describing the tactic, its
evidence tier (`strong` / `moderate` / `anecdotal`, matching
`plugin/docs/evidence.md`), and where the evidence comes from - no URLs, no
keywords, no brand names, no screenshots of a real site. The roadmap's
anonymized lessons library (see `ROADMAP.md`, v1.0) will formalize this into
something structured; until then, an issue is the right venue.

## Dev setup

```
git clone https://github.com/shalintripathi/organic-os.git
cd organic-os
python3 -m pip install --user pyyaml pytest
python3 -m pytest tests/ -q
./scripts/audit.sh
./scripts/verify-gates.sh
```

All three should be clean before you start (every test passing, `audit:
clean`, `verify-gates: all 8 probes behaved as designed`) and clean again
before you open a PR. `verify-gates.sh` is not redundant with pytest: it
builds a throwaway brain repo in a temp directory and runs eight probes
against the approval gates, checking that they refuse what they should
refuse and open for a genuine approval.

## Contributing a CMS adapter

The cms capability slot (ADR-0009,
`docs/adr/0009-capability-slots-not-tool-bindings.md`) takes new backends
as adapters. WordPress (`plugin/lib/onsite/wp.py`) is adapter one and the
reference for a REST backend. Git-static
(`plugin/lib/onsite/gitstatic.py`) is adapter two and the smallest honest
adapter - a local-clone file writer with no transport at all and every
gap declared (`rendered_head_verify: False`, `needs_human: ["merge-pr",
"deploy"]`, `get_rendered_head` raises naming the gap). Start from
whichever shape your backend matches.

- **Implement `CmsAdapter`** (`plugin/lib/onsite/cms.py`): one class per
  backend covering the full surface - `get_post`, `update_post`,
  `create_post`, `update_seo_meta`, `get_rendered_head`, `snapshot`,
  `rollback`, `capabilities`, `adapter_name`. Register the type in
  `adapter_for` and `SUPPORTED_CMS_TYPES`, and document any
  backend-specific site-profile keys the adapter reads.
- **The capabilities() honesty rule.** Declare what your adapter cannot
  do: `needs_human` lists the action types it cannot perform. When an
  approved proposal includes such a step, the item ends
  `partially-applied` with a note naming exactly what a human must finish
  (`docs/adr/0007-partially-applied-state.md`) - an adapter never fakes
  success for an action it cannot perform.
- **The test bar.** A fake-transport test file mirroring
  `tests/test_wp.py`'s pattern (an injected fake session, no network) -
  or, for a file-based backend, `tests/test_gitstatic.py`'s tmp-dir
  pattern (no real git, no transport) - proving the contract end to end:
  reads, writes, the snapshot/rollback round-trip, dry-run logging with
  zero transport calls, and backend errors surfacing as `RuntimeError`
  carrying the backend's message.
- **Gates stay in core.** Adapters never gate: `require_approved` /
  `require_approval_lineage` run in the skills through `core.contracts`
  before any mutating adapter call. An adapter performs the write it is
  asked to perform, nothing more, and never inspects item status.
- **PR checklist.** Tick the adapter line in the PR template: state which
  `capabilities()` flags are true and why, backed by the backend's docs,
  and point at the fake-transport test file.

## Contributing an analytics adapter

The analytics capability slot (ADR-0009) covers the read-side pulls the
daily and weekly routines make: sessions, referral segmentation (the
AI-surface list in `plugin/skills/hoo-daily/SKILL.md`), and per-page
metrics. GA4, reached through the user's own connector, is adapter one.

A Microsoft Clarity or Matomo adapter is a skill-readable doc, not a
Python class: a page under `plugin/docs/` describing the tool's query
surface (which of the pulls above it can answer, and how a skill should
ask), the connector or credential path the user sets up to reach it, and
the same graceful-degradation rule the skills already hold to - a source
that is not reachable this run is stated as missing, never guessed. No
lib contract exists yet, and that is deliberate: analytics is read-only
through connectors, so there is no mutation to gate and no interface to
implement. The doc plus the skills' slot language is the whole contract
until a real need forces a code one.

## Contributing an image-generation adapter

The image-generation slot's job is ce-image's featured-image step
(`plugin/skills/ce-image/SKILL.md`): turn a drafted post's title and
visual concept into a 1200x630 featured image saved next to the draft.
Canva, through the user's connector, is adapter one.

A Gemini or local-generator adapter has the same shape: a doc describing
how to invoke it (the connector or credential path, the generation
call), and what it returns - an image file saved next to the draft, or
the image-brief fallback (`<slug>-image-brief.md`, as ce-image already
writes without Canva) when generation is not possible. The no-fake-
success rule applies: an adapter never claims an image was generated
when it was not - the brief fallback plus a plain statement is the
honest degradation.

## Standards

- **TDD for `lib/core`, `lib/hoo`, `lib/onsite` code.** Write the failing
  test first. See `tests/` for the existing pattern per module.
- **No em-dashes.** Use a hyphen with spaces (` - `), a comma, or split the
  sentence.
- **No hype words.** `scripts/audit.sh` (check 4, the `BANNED` pattern)
  blocks a list of marketing cliches across `plugin/`, `docs/`, and the
  root-level docs. Open the script to see the exact pattern. If the audit
  flags a word, rephrase rather than add it to an exclude list.
- **Every claim sourced.** Numbers, study results, and comparisons need a
  link to where they came from, the same standard `plugin/docs/evidence.md` holds
  itself to.
- **Cross-file consistency.** `docs/INFORMATION-MAP.md` plus audit check 8
  guard the facts quoted in more than one file (version, counts, TTLs,
  layout); when you add a load-bearing fact, add its row to the map in the
  same commit.

## Sign your commits (DCO)

organic-os uses the [Developer Certificate of Origin](https://developercertificate.org/)
(DCO), not a CLA. The DCO is a one-line attestation that you wrote the patch,
or otherwise have the right to submit it under the project's MIT license. Sign
every commit with a `Signed-off-by` trailer:

```
Signed-off-by: Your Name <your.email@example.com>
```

`git commit -s` adds it for you from your configured `user.name` and
`user.email`. Why DCO and not a CLA: it is the lowest-friction way to record
provenance, it needs no separate signing service or account to click through,
and for an MIT-licensed project a CLA would add process without adding any
right the license does not already grant.

## PR checklist

Mirrors `.github/PULL_REQUEST_TEMPLATE.md` - see that file for the exact
checkboxes a PR should carry.

## Cutting a release (maintainers)

Releases are cut by the maintainer, not by CI. Before tagging a new version,
run the pre-release check:

```
./scripts/release-check.sh
```

It fails when plugin code sits past the last tag without a version bump - the
one gap the plugin updater cannot see through. A tagged-but-unbumped commit
carries the same version string, so an installed plugin never advances to it
(the symptom and remedy are in `plugin/docs/updating.md`). The check is
advisory and deliberately NOT part of the PR CI gate: a contributor branch is
expected to sit past the last tag unbumped, so gating PRs on it would fight
normal contribution.

Required pre-release steps, in order:

1. `./scripts/release-check.sh` prints OK (bump the version if it does not).
2. Bump `version` in `plugin/.claude-plugin/plugin.json` and
   `.claude-plugin/marketplace.json`, plus any version string in
   `docs/images/install-*.svg`.
3. Add a dated `CHANGELOG.md` entry, and reconcile the README inventory line
   if counts changed (audit checks 8 and 9 enforce this).
4. `./scripts/audit.sh`, `python3 -m pytest tests -q`, and
   `./scripts/verify-gates.sh` are all green.
5. Tag `vX.Y.Z` and push the tag.

## Code of conduct

Be professional. Disagree about code, not people. Assume good faith on a
first pass, and say so plainly if a PR does not fit organic-os's scope
rather than letting it sit. Maintainer discretion applies to anything not
covered explicitly above.
