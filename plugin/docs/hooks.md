# Session hooks

Since v0.8.0 the plugin ships two harness runtime hooks, wired in
`plugin/hooks/hooks.json` (decision: [ADR-0014](../../docs/adr/0014-runtime-enforcement-hooks.md)).
They surface state and guard one-writer files in live sessions; they never
enforce correctness - contracts refuse illegal transitions and CI refuses
bad commits whether or not a hook ever fires.

## What each hook does

**Session-start status line** (`session_status.py`, SessionStart). When a
session starts where a brain resolves - the working directory or a parent
that holds `site-profile.yaml` plus `approvals/`, else the sites registry's
active site - it injects at most 3 short lines, and only lines that carry
news:

```
[organic-os] example-com: 2 items awaiting approval (oldest 12d); queue notes 2 MALFORMED. Run /organic-os:status.
[organic-os] last routine signal 2026-09-25 (2d ago); stage: early.
```

Nothing pending, no MALFORMED/PARTIAL queue notes, and a signal fresher
than 2 days means it prints nothing at all - silence is the default, per
ADR-0014's no-nagging constraint. The line formats are canonical in
`render_lines` in `plugin/hooks/session_status.py`
(see `docs/INFORMATION-MAP.md`). The read is cheap by construction: no
network, no git commands, no writes, directory listings capped.

**Derived-file guard** (`derived_guard.py`, PreToolUse on
Edit|Write|MultiEdit). Refuses hand edits to the files inside a brain repo
that have exactly one writer, naming the writer and the supported path -
the same refusal shape as every other gate:

- `approvals/queue.md` - derived, rebuilt from item frontmatter by
  `core.contracts.rebuild_queue`; hand edits are overwritten and can
  corrupt state.
- `approvals/*.md` decision records - written by
  `core.approval.record_decision` after a gate; hand-edited records are
  how the reference deployment got six weeks of unnoticed malformed
  approvals.

The guarded-file list is canonical in `plugin/hooks/derived_guard.py`
(see `docs/INFORMATION-MAP.md`). A file is only guarded inside a brain
repo (its `approvals/` directory has a `site-profile.yaml` sibling); a
file that merely shares the name in any other project is never touched.

## The fail-silent guarantee

A hook that errors or hangs must cost you nothing. Both scripts wrap every
code path: any internal failure - unreadable directory, malformed YAML,
missing PyYAML, garbage stdin - means exit 0 with no output, which the
harness reads as "nothing to say" or "allow". No network calls, no writes,
stdlib plus PyYAML only. The guard fails open by design: an edit it cannot
judge is allowed, because contracts and CI still hold the line behind it.

## Where hooks run, honestly

Plugin hook execution is harness-dependent. Verified 2026-09 against the
current official docs: hooks fire on session start and before tool use in
Claude Code once the plugin is installed; the docs are silent on whether
plugin hooks fire in Cowork or in `claude -p` runs. The plugin is built so
this does not matter: nothing in any skill, gate, or contract assumes a
hook ran. On a harness that does not run them you simply keep the exact
pre-v0.8 behavior.

## Disabling

Remove the hook's entry from `plugin/hooks/hooks.json` in your installed
copy (or uninstall the plugin). Both refusal messages name this path. If
you find yourself disabling the guard because it fires on legitimate work,
that is a bug worth reporting - the file set is meant to be the narrow set
that is always wrong to hand-edit.
