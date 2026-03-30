"""
scenario_manual.py
------------------
Scenario 2 — Fill In Manually (Chat Interview)
The AI conducts a structured, conversational interview to collect
all required R&D project data, then scores and generates the PDF.
"""

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Interview stages ───────────────────────────────────────────────────────────

INTERVIEW_STAGES = [
    "project_basics",
    "company_details",
    "project_overview",
    "core_activities",
    "supporting_activities",
    "recordkeeping",
    "review_and_score",
]

STAGE_PROMPTS = {
    "project_basics": """You are collecting basic project information for an Australian RDTI (R&D Tax Incentive) claim.
Ask the user for:
1. Project title
2. Financial year (e.g. FY 2024-25)
3. Project start date and end date
4. Industry / ANZSIC class
5. Budgeted R&D spend

Ask these naturally in conversation — one or two at a time. When you have all of them, say exactly: [STAGE_COMPLETE]
and summarise what was collected as JSON in a <data> block like: <data>{"project_title": "..."}</data>""",

    "company_details": """You are collecting company details for an RDTI claim.
Ask for:
1. Company legal name
2. ABN
3. Contact person name
4. Contact email address

Ask naturally. When complete, say [STAGE_COMPLETE] and summarise as JSON in a <data> block.""",

    "project_overview": """You are collecting the project overview for an RDTI claim.
Ask for:
1. Project objective — what problem does it solve? What are the specific measurable targets?
2. Record keeping — what documentation does the company keep? (experiment logs, design docs, test results, etc.)
3. IP / Know-how beneficiary — who owns the IP? Who controls and funds the R&D?

Use ATO-compliant language. Prompt for specifics: quantified targets, field conditions, technical constraints.
When complete, say [STAGE_COMPLETE] and summarise as JSON in a <data> block.""",

    "core_activities": """You are collecting CORE R&D activity details for an RDTI claim.
For each core activity, you must collect:
1. Activity title and date range
2. Description of what was done
3. Hypothesis — what did you believe you could achieve?
4. Why the outcome could not be known in advance (technical uncertainty)
5. Why a competent professional couldn't have determined the outcome
6. Sources investigated (literature, patents, experts, competitors)
7. Experiments conducted — step by step
8. How results were evaluated
9. Conclusions reached (including failures and what was learned)
10. New knowledge generated

Ask one topic at a time. Use probing follow-ups:
- "What specifically was unknown at the start?"
- "What failed, and what did you learn from that failure?"
- "How did you measure success?"
- "Would a competent engineer have known this without experimenting?"

When the user indicates no more core activities, say [STAGE_COMPLETE] and output all activities as JSON in a <data> block:
<data>{"activities": [{"title": "", "type": "Core", "hypothesis": "", ...}]}</data>""",

    "supporting_activities": """You are collecting SUPPORTING R&D activity details.
For each supporting activity, collect:
1. Title and which core activity it supports
2. Description of the activity
3. How it directly supported the core R&D (the link must be explicit)
4. Dominant purpose — was the dominant purpose to support core R&D?
5. Did it produce goods or services? (yes/no + explanation)
6. Evidence kept

When done, say [STAGE_COMPLETE] and summarise as JSON in a <data> block:
<data>{"supporting_activities": [{"title": "", "linkage": "", ...}]}</data>""",

    "recordkeeping": """You are finalising the RDTI claim record-keeping section.
Ask about:
1. Types of evidence kept (experiment logs, test results, version control, photos, meeting notes, invoices)
2. Confirm who bears the financial burden of R&D
3. Confirm who controls the direction of R&D
4. Any overseas work or Research Service Provider involvement?

When done, say [STAGE_COMPLETE] and summarise as JSON in a <data> block.""",

    "review_and_score": """You are reviewing the complete RDTI claim before final report generation.
Summarise everything collected so far for the user. Then:
1. Identify any remaining weak sections
2. Ask if the user wants to strengthen any answers
3. Confirm readiness to generate the PDF

When the user confirms, say [STAGE_COMPLETE] and output: <data>{"ready": true}</data>"""
}


# ── Chat session management ────────────────────────────────────────────────────

