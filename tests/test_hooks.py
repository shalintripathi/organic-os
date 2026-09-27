"""Unit tests for the plugin's two runtime hooks (ADR-0014).

Both hook scripts are imported as modules: logic lives in functions, the
__main__ block is a thin wrapper. Subprocess probes at the end prove the
fail-silent guarantee end to end - exit 0, no output, on any garbage.
"""
import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
HOOKS = Path(__file__).resolve().parents[1] / "plugin" / "hooks"
sys.path.insert(0, str(LIB))
sys.path.insert(0, str(HOOKS))

import pytest  # noqa: E402
import yaml  # noqa: E402
from core.init_site_repo import init_site_repo  # noqa: E402

import derived_guard  # noqa: E402
import session_status  # noqa: E402

TODAY = "2026-09-27"


@pytest.fixture
def brain(tmp_path):
    return init_site_repo(tmp_path / "brain", "https://example.com", "Example")


def _item(brain, folder, name, created, status="proposed"):
    meta = {"id": f"p-{name}", "kind": "onpage-fix", "status": status,
            "created": f"{created}T08:00:00Z", "title": name,
            "target": "/", "source": "test", "approvals": []}
    path = brain / folder / f"{name}.md"
    path.write_text("---\n" + yaml.safe_dump(meta, sort_keys=False)
                    + "---\nbody\n")
    return path


# -- session_status: brain resolution -----------------------------------------

