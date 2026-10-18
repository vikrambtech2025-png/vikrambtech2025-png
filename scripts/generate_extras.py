#!/usr/bin/env python3
# Extras generator: language donut, constellation, activity, traffic, wrapped,
# galaxy, guestbook, reactions, data.json, blog + RSS, OG card.
# 100% self-hosted. Standard library only.
import hashlib
import json
import math
import os
import random
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_art as g

USER = g.USER
REPO = "vikrambtech2025-png/vikrambtech2025-png"
OUT = g.OUT_DIR
MONO = g.MONO
PAL = ["#00E5FF", "#FF1F4B", "#8B5CF6", "#FFB300", "#22C55E", "#00A3FF", "#FF6B9D", "#7CFFB2", "#5A6B85"]


def opt(path):
    try:
        return g.api(path)
    except Exception as exc:
        print("  ! " + str(path)[:60] + " -> " + str(exc)[:70], file=sys.stderr)
        return None


def human(n):
    n = float(n)
    for u in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return ("%d B" % int(n)) if u == "B" else ("%.1f %s" % (n, u))
        n /= 1024.0
    return "%.1f TB" % n


def head(w, h, label):
    return g.svg_header(w, h, label)


def panel(w, h, title, sub):
    return [
        head(w, h, title),
        "<defs><linearGradient id='bg' x1='0' y1='0' x2='0' y2='1'>"
        "<stop offset='0' stop-color='#000000'/><stop offset='1' stop-color='#05070d'/></linearGradient></defs>",
        "<rect width='%d' height='%d' fill='url(#bg)'/>" % (w, h),
        "<rect x='1' y='1' width='%d' height='%d' rx='14' fill='none' stroke='#16203a' stroke-width='2'/>" % (w - 2, h - 2),
        "<text x='34' y='38' font-family=\"%s\" font-size='14' fill='#00E5FF'>%s</text>" % (MONO, title),
        "<text x='%d' y='38' text-anchor='end' font-family=\"%s\" font-size='11.5' fill='#5A6B85'>%s</text>" % (w - 34, MONO, sub),
    ]


