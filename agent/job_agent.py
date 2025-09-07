
import argparse
import hashlib
import logging
import os
import smtplib
import sqlite3
import ssl
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .sources.greenhouse import fetch_jobs as fetch_greenhouse_jobs
from .sources.lever import fetch_jobs as fetch_lever_jobs
from . import filters as job_filters
from . import resume_matching


@dataclass
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    source: str
    description: str
    date_posted: Optional[str] = None
    entry_level_score: float = 0.0
    h1b_confidence: float = 0.0
    resume_match: float = 0.0
    final_score: float = 0.0


def load_config(path: str) -> Dict:
    if not os.path.isfile(path):
        example_path = os.path.join(os.path.dirname(path), 'config.example.yaml')
        if os.path.isfile(example_path):
            with open(example_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            raise FileNotFoundError(f"Config not found: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def ensure_db(db_path: str):
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(
        '''CREATE TABLE IF NOT EXISTS jobs (
               job_id TEXT PRIMARY KEY,
               title TEXT,
               company TEXT,
               location TEXT,
               url TEXT,
               source TEXT,
               date_posted TEXT,
               first_seen TEXT,
               last_seen TEXT,
               description TEXT
           )'''
    )
    con.commit()
    con.close()


def job_hash(url: str) -> str:
    import hashlib as _h
    return _h.sha256(url.encode('utf-8')).hexdigest()


def upsert_job(db_path: str, job: Job):
    now = datetime.utcnow().isoformat()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('SELECT job_id FROM jobs WHERE job_id = ?', (job.id,))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            '''UPDATE jobs SET last_seen=?, title=?, company=?, location=?, url=?, source=?, date_posted=?, description=?
               WHERE job_id=?''',
            (now, job.title, job.company, job.location, job.url, job.source, job.date_posted, job.description, job.id)
        )
    else:
        cur.execute(
            '''INSERT INTO jobs (job_id, title, company, location, url, source, date_posted, first_seen, last_seen, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (job.id, job.title, job.company, job.location, job.url, job.source, job.date_posted, now, now, job.description)
        )
    con.commit()
    con.close()


def fetch_all_jobs(cfg: Dict) -> List[Dict]:
    jobs: List[Dict] = []
    gh_companies = cfg.get('sources', {}).get('greenhouse', []) or []
    lever_companies = cfg.get('sources', {}).get('lever', []) or []

    for slug in gh_companies:
        try:
            jobs.extend(fetch_greenhouse_jobs(slug))
        except Exception as e:
            logging.warning(f"Greenhouse fetch failed for {slug}: {e}")

    for slug in lever_companies:
        try:
            jobs.extend(fetch_lever_jobs(slug))
        except Exception as e:
            logging.warning(f"Lever fetch failed for {slug}: {e}")

    return jobs


def score_and_filter_jobs(raw_jobs: List[Dict], cfg: Dict, resume_profile: resume_matching.ResumeProfile) -> List[Job]:
    known_sponsors_file = cfg.get('h1b', {}).get('known_sponsors_file')
    known_set = set()
    if known_sponsors_file and os.path.isfile(known_sponsors_file):
        with open(known_sponsors_file, 'r', encoding='utf-8') as f:
            known_set = {line.strip().lower() for line in f if line.strip()}

    out: List[Job] = []
    for rj in raw_jobs:
        title = (rj.get('title') or '').strip()
        company = (rj.get('company') or '').strip()
        location = (rj.get('location') or '').strip()
        url = (rj.get('url') or '').strip()
        source = (rj.get('source') or '').strip()
        description = (rj.get('description') or '').strip()
        date_posted = rj.get('date_posted')

        if cfg.get('filters', {}).get('require_us_location', True):
            if not job_filters.is_us_location(location):
                continue

        entry_score = job_filters.compute_entry_level_score(title, description, cfg)
        if entry_score <= 0.0:
            continue

        h1b_conf = job_filters.compute_h1b_confidence(company, f"{title}
{description}", known_set, cfg)
        resume_match = resume_matching.compute_match_score(f"{title}
{description}", resume_profile)

        min_match = float(cfg.get('resume', {}).get('min_match_score', 0.0))
        if resume_match < min_match:
            continue

        final_score = 0.5 * resume_match + 0.3 * h1b_conf + 0.2 * entry_score

        jid = job_hash(url)
        job = Job(
            id=jid,
            title=title,
            company=company,
            location=location,
            url=url,
            source=source,
            description=description,
            date_posted=date_posted,
            entry_level_score=entry_score,
            h1b_confidence=h1b_conf,
            resume_match=resume_match,
            final_score=final_score,
        )
        out.append(job)

    out.sort(key=lambda j: j.final_score, reverse=True)
    return out


def render_html_report(jobs: list, limit: int = 50) -> str:
    rows = []
    for j in jobs[:limit]:
        rows.append(
            f"<tr>
"
            f"  <td><a href='{j.url}' target='_blank' rel='noopener'>{j.title}</a></td>
"
            f"  <td>{j.company}</td>
"
            f"  <td>{j.location}</td>
"
            f"  <td>{j.source}</td>
"
            f"  <td>{j.date_posted or ''}</td>
"
            f"  <td>{j.resume_match:.2f}</td>
"
            f"  <td>{j.h1b_confidence:.2f}</td>
"
            f"  <td>{j.entry_level_score:.2f}</td>
"
            f"  <td><b>{j.final_score:.2f}</b></td>
"
            f"</tr>
"
        )
    table_rows = "".join(rows)
    generated = datetime.utcnow().isoformat() + 'Z'
    html = (
        "<html>
"
        "  <head>
"
        "    <meta charset='utf-8'>
"
        "    <title>Job AI Agent Report</title>
"
        "    <style>
"
        "      body { font-family: Arial, sans-serif; padding: 20px; }
"
        "      table { border-collapse: collapse; width: 100%; }
"
        "      th, td { border: 1px solid #ddd; padding: 8px; }
"
        "      th { background-color: #f4f4f4; }
"
        "      tr:hover { background: #fafafa; }
"
        "    </style>
"
        "  </head>
"
        "  <body>
"
        f"    <h2>Job AI Agent Report</h2>
"
        f"    <p>Generated at: {generated}</p>
"
        "    <table>
"
        "      <thead>
"
        "        <tr>
"
        "          <th>Title</th>
"
        "          <th>Company</th>
"
        "          <th>Location</th>
"
        "          <th>Source</th>
"
        "          <th>Date</th>
"
        "          <th>Resume</th>
"
        "          <th>H-1B</th>
"
        "          <th>Entry</th>
"
        "          <th>Score</th>
"
        "        </tr>
"
        "      </thead>
"
        "      <tbody>
"
        f"        {table_rows}
"
        "      </tbody>
"
        "    </table>
"
        "  </body>
"
        "</html>
"
    )
    return html


def send_email(cfg: Dict, subject: str, html_body: str):
    email_cfg = cfg.get('email', {})
    if not email_cfg.get('enabled', False):
        return False

    host = os.environ.get('SMTP_HOST') or str(email_cfg.get('smtp_host', ''))
    port = int(os.environ.get('SMTP_PORT') or email_cfg.get('smtp_port') or 587)
    user = os.environ.get('SMTP_USER') or str(email_cfg.get('smtp_user', ''))
    password = os.environ.get('SMTP_PASS') or str(email_cfg.get('smtp_pass', ''))
    from_email = os.environ.get('REPORT_FROM_EMAIL') or str(email_cfg.get('from_email', ''))
    to_email = os.environ.get('REPORT_TO_EMAIL') or str(email_cfg.get('to_email', ''))

    if not (host and port and from_email and to_email):
        logging.warning('Email not fully configured; skipping send.')
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    part = MIMEText(html_body, 'html')
    msg.attach(part)

    context = ssl.create_default_context()
    import smtplib as _smtp
    with _smtp.SMTP(host, port) as server:
        try:
            server.starttls(context=context)
        except Exception:
            pass
        if user and password:
            server.login(user, password)
        server.sendmail(from_email, [to_email], msg.as_string())
    return True


def run(config_path: str) -> str:
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')
    cfg = load_config(config_path)

    db_path = cfg.get('persistence', {}).get('database_path', 'data/jobs.db')
    ensure_db(db_path)

    profile = resume_matching.build_resume_profile(cfg)

    raw = fetch_all_jobs(cfg)
    logging.info(f"Fetched {len(raw)} raw jobs")

    scored = score_and_filter_jobs(raw, cfg, profile)
    logging.info(f"Scored/filtered down to {len(scored)} jobs")

    for j in scored:
        upsert_job(db_path, j)

    top_n = int(cfg.get('report', {}).get('top_n', 50))
    html = render_html_report(scored, limit=top_n)

    Path('reports').mkdir(exist_ok=True)
    report_path = os.path.join('reports', 'latest_report.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    sent = send_email(cfg, subject='Job AI Agent Daily Report', html_body=html)
    if sent:
        logging.info('Email sent successfully.')
    else:
        logging.info(f'Report written to {report_path}')

    return report_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run the Enhanced Job AI Agent')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Path to YAML config file')
    args = parser.parse_args()
    rp = run(args.config)
    print(f"Report ready: {rp}")
