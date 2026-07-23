import sys
from pathlib import Path
LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

import pytest  # noqa: E402

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
    assert payload["parse_mode"] == "HTML"
    # short id -> tap buttons carry the decision, no typed id needed
    kb = payload["reply_markup"]["inline_keyboard"][0]
    assert kb[0]["callback_data"] == "a:p-1"
    assert kb[1]["callback_data"] == "r:p-1"
    assert "Approve" in kb[0]["text"] and "Reject" in kb[1]["text"]


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


def test_send_item_shows_buttons_for_a_normal_id():
    http = FakeHTTP()
    T.send_item(http, token="t", chat_id=42,
                item={"meta": {"id": "p-2", "kind": "onpage-fix", "title": "T",
                                "target": ""}, "body": "b"})
    _, payload = http.sent[0]
    assert payload["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "a:p-2"
    assert "records your decision" in payload["text"]  # reassures a tap is safe


def test_send_item_falls_back_to_typed_grammar_when_id_too_long():
    http = FakeHTTP()
    long_id = "b-20260721-" + ("x" * 60)  # pushes a:<id> past the 64-byte cap
    T.send_item(http, token="t", chat_id=42,
                item={"meta": {"id": long_id, "kind": "content-brief", "title": "T",
                                "target": ""}, "body": "b"})
    _, payload = http.sent[0]
    assert "reply_markup" not in payload            # no button that cannot resolve
    assert f"approve {long_id}" in payload["text"]  # typed path offered instead


def test_poll_decisions_records_a_button_tap_and_acknowledges():
    class TapHTTP(FakeHTTP):
        def __init__(self):
            super().__init__()
            self.updates = {"result": [
                {"update_id": 11, "callback_query": {
                    "id": "cq99", "data": "a:b-20260721-wp-checklist",
                    "message": {"chat": {"id": 42}}}},
                {"update_id": 12, "callback_query": {
                    "id": "cq100", "data": "r:p-20260721-thin",
                    "message": {"chat": {"id": 42}}}},
            ]}
    http = TapHTTP()
    decisions, last = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == [("b-20260721-wp-checklist", "approved", ""),
                         ("p-20260721-thin", "rejected", "")]
    assert last == 12
    # both taps acknowledged via answerCallbackQuery so the buttons stop spinning
    acks = [pl for url, pl in http.sent if "answerCallbackQuery" in url]
    assert len(acks) == 2 and acks[0]["callback_query_id"] == "cq99"


def test_poll_decisions_ignores_button_taps_from_another_chat():
    class OtherChatHTTP(FakeHTTP):
        def __init__(self):
            super().__init__()
            self.updates = {"result": [
                {"update_id": 13, "callback_query": {
                    "id": "cq1", "data": "a:b-20260721-x",
                    "message": {"chat": {"id": 999}}}},
            ]}
    http = OtherChatHTTP()
    decisions, _ = T.poll_decisions(http, token="t", chat_id=42, offset=0)
    assert decisions == []


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



def test_urllibhttp_post_sanitizes_invalid_url(monkeypatch):
    """InvalidURL (e.g. newline in token) must not leak the token (issue #12).

    The client local is deliberately NOT named `http`: that would shadow the
    `http` module inside fake_urlopen's closure, so `http.client.InvalidURL`
    would raise AttributeError and the InvalidURL path would never run.
    """
    import http.client

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123\n/sendMessage"

    def fake_urlopen(req, timeout=None):
        raise http.client.InvalidURL(
            "URL can't contain control characters. '/botSECRET-TOKEN-123\n/sendMessage'"
        )

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    client = T.UrllibHTTP()
    try:
        client.post(token_url, {"chat_id": "1", "text": "hi"})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "telegram api error" in str(e)
        assert "InvalidURL" in str(e)  # the class names the failure
        assert "control characters" not in str(e)  # the original message stays out
    else:
        raise AssertionError("post did not raise on InvalidURL")


def test_urllibhttp_get_sanitizes_invalid_url(monkeypatch):
    import http.client

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123 /getUpdates"

    def fake_urlopen(req, timeout=None):
        raise http.client.InvalidURL(
            "URL can't contain control characters. 'SECRET-TOKEN-123 '"
        )

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    try:
        T.UrllibHTTP().get(token_url, {"offset": 1})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
    else:
        raise AssertionError("get did not raise on InvalidURL")


def test_urllibhttp_post_multipart_sanitizes_invalid_url(monkeypatch):
    import http.client

    token_url = "https://api.telegram.org/botSECRET-TOKEN-123\n/sendDocument"

    def fake_urlopen(req, timeout=None):
        raise http.client.InvalidURL("URL can't contain control characters. SECRET-TOKEN-123")

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    try:
        T.UrllibHTTP().post_multipart(token_url, {"chat_id": "1"}, "document", "r.pdf", b"x")
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
    else:
        raise AssertionError("post_multipart did not raise on InvalidURL")


def test_urllibhttp_post_sanitizes_value_error_unknown_url_type(monkeypatch):
    token_url = "botSECRET-TOKEN-123/sendMessage"  # scheme-less

    def fake_urlopen(req, timeout=None):
        raise ValueError("unknown url type: 'botSECRET-TOKEN-123/sendMessage'")

    monkeypatch.setattr(T.urllib.request, "urlopen", fake_urlopen)
    try:
        T.UrllibHTTP().post(token_url, {"chat_id": "1", "text": "hi"})
    except RuntimeError as e:
        assert "SECRET-TOKEN-123" not in str(e)
        assert "unknown url type" not in str(e)
        assert "ValueError" in str(e)  # the class names the failure
    else:
        raise AssertionError("post did not raise on ValueError")


def test_urllibhttp_names_the_failure_class_without_the_url(monkeypatch):
    """A malformed response and a caller TypeError must read differently.

    The blanket handler used to fold every non-HTTP/URL failure into one
    constant string, so an operator could not tell a broken response from a
    broken token at 3am. The exception class name is safe to surface: a type
    name can never carry the token. The original message still stays out,
    because that is the part that embeds the URL.
    """
    token_url = "https://api.telegram.org/botSECRET-TOKEN-123/sendMessage"

    class BadJSONResponse:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def read(self):
            return b"<html>502 Bad Gateway</html>"

    def json_failure(req, timeout=None):
        return BadJSONResponse()

    def type_failure(req, timeout=None):
        raise TypeError(f"a bytes-like object is required, not 'str': {token_url}")

    messages = {}
    for label, fake in (("json", json_failure), ("type", type_failure)):
        monkeypatch.setattr(T.urllib.request, "urlopen", fake)
        try:
            T.UrllibHTTP().post(token_url, {"chat_id": "1", "text": "hi"})
        except RuntimeError as e:
            messages[label] = str(e)
        else:
            raise AssertionError(f"post did not raise on the {label} failure")

    assert "JSONDecodeError" in messages["json"]
    assert "TypeError" in messages["type"]
    assert messages["json"] != messages["type"], \
        "the two failures are still indistinguishable"
    for msg in messages.values():
        assert "SECRET-TOKEN-123" not in msg
        assert token_url not in msg
        assert "bytes-like object" not in msg  # original message withheld


def test_sanitize_bot_token_strips_and_rejects_controls():
    assert T.sanitize_bot_token("  SECRET-TOKEN-123\n") == "SECRET-TOKEN-123"
    try:
        T.sanitize_bot_token("SECRET TOKEN WITH SPACE")
    except RuntimeError as e:
        # Two independent assertions. The earlier `A or B` form could never
        # fail: B ("whitespace" in the message) is always true, so a message
        # that echoed the whole token would still have passed.
        assert "SECRET" not in str(e)
        assert "SECRET TOKEN WITH SPACE" not in str(e)
        assert "whitespace" in str(e).lower()  # names the rejection reason
    else:
        raise AssertionError("expected RuntimeError for spaced token")


@pytest.mark.parametrize("bad_char,kind", [
    ("\x7f", "DEL"),
    ("\x80", "C1"),
    ("\x9f", "C1"),
])
def test_sanitize_bot_token_rejects_del_and_c1_controls(bad_char, kind):
    """http.client rejects DEL (0x7f) and C1 (0x80-0x9f); the sanitizer must
    reject them too so the token never reaches the stack that would echo it."""
    token = "SECRET-TOKEN-123" + bad_char
    try:
        T.sanitize_bot_token(token)
    except RuntimeError as e:
        assert "SECRET" not in str(e), f"{kind} char: token leaked in error"
        assert token not in str(e), f"{kind} char: full token leaked in error"
        assert "control" in str(e).lower(), f"{kind} char: reason not named"
    else:
        raise AssertionError(f"expected RuntimeError for {kind} control char")


def test_send_document_empty_caption_omitted(tmp_path):
    doc = tmp_path / "r.html"
    doc.write_bytes(b"<p>x</p>")
    http = FakeMultipartHTTP()
    T.send_document("tok", 42, doc, caption="", transport=http)
    assert "caption" not in http.calls[0]["fields"]


# -- sanitizer wiring at the three public call sites --------------------------
#
# send_item, send_document and poll_decisions each build the API URL through
# sanitize_bot_token(). Deleting that call from all three left the rest of
# the suite green, so nothing pinned the wiring and a refactor could drop it
# silently. These two parametrized tests pin both halves of the sanitizer's
# contract at every call site: a recoverable token is normalized before it
# reaches the transport, and an unrecoverable one never reaches it at all.

CLEAN_TOKEN = "SECRET-TOKEN-123"
TRAILING_NEWLINE_TOKEN = CLEAN_TOKEN + "\n"   # as an env file hands it over
INTERIOR_CONTROL_TOKEN = "SECRET-TOKEN\n123"  # unrecoverable, must fail closed

ENTRY_POINTS = ["send_item", "send_document", "poll_decisions"]


class RecordingHTTP:
    """Transport that records every URL it is handed, on any method."""

    def __init__(self):
        self.urls = []

    def post(self, url, payload):
        self.urls.append(url)
        return {"ok": True, "result": {"message_id": 1}}

    def get(self, url, params):
        self.urls.append(url)
        return {"result": []}

    def post_multipart(self, url, fields, file_field, file_name, file_bytes):
        self.urls.append(url)
        return {"ok": True, "result": {"message_id": 1}}


def _drive(entry, token, http, tmp_path):
    """Call one public entry point with the given token and transport."""
    if entry == "send_item":
        return T.send_item(http, token=token, chat_id=42,
                           item={"meta": {"id": "p-1", "kind": "onpage-fix",
                                          "title": "T", "target": ""},
                                 "body": "b"})
    if entry == "send_document":
        doc = tmp_path / "r.html"
        doc.write_bytes(b"<p>x</p>")
        return T.send_document(token, 42, doc, transport=http)
    if entry == "poll_decisions":
        return T.poll_decisions(http, token=token, chat_id=42, offset=0)
    raise AssertionError(f"unknown entry point: {entry}")


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_call_site_sanitizes_token_before_the_transport(entry, tmp_path):
    http = RecordingHTTP()
    _drive(entry, TRAILING_NEWLINE_TOKEN, http, tmp_path)
    assert http.urls, f"{entry} never reached the transport"
    for url in http.urls:
        assert TRAILING_NEWLINE_TOKEN not in url, (
            f"{entry} handed the transport a URL carrying the raw token; "
            "sanitize_bot_token is not wired at that call site")
        assert CLEAN_TOKEN in url, f"{entry} did not send the sanitized token"


@pytest.mark.parametrize("entry", ENTRY_POINTS)
def test_call_site_fails_closed_on_control_character_token(entry, tmp_path):
    http = RecordingHTTP()
    try:
        _drive(entry, INTERIOR_CONTROL_TOKEN, http, tmp_path)
    except RuntimeError as e:
        assert "SECRET-TOKEN" not in str(e)
        assert "control characters" in str(e)
    else:
        raise AssertionError(
            f"{entry} accepted a control-character token; "
            "sanitize_bot_token is not wired at that call site")
    assert http.urls == [], (
        f"{entry} reached the transport with an unsanitized token: {http.urls}")


# -- advisory redaction at the outbound sinks ---------------------------------
#
# The guard reports; it never blocks. Both sinks must send exactly once with
# a planted credential in hand, and must still send when the scan itself
# breaks - a guard that stops a send is worse than the leak it watched for.

from core import redact  # noqa: E402

PLANTED = "api_key=FAKE-API-KEY-VALUE-abcdefghij"


class CountingHTTP:
    def __init__(self):
        self.posts = []
        self.multiparts = []

    def post(self, url, payload):
        self.posts.append(payload)
        return {"ok": True, "result": {"message_id": 1}}

    def post_multipart(self, url, fields, file_field, file_name, file_bytes):
        self.multiparts.append(fields)
        return {"ok": True, "result": {"message_id": 2}}


def _item(body):
    return {"meta": {"id": "p-1", "kind": "onpage-fix", "title": "T",
                     "target": ""}, "body": body}


def test_send_item_warns_about_a_planted_credential_and_still_sends():
    http = CountingHTTP()
    T.send_item(http, token="SECRET-TOKEN-123", chat_id=42, item=_item(PLANTED))
    assert len(http.posts) == 1, "the guard changed how many sends happen"
    assert "redaction:" in http.posts[0]["text"]
    assert "1 high" in http.posts[0]["text"]
    assert PLANTED in http.posts[0]["text"], "the guard altered the message body"


def test_send_item_stays_quiet_on_clean_content():
    http = CountingHTTP()
    T.send_item(http, token="SECRET-TOKEN-123", chat_id=42,
                item=_item("rewrite the title to lead with the query"))
    assert "redaction:" not in http.posts[0]["text"]


def test_send_item_still_sends_when_the_scan_raises(monkeypatch):
    def boom(_text):
        raise RuntimeError("scanner exploded")

    monkeypatch.setattr(redact, "scan", boom)
    http = CountingHTTP()
    T.send_item(http, token="SECRET-TOKEN-123", chat_id=42, item=_item(PLANTED))
    assert len(http.posts) == 1
    assert PLANTED in http.posts[0]["text"]


def test_send_document_warns_in_the_caption_and_still_sends(tmp_path):
    doc = tmp_path / "report.html"
    doc.write_bytes(b"<p>x</p>")
    http = CountingHTTP()
    T.send_document("SECRET-TOKEN-123", 42, doc,
                    caption=f"Week of 2026-07-20\n{PLANTED}", transport=http)
    assert len(http.multiparts) == 1
    caption = http.multiparts[0]["caption"]
    assert "redaction:" in caption and "1 high" in caption
    assert "Week of 2026-07-20" in caption


def test_send_document_still_sends_when_the_scan_raises(tmp_path, monkeypatch):
    def boom(_text):
        raise RuntimeError("scanner exploded")

    monkeypatch.setattr(redact, "scan", boom)
    doc = tmp_path / "report.html"
    doc.write_bytes(b"<p>x</p>")
    http = CountingHTTP()
    T.send_document("SECRET-TOKEN-123", 42, doc, caption=PLANTED, transport=http)
    assert len(http.multiparts) == 1
    assert http.multiparts[0]["caption"] == PLANTED


def test_send_document_without_a_caption_is_unchanged(tmp_path):
    doc = tmp_path / "report.html"
    doc.write_bytes(b"<p>x</p>")
    http = CountingHTTP()
    T.send_document("SECRET-TOKEN-123", 42, doc, transport=http)
    assert "caption" not in http.multiparts[0]
