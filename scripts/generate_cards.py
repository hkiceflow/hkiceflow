
import base64
import os
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
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
    with urllib.request.urlopen(request, timeout=30) as response:
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

      <linearGradient id="rgbBorder"
        x1="0" y1="0" x2="1" y2="1">

        <stop offset="0%" stop-color="#FF0000"/>
        <stop offset="33%" stop-color="#00FF00"/>
        <stop offset="67%" stop-color="#0000FF"/>
        <stop offset="100%" stop-color="#FF0000"/>

        <animateTransform
          attributeName="gradientTransform"
          type="rotate"
          from="0 0.5 0.5"
          to="360 0.5 0.5"
          dur="12s"
          repeatCount="indefinite"/>
      </linearGradient>
    </defs>

    <rect width="100%" height="100%" rx="18" fill="url(#bg)"
      stroke="#34415f" stroke-width="1"/>

    <circle cx="{width-30}" cy="10" r="100"
      fill="#765cff" opacity=".07"/>

    <text x="28" y="39" fill="#f0f3ff" font-size="20"
      font-family="Segoe UI,Arial" font-weight="600">{escape(title)}</text>

    <text x="28" y="61" fill="#8998b8" font-size="11"
      font-family="Segoe UI,Arial" letter-spacing="2">{escape(subtitle.upper())}</text>

    <rect x="28" y="76" width="54" height="3" rx="2"
      fill="url(#accent)"/>
    '''


def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''


def write_svg(filename, content):
    rgb_cards = {
        "stats.svg",
        "brief.svg",
        "projects.svg",
        "stack.svg",
        "languages.svg",
        "heatmap.svg",
    }

    if filename in rgb_cards:
        height = int(
            content.split('height="', 1)[1].split('"', 1)[0]
        )

        content = (
            content.rsplit("</svg>", 1)[0]
            + svg_end(height)
        )

    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        f.write(content)


query = """
{
  user(login: "hkiceflow") {
    name
    login
    avatarUrl
    createdAt
    followers { totalCount }
    repositories(
  first: 100
  after: null
  ownerAffiliations: OWNER
  privacy: PUBLIC
  isFork: false
  orderBy: {field: STARGAZERS, direction: DESC}
) {
  totalCount
  pageInfo {
    hasNextPage
    endCursor
  }
  nodes {
    name
    description
    url
    stargazerCount
    forkCount
    primaryLanguage { name }
   languages(first: 100) {
  pageInfo {
    hasNextPage
    endCursor
  }
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

repo_data = user["repositories"]
repos = repo_data["nodes"]

while repo_data["pageInfo"]["hasNextPage"]:
    cursor = repo_data["pageInfo"]["endCursor"]

    next_query = query.replace(
        "after: null",
        f'after: "{cursor}"'
    )

    repo_data = github_graphql(next_query)["user"]["repositories"]
    repos.extend(repo_data["nodes"])
# Fetch all language pages for each repository
for repo in repos:
    language_data = repo["languages"]

    while language_data["pageInfo"]["hasNextPage"]:
        cursor = language_data["pageInfo"]["endCursor"]

        language_query = f"""
        query {{
          repository(
            owner: {json.dumps(USERNAME)}
            name: {json.dumps(repo["name"])}
          ) {{
            languages(first: 100, after: {json.dumps(cursor)}) {{
              pageInfo {{
                hasNextPage
                endCursor
              }}
              edges {{
                size
                node {{
                  name
                }}
              }}
            }}
          }}
        }}
        """

        language_data = github_graphql(language_query)["repository"]["languages"]
        repo["languages"]["edges"].extend(language_data["edges"])
# Fetch and embed GitHub avatar
avatar_request = urllib.request.Request(
    user["avatarUrl"],
    headers={"User-Agent": "Mozilla/5.0"}
)

with urllib.request.urlopen(avatar_request, timeout=30) as response:
    avatar_mime = response.headers.get_content_type()
    avatar_base64 = base64.b64encode(response.read()).decode("ascii")

avatar_data_uri = f"data:{avatar_mime};base64,{avatar_base64}"

# GitHub account creation time
github_since = user["createdAt"]
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

# Galaxy orbit animation
svg += '''
    <defs>
      <radialGradient id="planetBlue">
        <stop offset="0%" stop-color="#d8f7ff"/>
        <stop offset="35%" stop-color="#62caff"/>
        <stop offset="75%" stop-color="#2585e8"/>
        <stop offset="100%" stop-color="#1550a8"/>
      </radialGradient>

      <filter id="planetGlow" x="-300%" y="-300%"
        width="700%" height="700%">
        <feGaussianBlur stdDeviation="4" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>

    <!-- Diagonal galaxy orbit -->
    <ellipse cx="790" cy="60" rx="85" ry="20"
      transform="rotate(-35 790 60)"
      fill="none"
      stroke="#557bbd"
      stroke-width="1.2"
      opacity=".38"/>

    <ellipse cx="790" cy="60" rx="85" ry="20"
      transform="rotate(-35 790 60)"
      fill="none"
      stroke="#79caff"
      stroke-width="1.5"
      stroke-dasharray="28 190"
      opacity=".65"/>

    <!-- Blue planet glow -->
    <circle r="8" fill="#319dff" opacity=".35"
      filter="url(#planetGlow)">
      <animateMotion
        dur="8s"
        repeatCount="indefinite"
        path="M 859.6,11.3 A 85,20 -35 1,1 720.4,108.7 A 85,20 -35 1,1 859.6,11.3"/>
    </circle>

    <!-- Moving blue planet -->
    <circle r="5.5" fill="url(#planetBlue)"
      stroke="#a8e8ff" stroke-width=".8"
      filter="url(#planetGlow)">
      <animateMotion
        dur="8s"
        repeatCount="indefinite"
        path="M 859.6,11.3 A 85,20 -35 1,1 720.4,108.7 A 85,20 -35 1,1 859.6,11.3"/>
    </circle>

    <!-- Planet highlight -->
    <circle r="1.5" fill="#ffffff" opacity=".9">
      <animateMotion
        dur="8s"
        repeatCount="indefinite"
        path="M 859.6,11.3 A 85,20 -35 1,1 720.4,108.7 A 85,20 -35 1,1 859.6,11.3"/>
    </circle>
