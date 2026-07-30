"""File contracts for the site brain. The ONLY code that reads/writes brain files.

Item = a brief or proposal: markdown file with YAML frontmatter.
Lifecycle: proposed -> approved|rejected; approved -> applied|drafted|failed|
partially-applied; partially-applied -> applied|failed; drafted -> published;
applied|published -> measured.
("failed" marks an approved item whose apply-verify failed and was rolled back;
it happens pre-applied, so applied -> failed is deliberately illegal.
"partially-applied" marks an approved item where some changes landed and the
rest hit a permission or capability wall; a human finishes it -> applied, or
the partial work is rolled back -> failed. See docs/adr/0007.)
Approvals expire: both gates require the latest approved record to be
younger than the site TTL (approvals.ttl_days, default 30 days). An expired
item keeps its status; re-approving it refreshes the clock. See docs/adr/0008.
Skillbook: append-only entries with IDs; updates touch single entries only.
"""
from __future__ import annotations
import datetime as _dt
import os
import re
from pathlib import Path

import yaml

TRANSITIONS = {
    "proposed": {"approved", "rejected"},
    "approved": {"applied", "drafted", "failed", "partially-applied"},
    "partially-applied": {"applied", "failed"},
    "drafted": {"published"},
    "applied": {"measured"},
    "published": {"measured"},
}
KINDS = {"onpage-fix", "content-brief", "publish", "strategy"}
# content-brief shape; absence of the frontmatter field means "explainer".
BRIEF_TYPES = {"explainer", "comparison"}

SCHEMA_VERSION = 1


class ContractError(Exception):
    pass


# -- schema versioning ---------------------------------------------------------

def check_schema(root) -> dict:
    """Returns {"version": int, "compatible": bool, "action": str}.

    Missing site-profile.yaml -> version 0, compatible False, action
    "run /organic-os:setup". Missing schema_version key (pre-v0.1.3 brain)
    -> version 1 assumed, compatible True, action "stamp" (layout is
    identical; setup update mode adds the key). version == SCHEMA_VERSION
    -> compatible True, action "none". version < SCHEMA_VERSION ->
    compatible False, action "run /organic-os:setup to migrate".
    version > SCHEMA_VERSION -> compatible False, action "update the
    plugin (/plugin update organic-os)".
    """
    path = Path(root) / "site-profile.yaml"
    if not path.exists():
        return {"version": 0, "compatible": False, "action": "run /organic-os:setup"}
    data = yaml.safe_load(path.read_text()) or {}
    if "schema_version" not in data:
        return {"version": 1, "compatible": True, "action": "stamp"}
    version = data["schema_version"]
    if version == SCHEMA_VERSION:
        return {"version": version, "compatible": True, "action": "none"}
    if version < SCHEMA_VERSION:
        return {"version": version, "compatible": False,
                "action": "run /organic-os:setup to migrate"}
    return {"version": version, "compatible": False,
            "action": "update the plugin (/plugin update organic-os)"}


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -- approval expiry -----------------------------------------------------------

DEFAULT_APPROVAL_TTL_DAYS = 30


def approval_ttl_days(root) -> int:
    """Approval TTL for this site, in days. Reads `approvals: {ttl_days: n}`
    from site-profile.yaml; default 30. The key is additive (schema stays 1;
    absence means the default)."""
    path = Path(root) / "site-profile.yaml"
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    ttl = ((data or {}).get("approvals") or {}).get("ttl_days",
                                                   DEFAULT_APPROVAL_TTL_DAYS)
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 1:
        raise ContractError(
            "ttl_days must be positive; to disable expiry set a large value deliberately")
    return ttl


def latest_approval(item) -> dict | None:
    """Newest approvals entry with decision == 'approved', by its timestamp."""
    approved = [a for a in item["meta"].get("approvals") or []
                if isinstance(a, dict) and a.get("decision") == "approved"
                and a.get("at")]
    return max(approved, key=lambda a: a["at"]) if approved else None


def _entry_expired(entry: dict, ttl: int) -> bool:
    """True when the entry's timestamp is at least `ttl` days old (UTC dates)."""
    approved_date = _dt.date.fromisoformat(str(entry["at"])[:10])
    age = (_dt.datetime.now(_dt.timezone.utc).date() - approved_date).days
    return age >= ttl


