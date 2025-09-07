
import re
from typing import Dict

US_STATES = {
    'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'
}

NEGATIVE_SPONSOR_PHRASES = [
    'no sponsorship',
    'cannot sponsor',
    'not sponsor',
    'without sponsorship',
    'must be authorized to work in the us without sponsorship',
]

POSITIVE_SPONSOR_PHRASES = [
    'h-1b', 'h1b', 'visa sponsorship', 'sponsor work visa', 'visa support'
]

SENIOR_BLOCK = ['senior', 'sr.', 'staff', 'principal', 'lead', 'manager', 'director']
ENTRY_KEYWORDS_DEFAULT = ['new grad', 'entry-level', 'junior', 'graduate', 'early career', 'university', 'campus', 'recent graduate', '0-2 years', '1+ years']


def is_us_location(location: str) -> bool:
    if not location:
        return False
    s = location.lower()
    if 'united states' in s or s.strip() in ('us', 'usa', 'u.s.', 'u.s.a.'):
        return True
    tokens = re.split(r'[,\s]+', location.upper())
    return any(tok in US_STATES for tok in tokens)


def compute_entry_level_score(title: str, description: str, cfg: Dict) -> float:
    t = (title or '').lower()
    d = (description or '').lower()

    excluded = set([x.lower() for x in cfg.get('filters', {}).get('excluded_seniority', [])] or SENIOR_BLOCK)
    if any(x in t for x in excluded):
        return 0.0

    entry_terms = set([x.lower() for x in cfg.get('filters', {}).get('entry_level_keywords', [])] or ENTRY_KEYWORDS_DEFAULT)
    score = 0.0
    if any(x in t for x in entry_terms):
        score = max(score, 0.9)
    if any(x in d for x in entry_terms):
        score = max(score, 0.8)

    interests = [x.lower() for x in cfg.get('filters', {}).get('titles_of_interest', [])]
    if interests and any(x in t for x in interests):
        score = max(score, 0.6)

    if score == 0.0 and not any(x in d for x in excluded):
        score = 0.4

    return min(score, 1.0)


def clean_company_name(name: str) -> str:
    return (name or '').strip().lower()


def compute_h1b_confidence(company: str, text: str, known_sponsors: set, cfg: Dict) -> float:
    s = (text or '').lower()
    comp = clean_company_name(company)

    neg = [x.lower() for x in cfg.get('h1b', {}).get('negative_keywords', [])] or NEGATIVE_SPONSOR_PHRASES
    if any(x in s for x in neg):
        return 0.0

    pos = [x.lower() for x in cfg.get('h1b', {}).get('positive_keywords', [])] or POSITIVE_SPONSOR_PHRASES
    confidence = 0.0
    if any(x in s for x in pos):
        confidence = max(confidence, 1.0)

    if comp in known_sponsors:
        confidence = max(confidence, 0.7)

    if confidence == 0.0:
        confidence = 0.4 if comp in known_sponsors else 0.2

    return min(confidence, 1.0)
