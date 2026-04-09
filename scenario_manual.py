"""
scenario_manual.py
------------------
Scenario 2 — Fill In Manually (Chat Interview)
The AI conducts a structured, conversational interview to collect
all required R&D project data, then scores and generates the PDF.

Changes:
- Company details collected FIRST (before project basics)
- New/continuing project toggle after company info
- Financial year & industry pre-populated via UI dropdowns (not asked by AI)
- Continuing projects skip to 4 update fields with char limits
- Stronger one-question-at-a-time sequencing in all prompts
"""

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── Interview stages ───────────────────────────────────────────────────────────

# Full flow for NEW projects
INTERVIEW_STAGES_NEW = [
    "company_details",
    "project_type",
    "project_basics",
    "project_overview",
    "core_activities",
    "supporting_activities",
    "recordkeeping",
    "review_and_score",
]

# Shortened flow for CONTINUING projects
INTERVIEW_STAGES_CONTINUING = [
    "company_details",
    "project_type",
    "continuing_updates",
    "review_and_score",
]

# Default — starts as the full list; gets swapped if user picks "continuing"
INTERVIEW_STAGES = INTERVIEW_STAGES_NEW

# Stage labels for progress display (new project)
STAGE_LABELS_NEW = [
    "Company Details", "Project Type", "Project Basics", "Project Overview",
    "Core Activities", "Supporting Activities", "Recordkeeping", "Review",
]

STAGE_LABELS_CONTINUING = [
    "Company Details", "Project Type", "Annual Updates", "Review",
]


# ── Prompts ────────────────────────────────────────────────────────────────────

STAGE_PROMPTS = {
    "company_details": """You are collecting company details for an Australian RDTI (R&D Tax Incentive) claim.
The company legal name has ALREADY been provided by the user via a form field — it is stored in the collected data as "company_name". Do NOT ask for it again.

Ask for these remaining details ONE AT A TIME — ask a single question, wait for the answer, then ask the next:
1. ABN (Australian Business Number — must be exactly 11 digits)
2. Contact person name
3. Contact email address

IMPORTANT RULES:
- Do NOT ask for the company name — it is already known.
- Ask ONE question at a time. Do NOT bundle questions.
- If the user provides an ABN that is not exactly 11 digits, politely ask them to re-enter it.
- When you have all 3 remaining items, say [STAGE_COMPLETE] and summarise as JSON in a <data> block like:
  <data>{"abn": "...", "contact_person": "...", "contact_email": "..."}</data>""",

    "project_type": """You are determining whether this is a new or continuing R&D project for an RDTI claim.

Ask the user: "Is this a new R&D project, or are you providing annual updates for a continuing project?"

Wait for their answer. Classify their response as either "new" or "continuing".

When you have their answer, say [STAGE_COMPLETE] and output:
<data>{"project_type": "new"}</data>
or
<data>{"project_type": "continuing"}</data>""",

    "project_basics": """You are collecting basic project information for an Australian RDTI claim.
The financial year and industry have already been selected by the user via dropdowns — do NOT ask for them again.

Ask the user for these details ONE AT A TIME:
1. Project title
2. Project start date
3. Project end date
4. Budgeted R&D spend

IMPORTANT RULES:
- Ask ONE question at a time. Do NOT bundle questions together.
- Wait for each answer before asking the next question.
- When you have all items, say exactly: [STAGE_COMPLETE]
  and summarise what was collected as JSON in a <data> block like:
  <data>{"project_title": "...", "start_date": "...", "end_date": "...", "budget": "..."}</data>""",

    "project_overview": """You are collecting the project overview for an RDTI claim.
Ask for these details ONE AT A TIME — do NOT bundle questions:
1. Project objective — what problem does it solve? What are the specific measurable targets?
2. Record keeping — what documentation does the company keep? (experiment logs, design docs, test results, etc.)
3. IP / Know-how beneficiary — who owns the IP? Who controls and funds the R&D?

IMPORTANT RULES:
- Ask ONE question at a time. Wait for each answer before asking the next.
- Use ATO-compliant language. Prompt for specifics: quantified targets, field conditions, technical constraints.
- When complete, say [STAGE_COMPLETE] and summarise as JSON in a <data> block.""",

    "core_activities": """You are collecting CORE R&D activity details for an RDTI claim.
For each core activity, you must collect ALL of these fields — ask them ONE AT A TIME:
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

CRITICAL RULES:
- Ask ONLY ONE question at a time. Never bundle multiple questions.
- Wait for the user's response before asking the next question.
- Use probing follow-ups when answers are vague:
  * "What specifically was unknown at the start?"
  * "What failed, and what did you learn from that failure?"
  * "How did you measure success?"
  * "Would a competent engineer have known this without experimenting?"
- After completing one activity, ask: "Do you have any more core R&D activities to add?"
- When the user indicates no more core activities, say [STAGE_COMPLETE] and output all activities as JSON:
  <data>{"activities": [{"title": "", "type": "Core", "hypothesis": "", ...}]}</data>""",

    "supporting_activities": """You are collecting SUPPORTING R&D activity details.
For each supporting activity, collect these details ONE AT A TIME:
1. Title and which core activity it supports
2. Description of the activity
3. How it directly supported the core R&D (the link must be explicit)
4. Dominant purpose — was the dominant purpose to support core R&D?
5. Did it produce goods or services? (yes/no + explanation)
6. Evidence kept

IMPORTANT RULES:
- Ask ONE question at a time. Wait for each answer before continuing.
- When done, say [STAGE_COMPLETE] and summarise as JSON in a <data> block:
  <data>{"supporting_activities": [{"title": "", "linkage": "", ...}]}</data>""",

    "recordkeeping": """You are finalising the RDTI claim record-keeping section.
Ask about these topics ONE AT A TIME:
1. Types of evidence kept (experiment logs, test results, version control, photos, meeting notes, invoices)
2. Confirm who bears the financial burden of R&D
3. Confirm who controls the direction of R&D
4. Any overseas work or Research Service Provider involvement?

IMPORTANT RULES:
- Ask ONE question at a time. Do NOT bundle questions.
- When done, say [STAGE_COMPLETE] and summarise as JSON in a <data> block.""",

    "continuing_updates": """You are collecting annual update information for a CONTINUING R&D project for an RDTI claim.
The financial year has already been selected by the user.

You need to collect FOUR pieces of information, ONE AT A TIME.
Each answer has a minimum and maximum character count — inform the user of the limits.

Ask these questions ONE AT A TIME in this exact order:

1. "What experiment/s were conducted in the current financial year and how did they test the hypothesis?"
   (Minimum 650 characters, maximum 4000 characters)

2. "How did you evaluate or plan to evaluate the results from those experiment/s?"
   (Minimum 530 characters, maximum 4000 characters)

3. "Describe the conclusions you've reached from the experiment/s."
   (Minimum 340 characters, maximum 4000 characters)

4. "What is the New Knowledge generated?"
   (Minimum 600 characters, maximum 4000 characters)

CRITICAL RULES:
- Ask ONLY ONE question at a time. Never combine questions.
- After each answer, count the characters and tell the user the count.
- If the answer is below the minimum, ask the user to expand their response with more detail.
- If the answer exceeds the maximum, ask the user to shorten it.
- Only move to the next question when the current answer meets the character requirements.
- When all 4 questions are answered with valid lengths, say [STAGE_COMPLETE] and output:
  <data>{"continuing_experiments": "...", "continuing_evaluation": "...", "continuing_conclusions": "...", "continuing_new_knowledge": "..."}</data>""",

    "review_and_score": """You are reviewing the complete RDTI claim before final report generation.
Summarise everything collected so far for the user. Then:
1. Identify any remaining weak sections
2. Ask if the user wants to strengthen any answers
3. Confirm readiness to generate the PDF

When the user confirms, say [STAGE_COMPLETE] and output: <data>{"ready": true}</data>""",
}