def _require_fresh_approval(path, item) -> None:
    """Blocks when the latest approved record is older than the site TTL.
    Expiry means re-confirm, never silent rejection: the item's status is
    left exactly as it was; only the gate refuses until a fresh approval
    is recorded."""
    latest = latest_approval(item)
    if latest is None:
        return
    root = Path(path).resolve().parent.parent  # items live at <root>/{briefs,proposals}/
    ttl = approval_ttl_days(root)
    if _entry_expired(latest, ttl):
        approved_date = _dt.date.fromisoformat(str(latest["at"])[:10])
        raise ContractError(
            f"MUTATION BLOCKED: approval for {Path(path).name} expired "
            f"(approved {approved_date.isoformat()}, ttl {ttl} days) - "
            f"re-confirm with: python3 -m core approve {path} "
            "--actor <you> --channel <channel>")


# -- editorial policy ----------------------------------------------------------

# The enforceable editorial floor: ce-qa reads this policy and enforces it
# as hard checks; free-text brand rulebook prose still applies on top (the
# policy keys are the floor, the prose is the voice). These defaults are
# canonical - the site-profile template, docs/site-repo-contract.md, and
# plugin/agents/ce-qa.md quote them (docs/INFORMATION-MAP.md).
EDITORIAL_DEFAULTS = {
    "oversight_threshold": 7,      # ce-editor score at/above -> recommend human line-edit
    "internal_links_min": 0,       # min same-site links per draft; 0 = off
    "external_links_max": None,    # cap on external links; None = no cap
    "images_min": 0,               # min in-content images (or attached briefs); 0 = off
    "sourcing": "key-claims",      # "key-claims" | "every-claim"
    "require_reviewer_note": False,  # True: draft notes must name a human reviewer
}
SOURCING_MODES = ("key-claims", "every-claim")


def _editorial_count(policy: dict, key: str, hi: int | None = None) -> None:
    v = policy[key]
    bounds = f"0-{hi}" if hi is not None else "0 or more"
    if not isinstance(v, int) or isinstance(v, bool) or v < 0 \
            or (hi is not None and v > hi):
        raise ContractError(
            f"editorial.{key} must be an integer ({bounds}), got {v!r}")


def editorial_policy(root) -> dict:
    """The site's editorial policy: the `editorial:` site-profile section
    merged over EDITORIAL_DEFAULTS. Absent keys (or a missing section, or
    a missing profile) mean the defaults - the section is additive,
    schema_version stays 1. Unknown keys are ignored (a newer plugin's
    additive key never breaks an older reader); an invalid value raises
    ContractError naming the key."""
    path = Path(root) / "site-profile.yaml"
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    section = (data or {}).get("editorial")
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise ContractError(
            f"editorial: must be a mapping of policy keys, got {section!r}")
    policy = dict(EDITORIAL_DEFAULTS)
    policy.update({k: v for k, v in section.items() if k in EDITORIAL_DEFAULTS})
    _editorial_count(policy, "oversight_threshold", hi=10)
    _editorial_count(policy, "internal_links_min")
    _editorial_count(policy, "images_min")
    if policy["external_links_max"] is not None:
        _editorial_count(policy, "external_links_max")
    if policy["sourcing"] not in SOURCING_MODES:
        raise ContractError(
            f"editorial.sourcing must be one of {list(SOURCING_MODES)}, "
            f"got {policy['sourcing']!r}")
    if not isinstance(policy["require_reviewer_note"], bool):
        raise ContractError(
            "editorial.require_reviewer_note must be true or false, "
            f"got {policy['require_reviewer_note']!r}")
    return policy


# -- signals ------------------------------------------------------------------

def append_signal(root, text: str, date: str | None = None) -> Path:
    root = Path(root)
    date = date or _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    f = root / "signals" / f"{date}.md"
    stamp = _now()
    with f.open("a") as fh:
        fh.write(f"- [{stamp}] {text}\n")
    return f


# -- items (briefs + proposals) ----------------------------------------------

def _folder(root: Path, kind: str) -> Path:
    return root / ("briefs" if kind == "content-brief" else "proposals")