def test_no_brain_resolves_none(tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    assert session_status.resolve_brain(
        cwd=cwd, config_path=tmp_path / "missing.yaml") is None


def test_brain_resolved_walking_up_from_subdir(brain, tmp_path):
    got = session_status.resolve_brain(
        cwd=brain / "signals", config_path=tmp_path / "missing.yaml")
    assert got == brain


def test_brain_resolved_from_registry_active_site(brain, tmp_path):
    cfg = tmp_path / "sites.yaml"
    cfg.write_text(yaml.safe_dump({
        "active": "example-com",
        "sites": {"example-com": {"url": "https://example.com",
                                  "name": "Example", "brain": str(brain)}}}))
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    assert session_status.resolve_brain(cwd=cwd, config_path=cfg) == brain


# -- session_status: status lines ----------------------------------------------

def test_pending_and_malformed_render_the_documented_line(brain):
    _item(brain, "proposals", "20260915-old-fix", "2026-09-15")
    _item(brain, "proposals", "20260924-new-fix", "2026-09-24")
    (brain / "approvals" / "queue.md").write_text(
        "# Pending approvals\n\n"
        "- MALFORMED: proposals/junk.md\n"
        "- MALFORMED-APPROVAL: briefs/other.md (entry missing decision field)\n")
    (brain / "signals" / f"{TODAY}.md").write_text("- [t] fine\n")
    status = session_status.collect_status(brain, today=TODAY)
    lines = session_status.render_lines(status)
    assert lines == [
        "[organic-os] example-com: 2 items awaiting approval (oldest 12d); "
        "queue notes 2 MALFORMED. Run /organic-os:status."]


def test_single_pending_uses_singular_and_no_queue_note(brain):
    _item(brain, "briefs", "20260926-brief", "2026-09-26")
    (brain / "signals" / f"{TODAY}.md").write_text("- [t] fine\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert lines == [
        "[organic-os] example-com: 1 item awaiting approval (oldest 1d). "
        "Run /organic-os:status."]


def test_partial_note_surfaces_without_pending(brain):
    (brain / "approvals" / "queue.md").write_text(
        "# Pending approvals\n\n- PARTIAL: `p-x` [onpage-fix] X -> "
        "proposals/x.md (finish the redirect)\n")
    (brain / "signals" / f"{TODAY}.md").write_text("- [t] fine\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert lines == [
        "[organic-os] example-com: queue notes 1 PARTIAL. "
        "Run /organic-os:status."]


def test_fresh_and_clean_brain_is_silent(brain):
    (brain / "signals" / f"{TODAY}.md").write_text("- [t] all quiet\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert lines == []


def test_stale_signal_line_carries_date_age_and_stage(brain):
    (brain / "signals" / "2026-09-25.md").write_text(
        "- [2026-09-25T06:00:00Z] daily ran\n"
        "- [2026-09-25T06:00:01Z] stage: early - 4 clicks in the window\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert lines == [
        "[organic-os] last routine signal 2026-09-25 (2d ago); stage: early."]


def test_stale_signal_without_stage_still_reports(brain):
    (brain / "signals" / "2026-09-20.md").write_text("- [t] daily ran\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert lines == ["[organic-os] last routine signal 2026-09-20 (7d ago)."]


def test_never_more_than_three_lines(brain):
    _item(brain, "proposals", "20260901-a", "2026-09-01")
    (brain / "approvals" / "queue.md").write_text(
        "# Pending approvals\n\n- MALFORMED: proposals/j.md\n")
    (brain / "signals" / "2026-09-01.md").write_text("- [t] stage: early\n")
    lines = session_status.render_lines(
        session_status.collect_status(brain, today=TODAY))
    assert 1 <= len(lines) <= 3


# -- session_status: fail-silent -----------------------------------------------

def test_main_with_no_brain_prints_nothing_and_exits_zero(tmp_path):
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    out = io.StringIO()
    rc = session_status.main(cwd=cwd, config_path=tmp_path / "missing.yaml",
                             stdout=out)
    assert rc == 0
    assert out.getvalue() == ""


def test_main_survives_malformed_brain_yaml(tmp_path):
    root = tmp_path / "brain"
    (root / "approvals").mkdir(parents=True)
    (root / "briefs").mkdir()
    (root / "site-profile.yaml").write_text("{{{ not yaml [")
    (root / "briefs" / "junk.md").write_text("---\n:{bad\n---\n")
    out = io.StringIO()
    rc = session_status.main(cwd=root, config_path=tmp_path / "missing.yaml",
                             stdout=out)
    assert rc == 0


def test_main_survives_unreadable_dirs(brain, tmp_path):
    _item(brain, "proposals", "20260920-a", "2026-09-20")
    locked = brain / "approvals"
    locked.chmod(0)
    try:
        out = io.StringIO()
        rc = session_status.main(cwd=brain,
                                 config_path=tmp_path / "missing.yaml",
                                 stdout=out)
        assert rc == 0
    finally:
        locked.chmod(stat.S_IRWXU)


def test_main_survives_garbage_registry(tmp_path):
    cfg = tmp_path / "sites.yaml"
    cfg.write_text("\t{{{ not yaml")
    cwd = tmp_path / "elsewhere"
    cwd.mkdir()
    out = io.StringIO()
    assert session_status.main(cwd=cwd, config_path=cfg, stdout=out) == 0
    assert out.getvalue() == ""


def test_session_status_script_exit_zero_outside_any_brain(tmp_path):
    env = {**os.environ, "HOME": str(tmp_path)}
    r = subprocess.run([sys.executable, str(HOOKS / "session_status.py")],
                       cwd=tmp_path, env=env, capture_output=True, text=True,
                       timeout=10)
    assert r.returncode == 0
    assert r.stdout == ""


# -- derived_guard: deny shape ---------------------------------------------------

def _payload(path, tool="Edit"):
    return {"tool_name": tool, "tool_input": {"file_path": str(path)}}


def test_guard_denies_queue_inside_brain_with_exact_shape(brain):
    got = derived_guard.decide(_payload(brain / "approvals" / "queue.md"))
    assert got == {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": derived_guard.QUEUE_REASON}}


def test_guard_denies_decision_record_inside_brain(brain):
    rec = brain / "approvals" / "2026-09-01-approve-fix.md"
    got = derived_guard.decide(_payload(rec, tool="Write"))
    reason = got["hookSpecificOutput"]["permissionDecisionReason"]
    assert got["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "core.approval.record_decision" in reason


def test_guard_covers_multiedit(brain):
    got = derived_guard.decide(
        _payload(brain / "approvals" / "queue.md", tool="MultiEdit"))
    assert got is not None


def test_guard_allows_queue_outside_a_brain(tmp_path):
    q = tmp_path / "some-project" / "approvals" / "queue.md"
    q.parent.mkdir(parents=True)
    q.write_text("# not a brain\n")
    assert derived_guard.decide(_payload(q)) is None


def test_guard_allows_normal_brain_files(brain):
    for p in (brain / "briefs" / "20260927-b.md",
              brain / "signals" / "2026-09-27.md",
              brain / "site-profile.yaml",
              brain / "skillbook.md"):
        assert derived_guard.decide(_payload(p)) is None


def test_guard_allows_non_edit_tools_and_missing_fields(brain):
    q = brain / "approvals" / "queue.md"
    assert derived_guard.decide(_payload(q, tool="Read")) is None
    assert derived_guard.decide({"tool_name": "Edit"}) is None
    assert derived_guard.decide({}) is None


def test_guard_allows_non_markdown_in_approvals(brain):
    assert derived_guard.decide(
        _payload(brain / "approvals" / ".gitkeep")) is None


# -- derived_guard: fail-open ------------------------------------------------------

def test_guard_main_prints_deny_json(brain):
    out = io.StringIO()
    rc = derived_guard.main(
        stdin=io.StringIO(json.dumps(_payload(brain / "approvals" / "queue.md"))),
        stdout=out)
    assert rc == 0
    assert json.loads(out.getvalue()) == derived_guard.decide(
        _payload(brain / "approvals" / "queue.md"))


def test_guard_main_allows_silently_on_junk_stdin():
    out = io.StringIO()
    assert derived_guard.main(stdin=io.StringIO("not json {"), stdout=out) == 0
    assert out.getvalue() == ""


def test_guard_main_allows_silently_on_empty_stdin():
    out = io.StringIO()
    assert derived_guard.main(stdin=io.StringIO(""), stdout=out) == 0
    assert out.getvalue() == ""


def test_derived_guard_script_exit_zero_on_garbage(tmp_path):
    r = subprocess.run([sys.executable, str(HOOKS / "derived_guard.py")],
                       input="\x00\x01 garbage", cwd=tmp_path,
                       capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    assert r.stdout == ""


# -- hooks.json wiring ---------------------------------------------------------

def test_hooks_json_wires_both_scripts_with_timeouts():
    data = json.loads((HOOKS / "hooks.json").read_text())
    hooks = data["hooks"]
    session = hooks["SessionStart"][0]["hooks"][0]
    assert "session_status.py" in session["command"]
    assert session["command"].startswith("python3 ")
    assert "${CLAUDE_PLUGIN_ROOT}" in session["command"]
    assert session["timeout"] == 10
    pre = hooks["PreToolUse"][0]
    assert pre["matcher"] == "Edit|Write|MultiEdit"
    guard = pre["hooks"][0]
    assert "derived_guard.py" in guard["command"]
    assert guard["command"].startswith("python3 ")
    assert "${CLAUDE_PLUGIN_ROOT}" in guard["command"]
    assert guard["timeout"] == 10
