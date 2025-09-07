
import os
from dataclasses import dataclass
from typing import Dict

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


@dataclass
class ResumeProfile:
    skills: Dict[str, float]
    titles_of_interest: set


def _normalize(s: str) -> str:
    return (s or '').lower()


def _extract_text_from_pdf(path: str) -> str:
    if not PdfReader:
        return ''
    if not os.path.isfile(path):
        return ''
    try:
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            try:
                parts.append(page.extract_text() or '')
            except Exception:
                continue
        return '
'.join(parts)
    except Exception:
        return ''


def build_resume_profile(cfg: Dict) -> ResumeProfile:
    resume_cfg = cfg.get('resume', {})
    skills: Dict[str, float] = {}

    if resume_cfg.get('use_pdf'):
        text = _extract_text_from_pdf(resume_cfg.get('resume_pdf_path', ''))
        t = _normalize(text)
        configured = resume_cfg.get('skills', {}) or {}
        if configured:
            for skill, wt in configured.items():
                if _normalize(skill) in t:
                    skills[_normalize(skill)] = float(wt)
        else:
            defaults = {
                'python': 1.0, 'java': 0.8, 'javascript': 0.7, 'sql': 1.0,
                'aws': 0.8, 'docker': 0.7, 'react': 0.6, 'node': 0.6,
                'data structures': 0.9, 'algorithms': 0.9,
            }
            for k, v in defaults.items():
                if k in t:
                    skills[k] = v
    else:
        cfg_skills = resume_cfg.get('skills', {}) or {}
        for k, v in cfg_skills.items():
            skills[_normalize(k)] = float(v)

    titles = set(_normalize(x) for x in resume_cfg.get('titles_of_interest', []) or [])
    return ResumeProfile(skills=skills, titles_of_interest=titles)


def compute_match_score(text: str, profile: ResumeProfile) -> float:
    t = _normalize(text)
    if not profile.skills:
        return 0.0

    total_weight = sum(profile.skills.values())
    if total_weight <= 0:
        return 0.0

    score = 0.0
    for skill, weight in profile.skills.items():
        if skill in t:
            score += weight
    return max(0.0, min(1.0, score / total_weight))
