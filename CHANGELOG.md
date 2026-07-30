# Changelog

## [Unreleased]

### Added
- **core:** `approval.notify_pending(root, send, kinds, limit)` sends every
  un-notified proposed item exactly once and marks each as it goes. The
  check-send-mark sequence used to be prose in six skills, and prose gets
  skipped: items stayed marked un-notified over a working channel, so nothing
  ever reached the approver. An item is marked only after `send` returns
  without raising, so a failed send is retried on the next run instead of
  being silently lost, and one bad item does not stop the batch.

### Changed
- **skills:** the six skills that notify approvers (`hoo-daily`, `hoo-weekly`,
  `hoo-orchestrator`, `onsite-propose`, `hoo-import-audit`,
  `hoo-monthly-audit`) now call `core.approval.notify_pending` instead of
  describing the check-send-mark sequence in prose. Each keeps its own
  channel-selection logic; only the notify step changed.
- **docs:** `site-repo-contract.md` states that `approvals/queue.md` is
  derived and refreshed on every status change, so a queue that disagrees
  with the item files is a bug to report, not a state to work around.

### Fixed
- **core:** `set_status` now refreshes `approvals/queue.md` itself, so the
  derived queue can no longer go stale. Only the CLI rebuilt it before, so a
  skill calling `set_status` directly (publish, apply) left the queue frozen:
  it kept listing items as pending for days after they were approved and
  published, and an operator reading it concluded the loop had stopped. The
  refresh runs after the item is durably written and is best-effort - any
  failure inside it is swallowed, because a derived file must never roll back
  or block a real state transition. `reset_to_proposed` refreshes the same
  way.

## [0.6.0] - 2026-07-30

### Added
- **Early-stage mode: the loop is useful on a site that has impressions but
  no clicks yet.** A two-week-old site with 13 indexed pages and 61
  impressions across real commercial queries got the same report every
  morning for twelve days: quiet day, nothing sent. The data was fine. Every
  detector reading it assumed an established site - striking distance wants
  positions 4.0-15.0 above the site's median impressions, content decay wants
  50+ clicks in the older window, the anomaly check skips any metric whose
  trailing median is under 10, cannibalization wants two pages splitting a
  query - so a site with genuine, readable signal produced silence. Every
  site starts there, so every operator would have hit it, and silence from
  day 1 to day 90 is the worst experience this project can deliver.
- **core:** `stage.classify(rows)` reads a GSC page/query pull and returns
  the site's stage with the evidence sentence behind it: established at 100
  or more clicks in the window, growing at 10 or more, early below that. Zero
  impressions and zero clicks is early too but reads as "no search data yet",
  which is a different situation from having impressions nobody clicks.
- **core:** `stage.early_opportunities(rows, limit)` ranks what is worth
  acting on by POSITION rather than volume, because volume carries no signal
  yet. Four bands, each naming a lever instead of promising a result: top
  (page one, zero clicks - title and description), page-two (11-30, the
  closest thing to a breakthrough - on-page work), visible (31-70, being
  considered but not competitive - depth or authority, not a title tweak),
  distant (past 70 - a directional signal that the topic is targeted
  correctly, not a task).

### Changed
- **skills:** `hoo-daily` and `hoo-weekly` classify the stage from their own
  pull and record it as a `stage:` signal line. On an early site they report
  how many queries the site is visible for, the closest-to-breakthrough
  opportunities with their bands and levers, and the plain statement that
  zero clicks at those positions is normal and not a fault. The volume-gated
  detectors still skip, but now say they are dormant and name the threshold
  that activates each, so the silence is explained rather than mysterious.
  On growing and established sites nothing changes: every detector runs
  exactly as before.
- **skills:** the daily alert gains one case. On an early site the summary
  goes out weekly, because a daily "still climbing" message is noise, but a
  query the site was not visible for before always sends the day it appears -
  that is the real progress signal at this stage.

## [0.6.0] - 2026-07-30

### Added
- The daily and weekly routines now classify a site's stage from its own data
  and speak to it. Every detector this project ships assumes an established
  site: striking distance wants positions 4 to 15, decay wants 50 clicks in the
  older window, anomaly alerts skip a metric whose median is under 10. A new
  site clears none of those bars, so the loop reported "quiet day, nothing sent"
  while sitting on real data - indexed pages, live queries, climbing positions.
  Twelve days of that reads as a broken product, and every site starts there.
- On an early-stage site the routines now report which queries the site is
  visible for, the closest-to-breakthrough opportunities banded by position
  (top, page-two, visible, distant) with the lever that plausibly moves each,
  and an explicit line that zero clicks at those positions is expected rather
  than a fault. The dormant detectors are named along with the threshold that
  will wake each one, so silence is explained instead of mysterious.
- Early-stage sites get the channel summary weekly rather than daily, since a
  daily "still climbing" is noise, but always get an alert the moment a query
  appears that the site was not visible for before. On a new site that is the
  real progress signal.
- Growing and established sites are unaffected: all detectors behave exactly as
  before.

## [0.5.5] - 2026-07-30

### Fixed
- The queue rebuild crashed on a draft sidecar. content-engine writes
  `<brief>.draft.md` next to the brief it belongs to; the rebuild globbed
  every `.md` and died on the missing status key. Combined with the
  best-effort wrapper added in 0.5.4, that meant a brain containing any
  drafted content would silently stop refreshing its queue forever. Drafts
  are now skipped, and an item that parses but lacks required frontmatter is
  reported as malformed instead of raising.

## [0.5.4] - 2026-07-30

### Fixed
- The approvals queue could go stale and report work as pending long after it
  had been approved, drafted, or published. `approvals/queue.md` is a derived
  file, and only the CLI refreshed it, so any skill calling `set_status`
  directly left it frozen. It now refreshes on every status change, best-effort
  so a bookkeeping refresh can never block a real state transition. Found on a
  live instance whose queue had been wrong for six days while the loop kept
  working.
- Notifications could be skipped silently. Sending was described in skill prose
  as a three-step dance (check, send, mark), and prose steps get missed: on the
  same live instance every item showed as never notified while the channel was
  reachable the whole time. `approval.notify_pending` now sends and marks in one
  call, so an item is marked only after a successful send and a failed send is
  retried on the next run instead of being lost.

## [0.5.3] - 2026-07-24

### Fixed
- The Monday report's link renderer escapes URLs for the attribute context
  and allowlists link schemes. Before this, a double quote in a link URL
  could break out of the `href` attribute and inject its own, and a
  `javascript:` or `data:` URL became a clickable script link; both are
  neutralized. `http`, `https`, `mailto`, and relative URLs render as
  before; any other scheme renders its label as plain text with no anchor.
  The check normalizes the way a browser would (case, leading control
  characters) first. Found during the #18 review, closing #19.

## [0.5.2] - 2026-07-24

### Fixed
- The Monday report renders inline backtick code spans as `<code>` instead of
  literal backticks, so item ids read cleanly. Escaping runs before the span is
  wrapped, so report content stays injection-safe. Contributed by
  AshSgDe29071999 in #18, closing #7.
- `sanitize_bot_token` now rejects DEL and C1 control characters, which the
  earlier control-character guard missed. Contributed by MasRama in #16,
  closing #15. Two follow-ups are tracked in #19 and #20.
- `approval.find()` no longer crashes on a malformed sibling brief file; a bad
  file is skipped rather than aborting the scan.

## [0.5.1] - 2026-07-23

Approval UX and release hygiene. The Telegram approval message a human
actually taps becomes readable and gains buttons; diagnose learns to tell you
when your install is behind and why an update can look applied without being
applied; and a pre-release check plus troubleshooting docs close the gap that
let a tested feature sit on main unreleased.

### Added
- **Inline Approve/Reject buttons and readable Telegram approvals.** Landed
  on main in 43f266a and released here. `send_item` renders an approval
  request a person can read - bold title, plain framing, a reasoning excerpt -
  and attaches inline Approve / Reject buttons; `poll_decisions` records a
  button tap through `callback_query` and answers it so the button stops
  spinning and shows "Recorded". Telegram caps callback_data at 64 bytes, so a
  too-long item id falls back to the typed `approve <id>` grammar rather than
  shipping a button that cannot resolve. The redaction advisory now scans the
  rendered human-visible text. The typed and reply-context grammars are
  unchanged. Tests cover the button payload, the long-id fallback, tap
  parsing, and the cross-chat guard.
- **`/organic-os:diagnose` reports whether you are on the latest version.** It
  reads the running version from the plugin manifest and reads the latest
  public tag from GitHub (`gh`, or a plain GET of the public releases
  endpoint), and prints current, behind, or ahead. This is an inbound read of
  a version number already public on GitHub: not telemetry, nothing about you
  sent, and only when you run diagnose. The diagnostic itself is still never
  transmitted, and the read joins the same redaction scan. When you are behind
  it prints the upgrade command and the known-issue note about an update that
  reports success without changing the version. New `core.version` does the
  comparison with no guesswork (0.5.10 is newer than 0.5.9; a leading `v` and
  a pre-release suffix do not derail it; unknown never reads as up to date),
  stdlib-only with no I/O, 8 new tests.
- **`scripts/release-check.sh`.** A maintainer-run pre-release check that
  fails when plugin code sits past the last vN tag without a version bump -
  the exact state that made the Telegram feature invisible to the updater,
  since a tagged-but-unbumped commit carries the same version string. Docs-
  only or scripts-only work past a tag passes. Advisory and deliberately not
  in the PR CI gate, since a contributor branch is expected to sit past the
  last tag unbumped. Documented as the first required pre-release step in
  CONTRIBUTING.md.

### Changed
- **Update troubleshooting is documented and detectable.** A user reported an
  update that reported success, and even listed files to modify, while the
  running version never moved and every later update re-offered the same diff.
  The cause is host-side: Claude's plugin manager downloaded the new version
  into its cache without advancing the active-version pointer, so the plugin
  kept loading the old files. A plugin cannot fix this from inside its own
  update, so `plugin/docs/updating.md` gains a section with the accurate cause
  and the reinstall remedy for Claude Code CLI and Cowork; the README FAQ and
  SUPPORT.md point at it, and diagnose's update-currency note links it.
  `docs/INFORMATION-MAP.md` tracks the remedy.
