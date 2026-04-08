"""
abn_lookup.py
-------------
ABN validation and ABR (Australian Business Register) lookup.

- validate_abn_format: checks 11-digit format + ATO weighting checksum
- lookup_abn: calls the ABR JSON endpoint (requires a free GUID)
- check_name_match: fuzzy compare ABR entity name vs user-entered name
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

ABR_GUID = os.getenv("ABR_GUID", "")

# ── ATO ABN checksum weights ──────────────────────────────────────────────────
# https://www.clearwater.com.au/code/abn
ABN_WEIGHTS = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]


def validate_abn_format(abn: str) -> dict:
    """
    Validate ABN format: must be exactly 11 digits and pass checksum.
    Returns {"valid": bool, "error": str | None}
    """
    cleaned = re.sub(r"\s+", "", abn)

    if not re.fullmatch(r"\d{11}", cleaned):
        return {
            "valid": False,
            "error": "ABN must be exactly 11 numerals.",
            "cleaned": cleaned,
        }

    # ATO checksum algorithm
    digits = [int(d) for d in cleaned]
    digits[0] -= 1  # subtract 1 from first digit
    total = sum(d * w for d, w in zip(digits, ABN_WEIGHTS))
    if total % 89 != 0:
        return {
            "valid": False,
            "error": "ABN checksum is invalid — please double-check the number.",
            "cleaned": cleaned,
        }

    return {"valid": True, "error": None, "cleaned": cleaned}


def lookup_abn(abn: str, guid: str = None) -> dict:
    """
    Look up an ABN via the ABR JSON API.
    Returns the parsed JSON response or an error dict.
    Requires a valid ABR GUID (free registration at
    https://abr.business.gov.au/Tools/WebServices).
    """
    guid = guid or ABR_GUID
    if not guid:
        return {
            "success": False,
            "error": "ABR_GUID not configured — skipping live ABN verification.",
        }

    cleaned = re.sub(r"\s+", "", abn)
    url = (
        f"https://abr.business.gov.au/json/AbnDetails.aspx"
        f"?abn={cleaned}&guid={guid}"
    )

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()

        # Response is JSONP: callback({...})  — strip the callback wrapper
        text = resp.text.strip()
        # Remove callback wrapper if present
        match = re.match(r"^[a-zA-Z_]\w*\((.*)\)\s*;?\s*$", text, re.DOTALL)
        if match:
            text = match.group(1)

        import json
        data = json.loads(text)

        if data.get("Message"):
            return {"success": False, "error": data["Message"], "data": data}

        return {
            "success": True,
            "entity_name": data.get("EntityName", ""),
            "abn_status": data.get("AbnStatus", ""),
            "entity_type": data.get("EntityTypeName", ""),
            "business_names": [
                bn.get("Value", "") if isinstance(bn, dict) else str(bn)
                for bn in data.get("BusinessName", [])
            ],
            "state": data.get("AddressState", ""),
            "postcode": data.get("AddressPostcode", ""),
            "data": data,
        }

    except requests.RequestException as e:
        return {"success": False, "error": f"ABR lookup failed: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error parsing ABR response: {str(e)}"}


def _normalise_name(name: str) -> str:
    """Strip common suffixes and normalise for comparison."""
    name = name.upper().strip()
    # Remove common entity suffixes
    for suffix in [
        "PTY LTD", "PTY. LTD.", "PTY LTD.", "PTY. LTD",
        "LIMITED", "LTD", "LTD.", "INC", "INC.",
        "PROPRIETARY", "CORPORATION", "CORP", "CORP.",
        "TRUST", "TRADING AS", "T/A", "ABN",
    ]:
        name = re.sub(r"\b" + re.escape(suffix) + r"\b", "", name)
    # Strip punctuation and extra whitespace
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def check_name_match(abr_entity_name: str, user_company_name: str) -> dict:
    """
    Compare ABR entity name against user-entered company name.
    Returns {"match": bool, "abr_name": str, "user_name": str, "message": str}
    """
    norm_abr = _normalise_name(abr_entity_name)
    norm_user = _normalise_name(user_company_name)

    if not norm_abr or not norm_user:
        return {
            "match": False,
            "abr_name": abr_entity_name,
            "user_name": user_company_name,
            "message": "Could not compare — one of the names is empty.",
        }

    # Exact match after normalisation
    if norm_abr == norm_user:
        return {
            "match": True,
            "abr_name": abr_entity_name,
            "user_name": user_company_name,
            "message": "✅ Company name matches ABR records.",
        }

    # Check if one contains the other
    if norm_abr in norm_user or norm_user in norm_abr:
        return {
            "match": True,
            "abr_name": abr_entity_name,
            "user_name": user_company_name,
            "message": "✅ Company name is a close match to ABR records.",
        }

    return {
        "match": False,
        "abr_name": abr_entity_name,
        "user_name": user_company_name,
        "message": (
            f"⚠️ Name mismatch: ABR shows '{abr_entity_name}' "
            f"but you entered '{user_company_name}'. "
            f"Please verify the company name and ABN."
        ),
    }


def validate_and_lookup(abn: str, company_name: str) -> dict:
    """
    Full validation pipeline: format check → ABR lookup → name cross-check.
    Returns a combined result dict.
    """
    # Step 1: Format validation
    fmt = validate_abn_format(abn)
    if not fmt["valid"]:
        return {
            "valid": False,
            "format_ok": False,
            "lookup_done": False,
            "name_match": None,
            "error": fmt["error"],
        }

    # Step 2: ABR lookup
    lookup = lookup_abn(fmt["cleaned"])
    if not lookup.get("success"):
        return {
            "valid": True,
            "format_ok": True,
            "lookup_done": False,
            "name_match": None,
            "warning": lookup.get("error", "ABR lookup not available."),
        }

    # Step 3: Name cross-check
    abr_name = lookup.get("entity_name", "")
    # Also check business names
    all_names = [abr_name] + lookup.get("business_names", [])
    best_match = None
    for name in all_names:
        if name:
            result = check_name_match(name, company_name)
            if result["match"]:
                best_match = result
                break

    if best_match is None and abr_name:
        best_match = check_name_match(abr_name, company_name)

    return {
        "valid": True,
        "format_ok": True,
        "lookup_done": True,
        "abn_status": lookup.get("abn_status", ""),
        "entity_name": abr_name,
        "entity_type": lookup.get("entity_type", ""),
        "name_match": best_match,
    }
