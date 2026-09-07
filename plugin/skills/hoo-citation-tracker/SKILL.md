---
name: hoo-citation-tracker
description: Use to measure AI answer-engine visibility - "are we cited by ChatGPT/Perplexity", "AI share of voice", /organic-os:citations, or the weekly routine's citation step.
---

# AI citation tracking

1. Read profile: keywords.targets (the query set), competitors, site url,
   and the optional `citations: {engines: [...]}` key (see Engine set
   below).
2. For each query (cap 20 per run; rotate through the set across runs),
   ask each engine in the engine set that is actually reachable from this
   session. Sources in order of preference: an authorized AI-search
   connector; the search-data adapter's AI-visibility read, when its
   tools are present in this session (the search-data slot, ADR-0009 in
   the repo; the known adapter is OpenSEO - see
   `$CLAUDE_PLUGIN_ROOT/docs/connectors.md` - licensed data, and every
   line carrying it names the adapter as its source); WebSearch with
   engine-targeted queries; plain WebSearch otherwise. Never scrape
   engines through automation that violates their ToS.
3. Record per query: engine | our domain mentioned? | cited (linked)? |
   position (only when cited - the ordinal below) | sentiment (only when
   mentioned - the label plus its evidence quote, below) | competitors
   mentioned | answer summary (<=30 words).
4. Metrics: mention rate, citation rate, share of voice vs competitors
   (mentions of us / mentions of anyone tracked).
5. Persist to runs/YYYYMMDD-citations/ + append one signal line with the
   headline movement vs the previous run (diff the last runs/ folder).
6. New citation appearing or disappearing on a money query -> P1 signal.
7. When `runs/<date>-ai-baseline/REPORT.md` exists in the brain (written by
   `/organic-os:setup`'s AI-visibility baseline step), compare this run's
   headline numbers against it and report movement, not just this run's
   absolutes - see Baseline comparison below for what movement now covers.

## Position within the answer

When the brand IS cited, record where it sits in the answer. One of four
ordinal values, best to worst:

- `lead-answer` - the answer's opening or primary recommendation is
  built on the brand; a reader who stops after the first paragraph has
  seen it.
- `supporting-mention` - the brand is named with substance in the body
  of the answer, as one of the inputs the answer actually uses.
- `listed-among-others` - the brand appears only inside a list or
  comparison of alternatives, with nothing said about it specifically.
- `footnote-link` - the brand appears only as a cited source link; the
  answer text itself never names it.

An uncited mention gets no position value - position describes where a
citation sits, and recording one without a citation would overstate the
result.

## Sentiment of the mention

When the brand is mentioned, judge the sentiment of that mention from the
answer text: `positive`, `neutral`, or `mixed-negative`. Every sentiment
label MUST carry the exact quoted phrase from the answer that justifies
it - never a bare label without the quote. The quote is the evidence and
the check: anyone reading the report can re-judge the call from the same
words. If no phrase in the answer supports a judgment either way, the
label is `neutral` with the brand's surrounding sentence as the quote.

## Baseline comparison and movement

The per-query table in this run's REPORT.md carries the position and
sentiment columns from step 3. The baseline REPORT.md format extends the
same way, additively: new baselines written from now on include both
columns; old baselines without them compare on presence only, and the
movement section states that plainly ("baseline predates
position/sentiment fields - movement reported on presence only").

Movement reporting covers three layers, deepest available first:

- Presence: cited or not, mentioned or not, vs the baseline or the
  previous run.
- Position: when both runs have position values, report the shift by
  name - "cited, and moved from listed-among-others to lead answer".
- Sentiment: when both runs have sentiment values and the label changed,
  report it with the new evidence quote attached - "sentiment shifted
  from neutral to mixed-negative; quote attached".

## Honesty rules

- This method samples, it does not measure. A run covers the queries it
  checked on the engines it could reach, nothing more - never let a
  report imply broader coverage than that.
- Every REPORT.md lists which engines were actually reachable from the
  session that ran it, and which configured engines were not.
- Sentiment is a judgment call and is labeled as such in the report; the
  recorded quote is the check on that judgment.
- Position and sentiment are recorded only from answer text actually
  read this run - never inferred, never carried forward from a previous
  run.

## Engine set (BYO, no tiers)

The default engine set, canonical here (see docs/INFORMATION-MAP.md in
the repo): ChatGPT, Perplexity, Google AI Overviews, Gemini, Microsoft
Copilot.

The set is profile-configurable via the additive
`citations: {engines: [...]}` key in site-profile.yaml (absence means
the default set; `schema_version` stays 1 - documented in
site-repo-contract.md). Each listed engine is checked only if it is
reachable from the session running the tracker - an unreachable engine
is listed as unreachable in the report, never silently skipped and never
guessed at. Users add engines the same way: one more list entry, checked
through the same connector-or-WebSearch path under the same ToS rule.
No tiers, no per-engine pricing - commercial AI-visibility tools sell
extra engines, per-answer position, and sentiment as paid add-on tiers;
here they are the same skill reading the user's own reachable surfaces,
inside ADR-0006's no-scraping rule (docs/adr/0006 in the repo).
