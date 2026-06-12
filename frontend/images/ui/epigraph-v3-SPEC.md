# Epigraph v3 · Design Spec

> **Status:** Draft — assets + CSS ready, **not wired** in `index.html`.  
> **Review:** Compare live CSS against `epigraph-v3-mockup.png` before linking `epigraph-v3-draft.css`.

## Intent

Redesign the workbench topbar epigraph after v2 feedback:

1. Match overall 2711 warm healing aesthetic (not cold/tech)
2. Fix flat/squashed layout — more vertical breathing room, easier to read
3. **No illegible decorative fonts** — clean readable serif/humanist sans only
4. Feel **温暖治愈** — soft cream base, gentle glow, cozy not flashy

Keeps the **WLJ / MZC** six-letter accent system. HTML/JS unchanged.

## Reference Assets

| File | Size | Purpose |
|------|------|---------|
| `images/ui/epigraph-v3-mockup.png` | 1000×160 | Full banner mockup — both lines, divider, warm glow |

Registered in `frontend/images/manifest.json` (`source: generated`).

## Copy & Highlight Logic (unchanged)

| Line | `data-brand` | Text | Highlight letters |
|------|--------------|------|-------------------|
| 1 | `quoteLuminous` | Wish you a Luminous Journey | **W** **L** **J** → sakura pink |
| 2 | `quoteZest` | May your Zest Continue to shine | **M** **Z** **C** → sky blue |

`frontend/js/brand.js` wraps caps in `<span class="workbench__epigraph-cap">` — **no HTML/JS changes** for v3.

## v2 → v3 Changes (addressing feedback)

| Issue (v2) | v3 fix |
|------------|--------|
| Ornate italic Cormorant + gradient `background-clip: text` | Normal (non-italic) serif, **solid** cap colors |
| `clamp(11.5px … 14px)` too small | `clamp(15px … 17px)` with `line-height: 1.55` |
| Tight `gap: 6px`, flat banner feel | `gap: 8px`, `padding: 6px 0`, `max-width: 360px` |
| Cold sky/sakura body inversion | Warm **cream/ivory** base (`--vn-ivory`, `--vn-gold` mix) |
| Flashy cap breathe + sep pulse | Only subtle sep dot glow; caps static |
| `letter-spacing: 0.08em` spreads text thin | `0.02em` (near normal) |
| Cap size `1.18em` + weight 600 | Cap size `1.06em` — highlight without shouting |

## Token Mapping

| Role | Token | Usage |
|------|-------|-------|
| Line body (both) | `--vn-ivory`, `--vn-gold` | Warm cream/ink readable base |
| WLJ caps | `--sakura`, `--sakura-soft` | Solid pink + soft glow |
| MZC caps | `--sky`, `--sky-soft` | Solid blue + soft glow |
| Divider | `--vn-gold`, `--vn-ivory`, `--vn-glow-gold` | Warm gold bridge (not sky↔sakura rainbow) |
| Chrome context | `--vn-bg-deep`, `--vn-glow-warm` | Inherited dark topbar warmth |

## Typography

| Property | v1 (`workbench-layout.css`) | v2 (`epigraph-v2-draft.css`) | v3 (`epigraph-v3-draft.css`) |
|----------|-------------------------------|------------------------------|------------------------------|
| Family | `Outfit` | `Cormorant Garamond` italic | `Cormorant Garamond` **normal** (+ `Source Serif 4` fallback) |
| Size | `clamp(11px … 13px)` | `clamp(11.5px … 14px)` | **`clamp(15px … 17px)`** |
| Line-height | 1.45 | 1.5 | **1.55** |
| Letter-spacing | 0.06em | 0.08em | **0.02em** |
| Cap treatment | small-caps + color | gradient clip + underline + dot | **solid color** + subtle underline |
| Base color | sky / sakura bodies | sky / sakura bodies | **warm ivory cream** |
| Motion | none | cap breathe + sep pulse | **sep dot glow only** |

## CSS Selectors (draft file)

```
.workbench__epigraph
.workbench__epigraph-line
.workbench__epigraph-line--luminous
.workbench__epigraph-line--zest
.workbench__epigraph-cap
.workbench__epigraph-line--luminous .workbench__epigraph-cap   → solid sakura
.workbench__epigraph-line--zest .workbench__epigraph-cap      → solid sky
.workbench__epigraph-cap::after                               → 1px currentColor underline
.workbench__epigraph-sep
.workbench__epigraph-sep::before                              → warm gold dot
```

## Wiring Checklist (when approved)

1. Add after `workbench-layout.css` in `index.html`:
   ```html
   <link rel="stylesheet" href="css/epigraph-v3-draft.css?v=1" />
   ```
2. Bump `?v=` after tweaks.
3. Optionally add `Source Serif 4` to Google Fonts link (Cormorant already loaded).
4. Remove or override duplicate epigraph rules in `workbench-layout.css` (lines ~41–127) to avoid cascade fights.
5. Visual QA at 1280 / 768 / 390 widths in workbench topbar.

## Design Notes from Mockup

- **Readability first:** Entire line legible at a glance; caps distinguished by color + hairline underline, not size jump or gradient.
- **Warm base:** Cream ivory body anchors the epigraph to the VN healing palette instead of cold accent-on-accent.
- **Breathing room:** Taller aspect (~1000×160 mockup) informs looser gap/padding — text should not feel crushed in the topbar.
- **Gentle glow:** Warm `text-shadow` on lines; cap glow is soft and low-opacity.
- **No bounce:** Single slow sep animation; disabled under `prefers-reduced-motion`.

## Files Delivered

| Path | Type |
|------|------|
| `frontend/images/ui/epigraph-v3-mockup.png` | Reference asset (1000×160) |
| `frontend/css/epigraph-v3-draft.css` | Ready-to-apply CSS |
| `frontend/images/ui/epigraph-v3-SPEC.md` | This spec |
