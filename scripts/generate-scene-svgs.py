"""Generate 62 Ghibli-style watercolor SVG scene backgrounds with rich procedural detail."""
from __future__ import annotations

import random
from pathlib import Path

# id -> (sky_top, sky_mid, sky_low, ground, accent, composition)
SCENES: dict[str, tuple[str, str, str, str, str, str]] = {
    "calm_meadow": ("#a8d4ff", "#c8e8ff", "#b8d4c8", "#6b8e6b", "#eef5e8", "meadow"),
    "sunset_hill": ("#ffc8dd", "#f8c896", "#a8d4ff", "#6b8e6b", "#faf6ed", "meadow"),
    "forest_path": ("#7eb8ff", "#8ab898", "#5a7860", "#4a6850", "#eef5e8", "forest"),
    "rainy_street": ("#5a8fc8", "#6a8090", "#4a5868", "#3a4858", "#a8d4ff", "city"),
    "school_corridor": ("#ffc8dd", "#faf6ed", "#e8dcc8", "#c8b8e8", "#a8d4ff", "interior"),
    "rooftop_sky": ("#a8d4ff", "#7eb8ff", "#ffc8dd", "#eef5e8", "#faf6ed", "sky"),
    "night_stars": ("#1a2430", "#2a3848", "#3a4860", "#4a5868", "#eef5e8", "night"),
    "city_lights": ("#2a3848", "#4a5868", "#7eb8ff", "#f8a8c8", "#ffc8dd", "city"),
    "mystery_fog": ("#4a6850", "#5a7860", "#6a8090", "#3a4858", "#c8b8e8", "fog"),
    "romance_cafe": ("#ffc8dd", "#faf6ed", "#f8a8c8", "#e8dcc8", "#a8d4ff", "interior"),
    "campus_field": ("#a8d4ff", "#8ab898", "#6b8e6b", "#eef5e8", "#ffc8dd", "meadow"),
    "xianxia_peaks": ("#a8d4ff", "#c8b8e8", "#5a7860", "#6b8e6b", "#eef5e8", "mountain"),
    "indoor_warm": ("#f8c896", "#faf6ed", "#ffc8dd", "#e8dcc8", "#a8d4ff", "interior"),
    "beach_wind": ("#a8d4ff", "#7eb8ff", "#eef5e8", "#ffc8dd", "#faf6ed", "water"),
    "train_countryside": ("#a8d4ff", "#8ab898", "#6b8e6b", "#ffc8dd", "#faf6ed", "train"),
    "winter_snow": ("#eef5e8", "#c5d8e8", "#a8d4ff", "#faf6ed", "#8ab898", "snow"),
    "bamboo_grove": ("#8ab898", "#6b8e6b", "#5a7860", "#4a6850", "#a8d4ff", "forest"),
    "shrine_path": ("#ffc8dd", "#a8d4ff", "#6b8e6b", "#4a6850", "#faf6ed", "shrine"),
    "lakeside_dock": ("#7eb8ff", "#a8d4ff", "#6b8e6b", "#eef5e8", "#faf6ed", "water"),
    "hot_spring": ("#f8c896", "#ffc8dd", "#8ab898", "#6b8e6b", "#e8dcc8", "mist"),
    "castle_clouds": ("#a8d4ff", "#c8b8e8", "#ffc8dd", "#eef5e8", "#faf6ed", "sky"),
    "lantern_festival": ("#1a2430", "#2a3848", "#5a8fc8", "#f8a8c8", "#ffc8dd", "night"),
    "library_aisle": ("#faf6ed", "#e8dcc8", "#c8b8e8", "#8ab898", "#a8d4ff", "interior"),
    "hospital_hall": ("#eef5e8", "#a8d4ff", "#faf6ed", "#c8b8e8", "#7eb8ff", "interior"),
    "airport_sunset": ("#ffc8dd", "#f8c896", "#7eb8ff", "#a8d4ff", "#faf6ed", "sky"),
    "balcony_night": ("#1a2430", "#2a3848", "#5a8fc8", "#f8a8c8", "#ffc8dd", "city"),
    "cherry_tunnel": ("#ffc8dd", "#f8a8c8", "#8ab898", "#6b8e6b", "#faf6ed", "forest"),
    "autumn_road": ("#f8c896", "#c45c6a", "#6b8e6b", "#8ab898", "#e8dcc8", "meadow"),
    "thunder_field": ("#3a4058", "#4a5868", "#5a7860", "#6a8090", "#7eb8ff", "storm"),
    "snow_shrine": ("#eef5e8", "#c5d8e8", "#a8d4ff", "#faf6ed", "#8ab898", "shrine"),
    "cliff_lighthouse": ("#5a8fc8", "#7eb8ff", "#4a6850", "#eef5e8", "#faf6ed", "water"),
    "village_dusk": ("#ffc8dd", "#f8c896", "#6b8e6b", "#a8d4ff", "#eef5e8", "meadow"),
    "enchanted_grove": ("#8ab898", "#c8b8e8", "#5a7860", "#6b8e6b", "#ffc8dd", "forest"),
    "cave_glow": ("#1a2030", "#3a4058", "#4a6850", "#6b8e6b", "#f8c896", "cave"),
    "sky_tram": ("#a8d4ff", "#7eb8ff", "#8ab898", "#6b8e6b", "#ffc8dd", "sky"),
    "floating_isles": ("#a8d4ff", "#c8b8e8", "#8ab898", "#ffc8dd", "#faf6ed", "sky"),
    "flower_field": ("#ffc8dd", "#a8d4ff", "#6b8e6b", "#faf6ed", "#f8a8c8", "meadow"),
    "night_bazaar": ("#1a2430", "#2a3848", "#5a7860", "#f8a8c8", "#ffc8dd", "city"),
    "harbor_dawn": ("#ffc8dd", "#a8d4ff", "#7eb8ff", "#eef5e8", "#faf6ed", "water"),
    "windy_hill": ("#a8d4ff", "#8ab898", "#6b8e6b", "#eef5e8", "#ffc8dd", "meadow"),
    "candle_room": ("#f8c896", "#faf6ed", "#ffc8dd", "#e8dcc8", "#a8d4ff", "interior"),
    "storm_coast": ("#3a4058", "#5a8fc8", "#6a8090", "#4a6850", "#7eb8ff", "water"),
    "bamboo_rain": ("#5a7860", "#6a8090", "#4a6850", "#8ab898", "#a8d4ff", "rain"),
    "moon_bridge": ("#1a2430", "#2a3848", "#5a8fc8", "#6b8e6b", "#ffc8dd", "water"),
    "tea_house": ("#faf6ed", "#8ab898", "#6b8e6b", "#ffc8dd", "#e8dcc8", "interior"),
    "pagoda_mist": ("#a8d4ff", "#c8b8e8", "#5a7860", "#6b8e6b", "#eef5e8", "mountain"),
    "market_alley": ("#ffc8dd", "#faf6ed", "#f8a8c8", "#e8dcc8", "#a8d4ff", "city"),
    "subway_night": ("#1a2430", "#2a3848", "#4a5868", "#7eb8ff", "#f8a8c8", "city"),
    "greenhouse": ("#8ab898", "#faf6ed", "#6b8e6b", "#ffc8dd", "#a8d4ff", "interior"),
    "ruins_vine": ("#6b8e6b", "#5a7860", "#4a6850", "#8ab898", "#c8b8e8", "ruins"),
    "desert_oasis": ("#f8c896", "#ffc8dd", "#7eb8ff", "#6b8e6b", "#eef5e8", "oasis"),
    "volcano_dusk": ("#f8a8c8", "#f8c896", "#4a5868", "#2a3848", "#ffc8dd", "mountain"),
    "crystal_spring": ("#a8d4ff", "#c8b8e8", "#7eb8ff", "#eef5e8", "#faf6ed", "water"),
    "meadow_windmill": ("#a8d4ff", "#8ab898", "#6b8e6b", "#ffc8dd", "#eef5e8", "meadow"),
    "canal_twilight": ("#ffc8dd", "#7eb8ff", "#5a7860", "#a8d4ff", "#faf6ed", "water"),
    "observatory": ("#1a2430", "#2a3848", "#5a8fc8", "#c8b8e8", "#eef5e8", "night"),
    "campsite": ("#1a2430", "#2a3848", "#5a7860", "#f8c896", "#6b8e6b", "night"),
    "waterfall_rainbow": ("#a8d4ff", "#8ab898", "#7eb8ff", "#eef5e8", "#ffc8dd", "water"),
    "rice_terraces": ("#6b8e6b", "#8ab898", "#a8d4ff", "#eef5e8", "#faf6ed", "mountain"),
    "sakura_river": ("#ffc8dd", "#f8a8c8", "#7eb8ff", "#faf6ed", "#a8d4ff", "water"),
    "clock_tower": ("#a8d4ff", "#c8b8e8", "#faf6ed", "#ffc8dd", "#7eb8ff", "city"),
    "ghost_mansion": ("#1a2030", "#3a4058", "#4a5868", "#5a7860", "#6a8090", "fog"),
}