def create_item(root, kind: str, slug: str, title: str, body: str,
                target: str, source: str, brief_type: str | None = None) -> Path:
    if kind not in KINDS:
        raise ContractError(f"unknown kind {kind!r}")
    if brief_type is not None:
        if kind != "content-brief":
            raise ContractError(
                f"brief_type applies to content-brief items only, not {kind!r}")
        if brief_type not in BRIEF_TYPES:
            raise ContractError(
                f"unknown brief_type {brief_type!r} - one of {sorted(BRIEF_TYPES)}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ContractError(f"bad slug {slug!r} - use lowercase letters, digits, hyphens")
    root = Path(root)
    date = _dt.datetime.now(_dt.timezone.utc).date().strftime("%Y%m%d")
    path = _folder(root, kind) / f"{date}-{slug}.md"
    if path.exists():
        raise ContractError(f"item exists: {path}")
    meta = {"id": f"{'b' if kind == 'content-brief' else 'p'}-{date}-{slug}",
            "kind": kind, "status": "proposed", "created": _now(),
            "title": title, "target": target, "source": source, "approvals": []}
    if brief_type is not None:
        meta["brief_type"] = brief_type
    _dump(path, meta, body)
    return path


def load_item(path) -> dict:
    try:
        raw = Path(path).read_text()
    except FileNotFoundError:
        raise ContractError(f"no such item: {path}") from None
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, re.S)
    if not m:
        raise ContractError(f"no frontmatter: {path}")
    try:
        meta = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        raise ContractError(f"bad frontmatter yaml: {path}") from None
    return {"meta": meta, "body": m.group(2)}


def set_status(path, status: str, actor: str, channel: str | None = None,
               note: str | None = None) -> None:
    item = load_item(path)
    cur = item["meta"]["status"]
    if status not in TRANSITIONS.get(cur, set()):
        raise ContractError(f"illegal transition {cur} -> {status}")
    item["meta"]["status"] = status
    if status in {"approved", "rejected"}:
        entry = {"actor": actor, "channel": channel or "unknown",
                 "decision": status, "at": _now()}
        if note:
            entry["note"] = note
        item["meta"]["approvals"].append(entry)
    elif note:
        # Lifecycle notes (e.g. what a human must finish on a
        # partially-applied item) live on the item, not in approvals.
        item["meta"]["status_note"] = note
    _dump(Path(path), item["meta"], item["body"])
    if status == "rejected":
        _record_rejection(Path(path), item["meta"], actor, note)
    _refresh_queue(Path(path))


def _refresh_queue(path: Path) -> None:
    """Best-effort rebuild of the derived approvals queue after a status change.

    `approvals/queue.md` is derived: it is only ever true because something
    rebuilt it. The CLI did; a skill calling set_status directly did not, so
    the queue could sit frozen for days while the pipeline moved underneath it
    - an operator reading a stale queue concludes the loop is dead. Making the
    refresh part of the write puts the guarantee in the contract layer instead
    of in every caller.

    Runs only after the item is durably written, and NEVER fails the status
    change: any exception here is swallowed. A derived-file refresh must not
    roll back or block a real state transition (same reasoning as the advisory
    redaction guard at the outbound sinks - a guard that becomes the reason a
    transition does not happen is a worse failure than the one it watched for).
    """
    try:
        # items live at <root>/{briefs,proposals}/
        rebuild_queue(path.resolve().parent.parent)
    except Exception:
        pass


def _record_rejection(path: Path, meta: dict, actor: str, note: str | None) -> None:
    """A rejection outlives the item it killed. Without a durable record the
    loop re-proposes the same work next week, because nothing outside the
    item file remembers the human said no. Written after the transition is
    committed - the status change is the contract, the record is its memory.

    Imported here, not at module scope: decisions.py imports this module for
    the atomic writer, so a top-level import would be circular."""
    from . import decisions as _decisions
    title = str(meta.get("title") or path.stem)
    root = path.resolve().parent.parent  # items live at <root>/{briefs,proposals}/
    try:
        where = str(path.resolve().relative_to(root))
    except ValueError:
        where = str(path)
    _decisions.record(
        root,
        title=f"rejected: {title}",
        choice="rejected",
        rationale=note or "no reason recorded at rejection",
        actor=actor,
        scope=title,
        item=where)


