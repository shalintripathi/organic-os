"""SessionStart status line for a resolvable brain (ADR-0014).

One job: when a session starts where a registered brain can be found,
say what is waiting - pending approvals and their age, queue notes
(MALFORMED / PARTIAL), the last routine signal date, and the site stage.
The operator hears about waiting work by opening a session, not by
remembering to ask.

Silence is the default: nothing pending, no queue notes, and a fresh
signal (under 2 days old) prints nothing at all. At most 3 short lines,
only lines that carry news. The line formats rendered by
``render_lines`` are canonical here (docs/INFORMATION-MAP.md).

Fail-silent is the contract: no network, no git, no writes, every path
wrapped, and any internal failure means exit 0 with empty stdout.
Directory listings are capped defensively so a huge brain cannot make
session start slow. Dependencies: stdlib plus PyYAML (the plugin's one
existing dependency); if PyYAML is missing the hook stays silent.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

try:
    import yaml
except Exception:  # PyYAML absent: stay silent rather than error.
    yaml = None

FRESH_DAYS = 2      # a signal younger than this is not news
LIST_CAP = 200      # newest N files considered per directory
READ_CAP = 200_000  # max characters read from any one file

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)
_STAGE = re.compile(r"\bstage:\s*([A-Za-z][A-Za-z-]*)")


def _is_brain(d: Path) -> bool:
    return (d / "site-profile.yaml").is_file() and (d / "approvals").is_dir()


def _registry_path() -> Path:
    """The sites-registry path, reusing lib/core/registry's own DEFAULT
    when the lib is importable from this hook's install location."""
    try:
        lib = Path(__file__).resolve().parents[1] / "lib"
        if str(lib) not in sys.path:
            sys.path.insert(0, str(lib))
        from core import registry
        return Path(registry.DEFAULT)
    except Exception:
        return Path.home() / ".config" / "organic-os" / "sites.yaml"


def resolve_brain(cwd=None, config_path=None) -> Path | None:
    """The brain this session is about: the cwd or a parent that looks
    like one (site-profile.yaml + approvals/), else the registry's active
    site. None when nothing resolves - the hook then says nothing."""
    try:
        start = Path(cwd) if cwd is not None else Path.cwd()
        for d in (start, *start.parents):
            if _is_brain(d):
                return d
        if yaml is None:
            return None
        path = Path(config_path) if config_path is not None else _registry_path()
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text()) or {}
        if not isinstance(data, dict):
            return None
        slug = data.get("active")
        site = (data.get("sites") or {}).get(slug) if slug else None
        if isinstance(site, dict) and site.get("brain"):
            brain = Path(str(site["brain"])).expanduser()
            if _is_brain(brain):
                return brain
    except Exception:
        pass
    return None


def _as_date(today) -> _dt.date:
    if today is None:
        return _dt.datetime.now(_dt.timezone.utc).date()
    if isinstance(today, str):
        return _dt.date.fromisoformat(today)
    return today


def _label(brain: Path) -> str:
    try:
        data = yaml.safe_load(
            (brain / "site-profile.yaml").read_text()[:READ_CAP]) or {}
        url = str(((data.get("site") or {}).get("url"))
                  or data.get("url") or "")
        host = urlparse(url if "://" in url else f"//{url}").hostname or ""
        host = host.lower().removeprefix("www.")
        slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
        if slug:
            return slug
    except Exception:
        pass
    return brain.name


def collect_status(brain, today=None) -> dict:
    """Cheap, read-only summary of a brain. Every sub-read is wrapped:
    one unreadable corner never blanks the rest."""
    brain = Path(brain)
    status = {"label": brain.name, "pending": 0, "oldest_days": None,
              "malformed": 0, "partial": 0,
              "last_signal": None, "signal_age_days": None, "stage": None}
    try:
        today = _as_date(today)
    except Exception:
        today = _dt.datetime.now(_dt.timezone.utc).date()
    status["label"] = _label(brain)

    # Pending items: proposed briefs/proposals, same frontmatter shape
    # core.contracts reads (item files carry status: and created:).
    try:
        oldest = None
        for folder in ("briefs", "proposals"):
            for f in sorted((brain / folder).glob("*.md"))[-LIST_CAP:]:
                if f.name.endswith(".draft.md"):
                    continue
                try:
                    m = _FRONTMATTER.match(f.read_text()[:READ_CAP])
                    meta = yaml.safe_load(m.group(1)) if m else None
                    if not isinstance(meta, dict):
                        continue
                    if meta.get("status") != "proposed":
                        continue
                    status["pending"] += 1
                    created = _dt.date.fromisoformat(str(meta["created"])[:10])
                    age = (today - created).days
                    if oldest is None or age > oldest:
                        oldest = age
                except Exception:
                    continue
        status["oldest_days"] = oldest
    except Exception:
        pass

    # Queue notes: MALFORMED / PARTIAL rows the rebuild surfaced.
    try:
        queue = (brain / "approvals" / "queue.md").read_text()[:READ_CAP]
        for line in queue.splitlines():
            row = line.lstrip()
            if row.startswith("- MALFORMED"):
                status["malformed"] += 1
            elif row.startswith("- PARTIAL"):
                status["partial"] += 1
    except Exception:
        pass

    # Newest routine signal, and the stage if that signal states one.
    try:
        for f in sorted((brain / "signals").glob("*.md"))[-LIST_CAP:][::-1]:
            try:
                day = _dt.date.fromisoformat(f.stem)
            except ValueError:
                continue
            status["last_signal"] = day.isoformat()
            status["signal_age_days"] = (today - day).days
            hits = _STAGE.findall(f.read_text()[:READ_CAP])
            if hits:
                status["stage"] = hits[-1]
            break
    except Exception:
        pass
    return status


def render_lines(status: dict) -> list[str]:
    """At most 3 short lines, only lines that carry news; [] is silence."""
    lines: list[str] = []
    label = status.get("label") or "site"
    pending = status.get("pending") or 0
    notes = []
    if status.get("malformed"):
        notes.append(f"{status['malformed']} MALFORMED")
    if status.get("partial"):
        notes.append(f"{status['partial']} PARTIAL")

    if pending:
        line = (f"[organic-os] {label}: {pending} "
                f"item{'s' if pending != 1 else ''} awaiting approval")
        if status.get("oldest_days") is not None:
            line += f" (oldest {status['oldest_days']}d)"
        if notes:
            line += "; queue notes " + ", ".join(notes)
        lines.append(line + ". Run /organic-os:status.")
    elif notes:
        lines.append(f"[organic-os] {label}: queue notes "
                     + ", ".join(notes) + ". Run /organic-os:status.")

    age = status.get("signal_age_days")
    if status.get("last_signal") and age is not None and age >= FRESH_DAYS:
        line = f"[organic-os] last routine signal {status['last_signal']} ({age}d ago)"
        if status.get("stage"):
            line += f"; stage: {status['stage']}"
        lines.append(line + ".")
    return lines[:3]


def main(cwd=None, config_path=None, stdout=None) -> int:
    """Never raises, always returns 0; empty stdout means nothing to say."""
    try:
        stdout = stdout or sys.stdout
        brain = resolve_brain(cwd=cwd, config_path=config_path)
        if brain is None:
            return 0
        lines = render_lines(collect_status(brain))
        if lines:
            stdout.write("\n".join(lines) + "\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
