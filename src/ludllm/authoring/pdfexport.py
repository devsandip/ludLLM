"""Render finalized manuscript chapters to reading-quality PDFs.

Deliberately self-contained and dependency-light: reportlab is imported lazily
inside the function so the package still imports without it (the writer pipeline
does not depend on PDF output). The full-book runner calls `chapter_md_to_pdf`
after a chapter is accepted; `scripts/chapters_to_pdf.py` calls
`export_accepted_chapters` to backfill everything already on disk.

The chapter files are plain prose: paragraphs separated by blank lines, with
markdown emphasis (`*italic*`). We escape XML, convert the emphasis, and lay the
paragraphs out justified with book-style first-line indents.
"""

from __future__ import annotations

import re
from pathlib import Path

_ITALIC = re.compile(r"\*(.+?)\*", re.DOTALL)


def _para_to_markup(text: str) -> str:
    """One prose paragraph -> reportlab mini-HTML: escape, then *...* -> <i>...</i>."""
    text = " ".join(text.split())  # collapse intra-paragraph newlines/space
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _ITALIC.sub(r"<i>\1</i>", text)
    return text


def chapter_md_to_pdf(
    md_text: str,
    out_path: str | Path,
    *,
    book_title: str,
    chapter_n: int,
    subtitle: str | None = None,
) -> Path:
    """Render one chapter's prose to a single PDF. Returns the output path.

    Raises ImportError if reportlab is unavailable, so callers in an unattended
    run can catch and continue without it.
    """
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    body = ParagraphStyle(
        "Body", fontName="Times-Roman", fontSize=11.5, leading=17.5,
        alignment=TA_JUSTIFY, firstLineIndent=20, spaceBefore=0, spaceAfter=0,
    )
    body_first = ParagraphStyle("BodyFirst", parent=body, firstLineIndent=0)
    title_style = ParagraphStyle(
        "BookTitle", fontName="Times-Roman", fontSize=10, leading=14,
        alignment=TA_CENTER, textColor="#666666", spaceAfter=2, tracking=2,
    )
    chap_style = ParagraphStyle(
        "ChapterNo", fontName="Times-Bold", fontSize=18, leading=24,
        alignment=TA_CENTER, spaceBefore=8, spaceAfter=24,
    )
    sub_style = ParagraphStyle(
        "ChapterSub", fontName="Times-Italic", fontSize=11, leading=15,
        alignment=TA_CENTER, textColor="#444444", spaceAfter=20,
    )

    paras = [p.strip() for p in re.split(r"\n\s*\n", md_text.strip()) if p.strip()]

    story = [
        Paragraph(book_title.upper(), title_style),
        Paragraph(f"Chapter {chapter_n}", chap_style),
    ]
    if subtitle:
        story.append(Paragraph(_para_to_markup(subtitle), sub_style))
    for i, p in enumerate(paras):
        story.append(Paragraph(_para_to_markup(p), body_first if i == 0 else body))

    def _page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 9)
        canvas.setFillColor("#555555")
        canvas.drawCentredString(LETTER[0] / 2, 0.6 * inch, str(doc.page))
        canvas.restoreState()

    doc = SimpleDocTemplate(
        str(out_path), pagesize=LETTER,
        leftMargin=1.1 * inch, rightMargin=1.1 * inch,
        topMargin=1.0 * inch, bottomMargin=1.0 * inch,
        title=f"{book_title} - Chapter {chapter_n}", author="LudLLM",
    )
    if not paras:
        story.append(Spacer(1, 12))
    doc.build(story, onFirstPage=_page_number, onLaterPages=_page_number)
    return out_path


def _accepted_chapters(state) -> list[int]:
    from ludllm.state.schema import ChapterStatus
    return sorted(
        c.n for c in state.running.chapters if c.status == ChapterStatus.accepted
    )


def export_accepted_chapters(
    project, target_dir: str | Path, *, book_title: str, only: int | None = None,
    overwrite: bool = True,
) -> list[Path]:
    """Backfill: render every accepted chapter with prose on disk to the target dir.

    `only` restricts to a single chapter number. Skips chapters whose PDF is newer
    than the source unless `overwrite`. Returns the paths written.
    """
    target_dir = Path(target_dir)
    state = project.load()
    written: list[Path] = []
    chapters = _accepted_chapters(state)
    if only is not None:
        chapters = [n for n in chapters if n == only]
    for n in chapters:
        md = project.manuscript_dir / f"chapter_{n:03d}.md"
        if not md.exists():
            continue
        out = target_dir / f"{book_title} - Chapter {n:02d}.pdf"
        if not overwrite and out.exists() and out.stat().st_mtime >= md.stat().st_mtime:
            continue
        chapter_md_to_pdf(
            md.read_text(encoding="utf-8"), out, book_title=book_title, chapter_n=n
        )
        written.append(out)
    return written
