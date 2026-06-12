# Brand Panel v3 · Design Spec

> **Status:** Assets + draft CSS only — **not** linked in `index.html` yet.  
> **Files:** `brand-panel-v3-frame.png` (transparent cutout frame) · `brand-panel-v3-full.png` (reference mockup) · `brand-panel-v3-typography-only.png` (optional text reference)

## Design Rationale (v2 → v3)

| v2 feedback | v3 response |
|-------------|-------------|
| Typography must feel **designed** and brand-forward | Stronger gradient stacks on `2711` / `编辑器`; Jost + Noto Serif SC + Cinzel pairing retained but with higher weight & clearer gold→sky sweep |
| Panel too eye-catching vs soft healing site | **No opaque fill** — transparent center cutout frame only; whisper shadows; reduced hover glow |
| Needs cutout / transparent version | Production path: raster **frame** + live CSS text (i18n, `data-brand`, reduced-motion) |

v3 is intentionally **quieter** than v2-a (parchment fill) and v1 (dark gold block). It blends into sky / landing backgrounds while keeping readable, premium wordmark typography via CSS.

---

## Assets

| ID | Path | Size | Role |
|----|------|------|------|
| `brand-panel-v3-frame` | `images/ui/brand-panel-v3-frame.png` | 600×200 | **Production** — transparent cutout decorative border only; center hole for HTML text |
| `brand-panel-v3-full` | `images/ui/brand-panel-v3-full.png` | 800×320 | Reference mockup — typography + soft pastel panel for color/target review |
| `brand-panel-v3-typography-only` | `images/icons/brand-panel-v3-typography-only.png` | 600×200 | Optional — raster text treatment on transparent bg (fallback / QA reference) |

Frame processed with `rembg`; full mockup kept opaque for reference.

---

## Recommended Colors (`tokens.css`)

Use existing healing palette — **avoid** `--brand-panel-bg` dark gradient on v3.

| Role | Token | Value / usage |
|------|-------|----------------|
| Frame (no CSS fill) | — | `background: transparent` — frame image carries all border decoration |
| Fallback under frame (optional) | transparent | Do **not** use `--light-paper` fill unless frame alpha fails on a specific bg |
| `2711` numeral gradient | `--brand-v3-num-shine` *(draft)* | `#b8955a` → `#D6B06A` → `#8fa4c8` — gold-sky sweep, readable on pastel sky |
| `编辑器` label gradient | `--brand-v3-label-shine` *(draft)* | `#a07840` → `#c9a050` → `#6b84a8` — warmer gold with sky anchor |
| EN subline | `--brand-subline-color` | `rgba(168, 178, 196, 0.62)` — already quiet |
| Decorative rules | `--brand-rule-color` | `rgba(143, 164, 200, 0.38)` |
| Border accent (hover) | `--sky-soft` / `--sakura-soft` | `rgba(143, 164, 200, 0.35)` · `rgba(216, 154, 165, 0.35)` |
| Hover halo (subtle) | `--brand-panel-glow` | `rgba(143, 164, 200, 0.12)` — **half** v1/v2 intensity |
| Readable shadow on light bg | `--brand-v3-text-shadow` *(draft)* | `0 1px 2px rgba(45, 50, 64, 0.12)` — replaces heavy dark drop-shadow |

**Draft CSS custom properties** (defined in `brand-panel-v3-draft.css`, wire into `tokens.css` when promoting):

```css
--brand-panel-v3-frame: url("../images/ui/brand-panel-v3-frame.png");
--brand-panel-v3-aspect: 600 / 200;
--brand-v3-num-shine: linear-gradient(118deg, #b8955a 0%, #D6B06A 32%, #8fa4c8 68%, #6b84a8 100%);
--brand-v3-label-shine: linear-gradient(112deg, #8a6840 0%, #c9a050 38%, #8fa4c8 100%);
--brand-v3-text-shadow: 0 1px 2px rgba(45, 50, 64, 0.12), 0 0 1px rgba(255, 255, 255, 0.4);
```

On **dark workbench topbar**, optionally scope stronger shine via:

```css
.workbench__topbar .brand-lockup--v3 .brand-lockup__num {
  background: var(--brand-title-shine); /* existing dark-bg stack */
}
```

---

## Font Pairing

Keep existing brand stack — proven on mockups:

| Element | Token | Stack | v3 notes |
|---------|-------|-------|----------|
| `2711` | `--font-brand-num` | Jost → Cormorant Garamond → Noto Serif SC | `font-weight: 700`; `letter-spacing: 0.06em`; lining nums |
| `编辑器` | `--font-brand-cn` | Noto Serif SC → ZCOOL XiaoWei | `font-weight: 700`; `letter-spacing: 0.12em` — stronger serif presence |
| `2711 EDITOR` | `--font-brand-en` | Cinzel → Cormorant Garamond | `font-weight: 600`; `letter-spacing: 0.22em`; uppercase |

