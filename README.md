
# Enhanced Job AI Agent (Entry-level + H-1B Sponsorship + Resume Match)

This agent searches multiple career boards (Greenhouse, Lever), filters for US-based entry-level software engineering roles with a preference for H-1B sponsorship, and ranks them by how well they match your resume/skills. It generates a daily HTML email report and can run automatically via GitHub Actions.

## Features
- Multi-source search: Greenhouse and Lever company boards
- Entry-level detection (New Grad, Junior, Early Career)
- H-1B sponsorship heuristics (keywords + known sponsor list)
- Resume-based matching with adjustable skill weights
- SQLite persistence to avoid duplicates
- HTML email report (or save to file if email not configured)
- GitHub Actions workflow for daily automation

## Quick Start (Local)
1. Create and activate a Python 3.10+ environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the example config and edit as needed:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```
4. (Optional) Place your resume PDF at `resume/your_resume.pdf` and set the path in `config.yaml`.
5. Run the agent (either way works):
   ```bash
   # Option A: via package module (more robust)
   python -m agent --config config/config.yaml

   # Option B: via script (now works even if called from scripts/)
   python scripts/run_agent.py --config config/config.yaml
   ```
6. If email is not configured, find the latest HTML report at `reports/latest_report.html`.

## Configuration
See `config/config.example.yaml` for all options. Key sections:
- `sources.greenhouse` and `sources.lever`: lists of company slugs to crawl.
- `filters`: entry-level keywords, exclusions, and US location handling.
- `h1b`: keywords and known sponsor list (not exhaustive; customize as needed).
- `resume`: toggle `use_pdf` and configure `resume_pdf_path` or list your skills.
- `email`: SMTP settings and recipients.

## GitHub Actions (Automation)
1. Push this repo to GitHub.
2. In GitHub -> Settings -> Secrets and variables -> Actions, add:
   - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`
   - `REPORT_TO_EMAIL`, `REPORT_FROM_EMAIL`
3. (Optional) Add your customized `config/config.yaml` to the repo, or let the workflow copy the example.
4. The workflow runs daily and uploads the HTML report as a build artifact.

## Notes and Tips
- Company boards change; customize the lists to suit your targets.
- H-1B detection uses heuristics and a small known sponsor list. Always verify details in the JD or with recruiters.
- Resume parsing is lightweight; for better results, add your prioritized skills directly under `resume.skills` with weights.

## License
MIT
