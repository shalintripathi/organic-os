import datetime as dt
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

import pytest  # noqa: E402
import yaml  # noqa: E402
from core.init_site_repo import init_site_repo  # noqa: E402
from core import contracts as C  # noqa: E402


@pytest.fixture
def root(tmp_path):
    return init_site_repo(tmp_path / "brain", "https://ex.com", "Ex")


def test_append_signal_is_append_only(root):
    C.append_signal(root, "clicks dropped 12% on /pricing", date="2026-07-18")
    C.append_signal(root, "second observation", date="2026-07-18")
    text = (root / "signals" / "2026-07-18.md").read_text()
    assert text.index("clicks dropped") < text.index("second observation")


def test_create_and_load_proposal(root):
    p = C.create_item(root, kind="onpage-fix", slug="pricing-title",
                      title="Rewrite /pricing title tag",
                      body="Change title to 'Pricing - Ex'.",
                      target="https://ex.com/pricing", source="signal:2026-07-18")
    item = C.load_item(p)
    assert item["meta"]["status"] == "proposed"
    assert item["meta"]["kind"] == "onpage-fix"
    assert "Rewrite /pricing" in item["meta"]["title"]


def test_create_item_brief_type_comparison(root):
    p = C.create_item(root, kind="content-brief", slug="x-vs-y",
                      title="X vs Y", body="b", target="https://ex.com/x-vs-y",
                      source="s", brief_type="comparison")
    assert C.load_item(p)["meta"]["brief_type"] == "comparison"


def test_create_item_brief_type_absent_by_default(root):
    p = C.create_item(root, kind="content-brief", slug="plain", title="t",
                      body="b", target="https://ex.com/plain", source="s")
    assert "brief_type" not in C.load_item(p)["meta"]  # absence means explainer


def test_create_item_brief_type_unknown_raises(root):
    with pytest.raises(C.ContractError):
        C.create_item(root, kind="content-brief", slug="bad", title="t",
                      body="b", target="", source="s", brief_type="listicle")
    assert list((root / "briefs").glob("*.md")) == []


def test_create_item_brief_type_wrong_kind_raises(root):
    with pytest.raises(C.ContractError):
        C.create_item(root, kind="onpage-fix", slug="fix", title="t",
                      body="b", target="", source="s", brief_type="comparison")
    assert list((root / "proposals").glob("*.md")) == []


def test_status_lifecycle_enforced(root):
    p = C.create_item(root, kind="onpage-fix", slug="x", title="t", body="b",
                      target="https://ex.com/x", source="s")
    with pytest.raises(C.ContractError):
        C.set_status(p, "applied", actor="agent")          # cannot skip approval
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "applied", actor="agent")
    meta = C.load_item(p)["meta"]
    assert meta["status"] == "applied"
    assert meta["approvals"][0]["actor"] == "shivaa"


def test_require_approved_gate(root):
    p = C.create_item(root, kind="publish", slug="post-1", title="t", body="b",
                      target="", source="s")
    with pytest.raises(C.ContractError):
        C.require_approved(p)
    C.set_status(p, "approved", actor="shivaa", channel="pr-merge")
    C.require_approved(p)  # no raise


def test_skillbook_append_and_update(root):
    sid = C.skillbook_append(root, "Answer capsule under 60 words lifts snippet capture",
                             evidence="strong", source="princeton-geo")
    assert sid == "S-001"
    sid2 = C.skillbook_append(root, "Second lesson", evidence="anecdotal", source="operator")
    assert sid2 == "S-002"
    C.skillbook_update(root, "S-001", helpful=1)
    book = (root / "skillbook.md").read_text()
    assert "[helpful: 1, harmful: 0" in book.split("S-001")[1].split("\n")[0]


def test_skillbook_deprecate_not_delete(root):
    C.skillbook_append(root, "old idea", evidence="anecdotal", source="x")
    C.skillbook_update(root, "S-001", deprecate=True)
    line = [l for l in (root / "skillbook.md").read_text().splitlines() if "S-001" in l][0]
    assert line.startswith("~~") or "DEPRECATED" in line


