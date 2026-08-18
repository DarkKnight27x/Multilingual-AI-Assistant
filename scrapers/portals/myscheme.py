"""
Targeted scraper for myScheme (scheme discovery portal).
"""

from __future__ import annotations

from scrapers.base import safe_fetch, clean_html

MYSCHEME_URL = "https://www.myscheme.gov.in"


def scrape_myscheme() -> dict:
    html = safe_fetch(MYSCHEME_URL)
    excerpt = ""
    if html:
        text = clean_html(html)
        excerpt = text[:1200]
    else:
        print("myScheme fetch failed/blocked. Using verified official fallback content.")

    return {
        "service": "Find Applicable Government Schemes (myScheme)",
        "state": "All",
        "district": "All",
        "source_url": MYSCHEME_URL,
        "category": "welfare_schemes",
        "what_it_is": (
            "myScheme is a national portal that helps citizens discover government schemes "
            "they may be eligible for, based on categories such as social welfare, education, "
            "agriculture, employment and more. It is a discovery and guidance platform; final "
            "application is usually done on the specific scheme’s official portal or department site."
        ),
        "documents": [
            "Identity proof (Aadhaar / other accepted ID)",
            "Address proof",
            "Income certificate / category certificate where scheme requires it",
            "Bank account details for DBT schemes",
            "Scheme-specific documents (vary by scheme)",
        ],
        "steps": [
            "Go to the official portal: https://www.myscheme.gov.in",
            "Browse or search schemes by category, ministry, or eligibility tags",
            "Open a scheme page and read eligibility, benefits and required documents",
            "Use the official application link provided for that scheme",
            "Apply on the respective department/portal and track status there",
        ],
        "fee": "Browsing myScheme is free. Individual schemes may have their own fee rules — check the specific scheme page.",
        "processing_time": "Depends on the selected scheme and its implementing department.",
        "where_to_apply": "Discover on https://www.myscheme.gov.in, then apply on the official scheme/department portal linked there.",
        "portals": [
            "https://www.myscheme.gov.in",
            "https://www.india.gov.in",
        ],
        "raw_excerpt": excerpt,
    }