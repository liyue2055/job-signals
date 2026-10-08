#!/usr/bin/env python3
"""Backfill missing job descriptions by re-pulling detail endpoints.

Run:  cd ~/workspace/job-tracker && python3 backfill_descriptions.py
Polite: ~1 req/sec, same UA as collector.py.
"""
import json, sqlite3, time, sys
sys.path.insert(0, ".")
from collector import fetch, clean_html, classify, extract_skills, SLEEP

con = sqlite3.connect("jobs.db")
rows = con.execute(
    "SELECT id, source, source_id, title FROM postings "
    "WHERE description IS NULL OR TRIM(description)=''").fetchall()
print(f"missing descriptions: {len(rows)}", flush=True)

fixed, failed = 0, 0
for i, (rid, source, source_id, title) in enumerate(rows, 1):
    try:
        if source == "greenhouse" and ":" in source_id:
            board, jid = source_id.split(":", 1)
            d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}")
            # 2026-10: Greenhouse detail payload renamed description -> content
            desc = clean_html(d.get("content") or d.get("description", ""))
            loc = (d.get("location") or {}).get("name", "")
            posted = d.get("updated_at", "")
        else:
            raise ValueError(f"unsupported source: {source}/{source_id}")
        if desc:
            cat = classify(title, desc)
            skills = json.dumps(extract_skills(title, desc))
            con.execute(
                "UPDATE postings SET description=?, location=?, posted_at=?, "
                "category=?, skills=? WHERE id=?",
                (desc, loc, posted, cat, skills, rid))
            fixed += 1
        else:
            failed += 1
    except Exception as e:
        failed += 1
        print(f"  [{i}/{len(rows)}] {source_id} failed: {e}", flush=True)
    if i % 25 == 0:
        con.commit()
        print(f"  progress {i}/{len(rows)} — fixed {fixed}, failed {failed}", flush=True)
    time.sleep(SLEEP)

con.commit()
left = con.execute(
    "SELECT COUNT(*) FROM postings WHERE description IS NULL OR TRIM(description)=''").fetchone()[0]
con.close()
print(f"DONE: fixed {fixed}, failed {failed}, still missing {left}")
