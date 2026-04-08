"""
anzsic_mapping.py
-----------------
Maps human-readable industry names to ANZSIC Division codes.
Users pick from the friendly names; the code is stored internally
for ATO reporting.
"""

ANZSIC_INDUSTRIES = {
    "Agriculture, Forestry and Fishing": "A",
    "Mining": "B",
    "Manufacturing": "C",
    "Electricity, Gas, Water and Waste Services": "D",
    "Construction": "E",
    "Wholesale Trade": "F",
    "Retail Trade": "G",
    "Accommodation and Food Services": "H",
    "Transport, Postal and Warehousing": "I",
    "Information Media and Telecommunications": "J",
    "Financial and Insurance Services": "K",
    "Rental, Hiring and Real Estate Services": "L",
    "Professional, Scientific and Technical Services": "M",
    "Administrative and Support Services": "N",
    "Public Administration and Safety": "O",
    "Education and Training": "P",
    "Health Care and Social Assistance": "Q",
    "Arts and Recreation Services": "R",
    "Other Services": "S",
}

# Reverse lookup: code -> name
ANZSIC_CODE_TO_NAME = {v: k for k, v in ANZSIC_INDUSTRIES.items()}

# Sorted list for dropdowns
INDUSTRY_OPTIONS = sorted(ANZSIC_INDUSTRIES.keys())


def industry_to_anzsic(industry_name: str) -> str:
    """Return ANZSIC division code for a given industry name, or '' if not found."""
    return ANZSIC_INDUSTRIES.get(industry_name, "")


def format_industry_display(industry_name: str) -> str:
    """Return display string like 'Manufacturing (C)' for PDF/reports."""
    code = industry_to_anzsic(industry_name)
    if code:
        return f"{industry_name} ({code})"
    return industry_name
