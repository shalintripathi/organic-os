# The site repo contract

Every site organic-os manages has its own "brain": a git repo (or plain
folder, in local brain mode) holding everything the plugin knows about that
site. This page documents its layout, the item schema, the skillbook line
format, and the write discipline that keeps memory useful instead of
becoming an unreadable pile.

**The rule that matters most: any tool may READ these files; only
`lib/core` WRITES them.** Skills in `lib/hoo`, `lib/onsite`, and the
content-engine agents call into `core.contracts` and `core.approval` for
every mutation. None of them touch a brain-repo file with a raw `open()` or
a raw commit for anything status-bearing. This is what makes the approval
gate enforceable in code rather than by convention - there is exactly one
choke point where a write can happen, and that choke point checks status.

## Layout

```
organic-hq-<site>/
  site-profile.yaml        identity: url, sitemap, brand voice rules, competitors,
                            geos, connectors, approval channel, runtime mode, WP endpoint
  skillbook.md              curated playbook, one entry per line (see below)
  signals/YYYY-MM-DD.md     daily raw observations, append-only, never edited
  reflections/YYYY-Www.md   weekly reflector output: proposed skillbook deltas by entry ID
  decisions/<date>-<slug>.md decision records: what was chosen, by whom, why
  decisions/NNNN-*.md       ADRs for this site, MADR-lite + Agent Context section
  briefs/                   content briefs, one file each, status frontmatter
  proposals/                on-page fix proposals, same status lifecycle as briefs
  approvals/queue.md        pending-approval index, rebuilt on every status change
  runs/YYYYMMDD-<skill>/    timestamped run outputs: numbered raw files + REPORT.md
  keywords/tracking.yaml    tracked keyword set
  keywords/history.tsv      GSC keyword-portfolio history, append-only (additive, see below)
  outcomes/                 post-change measurements linked back to the item that caused them
  drift/baseline.json       on-page snapshot for drift detection, WP-only, lazy (see below)
```

`init_site_repo` (run by `/organic-os:setup`) creates every directory above,
a starter `site-profile.yaml` with the site's URL and name filled in, an
empty `skillbook.md` with its header, an empty `approvals/queue.md`, and an
empty `keywords/tracking.yaml`. It never overwrites a file that already
exists, so re-running setup on an existing brain repo is safe.

`keywords/history.tsv` is additive the same way (`schema_version` stays
`1`) and does not appear in the scaffold: the weekly routine's Keyword
portfolio section (skills/hoo-weekly) creates it on its first run with a
verified GSC connector and a non-empty tracked set. Tab-separated,
header `date	keyword	position	clicks	impressions`, one appended row per
tracked keyword per weekly run - append-only, rows never edited or
removed, the same discipline as `signals/`. The position is GSC average
position for queries matching the tracked term, never a scraped SERP
rank; a keyword with zero impressions in the window gets an EMPTY
position field - unknown is recorded as absent, never guessed.

`drift/` is additive and does not appear in that scaffold: `schema_version`
stays `1`, and the directory only comes into existence the first time
`hoo-daily`'s drift-watch section runs with a verified WordPress
connector (`onsite.drift.save_baseline` creates it on demand). A brain
repo with no WordPress connection never gets a `drift/` directory at all.

Ten optional `site-profile.yaml` keys are additive the same way
(`schema_version` stays `1`; absence means off, or the stated default):

- `brand: {readability_target: "grade 9-10"}` - the readability target
  ce-qa's hard check holds drafts to (sentence-length stats; a draft
  over target is returned for splitting). Absence means the default of
  "grade 9-10".
- `brand: {properties: [...]}` - exact URLs of the brand's public
  properties (a GitHub org or repo, a LinkedIn page) that
  `hoo-monthly-audit`'s entity-consistency section fetches and compares
  against the site's own brand facts. Only URLs listed here are ever
  fetched - the audit never guesses a handle from the brand name.
  Absence means the check covers the site's own pages only. Fixes the
  check proposes stay gated and on-site; anything on a third-party
  property is a named human step.

