import requests
import time
import re
from html import unescape
from datetime import datetime
from typing import Dict, List, Optional

AMAZON_JOBS_JSON = "https://www.amazon.jobs/en/search.json"

# Reuse one session + set a reasonable UA so we get JSON reliably
_SESSION = requests.Session()
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.amazon.jobs/en/search",
}


def _get_json(url: str, params: Dict, tries: int = 3, backoff: float = 0.6) -> Dict:
    """
    Thin wrapper around requests to fetch JSON with simple retry and backoff.
    Returns {} on final failure.
    """
    for attempt in range(tries):
        try:
            resp = _SESSION.get(url, params=params, headers=_HEADERS, timeout=15)
            # Backoff on 429
            if resp.status_code == 429 and attempt < tries - 1:
                time.sleep(backoff)
                backoff *= 2
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == tries - 1:
                return {}
            time.sleep(backoff)
            backoff *= 2
    return {}


def _clean_html(s: str) -> str:
    if not s:
        return ""
    # Remove tags, unescape entities, collapse whitespace
    txt = re.sub(r"<[^>]+>", " ", s)
    txt = unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _to_iso_date(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    # Example: "September 8, 2025"
    try:
        return datetime.strptime(s, "%B %d, %Y").date().isoformat()
    except Exception:
        return None


def _normalize_job(
    title: str,
    company: str,
    location: str,
    url: str,
    source: str,
    description: str,
    date_posted: Optional[str],
) -> Dict:
    return {
        "title": title,
        "company": company,
        "location": location,
        "url": url,
        "source": source,
        "description": description,
        "date_posted": date_posted,
    }


def fetch_jobs_amazon(
    query: str = "",
    location_query: str = "",
    country: str = "USA",         # Amazon JSON expects country codes like "USA"
    page_size: int = 100,
    max_pages: int = 3,
    sort: str = "recent",         # "recent" or "relevant"
) -> List[Dict]:
    """
    Best-effort fetch using the JSON behind amazon.jobs search UI (unofficial; may change).
    Fields observed in the JSON include: title, city, state, country_code, job_path, posted_date, description.
    """
    out: List[Dict] = []

    for page in range(max_pages):
        offset = page * page_size
        params = {
            "base_query": query,
            "loc_query": location_query,
            "country": country,           # e.g., "USA"
            "result_limit": page_size,    # page size
            "offset": offset,
            "sort": sort,                 # "recent" or "relevant"
        }

        data = _get_json(AMAZON_JOBS_JSON, params=params)
        if not isinstance(data, dict):
            break

        jobs = data.get("jobs") or []
        if not jobs:
            break

        total_hits = data.get("hits", 0)

        for j in jobs:
            title = j.get("title") or j.get("job_title") or ""
            # Prefer normalized strings where available
            city = (j.get("city") or "").strip()
            state = (j.get("state") or "").strip()
            country_code = (j.get("country_code") or j.get("country") or "").strip()

            # If Amazon already gives a normalized_location, use it; else build one
            location = j.get("normalized_location") or ", ".join(
                [v for v in [city, state, country_code] if v]
            )

            path = j.get("job_path") or ""
            url = f"https://www.amazon.jobs{path}" if path else ""

            # Clean description, falling back gracefully
            desc_html = j.get("description") or j.get("description_short") or ""
            description = _clean_html(desc_html)

            date_posted_raw = j.get("posted_date") or j.get("listing_updated_time")
            date_posted = _to_iso_date(date_posted_raw)

            company = j.get("company_name") or "Amazon"

            out.append(
                _normalize_job(
                    title=title,
                    company=company,
                    location=location,
                    url=url,
                    source="amazon_jobs",
                    description=description,
                    date_posted=date_posted,
                )
            )

        # Stop if we hit the last page (short page or reached total hits)
        if len(jobs) < page_size or (total_hits and offset + page_size >= total_hits):
            break

        # Gentle pacing
        time.sleep(0.25)

    return out