def _rng(name: str, salt: int = 0) -> random.Random:
    return random.Random(sum(ord(c) for c in name) + salt * 9973)


def _cloud_cluster(rng: random.Random, cx: int, cy: int, scale: float, op: float) -> str:
    parts: list[str] = []
    for i in range(7):
        dx = rng.randint(-int(80 * scale), int(80 * scale))
        dy = rng.randint(-int(25 * scale), int(20 * scale))
        rx = int(rng.randint(50, 130) * scale)
        ry = int(rng.randint(18, 45) * scale)
        fill = "#faf6ed" if i % 2 == 0 else "#eef5e8"
        parts.append(
            f'<ellipse cx="{cx + dx}" cy="{cy + dy}" rx="{rx}" ry="{ry}" '
            f'fill="{fill}" opacity="{op:.2f}"/>'
        )
    return "\n  ".join(parts)


def _clouds(rng: random.Random, count: int = 12) -> str:
    layers = []
    for _ in range(count):
        cx = rng.randint(80, 1840)
        cy = rng.randint(60, 380)
        scale = 0.7 + rng.random() * 0.8
        op = 0.18 + rng.random() * 0.28
        layers.append(_cloud_cluster(rng, cx, cy, scale, op))
    return "\n  ".join(layers)


def _mountains(rng: random.Random, base: int, color: str, peaks: int, op: float) -> str:
    pts = ["M0,1080", f"M0,{base + 40}"]
    x = 0
    while x <= 1920:
        y = base + rng.randint(-60, 40)
        pts.append(f"L{x},{y}")
        x += rng.randint(120, 260)
    pts += ["L1920,1080", "Z"]
    return f'<path d="{" ".join(pts)}" fill="{color}" opacity="{op:.2f}"/>'


def _mountain_layers(rng: random.Random, c2: str, c3: str) -> str:
    parts = []
    for base, color, op in ((520, c2, 0.35), (620, c3, 0.5), (720, c3, 0.65)):
        parts.append(_mountains(rng, base, color, 6, op))
    return "\n  ".join(parts)


def _hills(rng: random.Random, c2: str, c3: str) -> str:
    parts = []
    for layer, op in ((880, 0.42), (940, 0.55), (990, 0.68)):
        pts = ["M0,1080", f"M0,{layer}"]
        x = 0
        while x <= 1920:
            y = layer + rng.randint(-35, 35)
            pts.append(f"L{x},{y}")
            x += rng.randint(160, 280)
        pts += ["L1920,1080", "Z"]
        color = c3 if layer > 950 else c2
        parts.append(f'<path d="{" ".join(pts)}" fill="{color}" opacity="{op:.2f}"/>')
    return "\n  ".join(parts)


def _tree(rng: random.Random, x: int, y: int, scale: float, trunk: str, leaf: str) -> str:
    h = int(rng.randint(100, 220) * scale)
    w = int(rng.randint(50, 100) * scale)
    tw = max(8, int(14 * scale))
    parts = [
        f'<rect x="{x - tw // 2}" y="{y - h // 2}" width="{tw}" height="{h // 2}" '
        f'rx="3" fill="#5a4a38" opacity="0.65"/>',
        f'<ellipse cx="{x}" cy="{y - h // 3}" rx="{w}" ry="{h}" fill="{leaf}" opacity="0.72"/>',
        f'<ellipse cx="{x - w // 3}" cy="{y - h // 4}" rx="{w * 0.7:.0f}" '
        f'ry="{h * 0.75:.0f}" fill="{leaf}" opacity="0.45"/>',
        f'<ellipse cx="{x + w // 4}" cy="{y - h // 5}" rx="{w * 0.55:.0f}" '
        f'ry="{h * 0.6:.0f}" fill="{leaf}" opacity="0.38"/>',
    ]
    return "\n  ".join(parts)


