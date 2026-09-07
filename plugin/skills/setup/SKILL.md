---
name: setup
description: Use when the user installs organic-os, says "set up organic-os", "onboard my site", "connect my website", "add another website", "switch site", "organic-os status", or runs /organic-os:setup or /organic-os:sites. Reads the enable-time install form first (anything filled there is never re-asked), audits the site URL and proposes a pre-filled profile before asking, scaffolds the per-site brain repo, runs the connector wizard with live verification, records credentials one at a time, registers routines for the chosen runtime, ends with a tested postflight scorecard, and manages the multi-site registry (add / update / switch / status).
---

# organic-os setup

You are onboarding or managing sites in organic-os. Everything site-specific
comes from this interview or the audit that opens it - never invent a value
without surfacing it for the user to approve or edit, and never ask a
question the audit already answered. One question at a time, AskUserQuestion
with options where possible.

Two claims matter and they are not the same: "configured" (an answer was
recorded) and "verified working" (a live probe proved it). Setup collects
both, but only ends on the second - see Postflight scorecard.

## Interview style (every mode, every question)

- **One question at a time.** Never present a wall of questions. Ask, wait
  for the answer, then ask the next one.
- **Offer a default with every question.** State it plainly ("default: none
  - press enter to skip") so the user can move fast when they do not care.
- **Choice questions are chips.** Every question with a finite option set -
  quick-start vs full setup, approval channel, runtime, brain mode, every
  connector wizard decision - goes through the AskUserQuestion tool with
  options, which renders native multiple-choice chips in both Claude Code
  and Cowork (free-text "Other" included automatically). Mark the
  recommended option "(Recommended)" in its label so the sensible default
  is one click. Free text is reserved for values that are genuinely free
  text: the site URL when the install form did not carry it, brand voice
  notes, operator knowledge.
- **Install-form answers are pre-answered questions.** Anything Step 0.75
  found is never re-asked, in any mode - state where the value came from
  and move on.
- **Secrets are referenced, never echoed.** Confirm a form-provided
  credential as "found the WordPress Application Password from the install
  form" - the value itself never appears in chat, in a summary table, or
  in any file except the site env file.
- **Show progress.** Prefix each question with where the user is - e.g.
  "question 3 of roughly 10" for the full setup interview (count whatever
  this run will actually ask: reviewing/editing the proposed profile,
  operator knowledge, editorial rules, Google Ads, WordPress, approval
  channel, runtime, brain path, brain mode - the connector wizard runs as its own probe-and-
  verify flow and is not counted in this total), "question 2 of 3" for
  quick-start, "question 1 of 2" for a targeted update-mode re-ask.
- **End with a summary table.** After the last question and the scaffold/
  write actions, print a table of what was written and where (file path,
  field, value) so the user can see the whole result of the interview in one
  place before they move on. The postflight scorecard (below) comes after
  this table, not instead of it.

## Step 0: environment checks

- Confirm `python3` is on PATH.
- Confirm PyYAML is importable: `python3 -c "import yaml"`. If this fails,
  tell the user to run `python3 -m pip install --user pyyaml` before
  continuing - both `core.contracts` and `core.registry` require it.

## Step 0.5: where am I, where will routines run

Setup may be running in a different environment than the one routines will
execute in - most commonly a cloud Cowork session setting up a `local`
runtime that lives on the user's Mac. Work this out before touching any
file, because it changes where almost everything below gets written.

1. **Determine the setup environment.** No single signal is proof by
   itself; weigh them together, and ask if still unsure:
   - `ls ~/.config/organic-os 2>/dev/null` and `test -f ~/.claude.json` -
     a fresh cloud sandbox rarely carries config from a prior local run.
   - `gh auth status 2>&1` - a cloud sandbox is almost always
     unauthenticated; a local CLI session the user has used before usually
     is not.
   - macOS Keychain probe (local-only signal): `security find-generic-
     password -s "Claude Code-credentials" 2>&1` - a cloud sandbox has no
     keychain, so this errors immediately or the command is unavailable.
   - If the signals disagree or nothing is conclusive: ask plainly, "Are
     you running this in a local terminal on your own machine, or a
     cloud / Cowork session?"
2. **Ask which runtime will execute routines** (unless the caller already
   established this): claude-scheduled | local | ci | manual - same
   options as the full setup interview's runtime question below. If
   answered here, do not re-ask it later; carry it forward.
3. **If setup environment and runtime location match** (e.g. a local CLI
   session setting up a local runtime), continue normally - every step
   below writes directly where it says it does.
4. **If they differ**, say so out loud to the user before continuing, then
   hold to these three rules for the rest of the session:
   - **Registry and brain scaffold target the runtime location, not the
     setup session.** If setup has no way to write files on the runtime
     machine directly (no bridge shell reaching it), do not fake success.
     Emit a ready-to-run snippet - one bash block covering
     `init_site_repo.py`, `core.registry.register(...)`, and `git init` -
     for the user to paste into a terminal on the runtime machine. Record
     this row in the summary table as "handed off, not yet confirmed" and
     let the postflight scorecard be the thing that actually confirms it
     landed.
   - **Connector probes are labeled with the context that actually ran
     them.** Every `core.contracts.record_connector(...)` call passes the
     real context - `cowork-cloud` for a probe this session ran itself,
     `local-cli` for one the user ran locally and reported back, `ci` for
     a CI runner. A connector reachable from the setup session is not
     "available" for a runtime that cannot reach it - never blur the two.
     Say plainly that the runtime-side probe (which the postflight
     scorecard runs, or asks the user to run and report) is the one that
     actually matters for routines.
   - **Never run git through a device bridge.** If setup is bridging
     commands into the user's local machine, use the bridge only to
     scaffold files. `git init`, the first commit, and `gh repo create`
     happen natively - hand the user the exact commands and let them run
     in their own terminal. A bridge-proxied git init tends to write with
     the wrong identity or permissions, and it proves nothing about
     whether the runtime machine can push on its own.

## Step 0.75: read the install form

Claude Code and Cowork can render a native configuration form when the
plugin is enabled, declared in `plugin.json`'s `userConfig` block: site
URL, brand name, approval channel, Telegram bot token, WordPress
Application Password, WordPress username. Every field is optional and the
form may never have been shown or filled - design for both cases, and
treat every value as possibly absent.

Where the values land at runtime:

- **Sensitive fields** (`telegram_bot_token`, `wp_app_password`) are
  stored in the OS keychain and reach this session only as environment
  variables: `CLAUDE_PLUGIN_OPTION_TELEGRAM_BOT_TOKEN` and
  `CLAUDE_PLUGIN_OPTION_WP_APP_PASSWORD`. Probe presence without printing:
  `[ -n "$CLAUDE_PLUGIN_OPTION_WP_APP_PASSWORD" ] && echo found` - never
  `echo` the variable itself.
- **Non-sensitive fields** substitute as `${user_config.site_url}`,
  `${user_config.brand_name}`, `${user_config.approval_channel}`, and
  `${user_config.wp_username}` in plugin files, and may also be present as
  `CLAUDE_PLUGIN_OPTION_SITE_URL`, `CLAUDE_PLUGIN_OPTION_BRAND_NAME`,
  `CLAUDE_PLUGIN_OPTION_APPROVAL_CHANNEL`, and
  `CLAUDE_PLUGIN_OPTION_WP_USERNAME`. List names only, never values:
  `env | grep '^CLAUDE_PLUGIN_OPTION_' | cut -d= -f1`.
- **Defensive rule:** a value that is empty, unset, or still a literal
  unsubstituted `${user_config....}` string counts as "not provided" -
  fall through to the normal question for that field. Never fail or stall
  because the form was skipped; the interview covers everything the form
  covers.

What each present value pre-answers (never re-ask any of these):

- `site_url` - the URL question in both modes; the audit starts from it
  directly.
- `brand_name` - replaces the domain-label guess.
- `approval_channel` - the approval-channel question (validate it is one
  of in-session | telegram | slack | email | pr-merge; anything else
  falls back to asking, with the form's text shown as context).
- `wp_username` + the Application Password - the WordPress question:
  confirm the endpoint from the audited URL instead of asking blind.
- `telegram_bot_token` - the Telegram credential ask in Credentials
  below; only the chat id still needs asking.

Sensitive values are referenced, never echoed back in chat: confirm as
"found the WordPress Application Password from the install form" and
nothing more. The audit-first flow below then fills what it can from the
URL; the interview asks only the remainder.

## Step 1: read the registry, pick a mode

Read `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` calling
`core.registry.load()` (default path `~/.config/organic-os/sites.yaml`,
resolved at the runtime location per Step 0.5 when it differs from the
setup session).

- **Registry empty** (no sites): if the caller (e.g. `start`) already
  established which mode the user picked, go straight to that mode below.
  Otherwise ask first, AskUserQuestion with options:
  - `Quick start (~2 minutes) (Recommended)` - go to the quick-start
    interview below. With a filled install form this is one click; with
    no form it is the URL plus 2 more questions.
  - `Full setup (audit the site, then review the proposal)` - go to the
    full setup interview below.
- **Sites exist**: ask the user what they want, AskUserQuestion with options:
  - `update <active site name>` - refresh the currently active site's profile
  - `add another website` - onboard a new site (full setup interview, own
    brain path)
  - `switch active site` - change which site routines/commands act on
  - `show status` - print the registry (all sites, which is active) plus the
    active site's site-profile.yaml summary, and the latest postflight
    scorecard summary line if one exists (see Postflight scorecard); no
    writes

### Update mode

1. READ the existing `site-profile.yaml` for the active site first. Present
   the current values back to the user.
2. Schema check: run `core.contracts.check_schema(brain_path)`. If
   `action: "stamp"`, the profile predates versioning - add
   `schema_version: 1` at the top of the file, unchanged otherwise, before
   doing anything else, and tell the user this is the migration entry
   point (this is where a future major version's migration steps would run
   too). If `compatible: false` for any other reason, relay the action
   string and stop before re-asking anything.
3. Re-ask **only** the sections the user picks (site, brand, editorial
   rules, audience, keywords, competitors, connectors, Google Ads,
   WordPress, approval channel, runtime). Do not re-run the full setup interview. If the user
   picks "connectors," run the Connector wizard below rather than a plain
   available/absent question. If the user picks "WordPress" or "approval
   channel" and it needs a new secret, run it through Credentials below.
   Update mode re-asks these sections directly - it does not re-run the
   audit-and-propose flow, since a returning user already has a profile to
   edit from.
4. Rewrite `site-profile.yaml` with just those changes.
5. Skillbook: NEVER re-append an operator note unless its text is new - read
   `skillbook.md` first, skip anything that already matches an existing
   entry's text.
6. NEVER touch `signals/`, `decisions/`, `reflections/`, or existing
   skillbook entries beyond the dedup check above - those are memory, not
   config, and setup does not rewrite memory.
7. Do not re-register routines unless the user explicitly asks to change
   cadence or runtime.
8. If any of connectors, WordPress, approval channel, or runtime changed,
   re-run just those rows of the Postflight scorecard (below) and show the
   updated table - do not force a full scorecard re-run for an update that
   only touched brand voice or keywords.
9. **Rule of thumb to state to the user: config is editable, memory is not.**
   `site-profile.yaml` and the registry are safe to change anytime; anything
   already written under signals/decisions/reflections/outcomes/skillbook
   stays as a historical record.

### Add mode

Run the full setup interview below with a fresh brain path (never reuse
another site's brain). After scaffolding, call `core.registry.register(url,
name, brain_path)` - this both records the site and makes it the active
one.

### Switch mode

Ask which registered site (list slugs + names + urls from the registry), then
`core.registry.set_active(slug)`. No file other than the registry changes.

### Show status

Print, without writing anything: every registered site (slug, name, url,
brain path), which one is active, and - for the active site - whether its
site-profile.yaml, skillbook.md, and approvals/queue.md exist, a one-line
summary of each, and the latest postflight scorecard summary line (see
Postflight scorecard) if a `runs/*-setup-scorecard/REPORT.md` exists.

## URL first, audit before asking (shared by quick-start and full setup)

Both modes below start the same way: get the URL, then let organic-os do
the looking instead of the asking. Ask only what an audit genuinely cannot
answer - this is the "audit-and-propose" model: enter a URL, get a
pre-filled profile to approve, instead of a wall of questions the plugin
could have answered itself.

1. **Ask for the site URL** - unless Step 0.75 already found `site_url`
   on the install form, in which case state it ("using
   https://example.com from the install form") and skip straight to the
   audit. When asking: no default - this is the one thing neither mode
   can guess. If the brand name is not obviously derivable from the
   domain label (a generic domain, or one that plainly does not match the
   brand), ask for it in the same turn; otherwise guess it from the domain
   label and let the user correct it during proposal review. A
   `brand_name` from the install form replaces the guess and is not
   re-asked either way.
2. **Audit before asking anything else.** Fetch the homepage and
   `<url>/sitemap.xml` (or whatever sitemap the homepage's `<link
   rel="sitemap">` tag or `robots.txt` points at instead).
   - **Detect the CMS**: look for `wp-content`/`wp-includes` paths, a
     `generator` meta tag, and Yoast/RankMath fingerprints - a
     `post-sitemap.xml`/`page-sitemap.xml` sitemap-index shape usually
     means Yoast, a `sitemap-pt-*` shape usually means RankMath, plus
     either plugin's characteristic HTML comments. Record what was
     detected; this seeds the WordPress question later instead of asking
     blind.
   - **Read 3-5 representative pages**: the homepage plus whatever the
     sitemap or homepage nav suggests matters most - an about/product
     page, a couple of the most prominent content pages.
   - **Propose, from what was actually read** (never invent a value - if
     the audit could not reach enough pages to support a field, leave it
     blank and say so in the proposal rather than guessing):
     - Brand voice descriptors, grounded in the actual copy (e.g. "short
       sentences," "second person," "numbers up front" - whatever the
       fetched pages actually show, not a generic default list).
     - Audience segments, from who the copy is visibly written for.
     - 5-9 seed keywords, pulled from titles, headings, and repeated
       topics across the fetched pages.
     - 3-5 content-SERP competitors: run WebSearch on the top 2-3 proposed
       keywords and take the sites that actually rank for them. State the
       distinction to the user plainly - these are sites competing for
       the same search queries, which is not the same list as business
       rivals; the user can swap in rival domains during review if that
       is what they actually want tracked.
     - Target geos: from the TLD (`.in` -> `IN`, `.co.uk` -> `GB`, a
       generic `.com`/`.io`/etc. left to the next two signals), the
       homepage's `lang` attribute, and any address/currency/phone-format
       signals visible on the fetched pages.
3. **Degradation - the site cannot be fetched** (no web access this
   session, the site blocks fetches, a timeout): say so plainly, do not
   fabricate a proposal, and fall back to asking directly for whatever the
   audit would have proposed - brand name from the domain label (step 1),
   empty keywords/competitors, TLD-only geo guess. Note in the closing
   summary that the audit did not run, and why.

## Quick-start interview (propose + accept-all + defaults, ~2 minutes)

Runs the shared audit above, then asks at most 3 questions: URL, approval
channel, confirm - minus anything the install form pre-answered (Step
0.75). **With a filled form, quick start asks ZERO questions:** the URL
and the channel come from the form, and only the confirm chip in question
3 remains. Form filled = one click to a configured site. Everything else
gets a stated default, not a silent one - tell the user what was
defaulted (or proposed-and-accepted, or read from the form) in the
closing summary table so nothing is a surprise later.

1. Site URL (+ brand name only if not derivable - see above). Skipped
   entirely when the form carried `site_url`.
2. Approval channel, AskUserQuestion chips: `in-session (Recommended)` |
   telegram | slack | email | pr-merge. Recommended because it needs no
   setup and works immediately. Skipped entirely when the form carried a
   valid `approval_channel`.
3. Confirm, AskUserQuestion chips: show the proposed profile table (brand
   voice, audience, geos, keywords, competitors - whatever the audit
   produced, or its degraded fallback) and ask "does this look right?" -
   **Accept and continue (Recommended)** or **Switch to full setup to
   review row by row**. Quick-start does not support per-row editing; a
   user who wants that is, by definition, choosing full setup.

Defaulted or proposed-and-accepted silently (state each one in the summary
table, do not ask):

- **Brand voice, audience, geos, keywords, competitors**: whatever the
  audit proposed, accepted as-is on confirmation in question 3. This is
  new since the audit-and-propose rework - quick-start used to leave
  keywords, competitors, and voice notes empty; now it seeds them from the
  site itself. If the audit degraded (no web access, fetch blocked), the
  old empty/TLD-only defaults apply instead, and the summary says so.
- **Operator notes**: left empty - the audit cannot infer what the
  operator knows, and quick-start does not ask it. Fill in later via
  `/organic-os:setup` update mode.
- **Connectors, Google Ads, WordPress**: left `unknown`/`none`/unconnected.
  Quick-start never runs the Connector wizard and never probes connectors -
  analysis-only is the correct default outcome for a 2-minute setup, even
  when the audit detected WordPress on the site itself. If the install
  form carried a WordPress Application Password or a Telegram bot token,
  say so ("found the WordPress Application Password from the install
  form - run /organic-os:setup update mode to connect and verify it") -
  quick start records nothing it has not probed, and it does not probe.
- **Runtime**: `manual`. The user runs commands themselves until they choose
  to schedule routines (`$CLAUDE_PLUGIN_ROOT/docs/routines.md`).
- **Brain path**: `~/organic-hq/<slug>`, same derivation as full setup.
- **Brain mode**: `local` (no git init, no GitHub repo offer). Quick-start
  optimizes for "see something work in two minutes," not for versioned
  memory from the first run - the user can move to a git brain later via
  update mode if they want it.

### Actions after the quick-start interview

1. Run: `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 "$CLAUDE_PLUGIN_ROOT/lib/core/init_site_repo.py" <brain-path> --url <url> --name <name>`
2. Fill `site-profile.yaml`: the audited/confirmed profile fields (brand
   voice, audience, geos, keywords, competitors, or their degraded-audit
   fallback), the answered fields (approval channel, confirm), plus every
   silently defaulted field from the list above (runtime: manual, brain
   mode: local, brain repo path).
3. Call `core.registry.register(<url>, <name>, <brain-path>)`.
4. Print the summary table (interview style, above): what the audit
   proposed, what was asked and answered, what was defaulted, and where
   each value landed in `site-profile.yaml`. Point at `/organic-os:setup`
   update mode for editing anything, and at `/organic-os:onsite-audit` as
   the first thing to try right now.
5. Run a lightweight postflight scorecard: just "brain scaffold" (the four
   files from step 1 exist) and "registry readable" (`core.registry.
   get_active()` returns this site). Every connector/WordPress/approval/
   runtime row is skipped, not shown as failing, because quick-start never
   configured them - the scorecard only tests what was actually attempted.

## Full setup interview (propose + row-by-row review, also used for "add another website")

Runs the shared audit above, then works through the proposal and whatever
it could not answer.

1. **Review the proposed profile.** Present the full table from the audit
   (site, brand voice, audience, keywords, competitors, geos, WordPress
   detection). Ask, AskUserQuestion chips: **Accept all (Recommended)** /
   **Edit specific rows** / **Answer manually instead**.
   - *Edit specific rows*: one row at a time, same interview-style rules
     as everything else here - one question, a stated default (the
     audit's proposed value), progress shown.
   - *Answer manually instead*: skip the audit's proposal entirely and
     ask each field the old way - for a site the audit could not usefully
     read, or a user who wants zero inference. Site: URL, brand name,
     sitemap URL (offer to guess `<url>/sitemap.xml` and verify with a
     fetch). Brand rulebook: voice rules, banned phrases (offer sensible
     defaults - first person, short sentences, facts before adjectives, no
     exclamation marks; user edits). Audience: segments/ICP, geographies,
     languages. Keywords: target keywords/topics (free list; can be empty
     - keyword-intel will propose). Competitors: domains (up to 5 to
     start).
2. **Operator knowledge**: "What do you already know works in this niche -
   tips, channels, formats?" Each answer becomes a skillbook entry tagged
   `evidence: anecdotal`. The audit cannot infer this - always ask it,
   regardless of how the profile above was filled in.
2b. **Editorial rules**, AskUserQuestion chips: does the organization
   have written editorial conventions the QA pass should enforce as
   hard checks? Options: **Use the defaults (Recommended)** - sourcing
   on key claims only, no link or image minimums; **Set link, image,
   and sourcing rules now** - one question per key (minimum internal
   links, external-link cap, minimum in-content images, sourcing mode
   key-claims or every-claim, require a named human reviewer), each
   with its default stated; **Later, via update mode**. Answers land in
   the profile's `editorial:` section; the canonical defaults live in
   `core.contracts.editorial_policy`, so an absent section means the
   defaults, and free-text conventions still belong in the brand
   rulebook - the structured keys are the enforceable floor, the prose
   is the voice.
3. **Connectors**: run the **Connector wizard** below for GA4 and GSC (the
   heartbeat pair) first, then Notion, Slack, Canva, OpenSEO as optional
   extras.
   This replaces a plain available/absent question - every connector this
   interview records has been probed, and every `verified` status has
   passed one live query, not just "the tool appeared to be there."
4. **Google Ads**: ask whether they have a developer token and which access
   level. Point to https://github.com/shalintripathi/organic-os/blob/main/plugin/docs/credentials/google-ads-token.md
   (also at $CLAUDE_PLUGIN_ROOT/docs/credentials/google-ads-token.md in a
   local checkout). If they have a developer token or client secret to
   hand, route it through **Credentials** below. Record status only.
5. **WordPress**: infra is never guessed, so this stays an explicit
   question even though the audit already looked - if the audit detected
   WordPress, say so and ask to confirm the endpoint URL + username rather
   than asking blind; otherwise ask (AskUserQuestion chips: **Yes,
   WordPress** / **Another CMS** / **No CMS connection (Recommended to
   start)**) whether they have a connected site another CMS runs on. If
   Step 0.75 found the Application Password (and `wp_username`), the
   question collapses to confirming the endpoint URL: "found the
   WordPress Application Password from the install form" - never echo it.
   Otherwise the Application Password goes through **Credentials** below -
   it mirrors the exact wording of
   `plugin/docs/credentials/wordpress.md` step 2.
6. **Approval channel**, AskUserQuestion chips: `in-session (Recommended)`
   | telegram | slack | email | pr-merge. Recommended because it needs no
   setup and works immediately; no channel is privileged. Skip the
   question entirely when the form carried a valid `approval_channel` -
   state the value and move on. For telegram: chat id here, bot token
   through **Credentials** below (same env file, key
   `TELEGRAM_BOT_TOKEN`) - or from the install form when present.
7. **Runtime for routines**, AskUserQuestion chips: `manual (Recommended
   to start)` | claude-scheduled | local | ci - skip this question if
   Step 0.5 already answered it; otherwise ask now and carry the answer
   into Step 0.5's rules for the rest of setup. Manual is recommended
   first because it costs nothing to change later (`plugin/docs/
   routines.md`); explain costs honestly: claude-scheduled and local run
   on the user's Claude subscription; ci uses an API key billed per
   token.
8. **Where should the brain live?** Default `~/organic-hq/<slug>` **on the
   runtime machine** (per Step 0.5 - if setup and runtime differ, this
   path is not on the machine setup is currently running in), where
   `<slug>` is derived the same way the registry derives it (host minus
   `www.`, dots to hyphens - e.g. `example.com` -> `example-com`). Offer
   to change the path. After the answer, run `PYTHONPATH="$CLAUDE_PLUGIN_
   ROOT/lib" python3 -c "..."` calling `core.registry.path_warnings(<brain-
   path>, <runtime from question 7>)` - on the runtime machine if setup
   can reach it directly, or as a line inside the ready-to-run snippet
   (Step 0.5) with instructions to run it before scaffolding if setup
   cannot. If it returns any warnings, show them to the user verbatim and
   re-ask the question, with the default now switched to
   `~/organic-hq/<slug>`. Do not scaffold anything at a path that still has
   open warnings without the user explicitly confirming they want to
   proceed anyway.
9. **Brain mode**, AskUserQuestion chips: `git repo (Recommended)`
   (needed for claude-scheduled and ci runtimes and for versioned
   memory) or `local folder`. If git and Step
   0.5 flagged a setup/runtime mismatch, `git init` and the first commit
   happen natively on the runtime machine (see Step 0.5's git rule) - do
   not run them through a bridge.

The AI-visibility baseline offer (below) and the Postflight scorecard
(below) close out full setup - existing v3 machinery, unchanged by this
rework beyond running after a proposal instead of after a plain question
list.

## Connector wizard (GA4, GSC, then Notion/Slack/Canva/OpenSEO)

Replaces a passive "is this available" question with a probe-then-verify
flow. Run this for GA4 and GSC first - call them the heartbeat pair,
because they are the primary data source the rest of the plugin depends on
- then, only if the user wants to continue, for Notion, Slack, Canva, and
OpenSEO (the search-data adapter - user-run, their own DataForSEO key;
connect command and tool surface in `plugin/docs/connectors.md`).

For each connector, in this order:

1. **Probe** reachability in the current context: try listing the
   connector's tools (GA4/GSC/Notion/Slack/Canva/OpenSEO - whatever
   surface this session actually exposes). Note which context this probe
   ran in (`local-cli`, `cowork-cloud`, `ci`) - it is passed to
   `record_connector` either way.
2. **If reachable, run exactly one live verification query before
   recording anything as verified:**
   - GSC: list sites.
   - GA4: pull a 7-day sessions count.
   - Notion: search or list one workspace/database.
   - Slack: list channels.
   - Canva: list designs or brand kits.
   - OpenSEO: `whoami` (record the connector as `openseo`).
   A live call, not just tool presence, is what earns `verified` - a
   connector can appear installed but be unauthorized or pointed at the
   wrong property, and only a real call catches that. Only after the live
   call succeeds: `core.contracts.record_connector(profile_path, name,
   "verified", context)`. If the live call fails even though the
   connector looked reachable, treat it as absent and continue to step 3 -
   never record `verified` on a failed live call.
3. **If absent (or the live call failed):** present the guided connect for
   the user's actual surface:
   - claude.ai / Cowork: Settings, then Connectors.
   - Claude Code: `/mcp`, or `claude mcp add <server>` on the command line.
   Then offer, AskUserQuestion chips:
   - **Wait, connect it now** - pause, let the user connect, then re-probe
     from step 1 once they confirm. Marked "(Recommended)" for GSC and
     GA4, the heartbeat pair.
   - **Skip for now** - `core.contracts.record_connector(profile_path,
     name, "declined", context)`, plus one honest line about what
     degrades, pulled from the matching row of `plugin/docs/
     connectors.md`'s capability table. Marked "(Recommended)" for the
     optional extras (Notion, Slack, Canva, OpenSEO) - they are extras,
     and skipping keeps setup short.

**GSC/GA4 get a stronger framing than the optional extras.** Before offering
to skip either one, say plainly: "organic-os without GSC/GA4 still runs,
but `hoo-daily` will log no-data signals with nothing to act on until one
of these connects. Of everything in this interview, this is the single
connector most worth stopping to fix now." Still respect a "skip for now"
answer if that is what the user wants - never force a connection, just
make the tradeoff explicit before they choose.

**IndexNow (offered last, no account needed).** After the connectors
above, offer instant URL submission to Bing, Yandex, and the other
IndexNow-participating engines. Same verify-not-record bar as everything
else here:

1. Generate a key: `hoo.indexnow.gen_key()` (32-char hex). Show it - it
   is an ownership proof, not a secret.
2. Instruct placing `<key>.txt` at the site root, containing exactly the
   key (`hoo.indexnow.key_file_content(key)`): via the host's file
   manager or SFTP into the web root, or - on WordPress, where the media
   library cannot write to the root - a root-file plugin or the same
   file-manager route. Offer "I'll place it now, then verify" or "skip
   for now".
3. Verify by fetching `https://<host>/<key>.txt` and comparing the body
   to the key. Only a matching fetch earns enablement - then write
   `indexnow: {enabled: true, key: <key>}` into site-profile.yaml
   (additive key, schema stays 1). A failed or skipped fetch records
   nothing and leaves IndexNow off; say what degrades - applied and
   published changes wait to be crawled naturally instead of being
   submitted on ship.

## Credentials: one secret at a time

Applies to every secret this interview or an update touches - the
WordPress Application Password, the Telegram bot token, the Google Ads
OAuth client secret.

- **The install form comes first.** If Step 0.75 found the secret
  (`CLAUDE_PLUGIN_OPTION_WP_APP_PASSWORD` or
  `CLAUDE_PLUGIN_OPTION_TELEGRAM_BOT_TOKEN`), skip the ask entirely:
  confirm as "found the ... from the install form", write the site env
  file directly from the variable without printing it -
  ```
  mkdir -p ~/.config/organic-os && printf 'WP_APP_PASSWORD=%s\n' "$CLAUDE_PLUGIN_OPTION_WP_APP_PASSWORD" > ~/.config/organic-os/<site-slug>.env && chmod 600 ~/.config/organic-os/<site-slug>.env
  ```
  (same pattern, key `TELEGRAM_BOT_TOKEN`, for the bot token; append with
  `>>` when the file already exists) - and verify by probe as usual. The
  form value is keychain-backed; the env file exists so routines outside
  this session can read it.
- **One secret per question.** Never present a wall of env-file fields at
  once.
- **Name it precisely** - the exact field the user is looking at in the
  exact UI, so they never go hunting. Mirror the wording already proven in
  `plugin/docs/credentials/wordpress.md`: "In wp-admin, go to Users ->
  Profile ... -> Application Passwords, name the new password ..., click
  Add New Application Password. WordPress shows the password once; copy it
  immediately." Do the equivalent lookup before asking for any other
  secret - BotFather's one-time token print for Telegram, the developer
  token in the Google Ads API Center - rather than sending the user off to
  find the field themselves.
- **Always offer the paste-into-terminal alternative**, even when setup
  could technically run the write itself: give the exact command sequence
  and let the user run it in their own terminal.
  ```
  mkdir -p ~/.config/organic-os && read -s -p "App password: " P && printf 'WP_APP_PASSWORD=%s\n' "$P" > ~/.config/organic-os/<site-slug>.env && chmod 600 ~/.config/organic-os/<site-slug>.env
  ```
  Same pattern for `TELEGRAM_BOT_TOKEN` or any Google Ads secret - one
  `read -s` / `printf` / `chmod 600` line, one key.
- **Setup never needs to see the raw value.** It verifies the credential
  worked by probing - the Connector wizard's live check for connectors, a
  WordPress REST call (`wp-json/wp/v2/users/me`) for WordPress, a Telegram
  `getMe` call for the bot token - inside the Postflight scorecard, not by
  asking the user to paste the secret into the transcript.
- **Never echo a secret into the transcript**, regardless of which path
  the user picks.

## AI-visibility baseline (optional, ~5 minutes)

Offered once, after the interview's connectors and credentials steps and
before the Postflight scorecard - never required, always skippable. Full
setup only; quick-start does not collect the keywords/competitors this
step needs, so it is not offered there.

1. Ask, AskUserQuestion: "Want a one-time AI-visibility baseline - where
   you show up in AI answers today versus up to two competitors? About 5
   minutes, reuses the keywords and competitors already on file." Options:
   **Run it now** / **Skip - I'll run /organic-os:citations later**.
2. Skipped, or no keywords configured yet: note "AI-visibility baseline:
   skipped" (or "deferred - no keywords yet") in the closing summary table
   and stop here. Do not write a report or a signal.
3. Build the query set from `keywords.targets` (cap 8 - first 8 in file
   order if more are configured) and the competitor set from `competitors`
   (cap 2 - first 2 in file order).
4. For each query, check whichever AI answer surfaces are actually
   reachable from this session with WebSearch/WebFetch. This is a sample,
   not a census - record honestly which engines this session could
   actually reach, and never let the report imply broader coverage than
   that. Record per query: does the site's own brand/domain appear in the
   answer, does each tracked competitor appear, and who is actually cited
   (the source the answer points to, not just anything mentioned in
   passing).
5. Write `runs/<UTCdate>-ai-baseline/REPORT.md`:
   - A per-query table: query | brand mentioned? | competitor(s)
     mentioned | cited source(s).
   - Three summary numbers, each labeled with the sampling caveat inline:
     brand mention rate (queries where the brand appeared / queries
     checked), competitor mention rate (same, for the tracked
     competitors), share-of-voice ratio (brand mentions / (brand mentions
     + competitor mentions), or "n/a - no competitor mentions this run" if
     that denominator is zero).
   - One explicit line naming which engines/surfaces this session could
     actually reach - this method samples, it does not measure every
     engine.
6. Append one signal via `append_signal`: that the baseline now exists,
   its three headline numbers, and the falsifiability line - "re-run
   monthly via /organic-os:citations; if the mention rate has not moved
   within 90 days of shipped content work, that is evidence the content
   strategy hypothesis is wrong, not that the baseline was wrong."
7. **Degradation - no web access this session:** if WebSearch/WebFetch are
   unavailable, or every query fails to reach any engine, do not write a
   partial or fabricated report. Append a signal line "AI-visibility
   baseline: deferred - no web access in this session" instead, and tell
   the user to run `/organic-os:citations` later once a session with web
   access is available.

## Postflight scorecard (mandatory final step)

Setup does not claim success on its own - the scorecard does. Run every
check below that applies to what this session actually configured (skip
rows that are structurally not applicable, e.g. no WordPress row when
there is no WordPress connection at all), build a `checks` list of
`{"name", "status": "pass"|"degraded"|"fail", "detail", "fix"}`, call
`core.contracts.write_scorecard(brain_path, checks)`, and print the
resulting table to the user with any Fixes section intact.

Checks, in order:

1. **Brain scaffold** - pass if `site-profile.yaml`, `skillbook.md`, and
   `approvals/queue.md` exist at the brain path. Fix on fail: re-run
   `init_site_repo.py`.
2. **Git push** (brain mode: git only) - pass if `git log -1` in the brain
   path shows a commit, and, when a remote is configured, the push
   reached it. Detail: commit hash + branch. Fix: the exact `git remote
   add` / `git push -u origin main` command, or `gh repo create <name>
   --private --source=. --push` run from inside the brain path.
3. **Registry readable in runtime context** - pass if `core.registry.
   get_active()`, run from the runtime location, returns this site as
   active. If Step 0.5 flagged a setup/runtime mismatch and setup handed
   off a snippet instead of writing directly, this row is `degraded` with
   detail "handed off via snippet, not yet independently confirmed" and
   fix "run the Step 0.5 snippet, then `PYTHONPATH=... python3 -c
   \"from core import registry; print(registry.get_active())\"` on the
   runtime machine."
4. **WordPress REST** (only if WordPress connected) - pass if `curl -u
   '<user>:<app-password>' '<endpoint>/wp/v2/users/me?context=edit'`
   returns 200 JSON for the configured user. The detail column names the
   role detected from the response's `roles` field and what it cannot do,
   per the capability matrix in `plugin/docs/credentials/wordpress.md` -
   e.g. "role: editor - can write posts and SEO meta; cannot purge
   SEO-plugin caches or change plugin settings, those steps will be
   reported pending-human and end the proposal partially-applied". Fix on
   fail: recheck `plugin/docs/credentials/wordpress.md` step 2 (recreate
   the Application Password) or step 4 (bridge plugin not active).
5. **Approval channel test delivery** - for telegram: send a real test
   message ("organic-os setup test - reply not required") to the
   configured chat id and confirm the API call returned ok. State the
   prerequisite explicitly in the detail column either way: the first
   message to the bot has to come from the user first (open a chat, send
   anything) before `sendMessage` can deliver - Telegram rejects a
   bot-initiated first contact. Fix on fail: exactly that line. For
   in-session or pr-merge: pass automatically, detail "nothing to test -
   works by definition" / "confirmed on the first PR." For slack/email:
   the lightest live equivalent available in this session, same pass/fail
   logic as telegram.
6. **Each connector's live probe result** - one row per connector touched
   in the Connector wizard, carrying forward its recorded status
   (verified -> pass, declined -> degraded, unavailable -> fail) and
   context. Degraded/fail rows repeat the guided-connect instructions as
   the fix.
7. **Headless auth + model resolution** (runtime local or ci only; skip
   with detail "not applicable - runtime is manual/claude-scheduled"
   otherwise). For local runtime: have the user run `claude -p "ping"`
   through the wrapper (or a one-off `claude -p "ping" --permission-mode
   bypassPermissions`) and report the result.
   - Success: pass.
   - `Invalid API key - Please run /login`: fail, fix "run `claude
     setup-token`, add the result to the site env file as
     `CLAUDE_CODE_OAUTH_TOKEN`" (per `plugin/docs/routines.md`'s "Hard
     requirement: claude setup-token").
   - A 404 on the model: fail, fix "see the Model-404 recovery box in
     `plugin/docs/routines.md` - list models via curl, pin
     `ANTHROPIC_MODEL`/`ANTHROPIC_SMALL_FAST_MODEL`."
8. **PDF converter detection** - run
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "from core.report_render
   import find_pdf_converter; print(find_pdf_converter())"` in the runtime
   context (the probe order is canonical in
   `plugin/lib/core/report_render.py`). A converter found: pass, detail
   names it ("Monday report will arrive as PDF via <name>"). None found:
   degraded, detail "Monday report will arrive as styled HTML", fix "install
   pandoc or wkhtmltopdf if you want PDF - HTML delivery works without
   either." Never fail on this row; HTML is a full-fidelity fallback.
9. **One real scheduled run** (local runtime only) - kick the actual
   scheduler (`launchctl kickstart -k gui/$(id -u)/com.organic-os.daily`,
   or the systemd/cron equivalent already registered) and confirm via
   `git log -1 --format='%h %s'` in the brain repo that a fresh commit
   landed with today's date. Detail: the commit hash - this is the same
   proof `plugin/docs/routines.md`'s "Verify by commit hash" step already
   prescribes; pull that hash into the scorecard rather than re-describing
   it. Fix on fail: check `~/.config/organic-os/routine-daily.log` and
   `plugin/runtime/README.md`.

Close with one line: "<n> of <total> checks passed; <m> degraded, with the
fix for each above." Never say "setup complete" or "you're all set" unless
every non-skipped row is `pass` - a degraded or failed row is a next step
to hand to the user, not a caveat to bury.

## Rules

- Analysis-only mode is a valid outcome: a user with zero credentials still gets
  audits, briefs, and keyword work from public data.
- Never edit brain frontmatter directly. The contract CLI
  (`PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -m core ...`) is the only
  write path for status and approvals - setup itself never touches item
  status, and never teaches the user to hand-edit an item file either.
- Never write a secret into the brain repo, the registry, or the transcript. Env files only.
- Re-running setup is safe: the scaffolder never overwrites; the interview
  offers current values as defaults; update mode never touches memory.
- The registry (`~/.config/organic-os/sites.yaml`) is local operator state,
  not part of any brain repo - it is never committed to a site's git history.
- "Configured" and "verified working" are different claims. A connector is
  `verified` only after a live probe in the Connector wizard; a runtime is
  proven only after the postflight scorecard's headless-auth and (for
  local) scheduled-run checks pass. Never state either claim without the
  check behind it.
- Never run git through a device bridge (Step 0.5) - scaffold through the
  bridge, then let the user run git natively in the runtime environment.
