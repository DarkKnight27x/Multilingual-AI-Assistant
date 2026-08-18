"""
Targeted scraper for RTI Online guidance.
"""

from __future__ import annotations

from scrapers.base import safe_fetch, clean_html

RTI_URL = "https://rtionline.gov.in"


def scrape_rti() -> dict:
    html = safe_fetch(RTI_URL)
    excerpt = ""
    if html:
        text = clean_html(html)
        excerpt = text[:1200]
    else:
        print("RTI Online fetch failed/blocked. Using verified official fallback content.")

    return {
        "service": "RTI Application",
        "state": "All",
        "district": "All",
        "source_url": RTI_URL,
        "category": "grievances",
        "what_it_is": (
            "RTI (Right to Information) lets citizens request information from public authorities. "
            "For many Central Government public authorities, applications can be filed online through "
            "the RTI Online portal. Some state departments use their own state RTI portals."
        ),
        "documents": [
            "Applicant identity details",
            "Clear description of the information required",
            "Relevant period / office name if known",
            "Contact details for receiving the response",
            "Payment method for RTI fee where applicable",
        ],
        "steps": [
            "Go to the official portal: https://rtionline.gov.in",
            "Register / login if required by the portal",
            "Select the relevant Ministry/Department/Public Authority",
            "Draft a clear RTI request (specific and concise)",
            "Pay the prescribed fee if applicable and submit",
            "Note the registration number and track the status online",
        ],
        "fee": "A prescribed RTI application fee usually applies (commonly Rs 10 for many central applications). Fee exemptions may exist for some categories — confirm on the official portal before payment.",
        "processing_time": "As per RTI Act timelines (often up to 30 days in normal cases). Check portal status for updates.",
        "where_to_apply": "Central public authorities: https://rtionline.gov.in. For state authorities, use the relevant state RTI portal if available.",
        "portals": [
            "https://rtionline.gov.in",
            "https://pgportal.gov.in",
        ],
        "raw_excerpt": excerpt,
    }