def wfile(rel, content):
    d = os.path.dirname(rel)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(rel, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("wrote", rel, len(content), "bytes")


# --------------------------------------------------------------------- donut
def fetch_languages(repos):
    agg = {}
    for r in repos:
        if r.get("fork"):
            continue
        owner = (r.get("owner") or {}).get("login") or USER
        data = opt("/repos/%s/%s/languages" % (owner, r["name"]))
        if not data:
            continue
        for k, v in data.items():
            agg[k] = agg.get(k, 0) + int(v)
    return agg


def build_donut(agg, repo_count):
    items = sorted(agg.items(), key=lambda kv: -kv[1])
    top = list(items[:8])
    rest = sum(v for _, v in items[8:])
    if rest > 0:
        top.append(("Other", rest))
    total = float(sum(v for _, v in top)) or 1.0
    W, H = 980, 440
    cx, cy, r, sw = 300.0, 224.0, 132.0, 44.0
    circ = 2 * math.pi * r
    out = panel(W, H, "LANGUAGE DONUT", "real bytes across %d repos" % repo_count)
    out.insert(1, "<filter id='dglow' x='-40%' y='-40%' width='180%' height='180%'>"
                  "<feGaussianBlur stdDeviation='3' result='b'/><feMerge><feMergeNode in='b'/>"
                  "<feMergeNode in='SourceGraphic'/></feMerge></filter>")
    out.append("<style><![CDATA[.spin{transform-origin:%dpx %dpx;animation:sp 26s linear infinite}"
               "@keyframes sp{to{transform:rotate(360deg)}}]]></style>" % (int(cx), int(cy)))
    off = 0.0
    for i, (lang, val) in enumerate(top):
        seg = (val / total) * circ
        col = PAL[i % len(PAL)]
        out.append("<circle cx='%.1f' cy='%.1f' r='%.1f' fill='none' stroke='%s' stroke-width='%.1f' "
                   "stroke-dasharray='%.2f %.2f' stroke-dashoffset='%.2f' transform='rotate(-90 %.1f %.1f)'/>"
                   % (cx, cy, r, col, sw, seg, circ - seg, -off, cx, cy))
        off += seg
    out.append("<circle class='spin' cx='%.1f' cy='%.1f' r='%.1f' fill='none' stroke='#8B5CF6' "
               "stroke-width='1.4' stroke-dasharray='4 12' opacity='0.7'/>" % (cx, cy, r + sw / 2 + 12))
    out.append("<circle cx='%.1f' cy='%.1f' r='%.1f' fill='#050a12' stroke='#00E5FF' stroke-width='1.4' filter='url(#dglow)'/>"
               % (cx, cy, r - sw / 2 - 10))
    out.append("<text x='%.1f' y='%.1f' text-anchor='middle' font-family=\"%s\" font-size='24' font-weight='700' fill='#E6F1FF'>%s</text>"
               % (cx, cy, MONO, human(total)))
    out.append("<text x='%.1f' y='%.1f' text-anchor='middle' font-family=\"%s\" font-size='10.5' letter-spacing='3' fill='#5A6B85'>OF CODE</text>"
               % (cx, cy + 20, MONO))
    lx, ly = 566, 96
    for i, (lang, val) in enumerate(top):
        y = ly + i * 34
        out.append("<rect x='%d' y='%d' width='14' height='14' rx='3' fill='%s'/>" % (lx, y - 11, PAL[i % len(PAL)]))
        out.append("<text x='%d' y='%d' font-family=\"%s\" font-size='13' fill='#dce9f7'>%s</text>" % (lx + 24, y, MONO, g.esc(lang)))
        out.append("<text x='%d' y='%d' text-anchor='end' font-family=\"%s\" font-size='12' fill='#8ea3bd'>%.1f%%</text>"
                   % (W - 40, y, MONO, 100.0 * val / total))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------- constellation
def build_constellation(repos):
    W, H = 1280, 500
    nodes = []
    for r in repos:
        if r.get("fork") or r["name"] == USER:
            continue
        h = int(hashlib.md5(r["name"].encode("utf-8")).hexdigest(), 16)
        ang = (h % 360) * math.pi / 180.0
        rad = 70 + (h >> 9) % 470
        x = W / 2.0 + math.cos(ang) * rad * 1.35
        y = H / 2.0 + math.sin(ang) * rad * 0.55
        st = int(r.get("stargazers_count", 0))
        lang = r.get("language") or "Other"
        col = PAL[int(hashlib.md5(lang.encode()).hexdigest(), 16) % len(PAL)]
        nodes.append({"x": x, "y": y, "s": 1.4 + min(4.2, math.log1p(st) * 1.4),
                      "c": col, "n": r["name"], "st": st, "lang": lang})
    out = panel(W, H, "REPOSITORY CONSTELLATION", "%d tracked repos" % len(nodes))
    out.append("<style><![CDATA[.tw{animation:tw 3.6s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.35}50%{opacity:1}}]]></style>")
    lines = 0
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if lines >= 340:
                break
            a, b = nodes[i], nodes[j]
            if a["lang"] != b["lang"]:
                continue
            if math.hypot(a["x"] - b["x"], a["y"] - b["y"]) < 130:
                out.append("<line x1='%.1f' y1='%.1f' x2='%.1f' y2='%.1f' stroke='%s' stroke-width='0.5' opacity='0.18'/>"
                           % (a["x"], a["y"], b["x"], b["y"], a["c"]))
                lines += 1
    for nd in nodes:
        out.append("<circle class='tw' cx='%.1f' cy='%.1f' r='%.1f' fill='%s' style='animation-delay:%.2fs'/>"
                   % (nd["x"], nd["y"], nd["s"], nd["c"], (int(nd["x"]) % 30) / 10.0))
    for nd in sorted(nodes, key=lambda n: -n["st"])[:7]:
        out.append("<text x='%.1f' y='%.1f' font-family=\"%s\" font-size='10.5' fill='#8ea3bd'>%s</text>"
                   % (nd["x"] + 8, nd["y"] - 6, MONO, g.esc(nd["n"])))
    langs = []
    for nd in nodes:
        if nd["lang"] not in langs:
            langs.append(nd["lang"])
    for i, lg in enumerate(langs[:6]):
        x = 40 + i * 150
        col = PAL[int(hashlib.md5(lg.encode()).hexdigest(), 16) % len(PAL)]
        out.append("<circle cx='%d' cy='%d' r='5' fill='%s'/>" % (x, H - 30, col))
        out.append("<text x='%d' y='%d' font-family=\"%s\" font-size='11' fill='#5A6B85'>%s</text>" % (x + 12, H - 26, MONO, g.esc(lg)))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------ activity
ICON = {"PushEvent": ("PUSH", "#00E5FF"), "PullRequestEvent": ("PR", "#8B5CF6"),
        "IssuesEvent": ("ISSUE", "#FFB300"), "IssueCommentEvent": ("COMMENT", "#22C55E"),
        "CreateEvent": ("CREATE", "#00A3FF"), "WatchEvent": ("STAR", "#FFB300"),
        "ReleaseEvent": ("RELEASE", "#FF1F4B"), "ForkEvent": ("FORK", "#FF6B9D"),
        "DeleteEvent": ("DELETE", "#5A6B85"), "PublicEvent": ("PUBLIC", "#22C55E")}


def ago(iso):
    try:
        t = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return ""
    s = int((datetime.now(timezone.utc) - t).total_seconds())
    if s < 3600:
        return "%dm ago" % (s // 60)
    if s < 86400:
        return "%dh ago" % (s // 3600)
    if s < 2592000:
        return "%dd ago" % (s // 86400)
    return "%dmo ago" % (s // 2592000)


def build_activity(events):
    rows = events[:9]
    W = 980
    H = 72 + max(1, len(rows)) * 36 + 20
    out = panel(W, H, "ACTIVITY STREAM", "live from the events API")
    out.append("<style><![CDATA[.bl{animation:bl 1.6s ease-in-out infinite}@keyframes bl{0%,100%{opacity:.4}50%{opacity:1}}]]></style>")
    out.append("<circle class='bl' cx='%d' cy='%d' r='5' fill='#22C55E'/>" % (W - 60, 34))
    if not rows:
        out.append("<text x='34' y='100' font-family=\"%s\" font-size='13' fill='#5A6B85'>no public events yet</text>" % MONO)
    for i, e in enumerate(rows):
        typ = e.get("type", "")
        label, col = ICON.get(typ, (typ.replace("Event", "").upper()[:8] or "EVENT", "#5A6B85"))
        repo = ((e.get("repo") or {}).get("name") or "").split("/")[-1]
        y = 84 + i * 36
        out.append("<rect x='34' y='%d' width='74' height='22' rx='6' fill='#070c16' stroke='%s' stroke-opacity='0.6'/>"
                   % (y - 16, col))
        out.append("<text x='%d' y='%d' text-anchor='middle' font-family=\"%s\" font-size='10.5' fill='%s'>%s</text>"
                   % (71, y, MONO, col, g.esc(label)))
        out.append("<text x='122' y='%d' font-family=\"%s\" font-size='12.5' fill='#dce9f7'>%s</text>" % (y, MONO, g.esc(repo)))
        out.append("<text x='%d' y='%d' text-anchor='end' font-family=\"%s\" font-size='11.5' fill='#5A6B85'>%s</text>"
                   % (W - 34, y, MONO, g.esc(ago(e.get("created_at", "")))))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------- traffic
def build_traffic(views, clones, runs):
    W, H = 980, 320
    out = panel(W, H, "TRAFFIC + BUILD BOARD", "repo telemetry (push-access only)")
    vc = (views or {}).get("count", 0)
    vu = (views or {}).get("uniques", 0)
    cc = (clones or {}).get("count", 0)
    cu = (clones or {}).get("uniques", 0)
    cards = [("VIEWS 14d", "%d" % vc, "#00E5FF"), ("UNIQUE VISITORS", "%d" % vu, "#8B5CF6"),
             ("CLONES 14d", "%d" % cc, "#FFB300"), ("UNIQUE CLONERS", "%d" % cu, "#22C55E")]
    for i, (lbl, val, col) in enumerate(cards):
        x = 34 + i * 232
        out.append("<rect x='%d' y='64' width='216' height='70' rx='10' fill='#070c16' stroke='#16203a'/>" % (x,))
        out.append("<rect x='%d' y='72' width='4' height='54' rx='2' fill='%s'/>" % (x, col))
        out.append("<text x='%d' y='92' font-family=\"%s\" font-size='10.5' letter-spacing='2' fill='#5A6B85'>%s</text>" % (x + 18, MONO, g.esc(lbl)))
        out.append("<text x='%d' y='122' font-family=\"%s\" font-size='24' font-weight='700' fill='%s'>%s</text>" % (x + 18, MONO, col, g.esc(val)))
    series = (views or {}).get("views", [])[-14:]
    base_y, maxv = 268, max([p.get("count", 0) for p in series] + [1])
    bw = 56
    for i, p in enumerate(series):
        h = 60.0 * p.get("count", 0) / maxv
        x = 40 + i * bw
        out.append("<rect x='%d' y='%.1f' width='34' height='%.1f' rx='4' fill='#00E5FF' opacity='0.75'/>" % (x, base_y - h, h))
    out.append("<text x='34' y='%d' font-family=\"%s\" font-size='11' fill='#5A6B85'>views / day</text>" % (base_y + 20, MONO))
    out.append("<text x='%d' y='92' text-anchor='end' font-family=\"%s\" font-size='11.5' fill='#5A6B85'>LATEST BUILDS</text>" % (W - 34, MONO))
    for i, run in enumerate((runs or [])[:5]):
        y = 116 + i * 30
        concl = run.get("conclusion") or run.get("status") or "?"
        col = "#22C55E" if concl == "success" else ("#FFB300" if concl in ("queued", "in_progress") else "#FF1F4B")
        out.append("<circle cx='%d' cy='%d' r='5' fill='%s'/>" % (W - 40, y - 4, col))
        name = ((run.get("name") or "workflow"))[:32]
        out.append("<text x='%d' y='%d' text-anchor='end' font-family=\"%s\" font-size='11.5' fill='#8ea3bd'>%s</text>" % (W - 56, y, MONO, g.esc(name)))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------- wrapped
def build_wrapped(contrib, repos, agg):
    W, H = 980, 360
    year = (sorted(contrib)[-1][:4] if contrib else str(datetime.utcnow().year))
    total, longest, cur = g.streaks(contrib)
    active = sum(1 for _, c in contrib.values() if c > 0)
    busiest = max(contrib.items(), key=lambda kv: kv[1][1]) if contrib else ("-", (0, 0))
    top_lang = max(agg.items(), key=lambda kv: kv[1])[0] if agg else "-"
    top_repo = max(repos, key=lambda r: r.get("stargazers_count", 0)) if repos else {"name": "-"}
    cards = [("CONTRIBUTIONS", "%d" % total, "#22C55E"), ("ACTIVE DAYS", "%d" % active, "#00E5FF"),
             ("LONGEST STREAK", "%d d" % longest, "#FF1F4B"), ("TOP LANGUAGE", str(top_lang), "#8B5CF6"),
             ("BUSIEST DAY", str(busiest[0]), "#FFB300"), ("TOP REPO", str(top_repo.get("name", "-"))[:18], "#00A3FF")]
    out = panel(W, H, "GITHUB WRAPPED %s" % year, "your year in code")
    for i, (lbl, val, col) in enumerate(cards):
        x = 34 + (i % 3) * 306
        y = 66 + (i // 3) * 118
        out.append("<rect x='%d' y='%d' width='288' height='100' rx='12' fill='#070c16' stroke='#16203a'/>" % (x, y))
        out.append("<rect x='%d' y='%d' width='4' height='80' rx='2' fill='%s'/>" % (x, y + 10, col))
        out.append("<text x='%d' y='%d' font-family=\"%s\" font-size='11' letter-spacing='2' fill='#5A6B85'>%s</text>" % (x + 20, y + 30, MONO, g.esc(lbl)))
        out.append("<text x='%d' y='%d' font-family=\"%s\" font-size='21' font-weight='700' fill='%s'>%s</text>" % (x + 20, y + 70, MONO, col, g.esc(val)))
    out.append("<text x='%d' y='%d' text-anchor='middle' font-family=\"%s\" font-size='11' fill='#5A6B85'>regenerated automatically every day</text>" % (W // 2, H - 18, MONO))
    out.append("</svg>")
    return "\n".join(out)


# -------------------------------------------------------------------- galaxy
def build_galaxy(contrib):
    W, H = 980, 420
    rng = random.Random(42)
    out = panel(W, H, "CONTRIBUTION GALAXY", "one star per commit")
    out.append("<style><![CDATA[.st{animation:st 4s ease-in-out infinite}@keyframes st{0%,100%{opacity:.3}50%{opacity:1}}]]></style>")
    out.append("<ellipse cx='%d' cy='%d' rx='380' ry='150' fill='#8B5CF6' opacity='0.06'/>" % (W // 2, H // 2 + 10))
    stars = []
    for ds, (lvl, cnt) in sorted(contrib.items()):
        for _ in range(min(cnt, 10)):
            stars.append(lvl)
    n = max(1, len(stars))
    for i, lvl in enumerate(stars):
        rad = 40 + (i / float(n)) * 340 + rng.uniform(-16, 16)
        th = i * 0.55 + rng.uniform(-0.25, 0.25)
        x = W / 2.0 + math.cos(th) * rad
        y = H / 2.0 + 10 + math.sin(th) * rad * 0.42
        col = ["#12303f", "#0e7d92", "#00b8d4", "#00E5FF", "#E6F1FF"][min(lvl, 4)]
        r = 0.9 + lvl * 0.55 + rng.uniform(0, 0.7)
        out.append("<circle class='st' cx='%.1f' cy='%.1f' r='%.2f' fill='%s' style='animation-delay:%.2fs'/>"
                   % (x, y, r, col, rng.uniform(0, 3)))
    out.append("<circle cx='%d' cy='%d' r='26' fill='#050a12' stroke='#00E5FF' stroke-width='1.5'/>" % (W // 2, H // 2 + 10))
    out.append("<text x='%d' y='%d' text-anchor='middle' font-family=\"%s\" font-size='12' font-weight='700' fill='#00E5FF'>CORE</text>" % (W // 2, H // 2 + 14, MONO))
    out.append("</svg>")
    return "\n".join(out)


# ----------------------------------------------------------------- guestbook
def build_guestbook(comments):
    W = 980
    rows = comments[:8]
    H = 96 + max(1, len(rows)) * 58
    out = panel(W, H, "GUESTBOOK WALL", "sign it on the pinned issue")
    if not rows:
        out.append("<text x='34' y='104' font-family=\"%s\" font-size='13' fill='#8ea3bd'>No signatures yet. Be the first to sign the guestbook issue.</text>" % MONO)
    for i, c in enumerate(rows):
        y = 84 + i * 58
        login = ((c.get("user") or {}).get("login") or "anon")
        body = (c.get("body") or "").replace("\r", " ").replace("\n", " ").strip()
        if len(body) > 96:
            body = body[:93] + "..."
        col = PAL[int(hashlib.md5(login.encode()).hexdigest(), 16) % len(PAL)]
        out.append("<rect x='34' y='%d' width='%d' height='48' rx='9' fill='#070c16' stroke='#16203a'/>" % (y - 18, W - 68))
        out.append("<rect x='34' y='%d' width='4' height='48' rx='2' fill='%s'/>" % (y - 18, col))
        out.append("<text x='52' y='%d' font-family=\"%s\" font-size='12' font-weight='700' fill='%s'>@%s</text>"
                   % (y - 1, MONO, col, g.esc(login)))
        out.append("<text x='52' y='%d' font-family=\"%s\" font-size='11.5' fill='#8ea3bd'>%s</text>" % (y + 17, MONO, g.esc(body)))
        out.append("<text x='%d' y='%d' text-anchor='end' font-family=\"%s\" font-size='10.5' fill='#5A6B85'>%s</text>"
                   % (W - 52, y - 1, MONO, g.esc((c.get("created_at") or "")[:10])))
    out.append("</svg>")
    return "\n".join(out)


def build_reactions(react):
    W, H = 700, 150
    total = int((react or {}).get("total_count", 0))
    out = panel(W, H, "REACTION METER", "would you hire me?")
    out.append("<text x='%d' y='%d' text-anchor='middle' font-family=\"%s\" font-size='46' font-weight='700' fill='#FFB300'>%d</text>" % (W // 2, 104, MONO, total))
    out.append("<text x='%d' y='%d' text-anchor='middle' font-family=\"%s\" font-size='11.5' fill='#5A6B85'>reactions on the pinned issue</text>" % (W // 2, 128, MONO))
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------ data api
def build_data(repos, followers, following, contrib, agg):
    total, longest, cur = g.streaks(contrib)
    top = sorted([r for r in repos if not r.get("fork")], key=lambda r: -r.get("stargazers_count", 0))[:12]
    data = {
        "user": USER,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {"repos": len(repos), "followers": followers, "following": following,
                  "stars": sum(r.get("stargazers_count", 0) for r in repos),
                  "contributions": total, "current_streak": cur, "longest_streak": longest},
        "languages": [{"name": k, "bytes": v} for k, v in sorted(agg.items(), key=lambda kv: -kv[1])[:12]],
        "repos": [{"name": r["name"], "description": r.get("description"), "language": r.get("language"),
                   "stars": r.get("stargazers_count", 0), "url": r.get("html_url")} for r in top],
    }
    wfile(os.path.join("docs", "data.json"), json.dumps(data, indent=2))


# --------------------------------------------------------------------- blog
def _inline(t):
    t = g.esc(t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", "<a href='\\2'>\\1</a>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", "<strong>\\1</strong>", t)
    t = re.sub(r"`([^`]+)`", "<code>\\1</code>", t)
    t = re.sub(r"\*([^*]+)\*", "<em>\\1</em>", t)
    return t


def md(text):
    out, in_code, in_list = [], False, False
    for ln in text.split("\n"):
        if ln.startswith("```"):
            out.append("</code></pre>" if in_code else "<pre><code>")
            in_code = not in_code
            continue
        if in_code:
            out.append(g.esc(ln))
            continue
        s = ln.strip()
        if not s:
            if in_list:
                out.append("</ul>")
                in_list = False
            continue
        if s.startswith("### "):
            out.append("<h3>" + _inline(s[4:]) + "</h3>")
        elif s.startswith("## "):
            out.append("<h2>" + _inline(s[3:]) + "</h2>")
        elif s.startswith("# "):
            out.append("<h1>" + _inline(s[2:]) + "</h1>")
        elif s.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + _inline(s[2:]) + "</li>")
        else:
            out.append("<p>" + _inline(s) + "</p>")
    if in_list:
        out.append("</ul>")
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


BLOG_CSS = ("body{margin:0;background:#000;color:#dce9f7;font:15px/1.7 ui-monospace,Consolas,monospace}"
            "header{border-bottom:1px solid #16203a;background:#05070d;padding:16px 22px;position:sticky;top:0}"
            "header a{color:#00E5FF;text-decoration:none;letter-spacing:2px;font-weight:700}"
            "main{max-width:780px;margin:0 auto;padding:34px 22px 80px}"
            "h1{letter-spacing:2px} h2{margin-top:34px;color:#00E5FF} h3{color:#8B5CF6}"
            "a{color:#00E5FF} code{background:#0b1220;padding:2px 6px;border-radius:5px;color:#FFB300}"
            "pre{background:#05070d;border:1px solid #16203a;border-radius:12px;padding:16px;overflow:auto}"
            "ul{padding-left:20px} .d{color:#5A6B85;margin-right:10px} .posts li{margin:10px 0;list-style:none}"
            ".meta{color:#5A6B85;font-size:12.5px;margin-bottom:22px}")


def blog_shell(title, body, date):
    return ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'/>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
            "<title>" + g.esc(title) + " · Vikram</title><style>" + BLOG_CSS + "</style></head><body>"
            "<header><a href='../'>VIKRAM</a> &nbsp;·&nbsp; <a href='./'>notes</a></header>"
            "<main><h1>" + g.esc(title) + "</h1>"
            + ("<div class='meta'>" + g.esc(date) + "</div>" if date else "")
            + body + "</main></body></html>")


def build_blog():
    posts_dir = os.path.join("docs", "blog", "posts")
    if not os.path.isdir(posts_dir):
        return []
    entries = []
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        raw = open(os.path.join(posts_dir, fn), encoding="utf-8").read()
        m = re.search(r"^#\s+(.+)$", raw, re.M)
        title = m.group(1).strip() if m else fn
        dm = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", fn)
        date = dm.group(1) if dm else ""
        slug = dm.group(2) if dm else fn[:-3]
        wfile(os.path.join("docs", "blog", slug + ".html"), blog_shell(title, md(raw), date))
        entries.append({"title": title, "date": date, "slug": slug, "raw": raw})
    entries.sort(key=lambda e: e["date"], reverse=True)
    lis = "".join("<li><span class='d'>" + g.esc(e["date"]) + "</span><a href='" + e["slug"] + ".html'>" + g.esc(e["title"]) + "</a></li>" for e in entries)
    wfile(os.path.join("docs", "blog", "index.html"), blog_shell("Notes", "<ul class='posts'>" + lis + "</ul>", ""))
    items = []
    for e in entries:
        body = re.sub(r"^#\s+.+$", "", e["raw"], count=1, flags=re.M).strip()
        desc = _inline(body.split("\n\n")[0][:200]) if body else ""
        items.append("<item><title>" + g.esc(e["title"]) + "</title>"
                     "<link>https://vikrambtech2025-png.github.io/vikrambtech2025-png/blog/" + e["slug"] + ".html</link>"
                     "<guid>vikram-" + e["slug"] + "</guid><pubDate>" + g.esc(e["date"]) + "</pubDate>"
                     "<description>" + desc + "</description></item>")
    feed = ("<?xml version='1.0' encoding='UTF-8'?><rss version='2.0'><channel>"
            "<title>Vikram — Notes</title><link>https://vikrambtech2025-png.github.io/vikrambtech2025-png/blog/</link>"
            "<description>AI/ML engineering notes</description>" + "".join(items) + "</channel></rss>")
    wfile(os.path.join("docs", "feed.xml"), feed)
    return entries


# ----------------------------------------------------------------- og card
def build_og():
    W, H = 1200, 630
    out = [head(W, H, "Social card"),
           "<defs><linearGradient id='bg' x1='0' y1='0' x2='1' y2='1'>"
           "<stop offset='0' stop-color='#000000'/><stop offset='0.6' stop-color='#05070d'/>"
           "<stop offset='1' stop-color='#0a0f1a'/></linearGradient>"
           "<linearGradient id='rz' x1='0' y1='0' x2='1' y2='0'>"
           "<stop offset='0' stop-color='#00E5FF'/><stop offset='0.5' stop-color='#8B5CF6'/>"
           "<stop offset='1' stop-color='#FF1F4B'/></linearGradient></defs>",
           "<rect width='%d' height='%d' fill='url(#bg)'/>" % (W, H),
           "<rect x='40' y='40' width='%d' height='%d' rx='18' fill='none' stroke='#16203a' stroke-width='2'/>" % (W - 80, H - 80),
           "<text x='%d' y='300' text-anchor='middle' font-family=\"%s\" font-size='120' font-weight='700' letter-spacing='14' fill='#E6F1FF'>VIKRAM</text>" % (W // 2, MONO),
           "<text x='%d' y='360' text-anchor='middle' font-family=\"%s\" font-size='26' letter-spacing='9' fill='#00E5FF'>AI / ML ENGINEER</text>" % (W // 2, MONO),
           "<text x='%d' y='410' text-anchor='middle' font-family=\"%s\" font-size='16' fill='#8ea3bd'>IDEALISTIC AI AGENTS SOLVING REAL-WORLD PROBLEMS</text>" % (W // 2, MONO),
           "<rect x='%d' y='470' width='520' height='3' rx='1.5' fill='url(#rz)'/>" % ((W - 520) // 2),
           "<text x='%d' y='520' text-anchor='middle' font-family=\"%s\" font-size='15' fill='#5A6B85'>github.com/vikrambtech2025-png</text>" % (W // 2, MONO),
           "</svg>"]
    wfile(os.path.join("docs", "og-card.svg"), "\n".join(out))


# ----------------------------------------------------------------- self-hosted badges
#  100% self-hosted replacement for shields.io — rendered here, not fetched.
BADGE_SKILLS = [
    ("Python", "#00E5FF"), ("LangChain", "#22C55E"), ("LangGraph", "#22C55E"),
    ("PyTorch", "#FF1F4B"), ("Hugging Face", "#FFB300"), ("ColPali", "#FF1F4B"),
    ("FAISS", "#00E5FF"), ("Qdrant", "#FF1F4B"), ("FastAPI", "#00E5FF"),
    ("OpenCV", "#8B5CF6"), ("Unsloth", "#00E5FF"), ("Streamlit", "#FF1F4B"),
]


def write_badge(name, content):
    d = os.path.join("assets", "badges")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("wrote", p)


def _width(s, fs, cw, pad):
    return int(len(s) * cw) + pad


def two_tone(label, value, color, label_color="#dce9f7", value_color="#ffffff"):
    fs, cw, pad, h = 11, 6.7, 22, 22
    lw = _width(label, fs, cw, pad)
    rw = _width(value, fs, cw, pad)
    total = lw + rw
    o = [g.svg_header(total, h, "%s: %s" % (label, value)),
         "<defs><linearGradient id='gl' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='.12'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<g clip-path='url(#cp)'>",
         "<rect width='%d' height='%d' fill='#0b1220'/>" % (total, h),
         "<rect x='%d' width='%d' height='%d' fill='%s'/>" % (lw, rw, h, color),
         "<rect width='%d' height='%d' fill='url(#gl)'/>" % (total, h),
         "</g>",
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='%s' stroke-opacity='.8'/>"
         % (total - 1, h - 1, color),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' fill='%s'>%s</text>"
         % (lw / 2.0, MONO, fs, label_color, g.esc(label)),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' fill='%s'>%s</text>"
         % (lw + rw / 2.0, MONO, fs, value_color, g.esc(value)),
         "</svg>"]
    return "\n".join(o)


def skill_pill(name, color):
    fs, cw, pad, h = 11, 6.7, 22, 22
    total = _width(name, fs, cw, pad)
    o = [g.svg_header(total, h, name),
         "<defs><linearGradient id='gl' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='.12'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<g clip-path='url(#cp)'>",
         "<rect width='%d' height='%d' fill='#0b1220'/>" % (total, h),
         "<rect width='3' height='%d' fill='%s'/>" % (h, color),
         "<rect width='%d' height='%d' fill='url(#gl)'/>" % (total, h),
         "</g>",
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='%s' stroke-opacity='.85'/>"
         % (total - 1, h - 1, color),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' fill='%s'>%s</text>"
         % (total / 2.0 + 1, MONO, fs, color, g.esc(name)),
         "</svg>"]
    return "\n".join(o)


def filled(text, color, text_color="#000000"):
    fs, cw, pad, h = 11, 6.7, 26, 22
    total = _width(text, fs, cw, pad)
    o = [g.svg_header(total, h, text),
         "<defs><linearGradient id='fg' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='.22'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<g clip-path='url(#cp)'>",
         "<rect width='%d' height='%d' fill='%s'/>" % (total, h, color),
         "<rect width='%d' height='%d' fill='url(#fg)'/>" % (total, h),
         "</g>",
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='#000000' stroke-opacity='.2'/>"
         % (total - 1, h - 1),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' font-weight='700' fill='%s'>%s</text>"
         % (total / 2.0, MONO, fs, text_color, g.esc(text)),
         "</svg>"]
    return "\n".join(o)


def achievement(name, note, color="#FFB300"):
    # reversed two-tone: filled name segment on the left, dark note segment on the right
    # + a gold shimmer sweep on loop so earned badges visibly glint
    fs, cw, pad, h = 11, 6.7, 22, 22
    lw = _width(name, fs, cw, pad) + 8
    rw = _width(note, fs, cw, pad)
    total = lw + rw
    o = [g.svg_header(total, h, "Achievement: %s" % name),
         "<defs><linearGradient id='gl' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='.22'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<linearGradient id='shine' x1='0' y1='0' x2='1' y2='0'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='0'/>"
         "<stop offset='.5' stop-color='#ffffff' stop-opacity='.5'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<g clip-path='url(#cp)'>",
         "<rect width='%d' height='%d' fill='#0b1220'/>" % (total, h),
         "<rect width='%d' height='%d' fill='%s'/>" % (lw, h, color),
         "<rect width='%d' height='%d' fill='url(#gl)'/>" % (total, h),
         "</g>",
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='%s' stroke-opacity='.9'/>"
         % (total - 1, h - 1, color),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' font-weight='700' fill='#000000'>%s</text>"
         % (lw / 2.0, MONO, fs, g.esc(name)),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' fill='%s'>%s</text>"
         % (lw + rw / 2.0, MONO, fs, color, g.esc(note)),
         "<g clip-path='url(#cp)'><rect x='-40' y='0' width='32' height='%d' fill='url(#shine)'>" % h,
         "<animate attributeName='x' values='-40;%d' dur='3.4s' begin='-1.1s' repeatCount='infinite'/>" % (total + 10),
         "</rect></g>",
         "</svg>"]
    return "\n".join(o)


def status_chip(text, color, text_color="#000000"):
    # filled chip + pulsing LED dot — the "always on" signal
    fs, cw, pad, h = 11, 6.7, 40, 22
    total = _width(text, fs, cw, pad)
    o = [g.svg_header(total, h, text),
         "<defs><linearGradient id='fg' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='.22'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>"
         "<clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<g clip-path='url(#cp)'>",
         "<rect width='%d' height='%d' fill='%s'/>" % (total, h, color),
         "<rect width='%d' height='%d' fill='url(#fg)'/>" % (total, h),
         "<circle cx='13' cy='11' r='3.5' fill='none' stroke='#0b1220' stroke-width='1.6'>"
         "<animate attributeName='r' values='3.5;10' dur='1.7s' repeatCount='infinite'/>"
         "<animate attributeName='stroke-opacity' values='.85;0' dur='1.7s' repeatCount='infinite'/>"
         "</circle>",
         "<circle cx='13' cy='11' r='3.5' fill='#0b1220'/>",
         "</g>",
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='#000000' stroke-opacity='.2'/>"
         % (total - 1, h - 1),
         "<text x='%.1f' y='15' text-anchor='middle' font-family=\"%s\" font-size='%d' font-weight='700' fill='%s'>%s</text>"
         % (total / 2.0 + 10, MONO, fs, text_color, g.esc(text)),
         "</svg>"]
    return "\n".join(o)


def build_badges(agg, contrib, followers, repos):
    total, longest, cur = g.streaks(contrib)
    top_lang = max(agg.items(), key=lambda kv: kv[1])[0] if agg else "-"
    pub = sum(1 for r in repos if not r.get("fork"))

    # status chip — the one-liner that says what you're about (with live LED)
    write_badge("status-agents.svg", status_chip("building idealistic AI agents for real-world problems", "#00E5FF"))

    # GitHub achievement badge — earned, shown in the README too
    write_badge("achievement-yolo.svg", achievement("YOLO", "merged without review"))

    # live data badges
    data = [("contributions", str(total), "#22C55E"),
            ("current streak", "%dd" % cur, "#FF1F4B"),
            ("longest streak", "%dd" % longest, "#00E5FF"),
            ("public repos", str(pub), "#8B5CF6"),
            ("followers", str(followers), "#00E5FF"),
            ("top language", str(top_lang), "#FFB300")]
    for label, value, col in data:
        write_badge("data-%s.svg" % label.replace(" ", "-"), two_tone(label, value, col))

    # skill pills
    for name, col in BADGE_SKILLS:
        write_badge("skill-%s.svg" % name.lower().replace(" ", "-"), skill_pill(name, col))


# ------------------------------------------------- animated README art (loops)
#  SMIL animation drawn here. GitHub serves these SVGs through camo and the
#  browser plays the loops inside plain <img> tags — no JS, no third parties.
#  Curated, deterministic (fixed seeds) so daily CI runs don't churn the art.
ANIM_SKILLS = [  # name, color, level 0-100 (curated showcase values)
    ("Python", "#00E5FF", 96), ("LangChain", "#22C55E", 92), ("LangGraph", "#22C55E", 88),
    ("PyTorch", "#FF1F4B", 85), ("Hugging Face", "#FFB300", 90), ("ColPali", "#FF1F4B", 82),
    ("FAISS", "#00E5FF", 84), ("Qdrant", "#FF1F4B", 80), ("FastAPI", "#00E5FF", 87),
    ("OpenCV", "#8B5CF6", 78), ("Unsloth", "#00E5FF", 74), ("Streamlit", "#FF1F4B", 81),
]


def build_matrix_header():
    W, H = 800, 160
    rnd = random.Random(7)
    glyphs = "0123456789ABCDEF#$%&*+<>?"
    row_h = 17
    o = [g.svg_header(W, H, "Animated matrix rain: VIKRAM SATHYA"),
         "<defs>",
         "<linearGradient id='mg' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#0d5c40'/><stop offset='1' stop-color='#22C55E'/></linearGradient>",
         "<linearGradient id='tf' x1='0' y1='0' x2='0' y2='1'>"
         "<stop offset='0' stop-color='#02040a'/><stop offset='1' stop-color='#02040a' stop-opacity='0'/></linearGradient>",
         "<linearGradient id='bf' x1='0' y1='1' x2='0' y2='0'>"
         "<stop offset='0' stop-color='#02040a'/><stop offset='1' stop-color='#02040a' stop-opacity='0'/></linearGradient>",
         "</defs>",
         "<rect width='%d' height='%d' fill='#02040a'/>" % (W, H)]
    for i in range(W // 26):
        x = 13 + i * 26
        n = rnd.randint(10, 15)
        chars = [rnd.choice(glyphs) for _ in range(n)]
        dur = rnd.uniform(2.8, 6.4)
        delay = -rnd.uniform(0, dur)
        op = rnd.uniform(.35, .9)
        inner = []
        for k, ch in enumerate(chars):
            fill = "#eafff4" if k == 0 else "url(#mg)"
            inner.append("<text x='0' y='%d' text-anchor='middle' fill='%s'>%s</text>"
                         % ((k + 1) * row_h, fill, g.esc(ch)))
        o.append("<g transform='translate(%d,0)' opacity='%.2f'><g>"
                 "<animateTransform attributeName='transform' type='translate' values='0 %d; 0 %d' "
                 "dur='%.1fs' begin='%.1fs' repeatCount='infinite'/>%s</g></g>"
                 % (x, op, -n * row_h, H + row_h, dur, delay, "".join(inner)))
    o.append("<rect width='%d' height='28' fill='url(#tf)'/>" % W)
    o.append("<rect y='%d' width='%d' height='28' fill='url(#bf)'/>" % (H - 28, W))
    o.append("<rect x='170' y='44' width='460' height='72' rx='6' fill='#02040a' fill-opacity='.92' stroke='#00E5FF' stroke-opacity='.8'/>")
    o.append("<text x='400' y='76' text-anchor='middle' font-family=\"%s\" font-size='24' font-weight='700' fill='#00E5FF'>VIKRAM SATHYA</text>" % MONO)
    o.append("<text x='400' y='99' text-anchor='middle' font-family=\"%s\" font-size='11' fill='#22C55E'>// idealistic AI agents &#183; real-world problems</text>" % MONO)
    o.append("</svg>")
    return "\n".join(o)


def build_typewriter():
    text = "i love to create ai idealistic agents that solves real world problem"
    fs, cw, x0 = 13, 7.9, 18
    tw = int(len(text) * cw)
    W, H = tw + 2 * x0 + 16, 40
    o = [g.svg_header(W, H, "Typewriter: " + text),
         "<defs><mask id='wipe'>",
         "<rect x='%d' y='4' width='%d' height='32' fill='#000'/>" % (x0, tw),
         "<rect x='%d' y='4' height='32' fill='#fff'>" % x0,
         "<animate attributeName='width' values='0;0;%d;%d;0' keyTimes='0;0.05;0.62;0.92;1' dur='9s' repeatCount='infinite'/>" % (tw, tw),
         "</rect></mask></defs>",
         "<rect width='%d' height='%d' fill='#04070d'/>" % (W, H),
         "<rect x='.5' y='.5' width='%d' height='%d' rx='6' fill='none' stroke='#22C55E' stroke-opacity='.55'/>" % (W - 1, H - 1),
         "<text x='%d' y='26' font-family=\"%s\" font-size='%d' fill='#22C55E' mask='url(#wipe)'>%s</text>"
         % (x0, MONO, fs, g.esc(text)),
         "<rect x='%d' y='9' width='8' height='22' fill='#22C55E'>" % (x0 + 4),
         "<animate attributeName='x' values='%d;%d;%d;%d;%d' keyTimes='0;0.05;0.62;0.92;1' dur='9s' repeatCount='infinite'/>"
         % (x0 + 4, x0 + 4, x0 + tw - 4, x0 + tw - 4, x0 + 4),
         "<animate attributeName='opacity' values='1;1;0;1' keyTimes='0;0.45;0.5;1' dur='0.9s' repeatCount='infinite'/>",
         "</rect>",
         "</svg>"]
    return "\n".join(o)


def build_ecg():
    W, H = 800, 64
    d = "M0 34 H160 l12 -20 l10 40 l12 -20 H330 l12 -26 l10 52 l12 -26 H540 l12 -20 l10 40 l12 -20 H800"
    o = [g.svg_header(W, H, "Animated ECG heartbeat divider"),
         "<defs><filter id='glow' x='-20%' y='-40%' width='140%' height='180%'>"
         "<feGaussianBlur stdDeviation='2.2' result='b'/>"
         "<feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge></filter></defs>",
         "<path d='%s' stroke='#FF1F4B' stroke-opacity='.16' stroke-width='2' fill='none'/>" % d,
         "<path d='%s' pathLength='1000' stroke='#FF1F4B' stroke-width='2.4' fill='none' stroke-linejoin='round' filter='url(#glow)'>" % d,
         "<animate attributeName='stroke-dasharray' values='0 1000; 260 1000; 1000 0' keyTimes='0;0.25;0.62' dur='2.6s' repeatCount='infinite'/>",
         "<animate attributeName='stroke-opacity' values='1;1;1;0' keyTimes='0;0.7;0.9;1' dur='2.6s' repeatCount='infinite'/>",
         "</path>",
         "<circle r='3.4' fill='#FF1F4B' filter='url(#glow)'>",
         "<animateMotion path='%s' dur='2.6s' keyPoints='0;1' keyTimes='0;0.62' repeatCount='infinite'/>" % d,
         "<animate attributeName='opacity' values='0;1;1;0' keyTimes='0;0.04;0.62;0.7' dur='2.6s' repeatCount='infinite'/>",
         "</circle>",
         "<text x='%d' y='15' text-anchor='end' font-family=\"%s\" font-size='9' fill='#FF1F4B' opacity='.8'>BPM 72 // AGENT ONLINE</text>" % (W - 12, MONO),
         "</svg>"]
    return "\n".join(o)


def build_radar():
    W = H = 200
    o = [g.svg_header(W, H, "Animated radar scan"),
         "<defs><radialGradient id='swg' cx='.5' cy='.5' r='.5'>"
         "<stop offset='0' stop-color='#00E5FF' stop-opacity='.5'/>"
         "<stop offset='1' stop-color='#00E5FF' stop-opacity='0'/></radialGradient></defs>",
         "<circle cx='100' cy='100' r='93' fill='#04070d' stroke='#00E5FF' stroke-opacity='.6'/>",
         "<circle cx='100' cy='100' r='31' fill='none' stroke='#00E5FF' stroke-opacity='.18'/>",
         "<circle cx='100' cy='100' r='61' fill='none' stroke='#00E5FF' stroke-opacity='.18'/>",
         "<line x1='100' y1='7' x2='100' y2='193' stroke='#00E5FF' stroke-opacity='.12'/>",
         "<line x1='7' y1='100' x2='193' y2='100' stroke='#00E5FF' stroke-opacity='.12'/>",
         "<g><path d='M100 100 L100 12 A88 88 0 0 1 168 44 Z' fill='url(#swg)'/>"
         "<animateTransform attributeName='transform' type='rotate' from='0 100 100' to='360 100 100' dur='4s' repeatCount='infinite'/></g>"]
    rnd = random.Random(11)
    for i in range(4):
        ang = rnd.uniform(0, 360)
        rad = rnd.uniform(25, 80)
        bx = 100 + rad * math.sin(math.radians(ang))
        by = 100 - rad * math.cos(math.radians(ang))
        o.append("<circle cx='%.1f' cy='%.1f' r='2.6' fill='#22C55E'>"
                 "<animate attributeName='opacity' values='0;1;1;0' keyTimes='0;.05;.18;.26' dur='4s' begin='-%.2fs' repeatCount='infinite'/>"
                 "</circle>" % (bx, by, ang / 360.0 * 4.0))
    o.append("<circle cx='100' cy='100' r='4' fill='none' stroke='#FF1F4B' stroke-opacity='.9'>"
             "<animate attributeName='r' values='4;16' dur='2s' repeatCount='infinite'/>"
             "<animate attributeName='stroke-opacity' values='.9;0' dur='2s' repeatCount='infinite'/>"
             "</circle>")
    o.append("<circle cx='100' cy='100' r='2.6' fill='#FF1F4B'/>")
    o.append("</svg>")
    return "\n".join(o)


def build_wordcycle():
    words = ["idealistic ai agents", "rag pipelines", "vision models",
             "colpali search", "agentic evals"]
    fs, cw, pad, h = 12, 7.9, 48, 32
    total = int(max(len(w) for w in words) * cw) + pad
    o = [g.svg_header(total, h, "Cycling focus: " + ", ".join(words)),
         "<defs><clipPath id='cp'><rect width='%d' height='%d' rx='4'/></clipPath></defs>" % (total, h),
         "<rect width='%d' height='%d' fill='#0b1220'/>" % (total, h),
         "<rect x='.5' y='.5' width='%d' height='%d' rx='3.5' fill='none' stroke='#8B5CF6' stroke-opacity='.85'/>"
         % (total - 1, h - 1),
         "<circle cx='12' cy='16' r='3.5' fill='none' stroke='#8B5CF6' stroke-width='1.5'>"
         "<animate attributeName='r' values='3.5;9' dur='1.7s' repeatCount='infinite'/>"
         "<animate attributeName='stroke-opacity' values='.9;0' dur='1.7s' repeatCount='infinite'/>"
         "</circle>",
         "<circle cx='12' cy='16' r='3.5' fill='#8B5CF6'/>",
         "<text x='26' y='20' font-family=\"%s\" font-size='%d' fill='#8B5CF6'>&#9656;</text>" % (MONO, fs)]
    for i, w in enumerate(words):
        o.append("<text x='44' y='21' font-family=\"%s\" font-size='%d' fill='#dce9f7' opacity='0'>%s"
                 "<animate attributeName='opacity' values='0;1;1;0' keyTimes='0;0.06;0.88;0.94' dur='2s' begin='%.1fs' repeatCount='infinite'/>"
                 "</text>" % (MONO, fs, g.esc(w), i * 2.0))
    o.append("</svg>")
    return "\n".join(o)


def build_skillbars():
    rows, gap_x, bar_w = 6, 370, 210
    W = 740
    top, rowh = 34, 26
    H = top + rows * rowh + 14
    o = [g.svg_header(W, H, "Animated live skill matrix"),
         "<defs>",
         "<linearGradient id='shine' x1='0' y1='0' x2='1' y2='0'>"
         "<stop offset='0' stop-color='#ffffff' stop-opacity='0'/>"
         "<stop offset='.5' stop-color='#ffffff' stop-opacity='.55'/>"
         "<stop offset='1' stop-color='#ffffff' stop-opacity='0'/></linearGradient>",
         "<clipPath id='tracks'>"]
    for i, (name, col, lvl) in enumerate(ANIM_SKILLS):
        cx = 20 + (i // rows) * gap_x
        cy = top + (i % rows) * rowh
        o.append("<rect x='%d' y='%d' width='%d' height='9' rx='4.5'/>" % (cx + 122, cy, bar_w))
    o.append("</clipPath></defs>")
    o.append("<text x='%d' y='20' text-anchor='middle' font-family=\"%s\" font-size='11' font-weight='700' fill='#00E5FF'>&#9889; LIVE SKILL MATRIX</text>" % (W // 2, MONO))
    for i, (name, col, lvl) in enumerate(ANIM_SKILLS):
        cx = 20 + (i // rows) * gap_x
        cy = top + (i % rows) * rowh
        fw = int(bar_w * lvl / 100.0)
        o.append("<text x='%d' y='%d' font-family=\"%s\" font-size='11' fill='%s'>%s</text>"
                 % (cx + 116, cy + 9, MONO, col, g.esc(name)))
        o.append("<rect x='%d' y='%d' width='%d' height='9' rx='4.5' fill='#0b1220' stroke='%s' stroke-opacity='.7'/>"
                 % (cx + 122, cy, bar_w, col))
        o.append("<rect x='%d' y='%d' width='%d' height='9' rx='4.5' fill='%s' fill-opacity='.85'/>"
                 % (cx + 122, cy, fw, col))
        o.append("<text x='%d' y='%d' font-family=\"%s\" font-size='9' fill='#5A6B85'>%d</text>"
                 % (cx + 122 + bar_w + 8, cy + 9, MONO, lvl))
        o.append("<g clip-path='url(#tracks)'><rect x='%d' y='%d' width='26' height='9' fill='url(#shine)'>"
                 "<animate attributeName='x' values='%d;%d' dur='2.8s' begin='%.2fs' repeatCount='infinite'/>"
                 "</rect></g>" % (cx + 122, cy, cx + 122 - 26, cx + 122 + bar_w, i * 0.19))
    o.append("</svg>")
    return "\n".join(o)


def build_animated():
    g.write("anim-matrix-header.svg", build_matrix_header())
    g.write("anim-typewriter.svg", build_typewriter())
    g.write("anim-ecg.svg", build_ecg())
    g.write("anim-radar.svg", build_radar())
    g.write("anim-wordcycle.svg", build_wordcycle())
    g.write("anim-skillbars.svg", build_skillbars())


# --------------------------------------------------------------------- main
def main():
    repos = g.fetch_all_repos()
    contrib = g.fetch_contributions()
    try:
        user = g.api("/users/" + USER)
        followers = user.get("followers", 0)
        following = user.get("following", 0)
    except Exception:
        followers = following = 0
    print("repos:", len(repos), "days:", len(contrib))

    agg = fetch_languages(repos)
    events = opt("/users/%s/events/public?per_page=30" % USER) or []
    views, clones = None, None
    try:
        views = opt("/repos/%s/traffic/views?per_page=14" % REPO)
        clones = opt("/repos/%s/traffic/clones?per_page=14" % REPO)
    except Exception:
        pass
    runs = (opt("/repos/%s/actions/runs?per_page=5" % REPO) or {}).get("workflow_runs", [])

    comments, react = [], {}
    issues = opt("/repos/%s/issues?labels=guestbook&state=all&per_page=1" % REPO)
    if issues:
        num = issues[0]["number"]
        comments = opt("/repos/%s/issues/%d/comments?per_page=8&sort=created&direction=desc" % (REPO, num)) or []
        react = opt("/repos/%s/issues/%d/reactions" % (REPO, num)) or {}

    g.write("language-donut.svg", build_donut(agg, len(repos)))
    g.write("constellation.svg", build_constellation(repos))
    g.write("activity.svg", build_activity(events))
    g.write("traffic.svg", build_traffic(views, clones, runs))
    g.write("wrapped.svg", build_wrapped(contrib, repos, agg))
    g.write("galaxy.svg", build_galaxy(contrib))
    g.write("guestbook.svg", build_guestbook(comments))
    g.write("reactions.svg", build_reactions(react))

    build_data(repos, followers, following, contrib, agg)
    build_badges(agg, contrib, followers, repos)
    build_animated()
    build_blog()
    build_og()

    g.mirror_to_docs()
    print("extras done")


if __name__ == "__main__":
    main()
