"""
Convert structured scrape data into the markdown format
used by data/knowledge_base/ (front-matter + sections).
"""

from __future__ import annotations

from datetime import date
from typing import Any


def to_markdown(data: dict[str, Any]) -> str:
    docs = "\n".join(f"- {d}" for d in data.get("documents", []) or [])
    steps = "\n".join(
        f"{i}. {s}" for i, s in enumerate(data.get("steps", []) or [], 1)
    )
    portals = "\n".join(f"- {p}" for p in data.get("portals", []) or [])

    return f"""---
service: {data.get("service", "Unknown")}
state: {data.get("state", "All")}
district: {data.get("district", "All")}
source_url: {data.get("source_url", "")}
category: {data.get("category", "business_trade")}
last_crawled: {date.today().isoformat()}
---

## What it is
{data.get("what_it_is", "").strip()}

## Documents typically required
{docs}

## General process
{steps}

## Fee
{data.get("fee", "Check official portal")}

## Processing time
{data.get("processing_time", "Varies — check official portal")}

## Where to apply
{data.get("where_to_apply", "Official portal only")}

## Official portals
{portals}
"""