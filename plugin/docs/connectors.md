# How connectors connect

## The honest model

organic-os bundles no MCP servers and cannot trigger an OAuth prompt
itself. It uses whatever you have already connected:

- **GA4, GSC, Notion, Slack, Canva** - connectors you authorize yourself,
  either from claude.ai's Settings -> Connectors, or via `claude mcp add`
  / `/mcp` in Claude Code.
- **Google Ads** - a developer token plus OAuth client credentials, stored
  as local env vars (see `plugin/docs/credentials/google-ads-token.md`).
- **WordPress** - an Application Password for a dedicated Editor user,
  stored in a local env file (see `plugin/docs/credentials/wordpress.md`).
- **OpenSEO** - the optional search-data adapter: an MCP server you run
  (or subscribe to) yourself, paying DataForSEO directly with your own
  key. See the OpenSEO section below.

organic-os is a plugin - skills, agents, and scripts - not a running
process, so it has no server-side identity to authenticate anything on its
own behalf. Every credential above is yours, connected by you, on your
terms.

Credentials entered at the plugin's enable-time install form (the
Telegram bot token, the WordPress Application Password) skip the
paste-into-terminal step: setup finds them keychain-backed as
`CLAUDE_PLUGIN_OPTION_*` env vars and verifies them by probe like any
other credential.

## What happens instead of a prompt

Nothing in organic-os pops an OAuth window. `/organic-os:start` and
`/organic-os:setup` **probe** what is reachable - they try listing GA4/GSC
tools, ask about Notion/Slack/Canva/OpenSEO - and print a per-connector status with
the exact instructions for connecting on your surface:

- **claude.ai / Cowork:** Settings, then Connectors.
- **Claude Code:** `/mcp`, or `claude mcp add <server>` on the command
  line.

Every skill then degrades gracefully per what it finds, following the
credentials ladder in `plugin/docs/getting-started.md#the-upgrade-ladder`: no
credentials still gets you audits, briefs, and keyword work from public
data; each connector or credential you add turns on one more capability,
never blocks the ones you already have.

## Why no bundled servers

