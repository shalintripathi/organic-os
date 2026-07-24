import os
import stat
import sys
from pathlib import Path

LIB = Path(__file__).resolve().parents[1] / "plugin" / "lib"
sys.path.insert(0, str(LIB))

from core import report_render as R  # noqa: E402


SAMPLE = """# Monday report

## What moved

- **Clicks** rose from 120 to 150 ([signal](../signals/2026-07-13.md))
- AI referrals: 12 this week, up from 9

## What shipped

| Item | Status |
|---|---|
| p-20260713-title | applied |
| b-20260710-guide | published |

## What needs you

Nothing is waiting on a decision this week.
"""


def test_render_html_covers_the_report_subset():
    out = R.render_html(SAMPLE, title="Monday report", site_name="Example Site")
    assert "<h1>Monday report</h1>" in out
    assert "<h2>What moved</h2>" in out
    assert "<strong>Clicks</strong>" in out
    assert '<a href="../signals/2026-07-13.md">signal</a>' in out
    assert "<li>" in out
    assert "<table>" in out and "<th>Item</th>" in out
    assert "<td>applied</td>" in out
    assert "<p>Nothing is waiting on a decision this week.</p>" in out
    assert "Example Site" in out
    assert "<title>Monday report</title>" in out


def test_render_html_is_self_contained():
    # The page chrome references nothing external: content with no URLs
    # must render to HTML with no URLs at all - no CDN CSS, fonts, or
    # scripts smuggled in by the template.
    out = R.render_html("# T\n\nA plain paragraph.", title="T", site_name="S")
    assert "http" not in out
    assert "<script" not in out.lower()
    assert "<style>" in out  # inline CSS only


def test_render_html_escapes_raw_html():
    out = R.render_html("A <script>alert(1)</script> tag.",
                        title="T", site_name="S")
    assert "<script>alert(1)</script>" not in out
    assert "&lt;script&gt;" in out


