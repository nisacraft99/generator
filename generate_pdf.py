# generate_pdf.py
# Create a clean PDF with a Test Case summary and, for each test case,
# a neat "Step | Action | Expected Result" table (wrapped, zebra, split across pages).
#
# Uses OpenAI if OPENAI_API_KEY is set to generate JSON. Otherwise this script
# only formats whatever JSON you pass it (kept here for completeness).
#
# pip install openai python-dotenv reportlab

import os, re, sys, json, textwrap
from typing import List, Dict, Any
from dotenv import load_dotenv
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

# -------------------------------
# OpenAI (optional)
# -------------------------------
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = None
try:
    from openai import OpenAI
    if API_KEY:
        client = OpenAI(api_key=API_KEY)
except Exception:
    client = None

# A stricter, clearer schema for the model
SYSTEM = """
You are a senior test engineer.
Return ONLY valid JSON with this schema:

{
  "metadata": {"source_id": "string"},
  "design": {
    "equivalence_classes": ["string", ...],
    "boundary_values": ["string", ...],
    "negative_cases": ["string", ...]
  },
  "traceability": [
    {"criterion": "string", "covered_by": ["TC-1", "TC-2", "..."]}
  ],
  "test_cases": [
    {
      "id": "TC-1",
      "title": "string",
      "priority": "High|Medium|Low",
      "type": "Functional|Negative|Boundary|Security|Performance|Usability",
      "steps": [
        {"step": "concise action", "expected": "concise observable result"}
      ]
    }
  ]
}

Rules:
- Provide 3–6 focused test cases.
- Each test case MUST have at least 3 steps; every step has both 'step' and 'expected'.
- Be concise and testable. No Gherkin. No markdown. No code fences.
"""

# -------------------------------
# Read User Story (stdin)
# -------------------------------
def read_user_story_from_stdin() -> Dict[str, Any]:
    print(
        "Paste your User Story below.\n"
        "Optional: add Acceptance Criteria on new lines starting with 'AC:'.\n"
        "When done, type a single line: END and press Enter.\n"
        "------------------------------------------------------"
    )
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)

    txt = "\n".join(lines).strip()
    if not txt:
        return {}

    rows = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    story = rows[0]
    acs = [ln[3:].strip() for ln in rows[1:] if ln.lower().startswith("ac:")]
    return {"user_story": story, "acceptance_criteria": acs, "id": "US-NEW"}

# -------------------------------
# Call Model → JSON
# -------------------------------
def call_model(payload: dict, model="gpt-4o-mini", temperature=0.1, max_retries=2) -> dict:
    if not client:
        raise RuntimeError("No OpenAI client available. Set OPENAI_API_KEY in .env.")

    last_err = None
    for _ in range(max_retries + 1):
        resp = client.chat.completions.create(
            model=model, temperature=temperature,
            messages=[{"role":"system","content":SYSTEM},
                      {"role":"user","content":json.dumps(payload, ensure_ascii=False)}]
        )
        txt = resp.choices[0].message.content.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```(\w+)?\s*", "", txt)
            txt = re.sub(r"\s*```$", "", txt).strip()
        try:
            data = json.loads(txt)
            # minimal validation
            for key in ["metadata","design","traceability","test_cases"]:
                if key not in data:
                    raise ValueError(f"Missing key '{key}'")
            return data
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Failed to parse model JSON. Last error: {last_err}")

# -------------------------------
# Backward compatibility parser
# If you only have a big text block in 'testcases' OR a text blob per TC,
# we try to parse sections like:
#   TC-1 — Title
#   1. Do something
#   -> Expected result
#   2. ...
# -------------------------------
TC_HEADER_RE = re.compile(r"^\s*(TC[-\s]*\d+)\s+[—-]\s+(.+?)\s*$")
STEP_RE      = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*$")
EXPECT_RE    = re.compile(r"^\s*->\s*(.+?)\s*$")

def parse_legacy_testcases_blob(blob: str) -> List[Dict[str, Any]]:
    """
    Turn a legacy 'testcases' string into:
    [{"id":"TC-1","title":"...","priority":"","type":"","steps":[{"step":"...","expected":"..."}]}, ...]
    """
    blob = textwrap.dedent(blob or "").strip()
    if not blob:
        return []

    cases: List[Dict[str, Any]] = []
    current: Dict[str, Any] = {}
    lines = [l.rstrip() for l in blob.splitlines() if l.strip()]

    for line in lines:
        m_hdr = TC_HEADER_RE.match(line)
        if m_hdr:
            # new case
            if current:
                if "steps" not in current:
                    current["steps"] = []
                cases.append(current)
            current = {
                "id": m_hdr.group(1).replace(" ", ""),
                "title": m_hdr.group(2).strip(),
                "priority": "",
                "type": "",
                "steps": []
            }
            continue

        m_step = STEP_RE.match(line)
        if m_step:
            # new step in current case
            if not current:
                # if steps appear before a header, create a default case
                current = {"id":"TC-1","title":"", "priority":"","type":"","steps":[]}
            current["steps"].append({"step": m_step.group(2).strip(), "expected": ""})
            continue

        m_exp = EXPECT_RE.match(line)
        if m_exp and current and current.get("steps"):
            current["steps"][-1]["expected"] = m_exp.group(1).strip()
            continue

        # continuation lines
        if current and current.get("steps"):
            s = current["steps"][-1]
            if s.get("expected"):
                s["expected"] += " " + line.strip()
            else:
                s["step"] += " " + line.strip()

    if current:
        if "steps" not in current:
            current["steps"] = []
        cases.append(current)

    # ensure IDs sane
    for i, tc in enumerate(cases, start=1):
        if not tc.get("id"):
            tc["id"] = f"TC-{i}"
    return cases

