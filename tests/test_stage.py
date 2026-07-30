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


# -- early_opportunities -------------------------------------------------------

def _bands(out):
    return [o["band"] for o in out]


def test_empty_input_returns_empty_list():
    assert stage.early_opportunities([]) == []
    assert stage.early_opportunities(None) == []


def test_top_band_is_page_one_with_zero_clicks():
    out = stage.early_opportunities([_row(clicks=0, impressions=30,
                                          position=4.0)])
    assert _bands(out) == ["top"]


def test_band_boundaries():
    cases = [(1.0, "top"), (10.0, "top"), (10.1, "page-two"),
             (11.0, "page-two"), (30.0, "page-two"), (30.1, "visible"),
             (31.0, "visible"), (70.0, "visible"), (70.1, "distant"),
             (71.0, "distant"), (98.0, "distant")]
    for position, band in cases:
        out = stage.early_opportunities([_row(impressions=1,
                                              position=position)])
        assert _bands(out) == [band], (position, band)


def test_a_page_one_query_that_already_earns_clicks_is_not_an_opportunity():
    rows = [_row(clicks=3, impressions=40, position=5.0, query="earning"),
            _row(clicks=0, impressions=12, position=20.0, query="stuck")]
    out = stage.early_opportunities(rows)
    assert [o["query"] for o in out] == ["stuck"]


def test_rows_without_a_position_are_skipped_not_guessed():
    rows = [{"clicks": 0, "impressions": 9, "query": "no-position"},
            _row(impressions=2, position=25.0, query="banded")]
    out = stage.early_opportunities(rows)
    assert [o["query"] for o in out] == ["banded"]


def test_ordering_runs_top_then_page_two_then_visible_then_distant():
    rows = [_row(impressions=1, position=80.0, query="d"),
            _row(impressions=1, position=50.0, query="v"),
            _row(impressions=1, position=20.0, query="p"),
            _row(impressions=1, position=3.0, query="t")]
    out = stage.early_opportunities(rows)
    assert _bands(out) == ["top", "page-two", "visible", "distant"]
    assert [o["query"] for o in out] == ["t", "p", "v", "d"]


def test_within_a_band_ties_break_on_impressions_descending():
    rows = [_row(impressions=4, position=20.0, query="small"),
            _row(impressions=12, position=25.0, query="big"),
            _row(impressions=9, position=13.0, query="middle")]
    out = stage.early_opportunities(rows)
    assert [o["query"] for o in out] == ["big", "middle", "small"]


def test_limit_is_respected_and_defaults_to_five():
    rows = [_row(impressions=i, position=20.0, query=f"q{i}")
            for i in range(1, 9)]
    assert len(stage.early_opportunities(rows)) == 5
    assert len(stage.early_opportunities(rows, limit=2)) == 2
    assert len(stage.early_opportunities(rows, limit=None)) == 8


def test_each_opportunity_carries_the_fields_a_report_needs():
    rows = [_row(clicks=0, impressions=12, position=90.0, query="seo agent",
                 page="https://example.com/agents")]
    out = stage.early_opportunities(rows)
    assert out[0]["query"] == "seo agent"
    assert out[0]["page"] == "https://example.com/agents"
    assert out[0]["position"] == 90.0
    assert out[0]["impressions"] == 12
    assert out[0]["band"] == "distant"
    assert _sentence(out[0]["note"] + ".") or _sentence(out[0]["note"])


def test_the_note_describes_the_lever_and_promises_no_movement():
    rows = [_row(impressions=1, position=p, query=f"q{p}")
            for p in (5.0, 20.0, 50.0, 90.0)]
    for opportunity in stage.early_opportunities(rows):
        note = opportunity["note"].lower()
        assert note.strip() != ""
        for promise in ("will rank", "will move", "guarantee", "will reach",
                        "will improve", "will climb"):
            assert promise not in note, (opportunity["band"], promise)


def test_the_notes_name_the_documented_lever_per_band():
    levers = {"top": "title", "page-two": "on-page", "visible": "depth",
              "distant": "directional"}
    rows = [_row(impressions=1, position=p) for p in (5.0, 20.0, 50.0, 90.0)]
    for opportunity in stage.early_opportunities(rows):
        assert levers[opportunity["band"]] in opportunity["note"]
