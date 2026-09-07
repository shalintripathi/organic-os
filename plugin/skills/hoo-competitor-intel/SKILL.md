---
name: hoo-competitor-intel
description: Use for competitor content analysis - "what are competitors publishing", "content gaps vs <domain>", /organic-os:competitors, or the biweekly routine.
---

# Competitor intelligence

1. Read profile competitors. For each: fetch sitemap or blog index; diff
   against the previous snapshot in runs/ (first run = baseline, say so).
2. Launch competitive-intel-analyst agent per competitor (parallel, cap 3 per
   run) with the profile path.
3. Synthesize: new pages, topics they cover that we lack (cross-reference our
   sitemap), their apparent keyword focus per new page.
4. Gaps that fit our profile keywords/segments -> create_item
   kind="content-brief" (proposed, gated as always).
5. Persist runs/YYYYMMDD-competitors/ + signals for notable moves.

## search-data adapter (probed, optional)

When a search-data adapter's tools are present in this session (the
search-data slot, ADR-0009 in the repo; the known adapter is OpenSEO -
tool surface in `$CLAUDE_PLUGIN_ROOT/docs/connectors.md`, verify against
the tools actually present, never pin), add three reads the WebFetch path
above cannot reach:

1. Competitor ranking keywords via `get_ranked_keywords` per competitor
   domain - actual coverage, not inferred from page titles.
2. Backlink overview via `get_backlinks_overview` per competitor domain.
3. SERP competitors via `find_serp_competitors` on the profile's target
   keywords - domains competing in the SERPs that the profile does not
   list yet. Report them; adding one to the profile is a config change
   the user confirms, never an automatic write.

All of it is licensed data the user pays their own adapter for, so
ADR-0006 (no scraping) is untouched. Every output line carrying adapter
data names the adapter as its source. Adapter absent: steps 1-5 above
are the whole run, unchanged.
