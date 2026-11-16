
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
        languages(first: 100) {
          edges {
            size
            node {
              name
            }
          }
        }
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
# Language byte statistics
language_bytes = Counter()

for repo in repos:
    for edge in repo["languages"]["edges"]:
        language_bytes[edge["node"]["name"]] += edge["size"]

total_language_bytes = sum(language_bytes.values()) or 1

display_languages = [
    "GLSL",
    "Lua",
    "Python",
    "C",
    "Batchfile",
]

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

    <g opacity="0">
      <animate attributeName="opacity"
        from="0" to="1"
        begin="{i * 0.44:.2f}s"
        dur="1.30s"
        fill="freeze"/>
      <animateTransform attributeName="transform"
        type="translate"
        from="0 10" to="0 0"
        begin="{i * 0.44:.2f}s"
        dur="1.30s"
        fill="freeze"/>
      <text x="{x}" y="160" fill="#f3f5ff" font-size="27"
        font-family="Segoe UI,Arial" font-weight="600">{value:,}</text>
    </g>
    '''

svg += svg_end()
write_svg("stats.svg", svg)

# 1.5. Professional Brief
active_days = sum(
    1
    for week in calendar["weeks"]
    for day in week["contributionDays"]
    if day["contributionCount"] > 0
)

svg = svg_start(
    "Professional Snapshot",
    "Recruiter signal brief · hkiceflow",
    900,
    330
)

# Three-column panels
svg += '''
    <rect x="28" y="95" width="270" height="216" rx="12"
      fill="#0c1426" stroke="#34415f" stroke-width="1"/>

    <rect x="315" y="95" width="270" height="216" rx="12"
      fill="#0c1426" stroke="#34415f" stroke-width="1"/>

    <rect x="602" y="95" width="270" height="216" rx="12"
      fill="#0c1426" stroke="#34415f" stroke-width="1"/>

    <text x="48" y="123" fill="#dce5ff" font-size="13"
      font-family="Segoe UI,Arial" font-weight="600">
      职位 / 角色匹配度
    </text>

    <text x="335" y="123" fill="#dce5ff" font-size="13"
      font-family="Segoe UI,Arial" font-weight="600">
      公开证明
    </text>

    <text x="622" y="123" fill="#dce5ff" font-size="13"
      font-family="Segoe UI,Arial" font-weight="600">
      GitHub Momentum
    </text>

    <line x1="44" y1="136" x2="282" y2="136"
      stroke="#34415f" stroke-width="1"/>
    <line x1="331" y1="136" x2="569" y2="136"
      stroke="#34415f" stroke-width="1"/>
    <line x1="618" y1="136" x2="856" y2="136"
      stroke="#34415f" stroke-width="1"/>
'''

# Roles
roles = [
    "软硬件开发工程师",
    "测试工程师",
    "交互设计师",
    "产品经理",
    "CEO",
    "剪辑师",
    "调色师",
]

for i, role in enumerate(roles):
    y = 158 + i * 21
    svg += f'''
    <text x="48" y="{y}" fill="#aebcda" font-size="12"
      font-family="Segoe UI,Arial">{escape(role)}</text>
    '''

# Public proof
svg += f'''
    <text x="340" y="177" fill="#f0f3ff" font-size="29"
      font-family="Segoe UI,Arial" font-weight="600">
      {total_repos}
    </text>
    <text x="340" y="195" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      PUBLIC REPOSITORIES
    </text>

    <text x="340" y="243" fill="#f0f3ff" font-size="29"
      font-family="Segoe UI,Arial" font-weight="600">
      {stars}
    </text>
    <text x="340" y="261" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      TOTAL STARS
    </text>

    <text x="340" y="289" fill="#9eaccb" font-size="11"
      font-family="Segoe UI,Arial">
      SOCIAL ACCOUNTS  ·  OPEN SOURCE
    </text>