# Character limits for continuing project fields
CONTINUING_CHAR_LIMITS = {
    "continuing_experiments":   {"min": 650, "max": 4000},
    "continuing_evaluation":    {"min": 530, "max": 4000},
    "continuing_conclusions":   {"min": 340, "max": 4000},
    "continuing_new_knowledge": {"min": 600, "max": 4000},
}


# ── Chat session management ────────────────────────────────────────────────────

class RDTIInterviewSession:
    def __init__(self):
        self.stage_index = 0
        self.collected_data = {}
        self.history = []
        self.stage_complete = False
        self.interview_complete = False
        self.project_type = None  # "new" or "continuing"
        self._stages = list(INTERVIEW_STAGES_NEW)  # mutable copy

    @property
    def stages(self):
        return self._stages

    @property
    def current_stage(self):
        if self.stage_index < len(self._stages):
            return self._stages[self.stage_index]
        return None

    def get_stage_labels(self):
        if self.project_type == "continuing":
            return STAGE_LABELS_CONTINUING
        return STAGE_LABELS_NEW

    def switch_to_continuing(self):
        """Switch to the shortened continuing-project flow."""
        self.project_type = "continuing"
        self._stages = list(INTERVIEW_STAGES_CONTINUING)
        # We're currently at project_type (index 1), so stage_index stays at 1
        # The next stage_index increment will move to continuing_updates (index 2)

    def switch_to_new(self):
        """Confirm new-project flow (already the default)."""
        self.project_type = "new"
        self._stages = list(INTERVIEW_STAGES_NEW)

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

            # Handle project_type stage — switch flow if continuing
            if self.current_stage == "project_type":
                pt = self.collected_data.get("project_type", "new").lower().strip()
                if pt == "continuing":
                    self.switch_to_continuing()
                else:
                    self.switch_to_new()

            self.stage_index += 1
            self.history = []  # Fresh history for next stage
            if self.stage_index >= len(self._stages):
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

    def to_dict(self) -> dict:
        """Serialise session state for localStorage persistence."""
        return {
            "stage_index": self.stage_index,
            "collected_data": self.collected_data,
            "history": self.history,
            "stage_complete": self.stage_complete,
            "interview_complete": self.interview_complete,
            "project_type": self.project_type,
            "stages": self._stages,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RDTIInterviewSession":
        """Restore session state from a serialised dict."""
        session = cls()
        session.stage_index = d.get("stage_index", 0)
        session.collected_data = d.get("collected_data", {})
        session.history = d.get("history", [])
        session.stage_complete = d.get("stage_complete", False)
        session.interview_complete = d.get("interview_complete", False)
        session.project_type = d.get("project_type", None)
        session._stages = d.get("stages", list(INTERVIEW_STAGES_NEW))
        return session


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
