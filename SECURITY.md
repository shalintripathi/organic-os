# Security

For the full permissions table, the blast radius of a mis-approval, and the
release-integrity model, see [THREAT-MODEL.md](THREAT-MODEL.md). This file
covers what organic-os touches, what it never does, the env-file convention,
and how to report an issue.

## What organic-os touches

- **Your site repo (the brain).** Everything organic-os knows about a site
  - signals, briefs, proposals, approvals, the skillbook, ADRs - lives in a
  git repo or local folder you own. organic-os reads and writes it through
  `lib/core` only.
- **Your WordPress site, through your own Application Password.** Writes
  happen over HTTPS via the WordPress REST API, authenticated as a
  dedicated Editor-role user you create (`plugin/docs/credentials/wordpress.md`).
  organic-os never has Administrator access unless you explicitly grant it,
  and every write is gated on a recorded approval (`plugin/docs/site-repo-contract.md`).
- **APIs you configured yourself.** GA4, GSC, Notion, Slack, Canva via your
  own claude.ai connectors or MCP servers; Google Ads via a developer token
  and OAuth credentials you generate (`plugin/docs/credentials/google-ads-token.md`).
  organic-os calls whichever of these you set up and states plainly which
  ones it found; it never assumes a credential exists.

## What organic-os never does

- **No SERP or autocomplete scraping.** Ever, by design (see ADR-0006). All
  ranking and citation data comes from APIs and connectors you authorized.
- **No telemetry, no phone-home.** Nothing about your site, your usage, or
  your credentials is sent anywhere outside the APIs you configured.
- **No secrets stored in any repo.** Credentials live in
  `~/.config/organic-os/<site>.env` files (chmod 600) or in your platform's
  own credential storage (claude.ai connectors, plugin userConfig where
  keychain-backed). A site repo stores only *references* to which
  credentials exist (`site-profile.yaml connectors:` and `google_ads:
  status:`), never a value. `scripts/audit.sh` runs a secret-pattern scan
  on every commit to this repo as a second layer of defense.
- **No mutation without an approval record.** The executor checks a
  proposal's status before every write and refuses anything that is not
  `approved` (or, for post-approval stages like publishing a drafted brief,
  that lacks an `approved` decision in its lineage). This is enforced in
  code (`core.contracts.require_approved` /
  `core.contracts.require_approval_lineage`), not by convention - a
  hand-edited status field without a matching `approvals:` entry still
  fails the gate. Don't take that claim on faith: verify the gate yourself
  with `./scripts/verify-gates.sh` - it red-teams `require_approved`,
  `set_status`, `require_approval_lineage`, and `check_schema` against a
  throwaway brain repo and prints PASS/FAIL per probe.

## The env-file convention

Every credential organic-os needs is stored as an environment file, one per
site, at `~/.config/organic-os/<site-slug>.env`, created with `chmod 600`
so only the owning user can read it. Nothing under that directory is ever
committed, referenced by path outside your own machine, or printed into a
transcript by any skill. If you see a skill about to echo a credential
value, stop it - that is not expected behavior.

## Verified install channels

There are exactly two official sources for organic-os:

- **This repository:** `https://github.com/shalintripathi/organic-os`.
- **The plugin marketplace install documented in the README:**
  `/plugin marketplace add shalintripathi/organic-os`, which resolves to
  the same repository.

There is no npm package, no installer website, no hosted service, and no
other mirror. Anything else claiming to be organic-os - a package registry
entry, a lookalike repository, a paid tier - is unofficial and did not come
from the maintainer. If you find one, report it the same way as a security
issue (below).

## Reporting an issue

For an ordinary bug, open a GitHub issue at
`https://github.com/shalintripathi/organic-os/issues` using the bug-report
form. For a security or credential-handling finding, do not open a public
issue: open a private security advisory on the repository (GitHub > Security >
Advisories), or contact the maintainer through their GitHub profile
(@shalintripathi). Either way, keep the actual secret value out of the report
and describe the pattern instead.
