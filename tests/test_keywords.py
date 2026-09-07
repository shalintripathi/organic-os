import sys
from pathlib import Path
LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

import pytest  # noqa: E402
from core import keywords as K  # noqa: E402


def _tracking(root: Path) -> Path:
    return root / "keywords" / "tracking.yaml"


def test_load_missing_file_returns_empty_list(tmp_path):
    assert K.load_tracked(tmp_path) == []


def test_load_scaffold_empty_file_returns_empty_list(tmp_path):
    # init_site_repo scaffolds exactly this content.
    _tracking(tmp_path).parent.mkdir(parents=True)
    _tracking(tmp_path).write_text("keywords: []\n")
    assert K.load_tracked(tmp_path) == []


def test_save_then_load_round_trips_normalized_entries(tmp_path):
    entries = [
        {"term": "generic seo term", "added": "2026-09-01", "source": "hoo-keyword-intel"},
        {"term": "another topic", "added": "2026-09-08", "source": "setup"},
    ]
    K.save_tracked(tmp_path, entries)
    assert K.load_tracked(tmp_path) == entries


def test_load_normalizes_hand_written_plain_strings(tmp_path):
    _tracking(tmp_path).parent.mkdir(parents=True)
    _tracking(tmp_path).write_text("keywords:\n  - generic seo term\n  - another topic\n")
    assert K.load_tracked(tmp_path) == [
        {"term": "generic seo term", "added": None, "source": "hand-edited"},
        {"term": "another topic", "added": None, "source": "hand-edited"},
    ]


def test_load_junk_yaml_raises_value_error_naming_the_file(tmp_path):
    _tracking(tmp_path).parent.mkdir(parents=True)
    _tracking(tmp_path).write_text("keywords: [unclosed\n  - :::\n")
    with pytest.raises(ValueError, match="tracking.yaml"):
        K.load_tracked(tmp_path)


def test_load_wrong_shape_raises_value_error_naming_the_file(tmp_path):
    _tracking(tmp_path).parent.mkdir(parents=True)
    _tracking(tmp_path).write_text("just a scalar\n")
    with pytest.raises(ValueError, match="tracking.yaml"):
        K.load_tracked(tmp_path)


def test_save_dedupes_case_insensitively_keeping_the_earliest_entry(tmp_path):
    K.save_tracked(tmp_path, [
        {"term": "Generic SEO Term", "added": "2026-01-01", "source": "setup"},
        {"term": "another topic", "added": "2026-02-01", "source": "setup"},
        {"term": "generic seo term", "added": "2026-03-01", "source": "hand-edited"},
    ])
    loaded = K.load_tracked(tmp_path)
    assert len(loaded) == 2
    assert loaded[0] == {"term": "Generic SEO Term", "added": "2026-01-01",
                         "source": "setup"}
    assert loaded[1]["term"] == "another topic"


def test_add_tracked_reports_added_and_skipped(tmp_path):
    K.save_tracked(tmp_path, [
        {"term": "already tracked", "added": "2026-08-01", "source": "setup"},
    ])
    result = K.add_tracked(tmp_path, ["Already Tracked", "brand new term"],
                           source="hoo-keyword-intel", today="2026-09-08")
    assert result == {"added": ["brand new term"], "skipped": ["Already Tracked"]}
    loaded = K.load_tracked(tmp_path)
    assert loaded[0]["added"] == "2026-08-01"  # untouched
    assert loaded[1] == {"term": "brand new term", "added": "2026-09-08",
                         "source": "hoo-keyword-intel"}


def test_add_tracked_is_idempotent(tmp_path):
    first = K.add_tracked(tmp_path, ["one term", "two term"],
                          source="setup", today="2026-09-08")
    second = K.add_tracked(tmp_path, ["one term", "two term"],
                           source="setup", today="2026-09-09")
    assert first["added"] == ["one term", "two term"]
    assert second == {"added": [], "skipped": ["one term", "two term"]}
    loaded = K.load_tracked(tmp_path)
    assert len(loaded) == 2
    assert all(e["added"] == "2026-09-08" for e in loaded)


def test_add_tracked_dedupes_within_one_call(tmp_path):
    result = K.add_tracked(tmp_path, ["Same Term", "same term"],
                           source="setup", today="2026-09-08")
    assert result == {"added": ["Same Term"], "skipped": ["same term"]}
    assert len(K.load_tracked(tmp_path)) == 1


def test_add_tracked_creates_file_and_parent_dir_on_first_use(tmp_path):
    K.add_tracked(tmp_path, ["first ever term"], source="setup",
                  today="2026-09-08")
    assert _tracking(tmp_path).exists()
    assert K.load_tracked(tmp_path) == [
        {"term": "first ever term", "added": "2026-09-08", "source": "setup"},
    ]