'''

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

def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''
write_svg("stats.svg", svg)

# 1.5. Professional Brief
# Calculate current contribution streak
contribution_days = {
    datetime.strptime(day["date"], "%Y-%m-%d").date():
    day["contributionCount"]
    for week in calendar["weeks"]
    for day in week["contributionDays"]
}
calendar_dates = sorted(contribution_days)
latest_date = calendar_dates[-1] if calendar_dates else None

if latest_date:
    streak_date = (
        latest_date
        if contribution_days.get(latest_date, 0) > 0
        else latest_date - timedelta(days=1)
    )
else:
    streak_date = None

current_streak = 0

while (
    streak_date is not None
    and contribution_days.get(streak_date, 0) > 0
):
    current_streak += 1
    streak_date -= timedelta(days=1)
svg = svg_start(
    "Professional Snapshot",
    "Recruiter signal brief · hkiceflow",
    900,
    330
)
# Animated nebula background
nebula_layer = '''
    <defs>
      <clipPath id="briefNebulaClip">
        <rect width="900" height="330" rx="18"/>
      </clipPath>

      <radialGradient id="nebulaBlue">
        <stop offset="0%" stop-color="#398dff" stop-opacity=".48"/>
        <stop offset="55%" stop-color="#3565d8" stop-opacity=".20"/>
        <stop offset="100%" stop-color="#3565d8" stop-opacity="0"/>
      </radialGradient>

      <radialGradient id="nebulaPurple">
        <stop offset="0%" stop-color="#a56aff" stop-opacity=".42"/>
        <stop offset="55%" stop-color="#7951d6" stop-opacity=".18"/>
        <stop offset="100%" stop-color="#7951d6" stop-opacity="0"/>
      </radialGradient>

      <radialGradient id="nebulaCyan">
        <stop offset="0%" stop-color="#55d9ff" stop-opacity=".30"/>
        <stop offset="100%" stop-color="#55d9ff" stop-opacity="0"/>
      </radialGradient>
    </defs>
    
