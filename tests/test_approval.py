import datetime as dt
import json
import sys
from pathlib import Path
LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

import pytest  # noqa: E402
from core.init_site_repo import init_site_repo  # noqa: E402
from core import contracts as C  # noqa: E402
from core import approval as A  # noqa: E402


def test_pending_lists_and_approve_records(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    p = C.create_item(root, "onpage-fix", "fix1", "Fix one", "body", "https://e.com/1", "s")
    assert [i["meta"]["id"] for i in A.pending(root)] == ["p-" + p.name[:8] + "-fix1"]
    A.record_decision(root, item_id=A.pending(root)[0]["meta"]["id"],
                      decision="approved", actor="shivaa", channel="telegram")
    assert A.pending(root) == []
    assert C.load_item(p)["meta"]["status"] == "approved"


def _age_latest_approval(path, days):
    """Simulates aging: rewrites the newest approval timestamp to `days` ago."""
    item = C.load_item(path)
    old = (dt.datetime.now(dt.timezone.utc)
           - dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    item["meta"]["approvals"][-1]["at"] = old
    C._dump(Path(path), item["meta"], item["body"])


def test_reconfirm_expired_approval_appends_fresh_entry(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    p = C.create_item(root, "onpage-fix", "stale", "t", "b", "https://e.com/s", "s")
    item_id = C.load_item(p)["meta"]["id"]
    A.record_decision(root, item_id, "approved", actor="shivaa", channel="in-session")
    _age_latest_approval(p, days=31)
    with pytest.raises(C.ContractError, match="expired"):
        C.require_approved(p)

    # re-confirming via the same record_decision path refreshes the clock
    A.record_decision(root, item_id, "approved", actor="shivaa", channel="telegram")
    approvals = C.load_item(p)["meta"]["approvals"]
    assert len(approvals) == 2
    assert approvals[-1]["channel"] == "telegram"
    C.require_approved(p)          # gate reopens
    C.require_approval_lineage(p)  # lineage gate reopens too


def test_non_expired_replay_still_noops(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    p = C.create_item(root, "onpage-fix", "fresh", "t", "b", "https://e.com/f", "s")
    item_id = C.load_item(p)["meta"]["id"]
    A.record_decision(root, item_id, "approved", actor="shivaa", channel="in-session")
    A.record_decision(root, item_id, "approved", actor="shivaa", channel="in-session")
    assert len(C.load_item(p)["meta"]["approvals"]) == 1  # exactly one entry


class FakeTelegramHTTP:
    """Captures getUpdates params per call; returns one canned batch per call."""
    def __init__(self, batches):
        self.batches = batches
        self.calls = []

    def get(self, url, params):
        self.calls.append(params)
        idx = len(self.calls) - 1
        return self.batches[idx] if idx < len(self.batches) else {"result": []}

    def post(self, url, payload):
        raise AssertionError("process_telegram_decisions should never send messages")


def _updates(*msgs):
    return {"result": [{"update_id": uid, "message": {"chat": {"id": 42}, "text": text}}
                       for uid, text in msgs]}


def test_process_telegram_decisions_persists_offset_across_calls(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    p = C.create_item(root, "onpage-fix", "fix1", "Fix one", "body", "https://e.com/1", "s")
    item_id = C.load_item(p)["meta"]["id"]

    http = FakeTelegramHTTP([
        _updates((7, f"approve {item_id}")),
        {"result": []},
    ])
    out1 = A.process_telegram_decisions(root, token="t", chat_id=42, transport=http)
    assert out1 == [(item_id, "recorded")]
    assert http.calls[0]["offset"] == 1  # first call: no offset file yet -> offset+1 = 0+1

    offset_file = root / "approvals" / "telegram-offset.json"
    assert offset_file.exists()
    assert json.loads(offset_file.read_text())["offset"] == 7

    A.process_telegram_decisions(root, token="t", chat_id=42, transport=http)
    assert http.calls[1]["offset"] == 8  # second call: persisted offset (7) + 1


def test_process_telegram_decisions_records_reason_as_note(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    p = C.create_item(root, "onpage-fix", "fix1", "Fix one", "body", "https://e.com/1", "s")
    item_id = C.load_item(p)["meta"]["id"]
    http = FakeTelegramHTTP([_updates((5, f"reject {item_id} too thin"))])
    A.process_telegram_decisions(root, token="t", chat_id=42, transport=http)
    entry = C.load_item(p)["meta"]["approvals"][0]
    assert entry["decision"] == "rejected"
    assert entry["note"] == "too thin"


def test_process_telegram_decisions_unknown_id_never_raises(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    http = FakeTelegramHTTP([_updates((3, "approve b-20260101-ghost"))])
    out = A.process_telegram_decisions(root, token="t", chat_id=42, transport=http)
    assert out == [("b-20260101-ghost", "unknown")]


def test_process_telegram_decisions_stale_does_not_block_other_decisions(tmp_path):
    root = init_site_repo(tmp_path / "b", "https://e.com", "E")
    applied = C.create_item(root, "onpage-fix", "already-applied", "t", "b",
                            "https://e.com/a", "s")
    applied_id = C.load_item(applied)["meta"]["id"]
    C.set_status(applied, "approved", actor="shivaa", channel="in-session")
    C.set_status(applied, "applied", actor="agent")

    fresh = C.create_item(root, "onpage-fix", "fresh", "t", "b", "https://e.com/f", "s")
    fresh_id = C.load_item(fresh)["meta"]["id"]

    http = FakeTelegramHTTP([_updates(
        (10, f"approve {applied_id}"),   # stale: already past proposed
        (11, f"approve {fresh_id}"),     # still recordable
    )])
    out = A.process_telegram_decisions(root, token="t", chat_id=42, transport=http)
    assert out == [(applied_id, "stale"), (fresh_id, "recorded")]
    assert C.load_item(applied)["meta"]["status"] == "applied"       # untouched
    assert C.load_item(fresh)["meta"]["status"] == "approved"        # recorded


def test_find_skips_a_malformed_sibling_file(tmp_path):
    """A brief with no parseable frontmatter must not break resolving a good one."""
    import core.approval as A
    (tmp_path / "briefs").mkdir()
    (tmp_path / "proposals").mkdir()
    (tmp_path / "briefs" / "good.md").write_text(
        "---\nid: b-20260101-good\nkind: content-brief\nstatus: proposed\n"
        "title: Good\napprovals: []\n---\nbody\n")
    (tmp_path / "briefs" / "broken.md").write_text("no frontmatter here at all\n")
    found = A.find(str(tmp_path), "b-20260101-good")
    assert found.name == "good.md"
