---
name: hoo-daily
description: Use for the daily signal pull - "run the daily", scheduled daily routine, or "pull today's numbers". Appends observations to the brain repo signals; never mutates the site or the skillbook.
---

# Daily signal pull (Generator role - append only)

Resolve the brain: use registry.get_active() when running interactively;
scheduled runs receive the brain path from the routine configuration.

0. Run `core.contracts.check_schema(brain_path)` first. If not compatible,
   relay the action string and stop before any of the steps below.

1. Read site-profile.yaml. Determine available sources: GSC connector, GA4
   connector, tracked keywords in keywords/tracking.yaml, WordPress endpoint.
   The sessions and referral pulls read the analytics slot (ADR-0009) -
   GA4 is the adapter today; see CONTRIBUTING.md's "Contributing an
   analytics adapter" to add Clarity or Matomo.
2. Pull, for yesterday (or since the last signal date - read the latest file in
   signals/): GSC clicks/impressions/CTR/position for top and tracked queries;
   GA4 sessions; spot-check 3 tracked keywords in one AI engine, rotating.
2.5. AI-referral segmentation (runs only when GA4 is reachable): segment
   referral sessions whose source matches a known AI surface and record
   one `ai_referrals:` line in the daily signal - the session count plus
   the top landing pages (cap 3, each with its count). The known AI
   surfaces: chatgpt.com, perplexity.ai, gemini.google.com,
   copilot.microsoft.com, claude.ai. This list is maintained here, in
   this skill, and reviewed quarterly - hoo-weekly and hoo-monday-report
   quote it, never extend it (see docs/INFORMATION-MAP.md in the repo).
   Zero matching sessions is a real value - write `ai_referrals: 0`. GA4
   unreachable means no `ai_referrals:` line at all, never a guessed
   one.
2.6. Headline metrics line: record what steps 2 and 2.5 actually pulled as
   ONE structured signal line so later runs can parse it - the exact
   tokens `clicks: N`, `impressions: N`, `sessions: N` on a single line
   (site-wide daily totals; a source that was not pulled omits its token,
   never writes 0). Together with step 2.5's `ai_referrals: N` these are
   the daily's structured metric forms; the anomaly check below and the
   CSV export (skills/hoo-export, `core.export`) parse exactly these
   tokens.
2.7. Anomaly check: for each headline metric this run actually has - GSC
   clicks, GSC impressions, GA4 sessions, ai_referrals - collect the same
   metric's values from the trailing 7 daily signal files (parse the
   structured lines from steps 2.5 and 2.6; days without the metric are
   gaps, never zeros) and compare today's value to the median of those
   trailing values.
   - Baseline discipline: fewer than 4 prior daily signals carrying the
     metric -> skip that metric with a one-line note in today's signal
     ("anomaly check: skipped <metric>, no baseline yet") - no baseline,
     no alert.
   - Noise floor: a trailing median below 10 -> skip the metric; percent
     swings on single-digit medians are noise, not signals.
   - Threshold: today deviating from the median by more than 40 percent
     in either direction flags the metric. The default is
     profile-configurable via the additive `alerts: {threshold_pct: 40}`
     key in site-profile.yaml (absence means 40; see
     docs/site-repo-contract.md).
   Each flagged metric -> one P1 signal in falsifiable form: the metric,
   today's value, the 7-day median, the direction, and a cause line that
   obeys the attribution rule below. These P1 signals JOIN the daily
   alert below - never a separate message.

   THE ATTRIBUTION RULE, canonical here; hoo-weekly and onsite-measure
   quote it. A cause may not be asserted without naming the comparison
   that was actually run. Every causal claim carries three parts:
   - the claim: "clicks fell because it was a weekend";
   - the comparison actually performed: "today vs the 3 most recent
     same-weekday signals";
   - what would falsify it: "if next Saturday lands at the weekday
     median, seasonality was not the cause".
   If the comparison was not run, the cause is recorded as
   `cause: unknown (no same-weekday comparison run)` - never a
   plausible-sounding guess. "Weekend seasonality" is not an explanation
   unless the same-weekday prior-period comparison was actually made,
   and a deploy is not an explanation unless the deploy record was
   actually read. Candidates worth comparing against: same-weekday prior
   periods, a deploy or release record, a tracking or tag change, a SERP
   feature shift. An unknown cause is a complete signal, not a failed
   one: it says what moved and what has not yet been checked.
   The caveat still rides in the signal itself: this check compares one
   day against a 7-day median, so seasonality can trip it.
   Rationale: alerting is the retention feature of every commercial
   monitor; ours rides the existing channel taxonomy instead of adding a
   dashboard (ROADMAP, v0.4).