**Sizing (slightly bolder than v2 lockup):**

| Element | Size |
|---------|------|
| Numerals | `clamp(1.6rem, 3.4vh, 2.05rem)` |
| Chinese label | `clamp(1.32rem, 2.7vh, 1.7rem)` |
| EN subline | `clamp(0.52rem, 1vh, 0.65rem)` |

---

## Transparent Frame as `background-image`

Production pattern (see `brand-panel-v3-draft.css`):

```css
.brand-lockup--v3 .brand-lockup__panel {
  position: relative;
  background: transparent;
  border: none;
  box-shadow: none;

  background-image: var(--brand-panel-v3-frame);
  background-size: 100% 100%;
  background-repeat: no-repeat;
  background-position: center;

  /* Frame aspect — padding scales with badge width */
  aspect-ratio: var(--brand-panel-v3-aspect);
  min-width: clamp(168px, 28vw, 240px);
  padding: clamp(10px, 1.4vh, 14px) clamp(18px, 2.4vw, 28px) clamp(8px, 1.1vh, 11px);
}
```

Text layers sit above the frame hole:

```css
.brand-lockup--v3 .brand-lockup__main,
.brand-lockup--v3 .brand-lockup__subline {
  position: relative;
  z-index: 1;
}
```

**Do not** set `background-color` on the panel — the cutout must show the page sky/gradient through the center.

---

## Gradient Text (CSS)

### `2711` numerals

```css
.brand-lockup--v3 .brand-lockup__num {
  font-family: var(--font-brand-num);
  font-weight: 700;
  background: var(--brand-v3-num-shine);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(var(--brand-v3-text-shadow));
}
```

### `编辑器`

```css
.brand-lockup--v3 .brand-lockup__label {
  font-family: var(--font-brand-cn);
  font-weight: 700;
  background: var(--brand-v3-label-shine);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  -webkit-text-fill-color: transparent;
}
```

Split numeral treatment (optional, matches mockup “27” warm / “11” cool):

```css
.brand-lockup--v3 .brand-lockup__num-part--warm {
  background: linear-gradient(160deg, #c9a050 0%, #e8d4b0 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.brand-lockup--v3 .brand-lockup__num-part--cool {
  background: linear-gradient(160deg, #e4eaf4 0%, #8fa4c8 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
```

Requires HTML split: `<span class="brand-lockup__num-part--warm">27</span><span class="brand-lockup__num-part--cool">11</span>` — defer until wiring.

### `2711 EDITOR` + rules

Reuse existing rule gradients from `brand-lockup.css`; EN uses `--brand-subline-color` solid (not gradient) for quieter subline on light backgrounds:

```css
.brand-lockup--v3 .brand-lockup__en {
  color: var(--brand-subline-color);
  background: none;
  -webkit-text-fill-color: currentColor;
}
```

---

## Wiring Guide (later)

### Selectors

- Add modifier: `.brand-lockup--v3` on `.workbench__brand`
- Panel: `.brand-lockup__panel` / `.workbench__brand-mark`
- Text: unchanged HTML structure in `index.html`

### Steps

1. Link `css/brand-panel-v3-draft.css?v=1` **or** merge into `brand-lockup.css`
2. Add `brand-lockup--v3` class to navbar brand anchor
3. Remove / override v1 dark `--brand-panel-bg` rules for v3 modifier
4. Bump `?v=` on CSS link in `index.html`
5. Compare against `brand-panel-v3-full.png` on landing sky bg

### Hover / focus (quiet)

- `translateY(-0.5px)` max — less bounce than v1
- Opacity `0.92 → 1` instead of heavy box-shadow bloom
- Optional: `filter: brightness(1.04)` on text, not panel

### Responsive

- Frame 600×200 scales cleanly; at `max-width: 420px` hide `.brand-lockup__subline`
- At `max-width: 360px` reduce numeral `letter-spacing` to `0.04em`

### Option B — Full raster

`<img src="images/ui/brand-panel-v3-full.png" alt="2711编辑器" />` — loses i18n; use only for static marketing slices.

---

## Asset Manifest

Registered in `frontend/images/manifest.json` under `ui[]`:

- `brand-panel-v3-frame` → `images/ui/brand-panel-v3-frame.png`
- `brand-panel-v3-full` → `images/ui/brand-panel-v3-full.png`
- `brand-panel-v3-typography-only` → `images/icons/brand-panel-v3-typography-only.png`

---

## Related Files

- Draft CSS: `frontend/css/brand-panel-v3-draft.css` (not linked)
- Current production lockup: `frontend/css/brand-lockup.css`
- v2 spec (superseded for cutout path): `frontend/images/ui/brand-panel-v2-SPEC.md`
