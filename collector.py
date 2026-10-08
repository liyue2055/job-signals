#!/usr/bin/env python3
"""Job postings collector: Greenhouse + Lever + Ashby public JSON APIs -> SQLite.

No login, no scraping gray area. Polite: timeouts, UA header, ~1 req/sec.
Run:  cd ~/workspace/job-tracker && python3 collector.py
"""
import json, re, sqlite3, time, html as ihtml, sys, os
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DB = "jobs.db"
UA = {"User-Agent": "Mozilla/5.0 (compatible; job-signals/1.0; research)"}
# full-description fetches per greenhouse board per run; lower for bulk imports,
# later runs converge incrementally. Override: DETAIL_CAP_PER_BOARD=25
DETAIL_CAP_PER_BOARD = int(os.environ.get("DETAIL_CAP_PER_BOARD", "120"))
SLEEP = 1.0

# ---------------- fetch ----------------
def fetch(url, timeout=25):
    req = Request(url, headers=UA)
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def clean_html(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", ihtml.unescape(s)).strip()

# ---------------- classification ----------------
CATEGORY_RULES = [
    ("engineering", ["engineer", "developer", "software", "backend", "frontend",
     "fullstack", "full-stack", "mobile", "ios", "android", "devops", "sre",
     "infrastructure", "platform", "qa", "security", "systems"]),
    ("data", ["data scientist", "data engineer", "data analyst",
              "machine learning", "ml ", "analytics"]),
    ("product", ["product manager", "product designer", "product marketing",
                 "product ops", "product operations"]),
    ("design", ["designer", "ux", "ui ", "brand design", "illustrator",
                "motion design"]),
    ("marketing", ["marketing", "growth", "seo", "content", "social media"]),
    ("sales", ["sales", "account executive", "sdr", "business development",
               "partnerships", "revenue"]),
    ("operations", ["operations", "program manager", "chief of staff",
                    "workplace", "facilities"]),
    ("support", ["support", "customer success", "success manager"]),
    ("finance", ["finance", "accounting", "controller", "fp&a", "treasury"]),
    ("hr", ["recruit", "people ops", "talent", "human resources"]),
    ("legal", ["legal", "counsel", "compliance"]),
]
def classify(title, desc):
    t = (" " + title + " " + desc + " ").lower()
    for cat, kws in CATEGORY_RULES:
        if any(k in t for k in kws):
            return cat
    return "other"

SKILLS = ["python", "typescript", "javascript", "react", "go ", "golang", "rust",
    "java ", "kotlin", "swift", "c++", "sql", "kubernetes", "docker", "aws",
    "gcp", "azure", "terraform", "pytorch", "tensorflow", "scikit", "llm",
    "rag", "prompt engineering", "machine learning", "deep learning", "nlp",
    "computer vision", "data pipeline", "spark", "airflow", "dbt", "figma",
    "graphql", "rest api", "grpc", "redis", "postgres", "mysql",
    "elasticsearch", "kafka", "ci/cd", "github actions", "node.js", "next.js",
    "vue", "angular", "flutter", "react native", "tableau", "looker",
    "salesforce", "hubspot", "seo", "excel", "a/b testing"]
def extract_skills(title, desc):
    t = (" " + title + " " + desc + " ").lower()
    return sorted({s.strip() for s in SKILLS if s in t})

# ---------------- db ----------------
def db():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA journal_mode=WAL")
    with open("schema.sql") as f:
        con.executescript(f.read())
    return con

# ---------------- sources ----------------
def greenhouse(con, board):
    """Returns (fetched, inserted). Detail endpoint needed for full description.
    Incremental: details are fetched only for jobs not already stored with a
    description, so repeat runs cost ~1 list request per board."""
    fetched = ins = 0
    try:
        data = fetch(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs")
    except Exception as e:
        return 0, 0, f"list failed: {e}"
    jobs = data.get("jobs", [])
    have = {r[0] for r in con.execute(
        "SELECT source_id FROM postings WHERE source='greenhouse' "
        "AND description IS NOT NULL AND TRIM(description)<>''")}
    rows = []
    detail_n = 0
    for j in jobs:
        jid = str(j.get("id"))
        sid = f"{board}:{jid}"
        fetched += 1
        if sid in have or detail_n >= DETAIL_CAP_PER_BOARD:
            continue
        try:
            d = fetch(f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{jid}")
            # 2026-10: Greenhouse detail payload renamed description -> content
            desc = clean_html(d.get("content") or d.get("description", ""))
            loc = (d.get("location") or {}).get("name", "")
            posted = d.get("updated_at", "")
            detail_n += 1
        except Exception:
            desc, loc, posted = "", (j.get("location") or {}).get("name", ""), ""
        title = j.get("title", "")
        cat = classify(title, desc)
        rows.append(("greenhouse", sid, board, title, loc, cat, desc,
                     json.dumps(extract_skills(title, desc)),
                     j.get("absolute_url", ""), posted))
        time.sleep(SLEEP)
    cur = con.total_changes
    for r in rows:
        con.execute("""INSERT OR IGNORE INTO postings
            (source, source_id, company, title, location, category,
             description, skills, url, posted_at) VALUES (?,?,?,?,?,?,?,?,?,?)""", r)
    ins = con.total_changes - cur
    con.commit()
    return fetched, ins, "ok"

def lever(con, company):
    try:
        jobs = fetch(f"https://api.lever.co/v0/postings/{company}?mode=json")
    except Exception as e:
        return 0, 0, f"failed: {e}"
    if not isinstance(jobs, list):
        return 0, 0, "unexpected payload"
    cur = con.total_changes
    for j in jobs:
        title = j.get("text", "")
        desc = clean_html(j.get("description", ""))
        cats = j.get("categories") or {}
        loc = cats.get("location", "")
        created = j.get("createdAt")
        posted = ""
        if created:
            try:
                posted = datetime.fromtimestamp(created/1000, tz=timezone.utc).isoformat()
            except Exception:
                pass
        con.execute("""INSERT OR IGNORE INTO postings
            (source, source_id, company, title, location, category,
             description, skills, url, posted_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("lever", f"{company}:{j.get('id')}", company, title, loc,
             classify(title, desc), desc, json.dumps(extract_skills(title, desc)),
             j.get("hostedUrl", ""), posted))
        time.sleep(0.3)
    ins = con.total_changes - cur
    con.commit()
    return len(jobs), ins, "ok"

def ashby(con, board):
    try:
        data = fetch(f"https://api.ashbyhq.com/posting-api/job-board/{board}")
    except Exception as e:
        return 0, 0, f"failed: {e}"
    jobs = data.get("jobs", [])
    cur = con.total_changes
    for j in jobs:
        title = j.get("title", "")
        desc = clean_html(j.get("descriptionHtml", ""))
        posted = j.get("publishedAt", "")
        con.execute("""INSERT OR IGNORE INTO postings
            (source, source_id, company, title, location, category,
             description, skills, url, posted_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("ashby", f"{board}:{j.get('id')}", board, title,
             j.get("locationName", ""), classify(title, desc), desc,
             json.dumps(extract_skills(title, desc)), j.get("jobUrl", ""), posted))
        time.sleep(0.3)
    ins = con.total_changes - cur
    con.commit()
    return len(jobs), ins, "ok"

# 2026-10-07: notion/ramp migrated Greenhouse->Ashby; duolingo/netlify migrated Lever->Greenhouse
SEEDS = [
    ("greenhouse", "anthropic"), ("greenhouse", "figma"), ("ashby", "notion"),
    ("ashby", "ramp"), ("greenhouse", "datadog"),
    ("greenhouse", "duolingo"), ("greenhouse", "netlify"),
    ("ashby", "ashby"), ("ashby", "linear"),
]
FUNCS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}

def main():
    con = db()
    summary = []
    alive = []
    for src, board in SEEDS:
        try:
            fetched, ins, note = FUNCS[src](con, board)
        except Exception as e:
            fetched, ins, note = 0, 0, f"error: {e}"
        con.execute("INSERT INTO runs(source, fetched, inserted, note) VALUES (?,?,?,?)",
                    (f"{src}:{board}", fetched, ins, note))
        con.commit()
        status = "OK" if fetched else "DEAD"
        summary.append(f"{src}:{board} fetched={fetched} new={ins} [{status}]")
        if fetched:
            alive.append(f"- {src}:{board}")
        print(summary[-1], flush=True)
    total = con.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
    print(f"TOTAL postings in db: {total}", flush=True)
    with open("SEEDS.md", "w") as f:
        f.write("# Working job-board seeds\n\nVerified by collector runs.\n\n" + "\n".join(alive) + "\n")
    con.close()

if __name__ == "__main__":
    main()