def _pine(rng: random.Random, x: int, y: int, scale: float, color: str) -> str:
    h = int(rng.randint(140, 260) * scale)
    parts = [f'<rect x="{x - 6}" y="{y - 20}" width="12" height="{h // 2}" fill="#4a4038" opacity="0.6"/>']
    for i, frac in enumerate((0.35, 0.55, 0.75, 0.92)):
        w = int((120 - i * 18) * scale)
        cy = y - int(h * frac)
        parts.append(
            f'<ellipse cx="{x}" cy="{cy}" rx="{w}" ry="{int(45 * scale)}" '
            f'fill="{color}" opacity="{0.55 + i * 0.08:.2f}"/>'
        )
    return "\n  ".join(parts)


def _tree_grove(rng: random.Random, count: int, leaf: str, ground_y: int = 920) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(40, 1880)
        scale = 0.6 + rng.random() * 0.9
        if rng.random() < 0.35:
            parts.append(_pine(rng, x, ground_y, scale, leaf))
        else:
            parts.append(_tree(rng, x, ground_y, scale, "#5a4a38", leaf))
    return "\n  ".join(parts)


def _building(rng: random.Random, x: int, w: int, h: int, body: str, accent: str) -> str:
    y = 920 - h
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{body}" opacity="0.78"/>',
        f'<polygon points="{x},{y} {x + w // 2},{y - 28} {x + w},{y}" fill="{accent}" opacity="0.55"/>',
    ]
    rows = max(2, h // 55)
    cols = max(2, w // 38)
    for row in range(rows):
        for col in range(cols):
            wx = x + 12 + col * (w - 24) // cols
            wy = y + 18 + row * (h - 36) // rows
            lit = rng.random() < 0.45
            fill = "#ffc8dd" if lit else "#a8d4ff"
            op = 0.55 if lit else 0.25
            parts.append(
                f'<rect x="{wx}" y="{wy}" width="16" height="20" rx="2" fill="{fill}" opacity="{op:.2f}"/>'
            )
    return "\n  ".join(parts)


def _cityscape(rng: random.Random, c2: str, c3: str, c4: str) -> str:
    parts = []
    x = 30
    while x < 1750:
        w = rng.randint(70, 200)
        h = rng.randint(140, 420)
        parts.append(_building(rng, x, w, h, c3, c2))
        x += w + rng.randint(12, 40)
    for _ in range(6):
        lx = rng.randint(100, 1820)
        parts.append(
            f'<rect x="{lx}" y="780" width="6" height="140" rx="3" fill="{c4}" opacity="0.35"/>'
            f'<ellipse cx="{lx + 3}" cy="770" rx="18" ry="10" fill="#ffc8dd" opacity="0.45"/>'
        )
    return "\n  ".join(parts)


def _water(rng: random.Random, c1: str, c2: str, c4: str) -> str:
    parts = [
        f'<path d="M0,700 Q480,660 960,690 T1920,680 L1920,1080 L0,1080 Z" '
        f'fill="{c1}" opacity="0.58"/>',
        f'<path d="M0,740 Q640,710 1280,750 T1920,720 L1920,1080 L0,1080 Z" '
        f'fill="{c2}" opacity="0.42"/>',
    ]
    for i in range(12):
        y = 760 + i * 22
        op = 0.12 + (i % 3) * 0.05
        parts.append(
            f'<path d="M0,{y} Q320,{y - 8} 640,{y + 4} T1280,{y - 6} T1920,{y + 2}" '
            f'fill="none" stroke="{c4}" stroke-width="1.5" opacity="{op:.2f}"/>'
        )
    for _ in range(8):
        rx = rng.randint(60, 200)
        cx = rng.randint(100, 1820)
        cy = rng.randint(780, 920)
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="8" fill="{c4}" opacity="0.15"/>'
        )
    return "\n  ".join(parts)


def _reflection(rng: random.Random, c4: str) -> str:
    parts = []
    for _ in range(10):
        x = rng.randint(80, 1840)
        w = rng.randint(40, 120)
        parts.append(
            f'<ellipse cx="{x}" cy="{rng.randint(820, 980)}" rx="{w}" ry="6" '
            f'fill="{c4}" opacity="0.12"/>'
        )
    return "\n  ".join(parts)


def _path(rng: random.Random, c4: str) -> str:
    pts = ["M960,1080", "M960,1080"]
    y = 1080
    x = 960
    for _ in range(8):
        y -= rng.randint(60, 100)
        x += rng.randint(-80, 80)
        pts.append(f"L{x},{y}")
    d = " ".join(pts)
    return (
        f'<path d="{d}" fill="none" stroke="{c4}" stroke-width="48" stroke-linecap="round" '
        f'opacity="0.28"/>'
        f'<path d="{d}" fill="none" stroke="#faf6ed" stroke-width="4" stroke-dasharray="12 18" '
        f'opacity="0.2"/>'
    )


def _flowers(rng: random.Random, count: int) -> str:
    colors = ["#ffc8dd", "#f8a8c8", "#faf6ed", "#c8b8e8", "#ffc8dd"]
    parts = []
    for _ in range(count):
        x = rng.randint(60, 1860)
        y = rng.randint(880, 1020)
        c = rng.choice(colors)
        parts.append(f'<circle cx="{x}" cy="{y}" r="{rng.randint(3, 7)}" fill="{c}" opacity="0.65"/>')
        parts.append(
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 12}" stroke="#6b8e6b" '
            f'stroke-width="2" opacity="0.5"/>'
        )
    return "\n  ".join(parts)


def _stars(rng: random.Random, accent: str, count: int = 90) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(30, 520)
        r = rng.choice([1.2, 1.8, 2.4, 3])
        op = 0.5 + rng.random() * 0.5
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{accent}" opacity="{op:.2f}"/>')
    return "\n  ".join(parts)


def _moon(c4: str, cx: int = 1580, cy: int = 180) -> str:
    return (
        f'<circle cx="{cx}" cy="{cy}" r="72" fill="{c4}" opacity="0.85"/>'
        f'<circle cx="{cx + 28}" cy="{cy - 18}" r="62" fill="#2a3848" opacity="0.35"/>'
        f'<circle cx="{cx}" cy="{cy}" r="90" fill="{c4}" opacity="0.12"/>'
    )


def _rain(rng: random.Random, count: int = 60) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(200, 900)
        parts.append(
            f'<line x1="{x}" y1="{y}" x2="{x - 8}" y2="{y + 28}" '
            f'stroke="#a8d4ff" stroke-width="1.5" opacity="0.35"/>'
        )
    return "\n  ".join(parts)


def _snow(rng: random.Random, count: int = 50) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(40, 700)
        r = rng.choice([2, 3, 4])
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#faf6ed" opacity="0.75"/>')
    return "\n  ".join(parts)


