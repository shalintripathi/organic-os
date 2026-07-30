---
name: onsite-propose
description: Use to turn audit findings or signals into concrete gated change proposals - "propose fixes for /pricing", /organic-os:propose.
---

# Propose on-page changes (creates gated items; applies nothing)

1. Input: audit findings, a signal reference, or a user request naming URLs.
2. For each change, draft the exact after-state: new title (<= 60 chars),
   new meta description (<= 155 chars), canonical, focus keyword, schema
   JSON-LD payload, or a content edit (quote the exact before/after text).
2b. Decision check, BEFORE any `create_item` call. For every target, search
   the brain's decision memory:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` snippet importing
   `core.decisions` - `search(<brain>, [<page path>, <focus keyword>,
   <what the fix does>])`. It returns prior decisions newest first with
   `date`, `choice`, `scope`, `item`, and the `rationale`.
   A hit whose `choice` is `rejected` means a human already refused this
   work. Exactly two paths are allowed, never a third:
   - SKIP it, and say so in the run report: name the page, the decision
     date, and the recorded reason.
   - Or CREATE it with a line in the proposal body reading "previously
     rejected on <date> because <reason>; proposing again because <what
     changed>". What changed must be a concrete new fact - a new signal, a
     ranking move, a competitor or site change - never "worth another
     look".
   Silently re-creating a rejected proposal is forbidden. A hit with any
   other `choice` is context to quote in the body, not a blocker.
3. One proposal item per page: `create_item(kind="onpage-fix", target=<url>,
   body=<before/after table + rationale + expected effect + falsifiability>)`.
   `create_item` is the ONLY birth path - items are born `proposed` with an
   empty approvals list; never write a `proposals/` file directly or set
   any other status at creation.
4. Rebuild queue (`create_item` births items; the rebuild is what puts them in
   `approvals/queue.md`). Notify per the profile approval channel with ONE call:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
   `core.approval` and calling `notify_pending(<brain>, send)`, where `send`
   is a callable taking `(path, item)` and delivering over the channel chosen
   below. It sends every un-notified proposed item and marks each as it goes.
   An item is marked notified ONLY after its send returns without raising, so
   a failed send is retried on the next run rather than lost, and re-runs
   never re-notify. Do not call `is_notified` or `mark_notified` by hand.
   Channel selection:
   - in-session: present now with AskUserQuestion (approve/reject each)
   - telegram: send via core.telegram `send_item` (token from env file), then
     poll with `core.approval.process_telegram_decisions` on the next run to
     collect replies (offset persisted automatically)
   - pr-merge: commit the proposal file on a branch, open a PR (gh pr create)
   - slack/email: post/send a summary via the available connector; approval
     happens in-session or by channel reply read at the next run
4b. Image and alt-text fixes (action type: image-fix). Audit findings
   from the images checks - a missing or empty alt (skills/onsite-audit
   step 2), an imageless 500+ word explainer (step 3.3) - become one
   `onpage-fix` proposal per page whose body declares `action:
   image-fix` and carries one line per image:
   - Missing alt text: the image's src and media id (from the CMS
     adapter's `get_media`), the current alt (empty), and the proposed
     alt text. Ground the proposed alt in the surrounding content:
     describe what the image shows for someone who cannot see it, in
     one sentence. Never keyword-stuffed - alt text is accessibility
     text first, and a keyword appears only when the image is genuinely
     about it.
   - Missing in-content image: reference the ce-image brief path
     (skills/ce-image writes `<slug>-image-brief.md`) as the creation
     route, and name where in the post the image belongs. Creation
     happens through that brief, outside the apply path: apply only
     places a file that already exists (see the image-fix section in
     skills/onsite-apply), so the proposal must be executable once the
     asset exists, and honest about waiting until it does.
   Same gate as every proposal: born proposed via `create_item`,
   approved by a human, executed by onsite-apply.
5. Record any in-session decisions immediately via the contract CLI:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -m core approve <item-path>
   --actor <user> --channel in-session` (or `reject`, with `--note` for any
   reason given). Never edit brain frontmatter directly. The contract CLI is
   the only write path for status and approvals.
