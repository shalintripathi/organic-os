"""Render a markdown report as a self-contained HTML page, optionally PDF.

Dependency-free by design: the renderer covers exactly the markdown subset
the Monday report uses (headings, bold, links, lists, tables, paragraphs),
not general markdown. The page carries its whole style inline - no external
CSS, fonts, or scripts - so the file reads the same on a phone, in print,
and inside a chat client's document preview.

PDF is best-effort: find_pdf_converter() probes PATH for a known converter,
to_pdf() invokes it and returns None on any failure. Callers always have
the HTML to fall back on, so nothing here ever raises to them.
"""
import html as _html
import re
import shutil
import subprocess
from pathlib import Path

# Probe order: best HTML fidelity first. Names, not paths - resolution is
# PATH-based at call time, same as invoking them from a shell.
CONVERTERS = ("pandoc", "wkhtmltopdf", "weasyprint", "soffice")

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_ITEM = re.compile(r"^\s*[-*]\s+(.*)$")
_TABLE_SEP = re.compile(r"^\|?[\s:|-]+\|?$")
_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_CODE = re.compile(r"`([^`]+)`")

# RFC 3986 scheme syntax: a letter, then letters/digits/+/-/. , then ":".
_URL_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")
_ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}

_CSS = """
:root { color-scheme: light; }
body { margin: 0; background: #ffffff; color: #1c1c1c;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    Helvetica, Arial, sans-serif;
  line-height: 1.55; font-size: 16px; }
main { max-width: 42em; margin: 0 auto; padding: 24px 20px 48px; }
header.site { border-bottom: 2px solid #1c1c1c; padding-bottom: 8px;
  margin-bottom: 24px; }
header.site .name { font-weight: 600; letter-spacing: 0.02em; }
h1 { font-size: 1.6em; margin: 0.8em 0 0.4em; }
h2 { font-size: 1.2em; margin: 1.4em 0 0.4em;
  border-bottom: 1px solid #d9d9d9; padding-bottom: 4px; }
h3, h4, h5, h6 { font-size: 1em; margin: 1.2em 0 0.3em; }
p { margin: 0.6em 0; }
ul, ol { margin: 0.6em 0; padding-left: 1.4em; }
li { margin: 0.25em 0; }
a { color: #0b57d0; text-decoration: underline; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0;
  font-size: 0.95em; }
th, td { border: 1px solid #c9c9c9; padding: 6px 9px; text-align: left;
  vertical-align: top; }
th { background: #f2f2f2; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: #f4f4f4; padding: 0.1em 0.35em; border-radius: 3px;
  font-size: 0.92em; }
p.redaction-note { border: 1px solid #b58900; background: #fdf6e3;
  padding: 10px 12px; margin: 0 0 20px; font-size: 0.92em; }
@media (max-width: 480px) {
  body { font-size: 15px; }
  main { padding: 16px 12px 32px; }
  table { display: block; overflow-x: auto; }
}
@media print {
  body { font-size: 12pt; }
  main { max-width: none; padding: 0; }
  a { color: inherit; }
}
"""


def _is_safe_url(url: str) -> bool:
    """Allowlist http(s)/mailto/relative links; reject everything else.

    An allowlist only has to name the handful of schemes a report link
    legitimately needs (http, https, mailto) or no scheme at all (a
    relative link, anchor, or bare path). A denylist would instead have to
    enumerate every dangerous scheme -- javascript:, data:, vbscript:, and
    whatever else shows up later -- which is exactly the kind of gap that
    let this bug through in the first place.
    """
    match = _URL_SCHEME.match(url.strip())
    if not match:
        return True
    return match.group(1).lower() in _ALLOWED_URL_SCHEMES


def _link_sub(match: "re.Match[str]") -> str:
    label, url = match.group(1), match.group(2)
    if not _is_safe_url(url):
        # javascript:, data:, etc: drop the link but keep the label as
        # plain text so the surrounding sentence still reads naturally.
        return label
    # The whole text already went through html.escape(quote=False) before
    # this substitution runs (see _inline below), so & < > in `url` are
    # already entity-escaped -- re-escaping them here would double-escape
    # (turning &amp; into &amp;amp;). Only the quote character still needs
    # handling, since quote=False leaves it untouched, and it's the one
    # that lets a URL break out of the href="..." attribute.
    safe_url = url.replace('"', "&quot;")
    return f'<a href="{safe_url}">{label}</a>'