<g clip-path="url(#briefNebulaClip)" pointer-events="none">
 <!-- Slowly rotating nebula -->
      <g>
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="rotate"
          values="0 450 165;360 450 165"
          dur="8s"
          repeatCount="indefinite"/>

        <g opacity=".55">

        <ellipse cx="180" cy="90" rx="260" ry="105"
          fill="url(#nebulaBlue)"/>

        <ellipse cx="650" cy="70" rx="300" ry="115"
          fill="url(#nebulaPurple)"/>

        <ellipse cx="450" cy="230" rx="330" ry="100"
          fill="url(#nebulaCyan)"/>

        <ellipse cx="820" cy="260" rx="230" ry="100"
          fill="url(#nebulaBlue)"/>
        </g>
      </g>

      <!-- Star field -->
      <g fill="#d8eaff">
        <circle cx="105" cy="20" r="1.2">
          <animate attributeName="opacity" values=".25;1;.25" dur="3s" repeatCount="indefinite"/>
        </circle>
        <circle cx="185" cy="52" r=".9">
          <animate attributeName="opacity" values=".2;.9;.2" dur="4s" repeatCount="indefinite"/>
        </circle>
        <circle cx="270" cy="16" r="1.5">
          <animate attributeName="opacity" values=".3;1;.3" dur="2.8s" repeatCount="indefinite"/>
        </circle>
        <circle cx="350" cy="68" r="1">
          <animate attributeName="opacity" values=".2;.8;.2" dur="3.6s" repeatCount="indefinite"/>
        </circle>
        <circle cx="430" cy="18" r="1.3">
          <animate attributeName="opacity" values=".25;1;.25" dur="3.2s" repeatCount="indefinite"/>
        </circle>
        <circle cx="520" cy="48" r=".8">
          <animate attributeName="opacity" values=".2;.9;.2" dur="4.2s" repeatCount="indefinite"/>
        </circle>
        <circle cx="610" cy="17" r="1.4">
          <animate attributeName="opacity" values=".3;1;.3" dur="2.6s" repeatCount="indefinite"/>
        </circle>
        <circle cx="700" cy="58" r="1">
          <animate attributeName="opacity" values=".2;.9;.2" dur="3.8s" repeatCount="indefinite"/>
        </circle>
        <circle cx="790" cy="22" r="1.5">
          <animate attributeName="opacity" values=".25;1;.25" dur="3.1s" repeatCount="indefinite"/>
        </circle>
        <circle cx="860" cy="65" r=".9">
          <animate attributeName="opacity" values=".2;.8;.2" dur="4s" repeatCount="indefinite"/>
        </circle>

        <circle cx="55" cy="90" r="1.1"/>
        <circle cx="145" cy="78" r=".8"/>
        <circle cx="235" cy="88" r="1.3"/>
        <circle cx="325" cy="95" r=".8"/>
        <circle cx="415" cy="83" r="1.1"/>
        <circle cx="505" cy="92" r="1.4"/>
        <circle cx="595" cy="78" r=".9"/>
        <circle cx="685" cy="91" r="1.2"/>
        <circle cx="775" cy="82" r=".8"/>
        <circle cx="845" cy="100" r="1.2"/>

        <circle cx="18" cy="180" r="1"/>
        <circle cx="880" cy="155" r="1.2"/>
        <circle cx="15" cy="270" r="1.3"/>
        <circle cx="885" cy="285" r=".9"/>
        <circle cx="100" cy="320" r="1"/>
        <circle cx="300" cy="318" r="1.2"/>
        <circle cx="570" cy="320" r=".9"/>
        <circle cx="800" cy="318" r="1.3"/>
      </g>
    </g>
