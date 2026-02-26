# app.py  (READY VERSION WITH UI CONTEXT SUPPORT)

import os, io, json, re, time
import streamlit as st
from dotenv import load_dotenv
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ======================= NEW: LOAD UI CONTEXT =======================
UI_CONTEXT = {}
if os.path.exists("ui_context.json"):
    with open("ui_context.json","r",encoding="utf-8") as f:
        UI_CONTEXT = json.load(f)

# ======================= PAGE CONFIG =======================
st.set_page_config(
    page_title="User Story → Testcase Generator",
    page_icon="✨",
    layout="wide"
)

# --- OpenAI ---
from openai import OpenAI

# ======================= SIMPLE UI =======================
st.title("User Story → Testcase Generator")

user_story = st.text_input("User Story")
ac_text = st.text_area("Acceptance Criteria (one per line)", height=200)

# ======================= OPENAI =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if API_KEY else None

SYSTEM_PROMPT = """
You are a senior test engineer.

You also receive a UI structure (ui_context).
Use it to derive navigation paths.

Rules:
- Use ONLY nodes that exist in ui_context.
- Generate realistic navigation steps.
- Return ONLY JSON.

Schema:
{
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional",
      "steps":[
        {"step":"action","expected":"result"}
      ]
    }
  ]
}
"""

def _json_from_text(txt):
    txt = txt.strip()
    try:
        return json.loads(txt)
    except:
        m = re.search(r"\{.*\}", txt, flags=re.S)
        if m:
            return json.loads(m.group(0))
        return {"test_cases":[]}

# ======================= GENERATOR =======================
def generate_cases(story, ac_blob):
    if not client or not story.strip():
        return []

    payload = {
        "story": story,
        "acceptance_criteria":[l.strip() for l in ac_blob.splitlines() if l.strip()],
        "ui_context": UI_CONTEXT      # ⭐ NEW PART
    }

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":json.dumps(payload, ensure_ascii=False)}
        ]
    )

    data = _json_from_text(resp.choices[0].message.content)
    return data.get("test_cases",[])

# ======================= PDF BUILDER =======================
def build_pdf(story_text, ac_blob, cases):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)

    styles = getSampleStyleSheet()
    flow=[]

    flow.append(Paragraph("User Story", styles["Heading2"]))
    flow.append(Paragraph(story_text, styles["Normal"]))
    flow.append(Spacer(1,10))

    flow.append(Paragraph("Acceptance Criteria", styles["Heading2"]))
    lines=[l for l in ac_blob.splitlines() if l.strip()]
    flow.append(ListFlowable([ListItem(Paragraph(l, styles["Normal"])) for l in lines]))
    flow.append(Spacer(1,10))

    for tc in cases:
        flow.append(Paragraph(tc.get("title",""), styles["Heading3"]))
        for s in tc.get("steps",[]):
            flow.append(Paragraph(f"{s.get('step','')} — {s.get('expected','')}", styles["Normal"]))
        flow.append(Spacer(1,8))

    doc.build(flow)
    buf.seek(0)
    return buf.getvalue()

# ======================= EXPORT =======================
if st.button("Generate PDF"):
    with st.spinner("Generating test design..."):
        cases = generate_cases(user_story, ac_text)
        pdf_bytes = build_pdf(user_story, ac_text, cases)

    st.download_button("Download PDF", data=pdf_bytes, file_name="testcases.pdf")
















