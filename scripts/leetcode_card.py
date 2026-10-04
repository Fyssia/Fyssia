#!/usr/bin/env python3
"""Карточка LeetCode для README: тянет статистику из GraphQL и рисует два SVG (светлый и тёмный).

Запуск: python3 scripts/leetcode_card.py <username> <каталог>
"""
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """
query($u: String!) {
  allQuestionsCount { difficulty count }
  matchedUser(username: $u) {
    username
    profile { realName ranking }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    userCalendar { streak totalActiveDays submissionCalendar }
  }
  userProfileUserQuestionProgressV2(userSlug: $u) {
    numFailedQuestions { difficulty count }
  }
}
"""

# Палитры повторяют цвета GitHub, чтобы карточка выглядела родной на странице профиля
THEMES = {
    "dark": {
        "border": "#30363d", "text": "#e6edf3", "muted": "#9198a1", "track": "#21262d",
        "logo_l": "#e6edf3", "easy": "#1cbaba", "medium": "#ffb700", "hard": "#f63737",
        "heat": ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"],
    },
    "light": {
        "border": "#d0d7de", "text": "#1f2328", "muted": "#59636e", "track": "#eff2f5",
        "logo_l": "#1f2328", "easy": "#00af9b", "medium": "#ffb800", "hard": "#ef4743",
        "heat": ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"],
    },
}

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
W, PAD = 840, 24
CELL, GAP = 12, 3
LOGO = (
    '<path fill="#ffa116" d="M67.506,83.066 C70,80.576 74.037,80.582 76.522,83.08 C79.008,85.578 79.002,89.622 76.508,92.112 '
    "L65.435,103.169 C55.219,113.37 38.56,113.518 28.172,103.513 C28.112,103.455 23.486,98.92 8.227,83.957 "
    "C-1.924,74.002 -2.936,58.074 6.616,47.846 L24.428,28.774 C33.91,18.621 51.387,17.512 62.227,26.278 L78.405,39.362 "
    "C81.144,41.577 81.572,45.598 79.361,48.342 C77.149,51.087 73.135,51.515 70.395,49.3 L54.218,36.217 "
    "C48.549,31.632 38.631,32.262 33.739,37.5 L15.927,56.572 C11.277,61.552 11.786,69.574 17.146,74.829 "
    "C28.351,85.816 36.987,94.284 36.997,94.294 C42.398,99.495 51.13,99.418 56.433,94.123 L67.506,83.066 Z\"/>"
    '<path fill="{l}" d="M49.412,2.023 C51.817,-0.552 55.852,-0.686 58.423,1.722 C60.994,4.132 61.128,8.173 58.723,10.749 '
    "L15.928,56.572 C11.277,61.551 11.786,69.573 17.145,74.829 L36.909,94.209 C39.425,96.676 39.468,100.719 37.005,103.24 "
    "C34.542,105.76 30.506,105.804 27.99,103.336 L8.226,83.956 C-1.924,74.002 -2.936,58.074 6.617,47.846 L49.412,2.023 Z\"/>"
    '<path fill="#b3b3b3" d="M40.606,72.001 C37.086,72.001 34.231,69.142 34.231,65.614 C34.231,62.087 37.086,59.228 40.606,59.228 '
    'L87.624,59.228 C91.145,59.228 94,62.087 94,65.614 C94,69.142 91.145,72.001 87.624,72.001 L40.606,72.001 Z"/>'
)


