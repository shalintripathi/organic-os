---
name: hoo-keyword-intel
description: Use for keyword research, competitor keyword gaps, "what should we rank for", "keyword ideas for X", or the /organic-os:keywords command. Detects the user's Google Ads access tier and degrades honestly.
---

# Keyword intelligence (tiered)

0. Read site-profile.yaml (google_ads.status, keywords.targets, competitors,
   geos, languages). Source env from `~/.config/organic-os/<site-slug>.env`
   if present.

## Tier detection (once per session)
Run: `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` snippet importing
`hoo.google_ads.tier`: if env vars missing -> tier "none". Else build
real_client() and `tier.detect()` -> basic|explorer. Tell the user which tier
is active and what that enables.

In the same pass, check whether a search-data adapter's tools are present
in this session (the search-data capability slot, ADR-0009 in the repo;
the known adapter is OpenSEO - tool surface listed in
`$CLAUDE_PLUGIN_ROOT/docs/connectors.md`, OpenSEO section; verify against
the tools actually present, never pin the list). Present: the search-data
adapter section below applies on top of whatever tier is active. Absent:
every tier behaves exactly as it does today, and nothing is fabricated in
its place.

## basic (or standard)
1. Ideas: `keyword_ideas.run` with profile target keywords as seeds AND, per
   competitor, `site_seed=<competitor domain>`. Cache dir: `<brain>/keywords/cache/`.
2. Gap: ideas(own site_seed) vs ideas(competitor site_seed) - keywords in
   their set, absent from ours, volume >= 100. Rank by volume x profile fit.
3. Metrics for the shortlist: `historical.run` (batches of 200 handled inside).
4. Write `runs/YYYYMMDD-keywords/` (01-ideas.json, 02-gaps.json, REPORT.md)
   and update `keywords/tracking.yaml` targets the user confirms (additions
   are a strategy mutation -> create_item kind="strategy" + approval gate).

## explorer
Own-account GAQL only: search_term_view mining (queries with impressions and
no matching target), keyword_view quality scores. State plainly: "Planner
blocked at Explorer tier - apply for Basic (https://github.com/shalintripathi/organic-os/blob/main/plugin/docs/credentials/google-ads-token.md, also at $CLAUDE_PLUGIN_ROOT/docs/credentials/google-ads-token.md in a local checkout)".

## none (no token)
GSC query mining via the user's GSC connector: 16 months, queries with
impressions > 100 and position 8-30 = the opportunity set. If no GSC either:
offer CSV import.

## csv (always available)
Accept a Keyword Planner UI export: `csv_import.load_planner_csv(path)`.
Auction Insights CSVs: summarize overlap/position trends per competitor.

## search-data adapter (works with every tier above)

Runs only when tier detection found the adapter's tools in this session;
absent means this whole section does not exist for the run.

1. Hydrate the idea shortlist with volume, difficulty, and CPC via
   `get_keyword_metrics`. On tier "none" this is the headline value:
   keyword volume without a Google Ads token. On basic/explorer it
   enriches the Planner pull rather than replacing it.
2. Competitor gap without a Planner: `get_ranked_keywords` and
   `get_domain_keyword_suggestions` per competitor domain, diffed against
   our own coverage the same way the basic tier's gap step diffs
   site_seed pulls.
3. SERP snapshot for the top opportunities via `get_serp_results`: who
   holds the positions, which SERP features sit above them.

Every output line that carries adapter data names the adapter as its
source (evidence line style: `volume/difficulty per <adapter>`), the same
rule every capability slot follows.

Tracked-keyword management: never edit `keywords/tracking.yaml` by hand.
Additions are a strategy mutation - create_item kind="strategy" +
approval gate, unchanged - and once approved they land through the one
writer: `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c "..."` importing
`core.keywords` and calling `add_tracked(<brain>, [terms],
source="hoo-keyword-intel")`. It returns added and skipped lists;
already-tracked terms (case-insensitive) are skipped, so re-running an
approved addition is safe. Read the set with `core.keywords.load_tracked`.
The weekly run records tracked keywords' history (skills/hoo-weekly,
Keyword portfolio section).

If `tracking.yaml` is empty and the profile has seed keywords
(keywords.targets), offer to seed the tracked set from them - through the
same gated path above, never directly.

Output in every tier: REPORT.md with the top 20 opportunities, each carrying
volume (or proxy), difficulty proxy, intent guess, recommended action
(new page | optimize existing | ignore), and the evidence line.

## Cluster the ideas

Runs when the pull above produced 30 or more ideas (any tier). Fewer than
30: skip silently - too few ideas cluster into noise, and a skip note
would only add chrome.

1. Group the ideas by intent + lexical family into named clusters
   (shared head term, shared modifiers, same question family).
2. For each cluster: pick the hub - the highest-volume informational head
   term - and list the spokes (the remaining ideas that belong to it).
3. Check existing coverage: map each cluster against the site's published
   pages via the sitemap and, when the GSC connector is available, the
   pages already earning impressions for the cluster's queries. A cluster
   whose hub and spokes are already covered is reported as covered, not
   re-proposed.
4. Per UNCOVERED cluster, write ONE architecture signal (append_signal):
   the hub topic, 3-5 spoke topics, and the internal-linking rule - every
   spoke links the hub, the hub links every spoke. This is the build-time
   complement of the link-graph dimension's shallow striking-distance
   play (skills/onsite-audit step 4): pages born inside a cluster never
   start with fewer than 2 inbound internal links.
5. At most ONE cluster per run becomes a gated brief: for the best
   uncovered cluster, `create_item(kind="content-brief", ...)` targeting
   the hub, `brief_type` per the hub's intent (comparison-intent hub ->
   `brief_type="comparison"`; absence means explainer). Gated through the
   approval queue like every other proposal; the remaining clusters stay
   signals until a future run.

Pattern credit: claude-seo's SERP clustering
(https://github.com/AgriciDaniel/claude-seo), adapted here to consume
keyword-intel output instead of running its own SERP pulls.
