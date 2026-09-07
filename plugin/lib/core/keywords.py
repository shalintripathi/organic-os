"""The single writer for the tracked-keyword set (<brain>/keywords/tracking.yaml).

Skills used to instruct "edit the YAML by hand", re-implementing the same
normalize-dedupe-write logic in prose (same motivation as registry.unregister
in #24). Entries are normalized dicts {term, added, source}; hand-written
plain strings are tolerated on read and normalized, never rejected. Adding a
tracked keyword is still a strategy mutation gated through the approval
queue - this module is the writer that runs AFTER approval, not a bypass.
"""
from __future__ import annotations
import datetime as _dt
from pathlib import Path

import yaml

from . import contracts as C


def _path(root) -> Path:
    return Path(root) / "keywords" / "tracking.yaml"


def _normalize(entry, path: Path) -> dict:
    if isinstance(entry, dict):
        if "term" not in entry:
            raise ValueError(
                f"{path} has an entry with no 'term' key: {entry!r}. "
                "Each tracked keyword needs at least a term.")
        return {"term": str(entry["term"]),
                "added": entry.get("added"),
                "source": entry.get("source") or "hand-edited"}
    if isinstance(entry, (str, int, float)):
        # Hand-written shorthand: a bare scalar is the term itself.
        return {"term": str(entry), "added": None, "source": "hand-edited"}
    raise ValueError(
        f"{path} has an entry that is neither a mapping nor a plain "
        f"string: {entry!r}")


def load_tracked(root) -> list[dict]:
    """Read the tracked set, normalized to [{term, added, source}, ...].

    Tolerates a missing file and the scaffold's ``keywords: []`` (both ->
    []), and hand-written plain-string entries (term=the string, added=None,
    source="hand-edited"). A file that does not parse or has the wrong shape
    raises ValueError naming the file, never a raw parse trace.
    """
    path = _path(root)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"{path} is not valid YAML: {exc}") from exc
    if data is None:
        return []
    if isinstance(data, dict):
        entries = data.get("keywords") or []
    elif isinstance(data, list):
        entries = data  # a hand-written bare list is the keywords themselves
    else:
        raise ValueError(
            f"{path} should be a mapping with a 'keywords' list "
            f"(scaffold: 'keywords: []'), got {type(data).__name__}")
    if not isinstance(entries, list):
        raise ValueError(
            f"{path} has a 'keywords' key that is not a list, "
            f"got {type(entries).__name__}")
    return [_normalize(e, path) for e in entries]


def save_tracked(root, entries: list) -> None:
    """Atomic write of the tracked set. Dedupes case-insensitively on term,
    keeping the earliest entry (first occurrence); order is stable, as given.
    """
    path = _path(root)
    deduped: list[dict] = []
    seen: set[str] = set()
    for entry in entries:
        norm = _normalize(entry, path)
        key = norm["term"].lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(norm)
    path.parent.mkdir(parents=True, exist_ok=True)
    C._atomic_write(path, yaml.safe_dump({"keywords": deduped}, sort_keys=False,
                                         allow_unicode=True))


def add_tracked(root, terms: list, source: str, today: str | None = None) -> dict:
    """Add terms to the tracked set. Idempotent: already-tracked terms
    (case-insensitive, including duplicates within one call) are skipped.
    Returns {"added": [...], "skipped": [...]} in the order given.
    """
    if today is None:
        today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    entries = load_tracked(root)
    tracked = {e["term"].lower() for e in entries}
    added: list[str] = []
    skipped: list[str] = []
    for term in terms:
        term = str(term)
        if term.lower() in tracked:
            skipped.append(term)
            continue
        tracked.add(term.lower())
        entries.append({"term": term, "added": today, "source": source})
        added.append(term)
    if added:
        save_tracked(root, entries)
    return {"added": added, "skipped": skipped}
