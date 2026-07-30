"""Stage classification: which stage a site is in, judged from its own data.

Every fixture here is invented. The site is example.com and the queries are
generic. Nothing in this file is a real property, a real query set, or a
real number pulled from anyone's Search Console.
"""
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

from core import stage  # noqa: E402


def _row(clicks=0, impressions=0, position=50.0, query="q", page=None):
    return {"clicks": clicks, "impressions": impressions,
            "position": position, "query": query,
            "page": page or "https://example.com/a"}


def _sentence(text):
    """A human sentence: non-empty, ends in a full stop, has real words."""
    return (isinstance(text, str) and text.strip() != ""
            and text.strip().endswith(".") and len(text.split()) >= 4)


# -- classify ------------------------------------------------------------------

def test_established_at_100_clicks():
    rows = [_row(clicks=100, impressions=4000)]
    out = stage.classify(rows)
    assert out["stage"] == stage.ESTABLISHED
    assert out["clicks"] == 100


def test_growing_at_99_clicks():
    rows = [_row(clicks=99, impressions=4000)]
    assert stage.classify(rows)["stage"] == stage.GROWING


def test_growing_at_10_clicks():
    rows = [_row(clicks=10, impressions=400)]
    assert stage.classify(rows)["stage"] == stage.GROWING


def test_early_at_9_clicks():
    rows = [_row(clicks=9, impressions=400)]
    assert stage.classify(rows)["stage"] == stage.EARLY


def test_clicks_sum_across_rows():
    rows = [_row(clicks=60, impressions=900), _row(clicks=41, impressions=800)]
    out = stage.classify(rows)
    assert out["stage"] == stage.ESTABLISHED
    assert out["clicks"] == 101
    assert out["impressions"] == 1700


def test_impressions_but_no_clicks_is_early_and_says_so():
    rows = [_row(clicks=0, impressions=12, position=90.0, query="a"),
            _row(clicks=0, impressions=4, position=93.0, query="b")]
    out = stage.classify(rows)
    assert out["stage"] == stage.EARLY
    assert out["clicks"] == 0
    assert out["impressions"] == 16
    # The message must distinguish "seen but not clicked" from "no data".
    assert "16" in out["reason"]
    assert "no search data yet" not in out["reason"]


def test_zero_everything_reads_as_no_search_data_yet():
    rows = [_row(clicks=0, impressions=0, position=0.0)]
    out = stage.classify(rows)
    assert out["stage"] == stage.EARLY
    assert "no search data yet" in out["reason"]


def test_empty_list_is_early_with_no_search_data_yet():
    out = stage.classify([])
    assert out["stage"] == stage.EARLY
    assert out["clicks"] == 0
    assert out["impressions"] == 0
    assert out["pages"] == 0
    assert "no search data yet" in out["reason"]


def test_pages_counts_distinct_pages():
    rows = [_row(page="https://example.com/a"),
            _row(page="https://example.com/a"),
            _row(page="https://example.com/b")]
    assert stage.classify(rows)["pages"] == 2


def test_rows_without_a_page_key_do_not_invent_a_page():
    rows = [{"clicks": 0, "impressions": 5, "position": 44.0, "query": "q"}]
    assert stage.classify(rows)["pages"] == 0


def test_reason_is_a_human_sentence_in_every_case():
    cases = [[], [_row(clicks=0, impressions=0)],
             [_row(clicks=0, impressions=61)], [_row(clicks=10)],
             [_row(clicks=100, impressions=9000)]]
    for rows in cases:
        assert _sentence(stage.classify(rows)["reason"]), rows


def test_missing_and_unparseable_values_count_as_zero_not_a_crash():
    rows = [{"clicks": None, "impressions": "nope", "position": None},
            {"impressions": 7}]
    out = stage.classify(rows)
    assert out["stage"] == stage.EARLY
    assert out["clicks"] == 0
    assert out["impressions"] == 7
