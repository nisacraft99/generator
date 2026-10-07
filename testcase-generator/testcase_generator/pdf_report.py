"""PDF export of a generated test design."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .evaluation.text import acceptance_criteria_lines
from .generation import clean_open_questions

_TABLE_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)


def _table(rows: list[list[Any]], column_widths: list[int]) -> Table:
    table = Table(rows, colWidths=column_widths)
    table.setStyle(_TABLE_STYLE)
    return table


def _fraction(section: dict[str, Any], pct_key: str, count_key: str, total_key: str) -> str:
    """Format a metric as ``covered/total (pct%)``, or ``N/A`` if it was not computed."""
    if section.get(pct_key) is None:
        return "N/A"
    return f"{section[count_key]}/{section[total_key]} ({section[pct_key]}%)"


def build_pdf(
    story: str,
    ac_blob: str,
    cases: list[dict[str, Any]],
    open_questions: list[Any],
    evaluation: dict[str, Any] | None = None,
    story_id: str = "",
) -> bytes:
    """Render user story, optional metrics, open questions and all test cases as a PDF."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36)

    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=22)
    heading = ParagraphStyle("h", parent=styles["Heading2"], fontSize=14)
    body = ParagraphStyle("b", parent=styles["Normal"], fontSize=11, leading=14)
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=10, leading=13, wordWrap="CJK")

    def bullet_list(items: list[str]) -> ListFlowable:
        return ListFlowable(
            [ListItem(Paragraph(item, body), leftIndent=6) for item in items],
            bulletType="bullet",
            leftPadding=12,
        )

    flow: list[Any] = [Paragraph("User Story to Testcase Generator", title), Spacer(1, 10)]

    flow += [Paragraph("<b>User Story ID</b>", heading), Paragraph(story_id.strip() or "—", body), Spacer(1, 8)]
    flow += [Paragraph("<b>User Story</b>", heading), Paragraph(story.strip() or "—", body), Spacer(1, 8)]

    flow.append(Paragraph("<b>Acceptance Criteria</b>", heading))
    criteria = acceptance_criteria_lines(ac_blob)
    flow.append(bullet_list(criteria) if criteria else Paragraph("—", body))
    flow.append(Spacer(1, 12))

    if evaluation:
        metric_rows = [
            ["Metric", "Value"],
            ["AC Coverage", _fraction(evaluation["ac"], "overall_pct", "covered_count", "total_count")],
            [
                "Target Node Coverage",
                _fraction(evaluation.get("target_node", {}), "coverage_pct", "covered_count", "total_count"),
            ],
            [
                "Navigation Path Correctness",
                _fraction(evaluation["navigation_path"], "correctness_pct", "correct_count", "evaluated_count"),
            ],
            ["Role Coverage", _fraction(evaluation["role"], "overall_pct", "covered_count", "total_count")],
            ["Test Cases", str(len(cases))],
        ]
        flow += [Paragraph("<b>Automated Evaluation</b>", heading), _table(metric_rows, [180, 260]), Spacer(1, 12)]

    if open_questions:
        flow += [
            Paragraph("<b>Open Questions</b>", heading),
            bullet_list(clean_open_questions(open_questions)),
            Spacer(1, 12),
        ]

    if not cases:
        flow.append(Paragraph("<b>No test cases were generated.</b>", styles["Normal"]))
        document.build(flow)
        return buffer.getvalue()

    flow += [Paragraph("<b>Generated Test Design</b>", heading), Spacer(1, 6)]
    overview = [["ID", "Title", "Priority", "Type"]]
    for case in cases:
        overview.append([Paragraph(case.get(field, "") or "", cell) for field in ("id", "title", "priority", "type")])
    flow += [_table(overview, [50, 300, 70, 70]), Spacer(1, 12)]

    for case in cases:
        flow.append(Paragraph(f"<b>{case.get('id', '')}</b> — {case.get('title', '')}", styles["Heading3"]))
        step_rows = [[Paragraph(label, styles["Heading5"]) for label in ("Step", "Action", "Expected Result")]]
        for number, step in enumerate(case.get("steps", []) or [], start=1):
            step_rows.append(
                [
                    Paragraph(str(number), cell),
                    Paragraph(step.get("step", "") or "—", cell),
                    Paragraph(step.get("expected", "") or "—", cell),
                ]
            )
        flow += [_table(step_rows, [35, 230, 255]), Spacer(1, 10)]

    document.build(flow)
    return buffer.getvalue()