def test_skillbook_update_deprecated_entry_raises(root):
    C.skillbook_append(root, "old idea", evidence="anecdotal", source="x")
    C.skillbook_update(root, "S-001", deprecate=True)
    before = (root / "skillbook.md").read_text()
    with pytest.raises(C.ContractError):
        C.skillbook_update(root, "S-001", helpful=1)
    assert (root / "skillbook.md").read_text() == before  # line unchanged


# -- skillbook staleness -------------------------------------------------------

def _set_stale_days(root, value):
    p = root / "site-profile.yaml"
    data = yaml.safe_load(p.read_text()) or {}
    data["skillbook"] = {"stale_days": value}
    p.write_text(yaml.safe_dump(data))


def _confirmed_on(root, sid, date):
    """Simulates an entry last confirmed on `date` (a datetime.date)."""
    book = root / "skillbook.md"
    out = []
    for line in book.read_text().splitlines():
        if line.startswith(f"{sid} "):
            line = line.replace(
                line.split("last-confirmed: ")[1].split("]")[0], date.isoformat())
        out.append(line)
    book.write_text("\n".join(out) + "\n")


def _aged_entry(root, evidence, days_ago, today):
    sid = C.skillbook_append(root, f"a {evidence} lesson", evidence=evidence,
                             source="test")
    _confirmed_on(root, sid, today - dt.timedelta(days=days_ago))
    return sid


TIERS = [("anecdotal", 90), ("moderate", 180), ("strong", 365)]


@pytest.mark.parametrize("evidence,threshold", TIERS)
def test_entry_exactly_at_its_threshold_is_not_stale(root, evidence, threshold):
    today = dt.date(2026, 7, 23)
    _aged_entry(root, evidence, threshold, today)
    assert C.skillbook_stale(root, today=today) == []


@pytest.mark.parametrize("evidence,threshold", TIERS)
def test_entry_one_day_past_its_threshold_is_stale(root, evidence, threshold):
    today = dt.date(2026, 7, 23)
    sid = _aged_entry(root, evidence, threshold + 1, today)
    stale = C.skillbook_stale(root, today=today)
    assert [e["id"] for e in stale] == [sid]
    entry = stale[0]
    assert entry["evidence"] == evidence
    assert entry["threshold"] == threshold
    assert entry["days_stale"] == threshold + 1
    assert entry["last_confirmed"] == (today - dt.timedelta(days=threshold + 1)).isoformat()
    assert f"a {evidence} lesson" in entry["text"]


def test_deprecated_entry_is_never_returned_as_stale(root):
    today = dt.date(2026, 7, 23)
    sid = _aged_entry(root, "anecdotal", 900, today)
    C.skillbook_update(root, sid, deprecate=True)
    _confirmed_on(root, f"~~{sid}", today - dt.timedelta(days=900))
    assert C.skillbook_stale(root, today=today) == []


def test_profile_stale_days_override_is_honoured(root):
    today = dt.date(2026, 7, 23)
    sid = _aged_entry(root, "strong", 40, today)
    assert C.skillbook_stale(root, today=today) == []   # 40 days < default 365
    _set_stale_days(root, {"strong": 30})
    stale = C.skillbook_stale(root, today=today)
    assert [e["id"] for e in stale] == [sid]
    assert stale[0]["threshold"] == 30


def test_stale_days_partial_override_keeps_other_tiers_at_defaults(root):
    _set_stale_days(root, {"anecdotal": 7})
    assert C.skillbook_stale_days(root) == {"anecdotal": 7, "moderate": 180,
                                            "strong": 365}


def test_stale_days_defaults_without_a_profile_section(root):
    assert C.skillbook_stale_days(root) == C.STALE_DEFAULTS


@pytest.mark.parametrize("bad", [{"strong": 0}, {"strong": -5}, {"strong": "many"},
                                 {"strong": True}, {"anecdotal": 1.5}])
def test_malformed_stale_days_value_raises_naming_the_key(root, bad):
    _set_stale_days(root, bad)
    with pytest.raises(C.ContractError) as exc:
        C.skillbook_stale(root)
    assert f"skillbook.stale_days.{list(bad)[0]}" in str(exc.value)