def _inline(text: str) -> str:
    text = _html.escape(text, quote=False)
    # Split on code spans first so link/bold substitution cannot reach inside.
    parts = _CODE.split(text)
    out = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            out.append(f"<code>{part}</code>")
            continue
        part = _LINK.sub(_link_sub, part)
        part = _BOLD.sub(r"<strong>\1</strong>", part)
        out.append(part)
    return "".join(out)


def _flush_paragraph(buf, out):
    if buf:
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
        buf.clear()


def _table_cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _render_body(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out, para, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        m = _HEADING.match(line)
        if m:
            _flush_paragraph(para, out)
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2).strip())}</h{level}>")
            i += 1
            continue
        if (line.lstrip().startswith("|") and i + 1 < len(lines)
                and _TABLE_SEP.match(lines[i + 1].strip())
                and "|" in lines[i + 1]):
            _flush_paragraph(para, out)
            head = _table_cells(line)
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_table_cells(lines[i]))
                i += 1
            out.append("<table>")
            out.append("<thead><tr>"
                       + "".join(f"<th>{_inline(c)}</th>" for c in head)
                       + "</tr></thead>")
            out.append("<tbody>")
            for row in rows:
                out.append("<tr>"
                           + "".join(f"<td>{_inline(c)}</td>" for c in row)
                           + "</tr>")
            out.append("</tbody></table>")
            continue
        if _LIST_ITEM.match(line):
            _flush_paragraph(para, out)
            out.append("<ul>")
            while i < len(lines):
                m = _LIST_ITEM.match(lines[i])
                if not m:
                    break
                out.append(f"<li>{_inline(m.group(1).strip())}</li>")
                i += 1
            out.append("</ul>")
            continue
        if not line.strip():
            _flush_paragraph(para, out)
            i += 1
            continue
        para.append(line.strip())
        i += 1
    _flush_paragraph(para, out)
    return "\n".join(out)


def _redaction_note(markdown_text: str) -> str:
    """A marked block naming what the report body carries, or "".

    ADVISORY ONLY. The body is rendered exactly as written either way: this
    reports, it does not redact, and it never stops a report from being
    produced. Any failure inside the scan returns "" and the render
    continues.
    """
    try:
        from . import redact
        line = redact.summarize(redact.scan(markdown_text))
    except Exception:
        return ""
    if not line:
        return ""
    return ('<p class="redaction-note"><strong>Redaction check (advisory)</strong>'
            f"<br>{_html.escape(line, quote=False)}"
            "<br>Nothing was removed from this report and no send was "
            "blocked. Check the flagged values before sharing this file; a "
            "high-tier finding means the value is already in the report.</p>\n")


def render_html(markdown_text: str, title: str, site_name: str) -> str:
    """The markdown report as one self-contained, phone-and-print-ready page."""
    return ("<!doctype html>\n"
            '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f"<title>{_html.escape(title, quote=False)}</title>\n"
            f"<style>{_CSS}</style>\n</head>\n<body>\n<main>\n"
            '<header class="site"><span class="name">'
            f"{_html.escape(site_name, quote=False)}</span></header>\n"
            f"{_redaction_note(markdown_text)}"
            f"{_render_body(markdown_text)}\n"
            "</main>\n</body>\n</html>\n")


def find_pdf_converter():
    """The first known HTML-to-PDF converter on PATH, or None."""
    for name in CONVERTERS:
        if shutil.which(name):
            return name
    return None


def to_pdf(html_path, converter):
    """Convert the rendered HTML to PDF next to it. None on any failure."""
    html_path = Path(html_path)
    pdf_path = html_path.with_suffix(".pdf")
    commands = {
        "pandoc": ["pandoc", str(html_path), "-o", str(pdf_path)],
        "wkhtmltopdf": ["wkhtmltopdf", str(html_path), str(pdf_path)],
        "weasyprint": ["weasyprint", str(html_path), str(pdf_path)],
        "soffice": ["soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(html_path.parent), str(html_path)],
    }
    cmd = commands.get(converter)
    if cmd is None:
        return None
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode == 0 and pdf_path.exists():
        return pdf_path
    return None
