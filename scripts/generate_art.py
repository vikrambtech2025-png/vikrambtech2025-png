#!/usr/bin/env python3
"""
Obsidian profile art generator — 100% self-hosted, zero third-party services.

Reads live data from the GitHub REST API + the public contributions calendar and
renders four SVG assets into assets/generated/:

  * contribution-city.svg   -> isometric 3D city built from your real contributions
  * stats.svg               -> self-hosted stat cards (repos / stars / followers / streak)
  * tech-stack.svg          -> neon tech chips curated from real dependencies
  * featured-projects.svg   -> live project cards with real star counts

No pip installs. Standard library only.
"""

import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta

# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #
USER = os.environ.get("PROFILE_USER") or (os.environ.get("GITHUB_REPOSITORY", "/").split("/")[0]) or "vikrambtech2025-png"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT_DIR = os.path.join("assets", "generated")

FEATURED = [
    "LangGraph-Agent",
    "citecheck",
    "production-rag",
    "colpali-rag",
    "MOIL-Manganese-AI",
    "alpaka-mcp",
]

TECH = [
    ("Python", "#00E5FF"), ("Jupyter", "#FFB300"), ("TypeScript", "#00E5FF"),
    ("Java", "#FF1F4B"), ("JavaScript", "#FFB300"),
    ("LangChain", "#22C55E"), ("LangGraph", "#22C55E"), ("OpenAI", "#8B5CF6"),
    ("Hugging Face", "#FFB300"), ("ColPali", "#FF1F4B"), ("Unsloth", "#00E5FF"),
    ("FAISS", "#00E5FF"), ("Qdrant", "#FF1F4B"), ("ChromaDB", "#8B5CF6"),
    ("PyTorch", "#FF1F4B"), ("TensorFlow", "#FFB300"), ("scikit-learn", "#00E5FF"),
    ("XGBoost", "#22C55E"), ("OpenCV", "#FF1F4B"), ("MediaPipe", "#8B5CF6"),
    ("FastAPI", "#00E5FF"), ("Streamlit", "#FF1F4B"), ("Gradio", "#FFB300"),
    ("Flask", "#E6F1FF"), ("React", "#00E5FF"), ("Express", "#5A6B85"),
    ("pandas", "#8B5CF6"), ("NumPy", "#00E5FF"), ("Matplotlib", "#FFB300"),
    ("Seaborn", "#22C55E"), ("Inngest", "#8B5CF6"), ("Docker", "#00E5FF"),
    ("Supabase", "#22C55E"), ("SQLite", "#5A6B85"), ("GitHub Actions", "#8B5CF6"),
    ("Tavily", "#22C55E"), ("Alpaca API", "#FFB300"), ("Linux", "#FFB300"),
]

MONO = "Consolas, 'Courier New', monospace"


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def esc(text):
    return html.escape(str(text), quote=True)


def api(path):
    url = path if path.startswith("http") else "https://api.github.com" + path
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "obsidian-profile-art")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def fetch_all_repos():
    repos, page = [], 1
    while True:
        chunk = api("/users/%s/repos?per_page=100&page=%d&sort=updated" % (USER, page))
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


def fetch_contributions():
    """Return {date: (level, count)} parsed from the public contributions calendar."""
    url = "https://github.com/users/%s/contributions" % USER
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (obsidian-profile-art)")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            page = r.read().decode("utf-8", "replace")
    except Exception as exc:  # pragma: no cover
        print("contributions fetch failed:", exc, file=sys.stderr)
        return {}
    # Each day is a <td id="contribution-day-component-W-D" data-date=... data-level=...>
    days = {}
    for tag in re.findall(r"<td[^>]*data-date=\"[0-9]{4}-[0-9]{2}-[0-9]{2}\"[^>]*>", page):
        tid = re.search(r'id="([^"]+)"', tag)
        d = re.search(r'data-date="([^"]+)"', tag)
        lvl = re.search(r'data-level="(\d+)"', tag)
        if tid and d and lvl:
            days[tid.group(1)] = [d.group(1), int(lvl.group(1)), 0]

    # The human-readable count lives in a <tool-tip for="<td id>"> element.
    for tid, text in re.findall(r"<tool-tip[^>]*for=\"([^\"]+)\"[^>]*>(.*?)</tool-tip>", page, re.S):
        if tid in days:
            cm = re.search(r"(\d+)\s+contribution", text)
            days[tid][2] = int(cm.group(1)) if cm else 0

    return {date: (lvl, count) for date, lvl, count in days.values()}