class RDTIInterviewSession:
    def __init__(self):
        self.stage_index = 0
        self.collected_data = {}
        self.history = []
        self.stage_complete = False
        self.interview_complete = False

    @property
    def current_stage(self):
        if self.stage_index < len(INTERVIEW_STAGES):
            return INTERVIEW_STAGES[self.stage_index]
        return None

    def get_system_prompt(self):
        stage = self.current_stage
        base = STAGE_PROMPTS.get(stage, "")
        context = ""
        if self.collected_data:
            context = f"\n\nData collected so far:\n{json.dumps(self.collected_data, indent=2)[:2000]}"
        return base + context

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": self.get_system_prompt()}]
        messages += self.history[-20:]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.5,
            max_tokens=800,
        )

        assistant_msg = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": assistant_msg})

        # Check for stage completion
        if "[STAGE_COMPLETE]" in assistant_msg:
            self._extract_and_merge_data(assistant_msg)
            self.stage_index += 1
            self.history = []  # Fresh history for next stage
            if self.stage_index >= len(INTERVIEW_STAGES):
                self.interview_complete = True

        return assistant_msg

    def _extract_and_merge_data(self, message: str):
        match = re.search(r"<data>(.*?)</data>", message, re.DOTALL)
        if match:
            try:
                chunk = json.loads(match.group(1).strip())
                self._deep_merge(self.collected_data, chunk)
            except json.JSONDecodeError:
                pass

    def _deep_merge(self, base: dict, update: dict):
        for key, value in update.items():
            if key == "activities" and isinstance(value, list):
                existing = base.get("activities", [])
                for act in value:
                    matching = next((a for a in existing if a.get("title") == act.get("title")), None)
                    if matching:
                        matching.update(act)
                    else:
                        existing.append(act)
                base["activities"] = existing
            elif key == "supporting_activities" and isinstance(value, list):
                activities = base.get("activities", [])
                for sub in value:
                    core_title = sub.get("core_activity", "")
                    parent = next((a for a in activities if core_title.lower() in a.get("title", "").lower()), None)
                    if parent:
                        subs = parent.get("supporting_activities", [])
                        subs.append(sub)
                        parent["supporting_activities"] = subs
                    else:
                        base.setdefault("orphan_supporting", []).append(sub)
            elif isinstance(value, dict) and isinstance(base.get(key), dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def get_opening_message(self) -> str:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": "START_INTERVIEW"}
            ],
            temperature=0.5,
            max_tokens=400,
        )
        msg = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": msg})
        return msg


# ── Score and generate report ──────────────────────────────────────────────────

SCORING_SYSTEM = """You are an RDTI eligibility scorer. Evaluate the provided R&D project data
against the 7-category ATO scoring framework. Return ONLY a JSON object:

{
  "total": 0,
  "outcome": "Strong Eligible | Likely Eligible | At Risk | Unlikely Eligible",
  "breakdown": [
    {"category": "Technical Uncertainty", "score": 0, "max": 25},
    {"category": "Experimental Activities", "score": 0, "max": 25},
    {"category": "New Knowledge Creation", "score": 0, "max": 15},
    {"category": "Baseline / State of Art", "score": 0, "max": 10},
    {"category": "Supporting Activities Linkage", "score": 0, "max": 10},
    {"category": "Evidence & Documentation", "score": 0, "max": 10},
    {"category": "Exclusions Awareness", "score": 0, "max": 5}
  ],
  "gaps": ["..."],
  "recommendations": ["..."]
}"""


def score_claim(data: dict) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SCORING_SYSTEM},
            {"role": "user", "content": f"Score this RDTI claim:\n{json.dumps(data, indent=2)[:8000]}"}
        ],
        temperature=0.1,
        max_tokens=1000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def finalise_report(session: RDTIInterviewSession, output_dir: str = "outputs") -> dict:
    data = session.collected_data
    scoring = score_claim(data)
    data["scoring"] = scoring

    from pdf_generator import generate_pdf
    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r"[^\w\s-]", "", data.get("project_title", "report")).replace(" ", "_")
    safe_fy = re.sub(r"[^\w\s-]", "", data.get("financial_year", "FY")).replace(" ", "_")
    out_path = os.path.join(output_dir, f"RDTI_{safe_name}_{safe_fy}.pdf")
    generate_pdf(data, out_path)
    return {"data": data, "pdf_path": out_path}
