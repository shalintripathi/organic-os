"""Channel-neutral approval operations over the brain repo."""
from __future__ import annotations
import json
from pathlib import Path
from . import contracts as C
from . import telegram as T


def pending(root):
    items = []
    for folder in ("briefs", "proposals"):
        for f in sorted((Path(root) / folder).glob("*.md")):
            item = C.load_item(f)
            if item["meta"]["status"] == "proposed":
                item["path"] = f
                items.append(item)
    return items


def find(root, item_id: str):
    for folder in ("briefs", "proposals"):
        for f in (Path(root) / folder).glob("*.md"):
            try:
                meta = C.load_item(f).get("meta") or {}
            except Exception:
                continue  # a malformed sibling file must not break resolution
            if meta.get("id") == item_id:
                return f
    raise C.ContractError(f"no item {item_id}")


def notify_pending(root, send, kinds=None, limit=None) -> list:
    """Send every un-notified proposed item exactly once, marking each as it goes.

    `send` is a callable taking (item_path, item_dict) and performing the
    actual delivery (telegram, in-session print, whatever the channel is).
    Returns a list of (path, outcome) where outcome is 'sent' |
    'skipped-already-notified' | 'failed'.

    An item is marked notified ONLY after `send` returns without raising, so a
    failed send is retried on the next run rather than silently swallowed.
    This exists because the same three steps written as prose in a skill get
    skipped: a live instance ran twelve days with every item still marked
    notified=NO over a working, reachable bot. Send-then-mark belongs in one
    call so a caller cannot send without marking, or mark without sending.

    `kinds` filters by item kind (a single kind or an iterable of them);
    `limit` caps how many sends are attempted, counting attempts rather than
    items, so already-notified items never consume the budget. One failing
    item never stops the batch.
    """
    if isinstance(kinds, str):
        kinds = {kinds}
    elif kinds is not None:
        kinds = set(kinds)

    results, attempted = [], 0
    for item in pending(root):
        if kinds is not None and item["meta"].get("kind") not in kinds:
            continue
        path = item["path"]
        if C.is_notified(item):
            results.append((path, "skipped-already-notified"))
            continue
        if limit is not None and attempted >= limit:
            break
        attempted += 1
        try:
            send(path, item)
        except Exception:
            # Unmarked and reported: the next run retries it. Swallowing the
            # failure here would turn a broken channel into permanent silence.
            results.append((path, "failed"))
            continue
        C.mark_notified(path)
        results.append((path, "sent"))
    return results


def record_decision(root, item_id: str, decision: str, actor: str, channel: str,
                    note: str | None = None) -> None:
    """Records a decision. Replay-tolerant: poll loops may deliver the same
    decision twice, and a replay within the TTL is a silent no-op. When the
    item already sits at the decision but its latest matching record has
    expired per the site TTL, the same call is the re-confirm path: a fresh
    approval entry is appended, refreshing the clock the gates check."""
    path = find(root, item_id)
    item = C.load_item(path)
    if item["meta"]["status"] == decision:
        matching = [a for a in item["meta"].get("approvals") or []
                    if isinstance(a, dict) and a.get("decision") == decision
                    and a.get("at")]
        latest = max(matching, key=lambda a: a["at"]) if matching else None
        if latest is not None and C._entry_expired(latest, C.approval_ttl_days(root)):
            entry = {"actor": actor, "channel": channel, "decision": decision,
                     "at": C._now()}
            if note:
                entry["note"] = note
            item["meta"]["approvals"].append(entry)
            C._dump(Path(path), item["meta"], item["body"])
        return
    C.set_status(path, decision, actor=actor, channel=channel, note=note)
    C.rebuild_queue(root)


# -- telegram polling -----------------------------------------------------

def _offset_path(root) -> Path:
    return Path(root) / "approvals" / "telegram-offset.json"


def _load_offset(root) -> int:
    p = _offset_path(root)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("offset", 0))
    except (json.JSONDecodeError, OSError, ValueError):
        return 0


def _save_offset(root, offset: int) -> None:
    p = _offset_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    C._atomic_write(p, json.dumps({"offset": offset}) + "\n")


def process_telegram_decisions(root, token: str, chat_id, transport=None) -> list:
    """Poll Telegram once and apply decisions tolerantly. Returns [(item_id, outcome)].

    Outcomes: 'recorded', 'stale' (item already past proposed), 'unknown'
    (id not in this brain). Persists the poll offset at
    <root>/approvals/telegram-offset.json so replies are acknowledged across
    runs (Telegram drops unacked updates after ~24h).
    """
    http = transport or T.UrllibHTTP()
    offset = _load_offset(root)
    decisions, last = T.poll_decisions(http, token, chat_id, offset=offset)

    results = []
    for item_id, decision, reason in decisions:
        try:
            find(root, item_id)
        except C.ContractError:
            results.append((item_id, "unknown"))
            continue
        try:
            record_decision(root, item_id, decision, actor="telegram",
                            channel="telegram", note=reason or None)
            results.append((item_id, "recorded"))
        except C.ContractError as e:
            if "illegal transition" in str(e):
                results.append((item_id, "stale"))
            else:
                raise

    if last != offset:
        _save_offset(root, last)
    return results
