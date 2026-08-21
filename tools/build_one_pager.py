"""Render `docs/one-pager.md` to `docs/one-pager.pdf`.

    just one-pager

The words live in the Markdown file, not in this script, and that is the point:
a one-page description is a thing the human entrant will want to reword the night
before submitting, and a PDF nobody can edit without the tool that made it is a
dead end. Edit the prose, re-run this, commit both.

**reportlab is not a dependency of the application.** The product has no reason
to know how to make a PDF, so the justfile pulls it in for the length of this one
command with `uv run --with reportlab`. Nothing in `pyproject.toml` changes.

The one hard requirement is in `main`: the finished file is re-opened and its
pages counted. "One page" is the entire brief, and it is exactly the kind of
thing that silently becomes two pages when somebody adds a sentence.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Spacer,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "one-pager.md"
OUTPUT = ROOT / "docs" / "one-pager.pdf"

INK = HexColor("#16202c")
MUTED = HexColor("#5a6b7d")
ACCENT = HexColor("#14507a")

# The same colours as the interface (web/src/index.css), so the printed page and
# the running app look like the same project.
# Sizes chosen by rendering and looking, then filling the page. The guard in
# `main` is what makes that safe to do: overshoot and the build fails rather than
# quietly producing two pages.
TITLE = ParagraphStyle(
    "title", fontName="Helvetica-Bold", fontSize=23, leading=26, textColor=INK, spaceAfter=3
)
TAGLINE = ParagraphStyle(
    "tagline", fontName="Helvetica-Oblique", fontSize=12, leading=15, textColor=ACCENT,
    spaceAfter=11,
)
HEADING = ParagraphStyle(
    "heading", fontName="Helvetica-Bold", fontSize=9.4, leading=11, textColor=MUTED,
    spaceBefore=10, spaceAfter=3.5,
)
BODY = ParagraphStyle(
    "body", fontName="Helvetica", fontSize=9.9, leading=13.2, textColor=INK,
    alignment=TA_JUSTIFY, spaceAfter=5,
)
BULLET = ParagraphStyle("bullet", parent=BODY, alignment=TA_JUSTIFY, spaceAfter=3.5)
FOOTER = ParagraphStyle(
    "footer", fontName="Helvetica", fontSize=8.8, leading=11, textColor=MUTED, spaceBefore=6
)


def inline(text: str) -> str:
    """Markdown emphasis and code spans to the tag soup reportlab understands."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="9">\1</font>', text)
    return text


def build_story(markdown: str) -> list:
    """Turn the small subset of Markdown the one-pager uses into flowables."""
    story: list = []
    bullets: list = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), BODY))
            paragraph.clear()

    def flush_bullets() -> None:
        if bullets:
            story.append(
                ListFlowable(
                    [ListItem(Paragraph(inline(b), BULLET), leftIndent=9) for b in bullets],
                    bulletType="bullet",
                    bulletFontSize=6,
                    bulletOffsetY=-1,
                    leftIndent=9,
                    spaceAfter=3,
                )
            )
            bullets.clear()

    for raw in markdown.splitlines():
        line = raw.rstrip()

        if line.startswith("% "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(inline(line[2:]), TITLE if len(story) == 0 else TAGLINE))
        elif line.startswith("## "):
            flush_paragraph()
            flush_bullets()
            story.append(Paragraph(inline(line[3:]).upper(), HEADING))
        elif line.startswith("- "):
            flush_paragraph()
            bullets.append(line[2:])
        elif not line:
            flush_paragraph()
            flush_bullets()
        elif bullets:
            # A wrapped continuation of the bullet above it.
            bullets[-1] += " " + line
        else:
            paragraph.append(line)

    flush_paragraph()
    flush_bullets()

    # The last line is the repository address; give it the quieter style.
    if story and isinstance(story[-1], Paragraph):
        story[-1] = Paragraph(story[-1].text, FOOTER)
    return story


def page_count(path: Path) -> int:
    """Count pages by reading the finished file, not by trusting the builder."""
    data = path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def main() -> int:
    document = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        title="Why Not This Trial",
        author="UnivaBio 2026 submission",
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=12 * mm,
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    document.addPageTemplates([PageTemplate(id="one", frames=[frame])])
    story = build_story(SOURCE.read_text())
    story.append(Spacer(1, 1))
    document.build(story)

    pages = page_count(OUTPUT)
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size // 1024} KB, {pages} page)")
    if pages != 1:
        print(
            f"ERROR: the brief is one page and this is {pages}. Cut words from "
            f"{SOURCE.relative_to(ROOT)} — do not shrink the type below 8pt.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
