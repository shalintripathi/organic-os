---
name: hoo-import-audit
description: Use to import an external claude-seo audit report or action plan as gated proposals - "import this audit", "turn this audit report into proposals", /organic-os:import-audit. They audit, we operate.
---

# Import an external audit (claude-seo shape)

Turns a point-in-time audit report into organic-os proposals without
re-deriving the audit. The import trusts but attributes: findings keep
their original evidence labels ([Measured]/[Inference]/[Unverified]), the
original finding text rides in each proposal verbatim, and anything our
own audit dimensions would dispute is flagged for the human, never
silently rewritten.

1. Input: a file path from the user (a FULL-AUDIT-REPORT.md, an
   ACTION-PLAN.md, or similar markdown) or report text pasted in chat.
   Pasted text: write it to a temp file first. Read site-profile.yaml for
   the approval channel and the site URL.
2. Parse and rank with the import module - stdlib only, defensive by
   design (the format is theirs and may vary between versions; whatever
   matches no item pattern is preserved in `parsed["unparsed"]`, never
   dropped): `PYTHONPATH="$CLAUDE_PLUGIN_ROOT/lib" python3 -c` snippet
   importing `hoo.audit_import` - `parsed = parse_report(text)`, then
   `props = to_proposals(parsed, max_items=5)`.
3. Create each proposal via `create_item(kind=p["kind"], slug=p["slug"],
   title=p["title"], body=p["body"], target=<the finding's page URL if
   one appears in it, else parsed["source_meta"]["page_url"], else the
   profile site URL>, source="import-audit")`. `create_item` is the ONLY
   birth path - items are born `proposed` with an empty approvals list
   and are NEVER auto-approved; approval is the human's act, on the
   normal gate. Each body already carries the verbatim finding (quoted),
   its evidence label, the attribution line, and the dimension-mapping
   note: overlap names the onsite-audit dimension (skills/onsite-audit
   steps 3-4) via the `DIMENSION_HINTS` map in
   `plugin/lib/hoo/audit_import.py`; an llms.txt finding gets the
   deliberate-skip note (our position in plugin/docs/evidence.md); no
   overlap is marked external-only and imported as-is on the source
   audit's evidence.
4. Present a summary table in-session:
   - imported items: title, source severity, dimension mapping
     (dimension name | deliberate-skip | external-only)
   - skipped items: title + reason (ranked below the max_items cut;
     re-run with a higher max_items to import them)
   - unparsed excerpt count, with a pointer that the excerpts were
     preserved, not dropped
5. Rebuild the queue and route the approval notification through the
   configured channel exactly like any propose run: one
   `core.approval.notify_pending(<brain>, send)` call with the channel
   selection from skills/onsite-propose step 4. An item is
   marked notified ONLY after its send returns without raising, so a failed
   send is retried on the next run rather than lost, and re-runs never
   re-notify.
6. Append ONE signal recording the import: source audit date
   (`parsed["source_meta"]["audit_date"]`), items parsed, proposals
   created, skipped count, unparsed excerpt count.

Pattern credit: claude-seo (https://github.com/AgriciDaniel/claude-seo),
credited in README.md since v0.1.0. They audit, we operate.
