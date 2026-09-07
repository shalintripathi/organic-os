# Roadmap

Themes, not promises. Within each release, items are ordered by evidence of
user value, not by engineering convenience. The organizing insight behind
this order: commercial AI-visibility tools stop at monitoring and leave
execution on the user's desk
([source](https://discoveredlabs.com/blog/profound-vs-peec-vs-otterly-which-ai-visibility-platform-should-you-buy)).
organic-os is built as the inverse - a gated execution loop, not another
dashboard. All adapter work below is governed by ADR-0009
(`docs/adr/0009-capability-slots-not-tool-bindings.md`): every external
tool is a swappable adapter behind a named capability slot, never a
binding in contract logic. Issues and PRs against any item here are
welcome, including reprioritization - see `CONTRIBUTING.md`.

## v0.2 - First-week wins and loop hardening - COMPLETE

Closed by the v0.2.0 release (2026-07-19): the final item, approval
expiry, shipped there (ADR-0008) - approvals lapse after a per-site TTL,
default 30 days, and an expired item requires re-confirmation before the
next mutating stage runs. Everything else in this phase landed early
across v0.1.3 through v0.1.10, as itemized below.

**Landed early:** brain-repo schema versioning + migration entry point
shipped in v0.1.3 (`core.contracts.check_schema()`,
`schema_version: 1` in `site-profile.yaml`, the migration entry point in
`/organic-os:setup` update mode) rather than waiting for v0.2 - see
CHANGELOG.md. Also landed early in v0.1.4: the striking-distance detector
in the weekly routine (`hoo-weekly`), the Monday report (`hoo-monday-
report`), and the gate self-verification script (`scripts/verify-gates.sh`)
- see CHANGELOG.md. Also landed early in v0.1.5 (Wave A, from first-run
field testing): user docs shipping inside the plugin package, the runtime
wrapper plus launchd templates, and the rewritten local-runtime guide
(the `setup-token` requirement for headless auth, template-body invocation
instead of a slash string, model-404 recovery, and the TCC brain-path
guard now enforced in code, not just documented) - see CHANGELOG.md. Also
landed early in v0.1.6 (wave 1 of the block below, from the same first-run
field testing): the postflight scorecard (setup ends by testing what it
configured, not just writing config), runtime-location awareness (setup
distinguishes where it runs from where routines will run, and tags every
connector probe with the context it was tested in), the connector wizard
with live verification (GA4/GSC absence is a blocker to resolve with a
guided connect and a passed probe, not a status to record; `hoo-daily`
escalates a nudge after 3 consecutive no-data runs), and the
one-secret-at-a-time credentials flow - see CHANGELOG.md. Also landed
early in v0.1.7 (wave 2 of the block below): the three observe-side
detectors - the cannibalization detector and content decay detection in
the weekly routine, and the site drift watch riding the daily observe -
see CHANGELOG.md. Also landed early in v0.1.8 (wave 3): the audit-and-
propose interview and the AI-visibility baseline at setup - see
CHANGELOG.md. This finishes the "Setup verification and runtime
awareness" sub-block in full - every item first identified from
first-run field testing has now shipped ahead of the formal v0.2 release.
Also landed early in v0.1.9 (wave 4): cost transparency per routine run
(the monthly cost ledger written by the runtime wrapper, surfaced in the
Monday report), dry-run mode for `onsite-apply` (the full gated flow
against a client that records intended writes instead of performing
them, proven by verify-gates probe 7), and Bing Webmaster + IndexNow
submission (key generation, root-file verification, and per-ship URL
submission with the status recorded in the outcome) - see CHANGELOG.md.

## v0.3 - Execution breadth - COMPLETE

Closed by the v0.3.0 release (2026-07-19), which finalizes the alpha
train rather than shipping new capability: the phase landed the CMS
adapter contract plus the WordPress and git-static adapters, link
health plus the gated redirect and 404 workflow, mention opportunities
plus entity consistency plus AI-referral segmentation, comparison
briefs plus topic clustering plus editorial-oversight scoring, and the
claude-seo audit import. Everything landed early across
v0.3.0-alpha.1 through v0.3.0-alpha.8, as itemized below; the open
items move to v0.4.

**Landed early:** the CMS adapter contract, the structural priority for
this release, shipped in v0.3.0-alpha.1: `plugin/lib/onsite/cms.py`
defines `CmsAdapter` (the cms slot's documented interface) plus the
`adapter_for` factory reading the additive `cms: {type: wordpress}`
site-profile key, and `WPClient` is adapter one (`update_rankmath` stays
as its WordPress-specific alias for `update_seo_meta`). Adding a CMS is
now a new adapter file plus a profile entry, not a fork - see
CHANGELOG.md and CONTRIBUTING.md's "Contributing a CMS adapter" section.
The onsite skills were normalized to ADR-0009 slot language ("the CMS
adapter, WordPress today") in the same wave. Also landed early, in
v0.3.0-alpha.2: the git-based static-site adapter -
`onsite.gitstatic.GitStaticClient` targets Astro/Next/Hugo/Jekyll-class
sites, writes markdown/MDX frontmatter in a local clone of the site
repo, and delivers every approved change as a pull request, so the human
merge is the final act - the natural pair for the pr-merge approval
channel, serving the early-adopter persona directly. See CHANGELOG.md.
The Shopify adapter (deprioritized) remains open. Also landed early, in
v0.3.0-alpha.5: internal-link graph analysis (`onsite.linkgraph` - a
capped, sitemap-seeded, own-site-only crawl feeding onsite-audit's
link-health dimension: broken links, orphans, hubs, shallow
striking-distance pages, redirect chains) and the gated redirect and
404 fix workflow (the redirect action type in onsite-apply, decided by
the adapter's `capabilities()['redirects']` mode - wordpress
`needs-plugin`, git-static `config-file` via the additive
`cms.redirect_file` key - with anything beyond the declared mode ending
partially-applied and the human step named). See CHANGELOG.md. Also
landed early, in v0.3.0-alpha.6: the three observe-side items -
digital-PR mention signals (hoo-weekly samples where the brand and its
competitors are mentioned across public surfaces; competitor-only
surfaces become P3 signals, at most one gated outreach proposal per
run, and a human executes it - brand mentions correlate roughly 3x
more strongly with AI visibility than backlinks do, per Ahrefs'
75,000-brand study,
[source](https://ahrefs.com/blog/ai-brand-visibility-correlations/)),
the entity-consistency audit (hoo-monthly-audit compares core brand
facts across the site and the profile-listed properties in the
additive `brand.properties:` key; consistency across authoritative
sources drives inclusion in AI answers,
[source](https://www.useomnia.com/blog/how-to-improve-brand-visibility-chatgpt)),
and AI-referral traffic segmentation in the daily observe
([source](https://www.semrush.com/blog/the-operational-gap-ai-seo-study/)).
See CHANGELOG.md. Also landed early, in v0.3.0-alpha.7: the content
batch - the comparison-content brief type (an additive `brief_type`
frontmatter field on brief items; ce-produce layers fetch-verified
competitor research, the X-vs-Y draft structure, and two QA hard
checks - X-vs-Y and listicle shapes are the most-cited content shapes
in AI search,
[source](https://www.position.digital/blog/digital-pr-tactics/)),
topic clustering for content architecture (hoo-keyword-intel groups
30+ ideas into hub-and-spoke clusters, writes one architecture signal
per uncovered cluster, and gates at most one hub brief per run;
pattern credit
[claude-seo](https://github.com/AgriciDaniel/claude-seo)'s SERP
clustering, ours consumes keyword-intel output), and
editorial-oversight scoring before publish (ce-editor scores
human-review necessity 0-10 from named factors; onsite-publish
surfaces the recommendation in the approval message without adding a
second gate - scaled, unedited AI content correlates with
deindexation,
[source](https://www.rankability.com/data/does-google-penalize-ai-content/)).
The `editorial:` profile section has begun with its first key,
`editorial.oversight_threshold`; the full editorial-policy item (moved
to v0.4) stays open. See CHANGELOG.md. Also landed early, in
v0.3.0-alpha.8: the claude-seo audit import - "they audit, we
operate". `/organic-os:import-audit` parses a claude-seo report or
action plan defensively (`hoo.audit_import`, stdlib only; the format
is theirs and may vary between versions, so whatever cannot be parsed
is preserved as a raw excerpt, never dropped), keeps every finding's
original evidence label and text verbatim, maps findings onto our
onsite-audit dimensions where they overlap and marks the rest
external-only (llms.txt findings carry the deliberate-skip note per
`plugin/docs/evidence.md`), and creates at most five ranked proposals
via `create_item` - born `proposed` on the normal gate, never
auto-approved. See CHANGELOG.md. Open items move to v0.4, itemized
there: the analytics adapter slot, the image-generation adapter slot,
the gated image and alt-text fix workflow, and the full
editorial-policy section; the Shopify adapter stays deprioritized
(below, under "Deprioritized, with reasons") and pipeline parallelism
stays upstream-gated.

## v0.4 - Adapter breadth and editorial depth - COMPLETE

Closed by the v0.4.0 release (2026-07-19), which finalizes the alpha
train rather than shipping new capability: the phase landed the Monday
report as a channel-delivered document, marketer-grade onboarding (the
install form plus the click-through chip interview), anomaly alerts,
keyword-portfolio tracking from GSC, CSV export, citation-tracker depth
with a BYO engine set, the formalized analytics and image-generation
adapter slots, the gated image and alt-text fix workflow, and the
complete editorial-policy section. Everything landed early across
v0.4.0-alpha.1 through v0.4.0-alpha.5, as itemized per bullet below. Two
items carry forward: the Shopify adapter (deprioritized below, still
demand-gated on the first external request) and pipeline parallelism
(gated on an upstream sub-agent-dispatch dependency, not on this
project).

The five report-and-tracking items below were added after a market review
of commercial AI-visibility and SEO tooling (2026-07, owner-approved):
each one is a capability users demonstrably pay for elsewhere, rebuilt on
this project's terms - evidence-tiered, BYO-credential, no scraping.

- **Analytics adapter slot.** GA4 is the first adapter; Microsoft Clarity
  and Matomo are welcome contributions. **Landed early** in
  v0.4.0-alpha.4 as a formalized contribution contract:
  CONTRIBUTING.md's "Contributing an analytics adapter" section defines
  the slot's job (the daily/weekly read-side pulls) and the doc-shaped
  adapter contract - analytics is read-only through connectors, so
  there is deliberately no lib interface yet - and hoo-daily names the
  slot per ADR-0009. We did not build a Clarity or Matomo adapter; the
  first alternative adapters are community-welcome against that
  contract.
- **Image-generation adapter slot.** Canva is the first adapter; Gemini
  and local generators fit the same slot. **Landed early** in
  v0.4.0-alpha.4 the same way: CONTRIBUTING.md's "Contributing an
  image-generation adapter" section defines the slot's job (ce-image's
  featured-image step), the invoke-and-return shape (an image file or
  the image-brief fallback), and the no-fake-success rule, and ce-image
  names the slot per ADR-0009. We did not build a Gemini or
  local-generator adapter; contributions are welcome against that
  contract.
- **Gated image and alt-text fix workflow.** The audit already finds the
  gaps; close the loop with proposals the apply path executes. **Landed
  early** in v0.4.0-alpha.5: the CMS adapter contract grows `get_media`
  and `update_media_alt` with a per-adapter `media_alt` capability mode
  (WordPress writes the media library's alt_text; git-static rewrites
  the alt inside the content file, delivered as a PR), and the image-fix
  action type runs the normal gate - proposed alt text grounded in the
  surrounding content and never keyword-stuffed, missing images routed
  through the ce-image brief with the apply path only ever placing an
  existing file, and anything beyond the adapter's declared mode ending
  partially-applied with the human step named. See CHANGELOG.md.
- **Editorial policy in the site profile.** An additive `editorial:`
  section turning an organization's written conventions (minimum internal
  links, external-link limits, image requirements, sourcing rules) into
  hard QA checks, the way the answer capsule and readability target are
  enforced today. Free-text rulebook prose keeps working; this makes it
  enforceable. Begun in v0.3.0-alpha.7: `editorial.oversight_threshold`
  was the section's first key. **Landed early** in v0.4.0-alpha.5, the
  section complete: `core.contracts.editorial_policy` resolves the
  section over canonical defaults, and ce-qa enforces internal-link
  minimum, external-link cap, image minimum, sourcing mode, and a
  required reviewer note as return-to-writer hard checks - the policy
  keys are the enforceable floor, the rulebook prose stays the voice.
  See CHANGELOG.md. Regulated-industry review stages (for example a
  compliance reviewer before publish) belong to v1.0's multi-approver
  work, as planned.
- **Pipeline parallelism.** Per-page audit fan-out and research prefetch
  when sub-agent dispatch is reliable in headless runs (upstream
  dependency).
- **Report delivery to channels.** The Monday report arrives as a styled
  HTML document, and as PDF when a local converter is present, through
  the configured approval channel. Source: agencies pay 20 to 69 dollars
  per client per month for report automation alone, and PDF plus link in
  one chat message is the documented winning delivery pattern. **Landed
  early** in v0.4.0-alpha.1: `core.report_render` (HTML + best-effort
  PDF), `core.telegram.send_document`, and the hoo-monday-report
  delivery step, channel-neutral per ADR-0009 - see CHANGELOG.md.
- **Anomaly alerts through approval channels.** Sharp metric breaks
  surface as one alert on the channel the operator already watches.
  Source: alerting is the retention feature of every commercial monitor;
  ours rides the existing channel taxonomy instead of adding a dashboard.
  **Landed early** in v0.4.0-alpha.3: hoo-daily's anomaly check compares
  each headline metric to its trailing 7-day median (default 40 percent
  threshold, additive `alerts: {threshold_pct: 40}` profile key, noise
  floor and baseline minimum stated in the skill) and the flags join the
  existing actionable-only daily alert - see CHANGELOG.md.
- **Keyword-portfolio tracking from GSC.** A tracked keyword set with
  position over time, honestly labeled: GSC average position, not scraped
  SERP rank. Source: rank tracking is the most-requested gap left by
  ADR-0006; GSC is the licensed data that closes most of it. **Landed
  early** in v0.4.0-alpha.3: hoo-weekly's Keyword portfolio section
  appends per-keyword GSC history to `keywords/history.tsv`, reports
  weekly movement, and feeds the biggest mover to the Monday report,
  with the honesty rule stated in every output - see CHANGELOG.md.
- **CSV export from the brain for BI tools.** Signals, outcomes, and
  tracking flatten to CSV on demand. Source: commercial tools gate export
  behind top tiers; our data is the user's own files, so export is a
  right, not an upsell. **Landed early** in v0.4.0-alpha.3:
  `core.export.export_all` writes signals.csv, keywords.csv, and
  outcomes.csv into a dated run dir; the hoo-export skill and
  `/organic-os:export` command deliver them, no tier gate - see
  CHANGELOG.md.
- **Citation-tracker depth.** More engines via BYO credentials, plus
  sentiment and position within answers, not just cited-or-not. Source:
  per-answer position and sentiment are the paid tiers of every
  AI-visibility product; BYO credentials keep it inside ADR-0006.
  **Landed early** in v0.4.0-alpha.4: hoo-citation-tracker records a
  4-value position ordinal when cited and a sentiment label with its
  evidence quote when mentioned, both joining the baseline movement
  report (old baselines compare on presence only, stated), and the
  engine set is profile-configurable via the additive
  `citations: {engines: [...]}` key - each engine checked only if
  reachable, no tiers, no per-engine pricing - see CHANGELOG.md.

The Shopify adapter does not move here: it stays parked under
"Deprioritized, with reasons" below, still demand-gated on the first
external request.

## v0.5 - Memory integrity and honest boundaries - COMPLETE

Closed by the v0.5.0 release (2026-07-23). The phase came out of studying
[gstack](https://github.com/garrytan/gstack) and asking which of its
patterns this project was missing: memory that is consulted before
re-deciding, knowledge that expires, a boundary before content leaves,
and claims a stranger can recompute. ADR-0011 records the decision, the
four rules, and the not-adopted list with its reasons (telemetry even
opt-in, a browser sidebar with an ML classifier stack, a bundled
cross-model reviewer, LOC-style productivity claims). Nothing here adds a
data source or a write path; all six items make the existing loop harder
to fool, including harder for the loop to fool itself.

- **Durable decision memory.** Every rejection writes a record to
  `decisions/` (`core.decisions`, written by `set_status` so no skill has
  to remember), and onsite-propose, hoo-orchestrator, and ce-produce
  search those records before creating an item. A refused proposal is
  either skipped and named in the run report, or re-raised carrying when
  it was rejected, why, and what changed since. See CHANGELOG.md.
- **Skillbook entries that expire by evidence tier.** `last-confirmed`
  plus per-tier thresholds (anecdotal 90 days, moderate 180, strong 365,
  overridable per tier in the site profile) feed a stale review in the
  weekly reflection. Weak evidence goes stale fast, strong evidence keeps
  for a year, and a human re-confirms or retires. Surfaced, never
  enforced: nothing deletes a lesson on a timer.
- **Advisory redaction at every outbound sink.** `core.redact` scans
  content before it leaves through an approval channel, a Notion mirror,
  a report, or a CSV export, and reports masked findings. It never
  blocks, rewrites, or raises, and the limits are stated where the scan
  runs: a high-tier finding means the value already left, so the response
  is to rotate it, and a clean scan is the absence of a match rather than
  a guarantee.
- **`/organic-os:diagnose`, a report that never transmits.** The
  install-shaped facts a bug report needs (runtime, versions, brain
  schema, connector status with the context each probe ran in, last
  routine outcome), collected locally, redacted, and printed. The
  operator decides what to paste. This is the answer to "how do installs
  fail" that telemetry would otherwise have been the answer to.
- **Attribution that names the check that was run.** A cause claim needs
  the claim, the comparison actually run, and what would falsify it;
  where the comparison was not run, the record reads `cause: unknown` and
  keeps the number. Canonical in hoo-daily's anomaly section and carried
  through the weekly, the measure step, and every outcome record.
- **`/organic-os:verify-outcome`, independent reproduction.**
  `core.outcomes` parses a record and compares a claimed metric set
  against a recomputed one; the skill pulls the raw windows and computes
  the delta BEFORE reading what was claimed. Divergence is recorded as a
  signal, unreachable connectors mean unverified rather than confirmed,
  and `plugin/docs/reproducing-results.md` documents the same check by
  hand in Search Console so the claim survives without the tool. See
  CHANGELOG.md.

## v0.7 - The loop reads richer data (OpenSEO tier) - COMPLETE

Decision recorded in [ADR-0012](docs/adr/0012-openseo-optional-data-tier.md):
[OpenSEO](https://github.com/every-app/open-seo) (MIT, DataForSEO-backed,
MCP-exposed) became an optional probed data tier - a second adapter in the
existing search-data capability slot (ADR-0009), never a new slot. The user
runs it with their own DataForSEO key; organic-os holds no new credential
and requires nothing. All additive, gates untouched:

- **Connector probe.** The adapter's MCP tools are detected in-session the
  way GA4/GSC MCPs are detected; `/organic-os:diagnose` reports
  present/absent with the known tools actually seen, and setup's connector
  wizard carries it as one optional entry, verified by a live call.
- **`hoo-keyword-intel`: a tier that does not need Google Ads.** Volume,
  difficulty, and SERP data when the probe succeeds; the existing
  `none | basic | explorer` behavior unchanged when it does not. Tracked
  keywords now land through `core.keywords`, the single writer for
  `keywords/tracking.yaml` - still a gated strategy mutation.
- **Rank tracking with a real source.** The weekly reads true positions for
  `keywords/tracking.yaml` entries, independent of GSC's own-site lagged
  view - the feature that previously silently never ran on most instances.
  Recorded next to the GSC average in `keywords/history.tsv` via additive
  trailing columns; adapter absent means one honest no-rank-source line.
- **`hoo-competitor-intel`: licensed competitor data.** Keyword coverage and
  backlink profiles without touching the ADR-0006 no-scraping line.
- **`hoo-citation-tracker`: their AI Visibility workflow as a source.**
- **Tasks carried from the same study (still open, tracked as issues):** a
  deliberately broken fixture site for onsite-audit tests (their `badseo`
  pattern); investigate cross-listing skills on the `npx skills` registry
  for reach beyond the plugin marketplace.

Not adopted - their web-app architecture, bundling DataForSEO directly, any
UI - with reasons in the ADR, so the discussion is not re-litigated.

## v1.0 - Many sites, many hands

- **Multi-site orchestration across brain repos.** The sites registry
  (`~/.config/organic-os/sites.yaml`) already tracks multiple sites; v1.0
  adds running routines across all of them in one pass, not one at a time.
- **Agency mode.** Named approvers per site, approval TTL, white-label
  Monday report. Reporting is the retention feature for the agency
  persona, same evidence as the Monday report above
  ([source](https://seojuice.com/blog/automating-repetitive-seo-tasks-for-freelancers/)).
- **Content inventory and portfolio view over the brain repo.** Inventory
  analysis is the retention hook of MarketMuse-class tools
  ([source](https://checkthat.ai/brands/marketmuse/reviews)).
- **Reddit and community observe, read-only.** Subreddit mentions as
  signals, never posting. Reddit accounts for roughly a quarter of
  Perplexity citations
  ([source](https://www.cmswire.com/digital-marketing/reddits-rise-in-ai-citations-what-marketers-must-know-about-aeo-strategy/)).
- **AI-crawler analytics from server logs.** GPTBot, ClaudeBot,
  PerplexityBot crawl behavior over time - an open-source gap today
  ([source](https://www.surmado.com/blog/best-ai-visibility-tools-2026)).
- **Adapter contribution guide.** A how-to for the CMS/channel adapter
  pattern established in v0.3, once there are enough real adapters to
  generalize from.
- **Signed release provenance (Sigstore / SLSA build attestation).** Today
  a release is a tag on a CI-green commit, and that tag is the integrity
  anchor (see `THREAT-MODEL.md`). Cryptographic build-provenance attestation
  would let an installer verify the tree came from this repo's CI and was
  not tampered with in between. Named here honestly as not-yet-implemented
  rather than implied anywhere in the docs.
- **Read-only MCP surface over the brain repo.** Commercial tools now
  sell MCP access to their data; ours would be thin and optional, because
  the brain is already plain files in the user's own git repo. A richer
  onboarding card (MCP Apps) would share that same server if it ever
  ships - a revisit trigger once the MCP Apps surface is stable in both
  clients, not a promise; the enable form and chip interview carry
  onboarding until then.

## Deprioritized, with reasons

Not dropped - reordered below the items above, on purpose, with the reason
made explicit instead of left implicit.

- **Shopify adapter.** Waits for the first external request. The
  git-static adapter above serves the actual early adopters seen so far.
- **CrUX Core Web Vitals monitoring.** Table stakes elsewhere. Off-site
  authority is roughly 3x more influential than on-site technical factors
  for AI visibility, the same study cited for digital-PR mention signals
  above
  ([source](https://ahrefs.com/blog/ai-brand-visibility-correlations/)).
- **Anonymized lessons library.** A community feature that waits for a
  community. Tactic and evidence tier only, opt-in, no URLs, keywords, or
  brand names - the structured version of the "share a learning without
  data" path `CONTRIBUTING.md` describes today as an issue.

## Out of scope, deliberately

Each of these is a different surface with its own tooling category.
organic-os stays the search-and-AI-answers engine; it does not grow into a
general marketing suite.

- **Local SEO and Google Business Profile.** A different ranking system
  (map pack, not organic/AI answers) with its own signal set.
- **Review management.** A reputation-management surface, not a
  search-visibility one.
- **Email and newsletters.** A distribution channel organic-os's output
  can feed, not a channel it should operate.
- **Social repurposing.** Same reasoning as email - downstream of what
  this project produces, not a function it should absorb.
- **Conversion optimization beyond reporting.** On-site conversion work is
  a different discipline (CRO) from earning and keeping organic and AI
  visibility.

## What we will not build

The same market review that produced the v0.4 additions above also
produced this list. These are not gaps waiting for engineering time; they
are commercial-tool patterns rejected on principle, each with the reason
stated so the rejection survives a re-litigation.

- **Scraped SERP rank tracking.** ToS-violating scraping; ADR-0006 rules
  it out, and the GSC-position tracking above is the honest substitute.
- **Proprietary crawl or keyword databases.** BYO adapters exist; we will
  not fake a data moat we do not have.
- **Opaque 0-100 content scores.** A single score implies causation
  without evidence; we ship named checks with evidence tiers instead.
- **Pooled customer benchmarks.** Requires telemetry we refuse to
  collect.
- **Export gating and data-hostage patterns.** The brain is your git
  repo; leaving must always be trivial.
- **Aggregate visibility indexes without published methodology.** A
  number nobody outside the vendor can recompute is marketing, not
  measurement.

## Revisit triggers (not versioned)

Some items are blocked on something outside this project, not on
engineering time. They get picked up when the trigger fires, regardless of
which version is current:

- **WordPress `mcp-adapter` reaching 1.0** (see ADR-0003,
  `docs/adr/0003-rest-over-mcp-for-wordpress.md`) - the write path may move
  off plain REST once the official MCP bridge is no longer pre-1.0 and
  covers write operations, not just reads.
- **An official rank-tracking API** from Google or a comparable provider
  (see ADR-0006, `docs/adr/0006-no-scraping.md`) - organic-os ships no
  scraper by design; a licensed, official API is the only path to closing
  the rank-tracking coverage gap that decision leaves open.
- **A brain large enough to strain plain-text retrieval** - roughly 100
  signal files, or the point where a skill's memory read starts crowding
  the context it needs for the actual work. Today a brain is small enough
  that `decisions.search()`'s loose token overlap is the right tool: one
  irrelevant hit a human skims costs far less than a missed prior
  rejection. When the trigger fires, the fix is **progressive retrieval**
  rather than a vector database - rank matching chunks, return excerpts
  with a locator, and expand to the full section or the raw file only on
  demand. That needs no new dependency and no index to keep in sync.
  Pattern credit: [MemSearch](https://github.com/zilliztech/memsearch)'s
  L1/L2/L3 progressive search. Its other pillars stay deliberately
  unadopted: a local vector database and a downloaded embedding model
  would break the no-server, no-database promise this project enforces in
  CI, and live file watchers mean a background daemon organic-os has
  never shipped. Semantic retrieval solves precision at volume; if
  precision ever fails at volume, that is measurable, and it is the
  moment to reconsider - not before.
