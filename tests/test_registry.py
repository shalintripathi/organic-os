import sys
from pathlib import Path
LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

import pytest  # noqa: E402
from core import registry as R  # noqa: E402


def test_load_missing_file_returns_empty_structure(tmp_path):
    assert R.load(tmp_path / "sites.yaml") == {"active": None, "sites": {}}


def test_register_two_sites_switches_active_to_latest(tmp_path):
    path = tmp_path / "sites.yaml"
    slug1 = R.register("https://one.com", "One", "/brains/one", path=path)
    slug2 = R.register("https://two.com", "Two", "/brains/two", path=path)
    data = R.load(path)
    assert data["active"] == slug2
    assert set(data["sites"]) == {slug1, slug2}
    assert data["sites"][slug1]["brain"] == "/brains/one"
    assert data["sites"][slug1]["url"] == "https://one.com"
    assert data["sites"][slug1]["name"] == "One"


def test_set_active_switches_back(tmp_path):
    path = tmp_path / "sites.yaml"
    slug1 = R.register("https://one.com", "One", "/brains/one", path=path)
    R.register("https://two.com", "Two", "/brains/two", path=path)
    R.set_active(slug1, path=path)
    assert R.load(path)["active"] == slug1
    assert R.get_active(path=path)["slug"] == slug1
    assert R.get_active(path=path)["brain"] == "/brains/one"


def test_set_active_unknown_slug_raises_with_known_slugs_listed(tmp_path):
    path = tmp_path / "sites.yaml"
    R.register("https://one.com", "One", "/brains/one", path=path)
    with pytest.raises(ValueError, match="one-com"):
        R.set_active("ghost-site", path=path)


def test_slug_derivation_strips_www_and_hyphenates_dots(tmp_path):
    path = tmp_path / "sites.yaml"
    slug = R.register("https://www.my-site.co.uk/x", "My Site", "/brains/x", path=path)
    assert slug == "my-site-co-uk"


def test_register_upserts_existing_slug_instead_of_duplicating(tmp_path):
    path = tmp_path / "sites.yaml"
    slug1 = R.register("https://one.com", "One", "/brains/one", path=path)
    slug2 = R.register("https://one.com", "One Renamed", "/brains/one", path=path)
    assert slug1 == slug2
    data = R.load(path)
    assert len(data["sites"]) == 1
    assert data["sites"][slug1]["name"] == "One Renamed"


def test_register_locks_down_file_permissions(tmp_path):
    path = tmp_path / "sites.yaml"
    R.register("https://one.com", "One", "/brains/one", path=path)
    mode = path.stat().st_mode & 0o777
    assert mode == 0o600


def test_get_active_none_when_no_registry(tmp_path):
    assert R.get_active(tmp_path / "sites.yaml") is None


def test_register_empty_url_raises_and_does_not_write(tmp_path):
    path = tmp_path / "sites.yaml"
    with pytest.raises(ValueError, match="empty site id"):
        R.register("", "No URL", "/tmp/brain", path=path)
    assert not path.exists()


def test_register_whitespace_url_raises_and_does_not_write(tmp_path):
    path = tmp_path / "sites.yaml"
    with pytest.raises(ValueError, match="empty site id"):
        R.register("   ", "No URL", "/tmp/brain", path=path)
    assert not path.exists()


def test_register_empty_url_leaves_existing_registry_unchanged(tmp_path):
    path = tmp_path / "sites.yaml"
    slug = R.register("https://example.com", "Example", "/brains/ex", path=path)
    before = path.read_text()
    with pytest.raises(ValueError, match="empty site id"):
        R.register("", "Bad", "/tmp/brain", path=path)
    assert path.read_text() == before
    assert R.load(path)["active"] == slug
    assert set(R.load(path)["sites"]) == {slug}


def test_register_normal_url_still_returns_slug(tmp_path):
    path = tmp_path / "sites.yaml"
    slug = R.register("https://example.com", "Example", "/brains/ex", path=path)
    assert slug == "example-com"
    assert R.get_active(path)["slug"] == "example-com"


# -- path_warnings -----------------------------------------------------
# Field report: a brain scaffolded under ~/Documents (or Desktop/Downloads)
# breaks launchd/cron runs silently on macOS - TCC blocks the non-interactive
# process from writing .git/index.lock there, and the only symptom is
# "Operation not permitted" in the routine log. path_warnings() is an
# advisory pre-check the setup skill runs before scaffolding a brain.

def test_path_warnings_local_runtime_under_documents_warns_about_launchd():
    warnings = R.path_warnings("~/Documents/my-site", "local")
    assert len(warnings) == 1
    assert "launchd" in warnings[0]


def test_path_warnings_local_runtime_under_desktop_warns():
    warnings = R.path_warnings("~/Desktop/my-site", "local")
    assert len(warnings) == 1
    assert "launchd" in warnings[0]


def test_path_warnings_local_runtime_under_downloads_warns():
    warnings = R.path_warnings("~/Downloads/my-site", "local")
    assert len(warnings) == 1
    assert "launchd" in warnings[0]


def test_path_warnings_local_runtime_default_organic_hq_is_safe():
    assert R.path_warnings("~/organic-hq/my-site", "local") == []


def test_path_warnings_claude_scheduled_runtime_under_documents_is_safe():
    # Documented call: claude-scheduled runs in the cloud, not against the
    # local filesystem, so the macOS TCC failure mode this warning exists
    # for cannot happen under this runtime - Documents/Desktop/Downloads
    # are only a problem for the local runtime.
    assert R.path_warnings("~/Documents/my-site", "claude-scheduled") == []


def test_path_warnings_manual_runtime_under_documents_is_safe():
    # Manual runs happen in an interactive Terminal session, which TCC does
    # not restrict (only non-interactive launchd/cron processes are
    # blocked), so there is nothing to warn about here either.
    assert R.path_warnings("~/Documents/my-site", "manual") == []


def test_path_warnings_ci_runtime_under_documents_is_safe():
    # CI runs on a GitHub Actions runner, not the user's Mac at all.
    assert R.path_warnings("~/Documents/my-site", "ci") == []


def test_path_warnings_path_containing_plugins_segment_warns_any_runtime():
    for runtime in ("local", "claude-scheduled", "ci", "manual"):
        warnings = R.path_warnings(
            "~/.claude/plugins/organic-os/brain", runtime
        )
        assert len(warnings) == 1
        assert "plugin" in warnings[0].lower()


def test_path_warnings_safe_path_returns_empty_list_for_every_runtime():
    for runtime in ("local", "claude-scheduled", "ci", "manual"):
        assert R.path_warnings("~/organic-hq/my-site", runtime) == []


def test_path_warnings_inside_claude_plugin_root_env_warns(monkeypatch, tmp_path):
    plugin_root = tmp_path / "organic-os-plugin"
    plugin_root.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))
    warnings = R.path_warnings(str(plugin_root / "brain"), "local")
    assert len(warnings) == 1
    assert "plugin" in warnings[0].lower()


def test_path_warnings_both_conditions_returns_two_warnings():
    warnings = R.path_warnings(
        "~/Documents/.claude/plugins/organic-os/brain", "local"
    )
    assert len(warnings) == 2
