#!/usr/bin/env python3
"""Discover ATS board slugs from Hacker News comments (esp. monthly "Who is hiring" threads).

Uses the public HN Algolia API (no key needed):
  https://hn.algolia.com/api/v1/search_by_date?query=<term>&tags=comment
Walks back in time via numericFilters, extracts board slugs with per-ATS regexes,
and writes new candidates to hn_candidates.json.

Usage:  cd ~/workspace/job-tracker && python3 hn_discover.py [--pages 20]
Then:   python3 verify_boards.py --in hn_candidates.json
"""
import json, re, sys, time, html as ihtml, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; job-signals/1.0; research)"}
PATTERNS = {
    "greenhouse": re.compile(r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/([a-z0-9][a-z0-9_-]*)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([a-z0-9][a-z0-9_.%-]*)", re.I),
    "lever": re.compile(r"jobs\.(?:eu\.)?lever\.co/([a-z0-9][a-z0-9_.-]*)", re.I),
}
QUERIES = {"greenhouse": "greenhouse.io", "ashby": "ashbyhq.com", "lever": "lever.co"}

def hn_search(query, max_ts=None, hits=100):
    params = {"query": query, "tags": "comment", "hitsPerPage": hits}
    if max_ts:
        params["numericFilters"] = f"created_at_i<={int(max_ts)}"
    url = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    pages = int(sys.argv[sys.argv.index("--pages") + 1]) if "--pages" in sys.argv else 20
    found = {ats: set() for ats in PATTERNS}
    for ats, query in QUERIES.items():
        print(f"scanning HN comments for {query} ...", flush=True)
        max_ts, seen_pages = None, 0
        while seen_pages < pages:
            try:
                data = hn_search(query, max_ts)
            except Exception as e:
                print(f"  search error: {e}", flush=True)
                break
            hits = data.get("hits", [])
            if not hits:
                break
            for h in hits:
                text = ihtml.unescape(
                    (h.get("comment_text") or "") + " " + (h.get("story_title") or ""))
                for m in PATTERNS[ats].findall(text):
                    found[ats].add(m.lower().rstrip(".-_"))
            max_ts = min(h["created_at_i"] for h in hits) - 1
            seen_pages += 1
            print(f"  page {seen_pages}: {len(found[ats])} slugs so far", flush=True)
            time.sleep(0.5)
    out = {ats: sorted(s) for ats, s in found.items()}
    with open("hn_candidates.json", "w") as f:
        json.dump(out, f, indent=1)
    print("HN candidates:", {k: len(v) for k, v in out.items()})

if __name__ == "__main__":
    main()
