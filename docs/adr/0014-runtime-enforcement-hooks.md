# ADR-0014: Runtime enforcement via hooks, and what the ECC study rejected

- Status: accepted
- Date: 2026-09-27
- Decision makers: Shivaa Tripathi (human), Claude (agent)

## Context

Study of [ECC](https://github.com/affaan-m/ecc) (MIT, the largest
agent-harness plugin), same discipline as the gstack (ADR-0011) and OpenSEO
(ADR-0012) studies: adopt what fits the philosophy, record what does not.

ECC's central lesson for this project is architectural, not feature-level:
it does not merely describe its discipline in skill text, it enforces it at
runtime with harness hooks. organic-os ships zero hooks. Every rule we have
lives in CI (audit, gates), in the Python contract layer, or in skill
prose - and none of those layers can reach a user's own interactive
session. Two real failures on the reference deployment trace to exactly
that gap:

1. Two malformed approval records, created by hand-editing approval files
   in-session before the CLI existed, sat unnoticed for six weeks. Nothing
   at session time said "these are malformed" or "this file has one
   writer".
2. The July silence incident was at bottom a visibility failure: the loop
   was working and nothing told the operator. The fix then (v0.5.4/0.5.5)
   made the files truthful; nothing yet makes a session announce them.

## Decision

Adopt runtime hooks, scoped to two, in the plugin's hook surface:

1. **Session-start status surfacing.** When a session starts where a
   registered brain is resolvable, inject one short status line: pending
   approvals and their age, last routine signal date, site stage. The
   operator hears about waiting work by opening a session, not by
   remembering to ask. This is the incident-class fix.
2. **Derived-and-contracted file guard.** Intercept edits to files that
   have one writer (`approvals/queue.md`, approval records) and refuse
   with the writer named - the same shape as every other gate refusal:
   what was blocked, why, and the supported path.

Design constraints, learned first-hand from running under ECC's own gates
while writing this ADR:

- **Fail-silent and fast.** A hook that errors or hangs must cost the user
  nothing: wrap everything, exit 0 on any internal failure, no network, no
  writes. The loop's correctness never depends on a hook firing - hooks
  surface and guard, contracts enforce.
- **Low friction, no nagging.** A gate that interrupts routine work
  repeatedly trains the user to disable it. The status line speaks once
  per session; the file guard fires only on the narrow file set that is
  always wrong to hand-edit, and its refusal names the fix.
- **Degrade to today.** On any harness that does not run plugin hooks, the
  plugin behaves exactly as it does now. No skill may assume a hook ran.

Also adopted, same release, both cheap:

- **`AGENTS.md` at the repo root** - the cross-harness convention
  (Codex, Cursor, and others read it) so non-Claude contributor agents get
  the house rules `CLAUDE.md` gives Claude. Carried since the OpenSEO
  study; ECC ships both files.
- **Verified install channels in `SECURITY.md`** - one paragraph naming
  the only official sources (this repository and the plugin marketplace
  slug), so an impersonating re-upload is checkable. Costs nothing now,
  matters if the install base grows.

## Not adopted, and why

- **Hosted services in any form** - ECC's GitHub App, paid Pro tier, npm
  installer, website. Server, account, payment: the three things this
  README promises are absent. Same rejection as telemetry (ADR-0011) and
  OpenSEO's architecture (ADR-0012).
- **Their "instincts" memory system.** The skillbook already covers this
  ground with stricter discipline: evidence tiers, staleness decay
  (ADR-0011), and a human-curated reflector instead of auto-extracted
  behaviors. Importing a second memory system would fork the brain.
- **Thirteen translated READMEs and a Discord.** Community-scale mismatch;
  Discussions carry current volume. Revisit trigger: sustained non-English
  issue traffic, or Discussions threads outgrowing asynchronous form.
- **Multi-harness ports as a commitment.** ECC supports many harnesses;
  every organic-os skill assumes the plugin's Python lib and a brain repo
  (the ADR-0013 constraint). Carried as an investigation task, not a
  phase: the deliverable is an ADR - port with scope, or reject with
  reasons.

## Consequences

- The plugin gains its first harness-runtime surface. Hook scripts are
  code: stdlib-only, unit-tested, audited like `lib/core`.
- Enforcement now has three layers with distinct jobs: contracts refuse
  illegal transitions, CI refuses bad commits, hooks surface state and
  guard one-writer files in live sessions. No layer depends on another.
- Where plugin hooks do not run (harness-dependent), users simply keep
  today's behavior - the constraint is verified against current docs at
  build time and recorded in the connectors/runtime documentation.

## Revisit triggers

- The hook surface changes shape in the harness: re-verify, do not pin.
- Evidence of hook friction in real use (a user disabling them): revisit
  the guard's file set and the status line's length first, the feature
  second.
- A true standalone skill with no lib or brain dependency ships: the
  ADR-0013 and portability questions reopen together.
