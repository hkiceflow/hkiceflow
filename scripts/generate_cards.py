
import os
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from xml.sax.saxutils import escape

USERNAME = "hkiceflow"
TOKEN = os.environ["GITHUB_TOKEN"]
OUTPUT_DIR = "assets/gitskins-replacement"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def github_graphql(query):
    data = json.dumps({"query": query}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=data,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": USERNAME,
        },
    )
    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read())
    if "errors" in result:
        raise RuntimeError(result["errors"])

    return result["data"]


def svg_start(title, subtitle, width=900, height=220):
    return f'''<svg xmlns="http://www.w3.org/2000/svg"
    width="{width}" height="{height}" viewBox="0 0 {width} {height}">
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#10182d"/>
        <stop offset="100%" stop-color="#17112b"/>
      </linearGradient>
      <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#62a8ff"/>
        <stop offset="55%" stop-color="#9b7bff"/>
        <stop offset="100%" stop-color="#e18bff"/>
      </linearGradient>
    </defs>
    <rect width="100%" height="100%" rx="18" fill="url(#bg)"
      stroke="#34415f" stroke-width="1"/>
    <circle cx="{width-30}" cy="10" r="100" fill="#765cff" opacity=".07"/>
    <text x="28" y="39" fill="#f0f3ff" font-size="20"
      font-family="Segoe UI,Arial" font-weight="600">{escape(title)}</text>
    <text x="28" y="61" fill="#8998b8" font-size="11"
      font-family="Segoe UI,Arial" letter-spacing="2">{escape(subtitle.upper())}</text>
    <rect x="28" y="76" width="54" height="3" rx="2" fill="url(#accent)"/>
    '''


def svg_end():
    return "</svg>"


def write_svg(filename, content):
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(content)


query = """
{
  user(login: "hkiceflow") {
    name
    login
    followers { totalCount }
    repositories(
      first: 100
      ownerAffiliations: OWNER
      privacy: PUBLIC
      isFork: false
      orderBy: {field: STARGAZERS, direction: DESC}
    ) {
      totalCount
      nodes {
        name
        description
        url
        stargazerCount
        forkCount
        primaryLanguage { name }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

user = github_graphql(query)["user"]
repos = user["repositories"]["nodes"]
calendar = user["contributionsCollection"]["contributionCalendar"]
total_repos = user["repositories"]["totalCount"]
stars = sum(repo["stargazerCount"] for repo in repos)
forks = sum(repo["forkCount"] for repo in repos)
followers = user["followers"]["totalCount"]
contributions = calendar["totalContributions"]
languages = Counter(
    repo["primaryLanguage"]["name"]
    for repo in repos
    if repo["primaryLanguage"]
)

# 1. Statistics
svg = svg_start("GitHub Overview", "Profile statistics", 900, 190)
stats = [
    ("REPOSITORIES", total_repos),
    ("STARS", stars),
    ("CONTRIBUTIONS", contributions),
    ("FOLLOWERS", followers),
]
for i, (label, value) in enumerate(stats):
    x = 28 + i * 218
    svg += f'''
    <text x="{x}" y="125" fill="#8d9ab8" font-size="11"
      font-family="Segoe UI,Arial">{label}</text>
    <text x="{x}" y="160" fill="#f3f5ff" font-size="27"
      font-family="Segoe UI,Arial" font-weight="600">{value:,}</text>
    '''
svg += svg_end()
write_svg("stats.svg", svg)

# 2. Projects
svg = svg_start("Selected Projects", "Most starred repositories", 900, 300)
selected_repos = [
    repo for repo in repos
    if repo["name"].casefold() != "autogrowai"
][:3]

for i, repo in enumerate(selected_repos):
    y = 112 + i * 43
    name = escape(repo["name"])
    desc = escape((repo["description"] or "No description")[:65])
    svg += f'''
    <text x="30" y="{y}" fill="#dce5ff" font-size="14"
      font-family="Segoe UI,Arial" font-weight="600">{name}</text>
    <text x="30" y="{y+17}" fill="#8493b2" font-size="10"
      font-family="Segoe UI,Arial">{desc}</text>
    <text x="850" y="{y}" text-anchor="end" fill="#a9baff"
      font-size="12" font-family="Segoe UI,Arial">
      ★ {repo["stargazerCount"]}  ·  Forks {repo["forkCount"]}
    </text>
    '''
svg += svg_end()
write_svg("projects.svg", svg)

# 3. Technology stack
svg = svg_start("Technology Stack", "Primary languages across repositories", 900, 260)
top_languages = languages.most_common(6)
total_languages = sum(languages.values()) or 1
for i, (language, count) in enumerate(top_languages):
    y = 112 + i * 24
    bar_width = int(430 * count / max(languages.values()))
    svg += f'''
    <text x="30" y="{y}" fill="#dce5ff" font-size="12"
      font-family="Segoe UI,Arial">{escape(language)}</text>
    <rect x="180" y="{y-12}" width="430" height="8" rx="4"
      fill="#293550"/>
    <rect x="180" y="{y-12}" width="{bar_width}" height="8" rx="4"
      fill="url(#accent)"/>
    <text x="630" y="{y-2}" fill="#9eaccb" font-size="11"
      font-family="Segoe UI,Arial">{count} repositories</text>
    '''
if not top_languages:
    svg += '<text x="30" y="120" fill="#9eaccb">No language data available</text>'
svg += svg_end()
write_svg("stack.svg", svg)

# 4. Contribution heatmap
days = [
    day
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]
days = days[-371:]

svg = svg_start("Contribution Activity", "Daily contribution history", 900, 180)
for i, day in enumerate(days):
    col = i // 7
    row = i % 7
    x = 30 + col * 12
    y = 91 + row * 11
    color = day["color"] or "#202a40"
    svg += f'<rect x="{x}" y="{y}" width="8" height="8" rx="2" fill="{color}"/>'
svg += svg_end()
write_svg("heatmap.svg", svg)

print("Generated four SVG cards successfully.")
