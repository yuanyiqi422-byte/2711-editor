# Brand Panel v2 · Design Spec

> **Status:** Assets only — not wired into `index.html` yet.  
> **Files:** `brand-panel-v2-a.png` (panel frame) · `brand-panel-v2-b.png` (full mockup)

## Design Rationale

Replaces the current dark gold/silver CSS-gradient lockup with a **2D anime / Ghibli-inspired parchment badge** that matches the site’s healing pastel palette (sky blue, sakura pink, meadow mint). Variant **A** is the production path: raster frame + live CSS text (i18n, `data-brand`, reduced-motion). Variant **B** is a reference mockup for typography/color targets.

---

## Recommended Colors (`tokens.css`)

| Role | Token | Value / usage |
|------|-------|----------------|
| Panel fill (fallback under image) | `--light-paper` / `--light-paper-soft` | `#F5F1EA` — matches parchment center in v2-a |
| Border / filigree accent | `--sky` + `--brand-panel-border` | `#8fa4c8` · `rgba(143, 164, 200, 0.16)` |
| Pink gradient edge | `--sakura` / `--sakura-soft` | `#d89aa5` · `rgba(216, 154, 165, 0.35)` |
| Mint accent | `--meadow` / `--meadow-light` | `#9bc49d` · corner crystals/feathers |
| Gold trim | `--vn-gold` / `--gold-soft` | `#D6B06A` · `#e8d4b0` — filigree, rules |
| Primary title gradient | `--brand-title-shine` | gold → ivory → sky sweep on `2711` / `编辑器` |
| Title glow (hover/breathe) | `--brand-title-glow` | `rgba(143, 196, 220, 0.42)` |
| EN subline | `--brand-subline-color` | `rgba(168, 178, 196, 0.62)` |
| Decorative rules | `--brand-rule-color` | `rgba(143, 164, 200, 0.38)` |
| Outer shadow | `--shadow-card` + `--brand-panel-glow` | depth + soft sky halo |

**New tokens to add when wiring (optional):**

```css
--brand-panel-v2-image: url("../images/ui/brand-panel-v2-a.png");
--brand-panel-v2-aspect: 800 / 500; /* processed size */
```

---

## Font Pairing

Keep existing brand stack — it already matches v2-b mockup intent:

| Element | Token | Stack |
|---------|-------|-------|
| `2711` numerals | `--font-brand-num` | Jost → Cormorant Garamond → Noto Serif SC |
| `编辑器` | `--font-brand-cn` | Noto Serif SC → ZCOOL XiaoWei |
| `2711 EDITOR` | `--font-brand-en` | Cinzel → Cormorant Garamond |

**Sizing (unchanged):** num `clamp(1.55rem, 3.2vh, 2rem)` · label `clamp(1.28rem, 2.6vh, 1.65rem)` · EN `clamp(0.5rem, 0.95vh, 0.625rem)`.

---

## Wiring Guide (later)

### Selectors

- **Link wrapper:** `.brand-lockup.workbench__brand`
- **Panel / background host:** `.brand-lockup__panel` · `.workbench__brand-mark`
- **Text layers (keep as HTML):** `.brand-lockup__num`, `.workbench__brand-num`, `.brand-lockup__label`, `.workbench__brand-en`, `.brand-lockup__subline`, `.brand-lockup__rule`

### Option A — Panel image + CSS text (recommended)

In `frontend/css/brand-lockup.css`, on `.brand-lockup__panel` / `.workbench__brand-mark`:

```css
.brand-lockup .brand-lockup__panel,
.brand-lockup .workbench__brand-mark {
  position: relative;
  background-color: var(--light-paper);
  background-image: var(--brand-panel-v2-image);
  background-size: 100% 100%;
  background-repeat: no-repeat;
  border: none; /* frame is in the image */
  box-shadow: var(--shadow-card), 0 0 20px var(--brand-panel-glow);
}

.brand-lockup .brand-lockup__main,
.brand-lockup .workbench__brand-zh {
  position: relative;
  z-index: 1;
}
```

Bump `css/brand-lockup.css?v=` in `index.html` after edit.

### Option B — Full raster lockup

Replace inner markup with a single `<img src="images/ui/brand-panel-v2-b.png" alt="2711编辑器" />` inside `.workbench__brand-mark`. **Downside:** loses `data-brand` i18n and gradient text animations.

### Hover / focus

- Retain `translateY(-1px)` on `.brand-lockup.workbench__brand:hover`
- Strengthen `--brand-panel-glow` and `--brand-title-glow` on hover instead of swapping border color

### Responsive

- Processed asset: **800×500** — scales cleanly in topbar `clamp()` padding
- At `max-width: 420px`, consider hiding `.brand-lockup__subline` if panel feels tight

---

## Asset Manifest

Registered in `frontend/images/manifest.json` under `ui[]`:

- `brand-panel-v2-a` → `images/ui/brand-panel-v2-a.png`
- `brand-panel-v2-b` → `images/ui/brand-panel-v2-b.png`
