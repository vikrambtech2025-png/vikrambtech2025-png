"""Keep the profile README's repo/language counts honest.

Queries the GitHub API for the owner's public repos, then rewrites only the
lines between the <!--STATS:START--> / <!--STATS:END--> markers plus every
"N+ repos" phrase in the prose. Everything else in the README is left alone.

Run:  python .github/scripts/update_stats.py
Exits 0 and touches nothing when the numbers are already correct, so the
calling workflow can skip the commit.
"""

import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

OWNER = os.environ.get("PROFILE_OWNER", "vikrambtech2025-png")
README = Path(__file__).resolve().parents[2] / "README.md"
API = "https://api.github.com"

# .ipynb repos report "Jupyter Notebook" as their primary language, but the
# README talks about "Python & Jupyter" as one bucket, so fold them together.
LANG_ALIASES = {"Jupyter Notebook": "Python"}


def fetch_public_repos(token: str) -> list[dict]:
    """Page through every public repo for OWNER. Returns [] on API failure."""
    repos: list[dict] = []
    page = 1
    while True:
        url = f"{API}/users/{OWNER}/repos?per_page=100&page={page}&type=owner"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "profile-readme-stats",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = __import__("json").load(resp)
        except urllib.error.HTTPError as exc:
            print(f"error: GitHub API returned {exc.code} for page {page}", file=sys.stderr)
            return []
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def language_breakdown(repos: list[dict]) -> list[tuple[str, int]]:
    """Count primary languages, folding notebooks into Python.

    Repos with no detected language are skipped rather than bucketed as
    "Other" - they're empty or data-only repos, and listing them reads as
    noise next to real languages.
    """
    counter: Counter[str] = Counter()
    for repo in repos:
        lang = repo.get("language")
        if not lang:
            continue
        counter[LANG_ALIASES.get(lang, lang)] += 1
    return counter.most_common()


def render_stats_line(total: int, langs: list[tuple[str, int]]) -> str:
    """Rebuild the single <p> that sits between the STATS markers."""
    if not langs:
        return f"<p><b>Public repos:</b> {total}</p>"

    (top_lang, top_n), *rest = langs
    if top_lang == "Python":
        lead = f"Python &amp; Jupyter dominate — {top_n} repos"
    else:
        lead = f"{top_lang} leads — {top_n} repos"

    others = " · ".join(f"{lang} {n}" for lang, n in rest[:4])
    tail = f" · {others}" if others else ""
    return f"<p><b>Language mix across {total} public repos:</b> {lead}{tail}</p>"


def render_repo_count(total: int) -> str:
    """Keep the '200+' style claim honest without reading as silly when small."""
    return f"{total}+" if total >= 200 else str(total)


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("error: GITHUB_TOKEN / GH_TOKEN not set", file=sys.stderr)
        return 1

    repos = fetch_public_repos(token)
    if not repos:
        print("error: could not fetch repos, leaving README untouched", file=sys.stderr)
        return 1

    total = len(repos)
    langs = language_breakdown(repos)
    count_phrase = render_repo_count(total)
    new_line = render_stats_line(total, langs)

    original = README.read_text(encoding="utf-8")

    # 1. Replace the marked block (repo count line + language mix).
    updated, n = re.subn(
        r"(<!--STATS:START-->).*?(<!--STATS:END-->)",
        lambda m: f"{m.group(1)}\n{new_line}\n{m.group(2)}",
        original,
        flags=re.DOTALL,
    )
    if n != 1:
        print(f"error: expected 1 STATS block, found {n}", file=sys.stderr)
        return 1

    # 2. Refresh the "200+ repos" phrase everywhere it appears in prose.
    updated = re.sub(r"\b200\+\s+repos\b", f"{count_phrase} repos", updated)

    if updated == original:
        print("stats already up to date, nothing to commit")
        return 0

    README.write_text(updated, encoding="utf-8")
    print(f"updated: {total} public repos")
    for lang, n_lang in langs[:5]:
        print(f"  {lang:<16} {n_lang}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