- `editorial: {...}` - the editorial-policy section: an organization's
  written conventions as hard QA checks, the way the answer capsule and
  readability target are enforced. The canonical defaults live in
  `core.contracts.editorial_policy` (`plugin/lib/core/contracts.py`);
  absent keys mean the defaults, unknown keys are ignored (additive
  both ways), and an invalid value refuses naming the key. ce-qa
  enforces every key below except `oversight_threshold`, which belongs
  to ce-editor's scoring pass. Free-text rules in `brand.rulebook`
  still apply on top: the policy keys are the enforceable floor, the
  prose is the voice.

  ```yaml
  editorial:
    oversight_threshold: 7      # default 7
    internal_links_min: 0       # default 0 (off)
    external_links_max: null    # default null (no cap)
    images_min: 0               # default 0 (off)
    sourcing: key-claims        # default key-claims
    require_reviewer_note: false  # default false
  ```

  - `oversight_threshold` - the human-review-necessity score (0-10,
    built by ce-editor's final pass from named factors: claims density,
    YMYL adjacency, competitor mentions, legal/compliance surface,
    verbatim research survival) at or above which the draft notes
    recommend a human line-edit before publish and onsite-publish
    surfaces that recommendation prominently in the approval-channel
    message. The score informs the approver; publishing stays gated by
    the same single approval either way.
  - `internal_links_min` - when above 0, a draft linking fewer than N
    same-site pages is returned to the writer.
  - `external_links_max` - when set, a draft over the cap is returned
    to the writer.
  - `images_min` - when above 0, a draft with fewer in-content images
    than N needs an image brief attached per missing image
    (skills/ce-image's `<slug>-image-brief.md` shape) before it can
    pass QA.
  - `sourcing` - `key-claims`: statistics and comparative claims need
    sources; `every-claim`: every factual claim does.
  - `require_reviewer_note` - when true, the draft notes must name a
    human reviewer before publish qualifies.

  Regulated-industry review stages (a compliance reviewer before
  publish) are v1.0 multi-approver work, not this section.

- `alerts: {threshold_pct: 40}` - the deviation percent at which the
  daily anomaly check (skills/hoo-daily step 2.7) flags a headline
  metric against its trailing 7-day median and joins the daily alert;
  absence means 40. The noise floor (a median below 10 skips the
  metric) and the minimum baseline (4 prior daily signals) are fixed in
  the skill, not configurable here.
- `citations: {engines: [...]}` - the AI answer engines the citation
  tracker (skills/hoo-citation-tracker) samples. Absence means the
  default set, canonical in that skill. Each listed engine is checked
  only when it is reachable from the session running the tracker -
  unreachable engines are named as unreachable in the report, never
  silently skipped. Adding an engine is one more list entry, through
  the same connector-or-WebSearch path - no tiers, no per-engine
  pricing.
- `onsite: {dry_run: true}` - `onsite-apply` and `onsite-publish` run
  their full gated flow against a dry-run client that records every
  intended write instead of performing it; the outcome record is marked
  dry-run and lists them.
- `indexnow: {enabled: true, key: <32-hex>}` - after a successful
  verified apply or publish, the changed URL is submitted via IndexNow
  and the response status recorded in the outcome (see
  `plugin/docs/connectors.md`).
- `approvals: {ttl_days: 30}` - how many days an approved decision stays
  fresh before the gates require re-confirmation; absence means the
  default of 30. Below 1 refuses - to disable expiry, set a large value
  deliberately (see `plugin/docs/approval-channels.md` and docs/adr/0008
  in the repo).
- `skillbook: {stale_days: {anecdotal: 90, moderate: 180, strong: 365}}` -
  how many days a skillbook entry stays trusted, per evidence tier, before
  the weekly reflection asks a human to re-confirm it. The canonical
  defaults live in `core.contracts.STALE_DEFAULTS`
  (`plugin/lib/core/contracts.py`); each tier falls back to its default
  independently, so overriding one leaves the other two alone, and a value
  below 1 (or a non-integer) refuses naming the key. Weak evidence goes
  stale fast, strong evidence keeps for a year. An entry exactly at its
  threshold is still fresh; one day past is stale. Staleness is surfaced,
  never enforced: `skillbook_stale` reads, the reflector presents, a human
  re-confirms (which stamps `last-confirmed` to today) or approves a
  deprecation.
- `cms: {type: wordpress}` - which CMS adapter the onsite write path
  uses (`onsite.cms.adapter_for` builds it; the contract is `CmsAdapter`
  in `plugin/lib/onsite/cms.py`, per docs/adr/0009 in the repo). Absence
  defaults to `wordpress` when the profile has a wordpress endpoint
  configured; an unknown type refuses, naming the supported types.
  WordPress is adapter one. Git-static is adapter two, for static sites
  built from a git repo (Astro, Next, Hugo, Jekyll class) where content
  is markdown/MDX files with YAML frontmatter:

  ```yaml
  cms:
    type: git-static
    repo_root: /path/to/local/clone   # required; the runtime clones/pulls
    content_dir: src/content          # optional; this is the default
    deploy_url: https://site.example  # optional; best-effort post-merge check
    redirect_file: _redirects         # optional; where redirect fixes land
    fields:                           # optional; remap generic -> frontmatter
      description: excerpt
  ```

  The adapter reads and writes files in the local clone and never runs
  git itself; the skill layer runs the git/gh commands and delivers every
  change as a pull request against the site repo - merging is the human's
  final act (`needs_human: ["merge-pr", "deploy"]`). Default field names:
  `title`, `description`, `canonical`, `jsonld` (for `schema_jsonld`),
  `draft`, `slug`. The `jsonld` field holds a raw JSON-LD string the
  site's layout must render into the head; rendered-head verification is
  a declared capability gap (`rendered_head_verify: False` - static sites
  verify post-deploy, best-effort, against `deploy_url` when set).

  `redirect_file` is additive the same way (`schema_version` stays `1`):
  it names the platform redirect config the gated redirect workflow
  appends to - `_redirects` (Cloudflare/Netlify style), `netlify.toml`,
  or `vercel.json`. Adapters declare their redirect mode in
  `capabilities()['redirects']`: git-static is `config-file` (the skill
  layer appends the rule and delivers it on the normal branch/PR flow);
  wordpress is `needs-plugin` (core WordPress has no redirect REST
  surface, so the apply skill probes known SEO-plugin surfaces at run
  time and otherwise ends the item partially-applied naming the manual
  step). See the redirect-fixes section in skills/onsite-apply.

## The export run dir (additive)

`runs/<UTCdate>-export/` is written by `core.export.export_all` (the
hoo-export skill, `/organic-os:export`): `signals.csv` (date, metric,
value - parsed from the daily's structured metric tokens `clicks:`,
`impressions:`, `sessions:`, `ai_referrals:`; a line whose metric value
does not parse is skipped and counted, never guessed), `keywords.csv`
(`keywords/history.tsv` columns verbatim), and `outcomes.csv` (date,
item, action, status, verified - best-effort key parse; absent keys stay
empty). A source the brain does not have yet produces no file. Like
every `runs/` folder it is a timestamped output, not state: re-running
on the same UTC date overwrites that date's CSVs with a fresh flatten of
the same append-only sources.

## Items: briefs and proposals

An item is a markdown file with YAML frontmatter, living in `briefs/`
(content briefs, `kind: content-brief`) or `proposals/` (everything else:
`onpage-fix`, `publish`, `strategy`). The filename is
`<created-date>-<slug>.md`; the frontmatter `id` is `b-<date>-<slug>` for
briefs and `p-<date>-<slug>` for proposals.

Frontmatter fields: `id`, `kind`, `status`, `created` (UTC timestamp),
`title`, `target` (the URL or entity the item is about), `source` (what
produced it - a signal, an audit finding, an operator note), and
`approvals` (a list that starts empty and gets an entry appended every time
`set_status` records an `approved` or `rejected` decision: `actor`,
`channel`, `decision`, `at`).

Content briefs may carry one more optional field, `brief_type` - additive
(`schema_version` stays `1`; absence means the default, `explainer`). The
other value is `comparison`, marking an X-vs-Y brief: the content pipeline
drafts it with comparison-specific stage guidance (see skills/ce-produce),
and the signal-driven skills set it when comparison-intent queries
(vs / alternative / best-X-for) produced the brief. The field is written
only through `create_item(..., brief_type=...)`; an unknown value refuses,
naming the supported types (`BRIEF_TYPES` in `plugin/lib/core/contracts.py`).

### Status lifecycle

```
proposed -> approved | rejected
approved -> applied | drafted | failed
drafted  -> published
applied | published -> measured
```

`failed` exists for the case where an approved on-page fix was applied,
failed its post-write verification, and was rolled back - it sits between
`approved` and everything downstream, and `applied -> failed` is
deliberately not a legal transition, because a failure is only possible
before the write is confirmed to have stuck.

Illegal transitions raise `ContractError` rather than silently no-op. There
is no path back from `approved` to `proposed`, and no path at all out of
`rejected` - a rejected item is done; a new item gets created if the work
still needs doing.

### The approval gate in code

Two functions gate mutation, used at different points in an item's life:

- **`require_approved(path)`** - the item's *current* status must be
  `approved`. This is the gate `onsite-apply` uses before it writes
  anything to WordPress: an on-page fix has exactly one mutating step, so
  its status is still `approved` at the moment of the write.
- **`require_approval_lineage(path)`** - the item's history must contain at
  least one `approved` decision, regardless of current status. This is the
  gate `onsite-publish` uses: a content brief moves `approved -> drafted`
  (content-engine writing the draft is not itself the mutation that
  matters), and only then does publishing become the actual WordPress
  write. By the time publishing happens the item's current status is
  `drafted`, not `approved`, so `require_approved` would wrongly block it.
  `require_approval_lineage` is safe here specifically because
  `approved -> rejected` is not a legal transition: once an item has an
  `approved` decision in its history, nothing can revoke it later, so a
  lineage check can never be tricked into approving something that was
  actually rejected afterward.

## approvals/queue.md

Rebuilt by `rebuild_queue` on every status change: one line per item
currently sitting at `proposed`, across both `briefs/` and `proposals/`,
sorted by filename. A malformed item (bad frontmatter, missing fields)
appears as a `MALFORMED` row instead of being silently dropped, so a broken
file surfaces instead of disappearing from view. An item born with a
non-proposed status and an empty approvals list - a file written outside
`create_item` - appears as an `ILLEGAL-STATE` row naming the repair
(`python3 -m core reset-to-proposed <path>`), because such an item can
neither be approved nor pass a gate and would otherwise jam the pipeline
silently.

### The queue is DERIVED - a stale queue is a bug

`approvals/queue.md` holds no state of its own. Every line in it is
recomputed from the item files, which are the only source of truth; the
file exists so a human can read the pending set at a glance. It is
therefore only ever correct because something rebuilt it.

`contracts.set_status` and `contracts.reset_to_proposed` rebuild it
themselves, after the item is durably written. Any status change made
through the contract layer - the CLI, a skill, a direct Python call -
leaves the queue current. Nothing needs to remember to refresh it, and
nothing should hand-edit the file: an edit is overwritten by the next
status change.

The rebuild is best-effort. If it fails (an unwritable file, a malformed
sibling), the status change still succeeds and the queue is simply left
at its previous content until the next change refreshes it. A derived
file must never roll back or block a real state transition.

So: if the queue disagrees with the item files, that is a defect to
report, not an expected state to work around. An earlier version rebuilt
the queue only in the CLI, so skills that published or applied items left
it frozen - it kept listing work as pending for days after that work had
shipped, and the operator reasonably read the stale queue as a dead
pipeline.

## Re-verification keys in outcome records (additive)

After a successful rendered-head-verified apply, `onsite-apply` writes a
re-verification window into the item's outcome record in `outcomes/`:

```yaml
reverify:
  due: 2026-07-19T15:04:00Z    # first re-check: one hour after the verified apply
  until: 2026-07-21T14:04:00Z  # window end: 48 hours after the verified apply
```

`hoo-daily` re-checks the live values against the applied values between
`due` and `until`; a mismatch is a P1 signal ("applied change no longer
live - external revert suspected; re-propose") delivered in the daily
alert. The window exists because an external bulk revert can undo an
applied change minutes after verification, and waiting for the next full
audit to notice is too slow. After `until` passes, the drift watch owns
the long horizon - the drift baseline was already refreshed at apply
time. The keys are additive: `schema_version` stays 1, and records
without them (older applies, git-static deliveries, dry-run outcomes)
are simply never re-checked this way.

## Outcome records, and recomputing what they claim

An outcome record is `outcomes/<item-id>.md`: markdown written by the
apply or publish step and added to by the measurement step, so it is
prose plus keys rather than a fixed schema. `core.outcomes.parse_outcome`
reads one back into a stable seven-field shape, and the alias names it
accepts for each field are canonical in `plugin/lib/core/outcomes.py`:

| Field | Key names a record may use |
|---|---|
| `item` | `item`, `item_id`, `id`, `slug` (falls back to the filename stem) |
| `url` | `url`, `target`, `target_url`, `page`, `permalink` |
| `applied_at` | `applied_at`, `applied`, `date`, `when`, `published_at` |
| `claimed_before` | `claimed_before`, `before`, `baseline` |
| `claimed_after` | `claimed_after`, `after` |
| `claimed_delta` | `claimed_delta`, `delta`, `change` |
| `windows` | `windows`, `window`, `measurement_windows` |

Every field is optional. A key the record never states parses as `None`,
never as a zero or a guess, and prose lines are skipped rather than
treated as an error. A key stated twice takes its last value, because
these records are appended to. `windows` holds the before and after date
ranges the claim was measured over:

```yaml
windows:
  before: {start: 2026-05-04, end: 2026-05-31}
  after: {start: 2026-06-02, end: 2026-06-29}
```

The windows are what make a claim checkable by someone who does not
trust the run that wrote it. `/organic-os:verify-outcome`
(skills/hoo-verify-outcome) reads the item, the URL and the windows from
the record, pulls those windows fresh through the search-data and
analytics slots, computes the delta, and only THEN reads the claimed
numbers and calls `core.outcomes.compare`. That order is the point: a
number already seen is a number the pull gets framed around. A divergence
is appended as a signal, never suppressed; unreachable connectors mean
the claim is unverified, never assumed correct. `plugin/docs/reproducing-results.md`
documents the same check by hand in Search Console.

## drift/baseline.json

The stored snapshot the daily drift watch (`hoo-daily`, `onsite.drift`)
compares against: `{page_id: {title, rank_math_title,
rank_math_description, canonical, slug, status, jsonld_present}}` for the
tracked-page set (pages from `outcomes/*-rollback.json` plus the homepage,
capped at 20). Written only through `onsite.drift.save_baseline`, which
atomic-writes via `core.contracts._atomic_write` - the same
read-through-core / write-through-core discipline as every other file in
this repo, just routed through `lib/onsite` instead of `lib/core` directly
since drift is an on-page (onsite) concern, not a mutation-gate concern.
No baseline on disk means `onsite.drift.compare` returns `[]` rather than
raising - a fresh brain or a brain that has never had a verified WordPress
connector simply has nothing to compare against yet. `onsite-apply`
refreshes the entry for a page it just changed as part of its own verify
step, so an intentional, approved change is never reported back as drift.

## decisions/

The brain's decision memory: what was chosen, by whom, and why, kept
where the next run can find it. Without it a rejection dies with the item
that carried it, and the loop re-proposes work a human already refused.

One file per decision, written by `core.decisions.record`:
`decisions/<UTCdate>-<slug>.md`, the slug derived from the title under the
same rule `create_item` enforces (lowercase letters, digits, hyphens).
A second decision with the same title on the same day takes a `-2`, `-3`
suffix - a new record never overwrites an older one. The frontmatter and
body:

```yaml
---
date: 2026-07-23              # UTC date of the decision
title: 'rejected: Rewrite /pricing title tag'
choice: rejected              # what was decided
actor: shivaa                 # who decided
scope: Rewrite /pricing title tag   # what the decision covers (searched)
item: proposals/20260723-pricing-title.md   # optional: the item it came from
---
legal owns that page's wording this quarter
```

The body is the rationale, verbatim. `set_status` writes one of these on
every rejection, taking the reason from the `note` the approver gave (an
unexplained rejection records "no reason recorded at rejection" rather
than an empty file), so no skill has to remember to log it.

`core.decisions.search(root, terms)` reads them back: case-insensitive
token overlap against title, scope, and rationale, newest first, no index
file. `onsite-propose`, `hoo-orchestrator`, and `ce-produce` call it
before `create_item`; a matching `rejected` decision means the work is
either skipped and named in the run report, or re-proposed with a line in
the item body stating when it was rejected, why, and what changed since.
Hand-written per-site ADRs keep their `NNNN-*.md` numbered form in the
same directory; anything `search` cannot parse as frontmatter is skipped,
not rewritten.

## Skillbook

`skillbook.md` is the curated, compounding memory: tactical lessons the
site has actually earned, not raw observations. One entry per line:

```
S-014 [evidence: strong] [helpful: 3, harmful: 0, last-confirmed: 2026-07-18] Title rewrites recover striking-distance drops (p-20260710-pricing-title)
```

- **ID** (`S-NNN`) is assigned sequentially by `skillbook_append` and never
  reused.
- **evidence** is one of `strong`, `moderate`, or `anecdotal` - the same
  three-tier vocabulary `plugin/docs/evidence.md` uses, so a skillbook entry's
  confidence is comparable across the whole plugin.
- **helpful / harmful** counters increment via `skillbook_update` whenever
  an outcome confirms or contradicts the lesson; they never reset.
- **last-confirmed** updates to today every time the entry is touched, and
  is what `skillbook_stale` judges: past its tier's threshold (the
  `skillbook.stale_days` key above), the entry joins the weekly
  reflection's stale review for a human to re-confirm or retire.
- The trailing `(source)` is the item id or the origin the lesson came
  from, so every lesson traces back to the evidence that produced it.

A deprecated entry is wrapped in `~~strikethrough~~` and suffixed
`DEPRECATED`; it stays in the file (memory is append-only-at-the-line-level,
not delete-capable) but is skipped by anything that reads active entries,
and any further update to it raises `ContractError`.

## The append-only + curator discipline

Borrowed from the ACE / Reflexion / Voyager line of agent-memory research,
carried through the whole brain repo, not just the skillbook:

- **Generator** (daily routines) appends signals via `append_signal`. It
  never touches the skillbook. `signals/YYYY-MM-DD.md` is a flat,
  timestamped, append-only log - lines are never edited or removed.
- **Reflector** (the weekly routine) reads the week's signals and outcomes
  and writes a `reflections/YYYY-Www.md` file proposing itemized deltas,
  each one referencing a specific skillbook entry ID (or proposing a new
  one). The reflector never writes `skillbook.md` directly.
- **Curator** applies those deltas as `skillbook_append` /
  `skillbook_update` calls - append, edit-in-place, or deprecate, on
  specific entries. Two things are forbidden by design: rewriting the whole
  file (it collapses the context each entry carries and makes the history
  useless for tracing why a lesson exists), and summarizing entries down to
  save space (it introduces brevity bias - a compressed lesson quietly
  drops the qualifier that made it correct). Curator merges are
  human-gated by default; a user can promote the curator to autonomous
  merging once they trust it, the same way any other mutation's gate can be
  adjusted.
- Every skillbook entry carries an evidence tag and a source, every ADR
  records the strategy-level decision it captures with an Agent Context
  section (who decided, on what evidence) - the skillbook is where
  tactical, repeatable lessons live; ADRs are where one-off strategic calls
  live. Neither substitutes for the other.
