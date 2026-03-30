# 🇦🇺 Australian R&D Tax Incentive (RDTI) Compliance Review Agent

An AI-powered tool that helps Australian businesses prepare, review, and score their **R&D Tax Incentive (RDTI)** project plans in compliance with ATO requirements. Built with OpenAI GPT-4, Streamlit, and ReportLab.

---

## 📋 Overview

The RDTI Compliance Review Agent automates the most time-consuming parts of preparing an R&D Tax Incentive claim. It supports two workflows:

- **Upload Document** — Upload an existing R&D plan PDF. The AI extracts all content, identifies gaps (placeholder sections, missing fields), fills them with ATO-compliant language, scores the claim, and generates a polished PDF report.
- **Fill In Manually** — A guided AI chat interview walks you through every required section step by step. The agent asks the right questions, prompts for specifics, and builds the report from your answers.

Both workflows produce a fully structured, ATO-compliant R&D project plan PDF with an RDTI eligibility score.

---

## ✨ Features

- 📤 **PDF ingestion** — Extracts and parses existing R&D plans using `pdfplumber`
- 🤖 **AI gap detection & filling** — Identifies placeholder text and incomplete sections, fills them using GPT-4 with proper RDTI language
- 💬 **Conversational interview** — 7-stage guided chat interview covering all required ATO fields
- 📊 **Pre-qualification scoring** — 100-point scoring engine across 7 ATO compliance categories
- 🚩 **Red flag detection** — Automatically flags disqualifying language and weak sections
- 📄 **PDF report generation** — Branded, multi-page ATO-compliant report with score breakdown, recommendations, and all activity sections
- 🖥️ **Streamlit UI** — Clean, professional web interface

---

## 🗂️ Project Structure

```
rdti_agent/
├── app.py                  # Streamlit frontend (main entry point)
├── scenario_upload.py      # Scenario 1: Upload & process existing PDF
├── scenario_manual.py      # Scenario 2: Chat interview session
├── utils/
│   ├── __init__.py
│   └── pdf_generator.py    # ReportLab PDF report builder
├── outputs/                # Generated PDF reports (git-ignored)
├── requirements.txt
├── .env                    # API keys (git-ignored)
├── .env.example            # Safe template for API keys
└── .gitignore
```

---

## ⚙️ Setup & Installation

### 1. Clone the repository

```bash
git clone https://github.com/sajjadUllah-sys/Australian-RD_TAX-AI.git
cd Australian-RD_TAX-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

Copy the example env file and add your OpenAI key:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder:

```
OPENAI_API_KEY=your_openai_api_key_here
```

> Get your API key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### 5. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

---

## 🚀 Usage

### Mode 1 — Upload Document

1. Select **Upload Document** on the home screen
2. Upload your existing R&D plan PDF
3. Toggle preferences (include recommendations, flag incomplete sections)
4. Click **Generate Report**
5. Review the eligibility score and download the PDF

### Mode 2 — Fill In Manually

1. Select **Fill In Manually** on the home screen
2. Answer the AI's questions through 7 interview stages:
   - Project Basics
   - Company Details
   - Project Overview
   - Core R&D Activities
   - Supporting Activities
   - Recordkeeping
   - Review & Confirm
3. Click **Generate PDF Report** when the interview is complete
4. Download your completed report

---

## 📊 Scoring Framework

The agent scores each claim out of 100 points across 7 ATO compliance categories:

| Category | Weight | Description |
|---|---|---|
| Technical Uncertainty | 25 pts | Core eligibility driver |
| Experimental Activities | 25 pts | Systematic experimentation required |
| New Knowledge Creation | 15 pts | Genuine R&D output |
| Baseline / State of Art | 10 pts | Why existing solutions were insufficient |
| Supporting Activities Linkage | 10 pts | Activities linked to core R&D |
| Evidence & Documentation | 10 pts | Audit defensibility |
| Exclusions Awareness | 5 pts | Avoids overclaiming |

**Eligibility thresholds:**

| Score | Outcome |
|---|---|
| 80 – 100 | ✅ Strong Eligible |
| 65 – 79 | 🔵 Likely Eligible |
| 50 – 64 | ⚠️ At Risk |
| < 50 | ❌ Unlikely Eligible |

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| [Streamlit](https://streamlit.io) | Web UI |
| [OpenAI GPT-4o](https://platform.openai.com) | AI extraction, gap filling, scoring, interview |
| [pdfplumber](https://github.com/jsvine/pdfplumber) | PDF text extraction |
| [ReportLab](https://www.reportlab.com) | PDF report generation |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Environment variable management |

---

## 📌 Requirements

- Python 3.9+
- OpenAI API key (GPT-4o access recommended)
- Internet connection for API calls

---

## 🔒 Security Notes

- Never commit your `.env` file — it is git-ignored by default
- Use `.env.example` as a safe template to share with collaborators
- Generated PDF reports in `outputs/` are also git-ignored

---

## 📄 License

This project is proprietary. All rights reserved.

---

## 👤 Author

**Sajjad Ullah**
- GitHub: [@sajjadUllah-sys](https://github.com/sajjadUllah-sys)
- Email: shafinsajjad07@gmail.com
