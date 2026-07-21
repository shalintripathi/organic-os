# Information map

Load-bearing facts that appear in more than one file drift unless something
guards them. This map names each fact, the single place it is canonical,
every file that quotes it, and what checks the quote: `audit-8` means
`scripts/audit.sh` check 8 verifies it mechanically on every run; `manual`
means a human consults this map when the canonical source changes.

| Fact | Canonical source | Quoted in | Checked by |
|---|---|---|---|
| Plugin version | `version` in `plugin/.claude-plugin/plugin.json` | `README.md` version badge; `.claude-plugin/marketplace.json` plugin entry; `CHANGELOG.md` release heading; `docs/images/install-2-install.svg`; `docs/images/install-4-form.svg` | audit-8 (badge, marketplace); manual (CHANGELOG, SVGs) |
| Test count | `python3 -m pytest --collect-only -q tests` | `README.md` tests badge; `README.md` inventory line | audit-8 |
| Skill / command / agent counts | Filesystem: dirs holding a `SKILL.md` under `plugin/skills/`; `plugin/commands/*.md`; `plugin/agents/*.md` | `README.md` inventory line; `docs/images/install-2-install.svg` | audit-8 (README); manual (SVG) |
| Approval TTL default (30 days) | `approval_ttl_days` in `plugin/lib/core/contracts.py` | `plugin/docs/approval-channels.md`; `README.md` human-gates paragraph; `docs/adr/0008-approval-expiry.md`; `plugin/docs/site-repo-contract.md` | manual |
| Schema version | `SCHEMA_VERSION` in `plugin/lib/core/contracts.py` | `plugin/docs/updating.md`; `plugin/docs/site-repo-contract.md` | manual |
| Install commands | Marketplace and plugin name in `.claude-plugin/marketplace.json` | `README.md`; `plugin/docs/getting-started.md`; `docs/images/install-1-marketplace.svg`; `docs/images/install-2-install.svg` | manual |
| Brain layout dirs | `DIRS` in `plugin/lib/core/init_site_repo.py` | `plugin/docs/site-repo-contract.md` layout block | manual |
| CMS adapter contract (`CmsAdapter` surface, `adapter_for`, supported types `wordpress` + `git-static`, `cms:` profile key, redirect modes in `capabilities()['redirects']`, media-alt modes in `capabilities()['media_alt']`) | `plugin/lib/onsite/cms.py` | `plugin/docs/site-repo-contract.md` cms key bullet; `plugin/docs/approval-channels.md` pr-merge section; `plugin/docs/getting-started.md` upgrade ladder; `plugin/skills/onsite-apply/SKILL.md` redirect-fixes + image-fix sections; `CONTRIBUTING.md` adapter section; `ROADMAP.md` v0.3 | manual |
| Notification taxonomy (what the operator hears and when) | "What you will hear and when" table in `plugin/docs/approval-channels.md` | `plugin/skills/onsite-apply/SKILL.md` outcome-summary step; `plugin/skills/onsite-publish/SKILL.md` outcome-summary step; `plugin/skills/hoo-daily/SKILL.md` daily-alert section; `plugin/skills/hoo-monday-report/SKILL.md` delivery step. README FAQ checked 2026-07-19: it does not mention notifications, nothing to sync there | manual |
| Audit-dimension list (page essentials: the seven checks, step 3; link health: the crawl-driven checks, step 4; signal severities for both) | numbered dimensions in `plugin/skills/onsite-audit/SKILL.md` (steps 3-4) | `plugin/skills/hoo-monthly-audit/SKILL.md` site-wide step; `docs/adr/0010-audit-dimension-responsibility.md` | manual |
| AI-surface referral list (chatgpt.com, perplexity.ai, gemini.google.com, copilot.microsoft.com, claude.ai; reviewed quarterly) | `ai_referrals` step (2.5) in `plugin/skills/hoo-daily/SKILL.md` | `plugin/skills/hoo-weekly/SKILL.md` week-over-week trend step; `plugin/skills/hoo-monday-report/SKILL.md` What-moved section | manual |
| Editorial policy keys and defaults (oversight_threshold 7, internal_links_min 0, external_links_max none, images_min 0, sourcing key-claims, require_reviewer_note false; sourcing modes key-claims / every-claim) | `EDITORIAL_DEFAULTS` + `editorial_policy` in `plugin/lib/core/contracts.py` | `plugin/lib/core/templates/site-profile.yaml` editorial block comment; `plugin/docs/site-repo-contract.md` editorial section; `plugin/agents/ce-qa.md` step 10 defaults | manual |
| Editorial-oversight factor list (claims density, YMYL adjacency, competitor mentions, legal/compliance surface, verbatim research survival) | oversight step in `plugin/agents/ce-editor.md` | `plugin/skills/onsite-publish/SKILL.md` gate step; `plugin/docs/site-repo-contract.md` editorial section | manual |
| Brief types (`explainer` via field absence, `comparison`) | `BRIEF_TYPES` in `plugin/lib/core/contracts.py` | `plugin/docs/site-repo-contract.md` items section; `plugin/skills/ce-produce/SKILL.md` comparison section; `plugin/skills/hoo-weekly/SKILL.md`; `plugin/skills/hoo-orchestrator/SKILL.md` step 4; `plugin/skills/hoo-keyword-intel/SKILL.md` cluster section | manual |
| Dimension-hints map (external audit finding keyword -> onsite-audit dimension; llms.txt -> deliberate-skip per `plugin/docs/evidence.md`) | `DIMENSION_HINTS` in `plugin/lib/hoo/audit_import.py` | `plugin/skills/hoo-import-audit/SKILL.md` create step; `plugin/docs/getting-started.md` claude-seo section | manual |
| PDF-converter probe list and order (pandoc, wkhtmltopdf, weasyprint, soffice) | `CONVERTERS` in `plugin/lib/core/report_render.py` | `plugin/skills/hoo-monday-report/SKILL.md` delivery step; `plugin/skills/setup/SKILL.md` scorecard check 8; `plugin/docs/routines.md` scorecard line | manual |
| userConfig field list (site_url, brand_name, approval_channel, telegram_bot_token, wp_app_password, wp_username; sensitive fields keychain-backed, env names `CLAUDE_PLUGIN_OPTION_<KEY_UPPERCASE>`) | `userConfig` in `plugin/.claude-plugin/plugin.json` | `README.md` install step 3; `plugin/docs/getting-started.md` enable-form section; `plugin/skills/setup/SKILL.md` Step 0.75; `plugin/docs/connectors.md` install-form line; `docs/images/install-4-form.svg` | manual |
| Anomaly-alert threshold default (40 percent vs the trailing 7-day median; noise floor: median below 10 skipped; baseline minimum: 4 prior daily signals; profile key `alerts: {threshold_pct: 40}`) | anomaly-check step (2.7) in `plugin/skills/hoo-daily/SKILL.md` | `plugin/docs/site-repo-contract.md` alerts key bullet | manual |
| Export file set (signals.csv date/metric/value from the daily's structured metric tokens; keywords.csv verbatim from history.tsv; outcomes.csv date/item/action/status/verified; run dir `runs/<UTCdate>-export/`) | `plugin/lib/core/export.py` | `plugin/skills/hoo-export/SKILL.md`; `plugin/docs/site-repo-contract.md` export run-dir section | manual |
| Citation-tracker default engine set (ChatGPT, Perplexity, Google AI Overviews, Gemini, Microsoft Copilot; profile key `citations: {engines: [...]}`) | Engine set section in `plugin/skills/hoo-citation-tracker/SKILL.md` | `plugin/docs/site-repo-contract.md` citations key bullet | manual |
| Plugin permissions and scopes (capability -> what it accesses -> credential -> where the credential lives) | `THREAT-MODEL.md` permissions table | `SECURITY.md` "What organic-os touches" + "What organic-os never does"; `README.md` human-gates paragraph | manual |
| Security-report + Code-of-Conduct enforcement contact (private security advisory on the repo, or the maintainer's GitHub profile @shalintripathi; never a personal email) | `CODE_OF_CONDUCT.md` Enforcement section | `SECURITY.md` "Reporting an issue"; `SUPPORT.md` security-issues section | manual |

Check 8 also verifies that every relative markdown link in the repo
resolves to an existing file, so cross-references never silently rot when
a file moves.

**The dev-cycle rule.** Any wave that touches a canonical source consults
this map before committing and updates every quoting file in the same
commit - a version bump, a test added, a renamed doc, a new skill all
land together with their quotes. When a change introduces a new
load-bearing fact (anything about to be quoted in a second file), add its
row here in that same commit, and prefer wiring it into audit check 8
over leaving it `manual`.

## Command reference

| Command | Description | File |
|---|---|---|
| `apply` | Execute approved on-page proposals against WordPress (refuses anything not approved) | [plugin/commands/apply.md](../plugin/commands/apply.md) |
| `citations` | Track AI answer-engine citations and share of voice for the profile's query set | [plugin/commands/citations.md](../plugin/commands/citations.md) |
| `competitors` | Run competitor content intelligence and surface gaps against the profile | [plugin/commands/competitors.md](../plugin/commands/competitors.md) |
| `daily` | Run the daily organic signal pull (append-only, never mutates) | [plugin/commands/daily.md](../plugin/commands/daily.md) |
| `export` | Export the brain to CSV for Sheets, Looker Studio, or any BI tool | [plugin/commands/export.md](../plugin/commands/export.md) |
| `image` | Create the featured image / social card for a drafted post | [plugin/commands/image.md](../plugin/commands/image.md) |
| `import-audit` | Import an external claude-seo audit report as gated proposals | [plugin/commands/import-audit.md](../plugin/commands/import-audit.md) |
| `keywords` | Run tiered keyword intelligence - ideas, competitor gaps, or CSV import | [plugin/commands/keywords.md](../plugin/commands/keywords.md) |
| `measure` | Measure applied or published on-page changes at day 7 and day 28 | [plugin/commands/measure.md](../plugin/commands/measure.md) |
| `monday-report` | Write a stakeholder-shareable weekly summary of what moved, shipped, and needs a decision | [plugin/commands/monday-report.md](../plugin/commands/monday-report.md) |
| `monthly-audit` | Run the monthly deep organic audit across all eight specialists | [plugin/commands/monthly-audit.md](../plugin/commands/monthly-audit.md) |
| `onsite-audit` | Audit on-page SEO for a URL or a whole site section (read-only) | [plugin/commands/onsite-audit.md](../plugin/commands/onsite-audit.md) |
| `produce` | Draft a publish-ready post from an approved content brief (six-stage pipeline) | [plugin/commands/produce.md](../plugin/commands/produce.md) |
| `propose` | Turn audit findings or signals into concrete gated on-page change proposals | [plugin/commands/propose.md](../plugin/commands/propose.md) |
| `publish` | Publish an approved, drafted content item to WordPress (refuses unapproved items) | [plugin/commands/publish.md](../plugin/commands/publish.md) |
| `reset` | Guided teardown of an organic-os site - what gets deregistered automatically, what you must delete or revoke yourself, and why | [plugin/commands/reset.md](../plugin/commands/reset.md) |
| `setup` | Onboard a site into organic-os (interview + brain scaffold + routines) | [plugin/commands/setup.md](../plugin/commands/setup.md) |
| `sites` | Manage organic-os sites - add another website, switch the active site, or show registry status | [plugin/commands/sites.md](../plugin/commands/sites.md) |
| `start` | The guided front door - run this first | [plugin/commands/start.md](../plugin/commands/start.md) |
| `status` | Show organic-os site status - pending approvals, recent signals, next routine | [plugin/commands/status.md](../plugin/commands/status.md) |
| `task-board` | Show the organic-os work queue and mirror it to Notion when available | [plugin/commands/task-board.md](../plugin/commands/task-board.md) |
| `weekly` | Run the weekly organic health check + reflection | [plugin/commands/weekly.md](../plugin/commands/weekly.md) |
