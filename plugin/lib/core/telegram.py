"""Telegram adapter. Transport is injected so tests never touch the network.

Real transport (used by skills):
    from core.telegram import UrllibHTTP
    http = UrllibHTTP()
Approval grammar in chat: 'approve <item-id>' or 'reject <item-id> [reason]'.
Reply-context grammar: replying to a message that contains an item id, a bare
decision word resolves against that id - approve/approved/yes/ok/go ahead/
ship it/lgtm/thumbs-up approve it, reject/rejected/no/thumbs-down reject it;
the phrase must start the reply, and trailing text after it is kept as the
note. The strict grammar takes precedence when both could apply.

The negative set is deliberately narrow: deferrals ("wait", "hold",
"later") are NOT decisions and must resolve nothing - deferring is not
rejecting, so the item stays pending for a real answer.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

API = "https://api.telegram.org/bot{token}/{method}"
_DECISION = re.compile(r"^(approve|reject)\s+([bp]-[\w-]+)\s*(.*)$", re.I)
# Item ids as create_item mints them: [bp]-YYYYMMDD-slug (lowercase slug).
_ITEM_ID = re.compile(r"\b[bp]-\d{8}-[a-z0-9][a-z0-9-]*")
_REPLY_VERBS = {"approved": "approved", "approve": "approved", "yes": "approved",
                "ok": "approved", "go ahead": "approved", "ship it": "approved",
                "lgtm": "approved", "\U0001F44D": "approved",
                "rejected": "rejected", "reject": "rejected", "no": "rejected",
                "\U0001F44E": "rejected"}
# Longest alternatives first so 'approved' is not split as 'approve' + 'd'.
_REPLY_DECISION = re.compile(
    "^(" + "|".join(re.escape(v) for v in sorted(_REPLY_VERBS, key=len, reverse=True))
    + r")(?:[\s,.:;-]+(.*))?$", re.I | re.S)


def _reply_decision(msg: dict):
    """Resolve a reply-context decision: (item_id, decision, note) or None.

    Only fires when the update is a reply, the replied-to text carries an
    item id, and the reply's own text is (or starts with) a decision word.
    """
    reply = msg.get("reply_to_message") or {}
    ids = _ITEM_ID.findall(reply.get("text") or "")
    if not ids:
        return None
    m = _REPLY_DECISION.match(msg.get("text", "").strip())
    if not m:
        return None
    verb, note = m.group(1).lower(), (m.group(2) or "").strip()
    return ids[0], _REPLY_VERBS[verb], note


def sanitize_bot_token(token: str) -> str:
    """Strip surrounding whitespace; reject whitespace/control characters.

    Tokens often come from env files with a trailing newline. Those control
    characters make urllib raise InvalidURL with the full URL (and token) in
    the message. Fail closed with a message that never echoes the secret.
    """
    if token is None:
        raise RuntimeError("telegram bot token is missing")
    cleaned = str(token).strip()
    if not cleaned:
        raise RuntimeError("telegram bot token is empty")
    # Reject any remaining whitespace or ASCII controls (incl. newline/tab).
    if any(ch.isspace() or ord(ch) < 32 for ch in cleaned):
        raise RuntimeError(
            "telegram bot token contains whitespace or control characters; "
            "strip the token (e.g. trailing newline from a file) and retry"
        )
    return cleaned


def _telegram_api_error(exc: BaseException) -> RuntimeError:
    """Re-raise transport failures without the token-bearing URL."""
    if isinstance(exc, urllib.error.HTTPError):
        return RuntimeError(f"telegram api error: HTTP {exc.code} {exc.reason}")
    if isinstance(exc, urllib.error.URLError):
        return RuntimeError(f"telegram api error: {exc.reason}")
    # InvalidURL / ValueError / anything else that may embed the URL.
    return RuntimeError("telegram api error: invalid request")


class UrllibHTTP:
    # Errors are re-raised with status/reason only: the URL embeds the bot
    # token and must never surface in a printed exception. Catch broader than
    # HTTPError/URLError so InvalidURL (control chars in token) and ValueError
    # (scheme-less URL) cannot leak the token (issue #12).
    def post(self, url, payload):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise _telegram_api_error(e) from None
        except urllib.error.URLError as e:
            raise _telegram_api_error(e) from None
        except Exception as e:
            # InvalidURL / ValueError (scheme-less Request) may embed the URL.
            raise _telegram_api_error(e) from None

    def get(self, url, params):
        try:
            with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params),
                                        timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise _telegram_api_error(e) from None
        except urllib.error.URLError as e:
            raise _telegram_api_error(e) from None
        except Exception as e:
            raise _telegram_api_error(e) from None

    def post_multipart(self, url, fields, file_field, file_name, file_bytes):
        boundary = "organic-os-" + uuid.uuid4().hex
        parts = []
        for name, value in fields.items():
            parts.append((f"--{boundary}\r\n"
                          f'Content-Disposition: form-data; name="{name}"\r\n'
                          f"\r\n{value}\r\n").encode())
        parts.append((f"--{boundary}\r\n"
                      f'Content-Disposition: form-data; name="{file_field}"; '
                      f'filename="{file_name}"\r\n'
                      f"Content-Type: application/octet-stream\r\n\r\n").encode()
                     + file_bytes + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        body = b"".join(parts)
        try:
            req = urllib.request.Request(
                url, data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise _telegram_api_error(e) from None
        except urllib.error.URLError as e:
            raise _telegram_api_error(e) from None
        except Exception as e:
            raise _telegram_api_error(e) from None


def send_item(http, token: str, chat_id, item: dict) -> None:
    m = item["meta"]
    text = (f"organic-os proposal {m['id']}\n"
            f"[{m['kind']}] {m['title']}\n"
            f"target: {m.get('target') or '-'}\n\n"
            f"{item['body'][:800]}\n\n"
            f"Reply to this message with approve or reject "
            f"(a bare 'approved' works as a reply).\n"
            f"Or send: approve {m['id']}  |  reject {m['id']} <reason>")
    http.post(API.format(token=sanitize_bot_token(token), method="sendMessage"),
              {"chat_id": chat_id, "text": text})


def send_document(token: str, chat_id, file_path, caption=None, transport=None):
    """Deliver a file (the weekly report as HTML or PDF) via sendDocument.

    Multipart is built by the transport so tests capture the payload
    without touching the network; the default transport is the real one.
    """
    http = transport if transport is not None else UrllibHTTP()
    path = Path(file_path)
    fields = {"chat_id": str(chat_id)}
    if caption:
        fields["caption"] = caption
    return http.post_multipart(API.format(token=sanitize_bot_token(token), method="sendDocument"),
                               fields, "document", path.name, path.read_bytes())


def poll_decisions(http, token: str, chat_id, offset: int = 0):
    data = http.get(API.format(token=sanitize_bot_token(token), method="getUpdates"),
                    {"offset": offset + 1, "timeout": 0})
    decisions, last = [], offset
    for u in data.get("result", []):
        last = max(last, u["update_id"])
        msg = u.get("message") or {}
        if str(msg.get("chat", {}).get("id")) != str(chat_id):
            continue
        m = _DECISION.match(msg.get("text", "").strip())
        if m:  # strict grammar wins whenever it matches, reply or not
            verb, item_id, reason = m.groups()
            decisions.append((item_id,
                              "approved" if verb.lower() == "approve" else "rejected",
                              reason.strip()))
            continue
        resolved = _reply_decision(msg)
        if resolved:
            decisions.append(resolved)
    return decisions, last
