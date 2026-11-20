#!/usr/bin/env python3
"""Re-run the fixed extract_skills over stored descriptions in jobs.db.

Prepared 2026-11-19, NOT yet run — running it rewrites the skills column
for all rows and the next dashboard regeneration will reflect corrected
tags. Usage: cd ~/workspace/job-tracker && python3 backfill_skills.py
Makes a timestamped backup of jobs.db first.
"""
import json, shutil, sqlite3, time
from collector import extract_skills

backup = f"jobs.db.bak-{time.strftime('%Y%m%d-%H%M%S')}"
shutil.copyfile("jobs.db", backup)
print(f"backup: {backup}")

con = sqlite3.connect("jobs.db")
rows = con.execute("SELECT id, title, description FROM postings").fetchall()
changed = 0
for pid, title, desc in rows:
    new = json.dumps(extract_skills(title or "", desc or ""))
    old = con.execute("SELECT skills FROM postings WHERE id=?", (pid,)).fetchone()[0]
    if new != old:
        con.execute("UPDATE postings SET skills=? WHERE id=?", (new, pid))
        changed += 1
con.commit()
print(f"{changed} of {len(rows)} rows re-tagged")
con.close()
