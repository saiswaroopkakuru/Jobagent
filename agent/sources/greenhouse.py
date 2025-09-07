
import requests
import re
from html import unescape
from typing import Dict, List

API_URL = 'https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true'


def _strip_html(html: str) -> str:
    if not html:
        return ''
    text = re.sub(r'<[^>]+>', ' ', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_jobs(slug: str) -> List[Dict]:
    url = API_URL.format(slug=slug)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    out: List[Dict] = []
    for j in data.get('jobs', []):
        title = j.get('title') or ''
        location = (j.get('location') or {}).get('name') or ''
        abs_url = j.get('absolute_url') or ''
        content = j.get('content') or ''
        desc = _strip_html(content)
        updated = j.get('updated_at') or j.get('created_at')
        company = slug.title()
        out.append({
            'title': title,
            'company': company,
            'location': location,
            'url': abs_url,
            'source': f'greenhouse:{slug}',
            'description': desc,
            'date_posted': updated,
        })
    return out
