# ADR-0013: Do not cross-list organic-os skills on the npx skills registry

- Status: accepted
- Date: 2026-09-27
- Decision makers: Shivaa Tripathi (human), Claude (agent); investigation by
  @ayushdwivedi-stack

## Context

ADR-0012 carried this investigation as a follow-up task from the OpenSEO
study: can organic-os skills be listed on the `npx skills` registry
(skills.sh, maintained by Vercel Labs) alongside `every-app/open-seo`'s own
skills, without forking content, and without conflicting with the Claude
plugin marketplace (ADR-0001) staying the canonical install path?

`npx skills` uses GitHub itself as the registry. There is no separate
submission, approval, or central index: any public repo with a `SKILL.md`
(YAML frontmatter - `name`, `description`) at the expected path becomes
installable via `npx skills add owner/repo --skill <name>`. "Listing" is not
a distinct action from being a public repo with correctly-shaped skill
files - organic-os's skills already carry this exact frontmatter shape
(confirmed directly in `plugin/skills/onsite-audit/SKILL.md`), so no
reformatting or content fork would be required to become installable this
way.

`every-app/open-seo` uses the registry for skills that are close to
self-contained: each is a `SKILL.md` of prompt instructions with no
dependency on a supporting Python/JS library or persistent local state
beyond what the skill itself describes.

organic-os's skills are not self-contained in that sense. `onsite-audit`,
for example, depends on `plugin/lib/onsite` (`linkgraph.py`'s `crawl()` /
`analyze()`), `plugin/lib/core`'s contract layer, and - for anything past
the credential-free public checks - a scaffolded brain repo
(`core.init_site_repo`, ADR-0002). A bare `npx skills add
shalintripathi/organic-os --skill onsite-audit` would install the markdown
instructions only; the skill would reference Python modules and a brain
repo structure that were never installed alongside it, and would fail or
silently degrade in ways the registry install path gives no signal about.

## Decision

Do not cross-list organic-os skills on the `npx skills` registry.

The Claude plugin marketplace (ADR-0001) remains the canonical supported install path.
`npx skills add` is left available to anyone who runs it against this repo
directly - GitHub-as-registry means that path cannot be blocked - but
organic-os will not advertise it, document it, or optimize skill files for
it.

## Not adopted, and why

- **Listing with a documentation caveat instead of rejecting outright.**
  Considered: list the skills but prominently document that they require
  the full plugin install. Rejected because the registry's install
  surface (`npx skills add owner/repo --skill <name>`) gives a user no
  natural place to see that caveat before running the command - the
  failure mode (a skill that references missing modules) would be the
  first thing they see, not a warning.
- **Splitting out a registry-compatible subset.** Considered: identify any
  organic-os skill with no `plugin/lib` import (the content-engine skills,
  e.g. `ce-produce`, `ce-image`) and list only those. On review, "no lib
  import" does not mean self-contained: `ce-produce` calls the contract CLI
  (`python3 -m core status`, `core.decisions.search`) and assumes a
  scaffolded brain repo's `briefs/` and `runs/` layout; `ce-image` consumes
  a draft file that only exists because `ce-produce` wrote it inside that
  same structure. Every skill in `plugin/skills/`, lib-importing or not,
  assumes the brain-repo contract (ADR-0002) is present. None qualify as
  registry-installable standalone today.

## Consequences

- No new distribution surface to maintain; zero runtime or maintenance
  cost, matching ADR-0012's framing that a second listing is only worth it
  at zero cost.
- organic-os stays discoverable only through the Claude plugin marketplace
  and its own README/repo, unlike `open-seo`, which benefits from the
  registry's cross-harness reach (Cursor, Codex, etc. per the registry's
  own docs).
- Nothing prevents a future skill that genuinely has no `plugin/lib` or
  brain-repo dependency from being listed individually if one is ever
  built with that constraint in mind from the start.

## Revisit triggers

- A skill is added or refactored to have zero dependency on `plugin/lib`
  or a brain repo (a true standalone prompt skill): re-evaluate listing
  that skill alone.
- The `npx skills` registry adds a documented way to declare install-time
  dependencies or prerequisites beyond the `SKILL.md` itself: re-evaluate,
  since that would close the exact gap this ADR rejects on.
