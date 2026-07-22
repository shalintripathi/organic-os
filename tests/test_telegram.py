import sys
from pathlib import Path
LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

from core import telegram as T  # noqa: E402


class FakeHTTP:
    def __init__(self):
        self.sent = []
        self.updates = {"result": [
            {"update_id": 7, "message": {"chat": {"id": 42},
                                          "text": "approve p-20260718-fix1"}},
            {"update_id": 8, "message": {"chat": {"id": 42},
                                          "text": "reject b-20260718-guide too thin"}},
        ]}
    def post(self, url, payload):
        self.sent.append((url, payload))
        return {"ok": True, "result": {"message_id": 1}}
    def get(self, url, params):
        return self.updates


def test_send_proposal_formats_message():
    http = FakeHTTP()
    T.send_item(http, token="t", chat_id=42,
                item={"meta": {"id": "p-1", "kind": "onpage-fix", "title": "Fix titles",
                                "target": "https://e.com/x"}, "body": "details"})
    url, payload = http.sent[0]
    assert "sendMessage" in url and "Fix titles" in payload["text"]
    assert "approve p-1" in payload["text"]  # instructions included


def test_poll_decisions_parses_both():
    http = FakeHTTP()
    decisions, last = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", ""),
                        ("b-20260718-guide", "rejected", "too thin")]
    assert last == 8


def test_poll_decisions_chat_id_type_insensitive():
    # API sends int chat ids; site-profile.yaml stores strings. Both must match.
    http = FakeHTTP()
    decisions, last = T.poll_decisions(http, token="t", chat_id="42", offset=0)
    assert decisions == [("p-20260718-fix1", "approved", ""),
                        ("b-20260718-guide", "rejected", "too thin")]
    assert last == 8


# -- reply-context decisions --------------------------------------------------

PROPOSAL_TEXT = ("organic-os proposal p-20260718-fix1\n"
                 "[onpage-fix] Fix titles\ntarget: https://example.com/x")


class ReplyHTTP:
    """FakeHTTP variant with caller-supplied updates."""
    def __init__(self, updates):
        self.updates = {"result": updates}

    def get(self, url, params):
        return self.updates


def _upd(uid, text, reply_to_text=None):
    msg = {"chat": {"id": 42}, "text": text}
    if reply_to_text is not None:
        msg["reply_to_message"] = {"text": reply_to_text}
    return {"update_id": uid, "message": msg}


def test_reply_approved_resolves_id_from_replied_to_text():
    http = ReplyHTTP([_upd(9, "Approved", reply_to_text=PROPOSAL_TEXT)])
    decisions, last = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "")]
    assert last == 9


