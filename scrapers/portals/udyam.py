"""
Targeted scraper for Udyam Registration (official MSME portal).
"""

from __future__ import annotations

from scrapers.base import fetch, clean_html

UDYAM_URL = "https://udyamregistration.gov.in"


def scrape_udyam() -> dict:
    """
    Fetch the official Udyam page and return structured fields.
    For MVP we combine page text with known stable official facts.
    Never invent fees/process beyond official known procedure.
    """
    html = fetch(UDYAM_URL)
    text = clean_html(html)

    # Keep a short excerpt for debugging/traceability
    excerpt = text[:1200]

    return {
        "service": "Udyam Registration",
        "state": "All",
        "district": "All",
        "source_url": UDYAM_URL,
        "category": "business_trade",
        "what_it_is": (
            "Udyam Registration is the official registration for Micro, Small and "
            "Medium Enterprises (MSMEs) in India. It replaces the earlier Udyog "
            "Aadhaar system and is used to access MSME benefits, priority lending, "
            "subsidies and government tender preferences."
        ),
        "documents": [
            "Aadhaar number of the proprietor / managing partner / karta",
            "PAN of the business (as applicable)",
            "Bank account details",
            "Basic business activity details (NIC code)",
        ],
        "steps": [
            "Go to the official portal: https://udyamregistration.gov.in",
            "Enter Aadhaar / organisation details as required and verify with OTP",
            "Fill business PAN, bank details and activity (NIC code)",
            "Submit the form (paperless self-declaration; no document upload needed for basic registration)",
            "On successful submission, Udyam Registration Certificate/Number is generated",
        ],
        "fee": "Free on the official portal. Beware of third-party sites that charge fees.",
        "processing_time": "Usually immediate after successful online submission.",
        "where_to_apply": "Official portal only: https://udyamregistration.gov.in",
        "portals": [UDYAM_URL],
        "raw_excerpt": excerpt,  # optional, not written into final markdown unless you want
    }