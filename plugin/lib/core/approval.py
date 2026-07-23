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
