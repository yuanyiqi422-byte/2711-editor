#!/usr/bin/env python3
"""Build 2711-style GenerateImage prompts from templates + art-style.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent
TEMPLATES = SCRIPTS / "art-prompt-templates.json"
ART_STYLE = SCRIPTS / "art-style.json"


def _load() -> tuple[dict, dict]:
    templates = json.loads(TEMPLATES.read_text(encoding="utf-8"))
    art = json.loads(ART_STYLE.read_text(encoding="utf-8"))
    return templates, art


def _fmt(pattern: str, art: dict, subject: str, *, bg_suffix: str = "") -> str:
    mapping = {
        "subject": subject.strip(),
        "style_prefix": art.get("style_prefix", ""),
        "landing_prefix": art.get("landing_prefix", ""),
        "ui_prefix": art.get("ui_prefix", ""),
        "crowd_suffix": art.get("crowd_sparse_suffix", ""),
        "scene_negative": art.get("scene_negative", ""),
        "negative": art.get("negative", ""),
        "bg_suffix": bg_suffix,
    }
    out = pattern
    for key, val in mapping.items():
        out = out.replace("{" + key + "}", val)
    return " ".join(out.split())


def build_prompt(category: str, subject: str, *, crowd: str = "sparse") -> dict[str, str]:
    templates, art = _load()
    cats = templates["categories"]
    if category not in cats:
        raise SystemExit(f"Unknown category {category!r}. Choose: {', '.join(cats)}")

    spec = cats[category]
    bg_suffix = ""
    if spec.get("remove_bg"):
        bg_suffix = spec.get("bg_prompt_suffix", "")

    crowd_suffix = art.get("crowd_sparse_suffix", "")
    if crowd == "social":
        crowd_suffix = art.get("crowd_social_suffix", crowd_suffix)
    elif crowd == "empty":
        crowd_suffix = art.get("crowd_empty_suffix", crowd_suffix)

    art = {**art, "crowd_sparse_suffix": crowd_suffix}
    prompt = _fmt(spec["prompt_pattern"], art, subject, bg_suffix=bg_suffix)

    neg_parts = [templates.get("base_negative", "")]
    neg_append = spec.get("negative_append", "")
    if neg_append:
        neg_parts.append(_fmt(neg_append, art, subject))

    negative = ", ".join(p for p in neg_parts if p.strip())
    return {"prompt": prompt, "negative": negative, "category": category, "spec": spec}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build 2711 asset prompt")
    parser.add_argument("category", choices=["scene", "landing", "ui", "icon", "workbench"])
    parser.add_argument("subject", help="English subject description")
    parser.add_argument("--crowd", choices=["social", "sparse", "empty"], default="sparse")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    result = build_prompt(args.category, args.subject, crowd=args.crowd)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PROMPT:")
        print(result["prompt"])
        print()
        print("NEGATIVE:")
        print(result["negative"])


if __name__ == "__main__":
    main()