- README inventory reconciled to 415 tests.

## [0.5.0] - 2026-07-23

Memory integrity and honest boundaries. Nothing here adds a data source
or a write path: six changes that make the existing loop harder to fool,
including harder for the loop to fool itself. The patterns come from
studying [gstack](https://github.com/garrytan/gstack) and asking which of
them this project was missing - durable decisions consulted before
re-deciding, learned knowledge that expires, a redaction boundary before
external sinks, and the reproduction-script posture applied to our own
claims. `docs/adr/0011-memory-integrity.md` records the decision and the
not-adopted list with reasons (telemetry even opt-in, a browser sidebar
with an ML classifier stack, a bundled cross-model reviewer, LOC-style
productivity claims).

### Added
- **Durable decision memory.** `core.decisions` writes one record per
  decision to `decisions/<UTCdate>-<slug>.md` (frontmatter plus the
  rationale as the body) and searches them back by case-insensitive token
  overlap, newest first, with no index file. `set_status` writes one on
  every rejection, so no skill has to remember to log it, and a second
  decision with the same title on the same day takes a numeric suffix
  rather than overwriting the first. onsite-propose, hoo-orchestrator and
  ce-produce search before `create_item`: a prior rejection leaves two
  paths, skip it and name it in the run report, or re-raise it carrying
  when it was rejected, why, and what changed since. Silently re-creating
  refused work is forbidden in all three.
- **Skillbook entries that go stale by evidence tier.** Entries carry
  `last-confirmed`, and `skillbook_stale` reports the ones past their
  tier's threshold (`STALE_DEFAULTS`: anecdotal 90 days, moderate 180,
  strong 365; overridable per tier via the additive `skillbook:
  {stale_days: {...}}` profile key, each tier falling back
  independently). At the threshold is fresh, one day past is stale. The
  weekly reflector presents each aged entry next to the week's evidence
  for a human to re-confirm or to approve a deprecation; it never
  auto-deprecates, and nothing deletes a lesson on a timer.
- **Advisory redaction at every outbound sink.** `core.redact.scan`
  returns `{tier, pattern, excerpt}` findings across three tiers
  (credential shapes high, personal email and phone runs medium, absolute
  local paths low), with excerpts masked in the module to the first four
  and last two characters, and `summarize` folds them into one line.
  Wired into the four places content leaves the brain: the Telegram item
  and document sends, the rendered report, the CSV export, and the task
  board's Notion mirror. Every sink swallows a scanner failure and
  delivers anyway, pinned by tests - a guard that becomes the reason a
  proposal never reaches its approver is a worse failure than the one it
  watches for.
- **`/organic-os:diagnose`.** Runtime, Python and plugin versions,
  PyYAML presence, brain schema, registry counts with only the active
  slug's URL, connector statuses with the context each was probed in, the
  last setup scorecard, the last routine outcome, and any recent error -
  collected locally, redacted, and printed. No channel, no upload, no
  issue filed; the operator decides what to paste. Credentials are
  reported present or absent and never read, and paths are relativised.
  SUPPORT.md points at it and states the project's actual feedback loop,
  since there is no telemetry and silence reads as nothing wrong.
- **`/organic-os:verify-outcome` and `core.outcomes`.** `parse_outcome`
  reads an outcome record into a stable seven-field shape (prose plus
  keys, absent keys parse as None, the filename is the item identity),
  and `compare` puts a claimed metric set next to a recomputed one:
  divergences beyond a relative tolerance, one-sided or non-numeric
  metrics reported as unverifiable rather than as disagreement, and
  agreement claimed only when at least one metric was actually compared.
  The skill runs it in the order that makes it worth something - item,
  URL and windows from the record, a fresh pull through the search-data
  and analytics slots, the delta, and only THEN the claimed numbers.
  Unreachable connectors mean the claim is unverified, never assumed
  correct, and a divergence is appended as a signal instead of being
  re-run away.
- **`plugin/docs/reproducing-results.md`.** How anyone rechecks a claim
  organic-os makes about a site, by command or by hand in Search Console
  with the windows the record names, and what reproduction does not
  prove: attribution to a single change stays unprovable, only
  consistency between claim and data is checkable.

### Changed
- **Attribution now requires naming the check that was run.** A cause may
  not be asserted without the claim, the comparison actually performed,
  and what would falsify it; where the comparison was not run, the record
  reads `cause: unknown`. Canonical in hoo-daily's anomaly step, binding
  hoo-weekly's striking-distance, cannibalization and content-decay
  detectors and onsite-measure. "Weekend seasonality" was the specific
  offender: a phrase that reads like an explanation while asserting a
  same-weekday comparison nobody ran. The reflector scores skillbook
  entries off exactly these records, so a confident story nobody checked
  teaches the loop the wrong lesson.
- THREAT-MODEL.md and `plugin/docs/connectors.md` state the redaction
  guard's limits where the guard is described: it reports rather than
  prevents, a high-tier finding means the value has already left the
  brain and the response is to rotate it, and a clean scan is the absence
  of a known pattern rather than the absence of a secret.
- `plugin/docs/site-repo-contract.md` documents the decision-record
  format, the additive `skillbook.stale_days` key, and the outcome-record
  fields with the key aliases each accepts. `docs/INFORMATION-MAP.md`
  gains rows for every fact those files now quote in more than one place.
- README inventory reconciled to 24 skills, 24 slash commands, 404
  passing tests, and the credits section names gstack for the four
  patterns taken from it.

### Fixed
- The redaction phone pattern allowed any whitespace inside a digit run,
  so a CSV value on one line joined the date on the next and reported a
  false positive on the export sink's first run. Whitespace is now a
  single literal space, pinned by a regression test.
- The Telegram bot-token pattern used `\b`, which never matches between
  two word characters and so missed the likeliest shape of all: a token
  inside a real API URL, where the digits are preceded by the letters of
  `bot`. Replaced with a lookbehind.

## [0.4.4] - 2026-07-23

A security release for the Telegram adapter, plus four follow-ups found
while reviewing the merged contribution.

### Fixed
- `UrllibHTTP.post`, `.get` and `.post_multipart` no longer leak the bot
  token when urllib raises `InvalidURL` (a trailing newline in the token)
  or `ValueError` (a scheme-less URL). Both escaped the HTTPError/URLError
  handlers carrying the full token-bearing URL. The handlers now catch
  broader, and `sanitize_bot_token()` validates the token at the boundary.
  Contributed by kevinnft in #13, closing #12.
- The sanitized message for a non-HTTP/URL failure now names the exception
  class (`telegram api error: InvalidURL`) instead of collapsing every case
  into one constant string. A malformed JSON response, a caller's
  `TypeError` and a bad URL used to be indistinguishable in a log. A class
  name cannot carry the token; the original message and the URL still stay
  out.

### Changed
- `test_urllibhttp_post_sanitizes_invalid_url` bound its client to a local
  named `http`, shadowing the `http` module inside the fake transport's
  closure. `http.client.InvalidURL` raised `AttributeError`, which the
  blanket handler folded into the same sanitized string, so the test passed
  without ever exercising the InvalidURL path. The `get` and
  `post_multipart` siblings do not rebind the name and were already sound.
- The token-rejection assertion `"SECRET" not in str(e) or "whitespace" in
  str(e).lower()` could never fail, because the right operand is always true
  for that message. Split into independent assertions covering the absent
  token and the named rejection reason.

### Added
- Tests pinning `sanitize_bot_token()` at all three call sites (`send_item`,
  `send_document`, `poll_decisions`). Removing the call from every site left
  the suite green, so nothing stopped a refactor from dropping it. Each site
  is now pinned on both halves of the contract: a recoverable token reaches
  the transport stripped, an unrecoverable one never reaches it at all.
- README inventory reconciled to 313 tests, up from 306.

## [0.4.3] - 2026-07-22

### Added
- Regression tests pinning token sanitization for `UrllibHTTP.post` and `.get`,
  plus the `post_multipart` URLError branch, so a future change cannot silently
  reintroduce a token leak through those paths. Contributed by kevinnft in #10,
  closing #6.

### Fixed
- `registry.register()` now rejects a URL that slugifies to an empty string
  before writing anything, instead of creating a site entry that
  `get_active()` can never return. Contributed by kevinnft in #11, closing #2.

### Changed
- README inventory reconciled to 301 tests and its verification date refreshed.
  Both merged branches bumped the same line from 292 independently.

## [0.4.2] - 2026-07-22

A documentation and audit-correctness release. The loop is unchanged and
tests stay at 292. It also reconciles the work that landed after the
v0.4.1 tag and was never released.

- **docs: a command reference for all 22 slash commands**, contributed by
  AK-Lmn in #9 against issue #8. First reference in the repo that lists
  every command in one place, with descriptions taken verbatim from each
  command's frontmatter.
- **docs: completed that reference.** Three gaps against #8 closed. Every
  row now shows the full invocation form (`/organic-os:<name>`), since the
  bare names it shipped with invoke nothing when typed. A third column
  records which skill each command invokes (`status` has none and carries
  a dash). Rows are grouped by product area - getting started, observe and
  report, act on the site, content - rather than alphabetically. The
  README and getting-started pointers stay, reworded so neither claims a
  completeness that could rot.
- **docs(readme): benefit-first rewrite.** Hero states what the plugin
  does for the reader before how it is built, install moves above the
  fold, and live CI and release badges replace hardcoded ones. Both
  manifests gained a keyword list and a marketplace category for
  discoverability.
- **fix(plugin): every userConfig field now declares a `title`.** All six
  fields (site URL, brand name, approval channel, Telegram bot token,
  WordPress application password, WordPress username) were missing the
  required key, so the enable-time configuration form could render them
  without labels.
- **fix(audit): the badge assertions work again.** Making them conditional
  on live badges being present turned both permanently inert once the
  README carried live badges. They now assert only when a hardcoded badge
  exists, so a stale one added later is caught and the live-badge state
  passes trivially.
- **feat(audit): check 9, command reference sync.** Fails if a command file
  is missing from `plugin/docs/commands.md`, if the table lists a command
  that does not exist, or if a description has drifted from its
  frontmatter. `docs/INFORMATION-MAP.md` records the frontmatter as
  canonical and the reference as its quoter, checked by audit-9 rather
  than by hand.

