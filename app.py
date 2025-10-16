# app.py — Aqua + Comic Sans, cut-off fix, tall AC box, and PDF with pretty Step/Action/Expected tables
# Run:
#   conda activate thesis
#   pip install streamlit python-dotenv reportlab openai
#   streamlit run app.py

import os, io, json, re, time
import streamlit as st
from dotenv import load_dotenv
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem, Table, TableStyle
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- OpenAI (optional for test design) ---
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

st.set_page_config(page_title="Amazing User Story to Testcase Generator", page_icon="📝", layout="wide")

# --- Kawaii Password Gate (updated sizing + centering) ---
import os
import streamlit as st

APP_PASSWORD = st.secrets.get("APP_PASSWORD", os.getenv("APP_PASSWORD", ""))

if "auth_ok" not in st.session_state:
    st.session_state.auth_ok = False

def try_login():
    if st.session_state.get("pw_input", "") == APP_PASSWORD and APP_PASSWORD:
        st.session_state.auth_ok = True
        st.session_state.pop("pw_error", None)
    else:
        st.session_state.pw_error = "Wrong password 🫠"

# Pretty login screen
if not st.session_state.auth_ok:
    st.markdown("""
    <style>
      @font-face { font-family:"Comic Sans MS"; src: local("Comic Sans MS"); }

      .stApp { background:#dff7f7; } /* pastel aqua */

      .login-card{
        max-width: 640px; margin: 10vh auto; padding: 28px 30px;
        border-radius: 22px; border: 2px solid #a3d9ff;
        background:#ffffffcc; backdrop-filter: blur(6px);
        box-shadow: 0 12px 28px rgba(91,153,255,.25);
        font-family: "Comic Sans MS", cursive, sans-serif;
        text-align:center;
      }

      /* BIG centered pink title */
      .login-title{
        display:block;
        width: fit-content;
        margin: 0 auto 12px auto;
        padding: 12px 24px;
        border-radius:18px; border:2px solid #b98db0;
        background:#f8c9ea; color:#333;
        font-size: 36px; font-weight: 800;   /* << bigger */
        line-height:1.1;
      }

      .login-note{ color:#355c7d; font-size:16px; margin:6px 0 16px; }

      /* keep styles inside card only */
      .login-card .stTextInput { 
        max-width: 320px;  /* << shorter field */
        margin: 0 auto 10px auto;
      }
      .login-card .stTextInput > div > div > input{
        border-radius: 16px; border:2px solid #bfe1ff;
        background:#f9ffff;
        font-family: "Comic Sans MS", cursive, sans-serif;
        font-size: 24px;   /* << bigger password characters */
        height: 54px; padding: 6px 16px;
        letter-spacing: 0.08em;  /* cute, readable */
      }

      .login-card .stButton { display:flex; justify-content:center; }
      .login-card .stButton>button{
        font-family:"Comic Sans MS", cursive;
        border:none; border-radius:999px; padding:.7rem 1.4rem; font-weight:700;
        background: linear-gradient(135deg,#bfe1ff,#9fd2ff);
        box-shadow:0 8px 18px rgba(159,210,255,.45); color:#123;
      }
      .login-card .stButton>button:hover{ filter:brightness(1.05); }
    </style>

    <div class="login-card">
      <div class="login-title">User Story to Testcase Generator</div>
      <p class="login-note">🔒 Private app — please enter the password to continue.</p>
    """, unsafe_allow_html=True)

    st.text_input("Password", type="password", key="pw_input", label_visibility="collapsed")
    st.button("Let me in ✨", on_click=try_login)

    if st.session_state.get("pw_error"):
        st.error(st.session_state["pw_error"])

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# optional logout
if st.sidebar.button("🚪 Logout"):
    st.session_state.auth_ok = False
    st.experimental_rerun()
# --- end gate ---