def fetch(username):
    body = json.dumps({"query": QUERY, "variables": {"u": username}}).encode()
    req = urllib.request.Request(
        "https://leetcode.com/graphql",
        data=body,
        headers={"Content-Type": "application/json", "Referer": "https://leetcode.com", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors") or not data["data"]["matchedUser"]:
        raise SystemExit(f"LeetCode не отдал профиль {username}: {data.get('errors')}")
    return data["data"]


def parse(data):
    user = data["matchedUser"]
    total = {q["difficulty"]: q["count"] for q in data["allQuestionsCount"]}
    solved = {q["difficulty"]: q["count"] for q in user["submitStatsGlobal"]["acSubmissionNum"]}
    cal = user["userCalendar"]
    days = {
        dt.datetime.fromtimestamp(int(ts), dt.timezone.utc).date(): n
        for ts, n in json.loads(cal["submissionCalendar"] or "{}").items()
    }
    rank = user["profile"]["ranking"]
    return {
        "name": user["profile"]["realName"] or user["username"],
        "username": user["username"],
        # Так же показывает сам LeetCode: всех, кто ниже пяти миллионов, он округляет
        "rank": "~5,000,000" if rank >= 5_000_000 else f"{rank:,}",
        "total": total,
        "solved": solved,
        "attempting": sum(q["count"] for q in data["userProfileUserQuestionProgressV2"]["numFailedQuestions"]),
        "days": days,
        "active_days": cal["totalActiveDays"],
        "max_streak": cal["streak"],
    }


def arc(cx, cy, r, start, sweep):
    """Дуга по часовой стрелке; углы в градусах от оси X (в SVG ось Y смотрит вниз)."""
    a0, a1 = math.radians(start), math.radians(start + sweep)
    x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    large = 1 if sweep > 180 else 0
    return f"M{x0:.2f},{y0:.2f} A{r},{r} 0 {large} 1 {x1:.2f},{y1:.2f}"


def level(n):
    return 0 if n == 0 else 1 if n <= 2 else 2 if n <= 5 else 3 if n <= 9 else 4


def render(s, t, today):
    out = []
    add = out.append

    # Шапка: логотип, имя, ранг
    add(f'<g transform="translate({PAD},20) scale(0.25)">{LOGO.format(l=t["logo_l"])}</g>')
    add(f'<text x="{PAD + 34}" y="40" class="b" font-size="16">{escape(s["name"])}'
        f'<tspan class="m" font-weight="400" font-size="13" dx="8">{escape(s["username"])}</tspan></text>')
    add(f'<text x="{W - PAD}" y="40" text-anchor="end" class="m" font-size="13">Rank '
        f'<tspan class="t" font-weight="600">{s["rank"]}</tspan></text>')

    # Кольцо: дуга в 270°, разбитая на сегменты по числу задач каждой сложности
    cx, cy, r = PAD + 70, 142, 56
    diffs = ["Easy", "Medium", "Hard"]
    gap = 10
    usable = 270 - gap * 2
    angle = 135
    for d in diffs:
        sweep = usable * s["total"][d] / s["total"]["All"]
        add(f'<path d="{arc(cx, cy, r, angle, sweep)}" stroke="{t[d.lower()]}" stroke-opacity="0.2" '
            f'stroke-width="6" fill="none" stroke-linecap="round"/>')
        done = s["solved"].get(d, 0)
        if done:
            part = max(sweep * done / s["total"][d], 0.5)
            add(f'<path d="{arc(cx, cy, r, angle, part)}" stroke="{t[d.lower()]}" '
                f'stroke-width="6" fill="none" stroke-linecap="round"/>')
        angle += sweep + gap
    add(f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" class="b" font-size="30">{s["solved"]["All"]}'
        f'<tspan class="m" font-size="14" font-weight="400">/{s["total"]["All"]}</tspan></text>')
    add(f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" class="t" font-size="13">'
        f'<tspan fill="{t["easy"]}">✓</tspan> Solved</text>')
    add(f'<text x="{cx}" y="{cy + r + 6}" text-anchor="middle" class="m" font-size="12">'
        f'<tspan class="t">{s["attempting"]}</tspan> Attempting</text>')

    # Полоски по сложностям
    x0, x1 = PAD + 176, W - PAD
    for i, d in enumerate(diffs):
        y = 104 + i * 40
        done, total = s["solved"].get(d, 0), s["total"][d]
        add(f'<text x="{x0}" y="{y}" fill="{t[d.lower()]}" font-weight="600" font-size="13">{d}</text>')
        add(f'<text x="{x1}" y="{y}" text-anchor="end" class="b" font-size="13">{done}'
            f'<tspan class="m" font-weight="400"> / {total}</tspan></text>')
        add(f'<rect x="{x0}" y="{y + 9}" width="{x1 - x0}" height="6" rx="3" fill="{t["track"]}"/>')
        if done:
            width = max((x1 - x0) * done / total, 6)
            add(f'<rect x="{x0}" y="{y + 9}" width="{width:.1f}" height="6" rx="3" fill="{t[d.lower()]}"/>')

    # Тепловая карта за год: колонки — недели с воскресенья, как у GitHub и LeetCode
    year_ago = today - dt.timedelta(days=365)
    subs = sum(n for d, n in s["days"].items() if d > year_ago)
    top = 236
    add(f'<text x="{PAD}" y="{top}" class="b" font-size="15">{subs}'
        f'<tspan class="m" font-weight="400" font-size="13"> submissions in the past year</tspan></text>')
    add(f'<text x="{W - PAD}" y="{top}" text-anchor="end" class="m" font-size="12">Total active days: '
        f'<tspan class="t">{s["active_days"]}</tspan><tspan dx="16">Max streak: </tspan>'
        f'<tspan class="t">{s["max_streak"]}</tspan></text>')

    weeks = (W - PAD * 2 + GAP) // (CELL + GAP)
    pitch = (W - PAD * 2 + GAP) / weeks
    last_sunday = today - dt.timedelta(days=(today.weekday() + 1) % 7)
    first = last_sunday - dt.timedelta(weeks=weeks - 1)
    gy = top + 14
    prev_month, last_label_x = None, -100
    for w in range(weeks):
        x = PAD + w * pitch
        week_start = first + dt.timedelta(weeks=w)
        if week_start.month != prev_month:
            if x - last_label_x > 30 and w < weeks - 1:
                add(f'<text x="{x:.1f}" y="{gy + 7 * (CELL + GAP) + 12}" class="m" font-size="11">'
                    f'{week_start.strftime("%b")}</text>')
                last_label_x = x
            prev_month = week_start.month
        for d in range(7):
            day = week_start + dt.timedelta(days=d)
            if day > today:
                break
            fill = t["heat"][level(s["days"].get(day, 0))]
            add(f'<rect x="{x:.1f}" y="{gy + d * (CELL + GAP)}" width="{CELL}" height="{CELL}" rx="2" fill="{fill}"/>')

    h = gy + 7 * (CELL + GAP) + 30
    style = (f'text{{font-family:{FONT};fill:{t["text"]}}}'
             f'.b{{font-weight:600}}.t{{fill:{t["text"]}}}.m{{fill:{t["muted"]}}}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">'
            f'<title>LeetCode: {s["solved"]["All"]} solved</title><style>{style}</style>'
            f'<rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="6" fill="none" stroke="{t["border"]}"/>'
            + "".join(out) + "</svg>\n")


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    username, out_dir = sys.argv[1], sys.argv[2]
    stats = parse(fetch(username))
    today = dt.datetime.now(dt.timezone.utc).date()
    os.makedirs(out_dir, exist_ok=True)
    for name, theme in THEMES.items():
        with open(os.path.join(out_dir, f"leetcode-{name}.svg"), "w") as f:
            f.write(render(stats, theme, today))


if __name__ == "__main__":
    main()