## [0.4.1] - 2026-07-19

A cleanup and community-health release. No new plugin capability; the loop
and its tests are unchanged at 292.

- **chore: removed internal build docs from the public repo.** `docs/specs`
  held internal build scaffolding (a design spec referencing a specific
  deployment), not audience content. Removed; the ADRs in `docs/adr/` stay,
  and the five ADRs that cited the spec keep the historical fact while
  dropping the now-dead link. Audit checks 2 and 4 lose their
  `--exclude-dir=specs/plans` flags.
- **chore(audit): generalized the personal-data check.** Check 1 hardcoded
  one contributor's employer, email fragment, phone fragment, and private
  metrics - inappropriate for a community repo and a mild self-leak. Replaced
  with a generic PII guard (personal-email providers plus a phone-shaped
  digit run) that names no one. Verified empirically.
- **feat: community-health files.** A Contributor Covenant 2.1 Code of
  Conduct (enforcement routed to a private security advisory or the
  maintainer's GitHub profile, never a personal email), three YAML issue
  forms (bug, feature, setup help) plus a config disabling blank issues,
  `.github/CODEOWNERS`, `SUPPORT.md`, and a DCO section in CONTRIBUTING plus
  a sign-off checkbox in the PR template - DCO, not a CLA.
- **docs: THREAT-MODEL.md.** A permissions table (capability, what it
  accesses, credential, where the credential lives), the blast radius of a
  mis-approval with its layered mitigations, what the plugin never does, and
  a release-integrity model that names Sigstore/SLSA build attestation as a
  roadmap item rather than implying it exists. README and SECURITY.md
  cross-link it; ROADMAP adds signed release provenance as an honest future
  item. SECURITY.md's reporting section now routes sensitive findings to a
  private advisory, matching the Code of Conduct and SUPPORT.

## [0.4.0] - 2026-07-19

This finalizes the alpha train - v0.4.0-alpha.1 through v0.4.0-alpha.5,
each itemized in its own entry below - closing the v0.4 phase with no
new capability beyond alpha.5.

**v0.4 in aggregate.** The phase shipped entirely across the five alpha
releases above: the Monday report arriving as a styled document (HTML,
and PDF where a local converter exists) through the configured approval
channel; marketer-grade onboarding (the install-time configuration form
plus the click-through chip interview, so a filled form is one click to
a configured site); anomaly alerts riding the daily observe's
actionable-only alert; keyword-portfolio tracking from GSC, honestly
labeled as average position rather than a scraped SERP rank; CSV export
of signals, keywords, and outcomes with no tier gate; citation-tracker
depth (per-answer position and sentiment with its evidence quote, plus a
BYO engine set via the additive `citations: {engines: [...]}` key); the
analytics and image-generation adapter slots formalized as contribution
contracts per ADR-0009; the gated image and alt-text fix workflow
(`get_media` / `update_media_alt` on the CMS adapter with a per-adapter
`media_alt` mode); and the editorial-policy section completed
(`core.contracts.editorial_policy` resolving the additive `editorial:`
block, with ce-qa enforcing the policy keys as return-to-writer hard
checks).

Two items carry forward: the Shopify adapter (deprioritized, demand-gated
on the first external request) and pipeline parallelism (gated on an
upstream sub-agent-dispatch dependency) - see ROADMAP.md.

## [0.4.0-alpha.5] - 2026-07-19

The last two open v0.4 queue items land: image findings become gated
fixes, and an organization's editorial conventions become hard QA
checks.

- **feat(onsite): gated image and alt-text workflow.** The audit
  already found the gaps; the loop now closes with proposals the apply
  path executes. The CMS adapter contract grows `get_media` (the
  images referenced in a post plus their alt text) and
  `update_media_alt`, with a `media_alt` capability key per adapter.
  WordPress (`media_alt: True`): get_media parses the rendered
  content's img tags - the src and the alt that actually renders - and
  fetches library alt_text for wp-image-stamped attachments only; an
  unstamped image carries media_id None, never a guess.
  update_media_alt writes alt_text to /wp/v2/media/<id>, dry-run
  aware. Git-static (`media_alt: "in-content"`): alt text lives in the
  content file, so the fix is a content rewrite -
  `<post-ref>::<src>` for a body image (markdown and img-tag forms),
  `<post-ref>::frontmatter` for ce-image's featured alt field -
  delivered on the normal branch/PR flow. The new image-fix action
  type: onsite-propose grounds each proposed alt in the surrounding
  content (accessibility text first, never keyword-stuffed) and routes
  missing in-content images through the ce-image brief; onsite-apply
  consults the media_alt mode first, records prior alts for rollback,
  verifies by reading the alt back, only ever PLACES an existing
  generated file (nothing in the apply path generates an image), and
  ends anything beyond the adapter's declared mode partially-applied
  with the human step named. The gate is unchanged.
- **feat(ce): the editorial policy section, complete.** Begun in
  v0.3.0-alpha.7 with `editorial.oversight_threshold`; the full
  section now ships. `core.contracts.editorial_policy(root)` resolves
  the additive `editorial:` profile section over canonical defaults -
  oversight_threshold 7, internal_links_min 0, external_links_max
  none, images_min 0, sourcing key-claims, require_reviewer_note
  false - with absent keys meaning defaults, unknown keys ignored, and
  an invalid value refusing with the key named. ce-qa's hard-check
  list becomes policy-driven: internal-link minimum, external-link
  cap, image minimum (image briefs attached before pass), sourcing
  mode (every-claim: all factual claims need sources; key-claims:
  statistics and comparative claims do), and the required human
  reviewer note - each a return to the writer on failure, alongside
  the unchanged capsule and readability checks. Free-text brand
  rulebook prose still applies on top: the policy keys are the
  enforceable floor, the prose is the voice. Setup's full-mode
  interview gains the Editorial rules chip question (defaults, set
  now, or later via update mode), update mode edits the section, the
  site-profile template documents the block, and updating.md's
  "planned on the roadmap" sentence now points at the shipped section
  (regulated-industry review stages stay v1.0 multi-approver work).
- Tests 263 -> 292. With this release the v0.4 queue is complete
  except the Shopify adapter (deprioritized, demand-gated) and
  pipeline parallelism (upstream-gated) - see ROADMAP.md.

## [0.4.0-alpha.4] - 2026-07-19

Citation tracking gains depth, and two capability slots get the
contribution contracts ADR-0009 promised.

- **feat(hoo): citation depth - sentiment and position, honestly
  sampled.** hoo-citation-tracker extends each query check beyond
  appears/absent. Position within the answer, recorded only when cited:
  a 4-value ordinal defined in the skill (lead-answer,
  supporting-mention, listed-among-others, footnote-link). Sentiment of
  the mention: positive / neutral / mixed-negative, judged from the
  answer text with the exact quoted phrase recorded as evidence - never
  a bare label without the quote. Both join the baseline comparison:
  movement reports now cover presence, position shifts by name ("cited,
  and moved from listed-among-others to lead answer"), and sentiment
  shifts with the new quote attached; the baseline REPORT.md format
  extends additively, and old baselines without the fields compare on
  presence only, stated in the movement section. The engine set becomes
  BYO via the additive `citations: {engines: [...]}` profile key
  (absence means the default set, canonical in the skill and mapped in
  docs/INFORMATION-MAP.md): each engine is checked only if reachable
  from the session, adding one is one more list entry - no tiers, no
  per-engine pricing - and the honesty rules stay restated in the
  skill: sampling not measurement, reachable engines always listed,
  sentiment labeled as a judgment call with the quote as the check.
- **docs: analytics and image-generation slots formalized.**
  CONTRIBUTING.md gains "Contributing an analytics adapter" (the slot's
  job is the daily/weekly read-side pulls; GA4 via the user's connector
  is adapter one; a Clarity or Matomo adapter is a skill-readable doc -
  query surface, connector/credential path, graceful degradation - with
  no lib contract yet, deliberately, because analytics is read-only
  through connectors) and "Contributing an image-generation adapter"
  (the slot's job is ce-image's featured-image step; Canva is adapter
  one; Gemini or local generators follow the same shape - how to
  invoke, what to return, an image file or the image-brief fallback,
  and the no-fake-success rule). hoo-daily and ce-image each name
  their slot and point at the CONTRIBUTING section. The ROADMAP moves
  both slot items to Landed early, phrased honestly: the contracts are
  formalized; no Clarity or Gemini adapter was built, first alternative
  adapters are community-welcome.

## [0.4.0-alpha.3] - 2026-07-19

Three more market-validated v0.4 items land: sharp metric breaks reach
the channel the operator already watches, tracked keywords earn an
honest position history, and the whole brain flattens to CSV on demand.

- **feat(hoo): anomaly alerts in the daily observe.** hoo-daily gains a
  step 2.7 anomaly check: each headline metric the run actually has
  (GSC clicks, impressions, GA4 sessions, ai_referrals) is compared to
  its median across the trailing 7 daily signals; a deviation past the
  threshold (default 40 percent, profile-configurable via the additive
  `alerts: {threshold_pct: 40}` key) becomes one P1 signal in
  falsifiable form - metric, today, median, direction, a likely-cause
  hypothesis, and the stated caveat that weekends and seasonality can
  trip the check. Flags ride the existing actionable-only daily alert,
  never a separate message. Noise floor: medians below 10 are skipped;
  fewer than 4 prior daily signals means a one-line skip note, no
  baseline, no alert. A new step 2.6 records the day's pulls as one
  structured metrics line so the trailing window is parseable.
- **feat(hoo): keyword-portfolio tracking, honestly labeled.**
  hoo-weekly gains a Keyword portfolio section: when GSC is reachable
  and `keywords/tracking.yaml` has entries, each tracked keyword's
  last-28-day GSC average position, clicks, and impressions append one
  row to `keywords/history.tsv` (tab-separated, append-only, additive -
  documented in site-repo-contract.md). Movement vs the previous
  recorded week lands in the weekly REPORT.md; the biggest mover gets
  one line in the Monday report's What moved. The honesty rule is
  stated in the skill and every output: GSC average position for
  queries matching the tracked term, not a scraped SERP snapshot;
  zero-impression positions are unknown, recorded as absent, never
  guessed. hoo-keyword-intel points at tracking.yaml management.
- **feat: CSV export for BI tools.** `core.export` (stdlib only):
  `export_signals` parses the daily's structured metric tokens into
  signals.csv (date, metric, value; unparseable lines skipped and
  counted, never guessed), `export_keywords` converts history.tsv
  verbatim, `export_outcomes` best-effort-parses outcome records
  (date, item, action, status, verified), and `export_all` writes the
  set into `runs/<UTCdate>-export/`. New hoo-export skill +
  `/organic-os:export` command present the files and offer document
  delivery where the channel carries files. Your data is files in your
  own repo, so there is no locked tier and no gate - commercial tools
  sell exactly this connector behind top tiers. 12 new tests (263).

## [0.4.0-alpha.2] - 2026-07-19

Marketer-grade onboarding: the install form + click-through interview;
zero-question quick start when the form is filled.

- **feat: install-time configuration form.** `plugin.json` gains a
  `userConfig` block - six optional fields (site_url, brand_name,
  approval_channel, telegram_bot_token, wp_app_password, wp_username)
  rendered as a native form when the plugin is enabled, on Claude Code
  and Cowork alike. Every field optional, so update installs never
  force re-entry; `sensitive: true` fields (the bot token, the
  Application Password) are stored in the OS keychain, never in a
  file, and reach a session only as `CLAUDE_PLUGIN_OPTION_*` env vars.
- **feat: setup v4 - form-first, chips for the rest.** A new Step 0.75
  reads the install form before anything else: anything present is a
  pre-answered question and is never re-asked, in any mode; an empty,
  unset, or unsubstituted value falls through to the normal interview,
  so setup works whether or not the form was rendered or filled.
  Secrets are referenced, never echoed - "found the WordPress
  Application Password from the install form" is the whole
  confirmation, and Credentials writes the site env file straight from
  the variable without printing it. Every remaining finite-choice
  question is AskUserQuestion chips (native multiple-choice in both
  clients) with the recommended option marked: quick-start vs full,
  approval channel, runtime, brain mode, WordPress, every connector
  decision. Quick start recalibrated: at most 3 questions, minus form
  answers - with a filled form it asks zero (URL + channel from the
  form, confirm chip only). Form filled = one click to a configured
  site; the start front door says so before handing off.
- **docs: onboarding walkthrough v2.** README's install walkthrough
  gains the enable-form step with a fourth SVG terminal frame;
  getting-started documents the form-first flow and where sensitive
  values live (keychain, env at runtime, never in chat or the brain);
  INFORMATION-MAP gains the userConfig field-list row with plugin.json
  canonical; connectors.md notes that credentials entered at the
  install form skip the paste-into-terminal step.

## [0.4.0-alpha.1] - 2026-07-19

The v0.4 train opens with the market-validated roadmap update and the
first item off it: the Monday report arrives as a document in the chat
channel that already carries approvals.

- **docs: roadmap - market-validated v0.4 additions + what we will not
  build.** Five owner-approved v0.4 items from a commercial-tool market
  review (report delivery to channels, anomaly alerts through approval
  channels, keyword-portfolio tracking from GSC, CSV export from the
  brain, citation-tracker depth), one v1.0 line (a read-only MCP surface
  over the brain repo), and a new "What we will not build" section
  naming six rejected commercial patterns with the reason each stays
  rejected - scraped SERP rank tracking, proprietary data moats, opaque
  0-100 scores, pooled benchmarks, export gating, unaudited visibility
  indexes.
- **feat(core): channel document delivery.** `core.telegram` gains
  `send_document` (Telegram sendDocument via stdlib-built
  multipart/form-data; the injectable transport gains `post_multipart`
  with the same sanitized errors as the existing methods - no token in
  any raised message). New `core.report_render` (stdlib only, TDD):
  `render_html` renders the Monday report's markdown subset (headings,
  bold, links, lists, tables, paragraphs) into one self-contained
  styled page - inline CSS, print-friendly, phone-readable, no external
  assets; `find_pdf_converter` probes PATH for pandoc, wkhtmltopdf,
  weasyprint, soffice in that order; `to_pdf` invokes the found
  converter and returns None on any failure, never raising to the
  caller. 16 new tests; suite at 251.
- **feat(hoo): the Monday report arrives as a document.**
  `hoo-monday-report` renders REPORT.md to HTML, produces PDF when the
  runtime has a converter, and sends the document with a two-line
  caption through the configured approval channel - telegram via
  `send_document`, in-session by saving the file and naming the path,
  slack/email where the connector supports attachments, pr-merge as
  caption plus path. Document delivery is a channel capability per
  ADR-0009, declared per adapter, never Telegram-bound; the markdown in
  `runs/` stays the canonical record. The approval-channels taxonomy
  gains its weekly-document row, the setup postflight scorecard gains
  converter detection (HTML fallback is degraded-not-failed), and the
  information map tracks the converter probe list with
  `report_render.py` as canonical.

## [0.3.0] - 2026-07-19

This finalizes the alpha train - v0.3.0-alpha.1 through v0.3.0-alpha.8,
each itemized in its own entry below - closing the v0.3 phase with no
further code change.

**v0.3 in aggregate.** The phase shipped entirely across the eight
alpha releases above: the CMS adapter contract plus the WordPress and
git-static adapters, internal-link graph analysis plus the gated
redirect and 404 workflow, the three observe-side items (digital-PR
mention signals, the entity-consistency audit, AI-referral traffic
segmentation), the content batch (the comparison-content brief type,
topic clustering for content architecture, editorial-oversight scoring
before publish), and the claude-seo audit import - "they audit, we
operate".

Open items move to v0.4: the analytics adapter slot, the
image-generation adapter slot, the gated image and alt-text fix
workflow, and the full editorial-policy section (see ROADMAP.md).

## [0.3.0-alpha.8] - 2026-07-19

They audit, we operate: the claude-seo import lands. A point-in-time
audit report becomes gated organic-os proposals instead of a re-derived
audit.

- **feat(hoo): external-audit import parser.** `hoo.audit_import`
  (stdlib only, TDD, 16 tests) parses a claude-seo style markdown
  audit report or action plan best-effort: severity-tier headings
  (emoji or plain), bold-lead bullets, and numbered findings lists,
  with evidence labels ([Measured]/[Inference]/[Unverified]) and
  effort tags captured when present. The format belongs to the
  external tool and may vary between versions, so parsing is
  defensive - whatever matches no item pattern is preserved in
  `unparsed` as a raw excerpt, never dropped. `to_proposals` ranks
  findings (critical > high > medium > low > unlabeled, ties by
  document order), derives contract-valid slugs, and shapes each into
  a `create_item` body carrying the original finding verbatim
  (quoted), its evidence label, the source attribution, and a
  dimension-mapping note from the new `DIMENSION_HINTS` map: an
  overlap names the onsite-audit dimension, an llms.txt finding gets
  the deliberate-skip note per `plugin/docs/evidence.md`, and no
  overlap is marked external-only.
- **feat: /organic-os:import-audit skill + command.** hoo-import-audit
  takes a file path or pasted report text, creates each proposal via
  `create_item` (born `proposed` on the normal gate, never
  auto-approved), presents a summary table (imported items with
  severity + dimension mapping, skipped items with reason, unparsed
  excerpt count), routes the approval notification through the
  configured channel like any propose run, and appends one signal
  recording the import (source date + counts). Policy, stated in the
  skill: the import trusts but attributes - findings keep their
  original evidence labels, and anything our own audit dimensions
  would dispute is flagged for the human, not silently rewritten.
  getting-started gains a using-organic-os-with-claude-seo section,
  the README claude-seo credit notes the import path, and
  INFORMATION-MAP gains the `DIMENSION_HINTS` row.

## [0.3.0-alpha.7] - 2026-07-19

The content batch: three v0.3 roadmap items land together - the pipeline
learns the content shape AI search cites most, the keyword layer learns
to propose content architecture instead of loose ideas, and every draft
now tells the approver how badly it needs human eyes.

- **feat(ce): comparison-content brief type.** Brief items gain an
  optional, additive `brief_type` frontmatter field: absence means
  explainer, `comparison` marks an X-vs-Y brief. Written only through
  `create_item` (new optional param - content-brief kind only, unknown
  values refuse), so the single write path stays the single write path.
  ce-produce layers comparison-specific stage guidance: ce-researcher
  fetch-verifies every third-party claim against the product's live
  public pages with a checked-on date (pricing and features change),
  ce-writer produces the X-vs-Y structure (the honest one-line
  difference in the capsule, a table with only verified rows, a fair
  "who should pick which"), and ce-qa adds two hard checks - no
  unverifiable competitor claims (drop the row, never guess) and no
  disparagement (factual differences only, no adjectives about
  competitors). hoo-weekly and hoo-orchestrator set the field when
  comparison-intent queries (vs / alternative / best-X-for) produced
  the brief. Rationale: X-vs-Y and listicle shapes are the most-cited
  content shapes in AI search
  (https://www.position.digital/blog/digital-pr-tactics/).
- **feat(hoo): topic clustering for content architecture.**
  hoo-keyword-intel gains the "Cluster the ideas" section, running when
  a keyword pull produced 30+ ideas (fewer skips silently): ideas group
  by intent + lexical family into named clusters, each with a hub (the
  highest-volume informational head term) and spokes; coverage is
  checked against the site's published pages via sitemap and GSC; each
  uncovered cluster becomes ONE architecture signal naming the hub,
  3-5 spokes, and the internal-linking rule (spokes link the hub, the
  hub links every spoke) - the build-time complement of the link-graph
  dimension's shallow striking-distance play. At most one cluster per
  run becomes a gated brief targeting the hub, brief_type per the hub's
  intent. Pattern credit: claude-seo's SERP clustering
  (https://github.com/AgriciDaniel/claude-seo), adapted to consume
  keyword-intel output.
- **feat(ce): editorial-oversight scoring before publish.** ce-editor's
  final pass produces an oversight block in the draft notes: a 0-10
  human-review-necessity score from named factors (claims density, YMYL
  adjacency, competitor mentions, legal/compliance surface, verbatim
  research survival), each factor one line with its contribution. At or
  above the profile's `editorial.oversight_threshold` (default 7, a new
  optional additive key - the first key of the future `editorial:`
  section) the notes recommend a human line-edit and name the top
  factor, and onsite-publish surfaces that recommendation prominently
  in the approval-channel message. Publishing stays gated by the same
  single approval either way: the score informs the human, it never
  adds a second gate. Rationale: scaled, unedited AI content correlates
  with deindexation
  (https://www.rankability.com/data/does-google-penalize-ai-content/).

Tests 215 -> 219 (the `brief_type` contract addition, TDD). Roadmap:
"Comparison-content brief type", "Topic clustering", and
"Editorial-oversight scoring" move to landed early; the full editorial-
policy item stays open. Audit and verify-gates green throughout.

## [0.3.0-alpha.6] - 2026-07-19

Three observe-side v0.3 roadmap items land together, all at the skill
layer - no lib changes, no new gates: the loop learns to see brand
mentions, entity drift across public properties, and the AI-referral
traffic its work earns.

- **feat(hoo): digital-PR mention signals.** hoo-weekly gains the
  Mention opportunities section, after the query detectors: a capped
  WebSearch sample of where the brand and its top 2 competitors appear
  across public surfaces (industry roundups, comparison posts,
  community threads) for the profile's top 3 topics - the
  ADR-0006-sanctioned mechanism, same as the citation tracker.
  Competitor-only surfaces become P3 signals in falsifiable form; at
  most one outreach proposal per run, gated as kind=strategy, and a
  human executes it - the skill never contacts anyone. Rationale
  carried in the report: brand mentions correlate roughly 3x more
  strongly with AI visibility than backlinks do (Ahrefs'
  75,000-brand study). Honest sampling caveat, and no web access
  degrades to a one-line skip note.
- **feat(hoo): entity-consistency audit.** hoo-monthly-audit gains the
  Entity consistency section: fetch the brand's public presences the
  profile names - own homepage/about plus the new optional
  `brand.properties:` list (additive, `schema_version` stays 1,
  documented in site-repo-contract.md; only profile-listed URLs, never
  guessed handles) - and compare core brand facts: name, one-line
  description, founding/location claims where stated, logo reference,
  sameAs cross-links. Each mismatch is a P2 signal per fact naming
  what differs, where, and which version the profile says is
  canonical. Own-site fixes route to gated proposals; third-party
  fixes are named human steps - the skill never writes off-site. The
  check joins entity-schema-engineer's method list.
- **feat(hoo): AI-referral traffic segmentation.** hoo-daily segments
  referral sessions from known AI surfaces when GA4 is reachable and
  records an `ai_referrals` line in the daily signal - count plus top
  landing pages. The surface list (chatgpt.com, perplexity.ai,
  gemini.google.com, copilot.microsoft.com, claude.ai) is maintained
  in hoo-daily's SKILL.md and reviewed quarterly; a new
  INFORMATION-MAP row pins it as canonical there. hoo-weekly reads the
  week-over-week trend into the health check and flags a sustained
  one-page rise to the citation tracker's next movement check; the
  Monday report includes AI referrals in What moved only when the
  signals carry them, never invented when absent.

Tests stay at 215 (skill-level changes only). Roadmap: "Digital-PR
mention signals", "Entity-consistency audit", and "AI-referral traffic
segmentation" move to landed. Audit and verify-gates green throughout.

## [0.3.0-alpha.5] - 2026-07-19

Two v0.3 roadmap items land together because they are one loop: the
internal-link graph finds the broken links and the link gaps, and the
gated redirect workflow is the apply path that closes them - findings
become gated proposals, never report lines.

- **feat(onsite): link graph builder.** `onsite.linkgraph` - stdlib
  only, injectable fetcher per wp.py's session pattern, observe-side
  (nothing here mutates). `crawl(base_url, fetch, max_pages=100,
  seed_urls=None)` is a capped same-host BFS that never follows an
  off-host link: ADR-0006 bans scraping third parties, and your own
  property is yours to crawl - the own-site rule is enforced in code.
  Sitemap-style `seed_urls` join the frontier so a page nothing links
  to still enters the graph (what makes orphan detection possible).
  Graph keys strip fragments and query strings; `out_raw` keeps the
  as-written links. `analyze(graph)` returns broken links with their
  source page, orphans, top-10 hubs by inbound, shallow pages (fewer
  than 2 inbound), and redirect chains for 3xx targets; a target the
  cap left uncrawled appears in no finding rather than being guessed
  at. The default `stdlib_fetch` never follows redirects - a 3xx is
  graph data, not a hop.
- **feat(hoo+onsite): internal-link dimension + gated redirect/404
  workflow.** onsite-audit gains the link-health dimension (step 4):
  one capped sitemap-seeded crawl per run; broken internal links are
  P2 signals feeding ONE gated fix proposal per run (rewrite the
  source link, or a redirect where the target moved), orphans are P3
  signals recommending links from the top hubs, and a shallow page
  that is also on the weekly striking-distance list is a P2 with its
  falsifiability line - the highest-leverage internal-link play.
  hoo-monthly-audit runs the dimension site-wide (ADR-0010).
  onsite-apply gains the redirect action type, decided by the
  adapter's new `capabilities()['redirects']` mode: wordpress declares
  `needs-plugin` (core WP has no redirect REST surface; the skill
  probes Rank Math / Redirection surfaces at run time, verifies by
  fetching the old URL for a 301, and otherwise ends the item
  partially-applied naming the SEO-plugin redirections screen);
  git-static declares `config-file` (an additive append to the
  profile's new `cms.redirect_file` - `_redirects`, `netlify.toml`,
  `vercel.json` - on the normal branch/PR flow). `native` is reserved.
  Link rewrites stay on the plain `update_post` path, gates unchanged.

18 new tests bring the suite to 215. Roadmap: "Internal-link graph
analysis" and "Gated redirect and 404 fix workflow" move to landed.
Audit and verify-gates green throughout.

## [0.3.0-alpha.4] - 2026-07-19

The page-essentials wave: a third-party audit of a live deployment
exposed detection gaps; the dimension list now covers them. Detection
belongs to the audit dimensions, remediation splits by artifact
locality - the responsibility map is now an ADR.

- **feat(onsite): page-essentials audit dimension.** onsite-audit gains
  a numbered per-page dimension (site-wide where noted): author entity
  (E-E-A-T - visible bio, sameAs, a named human reviewer note for
  AI-attributed content, author schema `description` + `sameAs`; a thin
  entity is a P2 signal + a gated site-level proposal), answer capsule
  above the first H2 (P2 + refresh proposal), zero in-content images in
  a 500+ word explainer (P3, image-brief path; the full image workflow
  stays roadmapped), the ~155-char meta description flag folded into
  the existing meta checks, square og:image under a summary_large_image
  card (P3 + proposal, image-brief fallback when no landscape asset
  exists), publisher schema shape (P3, entity-schema lane), and
  site-wide sitemap membership for any published post older than 1 hour
  (P2, with the cache-purge honesty note). Each check emits the
  standard falsifiable signal and keeps the evidence discipline:
  measured versus inferred, third-party outcomes never promised.
  hoo-monthly-audit runs the dimension site-wide. New
  `WPClient.update_user` writes the author profile description via
  `/wp/v2/users` (dry-run aware); adapters declare
  `author_profile_fields` in `capabilities()` (git-static: False), and
  steps beyond `capabilities()` end partially-applied.
- **feat(ce): capsule enforcement + readability + link judgment.** A
  published article shipped without the mandated answer capsule - the
  convention existed, the enforcement did not. ce-qa gains three hard
  checks: the capsule (40-60 words, standalone, above the first H2; a
  failing draft returns to the writer, never passes through),
  readability (sentence-length stats; more than 5 sentences over 30
  words or college-plus density returns the draft for splitting; target
  profile-driven via the additive `brand.readability_target` key,
  default grade 9-10), and dofollow links to commercial or competitor
  domains flagged for an explicit editorial decision in the draft
  notes. ce-editor re-confirms the capsule in the last read (belt and
  braces); ce-produce writes `capsule: verified` into the draft
  frontmatter as the handoff note, and onsite-publish refuses a draft
  whose notes lack it (in-session human override, recorded in the
  outcome record).
- **docs: ADR-0010 - audit-dimension responsibility map.** Detection
  belongs to head-of-organic's audit dimensions: the checklist is the
  product's eyes, and a check that does not exist cannot fire.
  Remediation splits by artifact locality - site-level through the
  gated onsite lane, in-article at content-engine QA. The dimension
  list is a living contract: every externally-caught miss becomes a
  dimension addition, logged in the ADR. Cross-references the v0.3
  entity-consistency item as the deeper successor and the claude-seo
  import as the depth complement.

2 new tests bring the suite to 197. No roadmap items move - this wave
hardens existing audit scope. Audit and verify-gates green throughout.

## [0.3.0-alpha.3] - 2026-07-19

Hardening from continued field testing: four gaps a real operating loop
surfaced, each fixed at the layer that owns it. No roadmap items move -
this is regression work inside the phase.

- **fix(core): illegal birth states cannot jam the pipeline.** An item
  file that enters the brain with a non-proposed status and an empty
  approvals list (written outside `create_item`) can neither be approved
  nor pass a lineage gate - the loop stalls until a manual repair.
  `rebuild_queue` now lints for the birth state and flags it as an
  `ILLEGAL-STATE` row naming the exact repair, and a new guarded CLI
  subcommand performs it: `python3 -m core reset-to-proposed <item-path>
  --actor NAME [--note TEXT]`. The guard: only an item with an EMPTY
  approvals list can be reset (the born-wrong case); anything with
  approval history refuses - those reached their status legally and move
  through status transitions. The repair persists as a `status_note` on
  the item, so the file carries its own audit trail. The skill sweep
  fixed the birth path itself: ce-produce's manual-brief instruction now
  registers a handed brief via `create_item` (born `proposed`) plus a
  recorded approval before drafting, and hoo-orchestrator plus
  onsite-propose state the create_item-only birth rule explicitly.
- **feat(core): affirmative synonyms on reply-context approvals.**
  Reply-context affirmatives now cover `approve`, `approved`, `yes`,
  `ok`, `go ahead`, `ship it`, `lgtm`, and thumbs-up (case-insensitive;
  the phrase must start the reply; trailing text becomes the note).
  Negatives are unchanged and deliberately narrow: deferrals such as
  "wait" or "hold" remain non-decisions, because deferring is not
  rejecting - protected by tests so a synonym wave can never widen it by
  accident.
- **feat: outcome notifications - the approver always hears what
  happened.** onsite-apply and onsite-publish end every run by composing
  ONE outcome summary and delivering it through the configured approval
  channel: applied-and-verified items, partially-applied items with the
  named human step, failed or rolled-back items with the reason, and
  published posts with their URL. Silent success was the field gap -
  approval without feedback breaks the loop. hoo-daily gains an
  actionable-only daily alert (P1 signals or the no-data nudge, one
  message, quiet days send nothing), and approval-channels.md now
  carries the canonical "What you will hear and when" table, mapped in
  docs/INFORMATION-MAP.md.
- **feat: applied-change re-verification.** An external bulk revert can
  undo an applied change minutes after verification, and waiting for the
  next audit to notice is too slow. After a successful rendered-head
  verify, the outcome record gains additive keys `reverify: {due: <UTC
  now+1h>, until: <UTC now+48h>}`; hoo-daily re-checks live values
  against applied values inside that window, and a mismatch is a P1
  signal ("applied change no longer live - external revert suspected;
  re-propose") in the daily alert. After `until`, the drift watch owns
  the long horizon (the baseline was already refreshed at apply). Keys
  documented in site-repo-contract.md; schema stays 1.

15 new tests bring the suite to 195. Audit and verify-gates green
throughout.

## [0.3.0-alpha.2] - 2026-07-19

Adapter two: git-static. Proposals arrive as pull requests; merging is
approving.

- **feat(onsite): git-static adapter.** `plugin/lib/onsite/gitstatic.py`
  implements the CmsAdapter contract for static sites built from a git
  repo (Astro, Next, Hugo, Jekyll class): content is markdown/MDX files
  with YAML frontmatter, and the adapter reads and writes them in a
  LOCAL CLONE (`cms: {type: git-static, repo_root: ..., content_dir:
  ..., fields: {...}}`). It never shells out to git - the skill layer
  runs the git/gh commands, which keeps the adapter testable and honest.
  Frontmatter conventions, overridable per site via the `fields`
  mapping: title, description, canonical, the draft flag, slug, and
  `jsonld` for a raw JSON-LD string the site's layout must render.
  `capabilities()` declares the gaps instead of papering over them:
  `schema_injection: "frontmatter-field"`, `rendered_head_verify: False`
  (static sites verify post-deploy), `needs_human: ["merge-pr",
  "deploy"]`, and `get_rendered_head` raises naming the gap rather than
  faking a verify. Snapshot stores the file's full text; rollback
  restores it byte-identical. Dry-run mirrors WPClient: zero writes,
  every intent in `dry_run_log`. `adapter_for` builds it from the
  additive `cms:` profile key. 35 new tmp-dir tests (no real git, no
  transport) bring the suite to 180.
- **feat: git-static skill path + pr-merge flow.** onsite-apply and
  onsite-publish gain the git-static branch: the gate check runs
  unchanged BEFORE any write, changes land on a new
  `organic-os/<item-id>` branch, `gh pr create` carries the proposal
  text as the body, and the item sits `partially-applied` (apply) or
  stays `drafted` (publish) until merge detection (`gh pr view --json
  state`) moves it to applied/published - no publish without a human
  merge. For pr-merge-channel sites the brain-repo proposal PR's merge
  is recorded as the approval via the contract CLI when detected, so
  the same gesture governs both layers. Verification states the honest
  limit: no rendered head at apply time; a best-effort live fetch
  against `cms.deploy_url` after the merge, recorded as exactly that.
  Docs in the same wave: site-repo-contract documents the git-static
  profile keys, approval-channels' pr-merge section covers the
  two-layer flow, getting-started gains the one-line git-static
  variant, and the information map's adapter row names both supported
  types.
- **docs + release.** CONTRIBUTING cites GitStaticClient as the second
  reference implementation - the smallest honest adapter, no transport
  at all; ROADMAP moves the git-based static-site adapter to landed
  early (the Shopify adapter stays deprioritized, as documented).

## [0.3.0-alpha.1] - 2026-07-19

The v0.3 phase opens with its structural priority: the CMS adapter
contract. Alpha signals the phase is open, not finished.

- **refactor(onsite): CmsAdapter contract; WordPress is adapter one.**
  `plugin/lib/onsite/cms.py` defines the cms capability slot's interface
  (ADR-0009): `CmsAdapter` with `get_post`, `update_post`, `create_post`,
  `update_seo_meta`, `get_rendered_head`, `snapshot`, `rollback`, plus
  the introspection pair `capabilities()` (what the adapter can do, and
  the `needs_human` actions it honestly cannot) and `adapter_name()`.
  The `adapter_for` factory builds the configured adapter from the
  additive `cms: {type: wordpress}` site-profile key, defaulting to
  wordpress when a wordpress endpoint exists and refusing unknown types
  by naming the supported list. `WPClient` implements the contract:
  `update_rankmath` and `get_head` stay as the WordPress-specific
  implementations, with the contract names delegating to them. The
  onsite skills now speak slot language ("the CMS adapter, WordPress
  today"), drift accepts any adapter, and 20 new contract tests bring
  the suite to 145.
- **docs: adapter contribution guide.** CONTRIBUTING's "Contributing a
  CMS adapter" section: implement `CmsAdapter`, the `capabilities()`
  honesty rule (`needs_human` steps end partially-applied, never faked
  success), the fake-transport test bar mirroring `tests/test_wp.py`,
  and gates stay in core (adapters never gate). The PR template gains
  the adapter checklist line; ROADMAP marks the contract landed early,
  with the git-static and Shopify adapters remaining open.
- Honesty note: this release is a pure refactor with zero behavior
  change, proven by the pre-existing test suite passing unmodified.

## [0.2.1] - 2026-07-19

Channel neutrality, made explicit and made checkable.

- **docs:** expiry re-confirmation is channel-neutral. The approval-expiry
  section now leads with the contract-layer fact - expiry is enforced at
  the gate, not in any channel, so every channel's approvals age
  identically - and documents the re-confirm path per channel: in-session
  re-ask, Telegram reply to the original message, slack/email reply where
  the adapter reads replies, pr-merge comment plus CLI re-approval
  (merging is a one-time event), and the universal `python3 -m core
  approve`. README's human-gates section states the rule in one line.
- **docs:** ADR-0009, capability slots over tool bindings. Every external
  dependency belongs to a named capability slot (analytics, search-data,
  image-generation, approval-channel, cms, indexing) with tools as
  swappable adapters behind it: contract and gate logic never references
  a specific tool, skills name the configured adapter from the site
  profile, and new tools (Microsoft Clarity for analytics, Gemini for
  image generation) are adapter additions, never rewrites. The roadmap
  names ADR-0009 as the governing principle for all adapter work and adds
  the analytics and image-generation slots to v0.3.
- **audit:** check 8, information integrity. `docs/INFORMATION-MAP.md`
  tables every load-bearing fact (plugin version, test and inventory
  counts, approval TTL, schema version, install commands, brain layout)
  with its canonical source, every quoting file, and who checks it; audit
  check 8 mechanically verifies that relative markdown links resolve,
  that the README version badge and marketplace.json match plugin.json,
  and that the README tests badge and inventory line match pytest and the
  filesystem. Its first run against the repo caught real drift: the
  README version badge still said 0.1.9 and both test-count quotes still
  said 90 (actual: 125) after two releases, the install SVG still showed
  v0.1.3 with 19 skills and 19 commands, and CONTRIBUTING still said 52
  tests. All fixed; CONTRIBUTING now states the expectation without a
  number, which removes that drift surface for good.

## [0.2.0] - 2026-07-19

Approval expiry - the last v0.2 item - and the release that closes the
v0.2 phase.

- **core:** approval expiry (ADR-0008). Approvals lapse after 30 days by
  default, configurable per site with the additive `approvals:
  {ttl_days: n}` key in `site-profile.yaml` (`schema_version` stays 1;
  below 1 refuses). Both gates - `require_approved` and
  `require_approval_lineage` - now verify the latest approved record is
  younger than the TTL, comparing UTC dates at gate time, so the check
  applies retroactively to existing records with no migration. Expiry
  means re-confirm, never silent rejection: the item keeps its status and
  the gate blocks with the exact `python3 -m core approve` command to
  run; that command (or a Telegram reply of `approve` to the original
  proposal message) appends a fresh approval entry through
  `record_decision`, refreshing the clock, while a replay within the TTL
  stays a silent no-op. Proven end to end by verify-gates probe 8
  (12 new tests).

**v0.2 in aggregate.** Most of the phase shipped ahead of this release in
v0.1.3 through v0.1.10; this entry closes it. The headline capabilities:
the setup verification block (postflight scorecard, runtime-location
awareness, connector wizard with live verification, one-secret-at-a-time
credentials), the observe-side detectors (striking-distance,
cannibalization, content decay, site drift watch), the audit-and-propose
interview with the AI-visibility baseline at setup, cost transparency plus
dry-run mode plus Bing/IndexNow submission, and the field-run hardening
wave (contracts CLI, reply-context Telegram approvals, the
partially-applied state, headless resilience) - now capped by approval
expiry, so a gate never acts on a stale yes.

## [0.1.10] - 2026-07-19

Approval UX and contract ergonomics - fixes from the first full pipeline
field run, which continues to set the priorities here.

- **core:** reply-context Telegram approvals. Replying to a proposal
  message with a bare decision word now works: approve/approved/yes/ok/
  thumbs-up approve, reject/rejected/no/thumbs-down reject, with the item
  id resolved from the replied-to text and any trailing words kept as the
  note. The strict `approve <item-id>` grammar is unchanged and takes
  precedence when both could apply; a bare word outside a reply, or a
  reply to a message without an item id, resolves nothing. Proposal
  messages state the reply format prominently (8 new tests).
- **core:** contracts CLI. `python3 -m core approve|reject|status
  <item-path>` is now the only supported write path for item status and
  approvals - it prints the resulting status line and refuses an illegal
  transition with a nonzero exit and the reason on stderr. Decisions
  accept `--note`; telegram reply reasons persist as notes too. Every
  skill that records decisions or status now invokes the CLI and carries
  the rule: never edit brain frontmatter directly (9 new tests).
- **core:** approval-record lint. `rebuild_queue` flags any approvals
  entry missing its `decision` field - the fingerprint of a hand-edit -
  as a `MALFORMED-APPROVAL` row in the queue.
- **core:** `partially-applied` is a first-class state (ADR-0007). When
  some changes in an approved proposal land and the rest hit a permission
  or capability wall, the honest state now exists: approved ->
  partially-applied (with a note naming exactly what a human must
  finish), then -> applied or -> failed, and nothing else touches it. The
  queue shows PARTIAL rows with the note inline; the outcome record lists
  done vs pending (6 new tests).
- **runtime:** headless resilience. `run-routine.sh` pins the model with
  `--model "${ANTHROPIC_MODEL:-sonnet}"` (the env override reaches
  sub-agents unreliably); `plugin/docs/routines.md` documents the known
  sub-agent dispatch limitation and its inline fallback, watching a live
  run by tailing the run report, `--output-format stream-json`, and
  recovering a skill from its on-disk body. The four long skills append a
  UTC-stamped progress marker to the run report at each stage boundary.
- **docs:** WordPress capability matrix. Action vs minimum role in
  `plugin/docs/credentials/wordpress.md`: public reads need no role,
  REST writes need Editor plus an Application Password, and
  Administrator-only steps (SEO-plugin cache purges, plugin settings) are
  never requested - they report pending-human and end the proposal
  partially-applied. The setup scorecard's WordPress row now names the
  detected role and what it cannot do.

## [0.1.9] - 2026-07-19

Cost, dry-run, and IndexNow (v0.2 wave 4) - see ROADMAP.md.

- **runtime:** cost transparency per routine run. `run-routine.sh` now
  runs `claude -p` with `--output-format json`, times the run, recovers
  the assistant text and any usage fields with python3 only (no jq), and
  appends one row per run - date, routine, duration seconds,
  tokens-or-unavailable - to a monthly ledger at
  `~/.config/organic-os/cost-ledger-YYYYMM.tsv`, plus a cost line in the
  routine log. Usage parsing is defensive across CLI versions and says
  "usage unavailable in this CLI version" rather than guessing. The
  Monday report closes its "What moved" section with a one-line cost
  summary when the ledger exists and never invents numbers when it does
  not; `plugin/docs/routines.md` documents what the ledger can and cannot
  capture per runtime (subscription runtimes: tokens counted, not billed
  per token; CI: tokens are money; runs that bypass the wrapper leave no
  row).
- **onsite:** dry-run mode for apply. `WPClient(dry_run=True)` records
  every mutating call (update_post, update_rankmath, create_post,
  rollback) in `dry_run_log` - method, post id, fields - and returns a
  realistic-shaped response marked `dry_run: True` without touching the
  session; reads behave normally (4 new tests). With
  `onsite: {dry_run: true}` in site-profile.yaml (additive, schema stays
  1), `onsite-apply` and `onsite-publish` run the full gated flow -
  `require_approved` still enforced before the dry-run write, so a dry
  run rehearses the real path - write nothing, leave the item's status
  untouched, and mark the outcome record dry-run with every write that
  would have happened. `scripts/verify-gates.sh` gains probe 7: dry-run
  does not relax the gate, and an approved dry-run apply makes zero
  session calls.
- **hoo:** IndexNow and Bing submission. `plugin/lib/hoo/indexnow.py`
  (5 new tests): `gen_key` (32-char hex), `key_file_content`, and
  `submit` - one stdlib POST to `api.indexnow.org` with
  `{host, key, keyLocation, urlList}` through an injectable transport,
  returning `{status, submitted}` and never raising on a non-200. With
  `indexnow: {enabled: true, key: ...}` in site-profile.yaml (additive),
  apply and publish submit each successfully verified changed URL and
  record the status in the outcome; publish only submits posts that
  actually went live. Setup's connector wizard offers enablement
  verify-not-record style: generate the key, place `<key>.txt` at the
  site root, verify by fetch, then enable. `plugin/docs/connectors.md`
  adds the capability row and an honest Bing Webmaster paragraph - portal
  verification is manual, IndexNow covers the submission path, no API
  integration claimed.

## [0.1.8] - 2026-07-19

Baseline and audit-first setup (v0.2 wave 3) - see ROADMAP.md.

- **setup:** AI-visibility baseline - a new optional step, offered in full
  setup after connectors/credentials and before the postflight scorecard
  (~5 minutes, always skippable). Samples up to 8 seed keywords and 2
  competitors against whatever AI answer surfaces this session can reach
  via WebSearch/WebFetch, records per query whether the brand and each
  competitor appear and who is actually cited, and writes
  `runs/<date>-ai-baseline/REPORT.md`: a per-query table plus three
  summary numbers (brand mention rate, competitor mention rate,
  share-of-voice ratio), each labeled with an explicit sampling caveat -
  this method samples reachable engines, it does not measure every engine.
  Appends one signal with the headline numbers and a 90-day falsifiability
  line (re-run monthly via `/organic-os:citations`; no movement in mention
  rate 90 days after shipped content work means the content strategy
  hypothesis is wrong, not the baseline). Degrades to "baseline deferred"
  with no web access rather than fabricating a report.
- **hoo-citation-tracker:** when a baseline report exists, later runs
  compare against it and report movement, not just this run's absolutes.
- **setup:** audit-and-propose is now the default first-run flow, for both
  quick-start and full setup. Setup asks for the site URL first, then
  audits before asking anything else - fetches the homepage and sitemap,
  detects WordPress/Yoast/RankMath from markup and sitemap shape, reads
  3-5 representative pages, and proposes brand voice descriptors, audience
  segments, 5-9 seed keywords, 3-5 content-SERP competitors (sites
  competing for the same queries, not necessarily business rivals - the
  proposal says so), and target geos, grounded in what was actually read.
  The proposal is presented as a table for approval: accept all, edit
  specific rows, or answer manually instead. Quick-start collapses to 3
  questions (URL, approval channel, confirm) and now seeds keywords,
  competitors, and voice from the audit instead of leaving them blank.
  Full setup keeps every question the audit genuinely cannot answer -
  operator knowledge, connectors, Google Ads, WordPress, approval channel,
  runtime, brain mode - unchanged downstream of the new proposal step.
  Degrades to the old blind-question defaults when the site cannot be
  fetched.
- **docs:** `plugin/docs/getting-started.md`'s setup walkthrough and
  README's zero-credential quickstart now describe the audit-first flow.

## [0.1.7] - 2026-07-19

Observe-side detectors (v0.2 wave 2) - see ROADMAP.md.

- **hoo:** cannibalization detector, added to `hoo-weekly` directly after
  the striking-distance section and fed by the same 28-day GSC query
  pull. Flags queries split across two or more landing pages with no
  stable majority (guideline: the second page carries 20% or more of the
  query's impressions), writes one P2 signal per case for the top 3 by
  total impressions - query, both pages, positions, impression split, and
  a falsifiability check - and calls out the linkage when a page also
  shows up in the striking-distance list, since cannibalization is often
  the actual blocker behind a stuck position. Opens at most one gated
  consolidation proposal per run (canonical, 301, or content merge),
  never applied automatically. Degrades to a one-line REPORT.md note when
  GSC is unreachable.
- **hoo:** content decay detection, also in `hoo-weekly`. Compares each
  page's last-28-days GSC clicks against the same page's 28-day window
  90 days back, flags a 30%+ decline above a 50-click noise floor on the
  older window, and writes P2 signals for the top 3 pages by absolute
  click loss with a likely-cause read on position-vs-CTR movement
  (position fell means a ranking problem; position held but CTR fell
  points at a SERP feature or title/meta staleness). At most one gated
  refresh brief per run, created as a `content-brief` item so it moves
  through the existing brief lifecycle into content-engine rather than
  being applied directly. Same GSC-unavailable degradation.
- **core + onsite:** site drift watch. `plugin/lib/onsite/drift.py`
  (`snapshot_pages`, `baseline_path`, `save_baseline`, `compare`, 8 new
  tests) snapshots title, RankMath title/description, canonical, slug,
  status, and JSON-LD presence per tracked page via the existing
  `wp.get_post()` getter, and diffs against a stored baseline at
  `drift/baseline.json` (atomic-written through
  `core.contracts._atomic_write`; additive, `schema_version` stays 1).
  `hoo-daily` gains a WP-only "Drift watch" section: establishes the
  baseline on first run against a capped tracked-page set (pages from
  `outcomes/`/`proposals/` plus the homepage), then on later runs writes
  one P1 signal per changed field before refreshing the baseline, so a
  given drift is reported exactly once. `onsite-apply`'s verify step
  refreshes the baseline for a page it just changed, so an approved
  change is never reported back as drift on the next daily run. Skips
  silently with no WordPress connector.

## [0.1.6] - 2026-07-19

Setup verification and runtime awareness (v0.2 wave 1, field-tested) -
see ROADMAP.md.

- **core:** `contracts.record_connector()` - the `connectors:` block in
  `site-profile.yaml` now stores `{status, context, checked}` per
  connector, never a bare string or boolean. `status` is `verified`
  (a live probe query succeeded, not just tool presence), `unavailable`,
  or `declined`; `context` records where the probe actually ran
  (`local-cli`, `cowork-cloud`, `ci`) so a connector reachable from the
  setup session is never recorded as available for a runtime that cannot
  reach it. Upgrades pre-wave-1 bare-string entries in place, one
  connector at a time, without touching siblings.
- **core:** `contracts.write_scorecard()` - writes a pass/degraded/fail
  table with the exact fix command per non-pass row to
  `runs/<date>-setup-scorecard/REPORT.md`.
- **setup:** rewritten as v3 - runtime-aware, verify-not-record. A new
  "where am I, where will routines run" step catches a setup/runtime
  environment mismatch (e.g. a cloud Cowork session onboarding a local
  runtime) before scaffolding anything, and bans running git through a
  device bridge. The old passive connector probe is replaced by a
  connector wizard: GA4/GSC (the heartbeat pair) then Notion/Slack/Canva,
  each probed and then live-verified (GSC list-sites, a GA4 7-day
  sessions pull, etc.) before ever recording `verified`, with a guided
  connect, a wait-and-reprobe option, or an honest `declined` on
  absence. Credentials move to a one-secret-at-a-time flow, precisely
  named and always offering a paste-into-terminal alternative. Setup now
  ends on a mandatory postflight scorecard - brain scaffold, git push,
  registry readability in runtime context, WordPress REST, approval-
  channel delivery, each connector's live result, headless auth + model
  resolution, and (local runtime) one real scheduled run proven by
  commit hash - and states "configured" and "verified working" as
  different claims.
- **start:** returning-user status now shows the latest postflight
  scorecard's summary line, read-only.
- **hoo:** `hoo-daily` escalates after 3 consecutive no-data days (GSC
  and GA4 both unreachable) with one send_item-style nudge through the
  configured approval channel, not an approval item - naming the exact
  connect fix. The nudge is marked inside that day's own signal file (no
  new state file) and is suppressed if one was already sent in the last
  7 days.
- **docs:** `plugin/docs/connectors.md` documents the new connector
  record shape and the no-data escalation behavior.

## [0.1.5] - 2026-07-19

- **onboarding:** user-facing docs now ship inside `plugin/docs/` so
  marketplace and synced installs (which contain only the plugin
  directory) actually have them - `$CLAUDE_PLUGIN_ROOT/../docs` never
  resolved for those installs.
- **runtime:** `plugin/runtime/` - a wrapper script (`run-routine.sh`)
  and three `launchd` plist templates (daily, weekly, monthly) for the
  local-schedule recipe.
- **docs:** `plugin/docs/routines.md` rewritten from a first real
  local-runtime install, covering five failure modes the original
  version did not warn about: the `claude setup-token` requirement for
  headless auth, passing a command's template body instead of a slash
  string (slash-command expansion is not reliable headless), model-404
  recovery when a CLI model alias resolves to a retired model, and what
  the `claude-scheduled` runtime cannot reach (personal GitHub auth,
  local env-file secrets, desktop-bridged connectors).
- **core:** `registry.path_warnings()` - the TCC brain-path guard is now
  enforced in code, not just documented: warns when a local runtime's
  brain path sits under a macOS TCC-protected folder (Documents, Desktop,
  Downloads) or inside a plugin-managed directory, and `/organic-os:setup`
  re-asks with a safe default when it fires.
- **refactor:** the bridge mu-plugin (`organic-os-bridge.php`) is a
  product asset, not demo infra - relocated to `plugin/wordpress/` so it
  ships with the plugin. The rest of `playground/` (compose file, Caddy
  snippet, php.ini tweak, deploy runbook) is demo-deployment infra, not a
  marketplace-user concern, and is removed from the package.
- **docs:** `plugin/docs/credentials/wordpress.md` gains the direct
  wp-admin URL for the Application Password screen, a one-line sandbox
  pointer (any local WordPress works), and an explicit Editor-not-
  Administrator note; `plugin/docs/approval-channels.md` explains why the
  first message to your Telegram bot has to happen before the first poll.
- **docs:** ROADMAP gains a new v0.2 sub-block, "Setup verification and
  runtime awareness," covering five gaps this wave's field testing
  surfaced (postflight scorecard, runtime-location awareness,
  audit-and-propose interview, connector wizard with live verification,
  one-secret-at-a-time credentials flow) - see ROADMAP.md.

## [0.1.4] - 2026-07-19

- **fix(ci):** all five CI runs since the 0.1.3 publish failed at
  collection, not on test results. Bare `pytest` on the runner lacks the
  repo root on `sys.path`, so the e2e test's `from tests.test_wp import
  FakeSession` import only ever resolved locally under `python -m
  pytest`. Fix: added `tests/__init__.py` and switched the CI step to
  `python -m pytest -q`.
- **hoo:** striking-distance detector in the weekly routine. `hoo-weekly`
  pulls 28 days of GSC queries, filters to positions 4.0-15.0 with
  impressions above the site's median, groups by page, and writes P2
  signals for the top 5 opportunities; a page with 2+ striking queries
  gets a gated `onpage-fix` proposal. Degrades to a one-line REPORT.md
  note with no GSC connector.
- **hoo:** the Monday report - a new `hoo-monday-report` skill and
  `/organic-os:monday-report` command that reads the brain's last 7 days
  and writes a five-section, under-400-word stakeholder summary (what
  moved, what shipped, what needs you, what we learned, next week). Every
  number traces to a brain file; a sparse week produces a shorter honest
  report, never a padded one.
- **security:** `scripts/verify-gates.sh` red-teams the approval gates
  against a throwaway brain repo - `require_approved`, `set_status`,
  `require_approval_lineage`, and `check_schema`, six probes, PASS/FAIL
  per probe. Referenced from `SECURITY.md` and README's Human gates
  section, and now runs in CI right after pytest.
- **docs:** ROADMAP gained three new items (site drift watch, gated
  image/alt-text fix workflow, topic clustering for content
  architecture) and moved the striking-distance detector, the Monday
  report, and the gate self-verification script into v0.2's "Landed
  early" note now that all three shipped here; the dry-run mode for
  `onsite-apply` that used to share a bullet with the self-verification
  script is now its own open item.

## [0.1.3] - 2026-07-18

- **core:** brain schema versioning - every scaffolded `site-profile.yaml`
  now carries `schema_version: 1`, and `core.contracts.check_schema()`
  classifies any brain repo as missing, pre-versioning (stamp needed),
  current, stale (migrate), or newer-than-plugin (update needed).
  `/organic-os:start`, `/organic-os:setup` update mode, and the three
  routine skills (`hoo-daily`, `hoo-weekly`, `hoo-orchestrator`) call it
  before doing any work and stop with the exact next action on an
  incompatible brain instead of guessing.
- **docs:** `docs/updating.md` - what `/plugin update organic-os` can and
  cannot touch (plugin code only; brain repos, `~/.config/organic-os/`,
  and WordPress are outside its reach by design), the semver compatibility
  policy, and the downgrade note.
- **docs:** `docs/connectors.md` - the probe-and-guide connector model
  (organic-os bundles no MCP servers and cannot trigger OAuth), why
  (stdio MCP does not run on Cowork), and a capability-to-connector table.
- **docs:** README FAQ gained two entries ("What happens when I update"
  and "Why does nothing prompt me to connect Google Analytics") linking
  the two new docs; version badge and verified inventory bumped to 0.1.3
  and 57 passing tests.

## [0.1.2] - 2026-07-18

- **onboarding:** `/organic-os:start` - the branded front door. Health-checks
  python3/PyYAML/the registry, then routes a new user into quick-start or
  full setup and a returning user into a compact status view (active site,
  pending approvals, last signal date) plus a menu; always closes by naming
  the three commands used most (daily, onsite-audit, weekly).
- **onboarding:** quick-start setup path - 3 questions (site URL, brand name
  + voice note, approval channel), everything else defaulted and stated in a
  closing summary table; a one-question-at-a-time interview style (default
  with every question, progress indicator, closing summary) now applies
  explicitly to every setup mode.
- **docs:** visual install walkthrough - three SVG terminal frames in
  `docs/images/` for marketplace add, plugin install, and the first
  `/organic-os:start` run, embedded in a new README "Install, step by step"
  section.
- **docs:** fully-namespaced command references confirmed across README and
  `docs/getting-started.md`, plus an explanatory line on why namespacing
  prevents collisions with other plugins' commands.

## [0.1.1] - 2026-07-18

- **core:** telegram offset persistence (`approvals/telegram-offset.json`)
  and tolerant decision processing, so replayed `getUpdates` replies apply
  once and a bad reply never blocks the rest of a batch; a `notified` flag
  on items so a routine never re-sends an approval notification it already
  sent.
- **core:** canonical plugin-root invocations across every skill - fixed
  `PYTHONPATH` and docs-link references so `lib/core` resolves the same way
  regardless of which skill or command triggers it.
- **core:** sites registry (`~/.config/organic-os/sites.yaml`), mode-aware
  `/organic-os:setup` (update / add / switch / status), and guided
  `/organic-os:reset` teardown that never deletes a brain repo or revokes a
  credential on the user's behalf.
- **docs:** README v2 - mermaid loop and architecture diagrams, a verified
  inventory line, three persona-based quickstarts, a respectful comparison
  table, and a 6-item FAQ.
- **docs:** CONTRIBUTING.md with an enforced data boundary (audit check 7)
  and a matching `.github/PULL_REQUEST_TEMPLATE.md`.
- **docs:** ROADMAP.md - v0.2 hardening, v0.3 CMS/channel adapters, v1.0
  multi-site and agency mode, plus two revisit triggers tracked separately.

## [0.1.0] - 2026-07-18

- **core:** file-contract layer for the per-site brain repo - items
  (briefs/proposals) with a status lifecycle, an in-code approval gate
  (`require_approved`, `require_approval_lineage`), an append-only
  skillbook with evidence tags, channel-neutral approval adapters
  (in-session, telegram, slack/email, pr-merge), and the site-repo
  scaffolder.
- **head-of-organic:** setup interview, orchestrator, daily/weekly/monthly
  routines, 8 specialist agents, tiered Google Ads keyword intelligence
  (Basic/Standard planner, Explorer GAQL, GSC mining, CSV import), AI
  citation tracking, competitor intelligence, the weekly reflector, and a
  Notion/local task board.
- **onsite-optimizer:** WordPress REST client over Application Passwords,
  a bundled RankMath REST bridge mu-plugin, on-page audit (credential-free),
  gated apply with snapshot/verify/rollback, gated publish for
  content-engine drafts, and day-7/28 outcome measurement.
- **content-engine:** the six-stage content pipeline (research, draft, brand
  compliance, SEO/authority, editorial QA, edit) with an optional image step,
  generalized to run off any site's `site-profile.yaml`, plus a featured-
  image skill with a Canva step that degrades to an image brief.
- **docs:** getting-started, credential guides (Google Ads, GSC/GA4,
  WordPress), approval channels, routines and runtimes, an honest AEO/GEO
  evidence ranking, and the full site-repo contract.
- **playground:** reference WordPress deployment (compose file, Caddy
  snippet, bridge mu-plugin, runbook) for the parallel session that stands
  up the live demo site.