def reset_to_proposed(path, actor: str, note: str | None = None) -> None:
    """Repair path for illegal birth states only. Items are born `proposed`
    via create_item; a file that entered the brain with any other status and
    an empty approvals list can neither be approved (its status has no legal
    transition to approved) nor pass a lineage gate, so it jams the pipeline.
    This resets such an item to proposed so the normal lifecycle can start.

    GUARDED: refuses any item with approval history - those reached their
    status legally and must move through status transitions. The repair is
    recorded as a status_note so the item carries its own audit trail."""
    item = load_item(path)
    name = Path(path).name
    if item["meta"].get("approvals"):
        raise ContractError(
            f"cannot reset {name}: item has approval history; use status transitions")
    cur = item["meta"]["status"]
    if cur == "proposed":
        raise ContractError(f"{name} is already proposed - nothing to repair")
    item["meta"]["status"] = "proposed"
    stamp = (f"reset to proposed by {actor} at {_now()} "
             f"(born {cur} with no approvals)")
    if note:
        stamp += f": {note}"
    item["meta"]["status_note"] = stamp
    _dump(Path(path), item["meta"], item["body"])
    _refresh_queue(Path(path))


def require_approved(path) -> dict:
    item = load_item(path)
    if item["meta"]["status"] != "approved":
        raise ContractError(
            f"MUTATION BLOCKED: {Path(path).name} is '{item['meta']['status']}', "
            "needs 'approved' with a recorded approval")
    _require_fresh_approval(path, item)
    return item


def mark_notified(path) -> None:
    item = load_item(path)
    item["meta"]["notified_at"] = _now()
    _dump(Path(path), item["meta"], item["body"])


def is_notified(item) -> bool:
    return bool(item["meta"].get("notified_at"))


# -- connectors -----------------------------------------------------------

CONNECTOR_STATUSES = {"verified", "unavailable", "declined"}


def record_connector(profile_path, name: str, status: str, context: str) -> None:
    """Updates the connectors: block in site-profile.yaml. status:
    'verified'|'unavailable'|'declined'. context: where the probe ran, e.g.
    'local-cli', 'cowork-cloud', 'ci'. Stored as 'name: {status: ...,
    context: ..., checked: <UTC date>}'. Never stores bare booleans.

    Only the named connector entry is touched - every other key in the
    connectors: block and the rest of the profile is left exactly as read,
    including pre-wave-1 profiles where sibling connectors are still bare
    strings ('available'/'absent'/'unknown').
    """
    if status not in CONNECTOR_STATUSES:
        raise ContractError(
            f"connector status must be one of {sorted(CONNECTOR_STATUSES)}, got {status!r}")
    path = Path(profile_path)
    data = yaml.safe_load(path.read_text()) or {}
    connectors = data.setdefault("connectors", {})
    connectors[name] = {
        "status": status,
        "context": context,
        "checked": _dt.datetime.now(_dt.timezone.utc).date().isoformat(),
    }
    _atomic_write(path, yaml.safe_dump(data, sort_keys=False))


# -- postflight scorecard ---------------------------------------------------

SCORECARD_STATUSES = {"pass", "degraded", "fail"}


def write_scorecard(root, checks: list) -> Path:
    """checks: list of {'name','status'('pass'|'degraded'|'fail'),'detail','fix'}.
    Writes <root>/runs/<UTCdate>-setup-scorecard/REPORT.md with a pass/degraded/
    fail table and the exact fix command per non-pass row. Returns the path.
    """
    today = _dt.datetime.now(_dt.timezone.utc).date().strftime("%Y%m%d")
    folder = Path(root) / "runs" / f"{today}-setup-scorecard"
    folder.mkdir(parents=True, exist_ok=True)

    lines = [f"# Setup scorecard - {today}", "",
             "| Check | Status | Detail |", "|---|---|---|"]
    fixes = []
    for c in checks:
        status = c["status"]
        if status not in SCORECARD_STATUSES:
            raise ContractError(
                f"scorecard status must be one of {sorted(SCORECARD_STATUSES)}, got {status!r}")
        lines.append(f"| {c['name']} | {status} | {c.get('detail', '')} |")
        if status != "pass":
            fix = c.get("fix", "")
            if fix:
                fixes.append(f"- **{c['name']}**: `{fix}`")

    if fixes:
        lines += ["", "## Fixes", ""] + fixes

    path = folder / "REPORT.md"
    path.write_text("\n".join(lines) + "\n")
    return path