def _mist_layers(c4: str) -> str:
    parts = []
    for y, op in ((680, 0.18), (780, 0.25), (860, 0.32)):
        parts.append(
            f'<rect x="0" y="{y}" width="1920" height="220" fill="{c4}" opacity="{op:.2f}"/>'
        )
    return "\n  ".join(parts)


def _torii(c4: str, cx: int = 960) -> str:
    return (
        f'<rect x="{cx - 130}" y="560" width="260" height="16" rx="4" fill="#c45c6a" opacity="0.85"/>'
        f'<rect x="{cx - 110}" y="576" width="220" height="10" rx="2" fill="#a04050" opacity="0.7"/>'
        f'<rect x="{cx - 90}" y="430" width="18" height="150" rx="3" fill="#c45c6a" opacity="0.8"/>'
        f'<rect x="{cx + 72}" y="430" width="18" height="150" rx="3" fill="#c45c6a" opacity="0.8"/>'
        f'<rect x="{cx - 8}" y="400" width="16" height="180" rx="2" fill="#8a3038" opacity="0.65"/>'
    )


def _stone_lanterns(rng: random.Random, count: int = 4) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(200, 1720)
        parts.append(
            f'<rect x="{x}" y="820" width="28" height="50" rx="4" fill="#8a9098" opacity="0.6"/>'
            f'<rect x="{x + 4}" y="800" width="20" height="18" rx="3" fill="#ffc8dd" opacity="0.5"/>'
            f'<ellipse cx="{x + 14}" cy="790" rx="16" ry="8" fill="#faf6ed" opacity="0.35"/>'
        )
    return "\n  ".join(parts)


def _train(rng: random.Random, c2: str, c4: str) -> str:
    parts = [
        f'<rect x="0" y="830" width="1920" height="6" fill="#4a4038" opacity="0.45"/>',
        f'<rect x="0" y="848" width="1920" height="4" fill="#faf6ed" opacity="0.25"/>',
    ]
    for sx in range(0, 1920, 120):
        parts.append(f'<rect x="{sx}" y="826" width="8" height="24" fill="#5a5048" opacity="0.5"/>')
    tx = rng.randint(280, 520)
    parts.extend([
        f'<rect x="{tx}" y="760" width="340" height="72" rx="10" fill="{c2}" opacity="0.82"/>',
        f'<rect x="{tx + 20}" y="772" width="80" height="48" rx="6" fill="{c4}" opacity="0.45"/>',
        f'<rect x="{tx + 120}" y="772" width="80" height="48" rx="6" fill="{c4}" opacity="0.4"/>',
        f'<rect x="{tx + 220}" y="772" width="80" height="48" rx="6" fill="{c4}" opacity="0.38"/>',
        f'<rect x="{tx + 300}" y="776" width="24" height="40" rx="4" fill="#ffc8dd" opacity="0.55"/>',
    ])
    return "\n  ".join(parts)


def _windmill(c4: str) -> str:
    cx, cy = 1480, 680
    blades = []
    for angle in range(0, 360, 90):
        blades.append(
            f'<ellipse cx="{cx}" cy="{cy - 80}" rx="18" ry="90" fill="{c4}" opacity="0.5" '
            f'transform="rotate({angle} {cx} {cy})"/>'
        )
    return (
        f'<rect x="{cx - 35}" y="{cy}" width="70" height="180" rx="6" fill="#faf6ed" opacity="0.65"/>'
        f'<polygon points="{cx - 45},{cy + 180} {cx + 45},{cy + 180} {cx + 55},{cy + 200} '
        f'{cx - 55},{cy + 200}" fill="#e8dcc8" opacity="0.5"/>'
        f'<circle cx="{cx}" cy="{cy}" r="16" fill="#8a9098" opacity="0.6"/>'
        + "".join(blades)
    )


def _lighthouse(c4: str) -> str:
    return (
        f'<rect x="1680" y="420" width="48" height="320" rx="6" fill="#faf6ed" opacity="0.75"/>'
        f'<rect x="1670" y="400" width="68" height="30" rx="4" fill="#c45c6a" opacity="0.65"/>'
        f'<rect x="1688" y="480" width="32" height="24" rx="2" fill="#a8d4ff" opacity="0.45"/>'
        f'<rect x="1688" y="540" width="32" height="24" rx="2" fill="#a8d4ff" opacity="0.4"/>'
        f'<circle cx="1704" cy="380" r="28" fill="#ffc8dd" opacity="0.7"/>'
        f'<circle cx="1704" cy="380" r="48" fill="{c4}" opacity="0.2"/>'
    )


def _dock(c4: str) -> str:
    return (
        f'<rect x="720" y="780" width="480" height="18" rx="4" fill="#5a4a38" opacity="0.55"/>'
        f'<rect x="740" y="798" width="14" height="120" fill="#4a4038" opacity="0.5"/>'
        f'<rect x="1160" y="798" width="14" height="120" fill="#4a4038" opacity="0.5"/>'
        f'<ellipse cx="860" cy="770" rx="60" ry="20" fill="{c4}" opacity="0.35"/>'
        f'<path d="M820,770 Q860,740 900,770 L900,790 Q860,760 820,790 Z" fill="#6b8e6b" opacity="0.45"/>'
    )


def _lanterns(rng: random.Random, count: int = 12) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(80, 1840)
        y = rng.randint(500, 880)
        parts.append(
            f'<ellipse cx="{x}" cy="{y}" rx="14" ry="20" fill="#ffc8dd" opacity="0.65"/>'
            f'<rect x="{x - 2}" y="{y - 28}" width="4" height="10" fill="#8a9098" opacity="0.5"/>'
            f'<circle cx="{x}" cy="{y}" r="22" fill="#f8a8c8" opacity="0.15"/>'
        )
    return "\n  ".join(parts)


def _pagoda(c2: str, c4: str) -> str:
    parts = []
    cx = 960
    for i, (w, y) in enumerate([(200, 680), (160, 580), (120, 500), (80, 440)]):
        parts.append(
            f'<polygon points="{cx - w // 2},{y + 40} {cx},{y} {cx + w // 2},{y + 40}" '
            f'fill="{c2}" opacity="{0.55 + i * 0.08:.2f}"/>'
        )
        parts.append(
            f'<rect x="{cx - w // 4}" y="{y + 40}" width="{w // 2}" height="50" '
            f'fill="{c4}" opacity="0.5"/>'
        )
    return "\n  ".join(parts)


