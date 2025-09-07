
import requests
import re
from html import unescape
from typing import Dict, List

API_URL = 'https://api.lever.co/v0/postings/{slug}?mode=json'


def _strip_html(html: str) -> str:
    if not html:
        return ''
    text = re.sub(r'<[^>}+>', ' ', html)
    text = unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def fetch_jobs(slug: str) -> List[Dict]:
    url = API_URL.format(slug=slug)
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    arr = r.json()
    out: List[Dict] = []
    for j in arr:
        title = (j.get('text') or {}).get('title') or j.get('title') or ''
        location = (j.get('categories') or {}).get('location') or ''
        abs_url = j.get('hostedUrl') or j.get('applyUrl') or ''
        desc = _strip_html(j.get('descriptionPlain') or j.get('description') or '')
        created = j.get('createdAt')
        date_str = None
        if isinstance(created, (int, float)):
            import datetime
            try:
                date_str = datetime.datetime.utcfromtimestamp(created/1000).isoformat() + 'Z'
            except Exception:
                date_str = None
        company = slug.title()
        out.append({
            'title': title,
            'company': company,
            'location': location,
            'url': abs_url,
            'source': f'lever:{slug}',
            'description': desc,
            'date_posted': date_str,
        })
    return out