def require_approval_lineage(path) -> dict:
    """For post-approval lifecycle stages (e.g. drafted) where require_approved's status check no longer applies; safe because approved -> rejected is an illegal transition, so an approved lineage cannot be revoked. The lineage must also be fresh: an approved decision older than the site TTL blocks until re-confirmed."""
    item = load_item(path)
    approvals = item["meta"].get("approvals") or []
    if not any(a.get("decision") == "approved" for a in approvals):
        raise ContractError(
            f"MUTATION BLOCKED: {Path(path).name} has no approved decision in its lineage")
    _require_fresh_approval(path, item)
    return item


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text)
    os.replace(tmp, path)


def _dump(path: Path, meta: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, "---\n" + yaml.safe_dump(meta, sort_keys=False).strip()
                  + "\n---\n" + body.lstrip("\n"))


# -- skillbook ----------------------------------------------------------------

_ENTRY = re.compile(r"^(~~)?(S-\d{3,}) \[evidence: (\w+)\] "
                    r"\[helpful: (\d+), harmful: (\d+), last-confirmed: ([0-9-]+)\] (.*)$")


def skillbook_append(root, text: str, evidence: str, source: str) -> str:
    if evidence not in {"strong", "moderate", "anecdotal"}:
        raise ContractError("evidence must be strong|moderate|anecdotal")
    book = Path(root) / "skillbook.md"
    ids = [int(m.group(2)[2:]) for line in book.read_text().splitlines()
           if (m := _ENTRY.match(line))]
    sid = f"S-{(max(ids) + 1 if ids else 1):03d}"
    today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
    with book.open("a") as fh:
        fh.write(f"{sid} [evidence: {evidence}] [helpful: 0, harmful: 0, "
                 f"last-confirmed: {today}] {text} ({source})\n")
    return sid


def skillbook_update(root, sid: str, helpful: int = 0, harmful: int = 0,
                     deprecate: bool = False, edit: str | None = None) -> None:
    book = Path(root) / "skillbook.md"
    out, found = [], False
    for line in book.read_text().splitlines():
        m = _ENTRY.match(line)
        if m and m.group(2) == sid:
            if m.group(1):
                raise ContractError(f"{sid} is deprecated")
            found = True
            h, x = int(m.group(4)) + helpful, int(m.group(5)) + harmful
            text = edit if edit is not None else m.group(7)
            today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
            new = (f"{sid} [evidence: {m.group(3)}] [helpful: {h}, harmful: {x}, "
                   f"last-confirmed: {today}] {text}")
            out.append(f"~~{new}~~ DEPRECATED" if deprecate else new)
        else:
            out.append(line)
    if not found:
        raise ContractError(f"no skillbook entry {sid}")
    _atomic_write(book, "\n".join(out) + "\n")


# A lesson is only as good as its last confirmation. These are the days an
# entry stays trusted before the weekly reflection asks a human to re-confirm
# it, per evidence tier: weak evidence goes stale fast, strong evidence keeps
# for a year. Canonical - plugin/docs/site-repo-contract.md and
# plugin/skills/hoo-reflector quote them (docs/INFORMATION-MAP.md).
STALE_DEFAULTS = {"anecdotal": 90, "moderate": 180, "strong": 365}


def skillbook_stale_days(root) -> dict:
    """Per-tier staleness thresholds for this site: the optional
    `skillbook: {stale_days: {...}}` profile section merged over
    STALE_DEFAULTS, per key. The section is additive (schema_version stays
    1; an absent tier means its default). An invalid value raises
    ContractError naming the key."""
    path = Path(root) / "site-profile.yaml"
    data = yaml.safe_load(path.read_text()) if path.exists() else {}
    section = ((data or {}).get("skillbook") or {})
    if not isinstance(section, dict):
        raise ContractError(
            f"skillbook: must be a mapping holding stale_days, got {section!r}")
    override = section.get("stale_days")
    if override is None:
        override = {}
    if not isinstance(override, dict):
        raise ContractError(
            "skillbook.stale_days must be a mapping of evidence tier -> days, "
            f"got {override!r}")
    days = dict(STALE_DEFAULTS)
    for tier in STALE_DEFAULTS:
        if tier not in override:
            continue
        v = override[tier]
        if not isinstance(v, int) or isinstance(v, bool) or v < 1:
            raise ContractError(
                f"skillbook.stale_days.{tier} must be a positive integer "
                f"number of days, got {v!r}")
        days[tier] = v
    return days