# ======================= CSS (Comic Sans + fixed heights) =======================
st.markdown("""
<style>
html, body, [class*="css"] { font-family: "Comic Sans MS","Comic Sans",cursive !important; }

/* full aqua background */
.stApp { background: #ccf4f4 !important; }

/* title pill */
.mock-title {
  margin: 20px auto 26px auto; width: 520px;
  background: #f7d8ef; border: 3px solid #000; border-radius: 14px;
  text-align: center; font-weight: 800; font-size: 26px; padding: 10px 16px;
}

/* labels */
.mock-label { font-weight: 800; font-size: 20px; color: #000; margin: 12px 0 6px 40px; }

/* fixed widths so fields don't collapse */
.field-single, .field-multi { width: 900px; margin-left: 40px; }

/* cartoon rounded inputs (textarea-based to avoid clipping) */
.stTextArea textarea {
  background: #fff4c7 !important;
  border: 3px solid #000 !important;
  border-radius: 16px !important;
  color: #000 !important;
  font-size: 18px !important;
  padding: 12px 16px !important;
  box-shadow: none !important;
  line-height: 1.45 !important;
}

/* "single-line" textarea look for the User Story field */
.singleline textarea {
  min-height: 64px !important;
  max-height: 64px !important;
  resize: none !important;
  overflow: hidden !important;
  white-space: nowrap !important;   /* looks like a single line */
}

/* export button */
.export-wrap { margin: 28px 40px; }
.export-wrap .stButton > button {
  background: #e6f1a6; color:#000; border:3px solid #000;
  border-radius: 10px; font-weight:800; font-size: 20px; padding: 12px 24px;
}
.export-wrap .stButton > button:disabled { background:#e6e6e6; color:#777; border-color:#999; }

/* keep download button in same cute style */
.stDownloadButton > button {
  background: #ffffff; color:#000; border:3px solid #000;
  border-radius: 10px; font-weight:800; font-size: 18px; padding: 10px 20px;
}
</style>
""", unsafe_allow_html=True)

# --- UI ---
st.markdown('<div class="mock-title">Amazing User Story to Testcase Generator</div>', unsafe_allow_html=True)

# User Story (single line style; real single-line look via textarea to avoid clipping)
st.markdown('<div class="mock-label">Enter your User Story here</div>', unsafe_allow_html=True)
st.markdown('<div class="field-single singleline">', unsafe_allow_html=True)
user_story = st.text_area(
    "", key="us_one", label_visibility="hidden",
    placeholder="As a <role>, I want ..., so that ...",
    height=200  # keep this compact to look like a single line
)
st.markdown('</div>', unsafe_allow_html=True)

# Acceptance Criteria (big multi-line box)
st.markdown('<div class="mock-label">Enter the Acceptance Criteria (1 criteria per line)</div>', unsafe_allow_html=True)
st.markdown('<div class="field-multi">', unsafe_allow_html=True)
ac_text = st.text_area(
    "", key="ac_lines", label_visibility="hidden",
    placeholder="• Criterion 1\n• Criterion 2\n• Criterion 3",
    height=400   # nice and tall
)
st.markdown('</div>', unsafe_allow_html=True)

# ======================= OpenAI setup =======================
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY) if (API_KEY and OpenAI) else None

SYSTEM_PROMPT = """
You are a senior test engineer.
Return ONLY valid JSON (no markdown, no prose).
Schema:
{
  "test_cases":[
    {
      "id":"TC-1",
      "title":"string",
      "priority":"High|Medium|Low",
      "type":"Functional|Negative|Boundary|Security|Performance|Usability",
      "steps":[
        {"step":"concise action", "expected":"concise observable result"}
      ]
    }
  ]
}
Rules:
- Provide 3–6 focused test cases.
- Each test case MUST have at least 3 steps, each with 'step' and 'expected'.
- Be concise and testable. No Gherkin.
"""

def _json_from_text(txt: str):
    txt = txt.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```(json)?\\s*|\\s*```$", "", txt, flags=re.S)
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\\{.*\\}", txt, flags=re.S)
        if m: return json.loads(m.group(0))
        return {"test_cases":[]}

def generate_cases(story: str, ac_blob: str):
    """Return list of test case dicts; [] if no API or failure."""
    if not client or not story.strip():
        return []
    payload = {
        "story": story.strip(),
        "acceptance_criteria": [l.strip() for l in ac_blob.splitlines() if l.strip()]
    }
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini", temperature=0.2,
            messages=[{"role":"system","content":SYSTEM_PROMPT},
                      {"role":"user","content":json.dumps(payload, ensure_ascii=False)}]
        )
        data = _json_from_text(resp.choices[0].message.content)
        tcs = data.get("test_cases", [])
        # normalize steps structure
        fixed=[]
        for tc in tcs:
            steps=[]
            for s in tc.get("steps", []):
                if isinstance(s, dict):
                    steps.append({"step": s.get("step","").strip(), "expected": s.get("expected","").strip()})
                else:
                    steps.append({"step": str(s), "expected": ""})
            tc["steps"]=steps
            fixed.append(tc)
        return fixed
    except Exception:
        return []