def streaks(contrib):
    if not contrib:
        return 0, 0, 0
    keys = sorted(contrib)
    total = sum(c for _, c in contrib.values())

    longest = cur = 0
    prev = None
    for k in keys:
        if contrib[k][1] > 0:
            day = datetime.strptime(k, "%Y-%m-%d").date()
            cur = cur + 1 if (prev is not None and (day - prev).days == 1) else 1
            longest = max(longest, cur)
            prev = day
        else:
            cur = 0
            prev = None

    last_active = None
    for k in reversed(keys):
        if contrib[k][1] > 0:
            last_active = datetime.strptime(k, "%Y-%m-%d").date()
            break

    run = 0
    if last_active is not None:
        today = datetime.strptime(keys[-1], "%Y-%m-%d").date()
        if (today - last_active).days <= 1:  # alive if active today or yesterday
            probe = last_active
            while contrib.get(probe.strftime("%Y-%m-%d"), (0, 0))[1] > 0:
                run += 1
                probe -= timedelta(days=1)
    return total, longest, run


def svg_header(w, h, label):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s">' % (w, h, w, h, esc(label)))


# --------------------------------------------------------------------------- #
#  contribution-city.svg  (isometric)
# --------------------------------------------------------------------------- #
def build_city(contrib):
    W, H = 960, 380
    body = [svg_header(W, H, "Contribution city")]
    body.append("""
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000000"/>
      <stop offset="0.55" stop-color="#03060c"/>
      <stop offset="1" stop-color="#05070d"/>
    </linearGradient>
    <radialGradient id="core" cx="0.5" cy="0.78" r="0.6">
      <stop offset="0" stop-color="#00E5FF" stop-opacity="0.22"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0"/>
    </radialGradient>
    <filter id="cglow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style><![CDATA[
    .peak{animation:beacon 2.6s ease-in-out infinite}
    @keyframes beacon{0%,100%{opacity:.55}50%{opacity:1}}
  ]]></style>""")
    body.append('<rect width="%d" height="%d" fill="url(#sky)"/>' % (W, H))
    body.append('<rect width="%d" height="%d" fill="url(#core)"/>' % (W, H))
    body.append('<rect x="1" y="1" width="%d" height="%d" rx="14" fill="none" stroke="#16203a" stroke-width="2"/>'
                % (W - 2, H - 2))

    # layout grid: 53 weeks x 7 days
    start = datetime.strptime(min(contrib), "%Y-%m-%d").date() if contrib else datetime.today().date()
    first_sun = (start.weekday() + 1) % 7
    weeks = {}
    for ds, (lvl, _cnt) in contrib.items():
        d = datetime.strptime(ds, "%Y-%m-%d").date()
        idx = (d - start).days + first_sun
        w, day = idx // 7, idx % 7
        weeks.setdefault(w, {})[day] = lvl
    max_week = max(weeks) if weeks else 52

    s = 8.0
    step = 6.0
    shift_x = 140
    shift_y = 96
    faces = []
    for w in range(max_week + 1):
        for day in range(7):
            lvl = weeks.get(w, {}).get(day, 0)
            x = (w - day) * s + shift_x + 6 * s
            y = (w + day) * (s / 2) + shift_y
            h = max(lvl * step, 2.5) if lvl > 0 else 2.0
            if lvl == 0:
                top, left, right = "#0d1526", "#080e18", "#0a1220"
            else:
                tops = {1: "#12414f", 2: "#0e7d92", 3: "#00b8d4", 4: "#00E5FF"}
                base = tops[lvl]
                top = base
                left = base if lvl >= 3 else "#0b2430"
                right = "#0a1a24" if lvl < 3 else "#0891a6"
            cls = ' class="peak"' if lvl >= 4 else ""
            faces.append((w + day, w, x, y, h, top, left, right, cls))

    body.append('<g stroke="#04070d" stroke-width="0.6">')
    for _d, _w, x, y, h, top, left, right, cls in sorted(faces, key=lambda f: (f[0], f[1])):
        body.append(
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"%s/>'
            % (x, y, x + s, y + s / 2, x, y + s, x - s, y + s / 2, top, cls))
        body.append(
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"%s/>'
            % (x - s, y + s / 2, x, y + s, x, y + s + h, x - s, y + s / 2 + h, left, cls))
        body.append(
            '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"%s/>'
            % (x, y + s, x + s, y + s / 2, x + s, y + s / 2 + h, x, y + s + h, right, cls))
    body.append("</g>")

    body.append('<text x="34" y="38" font-family="%s" font-size="14" fill="#00E5FF">CONTRIBUTION CITY</text>' % MONO)
    body.append('<text x="%d" y="38" text-anchor="end" font-family="%s" font-size="11.5" fill="#5A6B85">isometric &#183; live from GitHub</text>'
                % (W - 34, MONO))
    body.append('<g font-family="%s" font-size="11" fill="#5A6B85">' % MONO)
    body.append('<text x="%d" y="%d">less</text>' % (W - 220, H - 26))
    body.append('<text x="%d" y="%d">more</text>' % (W - 60, H - 26))
    body.append("</g>")
    legend = ["#0d1526", "#12414f", "#0e7d92", "#00b8d4", "#00E5FF"]
    for i, c in enumerate(legend):
        body.append('<rect x="%d" y="%d" width="22" height="14" rx="3" fill="%s" stroke="#16203a"/>'
                    % (W - 200 + i * 30, H - 38, c))
    body.append("</svg>")
    return "\n".join(body)


