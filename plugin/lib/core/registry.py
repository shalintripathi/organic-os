"""Cross-site registry: which sites has this operator onboarded, which is active.

Lives outside any brain repo at ~/.config/organic-os/sites.yaml (never committed,
never part of a site's git history). Config is editable here; a site's memory
(signals/decisions/reflections/skillbook inside its brain repo) is not touched
by this module.
"""
from __future__ import annotations
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import yaml

DEFAULT = Path.home() / ".config" / "organic-os" / "sites.yaml"

# macOS TCC (Transparency, Consent, and Control) silently blocks
# non-interactive processes - launchd and cron specifically - from writing
# inside these folders, even though an interactive Terminal has full access
# to them. A brain repo scaffolded here breaks local-runtime routines with
# no warning ahead of time; see plugin/docs/routines.md.
TCC_PROTECTED = ("Documents", "Desktop", "Downloads")


def _slugify(url: str) -> str:
    host = urlparse(url if "://" in url else f"//{url}").hostname or url
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
    return slug


def load(path=DEFAULT) -> dict:
    path = Path(path)
    if not path.exists():
        return {"active": None, "sites": {}}
    data = yaml.safe_load(path.read_text()) or {}
    return {"active": data.get("active"), "sites": data.get("sites") or {}}


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, sort_keys=False))
    os.replace(tmp, path)
    os.chmod(path, 0o600)


def register(url: str, name: str, brain, path=DEFAULT) -> str:
    path = Path(path)
    data = load(path)
    slug = _slugify(url)
    if not slug:
        raise ValueError(
            f"cannot register {url!r}: it produces an empty site id. "
            "Pass a URL with a hostname, such as https://example.com"
        )
    data["sites"][slug] = {"url": url, "name": name, "brain": str(brain)}
    data["active"] = slug
    _atomic_write(path, data)
    return slug


def set_active(slug: str, path=DEFAULT) -> None:
    path = Path(path)
    data = load(path)
    if slug not in data["sites"]:
        known = sorted(data["sites"]) or ["(none registered)"]
        raise ValueError(f"unknown site {slug!r}; known sites: {', '.join(known)}")
    data["active"] = slug
    _atomic_write(path, data)


def get_active(path=DEFAULT) -> dict | None:
    data = load(path)
    slug = data.get("active")
    if not slug or slug not in data["sites"]:
        return None
    return {"slug": slug, **data["sites"][slug]}


def path_warnings(brain_path, runtime: str) -> list[str]:
    """Human-readable warnings about a chosen brain path, given the runtime
    that will run its routines. Advisory only - an empty list means no
    concerns found; the caller (setup skill) decides whether to re-ask.

    - ``runtime == "local"`` and the path passes through a macOS
      TCC-protected folder (Documents, Desktop, Downloads) anywhere in
      it -> a strong warning naming the failure mode (launchd/cron silently
      denied when writing ``.git/index.lock``, surfacing only as
      "Operation not permitted" in the routine log) and the safe default.
      This check is scoped to ``local`` on purpose: ``claude-scheduled``
      runs in the cloud, never touching the local filesystem's TCC rules,
      and ``manual``/``ci`` runs either happen in an interactive Terminal
      (which TCC does not restrict) or on a CI runner (not the user's Mac
      at all) - so the same path is not a problem under those runtimes.
    - Any runtime: warns if the path sits inside this plugin's own
      installed directory (``$CLAUDE_PLUGIN_ROOT``, when set) or contains
      a ``/plugins/`` path segment - plugin install, update, or
      marketplace sync can overwrite or delete files living there.
    """
    warnings: list[str] = []
    p = Path(brain_path).expanduser()

    if runtime == "local":
        hit = [part for part in p.parts if part in TCC_PROTECTED]
        if hit:
            warnings.append(
                f"Brain path is under {hit[0]!r}, a macOS-protected folder. "
                "launchd (and cron) jobs are silently blocked by TCC from "
                "writing there - git fails with \"error: unable to create "
                "'.git/index.lock': Operation not permitted\" with no warning "
                "ahead of time. Use the default ~/organic-hq/<slug> instead."
            )

    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    inside_plugin_root = False
    if plugin_root:
        try:
            p.relative_to(Path(plugin_root).expanduser())
            inside_plugin_root = True
        except ValueError:
            inside_plugin_root = False

    if inside_plugin_root or "/plugins/" in p.as_posix():
        warnings.append(
            "Brain path is inside a plugin directory. Plugin install, "
            "update, or marketplace sync can overwrite or delete files "
            "there - keep the brain repo outside any plugin directory, "
            "e.g. ~/organic-hq/<slug>."
        )

    return warnings
