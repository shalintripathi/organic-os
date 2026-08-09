## What this changes

<!-- One or two sentences. Link an issue if there is one. -->

## Checklist

- [ ] `python3 -m pytest tests/ -q` passes
- [ ] `./scripts/audit.sh` is clean
- [ ] `./scripts/verify-gates.sh` is clean
- [ ] No business data added (no `site-profile.yaml`, keyword lists, brand
      rulebooks, competitor lists, or skillbook content - see
      [CONTRIBUTING.md's data boundary](../CONTRIBUTING.md#the-data-boundary-hard-rule))
- [ ] No secrets (API keys, tokens, passwords, `.env` files)
- [ ] Commits are signed off (DCO): `git commit -s` adds the
      `Signed-off-by` trailer - we use DCO, not a CLA (see
      [CONTRIBUTING.md's DCO section](../CONTRIBUTING.md#sign-your-commits-dco))
- [ ] Every evidence/claim/statistic in this PR is sourced (a link, a study,
      a real citation)
- [ ] No em-dashes; no hype words (seamless, robust, delve, transform,
      unlock, supercharge, cutting-edge, world-class, best-in-class,
      synergy, holistic, revolutionary, and similar)
- [ ] Adapter PRs only: `capabilities()` declares honestly what the adapter
      cannot do (`needs_human`), and a fake-transport test file proves the
      `CmsAdapter` contract (see
      [CONTRIBUTING.md's adapter section](../CONTRIBUTING.md#contributing-a-cms-adapter))
