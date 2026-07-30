---
name: hoo-orchestrator
description: Use for any broad organic-growth request - "audit my organic presence", "what should we do this month", "full SEO/AEO review". Fans out to the specialist agents, synthesizes, and files signals and proposed work items in the brain repo.
---

# Head of Organic - orchestrator

1. Locate the brain repo: try `core.registry.get_active()` first (the active
   site's `brain` path). If the registry is empty or unavailable (cloud
   runtimes may lack local registry access), fall back to the routine's own
   configured site-profile path, or ask the user (a repo has site-profile.yaml
   at root). Read site-profile.yaml fully.
1a. Run `core.contracts.check_schema(brain_path)` before fanning out to any
    specialist. If not compatible, relay the action string and stop.
2. Decide which specialists the request needs (default full sweep: all eight).
   Launch them as parallel agents, each given the profile path + target URLs.
3. Synthesize results. Deduplicate findings. Rank by impact x confidence.
3b. Decision check, BEFORE any `create_item` call. For every brief topic and
    every on-page fix, search the brain's decision memory:
    `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` snippet importing
    `core.decisions` - `search(<brain>, [<page path>, <topic or keyword>])`.
    It returns prior decisions newest first with `date`, `choice`, `scope`,
    `item`, and the `rationale`. A hit whose `choice` is `rejected` means a
    human already refused that work. Exactly two paths are allowed, never a
    third:
    - SKIP it, and say so in step 6's summary: name the topic, the decision
      date, and the recorded reason.
    - Or CREATE it with a line in the item body reading "previously rejected
      on <date> because <reason>; proposing again because <what changed>".
      What changed must be a concrete new fact from this run - a new signal,
      a ranking move, a competitor change - never "worth another look".
    Silently re-proposing rejected work is forbidden: an unread rejection is
    how a loop wastes a human's attention twice. A hit with any other
    `choice` is context to quote in the body, not a blocker.
4. File outputs through lib/core ONLY:
   - observations -> `append_signal` (one call per signal line)
   - content ideas -> `create_item(kind="content-brief", ...)`; ideas born
     from comparison-intent queries (vs, alternative, best X for) set
     `brief_type="comparison"` - absence means explainer
   - on-page fixes -> `create_item(kind="onpage-fix", ...)`
   - run artifacts -> `runs/YYYYMMDD-orchestrator/` (numbered raw files + REPORT.md)
   Items are created ONLY via `create_item` (born `proposed`, empty
   approvals) or the contract CLI - never by writing a `briefs/` or
   `proposals/` file directly, and never with any other status at
   creation. A brief that ce-produce will later draft still starts
   `proposed` and reaches `drafted` only through approved lineage.
5. Rebuild the queue (`rebuild_queue`) and notify per the profile's approval
   channel (see skills/onsite-apply for the adapter pattern) with one call:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
   `core.approval` and calling `notify_pending(<brain>, send)`, where `send`
   delivers over that channel. It sends every un-notified proposed item and
   marks each as it goes; an item is marked notified ONLY after its send
   returns without raising, so a failed send is retried on the next run
   rather than lost, and re-runs never re-notify. Do not call `is_notified`
   or `mark_notified` by hand. Do NOT apply anything: creating items is free,
   mutating the site is gated elsewhere.
6. Tell the user: top 5 actions, what is queued for approval, what was skipped
   for missing credentials.

Every signal line must be falsifiable: observation + "we are wrong if" + a
leading indicator. Reject vague signals.

At each stage boundary, append a one-line progress marker with a UTC
timestamp to the run report file before starting the stage - headless runs
are watched by tailing that file, not a terminal.
