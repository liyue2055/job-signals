# Job Signals

Twice-daily collection of public job postings into SQLite, with a generated dashboard.

- `collector.py` — pulls Greenhouse / Lever / Ashby public APIs
- `gen_dashboard.py` — regenerates `index.html` from `jobs.db`
- `index.html` — the dashboard (GitHub Pages)