stdio MCP servers do not run on Cowork - there is no long-lived process to
host one. Bundling a GA4/GSC server with organic-os would work in Claude
Code but silently break on Cowork, which contradicts the plugin's actual
promise: the same skills, commands, and behavior on Claude Code CLI and
Claude Cowork (see `README.md`'s Install section - "no server process, no
stdio MCP server, no database"). Probing for connectors you already manage
is the only approach that works identically on both surfaces.

## Capability table

| Capability | Connector / credential | Where to connect | What works without it |
|---|---|---|---|
| Search ranking + impression signals | Google Search Console connector or MCP server | claude.ai Settings -> Connectors, or `/mcp` / `claude mcp add` in Claude Code | `hoo-daily` and the orchestrator skip the GSC pull and say so; on-page audits still run against any public URL |
| Traffic + AI-referral signals | Google Analytics 4 connector or MCP server | claude.ai Settings -> Connectors, or `/mcp` / `claude mcp add` in Claude Code | Same skip-and-state behavior as GSC; no traffic-trend signals until connected |
| Keyword planner data (volume, forecasts) | Google Ads developer token + OAuth client (env vars) | `plugin/docs/credentials/google-ads-token.md` | `hoo-keyword-intel` falls back to CSV import or public-data estimation |
| Task/brief hand-off | Notion connector | claude.ai Settings -> Connectors, or `/mcp` / `claude mcp add` in Claude Code | Briefs and proposals still write to the brain repo's `briefs/`/`proposals/`; nothing mirrors to Notion |
| Approval notifications outside a live session | Slack connector, or Telegram/email per `plugin/docs/approval-channels.md` | claude.ai Settings -> Connectors (Slack); channel-specific setup for Telegram/email | in-session approval works immediately with zero setup; you just have to be in the session when a proposal lands |
| Asset/creative generation | Canva connector | claude.ai Settings -> Connectors, or `/mcp` / `claude mcp add` in Claude Code | Content briefs and drafts still produce text; no generated creative assets |
| Publishing approved fixes/drafts to a live site | WordPress Application Password (env file) | `plugin/docs/credentials/wordpress.md` | Everything up to `approved` still works - proposals queue and get approved, they just are not applied until WordPress is connected |
| Keyword volume/difficulty, true rank tracking, competitor keyword + backlink coverage, an AI-visibility source | OpenSEO MCP server (yours - self-hosted or hosted, your own DataForSEO key) | OpenSEO section below (`claude mcp add`, or your own instance) | `hoo-keyword-intel`, the weekly's rank read, `hoo-competitor-intel`, and `hoo-citation-tracker` behave exactly as before; the weekly says plainly that no independent rank source was present |
| Instant URL submission on ship (Bing, Yandex, other IndexNow engines) | `indexnow: {enabled, key}` in site-profile.yaml + `<key>.txt` at the site root | `/organic-os:setup` connector wizard (generate key, place file, verify by fetch) | Apply and publish work unchanged; changed URLs just wait to be crawled naturally |

## OpenSEO (the search-data adapter, optional)

[OpenSEO](https://github.com/every-app/open-seo) (MIT) is an open-source
SEO data tool - keyword research, rank tracking, competitor insights,
backlinks, AI visibility - whose data comes from DataForSEO under your
own API key. It exposes an MCP server, which makes it a second adapter in
the search-data capability slot (ADR-0009): skills reference the slot,
the probe finds what fills it, and no gate or contract logic names the
vendor. The decision and its boundaries are
[ADR-0012](../../docs/adr/0012-openseo-optional-data-tier.md).

What organic-os does and does not hold: you run OpenSEO yourself
(self-hosted from their repo, or their hosted tier) and you pay
DataForSEO directly - the costs are your own DataForSEO spend, metered by
them, not by anything here. organic-os stores no OpenSEO or DataForSEO
credential, adds no env vars, and makes no DataForSEO call of its own.
Without the adapter, every skill behaves exactly as it does today and
says so; with it, four touchpoints read richer data and name the adapter
as the source on every line that carries it.

Connect (hosted endpoint):

```
claude mcp add --transport http --scope user openseo https://app.openseo.so/mcp
```

First use runs their OAuth flow in the browser. For headless setups the
server accepts an API key from your OpenSEO account instead, sent as an
`Authorization: Bearer <key>` header (their keys start with `oseo_`) or
as an `x-api-key: <key>` header - configure it on the MCP entry, and
never store it anywhere organic-os reads. Self-hosting works the same
way against your own instance's `/mcp` endpoint.

Known tool surface as of 2026-09 (the tool prefix depends on the server
name you chose - typically `mcp__openseo__*`): `get_keyword_metrics`,
`get_serp_results`, `get_ranked_keywords`, `get_domain_overview`,
`get_domain_keyword_suggestions`, `get_backlinks_overview`,
`get_backlinks_profile`, `find_serp_competitors`, `get_rank_tracker`,
`create_rank_tracker`, `add_rank_tracking_keywords`,
`estimate_rank_tracker_cost`, `list_saved_keywords`, `list_projects`,
`get_project_context`, `whoami`.

Verify against the tools actually present in your session - re-verify,
do not pin. The surface changing shape is a named revisit trigger in
ADR-0012, and every skill acts on what the probe finds, never on this
list.

## IndexNow and Bing Webmaster

When `site-profile.yaml` has `indexnow: {enabled: true, key: ...}`,
`onsite-apply` and `onsite-publish` submit each successfully verified
changed URL via `hoo.indexnow.submit()` - one POST to
`api.indexnow.org/indexnow`, the single endpoint shared by Bing, Yandex,
and every other participating engine - and record the response status in
the outcome. Enablement runs through setup's connector wizard: generate a
32-char hex key, place `<key>.txt` (containing exactly the key) at the
site root, and the wizard verifies by fetching it before writing the
profile key. No account, no OAuth, no API key.

Bing Webmaster Tools itself is a different, honest story: site
verification there is a manual step in Bing's portal (bing.com/webmasters
- add the site, verify via DNS record, meta tag, or Bing's XML file, then
submit the sitemap once). organic-os claims no Bing Webmaster API
integration; IndexNow covers the submission path, and portal verification
stays a one-time manual task you do yourself.

Setup never stores a token, password, or credential in the brain repo or
this plugin's own files - only a record of what a probe found, and where
it ran. `/organic-os:setup`'s connector wizard writes each connector as
`{status, context, checked}` in `site-profile.yaml` via
`core.contracts.record_connector()` - `status` is `verified` (a live query
succeeded, not just tool presence), `unavailable`, or `declined`; `context`
is where the probe ran (`local-cli`, `cowork-cloud`, `ci`), since a
connector reachable from the setup session is not the same claim as one
reachable from wherever routines actually run. See `plugin/docs/
updating.md` for how this boundary holds across plugin updates.

## The redaction guard on outbound content

Anything a connector carries out of the brain - a proposal sent to Telegram,
a report document, an exported CSV, a board mirrored to Notion - is scanned
first by `core.redact`, and any finding is reported next to the content as a
single counts line with the matched value masked.

The guard is advisory and nothing more. It reports; it does not prevent. It
never blocks a send, never edits what you are sending, and never raises: if
the scan itself fails, the send goes ahead and says the scan did not run. So
a high-tier finding does not mean a leak was stopped - it means a
credential-shaped string was already in the outbound content, which is a
reason to rotate that credential and check what put it there. Equally, a
clean scan is not a clearance: it matches known shapes, so an unusual key
format or a value split across lines passes it in silence. Keeping
credentials out of the brain in the first place (see the paragraph above:
setup stores only what a probe found, never a value) is the control; this
scan is a second pair of eyes on the way out. See
[THREAT-MODEL.md](../../THREAT-MODEL.md).

## No-data escalation in the daily routine

`hoo-daily` needs GSC/GA4 to produce anything beyond "no sources
available." When neither connector is reachable for a given run, the
routine writes a specific `no-data:` signal line instead of the ordinary
"no notable movement" one, and counts how many days in a row that has
happened.

At three consecutive no-data days, `hoo-daily` sends one nudge through the
configured approval channel - a plain notification, not an approval item,
since there is no decision to approve, only a connector to fix: "3 daily
runs with no analytics data - GSC/GA4 are not reachable from this runtime.
Fix: <exact connect instruction>." The nudge is marked sent with a
`nudge-sent:` line inside that day's own signal file - no new state file -
and `hoo-daily` checks the last 7 days of signals for that marker before
sending again, so a persistently disconnected site gets nudged at most once
a week, not every single day.