'''

svg = svg.replace(
    '    <circle cx="870" cy="10" r="100"',
    nebula_layer + '    <circle cx="870" cy="10" r="100"',
    1
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
svg += '''
    <a href="https://github.com/hkiceflow/mpv_video"
       target="_blank">
      <!-- mpv purple logo -->
      <circle cx="359" cy="174" r="19" fill="#ffffff"/>
      <circle cx="359" cy="174" r="17" fill="#493078"/>
      <circle cx="359" cy="174" r="14" fill="#8056c7"/>
      <circle cx="359" cy="174" r="9.5" fill="#f2edff"/>
      <path d="M356 168.5 L364.5 174 L356 179.5 Z"
        fill="#6741a8"/>

      <text x="389" y="173" fill="#f0f3ff" font-size="13"
        font-family="Segoe UI,Arial" font-weight="600">
        mpv_video
      </text>
      <text x="389" y="191" fill="#8abaff" font-size="10"
        font-family="Segoe UI,Arial">
        github.com/hkiceflow/mpv_video
      </text>
    </a>

    <a href="https://space.bilibili.com/368780828"
       target="_blank">
      <!-- Bilibili logo -->
      <rect x="342" y="221" width="34" height="27" rx="7"
        fill="#00a1d6"/>
      <path d="M350 220 L346 214 M368 220 L372 214"
        stroke="#00a1d6" stroke-width="3" stroke-linecap="round"/>
      <path d="M352 232 V239 M366 232 V239"
        stroke="#ffffff" stroke-width="3" stroke-linecap="round"/>

      <text x="389" y="237" fill="#f0f3ff" font-size="13"
        font-family="Segoe UI,Arial" font-weight="600">
        哔哩哔哩
      </text>
      <text x="389" y="255" fill="#8abaff" font-size="10"
        font-family="Segoe UI,Arial">
        space.bilibili.com/368780828
      </text>
    </a>
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
      {current_streak}
    </text>
    <text x="627" y="261" fill="#8998b8" font-size="10"
      font-family="Segoe UI,Arial" letter-spacing="1.2">
      CURRENT STREAK
    </text>
'''

def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''
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

def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''
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
def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''
write_svg("stack.svg", svg)
# 3.5. Language Distribution
svg = svg_start(
    "Language Distribution",
    "Public code composition",
    900,
    250
)

# Animated four-color nebula background
svg += '''
    <defs>
      <radialGradient id="langNebulaBlue">
        <stop offset="0%" stop-color="#2457c5" stop-opacity=".58"/>
        <stop offset="45%" stop-color="#2457c5" stop-opacity=".30"/>
        <stop offset="100%" stop-color="#2457c5" stop-opacity="0"/>
      </radialGradient>

      <radialGradient id="langNebulaPurple">
        <stop offset="0%" stop-color="#8549d6" stop-opacity=".52"/>
        <stop offset="48%" stop-color="#8549d6" stop-opacity=".26"/>
        <stop offset="100%" stop-color="#8549d6" stop-opacity="0"/>
      </radialGradient>

      <radialGradient id="langNebulaOrange">
        <stop offset="0%" stop-color="#e76a35" stop-opacity=".44"/>
        <stop offset="48%" stop-color="#e76a35" stop-opacity=".22"/>
        <stop offset="100%" stop-color="#e76a35" stop-opacity="0"/>
      </radialGradient>

      <radialGradient id="langNebulaGreen">
        <stop offset="0%" stop-color="#22b99a" stop-opacity=".48"/>
        <stop offset="48%" stop-color="#22b99a" stop-opacity=".24"/>
        <stop offset="100%" stop-color="#22b99a" stop-opacity="0"/>
      </radialGradient>

      <filter id="langNebulaBlur"
        x="-50%" y="-100%" width="200%" height="300%">
        <feGaussianBlur stdDeviation="22"/>
      </filter>
    </defs>

    <!-- Clockwise rotating nebula -->
    <g filter="url(#langNebulaBlur)" pointer-events="none">
      <g>
        <animateTransform
          attributeName="transform"
          attributeType="XML"
          type="rotate"
          values="0 450 125;360 450 125"
          dur="8s"
          repeatCount="indefinite"/>

        <!-- Deep blue -->
        <circle cx="145" cy="20" r="245"
          fill="url(#langNebulaBlue)" opacity=".75">
          <animate attributeName="r"
            values="220;285;220"
            dur="12s" repeatCount="indefinite"/>
          <animate attributeName="opacity"
            values=".72;.38;.72"
            dur="12s" repeatCount="indefinite"/>
        </circle>

        <!-- Purple -->
        <circle cx="760" cy="15" r="250"
          fill="url(#langNebulaPurple)" opacity=".72">
          <animate attributeName="r"
            values="225;290;225"
            dur="15s" repeatCount="indefinite"/>
          <animate attributeName="opacity"
            values=".68;.34;.68"
            dur="15s" repeatCount="indefinite"/>
        </circle>

        <!-- Orange red -->
        <circle cx="760" cy="235" r="245"
          fill="url(#langNebulaOrange)" opacity=".68">
          <animate attributeName="r"
            values="215;280;215"
            dur="13s" repeatCount="indefinite"/>
          <animate attributeName="opacity"
            values=".62;.30;.62"
            dur="13s" repeatCount="indefinite"/>
        </circle>

        <!-- Cyan green -->
        <circle cx="140" cy="235" r="250"
          fill="url(#langNebulaGreen)" opacity=".70">
          <animate attributeName="r"
            values="220;290;220"
            dur="14s" repeatCount="indefinite"/>
          <animate attributeName="opacity"
            values=".66;.32;.66"
            dur="14s" repeatCount="indefinite"/>
        </circle>
      </g>
    </g>