def _castle(c2: str, c4: str) -> str:
    return (
        f'<rect x="780" y="480" width="360" height="280" rx="8" fill="{c2}" opacity="0.55"/>'
        f'<rect x="860" y="380" width="80" height="120" rx="4" fill="{c4}" opacity="0.5"/>'
        f'<rect x="980" y="400" width="60" height="100" rx="4" fill="{c4}" opacity="0.45"/>'
        f'<polygon points="780,480 960,340 1140,480" fill="{c4}" opacity="0.42"/>'
        f'<rect x="900" y="520" width="40" height="60" rx="3" fill="#ffc8dd" opacity="0.35"/>'
        f'<rect x="980" y="520" width="40" height="60" rx="3" fill="#ffc8dd" opacity="0.32"/>'
    )


def _floating_isle(rng: random.Random, cx: int, cy: int, w: int, c2: str, c3: str) -> str:
    return (
        f'<ellipse cx="{cx}" cy="{cy + 30}" rx="{w}" ry="28" fill="#2a3848" opacity="0.15"/>'
        f'<ellipse cx="{cx}" cy="{cy}" rx="{w}" ry="36" fill="{c3}" opacity="0.65"/>'
        f'<ellipse cx="{cx - w // 3}" cy="{cy - 20}" rx="{w // 2}" ry="24" fill="{c2}" opacity="0.45"/>'
        + _tree(rng, cx + w // 4, cy + 10, 0.5, "#5a4a38", c2)
    )


def _cave_elements(c4: str) -> str:
    parts = []
    for x, h in ((200, 180), (400, 240), (600, 160), (1300, 200), (1500, 260), (1700, 170)):
        parts.append(
            f'<polygon points="{x},920 {x + 40},920 {x + 20},{920 - h}" fill="#3a4058" opacity="0.55"/>'
        )
    for _ in range(8):
        parts.append(
            f'<circle cx="{120 + _ * 220}" cy="{780 + (_ % 3) * 40}" r="12" fill="{c4}" opacity="0.55"/>'
            f'<circle cx="{120 + _ * 220}" cy="{780 + (_ % 3) * 40}" r="24" fill="{c4}" opacity="0.15"/>'
        )
    return "\n  ".join(parts)


def _ruins(rng: random.Random, c3: str, c4: str) -> str:
    parts = []
    for x, h in ((300, 220), (520, 160), (780, 280), (1100, 190), (1380, 250)):
        parts.append(
            f'<rect x="{x}" y="{920 - h}" width="48" height="{h}" rx="3" fill="{c3}" opacity="0.55"/>'
        )
        parts.append(
            f'<path d="M{x},{920 - h // 2} Q{x + 60},{920 - h // 2 - 40} {x + 30},{920 - h // 3}" '
            f'fill="none" stroke="{c4}" stroke-width="4" opacity="0.45"/>'
        )
    return "\n  ".join(parts)


def _rice_terraces(c2: str, c3: str) -> str:
    parts = []
    for i, y in enumerate(range(720, 980, 45)):
        op = 0.35 + i * 0.06
        parts.append(
            f'<path d="M0,{y} Q480,{y - 20} 960,{y + 10} T1920,{y} L1920,{y + 40} L0,{y + 40} Z" '
            f'fill="{c2 if i % 2 else c3}" opacity="{op:.2f}"/>'
        )
    return "\n  ".join(parts)


def _waterfall(c1: str, c4: str) -> str:
    return (
        f'<rect x="880" y="380" width="160" height="340" rx="8" fill="{c1}" opacity="0.35"/>'
        f'<path d="M960,380 Q940,520 960,660 Q980,520 960,380" fill="#eef5e8" opacity="0.45"/>'
        f'<ellipse cx="960" cy="720" rx="120" ry="30" fill="{c4}" opacity="0.35"/>'
        f'<path d="M820,400 Q900,380 960,400 T1100,390" fill="none" stroke="#ffc8dd" '
        f'stroke-width="8" opacity="0.35"/>'
        f'<path d="M840,420 Q920,400 980,420 T1120,410" fill="none" stroke="#a8d4ff" '
        f'stroke-width="6" opacity="0.3"/>'
    )


def _interior(name: str, rng: random.Random, c2: str, c3: str, c4: str) -> str:
    parts = [
        f'<rect x="0" y="0" width="1920" height="1080" fill="{c2}" opacity="0.35"/>',
        f'<rect x="120" y="120" width="680" height="420" rx="12" fill="{c4}" opacity="0.22"/>',
        f'<rect x="1120" y="180" width="520" height="380" rx="12" fill="{c4}" opacity="0.18"/>',
    ]
    for sx in (160, 1160):
        for row in range(4):
            for col in range(3):
                parts.append(
                    f'<rect x="{sx + col * 80}" y="{200 + row * 70}" width="50" height="40" '
                    f'rx="3" fill="{c3}" opacity="0.35"/>'
                )
    for lx in range(200, 1700, 280):
        parts.append(
            f'<circle cx="{lx}" cy="180" r="28" fill="#ffc8dd" opacity="0.35"/>'
            f'<circle cx="{lx}" cy="180" r="48" fill="#f8c896" opacity="0.12"/>'
        )
    if "library" in name:
        for i in range(12):
            parts.append(
                f'<rect x="{140 + i * 55}" y="600" width="40" height="{180 + (i % 3) * 30}" '
                f'rx="2" fill="{c3}" opacity="0.45"/>'
            )
    if "cafe" in name or "tea" in name:
        parts.append(
            f'<rect x="760" y="720" width="400" height="24" rx="6" fill="#5a4a38" opacity="0.45"/>'
            f'<ellipse cx="860" cy="700" rx="30" ry="18" fill="#faf6ed" opacity="0.5"/>'
            f'<ellipse cx="1060" cy="700" rx="30" ry="18" fill="#faf6ed" opacity="0.48"/>'
        )
    if "greenhouse" in name:
        for i in range(8):
            parts.append(
                f'<ellipse cx="{200 + i * 200}" cy="780" rx="50" ry="70" fill="#6b8e6b" opacity="0.45"/>'
            )
    for row in range(14):
        parts.append(
            f'<rect x="0" y="{880 + row * 14}" width="1920" height="8" '
            f'fill="#e8dcc8" opacity="{0.08 + (row % 2) * 0.04:.2f}"/>'
        )
    return "\n  ".join(parts)


def _bokeh(rng: random.Random, c4: str, count: int = 15) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(100, 800)
        r = rng.randint(8, 40)
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c4}" opacity="0.08"/>')
    return "\n  ".join(parts)


def _light_rays(c5: str, night: bool = False) -> str:
    if night:
        return ""
    parts = []
    cx, cy = 1480, 95
    for i in range(10):
        rot = -38 + i * 7
        spread = 36 + i * 10
        parts.append(
            f'<path d="M{cx},{cy} L{cx + 920},{cy + 720} L{cx + 920 + spread},{cy + 720} Z" '
            f'fill="{c5}" opacity="0.055" transform="rotate({rot} {cx} {cy})"/>'
        )
    return "\n  ".join(parts)


