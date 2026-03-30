"""
scenario_upload.py
------------------
Scenario 1 — Upload Document
User uploads an existing R&D plan PDF. The AI extracts all content,
identifies gaps, fills them using GPT-4, scores the claim, and
generates a completed ATO-compliant PDF report.
"""

import os
import json
import re
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# ── 1. Extract raw text from uploaded PDF ──────────────────────────────────────

def extract_pdf_text(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n\n"
    return text.strip()


# ── 2. Parse structured data from raw text using GPT-4 ────────────────────────

EXTRACTION_SYSTEM = """You are an expert RDTI (R&D Tax Incentive) compliance consultant for the Australian Tax Office.
Your job is to extract structured information from an uploaded R&D project plan PDF.
Return ONLY a valid JSON object — no markdown, no explanation, no preamble.

The JSON must follow this exact structure:
{
  "project_title": "",
  "financial_year": "",
  "start_date": "",
  "end_date": "",
  "anzsic": "",
  "company_name": "",
  "abn": "",
  "contact_person": "",
  "budget": "",
  "project_objective": "",
  "record_keeping": "",
  "ip_beneficiary": "",
  "activities": [
    {
      "title": "",
      "type": "Core",
      "description": "",
      "hypothesis": "",
      "sources_investigated": "",
      "competent_professional": "",
      "experiments": "",
      "evaluation": "",
      "conclusions": "",
      "new_knowledge": "",
      "evidence": "",
      "supporting_activities": [
        {
          "title": "",
          "description": "",
          "linkage": "",
          "dominant_purpose": "",
          "evidence": ""
        }
      ]
    }
  ],
  "gaps": []
}

For any field that is missing, contains placeholder text like 'Add text here', or is incomplete,
set the value to an empty string "" and add the field path to the "gaps" array (e.g. "activities[0].hypothesis").
Extract EVERY activity (both core and supporting) found in the document."""


def extract_structured_data(raw_text: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": f"Extract structured data from this R&D plan:\n\n{raw_text[:12000]}"}
        ],
        temperature=0.1,
        max_tokens=4000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ── 3. Fill gaps using GPT-4 ───────────────────────────────────────────────────

GAP_FILL_SYSTEM = """You are an expert RDTI compliance consultant. You will be given:
1. The current R&D project plan data (JSON)
2. A list of fields that are empty or incomplete (gaps)

Your job is to generate ATO-compliant, professional content for each gap based on the context
available in the rest of the plan. Use proper RDTI language:
- "systematic progression of work"
- "technical uncertainty"
- "hypothesis-driven experimentation"
- "new knowledge"
- Capture failures and iterations
- Avoid vague language like "we improved" or "we built"

Return ONLY a valid JSON object mapping each gap path to its suggested content.
Example: {"activities[0].hypothesis": "We hypothesised that..."}"""


def fill_gaps(data: dict, gaps: list) -> dict:
    if not gaps:
        return {}
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": GAP_FILL_SYSTEM},
            {"role": "user", "content": f"Project data:\n{json.dumps(data, indent=2)[:6000]}\n\nGaps to fill:\n{json.dumps(gaps)}"}
        ],
        temperature=0.4,
        max_tokens=3000,
    )
    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


def apply_gap_fills(data: dict, fills: dict) -> dict:
    for path, value in fills.items():
        try:
            # Parse path like "activities[0].hypothesis"
            parts = re.split(r"\.|(?=\[)", path)
            obj = data
            for i, part in enumerate(parts[:-1]):
                if part.startswith("["):
                    idx = int(part[1:-1])
                    obj = obj[idx]
                else:
                    key = part.rstrip("]").split("[")[0]
                    if "[" in part:
                        idx = int(part.split("[")[1].rstrip("]"))
                        obj = obj[key][idx]
                    else:
                        obj = obj[key]
            last = parts[-1]
            if last.startswith("["):
                obj[int(last[1:-1])] = value
            else:
                obj[last] = value
        except Exception:
            pass
    return data


# ── 4. Score the claim ─────────────────────────────────────────────────────────

SCORING_SYSTEM = """You are an RDTI eligibility scorer. Evaluate the provided R&D project data
against the 7-category ATO scoring framework and return ONLY a JSON object:

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
}

Score strictly. Flag red flags: "we built a platform", "we improved performance", no failed experiments mentioned."""


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


# ── 5. Main pipeline ───────────────────────────────────────────────────────────

def process_uploaded_document(pdf_path: str, output_dir: str = "outputs") -> dict:
    """
    Full pipeline for uploaded document scenario.
    Returns dict with 'data' (structured project data) and 'pdf_path'.
    """
    print("Step 1: Extracting text from PDF...")
    raw_text = extract_pdf_text(pdf_path)

    print("Step 2: Parsing structured data with GPT-4...")
    data = extract_structured_data(raw_text)

    gaps = data.get("gaps", [])
    print(f"Step 3: Found {len(gaps)} gaps — filling with AI...")
    if gaps:
        fills = fill_gaps(data, gaps)
        data = apply_gap_fills(data, fills)

    print("Step 4: Scoring the RDTI claim...")
    scoring = score_claim(data)
    data["scoring"] = scoring

    print("Step 5: Generating PDF report...")
    from pdf_generator import generate_pdf
    os.makedirs(output_dir, exist_ok=True)
    safe_name = re.sub(r"[^\w\s-]", "", data.get("project_title", "report")).replace(" ", "_")
    safe_fy = re.sub(r"[^\w\s-]", "", data.get("financial_year", "FY")).replace(" ", "_")
    out_path = os.path.join(output_dir, f"RDTI_{safe_name}_{safe_fy}.pdf")
    generate_pdf(data, out_path)

    print(f"Done! Report saved to: {out_path}")
    return {"data": data, "pdf_path": out_path}


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else "sample.pdf"
    result = process_uploaded_document(pdf_path)
    print(f"Score: {result['data']['scoring']['total']}/100 — {result['data']['scoring']['outcome']}")