def skillbook_stale(root, today=None) -> list:
    """Active skillbook entries past their tier's staleness threshold,
    most stale first: [{id, evidence, last_confirmed, days_stale,
    threshold, text}].

    An entry exactly at its threshold is still fresh; one day past is
    stale. Deprecated entries are skipped - they are already retired, and
    re-validating them is the one thing `skillbook_update` refuses.
    Nothing here mutates the book: the reflector presents the list, a
    human re-confirms (which `skillbook_update` stamps) or proposes a
    deprecation. `today` is injectable so the boundary is testable.
    """
    thresholds = skillbook_stale_days(root)
    if today is None:
        today = _dt.datetime.now(_dt.timezone.utc).date()
    elif isinstance(today, str):
        today = _dt.date.fromisoformat(today)
    book = Path(root) / "skillbook.md"
    if not book.exists():
        return []
    stale = []
    for line in book.read_text().splitlines():
        m = _ENTRY.match(line)
        if not m or m.group(1):          # not an entry, or deprecated
            continue
        threshold = thresholds.get(m.group(3))
        if threshold is None:
            continue                      # hand-edited tier: no threshold to judge by
        try:
            confirmed = _dt.date.fromisoformat(m.group(6))
        except ValueError:
            continue                      # unparseable date: leave it to the curator
        days = (today - confirmed).days
        if days > threshold:
            stale.append({"id": m.group(2), "evidence": m.group(3),
                          "last_confirmed": m.group(6), "days_stale": days,
                          "threshold": threshold, "text": m.group(7)})
    stale.sort(key=lambda e: (-e["days_stale"], e["id"]))
    return stale


# -- approvals queue ----------------------------------------------------------

def rebuild_queue(root) -> Path:
    root = Path(root)
    rows = []
    for folder in ("briefs", "proposals"):
        for f in sorted((root / folder).glob("*.md")):
            try:
                meta = load_item(f)["meta"]
            except ContractError:
                rows.append(f"- MALFORMED: {folder}/{f.name}")
                continue
            # Lint: every approvals entry must carry a decision field. An
            # entry without one is the fingerprint of a hand-edit that
            # bypassed set_status - surface it, never silently accept it.
            for entry in meta.get("approvals") or []:
                if not isinstance(entry, dict) or "decision" not in entry:
                    rows.append(f"- MALFORMED-APPROVAL: {folder}/{f.name} "
                                "(entry missing decision field)")
                    break
            # Lint: items are born proposed. A non-proposed status with an
            # empty approvals list is an illegal birth state (the file was
            # written outside create_item) - it can neither be approved nor
            # pass a lineage gate, so surface it with the repair command
            # instead of letting it jam the pipeline invisibly.
            if meta["status"] != "proposed" and not (meta.get("approvals") or []):
                rows.append(f"- ILLEGAL-STATE: {folder}/{f.name} "
                            f"(born {meta['status']} with no approvals - repair: "
                            f"python3 -m core reset-to-proposed {folder}/{f.name})")
                continue
            if meta["status"] == "proposed":
                rows.append(f"- `{meta['id']}` [{meta['kind']}] {meta['title']} "
                            f"(created {meta['created']}) -> {folder}/{f.name}")
            elif meta["status"] == "partially-applied":
                # Partial work is never invisible: show what a human must
                # finish right next to the pending approvals.
                note = meta.get("status_note") or "human follow-up needed"
                rows.append(f"- PARTIAL: `{meta['id']}` [{meta['kind']}] "
                            f"{meta['title']} -> {folder}/{f.name} ({note})")
    q = root / "approvals" / "queue.md"
    q.write_text("# Pending approvals\n\n" + ("\n".join(rows) + "\n" if rows else "(none)\n"))
    return q