def _grass_foreground(rng: random.Random, count: int = 75) -> str:
    colors = ["#6b8e6b", "#8ab898", "#4a6850", "#b8d4c8", "#5a7860"]
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(895, 1075)
        h = rng.randint(30, 90)
        tilt = rng.randint(-22, 22)
        c = rng.choice(colors)
        sw = rng.randint(2, 4)
        parts.append(
            f'<path d="M{x},{y} Q{x + tilt},{y - h // 2} {x + tilt * 2},{y - h}" '
            f'fill="none" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" opacity="0.52"/>'
        )
    return "\n  ".join(parts)


def _wildflowers_dense(rng: random.Random, count: int = 35) -> str:
    colors = ["#ffc8dd", "#f8a8c8", "#faf6ed", "#c8b8e8", "#ffc8dd", "#a8d4ff"]
    parts = []
    for _ in range(count):
        x = rng.randint(40, 1880)
        y = rng.randint(870, 1040)
        c = rng.choice(colors)
        r = rng.randint(3, 8)
        parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" opacity="0.68"/>')
        parts.append(
            f'<path d="M{x},{y} l{rng.randint(-4, 4)},{-r - 2} l{rng.randint(-4, 4)},{r + 2}" '
            f'fill="{c}" opacity="0.45"/>'
        )
        parts.append(
            f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 14}" stroke="#6b8e6b" '
            f'stroke-width="2" opacity="0.48"/>'
        )
    return "\n  ".join(parts)


def _birds(rng: random.Random, count: int = 10) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(160, 1760)
        y = rng.randint(50, 360)
        w = rng.randint(12, 32)
        parts.append(
            f'<path d="M{x - w},{y} Q{x},{y - 7} {x + w},{y}" fill="none" '
            f'stroke="#3a3548" stroke-width="2" opacity="0.34"/>'
        )
        if rng.random() < 0.45:
            ox = rng.randint(-60, 60)
            parts.append(
                f'<path d="M{x + ox - w},{y + 18} Q{x + ox},{y + 12} {x + ox + w},{y + 18}" '
                f'fill="none" stroke="#3a3548" stroke-width="1.5" opacity="0.26"/>'
            )
    return "\n  ".join(parts)


def _watercolor_wash(rng: random.Random, c1: str, c2: str, c3: str, count: int = 28) -> str:
    palette = [c1, c2, c3, "#ffc8dd", "#c8b8e8", "#eef5e8"]
    parts = []
    for _ in range(count):
        x = rng.randint(-120, 2040)
        y = rng.randint(0, 1080)
        rx = rng.randint(110, 420)
        ry = rng.randint(55, 180)
        c = rng.choice(palette)
        parts.append(
            f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{c}" '
            f'opacity="{0.04 + rng.random() * 0.07:.2f}"/>'
        )
    return "\n  ".join(parts)


def _distant_village(rng: random.Random, c2: str, c3: str) -> str:
    parts = []
    for _ in range(rng.randint(8, 14)):
        x = rng.randint(40, 1840)
        w = rng.randint(42, 95)
        h = rng.randint(38, 78)
        y = rng.randint(660, 810)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" fill="{c3}" opacity="0.44"/>'
            f'<polygon points="{x},{y} {x + w // 2},{y - 20} {x + w},{y}" fill="{c2}" opacity="0.4"/>'
        )
        if rng.random() < 0.5:
            parts.append(
                f'<rect x="{x + w // 4}" y="{y + h // 3}" width="{max(8, w // 4)}" '
                f'height="{h // 2}" rx="2" fill="#ffc8dd" opacity="0.28"/>'
            )
    return "\n  ".join(parts)


def _wood_fence(rng: random.Random, y: int = 992) -> str:
    parts = []
    posts = 28
    for i in range(posts):
        x = 48 + i * 68
        parts.append(
            f'<rect x="{x}" y="{y - 48}" width="7" height="58" rx="2" fill="#5a4a38" opacity="0.5"/>'
        )
    parts.append(
        f'<rect x="40" y="{y - 30}" width="{posts * 68}" height="5" rx="2" fill="#5a4a38" opacity="0.44"/>'
        f'<rect x="40" y="{y - 12}" width="{posts * 68}" height="4" rx="2" fill="#5a4a38" opacity="0.38"/>'
    )
    return "\n  ".join(parts)


def _figure_silhouette(x: int, y: int, scale: float = 1.0) -> str:
    s = scale
    return (
        f'<ellipse cx="{x}" cy="{y}" rx="{int(9 * s)}" ry="{int(11 * s)}" fill="#3a3548" opacity="0.36"/>'
        f'<path d="M{x - int(15 * s)},{y + int(24 * s)} Q{x},{y + int(10 * s)} '
        f'{x + int(15 * s)},{y + int(24 * s)}" fill="#3a3548" opacity="0.33"/>'
        f'<line x1="{x - int(11 * s)}" y1="{y + int(12 * s)}" x2="{x - int(20 * s)}" '
        f'y2="{y + int(30 * s)}" stroke="#3a3548" stroke-width="3" opacity="0.32"/>'
        f'<line x1="{x + int(11 * s)}" y1="{y + int(12 * s)}" x2="{x + int(20 * s)}" '
        f'y2="{y + int(30 * s)}" stroke="#3a3548" stroke-width="3" opacity="0.32"/>'
    )


def _xianxia_peaks_detail(c2: str, c3: str, c4: str) -> str:
    parts = []
    peaks = [(280, 400, 300), (640, 360, 360), (1060, 385, 330), (1520, 430, 280)]
    for cx, tip_y, w in peaks:
        parts.append(
            f'<polygon points="{cx - w // 2},920 {cx},{tip_y} {cx + w // 2},920" '
            f'fill="{c3}" opacity="0.58"/>'
            f'<polygon points="{cx - w // 4},920 {cx},{tip_y + 90} {cx + w // 4},920" '
            f'fill="{c2}" opacity="0.38"/>'
        )
        parts.append(
            f'<path d="M{cx - 70},{tip_y + 130} Q{cx},{tip_y + 85} {cx + 70},{tip_y + 130}" '
            f'fill="none" stroke="{c4}" stroke-width="3" opacity="0.28"/>'
        )
    for i in range(8):
        fx = 160 + i * 220
        parts.append(
            f'<path d="M{fx},690 Q{fx + 45},645 {fx + 90},690" fill="none" stroke="#c8b8e8" '
            f'stroke-width="2" opacity="0.32"/>'
            f'<ellipse cx="{fx + 45}" cy="655" rx="18" ry="8" fill="#eef5e8" opacity="0.22"/>'
        )
    return "\n  ".join(parts)


