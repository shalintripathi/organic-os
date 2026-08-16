# ADR-0012: OpenSEO as an optional data tier, not a dependency

- Status: accepted
- Date: 2026-08-16
- Decision makers: Shivaa Tripathi (human), Claude (agent)

## Context

organic-os reads evidence from GA4, GSC, WordPress, and the open web. That
list has known gaps, and the skills that live in them degrade honestly
rather than guess:

- `hoo-keyword-intel` tiers on Google Ads API access alone
  (`none | basic | explorer`). A user without a developer token gets ideas
  from their own GSC queries and nothing else. Volume, difficulty, and
  SERP-feature data have no source at any tier.
- Rank tracking does not exist. GSC reports impressions and average
  position only for queries where the site already surfaced; it cannot say
  where a tracked keyword ranks when the site is absent, and it lags days.
  `keywords/tracking.yaml` ships empty and on real instances tends to stay
  empty, so the daily's AI-engine spot-check never runs.
- `hoo-competitor-intel` works from WebFetch reads of competitor pages,
  bounded by ADR-0006 (no scraping). Competitor keyword coverage and
  backlink profiles are out of reach on principle.
- `hoo-citation-tracker` prefers "an authorized AI-search source" that few
  users have.

[OpenSEO](https://github.com/every-app/open-seo) (MIT, TypeScript, 12k+
stars as of this writing) is an open-source Semrush/Ahrefs alternative:
keyword research, rank tracking, competitor insights, backlinks, site
audits, AI visibility. Its data comes from DataForSEO under the user's own
API key, pay per use. Two properties matter to us:

1. **It exposes an MCP server.** An agent can consume its data directly.
   The bridge to organic-os is a connector probe, not an integration
   project.
2. **Its data is licensed, not scraped.** DataForSEO is a commercial API
   the user pays directly. Consuming it violates nothing in ADR-0006.

## Decision

Adopt OpenSEO as an **optional, probed data tier** - the same pattern
`hoo-keyword-intel` already uses for Google Ads and the routines use for
GA4/GSC MCPs:

- If the OpenSEO MCP is reachable in the session, four touchpoints may use
  it, each naming it as the source in the evidence line:
  `hoo-keyword-intel` (volume, difficulty, SERP data as a tier available
  without Google Ads access), the weekly's rank read (true position
  tracking for `keywords/tracking.yaml` entries, independent of GSC's
  own-site view), `hoo-competitor-intel` (competitor keyword coverage and
  backlinks from licensed data), and `hoo-citation-tracker` (their AI
  Visibility workflow as a source).
- If it is not reachable, every skill behaves exactly as today. No skill
  may require it, recommend it as the only path, or fail without it.
- The user runs OpenSEO themselves (self-hosted or their hosted account)
  with their own DataForSEO key. organic-os stores no OpenSEO or
  DataForSEO credential and makes no DataForSEO call of its own.

## Not adopted, and why

- **Their architecture.** OpenSEO is a web application: UI, Postgres,
  Docker/Cloudflare hosting, a hosted tier that earns a margin on
  DataForSEO calls. organic-os promises no server, no database, no
  account; the moment it needs a deploy it is a different product. Same
  reasoning that rejected telemetry in ADR-0011.
- **Bundling DataForSEO directly.** Calling DataForSEO from our own code
  would make us a metered-API client with a vendor default, and every
  future data question would route through one paid vendor. Going through
  OpenSEO keeps the vendor relationship, the spend, and the caching in a
  tool the user controls, behind a generic MCP boundary we do not own.
- **A UI of any kind.** Their "focused workflows over a bloated suite"
  design is good; our equivalent surface is skills and reports, and the
  brain stays plain files.

Recorded so the next "should we just call DataForSEO?" discussion starts
from this decision instead of re-litigating it.

## Consequences

- Users with an OpenSEO instance get volume-backed keyword intel, true
  rank tracking, competitor coverage, and an AI-visibility source, at
  their own DataForSEO cost, with organic-os holding zero new secrets.
- Users without one lose nothing and see nothing new.
- The capability-slot rule (ADR-0009) holds: skills name the capability
  ("a rank-tracking source"), the probe finds what fills it. If a second
  MCP-exposed SEO data tool appears, it fills the same slots without new
  skill text.
- Two smaller ideas from the same study are worth carrying as tasks, not
  decisions: a `badseo`-style deliberately broken fixture site for
  onsite-audit tests, and investigating cross-listing organic-os skills on
  the `npx skills` registry for distribution beyond the Claude plugin
  marketplace.

## Revisit triggers

- The OpenSEO MCP surface changes shape or licensing in a way that breaks
  the probe: re-verify, do not pin.
- Evidence that users route around the tier (running OpenSEO but the probe
  missing it): treat as a connector bug.
- A credible second source fills the same slots: confirm the slots stay
  generic, per ADR-0009.
