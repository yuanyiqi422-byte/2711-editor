"""Generate landing page SVG art (rich Ghibli watercolor style)."""
from __future__ import annotations

import importlib.util
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "frontend" / "images"


def _load_scene_helpers():
    path = Path(__file__).resolve().parent / "generate-scene-svgs.py"
    spec = importlib.util.spec_from_file_location("scene_svgs", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


S = _load_scene_helpers()


def _hero_cottage(rng: random.Random) -> str:
    parts = [
        '<rect x="408" y="728" width="248" height="28" rx="4" fill="#8a9098" opacity="0.38"/>',
        '<rect x="432" y="652" width="200" height="98" rx="10" fill="#faf6ed" opacity="0.84"/>',
        '<rect x="448" y="668" width="168" height="72" rx="6" fill="#eef5e8" opacity="0.35"/>',
        '<polygon points="420,652 532,572 644,652" fill="#c45c6a" opacity="0.72"/>',
        '<polygon points="448,652 532,598 616,652" fill="#f8a8c8" opacity="0.28"/>',
        '<rect x="572" y="588" width="28" height="78" rx="4" fill="#7a8088" opacity="0.58"/>',
        '<ellipse cx="586" cy="572" rx="22" ry="14" fill="#eef5e8" opacity="0.32"/>',
        '<rect x="498" y="708" width="52" height="48" rx="6" fill="#5a4a38" opacity="0.55"/>',
        '<circle cx="524" cy="732" r="4" fill="#ffc8dd" opacity="0.65"/>',
    ]
    for wx, wy in ((468, 688), (528, 688), (588, 688)):
        parts.extend([
            f'<rect x="{wx}" y="{wy}" width="34" height="38" rx="4" fill="#a8d4ff" opacity="0.42"/>',
            f'<rect x="{wx + 4}" y="{wy + 4}" width="26" height="30" rx="3" fill="#7eb8ff" opacity="0.28"/>',
            f'<line x1="{wx + 17}" y1="{wy}" x2="{wx + 17}" y2="{wy + 38}" stroke="#faf6ed" stroke-width="2" opacity="0.45"/>',
            f'<line x1="{wx}" y1="{wy + 19}" x2="{wx + 34}" y2="{wy + 19}" stroke="#faf6ed" stroke-width="2" opacity="0.45"/>',
        ])
    for fx in (452, 612):
        parts.extend([
            f'<rect x="{fx}" y="718" width="48" height="14" rx="3" fill="#5a4a38" opacity="0.42"/>',
            f'<circle cx="{fx + 12}" cy="712" r="6" fill="#ffc8dd" opacity="0.62"/>',
            f'<circle cx="{fx + 24}" cy="710" r="5" fill="#f8a8c8" opacity="0.55"/>',
            f'<circle cx="{fx + 36}" cy="712" r="6" fill="#c8b8e8" opacity="0.5"/>',
        ])
    for _ in range(6):
        sx = rng.randint(430, 620)
        parts.append(
            f'<ellipse cx="{sx}" cy="{rng.randint(560, 600)}" rx="{rng.randint(4, 9)}" '
            f'ry="{rng.randint(3, 6)}" fill="#eef5e8" opacity="0.22"/>'
        )
    return "\n  ".join(parts)


def _hero_windmill() -> str:
    cx, cy = 1380, 520
    blades = []
    for angle in range(0, 360, 45):
        blades.append(
            f'<ellipse cx="{cx}" cy="{cy - 95}" rx="22" ry="98" fill="#eef5e8" opacity="0.52" '
            f'transform="rotate({angle} {cx} {cy})"/>'
            f'<ellipse cx="{cx}" cy="{cy - 95}" rx="10" ry="88" fill="#faf6ed" opacity="0.38" '
            f'transform="rotate({angle} {cx} {cy})"/>'
        )
    return (
        f'<rect x="{cx - 48}" y="{cy + 10}" width="96" height="210" rx="10" fill="#faf6ed" opacity="0.78"/>'
        f'<rect x="{cx - 38}" y="{cy + 30}" width="76" height="170" rx="6" fill="#eef5e8" opacity="0.35"/>'
        f'<polygon points="{cx - 58},{cy + 220} {cx + 58},{cy + 220} {cx + 68},{cy + 248} '
        f'{cx - 68},{cy + 248}" fill="#e8dcc8" opacity="0.55"/>'
        f'<rect x="{cx - 18}" y="{cy + 120}" width="36" height="48" rx="5" fill="#5a4a38" opacity="0.42"/>'
        f'<rect x="{cx - 12}" y="{cy + 58}" width="24" height="28" rx="4" fill="#a8d4ff" opacity="0.38"/>'
        f'<circle cx="{cx}" cy="{cy}" r="20" fill="#8a9098" opacity="0.65"/>'
        f'<circle cx="{cx}" cy="{cy}" r="10" fill="#5a5048" opacity="0.5"/>'
        + "".join(blades)
    )


def _hero_torii() -> str:
    return (
        '<rect x="828" y="598" width="264" height="18" rx="5" fill="#c45c6a" opacity="0.88"/>'
        '<rect x="848" y="616" width="224" height="12" rx="3" fill="#a04050" opacity="0.72"/>'
        '<rect x="868" y="468" width="22" height="148" rx="4" fill="#c45c6a" opacity="0.82"/>'
        '<rect x="1030" y="468" width="22" height="148" rx="4" fill="#c45c6a" opacity="0.82"/>'
        '<rect x="948" y="438" width="24" height="178" rx="3" fill="#8a3038" opacity="0.68"/>'
    )


def _hero_path(rng: random.Random) -> str:
    pts = ["M960,1080", "M960,1080"]
    y, x = 1080, 960
    for _ in range(10):
        y -= rng.randint(55, 95)
        x += rng.randint(-70, 70)
        pts.append(f"L{x},{y}")
    d = " ".join(pts)
    stones = []
    for i in range(12):
        sx = 960 + rng.randint(-120, 120)
        sy = 880 + i * 18
        stones.append(
            f'<ellipse cx="{sx}" cy="{sy}" rx="{rng.randint(10, 18)}" ry="{rng.randint(6, 10)}" '
            f'fill="#c8b8a8" opacity="0.42"/>'
        )
    return (
        f'<path d="{d}" fill="none" stroke="#faf6ed" stroke-width="52" stroke-linecap="round" opacity="0.32"/>'
        f'<path d="{d}" fill="none" stroke="#e8dcc8" stroke-width="6" stroke-dasharray="14 20" opacity="0.22"/>'
        + "".join(stones)
    )


def hero_svg() -> str:
    rng = random.Random(2711)
    clouds = S._clouds(rng, 14)
    hills = S._hills(rng, "#6b8e6b", "#8ab898")
    mountains = (
        '<path d="M0,480 Q240,420 480,460 T960,440 T1440,470 T1920,450 L1920,1080 L0,1080 Z" '
        'fill="#6b8e6b" opacity="0.32"/>'
        '<path d="M0,560 Q320,500 640,540 T1280,520 T1920,550 L1920,1080 L0,1080 Z" '
        'fill="#8ab898" opacity="0.38"/>'
        '<polygon points="680,640 860,420 1040,640" fill="#5a7860" opacity="0.38"/>'
        '<polygon points="760,640 860,520 960,640" fill="#8ab898" opacity="0.3"/>'
    )
    trees_left = S._tree_grove(rng, 9, "#6b8e6b", 900)
    trees_right = S._tree_grove(random.Random(88), 8, "#5a7860", 920)
    village = S._distant_village(random.Random(19), "#8ab898", "#6b8e6b")
    wash = S._watercolor_wash(rng, "#a8d4ff", "#b8d4c8", "#8ab898", 32)
    rays = S._light_rays("#ffc8dd")
    birds = S._birds(rng, 12)
    grass = S._grass_foreground(rng, 95)
    flowers = S._wildflowers_dense(rng, 42)
    fence = S._wood_fence(rng, 998)
    bokeh = S._bokeh(rng, "#ffc8dd", 22)
    figure = S._figure_silhouette(820, 820, 1.15)
    petals = "\n  ".join(
        f'<ellipse cx="{rng.randint(80, 1840)}" cy="{rng.randint(160, 780)}" '
        f'rx="{rng.randint(7, 14)}" ry="{rng.randint(4, 8)}" fill="#ffc8dd" opacity="0.48" '
        f'transform="rotate({rng.randint(0, 180)} {rng.randint(80, 1840)} 400)"/>'
        for _ in range(28)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" role="img" aria-label="风旅物语 Hero">
  <defs>
    <linearGradient id="hero-sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#a8d4ff"/>
      <stop offset="32%" stop-color="#b8d4c8"/>
      <stop offset="58%" stop-color="#8ab898"/>
      <stop offset="100%" stop-color="#eef5e8"/>
    </linearGradient>
    <radialGradient id="hero-sun" cx="78%" cy="14%" r="34%">
      <stop offset="0%" stop-color="#ffc8dd" stop-opacity="0.95"/>
      <stop offset="60%" stop-color="#ffc8dd" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#ffc8dd" stop-opacity="0"/>
    </radialGradient>
    <filter id="hero-paper" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" result="noise"/>
      <feColorMatrix in="noise" type="saturate" values="0" result="gray"/>
      <feBlend in="SourceGraphic" in2="gray" mode="multiply"/>
    </filter>
  </defs>
  <g filter="url(#hero-paper)">
  <rect width="1920" height="1080" fill="url(#hero-sky)"/>
  <rect width="1920" height="1080" fill="url(#hero-sun)"/>
  {wash}
  {rays}
  {clouds}
  {mountains}
  {hills}
  {village}
  {bokeh}
  {_hero_path(rng)}
  {_hero_torii()}
  {_hero_cottage(rng)}
  {_hero_windmill()}
  {trees_left}
  {trees_right}
  {figure}
  {birds}
  {petals}
  {flowers}
  {grass}
  {fence}
  </g>
</svg>
"""


FEATURES = {
    "feature-branches": ("#6b8e6b", "#a8d4ff", "#ffc8dd", "tree"),
    "feature-transform": ("#7eb8ff", "#faf6ed", "#f8a8c8", "book"),
    "feature-play": ("#8ab898", "#ffc8dd", "#a8d4ff", "window"),
    "workshop-atmosphere": ("#f5f0e4", "#eef5e8", "#a8d4ff", "studio"),
}


def _branching_scene(c1: str, c2: str, c3: str, rng: random.Random) -> str:
    trees = []
    for tx in (140, 280, 520, 660):
        h = rng.randint(110, 160)
        trees.extend([
            f'<rect x="{tx - 8}" y="{340 - h // 3}" width="16" height="{h // 2}" rx="3" fill="#5a4a38" opacity="0.62"/>',
            f'<ellipse cx="{tx}" cy="{340 - h // 2}" rx="{60 + rng.randint(0, 20)}" ry="{h}" fill="{c1}" opacity="0.62"/>',
            f'<ellipse cx="{tx - 24}" cy="{340 - h // 3}" rx="42" ry="{int(h * 0.7)}" fill="#8ab898" opacity="0.42"/>',
        ])
    nodes = []
    path_pts = [(100, 380), (220, 340), (340, 390), (460, 320), (580, 370), (700, 330)]
    for i, (nx, ny) in enumerate(path_pts):
        nodes.append(f'<circle cx="{nx}" cy="{ny}" r="9" fill="{c3}" opacity="0.72"/>')
        nodes.append(f'<circle cx="{nx}" cy="{ny}" r="18" fill="{c3}" opacity="0.15"/>')
        if i < len(path_pts) - 1:
            nx2, ny2 = path_pts[i + 1]
            nodes.append(
                f'<path d="M{nx},{ny} Q{(nx + nx2) // 2},{(ny + ny2) // 2 - 30} {nx2},{ny2}" '
                f'fill="none" stroke="{c3}" stroke-width="3" opacity="0.55"/>'
            )
    forks = [
        '<path d="M340,390 Q380,280 420,240" fill="none" stroke="#f8a8c8" stroke-width="2.5" opacity="0.5"/>',
        '<path d="M340,390 Q300,280 260,250" fill="none" stroke="#7eb8ff" stroke-width="2.5" opacity="0.5"/>',
        '<circle cx="420" cy="240" r="7" fill="#ffc8dd" opacity="0.65"/>',
        '<circle cx="260" cy="250" r="7" fill="#a8d4ff" opacity="0.65"/>',
    ]
    return "\n  ".join(trees + nodes + forks)


def _transform_scene(c1: str, c2: str, c3: str, rng: random.Random) -> str:
    parts = [
        f'<rect x="180" y="200" width="280" height="220" rx="18" fill="#faf6ed" opacity="0.82"/>',
        f'<rect x="204" y="224" width="232" height="18" rx="4" fill="{c3}" opacity="0.55"/>',
    ]
    for row in range(5):
        parts.append(
            f'<rect x="204" y="{256 + row * 28}" width="{200 - row * 12}" height="12" rx="3" '
            f'fill="{c2}" opacity="{0.38 - row * 0.04:.2f}"/>'
        )
    parts.extend([
        f'<path d="M480,310 Q560,290 620,310 T740,290" fill="none" stroke="{c1}" '
        f'stroke-width="3" opacity="0.45" stroke-dasharray="10 14"/>',
        f'<circle cx="560" cy="300" r="28" fill="{c3}" opacity="0.22"/>',
        f'<path d="M548,300 L558,312 L578,288" fill="none" stroke="{c1}" stroke-width="3" opacity="0.55"/>',
        f'<rect x="560" y="180" width="200" height="260" rx="16" fill="{c1}" opacity="0.35"/>',
        f'<rect x="580" y="200" width="160" height="200" rx="12" fill="#eef5e8" opacity="0.42"/>',
        f'<rect x="600" y="220" width="120" height="80" rx="8" fill="#6b8e6b" opacity="0.38"/>',
        f'<ellipse cx="660" cy="340" rx="48" ry="28" fill="#8ab898" opacity="0.42"/>',
        f'<circle cx="620" cy="240" r="16" fill="#ffc8dd" opacity="0.45"/>',
    ])
    for _ in range(14):
        parts.append(
            f'<ellipse cx="{rng.randint(520, 720)}" cy="{rng.randint(200, 380)}" '
            f'rx="{rng.randint(6, 16)}" ry="{rng.randint(4, 9)}" fill="{c3}" opacity="0.18"/>'
        )
    return "\n  ".join(parts)


def _play_scene(c1: str, c2: str, c3: str, rng: random.Random) -> str:
    parts = [
        f'<rect x="160" y="120" width="480" height="300" rx="24" fill="#faf6ed" opacity="0.72"/>',
        f'<rect x="182" y="142" width="436" height="256" rx="16" fill="{c3}" opacity="0.38"/>',
        f'<line x1="400" y1="142" x2="400" y2="398" stroke="#faf6ed" stroke-width="6" opacity="0.55"/>',
        f'<line x1="182" y1="270" x2="618" y2="270" stroke="#faf6ed" stroke-width="6" opacity="0.55"/>',
        f'<circle cx="290" cy="200" r="38" fill="#ffc8dd" opacity="0.42"/>',
        f'<ellipse cx="510" cy="330" rx="62" ry="36" fill="{c1}" opacity="0.48"/>',
        f'<path d="M220,360 Q400,320 580,360" fill="none" stroke="#8ab898" stroke-width="2" opacity="0.4"/>',
        f'<rect x="240" y="380" width="320" height="52" rx="12" fill="#faf6ed" opacity="0.78"/>',
        f'<rect x="260" y="396" width="180" height="10" rx="3" fill="{c2}" opacity="0.35"/>',
        f'<rect x="260" y="414" width="120" height="8" rx="2" fill="{c2}" opacity="0.28"/>',
        f'<rect x="480" y="392" width="60" height="24" rx="8" fill="{c1}" opacity="0.45"/>',
    ]
    for x, y in [(250, 190), (330, 230), (470, 210), (550, 250)]:
        parts.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#faf6ed" opacity="0.5"/>')
    for _ in range(10):
        parts.append(
            f'<ellipse cx="{rng.randint(200, 600)}" cy="{rng.randint(150, 360)}" '
            f'rx="{rng.randint(8, 18)}" ry="{rng.randint(5, 10)}" fill="{c2}" opacity="0.12"/>'
        )
    return "\n  ".join(parts)


def _studio_scene(c1: str, c2: str, c3: str, rng: random.Random) -> str:
    parts = [
        f'<rect x="0" y="0" width="1920" height="1080" fill="{c1}" opacity="0.55"/>',
        f'<rect x="120" y="80" width="820" height="520" rx="18" fill="{c3}" opacity="0.28"/>',
        f'<rect x="148" y="108" width="768" height="464" rx="12" fill="#a8d4ff" opacity="0.22"/>',
        f'<line x1="532" y1="108" x2="532" y2="572" stroke="#faf6ed" stroke-width="8" opacity="0.35"/>',
        f'<line x1="148" y1="340" x2="916" y2="340" stroke="#faf6ed" stroke-width="8" opacity="0.35"/>',
        f'<rect x="980" y="140" width="720" height="420" rx="14" fill="{c2}" opacity="0.42"/>',
        f'<rect x="1020" y="180" width="120" height="340" rx="6" fill="#6b8e6b" opacity="0.35"/>',
    ]
    for i in range(10):
        parts.append(
            f'<rect x="{1040 + i * 58}" y="{200 + (i % 3) * 20}" width="36" height="{120 + (i % 4) * 25}" '
            f'rx="2" fill="{c3 if i % 2 else c2}" opacity="0.32"/>'
        )
    for lx in range(220, 860, 180):
        parts.append(
            f'<circle cx="{lx}" cy="160" r="32" fill="#ffc8dd" opacity="0.32"/>'
            f'<circle cx="{lx}" cy="160" r="52" fill="#f8c896" opacity="0.1"/>'
        )
    parts.extend([
        f'<rect x="1180" y="620" width="480" height="180" rx="12" fill="#faf6ed" opacity="0.38"/>',
        f'<rect x="1220" y="660" width="400" height="24" rx="6" fill="{c3}" opacity="0.28"/>',
        f'<rect x="1220" y="700" width="320" height="16" rx="4" fill="{c2}" opacity="0.22"/>',
        f'<rect x="1220" y="730" width="360" height="16" rx="4" fill="{c2}" opacity="0.18"/>',
        S._watercolor_wash(rng, c1, c2, c3, 18),
    ])
    for _ in range(20):
        parts.append(
            f'<ellipse cx="{rng.randint(100, 1820)}" cy="{rng.randint(80, 900)}" '
            f'rx="{rng.randint(8, 24)}" ry="{rng.randint(5, 12)}" fill="#ffc8dd" opacity="0.12"/>'
        )
    return "\n  ".join(parts)


def feature_svg(name: str, c1: str, c2: str, c3: str, kind: str) -> str:
    rng = random.Random(sum(ord(c) for c in name))
    if kind == "studio":
        body = _studio_scene(c1, c2, c3, rng)
        return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" role="img" aria-label="{name}">
  <defs>
    <filter id="paper-{name}" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" result="noise"/>
      <feColorMatrix in="noise" type="saturate" values="0" result="gray"/>
      <feBlend in="SourceGraphic" in2="gray" mode="multiply"/>
    </filter>
  </defs>
  <g filter="url(#paper-{name})">
  {body}
  </g>
</svg>
"""
    clouds = S._clouds(rng, 8)
    hills = (
        f'<path d="M0,360 Q180,320 360,350 T720,330 L720,500 L0,500 Z" fill="{c1}" opacity="0.42"/>'
        f'<path d="M0,400 Q220,370 440,395 T800,380 L800,500 L0,500 Z" fill="{c2}" opacity="0.38"/>'
        f'<path d="M0,430 Q280,400 560,420 T800,410 L800,500 L0,500 Z" fill="{c1}" opacity="0.32"/>'
    )
    scene_fn = {
        "tree": _branching_scene,
        "book": _transform_scene,
        "window": _play_scene,
    }[kind]
    extra = scene_fn(c1, c2, c3, rng)
    bokeh = S._bokeh(rng, c3, 18)
    grass = S._grass_foreground(rng, 35)
    rays = S._light_rays(c3)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" role="img" aria-label="{name}">
  <defs>
    <linearGradient id="fg-{name}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="45%" stop-color="{c2}"/>
      <stop offset="100%" stop-color="{c3}"/>
    </linearGradient>
    <filter id="paper-{name}" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" result="noise"/>
      <feColorMatrix in="noise" type="saturate" values="0" result="gray"/>
      <feBlend in="SourceGraphic" in2="gray" mode="multiply"/>
    </filter>
  </defs>
  <g filter="url(#paper-{name})">
  <rect width="800" height="500" fill="url(#fg-{name})"/>
  {rays}
  {clouds}
  {hills}
  {bokeh}
  {extra}
  {grass}
  <ellipse cx="400" cy="440" rx="360" ry="50" fill="{c2}" opacity="0.32"/>
  </g>
</svg>
"""


def _overlay_petals() -> str:
    rng = random.Random(7)
    parts = []
    for _ in range(48):
        x = rng.randint(20, 1900)
        y = rng.randint(40, 1040)
        rx = rng.randint(8, 16)
        ry = rng.randint(5, 10)
        rot = rng.randint(0, 180)
        c = rng.choice(["#ffc8dd", "#f8a8c8", "#faf6ed"])
        op = 0.18 + rng.random() * 0.22
        parts.append(
            f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{c}" opacity="{op:.2f}" '
            f'transform="rotate({rot} {x} {y})"/>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" aria-hidden="true">\n  '
        + "\n  ".join(parts)
        + "\n</svg>"
    )


def _overlay_wind() -> str:
    rng = random.Random(11)
    curves = []
    for i in range(12):
        y = 220 + i * 70
        op = 0.14 + (i % 3) * 0.05
        c = rng.choice(["#faf6ed", "#ffc8dd", "#a8d4ff", "#eef5e8"])
        curves.append(
            f'<path d="M{-40 + i * 8},{y} Q{320 + i * 20},{y - 30} {680 + i * 15},{y + 10} '
            f'Q{1040 + i * 10},{y + 40} {1480 + i * 12},{y - 10} T{1960},{y + 20}" '
            f'fill="none" stroke="{c}" stroke-width="{1.6 + (i % 3) * 0.4}" opacity="{op:.2f}"/>'
        )
    wisps = []
    for _ in range(18):
        x = rng.randint(80, 1840)
        y = rng.randint(180, 920)
        wisps.append(
            f'<ellipse cx="{x}" cy="{y}" rx="{rng.randint(60, 120)}" ry="{rng.randint(8, 16)}" '
            f'fill="{rng.choice(["#faf6ed", "#ffc8dd", "#a8d4ff"])}" opacity="0.1" '
            f'transform="rotate({rng.randint(-12, 12)} {x} {y})"/>'
        )
    dots = []
    for _ in range(24):
        dots.append(
            f'<circle cx="{rng.randint(0, 1920)}" cy="{rng.randint(0, 1080)}" '
            f'r="{rng.choice([2, 2.5, 3])}" fill="#faf6ed" opacity="{0.2 + rng.random() * 0.2:.2f}"/>'
        )
    gradient = """<defs>
    <linearGradient id="wind-g" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#a8d4ff" stop-opacity="0"/>
      <stop offset="30%" stop-color="#faf6ed" stop-opacity="0.22"/>
      <stop offset="55%" stop-color="#ffc8dd" stop-opacity="0.16"/>
      <stop offset="80%" stop-color="#eef5e8" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="#a8d4ff" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#wind-g)"/>"""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" aria-hidden="true">\n  '
        + gradient
        + "\n  "
        + "\n  ".join(curves + wisps + dots)
        + "\n</svg>"
    )


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "hero-ghibli.svg").write_text(hero_svg(), encoding="utf-8")
    for fname, colors in FEATURES.items():
        (ROOT / f"{fname}.svg").write_text(feature_svg(fname, *colors), encoding="utf-8")
    (ROOT / "overlay-petals.svg").write_text(_overlay_petals(), encoding="utf-8")
    (ROOT / "overlay-wind.svg").write_text(_overlay_wind(), encoding="utf-8")
    print("Landing + overlay SVGs written to", ROOT)


if __name__ == "__main__":
    main()