def _beach_foreground(rng: random.Random, c4: str) -> str:
    parts = [
        f'<path d="M0,920 Q480,880 960,910 T1920,895 L1920,1080 L0,1080 Z" '
        f'fill="#faf6ed" opacity="0.55"/>',
        f'<path d="M0,960 Q640,930 1280,955 T1920,940 L1920,1080 L0,1080 Z" '
        f'fill="#e8dcc8" opacity="0.45"/>',
    ]
    for _ in range(12):
        x = rng.randint(80, 1840)
        parts.append(
            f'<ellipse cx="{x}" cy="{rng.randint(930, 1000)}" rx="{rng.randint(8, 22)}" '
            f'ry="4" fill="{c4}" opacity="0.25"/>'
        )
    return "\n  ".join(parts)


def _cherry_petals(rng: random.Random, count: int = 25) -> str:
    parts = []
    for _ in range(count):
        x = rng.randint(0, 1920)
        y = rng.randint(200, 700)
        parts.append(
            f'<ellipse cx="{x}" cy="{y}" rx="8" ry="5" fill="#ffc8dd" opacity="0.55" '
            f'transform="rotate({rng.randint(0, 180)} {x} {y})"/>'
        )
    return "\n  ".join(parts)


def _lightning() -> str:
    return (
        f'<path d="M920,180 L900,320 L940,320 L880,520 L960,340 L920,340 Z" '
        f'fill="#eef5e8" opacity="0.65"/>'
        f'<path d="M920,180 L900,320 L940,320 L880,520 L960,340 L920,340 Z" '
        f'fill="#a8d4ff" opacity="0.25"/>'
    )


def _storm_clouds(rng: random.Random) -> str:
    parts = []
    for cx in (400, 960, 1400):
        parts.append(_cloud_cluster(rng, cx, 200, 1.4, 0.45))
    return "\n  ".join(parts)


def _scene_extras(name: str, rng: random.Random, c2: str, c3: str, c4: str) -> str:
    extras: list[str] = []
    if "windmill" in name:
        extras.append(_windmill(c4))
    if "lighthouse" in name or "cliff" in name:
        extras.append(_lighthouse(c4))
    if "dock" in name or "lakeside" in name:
        extras.append(_dock(c4))
    if "clock" in name:
        extras.append(
            f'<rect x="880" y="280" width="160" height="320" rx="8" fill="{c3}" opacity="0.65"/>'
            f'<circle cx="960" cy="440" r="60" fill="{c4}" opacity="0.5"/>'
            f'<line x1="960" y1="440" x2="960" y2="400" stroke="#2a3848" stroke-width="4"/>'
            f'<line x1="960" y1="440" x2="990" y2="450" stroke="#2a3848" stroke-width="3"/>'
        )
    if "tram" in name:
        extras.append(
            f'<line x1="200" y1="420" x2="1720" y2="380" stroke="#4a5868" stroke-width="3" opacity="0.45"/>'
            f'<rect x="680" y="360" width="180" height="48" rx="12" fill="{c2}" opacity="0.7"/>'
            f'<rect x="700" y="372" width="40" height="28" rx="4" fill="{c4}" opacity="0.45"/>'
        )
    if "observatory" in name:
        extras.append(
            f'<ellipse cx="960" cy="620" rx="180" ry="80" fill="{c3}" opacity="0.55"/>'
            f'<rect x="900" y="520" width="120" height="100" rx="60" fill="{c2}" opacity="0.6"/>'
            f'<rect x="930" y="480" width="60" height="50" rx="8" fill="{c4}" opacity="0.45"/>'
        )
    if "campsite" in name:
        extras.append(
            f'<polygon points="960,780 860,920 1060,920" fill="#c45c6a" opacity="0.55"/>'
            f'<circle cx="920" cy="880" r="18" fill="#ffc8dd" opacity="0.5"/>'
        )
    if "ghost" in name:
        extras.append(
            f'<rect x="720" y="420" width="480" height="340" rx="12" fill="{c3}" opacity="0.45"/>'
            f'<polygon points="720,420 960,300 1200,420" fill="{c2}" opacity="0.4"/>'
            f'<rect x="860" y="560" width="60" height="100" rx="4" fill="#1a2030" opacity="0.35"/>'
        )
    if "volcano" in name:
        extras.append(
            f'<polygon points="760,920 960,380 1160,920" fill="{c3}" opacity="0.6"/>'
            f'<ellipse cx="960" cy="400" rx="40" ry="20" fill="#f8a8c8" opacity="0.55"/>'
        )
    if "desert" in name or "oasis" in name:
        for px in (400, 800, 1300):
            extras.append(_pine(rng, px, 900, 0.8, c3))
    if "sakura" in name or "cherry" in name:
        extras.append(_cherry_petals(rng, 30))
    if "flower" in name:
        extras.append(_flowers(rng, 40))
    if "autumn" in name:
        for _ in range(20):
            x = rng.randint(100, 1820)
            extras.append(
                f'<ellipse cx="{x}" cy="{rng.randint(700, 950)}" rx="10" ry="6" '
                f'fill="#c45c6a" opacity="0.55" transform="rotate({rng.randint(0, 120)} {x} 800)"/>'
            )
    if "bamboo" in name:
        for bx in range(120, 1800, 80):
            extras.append(
                f'<rect x="{bx}" y="480" width="10" height="{rng.randint(280, 420)}" '
                f'rx="3" fill="#5a7860" opacity="0.55"/>'
                f'<line x1="{bx - 20}" y1="{600 + bx % 80}" x2="{bx + 30}" y2="{620 + bx % 80}" '
                f'stroke="#6b8e6b" stroke-width="2" opacity="0.35"/>'
            )
    return "\n  ".join(extras)