def _fake_bin(dirpath, name, body="#!/bin/sh\nexit 0\n"):
    p = dirpath / name
    p.write_text(body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_find_pdf_converter_probes_path_in_order(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    monkeypatch.setenv("PATH", str(bindir))
    assert R.find_pdf_converter() is None
    _fake_bin(bindir, "weasyprint")
    assert R.find_pdf_converter() == "weasyprint"
    # pandoc outranks weasyprint in the declared order
    _fake_bin(bindir, "pandoc")
    assert R.find_pdf_converter() == "pandoc"


def test_to_pdf_returns_path_when_converter_succeeds(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    # A fake wkhtmltopdf that writes its second argument.
    _fake_bin(bindir, "wkhtmltopdf",
              "#!/bin/sh\nprintf 'pdf' > \"$2\"\nexit 0\n")
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ["PATH"])
    html = tmp_path / "r.html"
    html.write_text("<p>hi</p>")
    out = R.to_pdf(html, "wkhtmltopdf")
    assert out == html.with_suffix(".pdf")
    assert out.read_bytes() == b"pdf"


def test_to_pdf_returns_none_when_converter_fails(tmp_path, monkeypatch):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    _fake_bin(bindir, "wkhtmltopdf", "#!/bin/sh\nexit 1\n")
    monkeypatch.setenv("PATH", str(bindir))
    html = tmp_path / "r.html"
    html.write_text("<p>hi</p>")
    assert R.to_pdf(html, "wkhtmltopdf") is None


def test_to_pdf_never_raises_on_a_missing_converter(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))  # empty PATH dir
    html = tmp_path / "r.html"
    html.write_text("<p>hi</p>")
    assert R.to_pdf(html, "wkhtmltopdf") is None


def test_render_html_renders_deeper_heading_levels():
    out = R.render_html("### Detail\n\ntext", title="T", site_name="S")
    assert "<h3>Detail</h3>" in out


def test_render_html_joins_wrapped_paragraph_lines():
    out = R.render_html("One line\nwrapped onto two.", title="T", site_name="S")
    assert "<p>One line wrapped onto two.</p>" in out


def test_render_html_table_cells_carry_inline_markup():
    md = "| Item |\n|---|\n| **bold** [x](y.md) |"
    out = R.render_html(md, title="T", site_name="S")
    assert "<td><strong>bold</strong> <a href=\"y.md\">x</a></td>" in out


def test_to_pdf_unknown_converter_returns_none(tmp_path):
    html = tmp_path / "r.html"
    html.write_text("<p>hi</p>")
    assert R.to_pdf(html, "not-a-converter") is None


# -- advisory redaction note ---------------------------------------------------
#
# The renderer reports what the report body carries. It never edits the body
# and never refuses to render.

from core import redact  # noqa: E402

PLANTED_REPORT = """# Monday report

## What shipped

- rotated the key, api_key=FAKE-API-KEY-VALUE-abcdefghij, on Tuesday
"""


def test_render_html_notes_a_finding_near_the_top():
    html = R.render_html(PLANTED_REPORT, "Monday report", "Example")
    assert "Redaction check" in html
    assert "redaction: 1 high finding(s)" in html
    # Near the top: ahead of the body's first heading.
    assert html.index("Redaction check") < html.index("<h1>")


def test_render_html_does_not_edit_the_body_it_flags():
    html = R.render_html(PLANTED_REPORT, "Monday report", "Example")
    assert "api_key=FAKE-API-KEY-VALUE-abcdefghij" in html


def test_render_html_adds_no_note_to_a_clean_report():
    html = R.render_html(SAMPLE, "Monday report", "Example")
    assert "Redaction check" not in html


def test_render_html_still_renders_when_the_scan_raises(monkeypatch):
    def boom(_text):
        raise RuntimeError("scanner exploded")

    monkeypatch.setattr(redact, "scan", boom)
    html = R.render_html(PLANTED_REPORT, "Monday report", "Example")
    assert "Redaction check" not in html
    assert "<h1>Monday report</h1>" in html


def test_render_html_inline_code_spans():
    out = R.render_html("- `p-20260713-title` [onpage-fix] Fix the title",
                        title="T", site_name="S")
    assert "<code>p-20260713-title</code>" in out
    assert "`p-20260713-title`" not in out


def test_render_html_code_spans_are_literal():
    md = "before `**not bold** [not a link](x)` after"
    out = R.render_html(md, title="T", site_name="S")
    assert "<code>**not bold** [not a link](x)</code>" in out
    assert "<strong>" not in out.split("<code>")[1].split("</code>")[0]
    assert "<a href" not in out.split("<code>")[1].split("</code>")[0]


def test_render_html_escapes_inside_code_spans():
    out = R.render_html("x `<script>y</script>` z", title="T", site_name="S")
    assert "<code>&lt;script&gt;y&lt;/script&gt;</code>" in out


# -- link safety (#19) ---------------------------------------------------------
#
# Report content carries brain data (titles, reasoning excerpts, URLs), so a
# link URL is hostile input. A quote must not break out of the href attribute,
# and only http, https, mailto, and relative URLs may become anchors; any
# other scheme renders its label as plain text with no anchor at all.


def test_link_url_quote_cannot_break_out_of_href():
    out = R.render_html('[click](x"onmouseover="stealcookies)',
                        title="T", site_name="S")
    # The quote is an entity inside the attribute, nothing more...
    assert '<a href="x&quot;onmouseover=&quot;stealcookies">click</a>' in out
    # ...so the page contains no injected attribute anywhere.
    assert '"x"onmouseover=' not in out
    assert 'onmouseover="stealcookies"' not in out


def test_javascript_scheme_link_renders_label_as_plain_text():
    out = R.render_html("[click](javascript:doevil)", title="T", site_name="S")
    assert "<p>click</p>" in out
    assert "<a" not in out
    assert "javascript" not in out
    assert "doevil" not in out


def test_data_scheme_link_renders_label_as_plain_text():
    out = R.render_html("[click](data:text/html,ohno)", title="T", site_name="S")
    assert "<p>click</p>" in out
    assert "<a" not in out
    assert "data:" not in out
    assert "ohno" not in out


def test_scheme_check_survives_case_and_control_char_tricks():
    # Browsers lowercase the scheme and drop leading C0 controls before
    # deciding what a URL means, so the renderer must normalize the same
    # way or these two still execute.
    for url in ("JaVaScRiPt:doevil", "\x01javascript:doevil"):
        out = R.render_html(f"[click]({url})", title="T", site_name="S")
        assert "<p>click</p>" in out, url
        assert "<a" not in out, url
        assert "doevil" not in out, url


def test_safe_and_relative_link_schemes_still_render():
    md = ("[site](https://example.com/page) "
          "[plain](http://example.com/page) "
          "[mail](mailto:team@example.com) "
          "[root](/page) [file](page.html)")
    out = R.render_html(md, title="T", site_name="S")
    assert '<a href="https://example.com/page">site</a>' in out
    assert '<a href="http://example.com/page">plain</a>' in out
    assert '<a href="mailto:team@example.com">mail</a>' in out
    assert '<a href="/page">root</a>' in out
    assert '<a href="page.html">file</a>' in out


def test_link_url_ampersand_is_escaped_exactly_once():
    # The attribute pass must not re-escape what _inline already escaped.
    out = R.render_html("[q](https://example.com/?a=b&c=d)",
                        title="T", site_name="S")
    assert '<a href="https://example.com/?a=b&amp;c=d">q</a>' in out
    assert "&amp;amp;" not in out
