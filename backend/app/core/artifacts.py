# backend/app/core/artifacts.py

from typing import Dict, Any, List, Tuple
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable
from reportlab.lib import colors
import datetime
import re

class PDFRenderer:
    """Render job results as polished PDFs using ReportLab.

    Improvements in this version:
    - Consistent headers + timestamps
    - Proper bullet lists (unordered + ordered)
    - Basic Markdown-like rendering:
        * '#', '##', '###' headings
        * '- ' and '* ' bullets
        * '1. ' numbered lists
        * **bold** and *italic* inline
        * Paragraph spacing and line breaks
    - Normalization helpers for Enhance/Cover Letter content
    """

    def __init__(self):
        styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            name="TitleCentered",
            parent=styles["Title"],
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        self.h1 = styles["Heading1"]
        self.h2 = styles["Heading2"]
        self.h3 = styles["Heading3"]
        self.body = styles["BodyText"]

        # Slightly tighter body text for letters
        self.body_letter = ParagraphStyle(
            name="BodyLetter",
            parent=self.body,
            leading=14
        )

    # ---------- Public API ----------
    def build_match_pdf(self, path: str, result: Dict[str, Any]) -> None:
        """Structured, sectioned report for matching results."""
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm
        )
        flow: List = []
        flow += self._header("Resume ↔ JD Match Report")

        score = result.get("match_score", "N/A")
        strengths: List[str] = result.get("strengths", []) or []
        gaps: List[str] = result.get("gaps", []) or []
        summary = result.get("summary", "")

        flow.append(Paragraph("Overall Score", self.h2))
        flow.append(Paragraph(f"<b>{self._escape_html(str(score))}%</b>", self.body))
        flow.append(Spacer(1, 0.3 * cm))

        flow.append(Paragraph("Strengths", self.h2))
        flow += self._bullet_list(strengths)
        flow.append(Spacer(1, 0.3 * cm))

        flow.append(Paragraph("Gaps", self.h2))
        flow += self._bullet_list(gaps)
        flow.append(Spacer(1, 0.3 * cm))

        flow.append(Paragraph("Summary", self.h2))
        flow.append(Paragraph(self._nl2br(self._escape_html(summary or "_No summary provided._")), self.body))

        doc.build(flow)

    def build_enhance_pdf(self, path: str, result: Dict[str, Any]) -> None:
        """Render enhancement suggestions with clear sections and bullets."""
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm
        )
        flow: List = []
        flow += self._header("Resume Enhancement Suggestions")

        raw_md = result.get("resume_enhancement_md", "") or "_No suggestions generated._"
        md = self._normalize_enhance_md(raw_md)
        flow += self._markdown_to_flowables(md, use_letter_style=False)

        doc.build(flow)

    def build_cover_letter_pdf(self, path: str, result: Dict[str, Any]) -> None:
        """Render the cover letter with readable paragraph spacing."""
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm
        )
        flow: List = []
        flow += self._header("Cover Letter")

        raw_md = result.get("cover_letter_md", "") or "_No cover letter generated._"
        md = self._normalize_cover_letter_md(raw_md)
        flow += self._markdown_to_flowables(md, use_letter_style=True)

        doc.build(flow)

    def build_generic_pdf(self, path: str, title: str, body_text_or_md: str) -> None:
        """Fallback generic PDF with a title and markdown-ish body."""
        doc = SimpleDocTemplate(
            path, pagesize=A4,
            topMargin=2 * cm, bottomMargin=2 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm
        )
        flow: List = []
        flow += self._header(title)
        flow += self._markdown_to_flowables(body_text_or_md or "_No content._", use_letter_style=False)
        doc.build(flow)

    # ---------- Section Builders ----------
    def _header(self, title: str) -> List:
        now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        return [
            Paragraph(title, self.title_style),
            Paragraph(f"<font size=9 color=grey>Generated: {self._escape_html(now)}</font>", self.body),
            Spacer(1, 0.5 * cm),
        ]

    def _bullet_list(self, items: List[str]) -> List:
        """Unordered bullet list with clean bullets."""
        if not items:
            return [Paragraph("<i>None</i>", self.body)]
        paras = [Paragraph(self._inline_format(self._escape_html(x)), self.body) for x in items]
        return [ListFlowable(
            paras,
            bulletType="bullet",
            leftIndent=10,
            bulletColor=colors.black,
        )]

    def _numbered_list(self, items: List[str]) -> List:
        """Ordered list (1., 2., 3., ...)"""
        if not items:
            return [Paragraph("<i>None</i>", self.body)]
        paras = [Paragraph(self._inline_format(self._escape_html(x)), self.body) for x in items]
        return [ListFlowable(
            paras,
            bulletType="1",
            leftIndent=10,
            bulletColor=colors.black,
        )]

    # ---------- Markdown-lite Rendering ----------
    def _markdown_to_flowables(self, text: str, use_letter_style: bool) -> List:
        """
        Very light-weight markdown-ish parser to make nice PDFs:
        - '# ', '## ', '### ' headings
        - '- ' or '* ' unordered bullets
        - '1. ' ordered bullets
        - Blank lines -> paragraph spacing
        - Inline **bold** and *italic* supported
        """
        lines = text.splitlines()
        flow: List = []
        buffer_ul: List[str] = []
        buffer_ol: List[str] = []

        def flush_lists():
            nonlocal buffer_ul, buffer_ol, flow
            if buffer_ul:
                flow += self._bullet_list(buffer_ul)
                flow.append(Spacer(1, 0.2 * cm))
                buffer_ul = []
            if buffer_ol:
                flow += self._numbered_list(buffer_ol)
                flow.append(Spacer(1, 0.2 * cm))
                buffer_ol = []

        p_style = self.body_letter if use_letter_style else self.body

        for raw in lines:
            line = raw.rstrip()

            # Blank line separates blocks
            if not line.strip():
                flush_lists()
                flow.append(Spacer(1, 0.2 * cm))
                continue

            # Headings
            if line.startswith("### "):
                flush_lists()
                flow.append(Paragraph(self._escape_html(line[4:]), self.h3))
                continue
            if line.startswith("## "):
                flush_lists()
                flow.append(Paragraph(self._escape_html(line[3:]), self.h2))
                continue
            if line.startswith("# "):
                flush_lists()
                flow.append(Paragraph(self._escape_html(line[2:]), self.h1))
                continue

            # Ordered list "1. ", "2. ", etc.
            m_num = re.match(r"^\s*\d+\.\s+(.*)$", line)
            if m_num:
                buffer_ol.append(m_num.group(1))
                continue

            # Unordered bullets "- " or "* "
            if line.lstrip().startswith("- "):
                buffer_ul.append(line.lstrip()[2:])
                continue
            if line.lstrip().startswith("* "):
                buffer_ul.append(line.lstrip()[2:])
                continue

            # Normal paragraph
            flush_lists()
            flow.append(Paragraph(self._nl2br(self._inline_format(self._escape_html(line))), p_style))

        flush_lists()
        return flow

    # ---------- Normalizers for specific job types ----------
    def _normalize_enhance_md(self, md: str) -> str:
        """Ensure standard sections exist for Enhance output."""
        text = md.strip()
        if not text:
            return "_No suggestions generated._"

        # If it doesn't contain an H2, add standard headings
        has_h2 = any(line.startswith("## ") for line in text.splitlines())
        if not has_h2:
            # Heuristic split: first paragraph as intro, then bullets become "Improvements"
            parts = text.splitlines()
            bullets = [p[2:] for p in parts if p.lstrip().startswith("- ")]
            intro = "\n".join(p for p in parts if not p.lstrip().startswith("- "))
            rebuilt = "## Improvements\n"
            if bullets:
                rebuilt += "\n".join(f"- {b}" for b in bullets)
            else:
                rebuilt += "_No bullet suggestions found._"
            if intro.strip():
                rebuilt = f"## Notes\n{intro.strip()}\n\n" + rebuilt
            return rebuilt

        return text

    def _normalize_cover_letter_md(self, md: str) -> str:
        """Make sure the letter reads well; add minimal structure if missing."""
        text = md.strip()
        if not text:
            return "_No cover letter generated._"

        # If there are no headings at all, just return as paragraphs
        has_heading = any(line.startswith("#") for line in text.splitlines())
        if not has_heading:
            return text

        return text

    # ---------- Inline helpers ----------
    @staticmethod
    def _nl2br(text: str) -> str:
        """Convert newlines to <br/> for ReportLab Paragraph."""
        return text.replace("\n", "<br/>")

    @staticmethod
    def _escape_html(text: str) -> str:
        """Minimal XML/HTML escaping for ReportLab Paragraph."""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )

    @staticmethod
    def _inline_format(text: str) -> str:
        """Convert **bold** and *italic* markdown to HTML for ReportLab."""
        # Bold: **text**
        text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
        # Italic: *text*
        text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", text)
        return text