def _compose(name: str, comp: str, c1: str, c2: str, c3: str, c4: str, c5: str) -> str:
    rng = _rng(name)
    outdoor = comp not in ("interior", "cave")
    nightish = comp in ("night", "storm") or "night" in name or "ghost" in name

    layers: list[str] = [
        _watercolor_wash(_rng(name, 99), c1, c2, c3),
        _light_rays(c5, night=nightish),
        _clouds(rng, 16 if outdoor else 6),
        _bokeh(rng, c4, 24),
    ]

    if comp in ("mountain", "sky", "fog", "storm", "oasis"):
        layers.append(_mountain_layers(_rng(name, 1), c2, c3))
    else:
        layers.append(_hills(_rng(name, 2), c2, c3))

    if outdoor and comp in ("meadow", "sky", "train"):
        layers.append(_distant_village(_rng(name, 31), c2, c3))

    if "xianxia" in name:
        layers.append(_xianxia_peaks_detail(c2, c3, c5))

    if comp in ("forest", "rain", "fog", "meadow", "shrine", "snow"):
        tree_n = 22 if comp == "forest" else 14
        layers.append(_tree_grove(_rng(name, 3), tree_n, c3))

    if comp in ("city", "night"):
        layers.append(_cityscape(_rng(name, 4), c2, c3, c4))

    if comp in ("water", "oasis"):
        layers.append(_water(_rng(name, 5), c1, c2, c4))
        layers.append(_reflection(_rng(name, 6), c4))

    if comp == "train":
        layers.append(_train(_rng(name, 7), c2, c4))
        layers.append(_tree_grove(_rng(name, 8), 12, c3))

    if comp == "shrine":
        layers.append(_torii(c4))
        layers.append(_stone_lanterns(_rng(name, 9), 6))
        layers.append(_path(_rng(name, 10), c4))
        layers.append(_wood_fence(_rng(name, 32)))

    if comp == "night":
        layers.append(_stars(_rng(name, 11), c4, 120))
        layers.append(_moon(c4))
        layers.append(_lanterns(_rng(name, 12), 14))

    if comp == "rain":
        layers.append(_rain(_rng(name, 13), 85))
        layers.append(_tree_grove(_rng(name, 14), 14, c3))

    if comp == "snow":
        layers.append(_snow(_rng(name, 15), 70))
        layers.append(_path(_rng(name, 16), "#faf6ed"))

    if comp == "mist" or comp == "fog":
        layers.append(_mist_layers(c4))

    if comp == "storm":
        layers.append(_storm_clouds(_rng(name, 17)))
        layers.append(_lightning())
        layers.append(_rain(_rng(name, 18), 55))

    if comp == "sky":
        if "castle" in name:
            layers.append(_castle(c2, c4))
        if "floating" in name:
            for cx in (400, 960, 1500):
                layers.append(_floating_isle(_rng(name, 19), cx, 520 + (cx % 200), 140, c2, c3))
        layers.append(_clouds(_rng(name, 20), 8))

    if comp == "mountain":
        if "pagoda" in name or "xianxia" in name:
            layers.append(_pagoda(c2, c4))
        if "rice" in name:
            layers.append(_rice_terraces(c2, c3))

    if comp == "cave":
        layers.append(_cave_elements(c4))

    if comp == "ruins":
        layers.append(_ruins(_rng(name, 21), c3, c4))

    if comp == "interior":
        layers = [
            _interior(name, _rng(name, 22), c2, c3, c4),
            _bokeh(_rng(name, 23), c4, 16),
            _watercolor_wash(_rng(name, 24), c1, c2, c3, 12),
        ]

    if comp == "meadow":
        layers.append(_flowers(_rng(name, 24), 35))
        layers.append(_wildflowers_dense(_rng(name, 33), 30))
        layers.append(_path(_rng(name, 25), c4))
        if rng.random() < 0.7:
            layers.append(_figure_silhouette(rng.randint(700, 1200), rng.randint(780, 860), 1.2))

    if "waterfall" in name:
        layers.append(_waterfall(c1, c4))

    if "lantern" in name and comp != "night":
        layers.append(_lanterns(_rng(name, 26), 22))

    if "harbor" in name or "canal" in name or "moon_bridge" in name or "crystal" in name:
        layers.append(_water(_rng(name, 27), c1, c2, c4))
        if "moon" in name:
            layers.append(_moon(c4, 960, 220))
            layers.append(_stars(_rng(name, 28), c4, 50))

    if "beach" in name or "storm_coast" in name:
        layers.append(_water(_rng(name, 29), c1, c2, c4))
        layers.append(_beach_foreground(_rng(name, 34), c4))

    layers.append(_scene_extras(name, _rng(name, 30), c2, c3, c4))

    if outdoor:
        layers.append(_birds(_rng(name, 35), 12 if not nightish else 4))
        layers.append(_grass_foreground(_rng(name, 36), 95))
        layers.append(_wildflowers_dense(_rng(name, 38), 22))
        if comp in ("meadow", "shrine", "forest") and "beach" not in name:
            layers.append(_wood_fence(_rng(name, 37)))

    return "\n  ".join(filter(None, layers))


def render_scene(name: str, colors: tuple[str, str, str, str, str, str]) -> str:
    c1, c2, c3, c4, c5, comp = colors
    seed = sum(ord(ch) for ch in name)
    body = _compose(name, comp, c1, c2, c3, c4, c5)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" role="img" aria-label="{name}">
  <defs>
    <linearGradient id="sky-{seed}" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="35%" stop-color="{c2}"/>
      <stop offset="68%" stop-color="{c3}"/>
      <stop offset="100%" stop-color="{c4}"/>
    </linearGradient>
    <radialGradient id="sun-{seed}" cx="76%" cy="18%" r="42%">
      <stop offset="0%" stop-color="{c5}" stop-opacity="0.8"/>
      <stop offset="55%" stop-color="{c5}" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="{c5}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glow-{seed}" cx="22%" cy="78%" r="35%">
      <stop offset="0%" stop-color="{c5}" stop-opacity="0.18"/>
      <stop offset="100%" stop-color="{c5}" stop-opacity="0"/>
    </radialGradient>
    <filter id="paper-{seed}" x="0" y="0" width="100%" height="100%">
      <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves="3" result="noise"/>
      <feColorMatrix in="noise" type="saturate" values="0" result="gray"/>
      <feBlend in="SourceGraphic" in2="gray" mode="multiply" result="blend"/>
    </filter>
  </defs>
  <g filter="url(#paper-{seed})">
  <rect width="1920" height="1080" fill="url(#sky-{seed})"/>
  <rect width="1920" height="1080" fill="url(#sun-{seed})"/>
  <rect width="1920" height="1080" fill="url(#glow-{seed})"/>
  {body}
  </g>
</svg>
"""


def main() -> None:
    out = Path(__file__).resolve().parent.parent / "frontend" / "images" / "scenes"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.svg"):
        old.unlink()
    for name, colors in SCENES.items():
        (out / f"{name}.svg").write_text(render_scene(name, colors), encoding="utf-8")
    print(f"Wrote {len(SCENES)} rich Ghibli scene SVGs to {out}")


if __name__ == "__main__":
    main()