'''

# GitHub Momentum
svg += f'''
    <text x="627" y="177" fill="#f0f3ff" font-size="29"
      font-family="Segoe UI,Arial" font-weight="600">
      {contributions}
    </text>
    <text x="627" y="195" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      CONTRIBUTIONS
    </text>

    <text x="627" y="243" fill="#f0f3ff" font-size="29"
      font-family="Segoe UI,Arial" font-weight="600">
      {active_days}
    </text>
    <text x="627" y="261" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      ACTIVE DAYS
    </text>
'''

svg += svg_end()
write_svg("brief.svg", svg)

# 2. Projects
svg = svg_start("Selected Projects", "Most starred repositories", 900, 300)

selected_repos = [
    repo for repo in repos
    if repo["name"].casefold() != "autogrowai"
][:3]

# Project window
svg += '''
    <rect x="28" y="91" width="844" height="184" rx="12"
      fill="#0c1426" stroke="#34415f" stroke-width="1"/>

    <text x="48" y="113" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      HKICEFLOW / PROJECT WINDOW
    </text>

    <circle cx="842" cy="108" r="7" fill="#55e68a" opacity=".18">
      <animate attributeName="opacity"
        values=".18;.04;.18"
        dur="2.2s" repeatCount="indefinite"/>
    </circle>

    <circle cx="842" cy="108" r="3.5" fill="#55e68a">
      <animate attributeName="opacity"
        values="1;.35;1"
        dur="2.2s" repeatCount="indefinite"/>
    </circle>

    <line x1="44" y1="127" x2="856" y2="127"
      stroke="#34415f" stroke-width="1"/>
'''

if selected_repos:
    for i, repo in enumerate(selected_repos):
        y = 151 + i * 40
        name = escape(repo["name"])
        desc = escape((repo["description"] or "No description")[:65])

        svg += f'''
        <text x="48" y="{y}" fill="#dce5ff" font-size="14"
          font-family="Segoe UI,Arial" font-weight="600">{name}</text>

        <text x="48" y="{y+17}" fill="#8493b2" font-size="10"
          font-family="Segoe UI,Arial">{desc}</text>

        <text x="850" y="{y}" text-anchor="end" fill="#a9baff"
          font-size="12" font-family="Segoe UI,Arial">
          ★ {repo["stargazerCount"]}  ·  Forks {repo["forkCount"]}
        </text>
        '''

        if i < len(selected_repos) - 1:
            svg += f'''
            <line x1="48" y1="{y+25}" x2="852" y2="{y+25}"
              stroke="#26334e" stroke-width="1"/>
            '''
else:
    svg += '''
    <text x="48" y="165" fill="#8493b2" font-size="12"
      font-family="Segoe UI,Arial">
      No selected repositories available
    </text>
    '''

svg += svg_end()
write_svg("projects.svg", svg)

# 3. Technology stack
svg = svg_start("Technology Stack", "Primary languages across repositories", 900, 260)

svg += '''
    <text x="872" y="39"
      text-anchor="end"
      fill="#8998b8"
      font-size="11"
      font-family="Consolas,Monaco,monospace"
      letter-spacing=".5">
      &gt; stack.scan
      <tspan fill="#55e68a">_
        <animate attributeName="opacity"
          values="1;0;1"
          dur="1s"
          repeatCount="indefinite"/>
      </tspan>
    </text>
'''

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
# 3.5. Language Distribution
svg = svg_start(
    "Language Distribution",
    "Public code composition",
    900,
    250
)

svg += '''
    <rect x="28" y="94" width="844" height="128" rx="12"
      fill="#0c1426" stroke="#34415f" stroke-width="1"/>