'''

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

def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''
write_svg("languages.svg", svg)


# 4. Contribution heatmap
days = [
    day
    for week in calendar["weeks"]
    for day in week["contributionDays"]
]
days = days[-371:]

svg = svg_start("Contribution Activity", "Daily contribution history", 900, 180)

# Contribution intensity legend
svg += '''
    <g>
      <text x="744" y="57"
        fill="#8998b8" font-size="10"
        font-family="Segoe UI,Arial">Less</text>

      <rect x="775" y="48" width="8" height="8" rx="2"
        fill="#B5EBC7"/>
      <rect x="787" y="48" width="8" height="8" rx="2"
        fill="#78D99A"/>
      <rect x="799" y="48" width="8" height="8" rx="2"
        fill="#43B978"/>
      <rect x="811" y="48" width="8" height="8" rx="2"
        fill="#239F61"/>
      <rect x="823" y="48" width="8" height="8" rx="2"
        fill="#16834D"/>

      <text x="841" y="57"
        fill="#8998b8" font-size="10"
        font-family="Segoe UI,Arial">More</text>
    </g>
'''

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





# Build serpentine scanning animation with a fixed four-cell trail
if len(scan_points) >= 5:
    scan_path = "M " + " L ".join(
        f"{x} {y}" for x, y in scan_points
    )

    scan_duration = 42.0
    trail_length = 4

    # Calculate cumulative distances along the serpentine path
    cumulative_distances = [0.0]

    for i in range(1, len(scan_points)):
        x1, y1 = scan_points[i - 1]
        x2, y2 = scan_points[i]

        segment_length = (
            (x2 - x1) ** 2 + (y2 - y1) ** 2
        ) ** 0.5

        cumulative_distances.append(
            cumulative_distances[-1] + segment_length
        )

    total_distance = cumulative_distances[-1]

    # Trail colors: nearest to farthest
    trail_colors = [
        "#239F61",
        "#43B978",
        "#78D99A",
        "#B5EBC7",
    ]

    # Initial head position: fifth cell
    head_offset = (
        cumulative_distances[trail_length]
        / total_distance
        * scan_duration
    )

    # Hide the entire five-cell train briefly before the path resets
    hide_start = (scan_duration - head_offset) / scan_duration
    fade_duration = min(0.002, hide_start / 2)
    hide_end = hide_start + fade_duration

    svg += '''
    <defs>
      <filter id="scanGlow" x="-100%" y="-100%"
        width="300%" height="300%">
        <feGaussianBlur stdDeviation="3"/>
      </filter>
    </defs>
    '''

    # All five cells move as one visual train
    svg += '<g id="scanTrain">'

    # Four complete trail cells, present from the first frame
    for trail_index in range(trail_length):
        color = trail_colors[trail_length - 1 - trail_index]

        trail_offset = (
            cumulative_distances[trail_index]
            / total_distance
            * scan_duration
        )

        svg += f'''
        <rect x="-4" y="-4" width="8" height="8" rx="2"
          fill="{color}" opacity="1">
          <animateMotion
            path="{scan_path}"
            dur="{scan_duration}s"
            begin="-{trail_offset:.6f}s"
            repeatCount="indefinite"
            calcMode="paced"/>
        </rect>
        '''

    # Soft glow behind the scanning head
    svg += f'''
    <rect x="-4" y="-4" width="8" height="8" rx="2"
      fill="#16834D" opacity=".45"
      filter="url(#scanGlow)">
      <animateMotion
        path="{scan_path}"
        dur="{scan_duration}s"
        begin="-{head_offset:.6f}s"
        repeatCount="indefinite"
        calcMode="paced"/>
    </rect>

    <!-- Full-size dark-green scanning head -->
    <rect x="-4" y="-4" width="8" height="8" rx="2"
      fill="#16834D" opacity="1">
      <animateMotion
        path="{scan_path}"
        dur="{scan_duration}s"
        begin="-{head_offset:.6f}s"
        repeatCount="indefinite"
        calcMode="paced"/>
    </rect>
    '''

    # Hide all five cells together during the loop reset
    svg += f'''
      <animate
        attributeName="opacity"
        values="1;1;0;0"
        keyTimes="0;{hide_start:.6f};{hide_end:.6f};1"
        dur="{scan_duration}s"
        repeatCount="indefinite"/>
    </g>
    '''
def svg_end(height=220):
    return f'''
    <rect x="2" y="2"
      width="896" height="{height - 4}"
      rx="16"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4"/>
    </svg>
    '''

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
  <!-- RGB flowing border -->
  <linearGradient id="rgbBorder"
    x1="0" y1="0" x2="1" y2="1">

    <stop offset="0%" stop-color="#0000FF"/>
    <stop offset="32%" stop-color="#0000FF"/>
    <stop offset="34%" stop-color="#00FF00"/>

    <stop offset="65%" stop-color="#00FF00"/>
    <stop offset="67%" stop-color="#FF0000"/>
    <stop offset="98%" stop-color="#FF0000"/>

    <stop offset="100%" stop-color="#0000FF"/>

    <animateTransform
      attributeName="gradientTransform"
      type="rotate"
      from="0 0.5 0.5"
      to="360 0.5 0.5"
      dur="12s"
      repeatCount="indefinite"/>
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
<!-- RGB flowing border -->
<rect x="2" y="2"
  width="896" height="216"
  rx="16"
  fill="none"
  stroke="url(#rgbBorder)"
  stroke-width="4"/>
</svg>'''