def test_stale_days_not_a_mapping_raises(root):
    _set_stale_days(root, 90)
    with pytest.raises(C.ContractError) as exc:
        C.skillbook_stale_days(root)
    assert "skillbook.stale_days" in str(exc.value)


def test_empty_skillbook_has_nothing_stale(root):
    assert C.skillbook_stale(root) == []


def test_stale_list_is_most_stale_first(root):
    today = dt.date(2026, 7, 23)
    fresher = _aged_entry(root, "anecdotal", 100, today)
    older = _aged_entry(root, "anecdotal", 400, today)
    assert [e["id"] for e in C.skillbook_stale(root, today=today)] == [older, fresher]


def test_create_item_rejects_path_escape_slug(root):
    with pytest.raises(C.ContractError):
        C.create_item(root, kind="onpage-fix", slug="../../escape", title="t", body="b",
                      target="", source="s")
    assert list((root / "proposals").glob("*.md")) == []
    assert list(root.rglob("escape.md")) == []


def test_set_status_records_note_only_when_given(root):
    p = C.create_item(root, kind="onpage-fix", slug="with-note", title="t", body="b",
                      target="https://ex.com/n", source="s")
    C.set_status(p, "approved", actor="op", channel="in-session", note="looks good")
    assert C.load_item(p)["meta"]["approvals"][0]["note"] == "looks good"

    q = C.create_item(root, kind="onpage-fix", slug="no-note", title="t", body="b",
                      target="https://ex.com/m", source="s")
    C.set_status(q, "approved", actor="op", channel="in-session")
    assert "note" not in C.load_item(q)["meta"]["approvals"][0]


def test_rebuild_queue_flags_approval_entry_missing_decision(root):
    p = C.create_item(root, kind="onpage-fix", slug="bad-approval", title="t", body="b",
                      target="https://ex.com/b", source="s")
    raw = p.read_text()
    assert "approvals: []" in raw, "unexpected frontmatter shape, cannot hand-write entry"
    p.write_text(raw.replace(
        "approvals: []",
        "approvals:\n- actor: someone\n  channel: manual-edit\n"
        "  at: '2026-07-19T00:00:00Z'"))
    C.rebuild_queue(root)
    q = (root / "approvals" / "queue.md").read_text()
    assert "MALFORMED-APPROVAL" in q
    assert "entry missing decision field" in q
    assert p.name in q


def test_queue_index_lists_pending(root):
    C.create_item(root, kind="content-brief", slug="guide", title="A guide", body="b",
                  target="", source="s")
    C.rebuild_queue(root)
    q = (root / "approvals" / "queue.md").read_text()
    assert "A guide" in q and "content-brief" in q


def test_failed_status_only_from_approved(root):
    p = C.create_item(root, kind="onpage-fix", slug="verify-fail", title="t", body="b",
                      target="https://ex.com/v", source="s")
    with pytest.raises(C.ContractError):
        C.set_status(p, "failed", actor="agent")           # proposed -> failed illegal
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "failed", actor="agent")               # approved -> failed legal
    assert C.load_item(p)["meta"]["status"] == "failed"

    q = C.create_item(root, kind="onpage-fix", slug="already-applied", title="t", body="b",
                      target="https://ex.com/a", source="s")
    C.set_status(q, "approved", actor="shivaa", channel="in-session")
    C.set_status(q, "applied", actor="agent")
    with pytest.raises(C.ContractError):
        C.set_status(q, "failed", actor="agent")           # applied -> failed illegal


def test_partially_applied_from_approved_stores_status_note(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial", title="t", body="b",
                      target="https://ex.com/p", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "partially-applied", actor="agent",
                 note="title and meta written; plugin settings need an admin")
    meta = C.load_item(p)["meta"]
    assert meta["status"] == "partially-applied"
    assert meta["status_note"] == "title and meta written; plugin settings need an admin"


def test_partially_applied_to_applied_legal(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial-done", title="t", body="b",
                      target="https://ex.com/pd", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "partially-applied", actor="agent")
    C.set_status(p, "applied", actor="shivaa", channel="in-session")
    assert C.load_item(p)["meta"]["status"] == "applied"


