#!/usr/bin/env python3
"""Generate index.html dashboard from jobs.db — bilingual, with search,
category filters and pagination (GitHub Pages / Vercel ready)."""
import sqlite3, json, html as ihtml
from datetime import datetime
from collections import Counter

CAT_ZH = {"engineering": "工程技术", "data": "数据", "product": "产品",
    "design": "设计", "marketing": "市场营销", "sales": "销售",
    "operations": "运营", "support": "客户成功", "finance": "财务",
    "hr": "人力资源", "legal": "法务", "other": "其他"}

def esc(s):
    return ihtml.escape(s or "")

con = sqlite3.connect("jobs.db")
total = con.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
by_src = con.execute("SELECT source, COUNT(*) FROM postings GROUP BY source").fetchall()
by_cat = con.execute(
    "SELECT category, COUNT(*) FROM postings GROUP BY category ORDER BY 2 DESC").fetchall()
max_cat = by_cat[0][1] if by_cat else 1

skill_all = Counter()
skill_cat = {}
rows = con.execute("""SELECT rowid, title, company, location, category, skills, url,
    posted_at, description, source FROM postings ORDER BY collected_at DESC""").fetchall()
data = []
full = []
for rid, title, comp, loc, cat, skills, url, posted, desc, src in rows:
    try:
        ss = json.loads(skills or "[]")
    except Exception:
        ss = []
    for s in ss:
        skill_all[s] += 1
        skill_cat.setdefault(cat, Counter())[s] += 1
    data.append({"id": rid, "t": title, "co": comp, "loc": loc, "cat": cat, "sk": ss,
                 "url": url, "posted": posted or "",
                 "d": (desc or "")[:600]})
    full.append({"id": rid, "title": title, "company": comp, "location": loc,
                 "category": cat, "skills": ss, "url": url,
                 "posted_at": posted or "", "source": src,
                 "description": desc or ""})
top_skills = skill_all.most_common(15)
last_run = con.execute("SELECT MAX(run_at) FROM runs").fetchone()[0] or "—"
con.close()

def cat_bar(cat, n):
    w = max(2, int(n / max_cat * 100))
    zh = CAT_ZH.get(cat, cat)
    return (f'<div class="brow"><div class="blabel"><span class="lang-en">{esc(cat)}</span>'
            f'<span class="lang-zh" style="display:none">{esc(zh)}</span></div>'
            f'<div class="btrack"><div class="bfill" style="width:{w}%"></div></div>'
            f'<div class="bnum">{n}</div></div>')

def chips(items):
    return " ".join(f'<span class="chip">{esc(s)} <b>{c}</b></span>' for s, c in items)

top3 = [c for c, _ in by_cat[:3]]
per_cat_html = ""
for cat in top3:
    zh = CAT_ZH.get(cat, cat)
    per_cat_html += (f'<h3><span class="lang-en">{esc(cat)}</span>'
                     f'<span class="lang-zh" style="display:none">{esc(zh)}</span></h3>'
                     f'<div class="tagrow">{chips(skill_cat.get(cat, Counter()).most_common(8))}</div>')