write_svg("social.svg", social_svg)

# 7. Animated gradient divider
svg = '''

<svg xmlns="http://www.w3.org/2000/svg"
     width="900" height="36"
     viewBox="0 0 900 36">

  <defs>
    <linearGradient id="dividerGradient"
      gradientUnits="userSpaceOnUse"
      x1="12" y1="18" x2="888" y2="18">
      <stop offset="0%" stop-color="#174CBB"/>
      <stop offset="100%" stop-color="#E21D36"/>
    </linearGradient>
  </defs>

  <!-- Gradient line -->
  <line x1="12" y1="18" x2="888" y2="18"
    stroke="url(#dividerGradient)"
    stroke-width="2"/>

  <!-- Left blue keyframe -->
  <path d="M12 10 L20 18 L12 26 L4 18 Z"
    fill="#174CBB"/>

  <!-- Right red keyframe -->
  <path d="M888 10 L896 18 L888 26 L880 18 Z"
    fill="#E21D36"/>

  <!-- Moving light glow -->
  <circle r="12" fill="#174CBB" opacity=".08">
    <animateMotion
      dur="7s"
      repeatCount="indefinite"
      path="M12 18 L888 18 L12 18"/>
    <animate
      attributeName="fill"
      values="#174CBB;#E21D36;#174CBB"
      keyTimes="0;0.5;1"
      calcMode="linear"
      dur="7s"
      repeatCount="indefinite"/>
  </circle>

  <circle r="8" fill="#174CBB" opacity=".16">
    <animateMotion
      dur="7s"
      repeatCount="indefinite"
      path="M12 18 L888 18 L12 18"/>
    <animate
      attributeName="fill"
      values="#174CBB;#E21D36;#174CBB"
      keyTimes="0;0.5;1"
      calcMode="linear"
      dur="7s"
      repeatCount="indefinite"/>
  </circle>

  <!-- Moving gradient-colored dot -->
  <circle r="5" fill="#174CBB">
    <animateMotion
      dur="7s"
      repeatCount="indefinite"
      path="M12 18 L888 18 L12 18"/>
    <animate
      attributeName="fill"
      values="#174CBB;#E21D36;#174CBB"
      keyTimes="0;0.5;1"
      calcMode="linear"
      dur="7s"
      repeatCount="indefinite"/>
  </circle>

</svg>
'''