2.8. Stage classification. Every detector in this skill and in
   skills/hoo-weekly was written for a site that already earns clicks, so
   a new site trips none of them and the loop goes quiet for months. Decide
   which stage this site is in, from its own numbers, before reporting
   anything.
   - Build rows from the GSC page/query pull step 2 already made: one dict
     per query carrying clicks, impressions, position, and the query and
     page where the pull has them.
   - Call `core.stage.classify(rows)`:
     `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
     `core.stage`. The thresholds live in that module, never restated here
     (see docs/INFORMATION-MAP.md in the repo).
   - Record it as ONE structured signal line: the exact token
     `stage: <early|growing|established>` followed by the returned reason
     sentence. No GSC pull this run means no `stage:` line at all, never a
     guessed one.
   - GROWING or ESTABLISHED: nothing else changes. Every section of this
     skill and of skills/hoo-weekly runs exactly as it runs today. This
     step is purely additive for a site that has clicks.
   - EARLY: run the early-stage report below instead of reporting a quiet
     day.
3. Write one `append_signal` line per notable observation (threshold: any WoW
   move > 10% or position change > 2 or a new AI citation appearing/vanishing).
   Quiet days produce one line: "no notable movement (checked: <sources>)".
   EXCEPTION: on an EARLY site with any impressions this run, a day is
   never quiet - the early-stage report below is what gets written, and
   "no notable movement" is wrong on data that says the site is visible.
   If neither GSC nor GA4 was reachable this run (both connectors read
   anything other than `verified` in `connectors:`), write the literal line
   `no-data: GSC/GA4 not reachable from this runtime (checked: none)` instead
   - this exact string is what step 3.5 below counts and greps for, so do
   not paraphrase it.
3.5. **No-data escalation.** After writing today's signal, count consecutive
   daily signal files - today's plus however many immediately prior days'
   files also contain a `no-data:` line, walking backward by filename date
   and stopping at the first file that does not (a day with real data, or a
   missing file, breaks the streak). If that count reaches 3:
   - Check the last 7 days of signal files for a `nudge-sent:` line. If one
     is already there, skip sending - do not repeat the nudge more than once
     per 7 days.
   - Otherwise send one nudge through the configured approval channel. This
     is a plain notification, not an approval item - send_item-style text
     delivered directly over the channel (telegram: one `sendMessage`; slack:
     one post; email: one send; in-session: print it; pr-merge: no live
     channel mid-cycle, so just log it to the signal and skip delivery), not
     a `create_item`/approve-reject proposal:
     "3 daily runs with no analytics data - GSC/GA4 are not reachable from
     this runtime. Fix: run /organic-os:setup and use the connector wizard
     for GSC/GA4, or connect directly - claude.ai Settings -> Connectors, or
     /mcp / claude mcp add <server> in Claude Code."
   - Mark the nudge sent by appending `nudge-sent: no-data escalation
     (GSC/GA4)` to today's signal file via `append_signal` - this is the
     state marker; do not create a new state file for it.
4. If an observation crosses P1 (drop > 30% on a money page), also
   `create_item(kind="onpage-fix"...)` or `kind="strategy"` and notify per the
   approval channel with one call:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
   `core.approval` and calling `notify_pending(<brain>, send)`, where `send`
   delivers over the configured channel (same channel selection as
   skills/onsite-propose step 4). An item is marked notified ONLY after its
   send returns without raising, so a failed send is retried on the next run
   rather than lost. Do not call `is_notified` or `mark_notified` by hand.
5. Outcome follow-ups: for items in `outcomes/` with a due measurement date of
   today, run the measurement per skills/onsite-measure and record.
5.5. Applied-change re-verification: scan `outcomes/` for records with a
   `reverify:` block whose `until` is still in the future (written by
   skills/onsite-apply after a successful verify; see
   site-repo-contract.md). For each with `due` <= now, fetch the live
   values via the CMS adapter - the same fields the apply verified
   (title, meta description, canonical) - and compare to what the outcome
   record says was applied. Match: note the passing re-check in the
   outcome record, nothing else. Mismatch: append one P1 signal -
   "applied change no longer live - external revert suspected;
   re-propose" - naming the item id, the field, the applied value, and
   the live value; it goes out in the daily alert below. Once `until`
   passes, stop re-checking: the drift watch owns the long horizon (the
   baseline was already refreshed at apply time). Records without a
   `reverify:` block are never re-checked this way.
6. If brain mode is git: commit and push with message "signals: YYYY-MM-DD".

Missing sources are stated, never guessed. This skill NEVER writes
skillbook.md. The no-data nudge in step 3.5 is a notification, never an
approval item - it needs no decision, just a fix.

Run cost: wrapper-invoked runs land one row (date, duration, tokens where
the CLI reports them) in `~/.config/organic-os/cost-ledger-YYYYMM.tsv`;
the wrapper writes it, this skill never does - the Monday report reads it.

## Early-stage report

Runs only when step 2.8 classified the site EARLY and this run pulled any
impressions at all. A site with impressions and no clicks is not a quiet
site; it is a site whose only readable signal is position. Reporting "no
notable movement" on it is the worst thing this loop can do, because it
reads as a broken product on exactly the days when the operator could
still act on what the data does say.

1. Call `core.stage.early_opportunities(rows)` on the same rows step 2.8
   built, and write into today's signal:
   - how many queries the site is visible for and across how many pages
     (the `classify` result carries both counts);
   - one line per returned opportunity: query | page | position |
     impressions | band | the lever from the note. The note names the
     lever, never a promised position change - a prediction nobody
     measured is not a finding, which is the same discipline the
     attribution rule in step 2.7 enforces on causes.
2. State the expectation plainly, in the signal and in any message that
   goes out: zero clicks at these positions is normal and not a fault.
   Nothing is being ranked and skipped over; there is simply nothing high
   enough yet to be clicked.
3. Say what would change the picture, naming the specific pages and
   queries from step 1 rather than generic advice: title and description
   work on anything in the `top` band, on-page work on the `page-two`
   queries, depth or authority on the `visible` ones, and time -
   indexing and position both move over weeks, not days.
4. Name the dormant detectors and the threshold that activates each, so
   the silence is explained instead of mysterious. All four stay skipped
   on an EARLY site; the point is to say so rather than to run them:
   - anomaly check (step 2.7): needs a trailing 7-day median of 10 or
     more on a headline metric, plus 4 prior daily signals carrying it.
   - striking distance (skills/hoo-weekly): needs queries at positions
     4.0-15.0 with impressions above the site's median.
   - content decay (skills/hoo-weekly): needs 50 or more clicks on a page
     in the older 28-day window.
   - cannibalization (skills/hoo-weekly): needs two pages each earning
     impressions on the same query.
   One summary line in the signal covers all four; do not repeat the list
   every day at length.

Classified EARLY with zero impressions: skip this section. There are no
positions to band yet, and the `stage:` line from step 2.8 already says
so in the words `no search data yet`.

## Drift watch

Runs only when the profile's WordPress connector is verified - drift is
WP-only, there is no page inventory to snapshot without it.

1. Build the tracked-page set: the WordPress post id recorded in every
   `outcomes/*-rollback.json` snapshot (already captured by onsite-apply's
   verify step), any `proposals/` item's target page still in play, plus
   the homepage - deduped, capped at 20.
2. First run for this brain (`onsite.drift.baseline_path(root)` does not
   exist yet): `onsite.drift.snapshot_pages(wp, page_ids)`, then
   `save_baseline`. Append one signal noting the baseline was established
   and how many pages it covers.
3. Every later run: snapshot the same tracked-page set again and
   `onsite.drift.compare(root, snap)`. Empty list: one quiet signal line,
   nothing else to do. Any diff: one P1 signal per changed page, naming
   the field, the old value, and the new value - "changed outside the
   loop: field, was, now - if this change was yours, refresh the
   baseline; if not, investigate theme or plugin updates."
4. Refresh the baseline (`save_baseline`) only AFTER the signal for that
   run's diff has been written, so a given drift is reported exactly once
   and never silently re-baselined out from under a pending
   investigation.

No WordPress connection: skip silently, no note needed - unlike the GSC
sections in the weekly routine, there is no page inventory to have
skipped pulling.

## Daily alert (actionable only)

After every section above has run, decide whether the operator needs to
hear anything today. Actionable content is exactly:

- P1 signals created by this run (anomaly flags from step 2.7, drift
  "changed outside the loop", money-page drops from step 4, failed
  re-verifications from step 5.5)
- the no-data nudge from step 3.5

- the early-stage summary, on the cadence below

If any exist, send ONE message through the configured approval channel,
using the same channel-neutral delivery as the step 3.5 nudge (telegram:
one `sendMessage`; slack: one post; email: one send; in-session: print
it; pr-merge: log to the signal file and skip delivery). When the
no-data nudge fires on the same day, it rides inside this one message
instead of going out separately - never two messages per day. Quiet days
send NOTHING: no "all quiet" spam. The signal file already records the
quiet day; silence on the channel means no action needed, never that
something was hidden.

### Early-stage cadence

On an EARLY site (step 2.8) a daily "still climbing" message is noise, so
the early-stage summary goes out WEEKLY rather than daily. Send it when
either is true:

- no `stage-summary-sent:` line appears in the last 7 days of signal
  files - the same 7-day marker discipline as the no-data nudge in step
  3.5;
- OR a new query appeared this run: a query in today's opportunity list
  that no daily signal in the trailing 28 days recorded a line for. This
  one ALWAYS sends, whatever the weekly marker says. A query the site was
  not visible for before is the real progress signal at this stage, and
  sitting on it for six days would bury the only good news a new site
  gets. Name the new queries first in the message.

Mark a sent summary by appending `stage-summary-sent: early-stage summary`
to today's signal via `append_signal` - the same state-marker pattern as
`nudge-sent:`, no new state file. P1 signals and the no-data nudge keep
their own rules and still go out the day they occur; when they land on
the same day as the summary they ride inside the same single message.