# --------------------------------------------------------------------------- #
#  stats.svg
# --------------------------------------------------------------------------- #
def build_stats(repos, followers, following, contrib):
    total, longest, cur = streaks(contrib)
    stars = sum(r.get("stargazers_count", 0) for r in repos)
    pub = sum(1 for r in repos if not r.get("fork"))
    cards = [
        ("PUBLIC REPOS", "%d" % pub, "#8B5CF6"),
        ("TOTAL STARS", "%d" % stars, "#FFB300"),
        ("FOLLOWERS", "%d" % followers, "#00E5FF"),
        ("CONTRIBUTIONS", "%d" % total, "#22C55E"),
        ("CURRENT STREAK", "%d d" % cur, "#FF1F4B"),
        ("LONGEST STREAK", "%d d" % longest, "#00E5FF"),
    ]
    W, H = 1040, 190
    body = [svg_header(W, H, "GitHub stats")]
    body.append("""
  <defs>
    <linearGradient id="sbg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000000"/>
      <stop offset="1" stop-color="#05070d"/>
    </linearGradient>
    <pattern id="sgrid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M40 0H0V40" fill="none" stroke="#0c1424" stroke-width="1"/>
    </pattern>
  </defs>""")
    body.append('<rect width="%d" height="%d" fill="url(#sbg)"/>' % (W, H))
    body.append('<rect width="%d" height="%d" fill="url(#sgrid)" opacity="0.6"/>' % (W, H))
    body.append('<rect x="1" y="1" width="%d" height="%d" rx="14" fill="none" stroke="#16203a" stroke-width="2"/>'
                % (W - 2, H - 2))
    cols, cw, ch, gap = 3, 320, 62, 14
    x0, y0 = 26, 22
    for i, (label, value, color) in enumerate(cards):
        cx = x0 + (i % cols) * (cw + gap)
        cy = y0 + (i // cols) * (ch + gap)
        body.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="#070c16" stroke="#16203a"/>'
                    % (cx, cy, cw, ch))
        body.append('<rect x="%d" y="%d" width="4" height="%d" rx="2" fill="%s"/>' % (cx, cy + 8, ch - 16, color))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="11" letter-spacing="2" fill="#5A6B85">%s</text>'
                    % (cx + 20, cy + 24, MONO, esc(label)))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="25" font-weight="700" fill="%s">%s</text>'
                    % (cx + 20, cy + 52, MONO, color, esc(value)))
    body.append("</svg>")
    return "\n".join(body)


# --------------------------------------------------------------------------- #
#  tech-stack.svg
# --------------------------------------------------------------------------- #
def build_tech():
    per_row = 6
    cw, ch, gap = 150, 40, 10
    rows = (len(TECH) + per_row - 1) // per_row
    W = 26 * 2 + per_row * cw + (per_row - 1) * gap
    H = 74 + rows * (ch + gap)
    body = [svg_header(W, H, "Tech stack")]
    body.append("""
  <defs>
    <linearGradient id="tbg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000000"/>
      <stop offset="1" stop-color="#05070d"/>
    </linearGradient>
    <filter id="tglow" x="-40%" y="-40%" width="180%" height="180%">
      <feGaussianBlur stdDeviation="2.2" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>""")
    body.append('<rect width="%d" height="%d" fill="url(#tbg)"/>' % (W, H))
    body.append('<rect x="1" y="1" width="%d" height="%d" rx="14" fill="none" stroke="#16203a" stroke-width="2"/>'
                % (W - 2, H - 2))
    body.append('<text x="26" y="38" font-family="%s" font-size="14" fill="#00E5FF">TECH ARSENAL</text>' % MONO)
    body.append('<text x="%d" y="38" text-anchor="end" font-family="%s" font-size="11.5" fill="#5A6B85">mapped to real dependencies</text>'
                % (W - 26, MONO))
    for i, (name, color) in enumerate(TECH):
        cx = 26 + (i % per_row) * (cw + gap)
        cy = 56 + (i // per_row) * (ch + gap)
        body.append('<rect x="%d" y="%d" width="%d" height="%d" rx="8" fill="#070c16" stroke="%s" stroke-opacity="0.55"/>'
                    % (cx, cy, cw, ch, color))
        body.append('<rect x="%d" y="%d" width="3" height="%d" rx="1.5" fill="%s"/>' % (cx, cy + 8, ch - 16, color))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="12.5" fill="#dce9f7">%s</text>'
                    % (cx + 14, cy + 25, MONO, esc(name)))
    body.append("</svg>")
    return "\n".join(body)