write_svg("divider.svg", svg)

# 8. Animated GitHub profile card
profile_svg = f'''
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="900" height="900"
     viewBox="0 0 900 900">

  <defs>
    <!-- Background -->
    <linearGradient id="profileBg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#020817"/>
      <stop offset="50%" stop-color="#071b43"/>
      <stop offset="100%" stop-color="#020817"/>
    </linearGradient>

    <radialGradient id="blueNebula">
      <stop offset="0%" stop-color="#1769e8" stop-opacity=".55"/>
      <stop offset="55%" stop-color="#1249a5" stop-opacity=".20"/>
      <stop offset="100%" stop-color="#1249a5" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="purpleNebula">
      <stop offset="0%" stop-color="#7654ff" stop-opacity=".30"/>
      <stop offset="100%" stop-color="#7654ff" stop-opacity="0"/>
    </radialGradient>

<linearGradient id="rgbBorder"
  x1="0" y1="0" x2="1" y2="1">

  <stop offset="0%" stop-color="#FF0000"/>
  <stop offset="33%" stop-color="#00FF00"/>
  <stop offset="67%" stop-color="#0000FF"/>
  <stop offset="100%" stop-color="#FF0000"/>

  <animateTransform
    attributeName="gradientTransform"
    type="rotate"
    from="0 0.5 0.5"
    to="360 0.5 0.5"
    dur="12s"
    repeatCount="indefinite"/>
</linearGradient>
    <linearGradient id="avatarBorder" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#168dff"/>
      <stop offset="50%" stop-color="#a9eaff"/>
      <stop offset="100%" stop-color="#397dff"/>
    </linearGradient>

    <linearGradient id="planetLight" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#1249a5" stop-opacity="0"/>
      <stop offset="50%" stop-color="#64caff"/>
      <stop offset="100%" stop-color="#1249a5" stop-opacity="0"/>
    </linearGradient>

    <!-- Reflection: brightest in the center, fading on both sides -->
    <linearGradient id="reflectionGradient"
      x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0"/>
      <stop offset="42%" stop-color="#ffffff" stop-opacity="0.02"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.34"/>
      <stop offset="58%" stop-color="#ffffff" stop-opacity="0.02"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </linearGradient>

    <clipPath id="profileClip">
      <rect x="35" y="25" width="830" height="830" rx="30"/>
    </clipPath>

    <clipPath id="avatarClip">
        <rect x="87" y="187.5" width="726" height="495" rx="18"/>
    </clipPath>
  </defs>

  <!-- Entire card swings around its bottom-center pivot -->
  <g>
    <animateTransform
      attributeName="transform"
      type="rotate"
      values="-1.2 450 850;1.2 450 850;-1.2 450 850"
      keyTimes="0;0.5;1"
      calcMode="spline"
      keySplines="0.42 0 0.58 1;0.42 0 0.58 1"
      dur="6s"
      repeatCount="indefinite"/>

    <!-- Card background -->
    <rect x="35" y="25" width="830" height="830"
      rx="30" fill="url(#profileBg)"
      stroke="#173d78" stroke-width="1.5"/>

    <g clip-path="url(#profileClip)">

      <!-- Nebula -->
      <ellipse cx="270" cy="390" rx="390" ry="330"
        fill="url(#blueNebula)"/>

      <ellipse cx="700" cy="280" rx="330" ry="300"
        fill="url(#purpleNebula)"/>

      <ellipse cx="480" cy="720" rx="420" ry="260"
        fill="url(#blueNebula)"/>

      <!-- Star field -->
      <g fill="#b9ddff">
        <circle cx="105" cy="115" r="1.5" opacity=".8"/>
        <circle cx="185" cy="230" r="1" opacity=".6"/>
        <circle cx="300" cy="155" r="1.3" opacity=".8"/>
        <circle cx="405" cy="105" r="1" opacity=".5"/>
        <circle cx="545" cy="190" r="1.5" opacity=".7"/>
        <circle cx="690" cy="120" r="1" opacity=".7"/>
        <circle cx="790" cy="220" r="1.5" opacity=".8"/>
        <circle cx="120" cy="390" r="1" opacity=".6"/>
        <circle cx="180" cy="540" r="1.5" opacity=".8"/>
        <circle cx="730" cy="440" r="1" opacity=".7"/>
        <circle cx="790" cy="570" r="1.4" opacity=".6"/>
        <circle cx="110" cy="680" r="1.3" opacity=".7"/>
        <circle cx="250" cy="750" r="1" opacity=".6"/>
        <circle cx="650" cy="700" r="1.4" opacity=".8"/>
        <circle cx="780" cy="760" r="1" opacity=".6"/>
        <circle cx="470" cy="650" r="1" opacity=".7"/>
      </g>

      <!-- Twinkling stars -->
      <g fill="#d8f2ff">
        <circle cx="145" cy="300" r="2">
          <animate attributeName="opacity"
            values=".25;1;.25" dur="3s"
            repeatCount="indefinite"/>
        </circle>
        <circle cx="750" cy="350" r="2">
          <animate attributeName="opacity"
            values="1;.2;1" dur="4s"
            repeatCount="indefinite"/>
        </circle>
        <circle cx="350" cy="690" r="2">
          <animate attributeName="opacity"
            values=".2;1;.2" dur="3.5s"
            repeatCount="indefinite"/>
        </circle>
      </g>

      <!-- Username -->
      <text x="90" y="155"
        fill="#ffffff"
        font-family="Arial, sans-serif"
        font-size="76"
        font-weight="bold">
        iceflow
      </text>

      <!-- Total stars -->
      <g>
        <path d="M730 90
          L741 116 L769 118
          L748 136 L754 164
          L730 149 L706 164
          L712 136 L691 118
          L719 116 Z"
          fill="#FFD84D"/>

        <text x="840" y="150"
          fill="#FFE45C"
          font-family="Arial, sans-serif"
          font-size="48"
          font-weight="bold"
          text-anchor="end">{stars}</text>
      </g>

      <!-- Rectangular avatar -->

      <image
        x="87" y="187.5"
        width="726" height="495"
        xlink:href="{avatar_data_uri}"
        preserveAspectRatio="xMidYMid meet"
        clip-path="url(#avatarClip)"/>

      <!-- Avatar subtle inner outline -->

      <!-- Planet horizon -->
      <path
        d="M35 835
           Q450 680 865 835
           L865 855 L35 855 Z"
        fill="#09295e"/>

      <path
        d="M35 835
           Q450 680 865 835"
        fill="none"
        stroke="url(#planetLight)"
        stroke-width="4"/>

      <path
        d="M35 842
           Q450 700 865 842"
        fill="none"
        stroke="#3289e8"
        stroke-opacity=".25"
        stroke-width="2"/>

            <!-- SINCE -->
      <text x="450" y="740"
        fill="#c6e5ff"
        font-family="monospace"
        font-size="26"
        letter-spacing="2"
        text-anchor="middle">
        SINCE {github_since}
      </text>

      <!-- Moving diagonal reflection -->
      <g clip-path="url(#profileClip)">
        <g>
          <rect x="-1100" y="-100"
            width="2200" height="1100"
            fill="url(#reflectionGradient)"
            transform="skewX(-25)"/>

          <animateTransform
            attributeName="transform"
            type="translate"
            values="-1500 0;1500 0"
            dur="5s"
            repeatCount="indefinite"/>
        </g>
       </g>

    <!-- RGB flowing border: follows the card swing -->
    <rect x="37" y="27"
      width="826" height="826"
      rx="28"
      fill="none"
      stroke="url(#rgbBorder)"
      stroke-width="4.4"/>

    </g>
  </g>
</svg>
'''

write_svg("profile.svg", profile_svg)

print("Generated SVG cards successfully.")
