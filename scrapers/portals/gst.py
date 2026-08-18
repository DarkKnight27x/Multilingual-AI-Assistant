"""
Targeted scraper for GST registration guidance.
If the portal blocks bots (403), we still emit verified official guidance
and point users only to the official GST portal.
"""

from __future__ import annotations

from scrapers.base import safe_fetch, clean_html

GST_URL = "https://www.gst.gov.in"
GST_SERVICES_URL = "https://services.gst.gov.in"


def scrape_gst() -> dict:
    html = safe_fetch(GST_URL) or safe_fetch(GST_SERVICES_URL)
    excerpt = ""
    if html:
        text = clean_html(html)
        excerpt = text[:1200]
    else:
        print("GST portal blocked live fetch. Using verified official fallback content.")

    return {
        "service": "GST Registration",
        "state": "All",
        "district": "All",
        "source_url": GST_URL,
        "category": "business_trade",
        "what_it_is": (
            "GST Registration is the official process to obtain a Goods and Services Tax "
            "Identification Number (GSTIN) in India. Businesses register on the official GST "
            "portal when required by law (for example, when turnover crosses the threshold, "
            "or in cases such as interstate supply / e-commerce supply)."
        ),
        "documents": [
            "PAN of the business / proprietor",
            "Aadhaar of the authorised signatory",
            "Proof of constitution of business (as applicable)",
            "Proof of principal place of business (utility bill, rent agreement, ownership proof, etc.)",
            "Bank account proof / cancelled cheque",
            "Photograph of authorised signatory",
        ],
        "steps": [
            "Go to the official GST portal: https://www.gst.gov.in",
            "Open the registration service (New Registration)",
            "Fill business details, promoter/partner details and authorised signatory details",
            "Upload the required documents",
            "Complete authentication / OTP verification as required",
            "Track application status on the portal; on approval, GSTIN is issued",
        ],
        "fee": "Registration through the official GST portal is free. Avoid third-party websites that charge for the same service.",
        "processing_time": "Typically a few days after submission and verification. Check status on the official portal.",
        "where_to_apply": "Official GST portal only: https://www.gst.gov.in",
        "portals": [
            "https://www.gst.gov.in",
            "https://services.gst.gov.in",
        ],
        "raw_excerpt": excerpt,
    }