"""
Official government portal map.

After category classification, every answer can cite the correct
.gov.in sources for that service family + state.
"""

from typing import Optional

PORTAL_MAP = {
    "vital_records": {
        "All": [
            "https://crsorgi.gov.in",
            "https://www.digilocker.gov.in",
        ],
        "Tamil Nadu": [
            "https://tnesevai.tn.gov.in",
            "https://crsorgi.gov.in",
        ],
        "Maharashtra": [
            "https://aaplesarkar.mahaonline.gov.in",
            "https://crsorgi.gov.in",
        ],
        "Kerala": [
            "https://edistrict.kerala.gov.in",
            "https://crsorgi.gov.in",
        ],
        "Gujarat": [
            "https://www.digitalgujarat.gov.in",
            "https://crsorgi.gov.in",
        ],
    },
    "property_inheritance": {
        "All": [
            "https://www.india.gov.in",
        ],
        "Tamil Nadu": ["https://tnesevai.tn.gov.in"],
        "Maharashtra": ["https://aaplesarkar.mahaonline.gov.in"],
        "Kerala": ["https://edistrict.kerala.gov.in"],
        "Gujarat": ["https://www.digitalgujarat.gov.in"],
    },
    "income_caste_domicile": {
        "All": [
            "https://www.india.gov.in",
        ],
        "Tamil Nadu": ["https://tnesevai.tn.gov.in"],
        "Maharashtra": ["https://aaplesarkar.mahaonline.gov.in"],
        "Kerala": ["https://edistrict.kerala.gov.in"],
        "Gujarat": ["https://www.digitalgujarat.gov.in"],
    },
    "business_trade": {
        "All": [
            "https://udyamregistration.gov.in",
            "https://www.gst.gov.in",
        ],
        "Tamil Nadu": [
            "https://udyamregistration.gov.in",
            "https://www.gst.gov.in",
            "https://tnesevai.tn.gov.in",
        ],
        "Maharashtra": [
            "https://udyamregistration.gov.in",
            "https://www.gst.gov.in",
            "https://aaplesarkar.mahaonline.gov.in",
        ],
        "Kerala": [
            "https://udyamregistration.gov.in",
            "https://www.gst.gov.in",
            "https://edistrict.kerala.gov.in",
        ],
        "Gujarat": [
            "https://udyamregistration.gov.in",
            "https://www.gst.gov.in",
            "https://www.digitalgujarat.gov.in",
        ],
    },
    "welfare_schemes": {
        "All": [
            "https://www.myscheme.gov.in",
            "https://nfsa.gov.in",
            "https://www.swavlambancard.gov.in",
        ],
    },
    "grievances": {
        "All": [
            "https://rtionline.gov.in",
            "https://pgportal.gov.in",
            "https://consumerhelpline.gov.in",
            "https://edaakhil.nic.in",
        ],
    },
}


def get_official_portals(
    category: Optional[str],
    state: Optional[str] = None,
) -> list[str]:
    """
    Return official portals for a category + optional state.
    State-specific links come first; central links are always included.
    """
    if not category or category not in PORTAL_MAP:
        return ["https://www.india.gov.in"]

    cat_map = PORTAL_MAP[category]
    portals: list[str] = []

    if state and state in cat_map:
        portals.extend(cat_map[state])

    for url in cat_map.get("All", []):
        if url not in portals:
            portals.append(url)

    return portals or ["https://www.india.gov.in"]