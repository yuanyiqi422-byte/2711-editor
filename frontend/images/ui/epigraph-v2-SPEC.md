# Epigraph v2 · Design Spec

> **Status:** Draft — assets + CSS ready, **not wired** in `index.html`.  
> **Review:** Compare live CSS against mockups before linking `epigraph-v2-draft.css`.

## Intent

Redesign the workbench topbar epigraph (two English quote lines) with more typographic craft while keeping the **WLJ / MZC** six-letter accent system. Palette stays **sky blue + sakura pink** on dark VN chrome, aligned with 2711 Ghibli pastel healing aesthetic.

## Reference Assets

| File | Size | Purpose |
|------|------|---------|
| `images/ui/epigraph-v2-mockup.png` | 900×120 | Full banner mockup — both lines, divider, glow |
| `images/ui/epigraph-v2-letters-detail.png` | 600×300 | Close-up of W L J (pink) and M Z C (blue) letter treatment |

Both registered in `frontend/images/manifest.json` (`source: generated`).

## Copy & Highlight Logic (unchanged)

| Line | `data-brand` | Text | Highlight letters |
|------|--------------|------|-------------------|
| 1 | `quoteLuminous` | Wish you a Luminous Journey | **W** **L** **J** → pink |
| 2 | `quoteZest` | May your Zest Continue to shine | **M** **Z** **C** → blue |

`frontend/js/brand.js` wraps caps in `<span class="workbench__epigraph-cap">` — **no HTML/JS changes** for v2.

## Token Mapping

| Role | Token | Usage |
|------|-------|-------|
| Line 1 body | `--sky`, `--sky-soft`, `--sky-deep` | Base text + cool glow |
| Line 2 body | `--sakura`, `--sakura-soft` | Base text + warm glow |
| WLJ caps | `--sakura` gradient + `--sakura-soft` glow | Gradient `background-clip: text` |
| MZC caps | `--sky` gradient + `--sky-soft` glow | Inverted accent vs line body |
| Divider | `--sky` → `--vn-gold` → `--sakura` | Ethereal bridge between lines |
| Divider dot | `--vn-ivory`, `--sky-soft`, `--sakura-soft` | Central pulse focal point |
| Ink / chrome | `--ink`, `--vn-bg-deep` | Inherited from topbar context |

## Typography (v2 vs v1)

| Property | v1 (`workbench-layout.css`) | v2 (`epigraph-v2-draft.css`) |
|----------|-------------------------------|------------------------------|
| Family | `Outfit` (`--font-display-en`) | `Cormorant Garamond` fallback → more literary italic |
| Cap size | `1.14em`, small-caps variant | `1.18em`, normal variant, gradient fill |
| Cap weight | 500 | 600 |
| Letter-spacing | `0.06em` line / `0.03em` cap | `0.08em` line / `0.04em` cap |
| Underline | 1px `currentColor` @ 22% opacity | Gradient hairline + optional center dot on L/Z |
| Separator | Gold-only gradient + `·` glyph | Sky↔gold↔sakura gradient + radial glow dot |
| Motion | None | Subtle breathe on caps + sep pulse; disabled under `prefers-reduced-motion` |

## CSS Selectors (draft file)

```
.workbench__epigraph
.workbench__epigraph-line
.workbench__epigraph-line--luminous
.workbench__epigraph-line--zest
.workbench__epigraph-cap
.workbench__epigraph-line--luminous .workbench__epigraph-cap   → pink gradient
.workbench__epigraph-line--zest .workbench__epigraph-cap      → blue gradient
.workbench__epigraph-cap::after                               → gradient underline
.workbench__epigraph-cap::before                              → dot on 2nd cap (L, Z)
.workbench__epigraph-sep
.workbench__epigraph-sep::before / ::after                     → dot + soft aura
```

## Wiring Checklist (when approved)

1. Add after `workbench-layout.css` in `index.html`:
   ```html
   <link rel="stylesheet" href="css/epigraph-v2-draft.css?v=1" />
   ```
2. Bump `?v=` on link tag after tweaks.
3. Optionally **remove** duplicate epigraph rules from `workbench-layout.css` (lines ~41–127) to avoid cascade fights — or rename draft → production and replace in-place.
4. Ensure `Cormorant Garamond` is loaded (check `index.html` font links; add if missing).
5. Visual QA at 1280 / 768 / 390 widths in workbench topbar.

## Design Notes from Mockups

- **Contrast inversion:** Line 1 is sky body + pink caps; line 2 is pink body + blue caps — creates rhythmic call-and-response.
- **Glow restraint:** Caps use `drop-shadow` not heavy `text-shadow` to keep gradient text legible.
- **Divider as bridge:** Mixed sky/sakura/gold gradient ties the two accent colors without introducing new hues.
- **No bounce:** Animations are slow breathe/pulse only; no elastic easing per project anti-patterns.

## Files Delivered

| Path | Type |
|------|------|
| `frontend/images/ui/epigraph-v2-mockup.png` | Reference asset |
| `frontend/images/ui/epigraph-v2-letters-detail.png` | Reference asset |
| `frontend/css/epigraph-v2-draft.css` | Ready-to-apply CSS |
| `frontend/images/ui/epigraph-v2-SPEC.md` | This spec |
