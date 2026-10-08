#!/usr/bin/env python3
"""Verify candidate ATS board slugs against live public APIs.

Usage:
  python3 verify_boards.py                # verify /tmp/candidate_slugs.json
  python3 verify_boards.py --in extra.json # verify additional candidates
Writes verified slugs to verified_boards.json (merged).
Polite: ~1 request per 1.5s.
"""
import json, sys, time
sys.path.insert(0, ".")
from collector import fetch, SEEDS

def check_greenhouse(slug):
    try:
        d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs")
        jobs = d.get("jobs", [])
        return True, len(jobs)
    except Exception as e:
        return False, str(e)[:80]

def check_lever(slug):
    try:
        d = fetch(f"https://api.lever.co/v0/postings/{slug}?mode=json")
        return (True, len(d)) if isinstance(d, list) else (False, "unexpected payload")
    except Exception as e:
        return False, str(e)[:80]

def check_ashby(slug):
    try:
        d = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        jobs = d.get("jobs", [])
        return True, len(jobs)
    except Exception as e:
        return False, str(e)[:80]

CHECKERS = {"greenhouse": check_greenhouse, "lever": check_lever, "ashby": check_ashby}

def main():
    in_path = "/tmp/candidate_slugs.json"
    if "--in" in sys.argv:
        in_path = sys.argv[sys.argv.index("--in") + 1]
    cands = json.load(open(in_path))
    try:
        verified = json.load(open("verified_boards.json"))
    except Exception:
        verified = {"greenhouse": [], "lever": [], "ashby": []}
    have = {(s, b) for s, b in SEEDS} | {
        (ats, s) for ats, lst in verified.items() for s in lst}

    for ats, slugs in cands.items():
        if ats not in CHECKERS:
            continue
        check = CHECKERS[ats]
        for slug in slugs:
            if (ats, slug) in have:
                continue
            ok, info = check(slug)
            print(f"{ats}:{slug} -> {'LIVE '+str(info)+' jobs' if ok else 'dead ('+str(info)+')'}",
                  flush=True)
            if ok:
                verified.setdefault(ats, []).append(slug)
                have.add((ats, slug))
            with open("verified_boards.json", "w") as f:
                json.dump(verified, f, indent=1)
            time.sleep(1.5)
    print("verified totals:", {k: len(v) for k, v in verified.items()})

if __name__ == "__main__":
    main()