'''

for i, language in enumerate(display_languages):
    x = 48 + i * 164
    count = language_bytes[language]
    percentage = count / total_language_bytes * 100

    svg += f'''
    <text x="{x}" y="125" fill="#dce5ff" font-size="13"
      font-family="Segoe UI,Arial" font-weight="600">
      {escape(language)}
    </text>

    <text x="{x}" y="165" fill="#f0f3ff" font-size="25"
      font-family="Segoe UI,Arial" font-weight="600">
      {percentage:.1f}%
    </text>

    <rect x="{x}" y="183" width="125" height="5" rx="2.5"
      fill="#293550"/>

    <rect x="{x}" y="183" width="{125 * percentage / 100:.2f}"
      height="5" rx="2.5" fill="url(#accent)">
      <animate attributeName="width"
        from="0" to="{125 * percentage / 100:.2f}"
        dur="1.4s" fill="freeze"/>
    </rect>
    '''

svg += svg_end()
write_svg("languages.svg", svg)


# 4. Contribution heatmap
days = [
    day
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]
days = days[-371:]

svg = svg_start("Contribution Activity", "Daily contribution history", 900, 180)

scan_points = []

for i, day in enumerate(days):
    col = i // 7

    # Alternate vertical direction for each column
    row = 6 - (i % 7) if col % 2 == 0 else i % 7

    x = 30 + col * 12
    y = 91 + row * 11

    color = day["color"] or "#202a40"

    svg += f'<rect x="{x}" y="{y}" width="8" height="8" rx="2" fill="{color}"/>'

    # Record the center of each cell for the scanning animation
    scan_points.append((x + 4, y + 4))

# Build a continuous serpentine scanning path
if scan_points:
    scan_path = "M " + " L ".join(
        f"{x} {y}" for x, y in scan_points
    )

    svg += f'''
    <circle r="5" fill="#55e68a" opacity="0.20">
      <animateMotion
        path="{scan_path}"
        dur="42s"
        repeatCount="indefinite"
        calcMode="linear"/>
    </circle>

    <circle r="2.2" fill="#8affb5">
      <animateMotion
        path="{scan_path}"
        dur="42s"
        repeatCount="indefinite"
        calcMode="linear"/>
      <animate
        attributeName="opacity"
        values="1;0.65;1"
        dur="1.2s"
        repeatCount="indefinite"/>
    </circle>
    '''

svg += svg_end()
write_svg("heatmap.svg", svg)

# 5. Social identity card

social_svg = '''<svg xmlns="http://www.w3.org/2000/svg"
width="900" height="220" viewBox="0 0 900 220">

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

  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
    <feGaussianBlur stdDeviation="4" result="blur"/>
    <feMerge>
      <feMergeNode in="blur"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
</defs>

<rect width="900" height="220" rx="18"
      fill="url(#bg)" stroke="#34415f" stroke-width="1"/>

<text x="450" y="43"
      text-anchor="middle"
      fill="#f0f3ff"
      font-size="19"
      font-family="Segoe UI,Arial"
      font-weight="600">Github</text>

<!-- Elliptical orbit -->
<ellipse cx="450" cy="111" rx="119" ry="49"
         fill="none"
         stroke="#34415f"
         stroke-width="1.5"
         opacity=".7"/>

<ellipse cx="450" cy="111" rx="119" ry="49"
         fill="none"
         stroke="url(#accent)"
         stroke-width="2.2"
         stroke-linecap="round"
         stroke-dasharray="230 520"
         filter="url(#glow)">
  <animate attributeName="stroke-dashoffset"
           from="0" to="-750"
           dur="6s"
           repeatCount="indefinite"/>
</ellipse>

<!-- Moving orbit highlight -->
<circle r="4" fill="#8deaff" filter="url(#glow)">
  <animateMotion
    dur="6s"
    repeatCount="indefinite"
    path="M 569,111 A 119,49 0 1,1 331,111 A 119,49 0 1,1 569,111"/>
</circle>

<!-- Central identity -->
<circle cx="450" cy="111" r="34"
        fill="#111a30"
        stroke="url(#accent)"
        stroke-width="2"/>

<text x="450" y="126"
      text-anchor="middle"
      fill="url(#accent)"
      font-size="43"
      font-family="Segoe UI,Arial"
      font-weight="600">I</text>

<text x="450" y="202"
      text-anchor="middle"
      fill="#8998b8"
      font-size="14"
      font-family="Segoe UI,Arial"
      letter-spacing="1">@hkiceflow</text>

</svg>'''

write_svg("social.svg", social_svg)

print("Generated five SVG cards successfully.")