# --------------------------------------------------------------------------- #
#  featured-projects.svg
# --------------------------------------------------------------------------- #
def build_projects(repos):
    by_name = {r["name"]: r for r in repos}
    picks = [(n, by_name[n]) for n in FEATURED if n in by_name]
    for r in repos[:40]:
        if len(picks) >= 6:
            break
        if r.get("fork") or r["name"] == USER:
            continue
        if any(p[0] == r["name"] for p in picks):
            continue
        if r.get("description") and any(k in (r.get("description") or "").lower()
                                        for k in ("rag", "llm", "agent", "ai", "ml", "vision", "nlp")):
            picks.append((r["name"], r))
    picks = picks[:6]

    cols, cw, ch, gap = 2, 454, 96, 16
    W = 26 * 2 + cols * cw + (cols - 1) * gap
    rows = (len(picks) + cols - 1) // cols
    H = 74 + rows * (ch + gap)
    accents = ["#00E5FF", "#8B5CF6", "#FF1F4B", "#FFB300", "#22C55E", "#00E5FF"]
    body = [svg_header(W, H, "Featured projects")]
    body.append("""
  <defs>
    <linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#000000"/>
      <stop offset="1" stop-color="#05070d"/>
    </linearGradient>
  </defs>""")
    body.append('<rect width="%d" height="%d" fill="url(#pbg)"/>' % (W, H))
    body.append('<rect x="1" y="1" width="%d" height="%d" rx="14" fill="none" stroke="#16203a" stroke-width="2"/>'
                % (W - 2, H - 2))
    body.append('<text x="26" y="38" font-family="%s" font-size="14" fill="#00E5FF">FEATURED SYSTEMS</text>' % MONO)
    body.append('<text x="%d" y="38" text-anchor="end" font-family="%s" font-size="11.5" fill="#5A6B85">live star counts</text>'
                % (W - 26, MONO))
    for i, (name, repo) in enumerate(picks):
        cx = 26 + (i % cols) * (cw + gap)
        cy = 56 + (i // cols) * (ch + gap)
        color = accents[i % len(accents)]
        desc = (repo.get("description") or "No description yet").strip()
        if len(desc) > 78:
            desc = desc[:75].rstrip() + "..."
        lang = repo.get("language") or "Code"
        stars = repo.get("stargazers_count", 0)
        body.append('<rect x="%d" y="%d" width="%d" height="%d" rx="10" fill="#070c16" stroke="#16203a"/>'
                    % (cx, cy, cw, ch))
        body.append('<rect x="%d" y="%d" width="4" height="%d" rx="2" fill="%s"/>' % (cx, cy + 10, ch - 20, color))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="14.5" font-weight="700" fill="%s">%s</text>'
                    % (cx + 18, cy + 28, MONO, color, esc(name)))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="10.8" fill="#8ea3bd">%s</text>'
                    % (cx + 18, cy + 50, MONO, esc(desc)))
        body.append('<text x="%d" y="%d" font-family="%s" font-size="10.8" fill="#5A6B85">%s</text>'
                    % (cx + 18, cy + 76, MONO, esc(lang)))
        body.append('<text x="%d" y="%d" text-anchor="end" font-family="%s" font-size="12" fill="#FFB300">%d stars</text>'
                    % (cx + cw - 18, cy + 76, MONO, stars))
    body.append("</svg>")
    return "\n".join(body)


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def write(name, content):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("wrote", path, len(content), "bytes")


def main():
    try:
        user = api("/users/" + USER)
        followers = user.get("followers", 0)
        following = user.get("following", 0)
    except Exception as exc:
        print("user fetch failed:", exc, file=sys.stderr)
        followers = following = 0
    try:
        repos = fetch_all_repos()
    except Exception as exc:
        print("repos fetch failed:", exc, file=sys.stderr)
        repos = []
    contrib = fetch_contributions()
    print("repos:", len(repos), "contribution days:", len(contrib))

    write("contribution-city.svg", build_city(contrib))
    write("stats.svg", build_stats(repos, followers, following, contrib))
    write("tech-stack.svg", build_tech())
    write("featured-projects.svg", build_projects(repos))


if __name__ == "__main__":
    main()
