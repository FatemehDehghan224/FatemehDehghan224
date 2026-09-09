#!/usr/bin/env python3
"""Generate self-hosted GitHub profile SVG cards.

Uses only GitHub's own REST/GraphQL APIs and Python's standard library.
If an API call fails, the script exits before touching the committed SVGs,
so the README keeps showing the last good snapshot instead of a broken image.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USERNAME = os.environ.get("PROFILE_USERNAME", "FatemehDehghan224")
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

BG = "#0A0F1D"
BG2 = "#0D1427"
BORDER = "#25304A"
TEXT = "#F8FAFC"
MUTED = "#7E8DA5"
CYAN = "#22D3EE"
VIOLET = "#8B5CF6"
PINK = "#F472B6"


def request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> dict | list:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2026-03-10",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"GitHub API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"GitHub API unavailable: {exc}") from exc


def fetch_profile() -> dict:
    data = request_json(f"https://api.github.com/users/{urllib.parse.quote(USERNAME)}")
    if not isinstance(data, dict) or "login" not in data:
        raise RuntimeError("Unexpected GitHub user API response")
    return data


def fetch_contributions() -> tuple[int, list[dict]]:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required for the GraphQL contribution calendar")

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=364)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                contributionLevel
                weekday
              }
            }
          }
        }
      }
    }
    """
    payload = {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "to": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        },
    }
    result = request_json("https://api.github.com/graphql", method="POST", payload=payload)
    if not isinstance(result, dict):
        raise RuntimeError("Unexpected GitHub GraphQL response")
    if result.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")
    try:
        cal = result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weeks = cal["weeks"]
        total = int(cal["totalContributions"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("Contribution calendar missing from GitHub GraphQL response") from exc

    days: list[dict] = []
    for week_index, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            days.append(
                {
                    "week": week_index,
                    "weekday": int(day["weekday"]),
                    "date": day["date"],
                    "count": int(day["contributionCount"]),
                    "level": day["contributionLevel"],
                }
            )
    if not days:
        raise RuntimeError("Contribution calendar returned no days")
    return total, days


def fmt(n: int) -> str:
    return f"{n:,}"


def stats_svg(profile: dict, contributions: int, active_days: int) -> str:
    public_repos = int(profile.get("public_repos", 0))
    followers = int(profile.get("followers", 0))
    metrics = [
        ("PUBLIC REPOS", public_repos),
        ("FOLLOWERS", followers),
        ("CONTRIBUTIONS · 12MO", contributions),
        ("ACTIVE DAYS · 12MO", active_days),
    ]

    cards = []
    xs = [58, 337, 616, 895]
    for i, ((label, value), x) in enumerate(zip(metrics, xs)):
        accent = [VIOLET, CYAN, PINK, CYAN][i]
        cards.append(
            f'''<g transform="translate({x} 82)">
  <rect width="247" height="88" rx="18" fill="#0D1427" stroke="#26334E"/>
  <rect x="1" y="1" width="245" height="86" rx="17" fill="url(#cardGlow{i})" opacity=".65"/>
  <circle cx="22" cy="24" r="4.5" fill="{accent}">
    <animate attributeName="opacity" values="1;.35;1" dur="{2.2 + i * .35:.2f}s" repeatCount="indefinite"/>
  </circle>
  <text x="36" y="29" fill="#738198" font-size="11" font-weight="700" letter-spacing="1.35" font-family="JetBrains Mono,Consolas,monospace">{label}</text>
  <text x="20" y="67" fill="#F8FAFC" font-size="30" font-weight="760" font-family="Inter,Segoe UI,Arial,sans-serif">{fmt(int(value))}</text>
</g>'''
        )

    gradients = "\n".join(
        f'''<radialGradient id="cardGlow{i}" cx="0" cy="0" r="1" gradientTransform="translate({215 if i%2==0 else 30} 12) rotate(135) scale(155 110)">
  <stop stop-color="{[VIOLET,CYAN,PINK,CYAN][i]}" stop-opacity=".11"/><stop offset="1" stop-color="{[VIOLET,CYAN,PINK,CYAN][i]}" stop-opacity="0"/>
</radialGradient>'''
        for i in range(4)
    )

    return f'''<svg width="1200" height="194" viewBox="0 0 1200 194" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="accent" x1="58" y1="0" x2="1142" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="{VIOLET}"/><stop offset=".52" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/>
  </linearGradient>
  <radialGradient id="topGlow" cx="0" cy="0" r="1" gradientTransform="translate(960 15) rotate(160) scale(330 120)">
    <stop stop-color="{VIOLET}" stop-opacity=".13"/><stop offset="1" stop-color="{VIOLET}" stop-opacity="0"/>
  </radialGradient>
  {gradients}
</defs>
<rect x="1" y="1" width="1198" height="192" rx="24" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
<rect x="1" y="1" width="1198" height="192" rx="24" fill="url(#topGlow)"/>
<text x="58" y="42" fill="#78879D" font-size="12" font-weight="700" letter-spacing="2.05" font-family="Inter,Segoe UI,Arial,sans-serif">GITHUB SIGNAL</text>
<text x="58" y="68" fill="{TEXT}" font-size="19" font-weight="700" font-family="Inter,Segoe UI,Arial,sans-serif">A live snapshot of what is happening on my public GitHub.</text>
<g transform="translate(929 31)">
  <rect width="213" height="30" rx="15" fill="#0F172A" stroke="#334155"/>
  <circle cx="17" cy="15" r="4" fill="{CYAN}"><animate attributeName="opacity" values="1;.3;1" dur="1.8s" repeatCount="indefinite"/></circle>
  <text x="30" y="19" fill="#93A4BB" font-size="10.5" letter-spacing="1.15" font-family="JetBrains Mono,Consolas,monospace">AUTO-SYNC · GITHUB</text>
</g>
{''.join(cards)}
<rect x="58" y="186" width="1084" height="2" rx="1" fill="url(#accent)" opacity=".48"/>
</svg>'''


def level_color(level: str) -> str:
    return {
        "NONE": "#111827",
        "FIRST_QUARTILE": "#312E81",
        "SECOND_QUARTILE": "#6D28D9",
        "THIRD_QUARTILE": "#0891B2",
        "FOURTH_QUARTILE": "#F472B6",
    }.get(level, "#111827")


def activity_svg(days: list[dict], total: int) -> str:
    max_week = max(d["week"] for d in days)
    # GitHub normally returns 53 weeks; if not, right-align the available weeks.
    week_offset = max(0, 52 - max_week)
    x0, y0, step, cell = 292, 102, 16, 11

    rects: list[str] = []
    for d in days:
        x = x0 + (d["week"] + week_offset) * step
        y = y0 + d["weekday"] * step
        color = level_color(d["level"])
        opacity = ".75" if d["level"] == "NONE" else "1"
        title = f"{fmt(d['count'])} contributions · {d['date']}"
        rects.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2.5" fill="{color}" opacity="{opacity}"><title>{escape(title)}</title></rect>'
        )

    # Month labels: label the first visible week for each month.
    month_labels: list[str] = []
    seen: set[str] = set()
    for d in sorted(days, key=lambda z: z["date"]):
        dt = datetime.strptime(d["date"], "%Y-%m-%d")
        key = f"{dt.year}-{dt.month}"
        if key in seen:
            continue
        seen.add(key)
        x = x0 + (d["week"] + week_offset) * step
        if x < x0 + 10:
            continue
        month_labels.append(
            f'<text x="{x}" y="88" fill="#64748B" font-size="10.5" font-family="JetBrains Mono,Consolas,monospace">{dt.strftime("%b").upper()}</text>'
        )

    active_days = sum(1 for d in days if d["count"] > 0)
    best_day = max(days, key=lambda d: d["count"])
    current_streak = 0
    for d in sorted(days, key=lambda z: z["date"], reverse=True):
        if d["count"] > 0:
            current_streak += 1
        elif current_streak == 0:
            # Ignore today/yesterday gaps only until the first active day encountered.
            continue
        else:
            break

    return f'''<svg width="1200" height="270" viewBox="0 0 1200 270" fill="none" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="accent" x1="58" y1="0" x2="1142" y2="0" gradientUnits="userSpaceOnUse">
    <stop stop-color="{VIOLET}"/><stop offset=".52" stop-color="{CYAN}"/><stop offset="1" stop-color="{PINK}"/>
  </linearGradient>
  <radialGradient id="glow" cx="0" cy="0" r="1" gradientTransform="translate(960 90) rotate(165) scale(390 170)">
    <stop stop-color="{CYAN}" stop-opacity=".10"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
  <filter id="soft" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="5"/></filter>
</defs>
<rect x="1" y="1" width="1198" height="268" rx="24" fill="{BG}" stroke="{BORDER}" stroke-width="2"/>
<rect x="1" y="1" width="1198" height="268" rx="24" fill="url(#glow)"/>
<text x="58" y="44" fill="#78879D" font-size="12" font-weight="700" letter-spacing="2.05" font-family="Inter,Segoe UI,Arial,sans-serif">CONTRIBUTION PULSE · LAST 12 MONTHS</text>

<g transform="translate(58 78)">
  <text x="0" y="45" fill="{TEXT}" font-size="44" font-weight="800" font-family="Inter,Segoe UI,Arial,sans-serif">{fmt(total)}</text>
  <text x="2" y="67" fill="#78879D" font-size="11" letter-spacing="1.1" font-family="JetBrains Mono,Consolas,monospace">CONTRIBUTIONS</text>
  <path d="M0 95H178" stroke="#26334E" stroke-width="1.5"/>
  <text x="0" y="120" fill="#64748B" font-size="11" font-family="JetBrains Mono,Consolas,monospace">active days</text>
  <text x="140" y="120" text-anchor="end" fill="{CYAN}" font-size="12" font-weight="700" font-family="JetBrains Mono,Consolas,monospace">{active_days}</text>
  <text x="0" y="143" fill="#64748B" font-size="11" font-family="JetBrains Mono,Consolas,monospace">best day</text>
  <text x="140" y="143" text-anchor="end" fill="{PINK}" font-size="12" font-weight="700" font-family="JetBrains Mono,Consolas,monospace">{best_day['count']}</text>
</g>

{''.join(month_labels)}
<text x="267" y="114" fill="#526078" font-size="9.5" text-anchor="end" font-family="JetBrains Mono,Consolas,monospace">SUN</text>
<text x="267" y="146" fill="#526078" font-size="9.5" text-anchor="end" font-family="JetBrains Mono,Consolas,monospace">TUE</text>
<text x="267" y="178" fill="#526078" font-size="9.5" text-anchor="end" font-family="JetBrains Mono,Consolas,monospace">THU</text>
<text x="267" y="210" fill="#526078" font-size="9.5" text-anchor="end" font-family="JetBrains Mono,Consolas,monospace">SAT</text>
<g>{''.join(rects)}</g>

<!-- moving signal across the contribution field -->
<circle cx="0" cy="0" r="4" fill="{CYAN}" filter="url(#soft)" opacity=".85">
  <animateMotion dur="8s" repeatCount="indefinite" path="M292 236 H1136"/>
  <animate attributeName="opacity" values="0;.9;.9;0" dur="8s" repeatCount="indefinite"/>
</circle>

<g transform="translate(894 232)">
  <text x="0" y="0" fill="#56657A" font-size="10" font-family="JetBrains Mono,Consolas,monospace">LESS</text>
  <rect x="40" y="-9" width="10" height="10" rx="2" fill="#111827"/>
  <rect x="56" y="-9" width="10" height="10" rx="2" fill="#312E81"/>
  <rect x="72" y="-9" width="10" height="10" rx="2" fill="#6D28D9"/>
  <rect x="88" y="-9" width="10" height="10" rx="2" fill="#0891B2"/>
  <rect x="104" y="-9" width="10" height="10" rx="2" fill="#F472B6"/>
  <text x="122" y="0" fill="#56657A" font-size="10" font-family="JetBrains Mono,Consolas,monospace">MORE</text>
</g>
<rect x="58" y="258" width="1084" height="2" rx="1" fill="url(#accent)" opacity=".42"/>
</svg>'''


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    try:
        profile = fetch_profile()
        total, days = fetch_contributions()
        active_days = sum(1 for d in days if d["count"] > 0)
        stats = stats_svg(profile, total, active_days)
        activity = activity_svg(days, total)
    except Exception as exc:
        print(f"Profile stats update failed safely: {exc}", file=sys.stderr)
        print("Existing SVG files were left untouched.", file=sys.stderr)
        return 1

    ASSETS.mkdir(parents=True, exist_ok=True)
    atomic_write(ASSETS / "github-stats.svg", stats)
    atomic_write(ASSETS / "github-activity.svg", activity)
    print(f"Updated profile SVGs for @{USERNAME}: {total} contributions / {active_days} active days")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