def test_partially_applied_to_failed_legal(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial-rollback", title="t", body="b",
                      target="https://ex.com/pr", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "partially-applied", actor="agent")
    C.set_status(p, "failed", actor="agent")
    assert C.load_item(p)["meta"]["status"] == "failed"


def test_proposed_to_partially_applied_raises(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial-skip", title="t", body="b",
                      target="https://ex.com/ps", source="s")
    with pytest.raises(C.ContractError):
        C.set_status(p, "partially-applied", actor="agent")


def test_partially_applied_to_published_raises(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial-pub", title="t", body="b",
                      target="https://ex.com/pp", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "partially-applied", actor="agent")
    with pytest.raises(C.ContractError):
        C.set_status(p, "published", actor="agent")


def test_queue_shows_partially_applied_with_note(root):
    p = C.create_item(root, kind="onpage-fix", slug="partial-queued", title="Half done",
                      body="b", target="https://ex.com/pq", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "partially-applied", actor="agent",
                 note="canonical pending: needs an admin")
    C.rebuild_queue(root)
    q = (root / "approvals" / "queue.md").read_text()
    assert "PARTIAL" in q
    assert "Half done" in q
    assert "canonical pending: needs an admin" in q


def test_approval_lineage_passes_for_drafted_after_approval(root):
    p = C.create_item(root, kind="content-brief", slug="lineage-ok", title="t", body="b",
                      target="", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "drafted", actor="agent")
    C.require_approval_lineage(p)  # no raise: approved decision is in the lineage


def test_approval_lineage_rejected_item_raises(root):
    p = C.create_item(root, kind="content-brief", slug="lineage-rejected", title="t", body="b",
                      target="", source="s")
    C.set_status(p, "rejected", actor="shivaa", channel="in-session")
    with pytest.raises(C.ContractError):
        C.require_approval_lineage(p)


def test_approval_lineage_fresh_proposed_raises(root):
    p = C.create_item(root, kind="content-brief", slug="lineage-fresh", title="t", body="b",
                      target="", source="s")
    with pytest.raises(C.ContractError):
        C.require_approval_lineage(p)


# -- illegal birth states ------------------------------------------------------

def _hand_birth(root, status, slug="born-wrong", kind="content-brief"):
    """Simulates the field bug: an item file that entered the brain with a
    non-proposed status and an empty approvals list (born outside create_item).
    Such an item can neither be approved (drafted -> approved is illegal) nor
    pass a lineage gate, so it jams the pipeline until repaired."""
    p = C.create_item(root, kind=kind, slug=slug, title="t", body="b",
                      target="", source="s")
    raw = p.read_text()
    assert "status: proposed" in raw, "unexpected frontmatter shape"
    p.write_text(raw.replace("status: proposed", f"status: {status}", 1))
    return p


def test_rebuild_queue_flags_born_drafted_with_no_approvals(root):
    p = _hand_birth(root, "drafted")
    C.rebuild_queue(root)
    q = (root / "approvals" / "queue.md").read_text()
    assert "ILLEGAL-STATE" in q
    assert p.name in q
    assert "born drafted with no approvals" in q
    assert "reset-to-proposed" in q  # the repair command is named inline


def test_rebuild_queue_does_not_flag_legitimate_items(root):
    C.create_item(root, kind="onpage-fix", slug="legit-proposed", title="t",
                  body="b", target="https://ex.com/lp", source="s")
    p = C.create_item(root, kind="content-brief", slug="legit-drafted", title="t",
                      body="b", target="", source="s")
    C.set_status(p, "approved", actor="op", channel="in-session")
    C.set_status(p, "drafted", actor="agent")
    C.rebuild_queue(root)
    q = (root / "approvals" / "queue.md").read_text()
    assert "ILLEGAL-STATE" not in q


def test_reset_to_proposed_repairs_born_drafted_item(root):
    p = _hand_birth(root, "drafted")
    C.reset_to_proposed(p, actor="operator")
    meta = C.load_item(p)["meta"]
    assert meta["status"] == "proposed"
    assert "born drafted" in meta["status_note"]
    # the normal lifecycle works again from here
    C.set_status(p, "approved", actor="op", channel="in-session")
    assert C.load_item(p)["meta"]["status"] == "approved"