# ======================= PDF builder (pretty Step/Action/Expected tables) =======================
def build_pdf(story_text: str, ac_blob: str, cases: list) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=40, bottomMargin=36)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=22)
    head  = ParagraphStyle("h", parent=styles["Heading2"], fontSize=14)
    body  = ParagraphStyle("b", parent=styles["Normal"], fontSize=11, leading=14)
    cell  = ParagraphStyle("cell", parent=styles["Normal"], fontSize=10, leading=13, wordWrap="CJK")

    flow = []
    flow.append(Paragraph(" User Story to Testcase Generator", title)); flow.append(Spacer(1, 10))

    flow.append(Paragraph("<b>User Story</b>", head))
    flow.append(Paragraph(story_text.strip() or "—", body)); flow.append(Spacer(1, 8))

    flow.append(Paragraph("<b>Acceptance Criteria</b>", head))
    lines = [l.strip() for l in ac_blob.splitlines() if l.strip()]
    if lines:
        flow.append(ListFlowable([ListItem(Paragraph(l, body), leftIndent=6) for l in lines],
                                 bulletType="bullet", leftPadding=12))
    else:
        flow.append(Paragraph("—", body))
    flow.append(Spacer(1, 12))

    if cases:
        flow.append(Paragraph("<b>Generated Test Design</b>", head)); flow.append(Spacer(1, 6))
        # Summary table
        trows = [["ID","Title","Priority","Type"]]
        for tc in cases:
            trows.append([Paragraph(tc.get("id",""), cell),
                          Paragraph(tc.get("title",""), cell),
                          Paragraph(tc.get("priority",""), cell),
                          Paragraph(tc.get("type",""), cell)])
        tbl = Table(trows, colWidths=[55, 300, 80, 80], repeatRows=1, splitByRow=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#9fd2ff")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("GRID",(0,0),(-1,-1),0.25,colors.grey),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
            ("FONTSIZE",(0,0),(-1,-1),9),
        ]))
        flow.append(tbl); flow.append(Spacer(1, 10))

        # One PRETTY table per test case: Step | Action | Expected Result
        for tc in cases:
            flow.append(Paragraph(f"<b>{tc.get('id','')}</b> — {tc.get('title','')}", styles["Heading3"]))
            steps = tc.get("steps", []) or []
            srows = [[Paragraph("Step", styles["Heading5"]),
                      Paragraph("Action", styles["Heading5"]),
                      Paragraph("Expected Result", styles["Heading5"])]]
            if steps:
                for i, s in enumerate(steps, start=1):
                    srows.append([Paragraph(str(i), cell),
                                  Paragraph(s.get("step",""), cell),
                                  Paragraph(s.get("expected",""), cell)])
            else:
                srows.append([Paragraph("—", cell), Paragraph("—", cell), Paragraph("—", cell)])

            # Wider Expected column, zebra rows, and page-splitting
            step_tbl = Table(srows, colWidths=[40, 230, 255], repeatRows=1, splitByRow=1)
            step_tbl.setStyle(TableStyle([
                ("GRID",(0,0),(-1,-1),0.3,colors.grey),
                ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#b8d7ff")),
                ("TEXTCOLOR",(0,0),(-1,0),colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("VALIGN",(0,0),(-1,-1),"TOP"),
                ("LEFTPADDING",(0,0),(-1,-1),6),
                ("RIGHTPADDING",(0,0),(-1,-1),6),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.whitesmoke, colors.HexColor("#eef7ff")]),
                ("FONTSIZE",(0,1),(-1,-1),10),
            ]))
            flow.append(step_tbl)
            flow.append(Spacer(1, 8))

    doc.build(flow)
    buf.seek(0); return buf.getvalue()

# ======================= Export =======================
pdf_ready = bool(user_story.strip() or ac_text.strip())
st.markdown('<div class="export-wrap">', unsafe_allow_html=True)

if st.button("Export to PDF!", disabled=not pdf_ready):
    st.info("📄 generating PDF… please be patient!! **this can take up to 2 minutes**. "
            "when it’s ready, a **download** button will appear below.")
    with st.spinner("creating test design…"):
        cases = generate_cases(user_story, ac_text)   # [] if no API key / blocked
        pdf_bytes = build_pdf(user_story, ac_text, cases)
        time.sleep(0.2)
    st.download_button("Download!", data=pdf_bytes, file_name="testcases.pdf",
                       mime="application/pdf", key="dl_pdf_btn")

st.markdown('</div>', unsafe_allow_html=True)