now = datetime.now().strftime("%Y-%m-%d %H:%M")
src_line = ", ".join(f"{s}: {n}" for s, n in by_src)
json_data = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Signals — JD analysis</title>
<style>
*{{box-sizing:border-box}}body{{font-family:Georgia,'Times New Roman',serif;background:#f7f2e9;color:#2b2620;margin:0;line-height:1.7}}
body:lang(zh-CN){{font-family:"Noto Serif SC","Songti SC",Georgia,serif}}
header{{text-align:center;padding:44px 20px 16px;max-width:1020px;margin:0 auto}}
.kicker{{font-size:.8rem;letter-spacing:3px;color:#b39b6d;text-transform:uppercase}}
h1{{font-size:2rem;margin:10px 0 6px}}p.sub{{color:#8a7f6d;font-style:italic;margin:0 0 16px}}
.lang-toggle{{display:inline-flex;border:1px solid #d8cba8;border-radius:30px;overflow:hidden;background:#fffdf8}}
.lang-btn{{font-family:ui-sans-serif,system-ui;font-size:.85rem;font-weight:700;padding:8px 22px;border:none;background:transparent;color:#8a7f6d;cursor:pointer}}
.lang-btn.active{{background:#1b1e26;color:#fff}}
main{{max-width:1020px;margin:0 auto;padding:10px 20px 60px}}
.card{{background:#fffdf8;border:1px solid #e8dfcd;border-radius:14px;padding:24px 28px;margin:22px 0;box-shadow:0 2px 10px rgba(90,70,40,.06)}}
h2{{font-size:1.3rem;margin:0 0 12px}}
.stats{{display:flex;gap:14px;flex-wrap:wrap}}
.stat{{flex:1;min-width:150px;background:#f6f1e4;border-radius:10px;padding:14px 18px;text-align:center}}
.stat .v{{font-size:1.9rem;font-weight:800}}.stat .l{{font-size:.82rem;color:#8a7f6d}}
.brow{{display:flex;align-items:center;gap:12px;margin:9px 0}}
.blabel{{width:130px;font-weight:700;font-size:.92rem}}
.btrack{{flex:1;background:#efe7d3;border-radius:6px;height:16px}}
.bfill{{background:linear-gradient(90deg,#3b82f6,#2dd4bf);height:16px;border-radius:6px}}
.bnum{{width:60px;text-align:right;font-variant-numeric:tabular-nums}}
.tagrow{{margin:6px 0 14px}}.chip{{display:inline-block;font-family:ui-sans-serif,system-ui;font-size:.82rem;background:#f1ead9;border-radius:16px;padding:4px 13px;margin:3px 6px 3px 0}}.chip b{{color:#1c5fd6}}
.controls{{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 14px;align-items:center}}
.search{{flex:1;min-width:220px;font-family:ui-sans-serif,system-ui;font-size:.95rem;padding:10px 16px;border:1px solid #d8cba8;border-radius:24px;background:#fff;color:#2b2620}}
.pill{{font-family:ui-sans-serif,system-ui;font-size:.82rem;font-weight:700;border:1px solid #d8cba8;background:#f6f1e4;color:#6b5f45;border-radius:20px;padding:7px 15px;cursor:pointer}}
.pill.active{{background:#1b1e26;color:#fff;border-color:#1b1e26}}
.pill .n{{opacity:.65;font-weight:400}}
table{{width:100%;border-collapse:collapse;font-size:.88rem}}
th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid #efe7d3;vertical-align:top}}
th{{color:#8a7f6d;font-weight:700}}td.sk{{color:#6b5f45;font-size:.8rem}}
a{{color:#0a66c2}}
.pager{{display:flex;gap:8px;justify-content:center;align-items:center;margin-top:18px;flex-wrap:wrap;font-family:ui-sans-serif,system-ui}}
.pg{{border:1px solid #d8cba8;background:#fff;border-radius:8px;padding:6px 13px;cursor:pointer;font-size:.85rem;color:#2b2620}}
.pg.active{{background:#1c5fd6;color:#fff;border-color:#1c5fd6}}
.pg:disabled{{opacity:.4;cursor:default}}
.count{{font-size:.85rem;color:#8a7f6d;font-family:ui-sans-serif,system-ui}}
h3{{margin:16px 0 4px;font-size:1.05rem}}
footer{{text-align:center;color:#8a7f6d;font-size:.85rem;padding:0 20px 40px;font-style:italic}}
</style>
</head>
<body>
<header>
<div class="kicker">JD analysis</div>
<div class="lang-en"><h1>Job Signals</h1><p class="sub">What employers are hiring for — tracked twice daily from public job boards.</p></div>
<div class="lang-zh" style="display:none"><h1>职位信号</h1><p class="sub">雇主们在招什么样的人——每天两次从公开招聘渠道追踪。</p></div>
<div class="lang-toggle"><button class="lang-btn active" data-lang="en" onclick="setLang('en')">English</button><button class="lang-btn" data-lang="zh" onclick="setLang('zh')">中文</button></div>
</header>
<main>
<div class="card">
<div class="lang-en"><h2>Overview</h2></div>
<div class="lang-zh" style="display:none"><h2>总览</h2></div>
<div class="stats">
<div class="stat"><div class="v">{total}</div><div class="l"><span class="lang-en">postings</span><span class="lang-zh" style="display:none">职位</span></div></div>
<div class="stat"><div class="v">{len(by_cat)}</div><div class="l"><span class="lang-en">categories</span><span class="lang-zh" style="display:none">类别</span></div></div>
<div class="stat"><div class="v">{len(skill_all)}</div><div class="l"><span class="lang-en">distinct skills</span><span class="lang-zh" style="display:none">技能关键词</span></div></div>
</div>
<p style="color:#8a7f6d;font-size:.85rem">Sources: {esc(src_line)} · <span class="lang-en">Last pull</span><span class="lang-zh" style="display:none">上次抓取</span>: {esc(last_run)} · <span class="lang-en">Generated</span><span class="lang-zh" style="display:none">生成于</span>: {now}</p>
</div>
<div class="card">
<div class="lang-en"><h2>By category</h2></div>
<div class="lang-zh" style="display:none"><h2>按类别</h2></div>
{"".join(cat_bar(c, n) for c, n in by_cat)}
</div>
<div class="card">
<div class="lang-en"><h2>Top skills overall</h2></div>
<div class="lang-zh" style="display:none"><h2>总体热门技能</h2></div>
<div class="tagrow">{chips(top_skills)}</div>
<div class="lang-en"><h2>Top skills by category</h2></div>
<div class="lang-zh" style="display:none"><h2>各类别热门技能</h2></div>
{per_cat_html}
</div>
<div class="card">
<div class="lang-en"><h2>Browse postings</h2></div>
<div class="lang-zh" style="display:none"><h2>浏览职位</h2></div>
<div class="controls">
<input id="q" class="search" placeholder="Search title, company, skill…" oninput="setQ(this.value)">
<button class="pill" onclick="doExport('csv')"><span class="lang-en">Export CSV</span><span class="lang-zh" style="display:none">导出 CSV</span></button>
<button class="pill" onclick="doExport('json')"><span class="lang-en">Export JSON</span><span class="lang-zh" style="display:none">导出 JSON</span></button>
</div>
<div class="count" id="expnote"><span class="lang-en">Export downloads the current filtered view (up to 2,000 records).</span><span class="lang-zh" style="display:none">导出下载当前筛选结果（最多 2,000 条）。</span></div>
<div class="controls" id="pills"></div>
<div class="count" id="count"></div>
<table><thead><tr>
<th><span class="lang-en">Title</span><span class="lang-zh" style="display:none">职位</span></th>
<th><span class="lang-en">Company</span><span class="lang-zh" style="display:none">公司</span></th>
<th><span class="lang-en">Location</span><span class="lang-zh" style="display:none">地点</span></th>
<th><span class="lang-en">Skills</span><span class="lang-zh" style="display:none">技能</span></th>
</tr></thead><tbody id="rows"></tbody></table>
<div class="pager" id="pager"></div>
</div>
</main>
<footer><span class="lang-en">Job Signals · automated collection twice daily · public job-board data · <a href="stats.html">admin stats</a></span><span class="lang-zh" style="display:none">职位信号 · 每天自动抓取两次 · 公开招聘渠道数据 · <a href="stats.html">管理统计</a></span></footer>
<script>
var DATA = {json_data};
var CATS = {json.dumps([c for c,_ in by_cat], ensure_ascii=False)};
var CATN = {json.dumps({c: n for c,n in by_cat}, ensure_ascii=False)};
var CATZH = {json.dumps(CAT_ZH, ensure_ascii=False)};
var PER = 15, q = "", cat = "all", page = 1, lang = "en";
function catName(c) {{ return lang === "zh" ? (CATZH[c] || c) : c; }}
function filtered() {{
  var ql = q.trim().toLowerCase();
  return DATA.filter(function(p) {{
    if (cat !== "all" && p.cat !== cat) return false;
    if (!ql) return true;
    var hay = (p.t + " " + p.co + " " + p.loc + " " + p.sk.join(" ")).toLowerCase();
    return hay.indexOf(ql) >= 0;
  }});
}}
function escH(s) {{ return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }}
function renderPills() {{
  var h = '<button class="pill' + (cat==="all"?" active":"") + '" onclick="setCat(\\'all\\')">'
    + (lang==="zh"?"全部":"All") + ' <span class="n">' + DATA.length + '</span></button>';
  CATS.forEach(function(c) {{
    h += '<button class="pill' + (cat===c?" active":"") + '" onclick="setCat(\\'' + c + '\\')">'
      + escH(catName(c)) + ' <span class="n">' + CATN[c] + '</span></button>';
  }});
  document.getElementById("pills").innerHTML = h;
}}
function render() {{
  var list = filtered();
  var pages = Math.max(1, Math.ceil(list.length / PER));
  if (page > pages) page = pages;
  var start = (page - 1) * PER;
  var rows = list.slice(start, start + PER).map(function(p) {{
    var link = p.url ? '<a href="' + escH(p.url) + '" target="_blank" rel="noopener">' + escH(p.t) + '</a>' : escH(p.t);
    return "<tr><td>" + link + "</td><td>" + escH(p.co) + "</td><td>" + escH(p.loc)
      + "</td><td class='sk'>" + escH(p.sk.slice(0,6).join(", ")) + "</td></tr>";
  }}).join("");
  document.getElementById("rows").innerHTML = rows || '<tr><td colspan="4" style="text-align:center;color:#8a7f6d">'
    + (lang==="zh" ? "没有匹配的职位" : "No matching postings") + "</td></tr>";
  document.getElementById("count").textContent = list.length + (lang==="zh" ? " 个职位" : " postings");
  var ph = '<button class="pg" ' + (page<=1?"disabled":"") + ' onclick="goPage(' + (page-1) + ')">‹</button>';
  var lo = Math.max(1, page - 2), hi = Math.min(pages, page + 2);
  for (var i = lo; i <= hi; i++) ph += '<button class="pg' + (i===page?" active":"") + '" onclick="goPage(' + i + ')">' + i + "</button>";
  ph += '<button class="pg" ' + (page>=pages?"disabled":"") + ' onclick="goPage(' + (page+1) + ')">›</button>';
  ph += '<span class="count">' + page + " / " + pages + "</span>";
  document.getElementById("pager").innerHTML = ph;
  renderPills();
}}
function setCat(c) {{ cat = c; page = 1; render(); }}
function setQ(v) {{ q = v; page = 1; render(); }}
function goPage(p) {{ page = p; render(); window.scrollTo({{top: document.getElementById("rows").offsetTop - 120, behavior: "smooth"}}); }}
var EXPORT_CAP = 2000;
function csvCell(v) {{
  v = String(v == null ? "" : v);
  return (/[",\\n\\r]/.test(v)) ? '"' + v.replace(/"/g, '""') + '"' : v;
}}
function stamp() {{
  var d = new Date(), p = function(n){{ return String(n).padStart(2, "0"); }};
  return d.getFullYear() + p(d.getMonth()+1) + p(d.getDate()) + "-" + p(d.getHours()) + p(d.getMinutes());
}}
function doExport(fmt) {{
  var ids = {{}};
  filtered().forEach(function(p) {{ ids[p.id] = 1; }});
  var note = document.getElementById("expnote");
  note.textContent = (lang === "zh" ? "正在准备导出…" : "Preparing export…");
  fetch("postings.json").then(function(r) {{
    if (!r.ok) throw new Error("fetch failed");
    return r.json();
  }}).then(function(all) {{
    var rows = all.filter(function(p) {{ return ids[p.id]; }});
    var capped = false;
    if (rows.length > EXPORT_CAP) {{ rows = rows.slice(0, EXPORT_CAP); capped = true; }}
    var blob, name = "job-signals-" + stamp();
    if (fmt === "csv") {{
      var head = ["id","title","company","location","category","skills","url","posted_at","source","description"];
      var lines = [head.join(",")];
      rows.forEach(function(p) {{
        lines.push(head.map(function(k) {{
          var v = p[k];
          if (k === "skills" && Array.isArray(v)) v = v.join("; ");
          return csvCell(v);
        }}).join(","));
      }});
      blob = new Blob(["\\ufeff" + lines.join("\\n")], {{type: "text/csv;charset=utf-8"}});
      name += ".csv";
    }} else {{
      blob = new Blob([JSON.stringify(rows, null, 2)], {{type: "application/json"}});
      name += ".json";
    }}
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function() {{ URL.revokeObjectURL(a.href); a.remove(); }}, 4000);
    note.textContent = (lang === "zh" ? "已导出 " : "Exported ") + rows.length
      + (lang === "zh" ? " 条记录" : " records") + (capped ? (lang === "zh" ? "（已达上限 2,000）" : " (capped at 2,000)") : "")
      + (lang === "zh" ? "。" : ".");
  }}).catch(function() {{
    note.textContent = (lang === "zh" ? "导出失败，请稍后重试。" : "Export failed, please try again.");
  }});
}}
function setLang(l) {{
  lang = l;
  document.querySelectorAll('.lang-en').forEach(function(e){{e.style.display=(l==='en')?'':'none'}});
  document.querySelectorAll('.lang-zh').forEach(function(e){{e.style.display=(l==='zh')?'':'none'}});
  document.querySelectorAll('.lang-btn').forEach(function(b){{b.classList.toggle('active',b.dataset.lang===l)}});
  document.documentElement.lang=(l==='zh')?'zh-CN':'en';
  document.getElementById("q").placeholder = l==="zh" ? "搜索职位、公司、技能…" : "Search title, company, skill…";
  render();
}}
render();
</script>
</body>
</html>"""

with open("index.html", "w") as f:
    f.write(page)
with open("postings.json", "w") as f:
    json.dump(full, f, ensure_ascii=False)
print(f"dashboard written: {total} postings, {len(data)} embedded, {len(json_data)//1024}KB json")
print(f"postings.json written: {len(full)} full records")

# ---- Admin stats page (stats.html): per-source health, job kinds, release timing, ingest history ----
con2 = sqlite3.connect("jobs.db")
t2 = con2.execute("SELECT COUNT(*) FROM postings").fetchone()[0]
by_board = con2.execute(
    "SELECT company, source, COUNT(*) FROM postings GROUP BY company, source ORDER BY 3 DESC").fetchall()
by_cat2 = con2.execute(
    "SELECT category, COUNT(*) FROM postings GROUP BY category ORDER BY 2 DESC").fetchall()
runs = con2.execute(
    "SELECT run_at, source, fetched, inserted, note FROM runs ORDER BY id DESC LIMIT 30").fetchall()
per_day = con2.execute(
    "SELECT substr(collected_at,1,10), COUNT(*) FROM postings GROUP BY 1 ORDER BY 1").fetchall()
posted_dates = [r[0] for r in con2.execute(
    "SELECT posted_at FROM postings WHERE posted_at IS NOT NULL AND posted_at <> ''").fetchall()]
con2.close()

from datetime import date as _d
wk = Counter()
for p in posted_dates:
    try:
        d = _d.fromisoformat(str(p)[:10])
    except Exception:
        continue
    wk[d.fromordinal(d.toordinal() - d.weekday())] += 1
weeks = sorted(wk)[-8:]
max_wk = max((wk[w] for w in weeks), default=1)
max_board = by_board[0][2] if by_board else 1
max_cat2 = by_cat2[0][1] if by_cat2 else 1
max_day = max((n for _, n in per_day), default=1)
boards_n = len(by_board)
ats_n = len(set(a for _, a, _ in by_board))

last_pull = {}
for run_at, src, fetched, inserted, note in runs:
    board = src.split(":", 1)[1] if src and ":" in src else (src or "")
    if board not in last_pull:
        last_pull[board] = (run_at, fetched, inserted, note or "")

def srow(comp, ats, n):
    w = max(2, int(n / max_board * 100))
    ra, f, i, note = last_pull.get(comp, ("—", "—", "—", ""))
    cls = "ok" if "ok" in str(note).lower() else "bad"
    return (f'<tr><td><span class="dot {cls}"></span>{esc(comp)}</td><td>{esc(ats)}</td>'
            f'<td class="num">{n}</td>'
            f'<td><div class="btrack"><div class="bfill" style="width:{w}%"></div></div></td>'
            f'<td class="num">{n / t2 * 100:.1f}%</td><td>{esc(str(ra))}</td>'
            f'<td class="num">{f}→{i}</td><td>{esc(str(note))}</td></tr>')

def c2row(cat, n):
    w = max(2, int(n / max_cat2 * 100))
    zh = CAT_ZH.get(cat, cat)
    return (f'<div class="brow"><div class="blabel"><span class="lang-en">{esc(cat)}</span>'
            f'<span class="lang-zh" style="display:none">{esc(zh)}</span></div>'
            f'<div class="btrack"><div class="bfill" style="width:{w}%"></div></div>'
            f'<div class="bnum">{n}</div></div>')

def wrow(m):
    w = max(2, int(wk[m] / max_wk * 100))
    return (f'<div class="brow"><div class="blabel">w/c {m.strftime("%b %d")}</div>'
            f'<div class="btrack"><div class="bfill" style="width:{w}%"></div></div>'
            f'<div class="bnum">{wk[m]}</div></div>')

def drow(dy, n):
    w = max(2, int(n / max_day * 100))
    return (f'<div class="brow"><div class="blabel">{esc(dy)}</div>'
            f'<div class="btrack"><div class="bfill" style="width:{w}%"></div></div>'
            f'<div class="bnum">{n}</div></div>')

def rrow(run_at, src, f, i, note):
    cls = "ok" if "ok" in str(note or "").lower() else "bad"
    return (f"<tr><td>{esc(str(run_at))}</td><td>{esc(str(src))}</td>"
            f'<td class="num">{f}</td><td class="num">{i}</td>'
            f'<td><span class="dot {cls}"></span>{esc(str(note))}</td></tr>')

stats_page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Job Signals — admin stats</title>
<style>
*{{box-sizing:border-box}}body{{font-family:Georgia,'Times New Roman',serif;background:#f7f2e9;color:#2b2620;margin:0;line-height:1.7}}
body:lang(zh-CN){{font-family:"Noto Serif SC","Songti SC",Georgia,serif}}
header{{text-align:center;padding:44px 20px 16px;max-width:1020px;margin:0 auto}}
.kicker{{font-size:.8rem;letter-spacing:3px;color:#b39b6d;text-transform:uppercase}}
h1{{font-size:2rem;margin:10px 0 6px}}p.sub{{color:#8a7f6d;font-style:italic;margin:0 0 16px}}
.lang-toggle{{display:inline-flex;border:1px solid #d8cba8;border-radius:30px;overflow:hidden;background:#fffdf8}}
.lang-btn{{font-family:ui-sans-serif,system-ui;font-size:.85rem;font-weight:700;padding:8px 22px;border:none;background:transparent;color:#8a7f6d;cursor:pointer}}
.lang-btn.active{{background:#1b1e26;color:#fff}}
main{{max-width:1020px;margin:0 auto;padding:10px 20px 60px}}
.card{{background:#fffdf8;border:1px solid #e8dfcd;border-radius:14px;padding:24px 28px;margin:22px 0;box-shadow:0 2px 10px rgba(90,70,40,.06)}}
h2{{font-size:1.3rem;margin:0 0 12px}}
.stats{{display:flex;gap:14px;flex-wrap:wrap}}
.stat{{flex:1;min-width:150px;background:#f6f1e4;border-radius:10px;padding:14px 18px;text-align:center}}
.stat .v{{font-size:1.9rem;font-weight:800}}.stat .l{{font-size:.82rem;color:#8a7f6d}}
.brow{{display:flex;align-items:center;gap:12px;margin:9px 0}}
.blabel{{width:130px;font-weight:700;font-size:.92rem}}
.btrack{{flex:1;background:#efe7d3;border-radius:6px;height:16px}}
.bfill{{background:linear-gradient(90deg,#3b82f6,#2dd4bf);height:16px;border-radius:6px}}
.bnum{{width:60px;text-align:right;font-variant-numeric:tabular-nums}}
table{{width:100%;border-collapse:collapse;font-size:.86rem}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #efe7d3;vertical-align:top}}
th{{color:#8a7f6d;font-weight:700}}td.num{{text-align:right;font-variant-numeric:tabular-nums}}
a{{color:#0a66c2}}
.dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}
.dot.ok{{background:#22c55e}}.dot.bad{{background:#ef4444}}
footer{{text-align:center;color:#8a7f6d;font-size:.85rem;padding:0 20px 40px;font-style:italic}}
.note{{color:#8a7f6d;font-size:.85rem}}
</style>
</head>
<body>
<header>
<div class="kicker">admin</div>
<div class="lang-en"><h1>Job Signals — stats</h1><p class="sub">Collection health, source mix, job kinds and release timing.</p></div>
<div class="lang-zh" style="display:none"><h1>职位信号——管理统计</h1><p class="sub">抓取健康状况、数据来源、职位类别与发布时间分布。</p></div>
<div class="lang-toggle"><button class="lang-btn active" data-lang="en" onclick="setLang('en')">English</button><button class="lang-btn" data-lang="zh" onclick="setLang('zh')">中文</button></div>
</header>
<main>
<div class="card">
<div class="lang-en"><h2>Overview</h2></div>
<div class="lang-zh" style="display:none"><h2>总览</h2></div>
<div class="stats">
<div class="stat"><div class="v">{t2}</div><div class="l"><span class="lang-en">postings</span><span class="lang-zh" style="display:none">职位</span></div></div>
<div class="stat"><div class="v">{boards_n}</div><div class="l"><span class="lang-en">boards</span><span class="lang-zh" style="display:none">招聘渠道</span></div></div>
<div class="stat"><div class="v">{ats_n}</div><div class="l"><span class="lang-en">ATS platforms</span><span class="lang-zh" style="display:none">ATS 平台</span></div></div>
<div class="stat"><div class="v">{len(by_cat2)}</div><div class="l"><span class="lang-en">categories</span><span class="lang-zh" style="display:none">类别</span></div></div>
<div class="stat"><div class="v">{len(runs)}</div><div class="l"><span class="lang-en">recent pulls logged</span><span class="lang-zh" style="display:none">最近抓取记录</span></div></div>
</div>
<p class="note"><span class="lang-en">Generated</span><span class="lang-zh" style="display:none">生成于</span>: {now} · <a href="index.html"><span class="lang-en">back to dashboard</span><span class="lang-zh" style="display:none">返回看板</span></a></p>
</div>
<div class="card">
<div class="lang-en"><h2>Sources — where the data comes from</h2></div>
<div class="lang-zh" style="display:none"><h2>数据来源</h2></div>
<table><thead><tr>
<th><span class="lang-en">Board</span><span class="lang-zh" style="display:none">渠道</span></th>
<th>ATS</th>
<th><span class="lang-en">Postings</span><span class="lang-zh" style="display:none">职位</span></th><th></th>
<th><span class="lang-en">Share</span><span class="lang-zh" style="display:none">占比</span></th>
<th><span class="lang-en">Last pull</span><span class="lang-zh" style="display:none">上次抓取</span></th>
<th><span class="lang-en">Fetched→new</span><span class="lang-zh" style="display:none">抓取→新增</span></th>
<th><span class="lang-en">Note</span><span class="lang-zh" style="display:none">备注</span></th>
</tr></thead><tbody>
{"".join(srow(c, a, n) for c, a, n in by_board)}
</tbody></table>
</div>
<div class="card">
<div class="lang-en"><h2>Job kinds — by category</h2></div>
<div class="lang-zh" style="display:none"><h2>职位类别分布</h2></div>
{"".join(c2row(c, n) for c, n in by_cat2)}
</div>
<div class="card">
<div class="lang-en"><h2>When released — postings by week</h2></div>
<div class="lang-zh" style="display:none"><h2>发布时间——按周</h2></div>
{"".join(wrow(m) for m in weeks)}
<p class="note"><span class="lang-en">Based on each posting's published date (posted_at), last 8 weeks.</span><span class="lang-zh" style="display:none">基于每条职位的发布时间，最近 8 周。</span></p>
</div>
<div class="card">
<div class="lang-en"><h2>Collected per day</h2></div>
<div class="lang-zh" style="display:none"><h2>每日新增入库</h2></div>
{"".join(drow(dy, n) for dy, n in per_day)}
</div>
<div class="card">
<div class="lang-en"><h2>Ingest history — last {len(runs)} pulls</h2></div>
<div class="lang-zh" style="display:none"><h2>抓取历史——最近 {len(runs)} 次</h2></div>
<table><thead><tr>
<th><span class="lang-en">Time</span><span class="lang-zh" style="display:none">时间</span></th>
<th><span class="lang-en">Board</span><span class="lang-zh" style="display:none">渠道</span></th>
<th><span class="lang-en">Fetched</span><span class="lang-zh" style="display:none">抓取</span></th>
<th><span class="lang-en">New</span><span class="lang-zh" style="display:none">新增</span></th>
<th><span class="lang-en">Note</span><span class="lang-zh" style="display:none">备注</span></th>
</tr></thead><tbody>
{"".join(rrow(*r) for r in runs)}
</tbody></table>
</div>
</main>
<footer><span class="lang-en">Job Signals · admin stats · generated with each collection</span><span class="lang-zh" style="display:none">职位信号 · 管理统计 · 随每次抓取自动生成</span></footer>
<script>
function setLang(l) {{
  document.querySelectorAll('.lang-en').forEach(function(e){{e.style.display=(l==='en')?'':'none'}});
  document.querySelectorAll('.lang-zh').forEach(function(e){{e.style.display=(l==='zh')?'':'none'}});
  document.querySelectorAll('.lang-btn').forEach(function(b){{b.classList.toggle('active',b.dataset.lang===l)}});
  document.documentElement.lang=(l==='zh')?'zh-CN':'en';
}}
</script>
</body>
</html>"""

with open("stats.html", "w") as f:
    f.write(stats_page)
print(f"stats.html written: {len(by_board)} boards, {len(by_cat2)} categories, {len(runs)} runs logged")