def test_reset_to_proposed_records_actor_and_note(root):
    p = _hand_birth(root, "applied", slug="born-applied", kind="onpage-fix")
    C.reset_to_proposed(p, actor="operator",
                        note="import script wrote status directly")
    note = C.load_item(p)["meta"]["status_note"]
    assert "operator" in note
    assert "import script wrote status directly" in note


def test_reset_to_proposed_refuses_item_with_approval_history(root):
    p = C.create_item(root, kind="onpage-fix", slug="has-history", title="t",
                      body="b", target="https://ex.com/h", source="s")
    C.set_status(p, "approved", actor="op", channel="in-session")
    with pytest.raises(C.ContractError, match="approval history"):
        C.reset_to_proposed(p, actor="operator")
    assert C.load_item(p)["meta"]["status"] == "approved"  # untouched


def test_rejection_auto_records_exactly_one_decision(root):
    p = C.create_item(root, kind="onpage-fix", slug="pricing-title",
                      title="Rewrite /pricing title tag", body="b",
                      target="https://ex.com/pricing", source="s")
    C.set_status(p, "rejected", actor="shivaa", channel="in-session",
                 note="legal owns that page's wording this quarter")
    files = list((root / "decisions").glob("*.md"))
    assert len(files) == 1
    doc = C.load_item(files[0])
    assert doc["meta"]["choice"] == "rejected"
    assert doc["meta"]["actor"] == "shivaa"
    assert p.name in doc["meta"]["item"]          # the decision names the item
    assert "pricing" in doc["meta"]["scope"]      # scope derived from the title
    assert "legal owns that page" in doc["body"]  # the reason is the rationale


def test_approval_records_no_decision_file(root):
    p = C.create_item(root, kind="onpage-fix", slug="approved-fix", title="t",
                      body="b", target="https://ex.com/a", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "applied", actor="agent")
    assert list((root / "decisions").glob("*.md")) == []


def test_reset_to_proposed_already_proposed_refuses(root):
    p = C.create_item(root, kind="onpage-fix", slug="fine-as-is", title="t",
                      body="b", target="https://ex.com/f", source="s")
    with pytest.raises(C.ContractError, match="already proposed"):
        C.reset_to_proposed(p, actor="operator")


# -- approval expiry -----------------------------------------------------------

