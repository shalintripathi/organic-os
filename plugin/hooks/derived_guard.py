"""PreToolUse guard for one-writer brain files (ADR-0014). Stdlib only.

Two files inside a brain repo have exactly one writer, and hand edits to
them are how the reference deployment got six weeks of unnoticed malformed
approvals:

- ``approvals/queue.md`` - derived, rebuilt from item frontmatter by
  ``core.contracts.rebuild_queue``. An edit is overwritten on the next
  rebuild at best, and corrupts the operator's view of state at worst.
- ``approvals/*.md`` decision records - written by
  ``core.approval.record_decision`` after a gate.

The guarded-file list above is canonical here (docs/INFORMATION-MAP.md).
A path is only guarded when it sits inside a brain repo: its ``approvals``
directory must have a ``site-profile.yaml`` sibling. A file that merely
shares the name, in any other project, is never touched.

Fail-open is the contract: on any doubt, parse failure, or internal error,
the hook allows the edit and says nothing. Guarding is a courtesy layer -
contracts and CI still enforce correctness where hooks never ran.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

QUEUE_REASON = (
    "approvals/queue.md is derived - it is rebuilt from item frontmatter "
    "and hand edits are overwritten and can corrupt state. Use the "
    "contract layer (core.contracts / the organic-os skills), or run "
    "/organic-os:status to rebuild. (Guard: organic-os plugin; disable by "
    "removing the hook from plugin hooks.json.)")

RECORD_REASON = (
    "approvals/*.md decision records are written by "
    "core.approval.record_decision after a gate - hand edits are how "
    "malformed approval records happen. Use the contract layer "
    "(core.approval / the organic-os skills) to record a decision. "
    "(Guard: organic-os plugin; disable by removing the hook from plugin "
    "hooks.json.)")

GUARDED_TOOLS = {"Edit", "Write", "MultiEdit"}


def _deny(reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "deny",
                                   "permissionDecisionReason": reason}}


def decide(payload: dict) -> dict | None:
    """Deny output for a guarded write, else None (allow)."""
    if not isinstance(payload, dict):
        return None
    if payload.get("tool_name") not in GUARDED_TOOLS:
        return None
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return None
    path = Path(file_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if path.suffix != ".md" or path.parent.name != "approvals":
        return None
    # Brain evidence: the approvals directory's parent holds the site
    # profile. Without it, this is some other project's file - allow.
    if not (path.parent.parent / "site-profile.yaml").is_file():
        return None
    if path.name == "queue.md":
        return _deny(QUEUE_REASON)
    return _deny(RECORD_REASON)


def main(stdin=None, stdout=None) -> int:
    """Reads one PreToolUse JSON payload from stdin. Prints a deny JSON for
    a guarded write, nothing otherwise. Never raises, always returns 0."""
    try:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        payload = json.loads(stdin.read())
        decision = decide(payload)
        if decision is not None:
            stdout.write(json.dumps(decision))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
