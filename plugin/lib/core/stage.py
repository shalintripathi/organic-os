"""What stage a site is in, and what is worth acting on there. Stdlib only.

Every detector in the loop was written for a site that already earns clicks.
Striking distance wants positions 4-15 above the site's median impressions;
content decay wants 50+ clicks in the older window; the anomaly check skips
any metric whose trailing median is under 10; cannibalization wants two
pages splitting a query. A two-week-old site meets none of those, so the
routines reported a quiet day every day and the operator reasonably
concluded the loop was broken. Every site starts there, so every operator
would hit it.

This module gives the routines a way to say which stage a site is in, from
that site's own numbers, and to name what is worth doing at the earliest
one. It reads data and returns dicts; it writes nothing and fetches
nothing.

The stage thresholds and the opportunity bands below are canonical here;
`docs/INFORMATION-MAP.md` in the repo tracks who quotes them.
"""
from __future__ import annotations

EARLY, GROWING, ESTABLISHED = "early", "growing", "established"

# Position bands, canonical here. Read as: up to and including the number.
TOP_MAX = 10.0
PAGE_TWO_MAX = 30.0
VISIBLE_MAX = 70.0

# Band order is priority order: what the operator should look at first.
BANDS = ("top", "page-two", "visible", "distant")

_NOTES = {
    "top": ("ranking on the first page but not earning the click; the "
            "title and description are the lever"),
    "page-two": ("the closest thing to a breakthrough; on-page work "
                 "plausibly moves this"),
    "visible": ("the page is being considered but is not competitive; "
                "content depth or authority is the lever, not a title "
                "tweak"),
    "distant": ("appearing at all confirms the topic is targeted "
                "correctly; a directional signal, not a task"),
}


def _num(value):
    """`value` as a float, or None when it is missing or not a number.

    Absent stays absent. A row with no position has an unknown position,
    which is different from a position of zero, and the callers below rely
    on being able to tell the two apart.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    """`value` as a non-negative int; anything unreadable counts as 0."""
    n = _num(value)
    if n is None or n < 0:
        return 0
    return int(n)


def classify(rows) -> dict:
    """Which stage is this site in, judged from a GSC page/query pull.

    `rows`: list of dicts with at least clicks, impressions, position.
    Returns {"stage", "clicks", "impressions", "pages", "reason"} where
    reason is one plain sentence naming the evidence, for a human to read.

    The rules, deliberately simple so an operator can check them by hand
    against their own Search Console:

    - ESTABLISHED when total clicks in the window are 100 or more. At that
      volume the click-gated detectors (decay's 50-click floor, the anomaly
      check's median-of-10 floor) have something to work with.
    - GROWING when total clicks are 10 or more. Clicks exist and trends are
      starting to mean something, but the volume gates still bite.
    - EARLY otherwise, including zero clicks. Position is the only readable
      signal here, which is what `early_opportunities` below works from.

    Zero impressions AND zero clicks is still EARLY, but it is a different
    situation and gets a different sentence: nothing has been seen yet, so
    there is no position data to act on either. A site with impressions and
    no clicks has real signal; saying "no data" about it would be wrong.
    """
    rows = list(rows or [])
    clicks = sum(_int(r.get("clicks")) for r in rows)
    impressions = sum(_int(r.get("impressions")) for r in rows)
    pages = len({r.get("page") for r in rows if r.get("page")})

    if clicks >= 100:
        name = ESTABLISHED
        reason = (f"{clicks} clicks and {impressions} impressions across "
                  f"{pages} pages in this window, at or above the 100-click "
                  f"mark this loop reads as an established site.")
    elif clicks >= 10:
        name = GROWING
        reason = (f"{clicks} clicks and {impressions} impressions across "
                  f"{pages} pages in this window, past the 10-click mark "
                  f"but not yet at 100.")
    elif impressions == 0:
        name = EARLY
        reason = ("no search data yet: zero clicks and zero impressions in "
                  "this window, so there is nothing to read yet.")
    else:
        name = EARLY
        reason = (f"{clicks} clicks from {impressions} impressions across "
                  f"{pages} pages in this window, below the 10-click mark, "
                  f"so position is the only readable signal.")

    return {"stage": name, "clicks": clicks, "impressions": impressions,
            "pages": pages, "reason": reason}