def _age_latest_approval(path, days):
    """Simulates aging: rewrites the newest approval timestamp to `days` ago."""
    item = C.load_item(path)
    old = (dt.datetime.now(dt.timezone.utc)
           - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    item["meta"]["approvals"][-1]["at"] = old
    C._dump(Path(path), item["meta"], item["body"])


def _set_ttl(root, ttl):
    profile = root / "site-profile.yaml"
    profile.write_text(profile.read_text() + f"approvals:\n  ttl_days: {ttl}\n")


def test_approval_ttl_days_defaults_to_30(root):
    assert C.approval_ttl_days(root) == 30


def test_approval_ttl_days_reads_profile_override(root):
    _set_ttl(root, 5)
    assert C.approval_ttl_days(root) == 5


def test_approval_ttl_days_zero_raises(root):
    _set_ttl(root, 0)
    with pytest.raises(C.ContractError, match="ttl_days must be positive"):
        C.approval_ttl_days(root)


def test_approval_ttl_days_negative_raises(root):
    _set_ttl(root, -3)
    with pytest.raises(C.ContractError, match="ttl_days must be positive"):
        C.approval_ttl_days(root)


def test_latest_approval_picks_newest_approved_entry(root):
    p = C.create_item(root, kind="onpage-fix", slug="latest", title="t", body="b",
                      target="https://ex.com/l", source="s")
    assert C.latest_approval(C.load_item(p)) is None
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    entry = C.latest_approval(C.load_item(p))
    assert entry is not None
    assert entry["decision"] == "approved"
    assert entry["actor"] == "shivaa"


def test_fresh_approval_passes_both_gates(root):
    p = C.create_item(root, kind="onpage-fix", slug="fresh", title="t", body="b",
                      target="https://ex.com/f", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.require_approved(p)          # no raise
    C.require_approval_lineage(p)  # no raise


def test_expired_approval_blocks_require_approved(root):
    p = C.create_item(root, kind="onpage-fix", slug="stale", title="t", body="b",
                      target="https://ex.com/s", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    _age_latest_approval(p, days=31)
    with pytest.raises(C.ContractError, match="expired"):
        C.require_approved(p)
    # re-confirm, never silent rejection: the gate does not touch the status
    assert C.load_item(p)["meta"]["status"] == "approved"


def test_expiry_message_names_the_reconfirm_command(root):
    p = C.create_item(root, kind="onpage-fix", slug="stale-msg", title="t", body="b",
                      target="https://ex.com/sm", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    _age_latest_approval(p, days=31)
    with pytest.raises(C.ContractError, match=r"re-confirm with: python3 -m core approve"):
        C.require_approved(p)


def test_expired_approval_blocks_lineage_gate_on_drafted_item(root):
    p = C.create_item(root, kind="content-brief", slug="stale-draft", title="t", body="b",
                      target="", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "drafted", actor="agent")
    _age_latest_approval(p, days=31)
    with pytest.raises(C.ContractError, match="expired"):
        C.require_approval_lineage(p)
    assert C.load_item(p)["meta"]["status"] == "drafted"  # state untouched


def test_profile_ttl_makes_shorter_window_expire(root):
    _set_ttl(root, 5)
    p = C.create_item(root, kind="onpage-fix", slug="short-ttl", title="t", body="b",
                      target="https://ex.com/st", source="s")
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    _age_latest_approval(p, days=6)
    with pytest.raises(C.ContractError, match="ttl 5 days"):
        C.require_approved(p)


# -- schema versioning ---------------------------------------------------------

def test_check_schema_missing_profile(tmp_path):
    empty = tmp_path / "no-brain-here"
    empty.mkdir()
    result = C.check_schema(empty)
    assert result == {"version": 0, "compatible": False, "action": "run /organic-os:setup"}


def test_check_schema_missing_key_assumes_v1_and_stamps(root):
    # root's site-profile.yaml was scaffolded with schema_version: 1 already;
    # simulate a pre-v0.1.3 brain by stripping the key out.
    profile = root / "site-profile.yaml"
    lines = [l for l in profile.read_text().splitlines() if "schema_version" not in l]
    profile.write_text("\n".join(lines) + "\n")
    result = C.check_schema(root)
    assert result == {"version": 1, "compatible": True, "action": "stamp"}


def test_check_schema_current_version(root):
    result = C.check_schema(root)
    assert result == {"version": 1, "compatible": True, "action": "none"}


def test_check_schema_older_version_needs_migration(root):
    profile = root / "site-profile.yaml"
    text = profile.read_text().replace("schema_version: 1", "schema_version: 0")
    profile.write_text(text)
    result = C.check_schema(root)
    assert result == {"version": 0, "compatible": False,
                       "action": "run /organic-os:setup to migrate"}


def test_check_schema_newer_version_needs_plugin_update(root):
    profile = root / "site-profile.yaml"
    text = profile.read_text().replace("schema_version: 1", "schema_version: 2")
    profile.write_text(text)
    result = C.check_schema(root)
    assert result == {"version": 2, "compatible": False,
                       "action": "update the plugin (/plugin update organic-os)"}


def test_mark_notified_and_is_notified(root):
    p = C.create_item(root, kind="onpage-fix", slug="notify-me", title="t", body="b",
                      target="https://ex.com/n", source="s")
    assert C.is_notified(C.load_item(p)) is False
    C.mark_notified(p)
    assert C.is_notified(C.load_item(p)) is True


# -- record_connector -----------------------------------------------------

def test_record_connector_round_trip_preserves_other_profile_keys(root):
    profile = root / "site-profile.yaml"
    before = yaml.safe_load(profile.read_text())
    C.record_connector(profile, "ga4", "verified", "local-cli")
    after = yaml.safe_load(profile.read_text())
    entry = after["connectors"]["ga4"]
    assert entry["status"] == "verified"
    assert entry["context"] == "local-cli"
    assert entry["checked"]  # a UTC date was stamped
    assert not isinstance(entry, bool)
    # every other top-level key is untouched
    for key in before:
        if key != "connectors":
            assert after[key] == before[key]


def test_record_connector_overwrite_updates_not_duplicates(root):
    profile = root / "site-profile.yaml"
    C.record_connector(profile, "gsc", "unavailable", "cowork-cloud")
    C.record_connector(profile, "gsc", "verified", "local-cli")
    data = yaml.safe_load(profile.read_text())
    assert data["connectors"]["gsc"]["status"] == "verified"
    assert data["connectors"]["gsc"]["context"] == "local-cli"
    # exactly one connectors mapping, no stray duplicate keys
    assert list(data["connectors"]).count("gsc") == 1


def test_record_connector_migrates_plain_string_entry_without_touching_siblings(root):
    profile = root / "site-profile.yaml"
    text = profile.read_text()
    # simulate a pre-wave-1 profile: connectors stored as bare strings
    assert "ga4: unknown" in text
    C.record_connector(profile, "ga4", "verified", "ci")
    data = yaml.safe_load(profile.read_text())
    assert data["connectors"]["ga4"] == {
        "status": "verified", "context": "ci",
        "checked": data["connectors"]["ga4"]["checked"],
    }
    # sibling connector untouched - still the old bare-string form
    assert data["connectors"]["gsc"] == "unknown"


def test_record_connector_rejects_invalid_status(root):
    profile = root / "site-profile.yaml"
    with pytest.raises(C.ContractError):
        C.record_connector(profile, "ga4", "connected", "local-cli")


# -- write_scorecard --------------------------------------------------------

def test_write_scorecard_table_has_fix_only_for_non_pass_rows(root):
    checks = [
        {"name": "brain scaffold", "status": "pass", "detail": "ok", "fix": ""},
        {"name": "GA4 connector", "status": "degraded",
         "detail": "not reachable from local-cli",
         "fix": "claude mcp add ga4"},
        {"name": "GSC connector", "status": "fail",
         "detail": "absent", "fix": "claude mcp add gsc"},
    ]
    path = C.write_scorecard(root, checks)
    assert path.name == "REPORT.md"
    assert path.parent.parent == root / "runs"
    text = path.read_text()
    assert "brain scaffold" in text and "pass" in text
    assert "GA4 connector" in text and "degraded" in text
    assert "GSC connector" in text and "fail" in text
    assert "claude mcp add ga4" in text
    assert "claude mcp add gsc" in text
    # the passing row's (empty) fix is not rendered as a fix line
    pass_line_idx = text.index("brain scaffold")
    fixes_idx = text.index("claude mcp add ga4")
    assert pass_line_idx < fixes_idx


# -- editorial policy ----------------------------------------------------------

def _set_editorial(root, section):
    p = root / "site-profile.yaml"
    data = yaml.safe_load(p.read_text()) or {}
    data["editorial"] = section
    p.write_text(yaml.safe_dump(data))


def test_editorial_policy_defaults_on_profile_without_section(root):
    assert C.editorial_policy(root) == {
        "oversight_threshold": 7,
        "internal_links_min": 0,
        "external_links_max": None,
        "images_min": 0,
        "sourcing": "key-claims",
        "require_reviewer_note": False,
    }


def test_editorial_policy_defaults_when_profile_missing(tmp_path):
    # A bare directory with no site-profile.yaml still answers with the
    # defaults - policy enforcement never crashes a profile-less caller.
    assert C.editorial_policy(tmp_path)["sourcing"] == "key-claims"


def test_editorial_policy_partial_override_keeps_other_defaults(root):
    _set_editorial(root, {"internal_links_min": 3, "sourcing": "every-claim"})
    policy = C.editorial_policy(root)
    assert policy["internal_links_min"] == 3
    assert policy["sourcing"] == "every-claim"
    assert policy["oversight_threshold"] == 7          # untouched defaults
    assert policy["external_links_max"] is None
    assert policy["images_min"] == 0
    assert policy["require_reviewer_note"] is False


def test_editorial_policy_full_override(root):
    _set_editorial(root, {"oversight_threshold": 9, "internal_links_min": 2,
                          "external_links_max": 5, "images_min": 1,
                          "sourcing": "every-claim",
                          "require_reviewer_note": True})
    policy = C.editorial_policy(root)
    assert policy["external_links_max"] == 5
    assert policy["images_min"] == 1
    assert policy["require_reviewer_note"] is True


@pytest.mark.parametrize("key,bad", [
    ("oversight_threshold", 12),
    ("oversight_threshold", "high"),
    ("internal_links_min", -1),
    ("internal_links_min", True),      # a bool is not a count
    ("external_links_max", -2),
    ("external_links_max", "none"),
    ("images_min", -1),
    ("sourcing", "all-claims"),
    ("require_reviewer_note", "yes"),
])
def test_editorial_policy_invalid_value_raises_naming_the_key(root, key, bad):
    _set_editorial(root, {key: bad})
    with pytest.raises(C.ContractError) as exc:
        C.editorial_policy(root)
    assert f"editorial.{key}" in str(exc.value)


def test_editorial_policy_section_not_a_mapping_raises(root):
    _set_editorial(root, "strict")
    with pytest.raises(C.ContractError) as exc:
        C.editorial_policy(root)
    assert "editorial" in str(exc.value)


def test_editorial_policy_ignores_unknown_keys_additively(root):
    # A newer plugin's additive key must not break an older reader.
    _set_editorial(root, {"internal_links_min": 1, "future_key": "x"})
    policy = C.editorial_policy(root)
    assert policy["internal_links_min"] == 1
    assert "future_key" not in policy


# -- derived queue stays true (the 12-day stale-queue bug) ---------------------

def test_set_status_refreshes_the_derived_queue(root):
    p = C.create_item(root, kind="content-brief", slug="auto-refresh", title="Auto",
                      body="b", target="", source="s")
    C.rebuild_queue(root)
    assert "Auto" in (root / "approvals" / "queue.md").read_text()
    # no explicit rebuild_queue call: the status change must refresh the queue
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    q = (root / "approvals" / "queue.md").read_text()
    assert "Auto" not in q, "queue still lists an approved item as pending"


def test_published_item_leaves_the_queue_without_explicit_rebuild(root):
    p = C.create_item(root, kind="content-brief", slug="auto-published", title="Shipped",
                      body="b", target="", source="s")
    C.rebuild_queue(root)
    item_id = C.load_item(p)["meta"]["id"]
    assert item_id in (root / "approvals" / "queue.md").read_text()
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    C.set_status(p, "drafted", actor="agent")
    C.set_status(p, "published", actor="agent")
    assert item_id not in (root / "approvals" / "queue.md").read_text()


def test_status_change_survives_a_failing_queue_rebuild(root, monkeypatch):
    """The refresh is best-effort: a derived file must never be able to block
    or roll back a real state transition."""
    p = C.create_item(root, kind="onpage-fix", slug="rebuild-blows-up", title="t",
                      body="b", target="https://ex.com/r", source="s")

    def boom(_root):
        raise OSError("queue file is read-only")

    monkeypatch.setattr(C, "rebuild_queue", boom)
    C.set_status(p, "approved", actor="shivaa", channel="in-session")
    assert C.load_item(p)["meta"]["status"] == "approved"  # durable on disk


def test_reset_to_proposed_refreshes_the_derived_queue(root):
    p = _hand_birth(root, "drafted", slug="reset-refresh")
    C.rebuild_queue(root)
    assert "ILLEGAL-STATE" in (root / "approvals" / "queue.md").read_text()
    C.reset_to_proposed(p, actor="operator")  # no explicit rebuild
    q = (root / "approvals" / "queue.md").read_text()
    assert "ILLEGAL-STATE" not in q
    assert C.load_item(p)["meta"]["id"] in q  # now listed as pending


def test_reset_to_proposed_survives_a_failing_queue_rebuild(root, monkeypatch):
    p = _hand_birth(root, "drafted", slug="reset-rebuild-blows-up")

    def boom(_root):
        raise OSError("queue file is read-only")

    monkeypatch.setattr(C, "rebuild_queue", boom)
    C.reset_to_proposed(p, actor="operator")
    assert C.load_item(p)["meta"]["status"] == "proposed"