# -------------------------------
# PDF rendering
# -------------------------------
def table(style_rows, col_widths=None) -> Table:
    t = Table(style_rows, colWidths=col_widths, repeatRows=1, splitByRow=1)
    t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.3,colors.grey),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#9fd2ff")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),6),
        ("RIGHTPADDING",(0,0),(-1,-1),6),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.whitesmoke, colors.HexColor("#eef7ff")]),
        ("FONTSIZE",(0,0),(-1,-1),9),
    ]))
    return t

def build_pdf(data: dict, out_path="testcases.pdf"):
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=10, leading=13, wordWrap="CJK")

    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36)
    elems: List[Any] = []

    # Title
    sid = (data.get("metadata") or {}).get("source_id") or "User Story"
    elems += [Paragraph(f"<b>Test Design for:</b> {sid}", styles["Title"]), Spacer(1, 10)]

    # Design
    design = data.get("design", {}) or {}
    drows = [["Section","Items"],
             ["Equivalence classes", Paragraph("<br/>".join(design.get("equivalence_classes", [])) or "—", cell)],
             ["Boundary values",   Paragraph("<br/>".join(design.get("boundary_values", [])) or "—", cell)],
             ["Negative cases",    Paragraph("<br/>".join(design.get("negative_cases", [])) or "—", cell)]]
    elems += [table(drows, [150, 350]), Spacer(1, 14)]

    # Traceability
    trace = data.get("traceability", []) or []
    trows = [["Acceptance Criterion","Covered By (TC IDs)"]]
    for t in trace:
        trows.append([Paragraph(t.get("criterion",""), cell),
                      Paragraph(", ".join(t.get("covered_by", [])), cell)])
    elems += [table(trows, [300, 200]), Spacer(1, 16)]

    # ------ Test cases ------
    test_cases = data.get("test_cases")
    if not test_cases:
        # legacy fallback from big text blob
        test_cases = parse_legacy_testcases_blob(data.get("testcases",""))

    # Summary table
    if test_cases:
        sum_rows = [["ID","Title","Priority","Type"]]
        for tc in test_cases:
            sum_rows.append([
                Paragraph(tc.get("id",""), cell),
                Paragraph(tc.get("title",""), cell),
                Paragraph(tc.get("priority",""), cell),
                Paragraph(tc.get("type",""), cell),
            ])
        elems += [Paragraph("<b>Test Case Summary</b>", styles["Heading2"]),
                  Spacer(1,6),
                  table(sum_rows, [50, 300, 70, 70]),
                  Spacer(1, 10)]

        # One table per test case
        for idx, tc in enumerate(test_cases):
            if idx:  # add a little gap between cases
                elems.append(Spacer(1, 8))
            elems.append(Paragraph(f"<b>{tc.get('id','')}</b> — {tc.get('title','')}", styles["Heading3"]))
            steps = tc.get("steps", []) or []
            step_rows = [[
                Paragraph("Step", styles["Heading5"]),
                Paragraph("Action", styles["Heading5"]),
                Paragraph("Expected Result", styles["Heading5"])
            ]]
            if steps:
                for i, s in enumerate(steps, start=1):
                    step_rows.append([
                        Paragraph(str(i), cell),
                        Paragraph(s.get("step",""), cell),
                        Paragraph(s.get("expected",""), cell),
                    ])
            else:
                step_rows.append([Paragraph("—", cell), Paragraph("—", cell), Paragraph("—", cell)])

            elems += [table(step_rows, [35, 230, 255])]
            # split to new page if the table grows too long naturally (ReportLab handles it)

    else:
        elems += [Paragraph("<b>No test cases were found.</b>", styles["Normal"])]

    doc.build(elems)

# -------------------------------
# Main
# -------------------------------
if __name__ == "__main__":
    payload = read_user_story_from_stdin()
    if not payload:
        print("❌ No input provided. Paste the User Story, then type END on a new line.")
        sys.exit(1)

    # Call model if possible; otherwise, expect user to replace 'data' manually.
    try:
        if client:
            data = call_model(payload, model="gpt-4o-mini", temperature=0.0)
        else:
            raise RuntimeError("No OpenAI API key; cannot generate.")
    except Exception as e:
        print(f"⚠️ OpenAI generation unavailable: {e}")
        print("Provide a JSON file matching the schema and I'll format it.")
        sys.exit(1)

    try:
        build_pdf(data, out_path="testcases.pdf")
        print("✅ PDF saved as testcases.pdf")
    except Exception as e:
        print(f"❌ Failed to write PDF: {e}")
        sys.exit(1)
