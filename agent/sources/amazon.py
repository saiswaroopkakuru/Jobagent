import requests
import re
from html import unescape
from typing import Dict, List


# ========== Amazon Jobs JSON (best-effort, unofficial) ==========

AMAZON_JOBS_JSON = "https://www.amazon.jobs/en/search.json"

def fetch_jobs_amazon(
    query: str = "",
    location_query: str = "",
    country: str = "United States",
    page_size: int = 100,
    max_pages: int = 3,
    sort: str = "recent",
) -> List[Dict]:
    """
    Uses the JSON endpoint behind amazon.jobs search UI. Not officially documented; may change.
    Reference (community): https://stackoverflow.com/a/49507722
    """
    out: List[Dict] = []
    for page in range(max_pages):
        offset = page * page_size
        params = {
            "base_query": query,
            "loc_query": location_query,
            "country": country,
            "result_limit": page_size,
            "offset": offset,
            "sort": sort,
        }
        data = _get_json(AMAZON_JOBS_JSON, params=params)
        jobs = data.get("jobs", []) or []
        if not jobs:
            break
        for j in jobs:
            title = j.get("title") or j.get("job_title") or ""
            # Build a location string if fields exist
            city = j.get("city") or ""
            state = j.get("state") or ""
            country_code = j.get("country") or ""
            location = ", ".join([v for v in [city, state, country_code] if v])
            path = j.get("job_path") or ""
            url = f"https://www.amazon.jobs{path}" if path else ""
            date_posted = j.get("posted_date") or j.get("listing_updated_time") or None
            # Amazon JSON often doesn't include full description here
            out.append(_normalize_job(
                title=title,
                company="Amazon",
                location=location,
                url=url,
                source="amazon_jobs",
                description="",
                date_posted=date_posted,
            ))
        # Stop if short page
        if len(jobs) < page_size:
            break
        time.sleep(0.2)
    return out