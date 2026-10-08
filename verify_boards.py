#!/usr/bin/env python3
"""Verify candidate ATS board slugs against live public APIs.

Usage:
  python3 verify_boards.py --in slug_sources/all_candidates.json
Writes verified slugs to verified_boards.json (merged) as {slug: job_count},
so the seed-wiring step can keep only boards with real openings.
Polite: ~1 request per 1.5s. Idempotent: skips SEEDS and already-verified slugs.
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
        # normalize legacy list format to {slug: job_count}
        for ats in list(verified):
            if isinstance(verified[ats], list):
                verified[ats] = {s: None for s in verified[ats]}
    except Exception:
        verified = {"greenhouse": {}, "lever": {}, "ashby": {}}
    have = {(s, b) for s, b in SEEDS} | {
        (ats, s) for ats, d in verified.items() for s in d}

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
                verified.setdefault(ats, {})[slug] = info if isinstance(info, int) else 0
                have.add((ats, slug))
            with open("verified_boards.json", "w") as f:
                json.dump(verified, f, indent=1)
            time.sleep(1.5)
    print("verified totals:", {k: len(v) for k, v in verified.items()})

if __name__ == "__main__":
    main()