def test_reply_thumbs_up_with_note_approves_and_keeps_note():
    http = ReplyHTTP([_upd(10, "\U0001F44D looks good", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "looks good")]


def test_reply_reject_word_with_note():
    http = ReplyHTTP([_upd(11, "no too thin", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "rejected", "too thin")]


def test_non_reply_bare_approved_resolves_nothing():
    # No reply context means no item id to resolve against.
    http = ReplyHTTP([_upd(12, "Approved")])
    decisions, last = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []
    assert last == 12  # still acknowledged, never re-polled


def test_strict_form_in_reply_still_works_and_takes_precedence():
    # The typed id wins over the replied-to message's id.
    http = ReplyHTTP([_upd(13, "approve p-20260718-other",
                           reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-other", "approved", "")]


def test_reply_to_message_without_item_id_resolves_nothing():
    http = ReplyHTTP([_upd(14, "Approved", reply_to_text="hello there")])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []


def test_reply_with_non_decision_text_resolves_nothing():
    http = ReplyHTTP([_upd(15, "interesting, let me think",
                           reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []


def test_reply_go_ahead_approves():
    http = ReplyHTTP([_upd(16, "Go ahead", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "")]


def test_reply_go_ahead_with_trailing_text_approves_with_note():
    http = ReplyHTTP([_upd(17, "go ahead and fix the title too",
                           reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "and fix the title too")]


def test_reply_ship_it_approves():
    http = ReplyHTTP([_upd(18, "ship it", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "")]


def test_reply_lgtm_approves():
    http = ReplyHTTP([_upd(19, "LGTM", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "approved", "")]


def test_reply_wait_for_now_resolves_nothing():
    # Deferring is not rejecting: "wait" must stay a non-decision so the
    # item stays pending for a real answer later.
    http = ReplyHTTP([_upd(20, "Wait for now", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []


def test_reply_hold_resolves_nothing():
    http = ReplyHTTP([_upd(21, "hold", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []


def test_reply_bare_no_rejects():
    http = ReplyHTTP([_upd(22, "no", reply_to_text=PROPOSAL_TEXT)])
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("p-20260718-fix1", "rejected", "")]


def test_send_item_states_reply_format():
    http = FakeHTTP()
    T.send_item(http, token="t", chat_id=42,
                item={"meta": {"id": "p-2", "kind": "onpage-fix", "title": "T",
                                "target": ""}, "body": "b"})
    _, payload = http.sent[0]
    assert "Reply to this message" in payload["text"]
    assert "approve p-2" in payload["text"]  # strict form still shown


# -- document delivery --------------------------------------------------------

class FakeMultipartHTTP:
    def __init__(self):
        self.calls = []

    def post_multipart(self, url, fields, file_field, file_name, file_bytes):
        self.calls.append({"url": url, "fields": fields,
                           "file_field": file_field, "file_name": file_name,
                           "file_bytes": file_bytes})
        return {"ok": True, "result": {"message_id": 5}}


def test_send_document_posts_file_with_caption(tmp_path):
    doc = tmp_path / "report.pdf"
    doc.write_bytes(b"%PDF-1.4 fake")
    http = FakeMultipartHTTP()
    T.send_document("tok", 42, doc, caption="Week of 2026-07-13\n2 shipped",
                    transport=http)
    call = http.calls[0]
    assert "sendDocument" in call["url"]
    assert call["fields"]["chat_id"] == "42"
    assert call["fields"]["caption"] == "Week of 2026-07-13\n2 shipped"
    assert call["file_field"] == "document"
    assert call["file_name"] == "report.pdf"
    assert call["file_bytes"] == b"%PDF-1.4 fake"


def test_send_document_caption_optional(tmp_path):
    doc = tmp_path / "report.html"
    doc.write_bytes(b"<p>hi</p>")
    http = FakeMultipartHTTP()
    T.send_document("tok", 42, doc, transport=http)
    assert "caption" not in http.calls[0]["fields"]


def test_urllibhttp_post_multipart_encodes_fields_and_file(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b'{"ok": true}'

    def fake_urlopen(req, timeout=None):
        captured["req"] = req
        return FakeResponse()

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    out = http.post_multipart("https://api.example/sendDocument",
                              {"chat_id": "42", "caption": "two lines"},
                              "document", "r.pdf", b"BYTES\x00\xffHERE")
    assert out == {"ok": True}
    req = captured["req"]
    ctype = req.headers["Content-type"]
    assert ctype.startswith("multipart/form-data; boundary=")
    boundary = ctype.split("boundary=", 1)[1]
    body = req.data
    assert boundary.encode() in body
    assert b'name="chat_id"' in body and b"42" in body
    assert b'name="caption"' in body and b"two lines" in body
    assert b'name="document"; filename="r.pdf"' in body
    assert b"BYTES\x00\xffHERE" in body
    assert body.rstrip().endswith(b"--" + boundary.encode() + b"--")


def test_urllibhttp_post_multipart_sanitizes_errors(monkeypatch):
    import urllib.error

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            "https://api.telegram.org/botSECRET-TOKEN/sendDocument",
            413, "Payload Too Large", None, None)

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.post_multipart("https://api.telegram.org/botSECRET-TOKEN/sendDocument",
                            {"chat_id": "1"}, "document", "r.pdf", b"x")
    except RuntimeError as e:
        assert "SECRET-TOKEN" not in str(e)
        assert "413" in str(e)
    else:
        raise AssertionError("post_multipart did not raise on HTTPError")


def test_urllibhttp_post_sanitizes_http_errors(monkeypatch):
    import urllib.error

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/sendMessage"

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            token_url, 401, "Unauthorized", None, None)

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.post(token_url, {"chat_id": "1", "text": "hi"})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "401" in str(e)
    else:
        raise AssertionError("post did not raise on HTTPError")


def test_urllibhttp_post_sanitizes_url_errors(monkeypatch):
    import urllib.error

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/sendMessage"

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("network unreachable")

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.post(token_url, {"chat_id": "1", "text": "hi"})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "network unreachable" in str(e)
    else:
        raise AssertionError("post did not raise on URLError")


def test_urllibhttp_get_sanitizes_http_errors(monkeypatch):
    import urllib.error

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/getUpdates"

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            token_url, 403, "Forbidden", None, None)

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.get(token_url, {"offset": 1, "timeout": 0})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "403" in str(e)
    else:
        raise AssertionError("get did not raise on HTTPError")


def test_urllibhttp_get_sanitizes_url_errors(monkeypatch):
    import urllib.error

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/getUpdates"

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("timed out")

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.get(token_url, {"offset": 1, "timeout": 0})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "timed out" in str(e)
    else:
        raise AssertionError("get did not raise on URLError")


def test_urllibhttp_post_multipart_sanitizes_url_errors(monkeypatch):
    import urllib.error

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/sendDocument"

    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    http = T.UrllibHTTP()
    try:
        http.post_multipart(token_url, {"chat_id": "1"}, "document", "r.pdf", b"x")
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "connection reset" in str(e)
    else:
        raise AssertionError("post_multipart did not raise on URLError")


def test_send_document_empty_caption_omitted(tmp_path):
    doc = tmp_path / "r.html"
    doc.write_bytes(b"<p>x</p>")
    http = FakeMultipartHTTP()
    T.send_document("tok", 42, doc, caption="", transport=http)
    assert "caption" not in http.calls[0]["fields"]
