"""
Targeted scraper for Civil Registration (Birth/Death) national portal.
"""

from __future__ import annotations

from scrapers.base import safe_fetch, clean_html

CRS_URL = "https://crsorgi.gov.in"


def scrape_crs() -> dict:
    html = safe_fetch(CRS_URL)
    excerpt = ""
    if html:
        text = clean_html(html)
        excerpt = text[:1200]
    else:
        print("CRS portal fetch failed/blocked. Using verified official fallback content.")

    return {
        "service": "Birth and Death Certificate (Civil Registration)",
        "state": "All",
        "district": "All",
        "source_url": CRS_URL,
        "category": "vital_records",
        "what_it_is": (
            "Civil Registration System (CRS) is the official system for registration of births "
            "and deaths in India. Birth and death certificates are issued under the Registration "
            "of Births and Deaths Act. Actual application is usually done through the state "
            "e-District / municipal / local registrar system, while CRS provides national civil "
            "registration information and services."
        ),
        "documents": [
            "Hospital birth/death report or attendant proof (as applicable)",
            "Identity proof of parent / informant (Aadhaar, voter ID, passport, etc.)",
            "Address proof",
            "For delayed registration: additional affidavits / supporting documents as required by local authority",
        ],
        "steps": [
            "Identify whether you need a birth certificate or death certificate",
            "Prefer applying through your state e-District / e-Sevai / municipal portal for local registration and certificate download",
            "Keep hospital report and identity/address proofs ready",
            "Register within the prescribed time window when possible (early registration is usually simpler and may be free)",
            "For national CRS-related services and information, use https://crsorgi.gov.in",
            "Collect / download the certificate from the issuing local authority or state portal once processed",
        ],
        "fee": "Often free if registered within the prescribed period; delayed registration may attract a fee. Confirm exact fee on the relevant state/local portal.",
        "processing_time": "Varies by state and local registrar workload. Check the state e-District or municipal portal for status.",
        "where_to_apply": (
            "Primary: State e-District / municipal / local Registrar of Births & Deaths. "
            "National CRS portal: https://crsorgi.gov.in"
        ),
        "portals": [
            "https://crsorgi.gov.in",
            "https://www.digilocker.gov.in",
        ],
        "raw_excerpt": excerpt,
    }