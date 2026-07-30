---
name: hoo-monthly-audit
description: Use for the monthly deep audit - "run the monthly audit", /organic-os:monthly-audit, or the scheduled monthly routine.
---

# Monthly deep audit

1. Full sweep via the orchestrator pattern: launch all eight specialists in
   parallel with the profile path.
2. Additionally: content freshness review (pages > 12 months stale that hold
   rankings - freshness is a strong-evidence AEO factor), schema validity,
   internal-link health, tracked-keyword trend over the month, outcomes review
   (which applied changes moved metrics; feed wins/losses to the reflector).
   Run the page-essentials dimension (skills/onsite-audit step 3: author
   entity, answer capsule, in-content images, social image shape,
   publisher schema shape, sitemap membership) site-wide across the
   audited page set, not only on newly flagged pages - the checklist is
   the product's eyes, and a check that does not run cannot fire. The
   internal-link health line above runs as skills/onsite-audit step 4:
   one capped own-site crawl (`onsite.linkgraph`, sitemap-seeded) for
   broken links, orphans, hubs, shallow striking-distance pages, and
   redirect chains - same signal severities, same one-proposal cap.
3. Compare with last month's runs/ artifacts; the report leads with deltas.
4. File signals, briefs, and fixes through core contracts; rebuild queue;
   notify per approval channel with one call:
   `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
   `core.approval` and calling `notify_pending(<brain>, send)`, where `send`
   delivers over the configured channel (same channel selection as
   skills/onsite-propose step 4). An item is marked notified ONLY after its
   send returns without raising, so a failed send is retried on the next run
   rather than lost. Do not call `is_notified` or `mark_notified` by hand.
5. Output runs/YYYYMM-monthly/REPORT.md: executive summary in plain language,
   then per-specialist sections, then this month's queued work.

At each stage boundary, append a one-line progress marker with a UTC
timestamp to the run report file before starting the stage - headless runs
are watched by tailing that file, not a terminal.

## Entity consistency

1. Build the property set from the profile: the site's own homepage and
   about page, plus every URL in the optional `brand.properties:` list
   (a GitHub org or repo, a LinkedIn page - see site-repo-contract.md).
   Only URLs the profile provides are fetched - never guess a handle or
   search for unlisted profiles. No `brand.properties:` list means the
   check runs on the site's own pages only, and the report says so.
2. Fetch each property (WebFetch of public pages within the session -
   the sanctioned mechanism, docs/adr/0006 in the repo, same as the
   citation tracker) and extract the core brand facts each one states:
   brand name, one-line description, founding and location claims where
   stated, logo reference, and sameAs cross-links between properties.
3. Compare across properties. Each inconsistency is one P2 signal per
   fact: what differs, where (the URLs and their two values), and which
   version the profile says is canonical (the profile's site name and
   organization details are the reference; a fact the profile does not
   state has no canonical version - report the divergence, pick none).
4. Route fixes by where they land: an inconsistency on the user's own
   site becomes a gated proposal (a schema or about-page edit via
   `create_item`, through the normal approval gate); an inconsistency
   on a third-party property is a named human step in the report - this
   skill never writes off-site.
5. Rationale line, carried next to this section's output: consistency
   across authoritative sources drives inclusion in AI answers
   (https://www.useomnia.com/blog/how-to-improve-brand-visibility-chatgpt).

No web access this session: skip this section and note it as one line
in REPORT.md ("entity consistency: skipped, no web access") instead of
guessing.
