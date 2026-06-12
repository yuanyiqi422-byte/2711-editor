# Console CTA v2 · Asset Spec & Wiring Notes

> **Status:** Assets only — HTML/CSS not wired yet.  
> **Scope:** `.workbench__cta--console` footer in `frontend/index.html` (开始游戏 panel).

## Asset Inventory

| ID | File | Size | Alpha | Role |
|----|------|------|-------|------|
| `console-outer-panel-v2` | `images/workbench/console-outer-panel-v2.png` | 1200×400 | No | Outer parchment/glass frame; center ~60% empty for button overlay |
| `console-start-btn-v2` | `images/workbench/console-start-btn-v2.png` | 480×120 | **Yes** | Inner button chrome only; live text stays in DOM |
| `console-full-mockup-v2` | `images/workbench/console-full-mockup-v2.png` | 1200×400 | No | Reference mockup (baked text); use for QA / fallback only |

All three registered in `frontend/images/manifest.json` (`ui[]`, `source: generated`).

## Recommended Integration (Layered)

Prefer **A + B + live HTML text** over the full mockup:

1. **Outer panel** → `.workbench__cta--console` background  
2. **Button chrome** → `.workbench__new-game` background (transparent PNG)  
3. **Copy** → keep existing DOM (`开始游戏`, `NEW GAME`, note line)

This preserves accessibility, loading states (`.is-loading`), and i18n without raster text.

## CSS Wiring Sketch

Target file: `frontend/css/workbench-console-cta.css`  
Bump `frontend/index.html` link: `workbench-console-cta.css?v=2` when applied.

### Outer panel — `.workbench__cta--console`

```css
.workbench__cta--console {
  /* Remove dark glass gradient + gold corner pseudo-borders when switching */
  background:
    url("../images/workbench/console-outer-panel-v2.png?v=2") center / 100% 100% no-repeat;
  border: none;
  backdrop-filter: none;
  box-shadow: none;
  /* Match art aspect: wide strip; current max-width 380px may crop — consider min(100%, 520px) */
  width: min(100%, 520px);
  min-height: clamp(140px, 18vh, 180px);
  padding: clamp(20px, 2.6vh, 28px) clamp(18px, 2.4vw, 24px) clamp(16px, 2vh, 22px);
}

.workbench__cta--console::before,
.workbench__cta--console::after {
  display: none; /* corners now in artwork */
}
```

### Note line — `.workbench__cta--console .workbench__cta-note`

```css
.workbench__cta--console .workbench__cta-note {
  color: var(--ink-muted, rgba(62, 58, 72, 0.72));
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.6);
}
```

### Button — `.workbench__cta--console .workbench__new-game`

```css
.workbench__cta--console .workbench__new-game {
  background:
    url("../images/workbench/console-start-btn-v2.png?v=2") center / 100% 100% no-repeat;
  border: none;
  clip-path: none; /* shape baked into PNG */
  box-shadow: 0 0 24px rgba(255, 183, 197, 0.35);
  width: min(100%, 300px);
  min-height: 56px;
}

.workbench__cta--console .new-game__zh {
  color: var(--ink, #3e3848);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.5);
}

.workbench__cta--console .new-game__en {
  color: rgba(62, 58, 72, 0.65);
  letter-spacing: 0.32em;
}
```

### Hover / breathe animation

Retarget glow from gold (`--vn-gold`) to pastel tokens:

- `--sakura` / `--sky-soft` for `box-shadow` keyframes in `console-cta-breathe`
- Keep `prefers-reduced-motion: reduce` override as-is

## HTML Structure (unchanged)

```html
<footer class="workbench__cta workbench__cta--console" aria-label="开始游戏">
  <p class="workbench__cta-note">AI 将为你构筑独一无二的分支剧情世界</p>
  <button type="button" id="create-btn" class="workbench__new-game …">
    …
  </button>
</footer>
```

No markup changes required for layered approach.

## Variant C Usage

`console-full-mockup-v2.png` is a **design reference** only:

- Side-by-side compare against live panel before/after CSS swap
- Optional single-layer fallback: `background-image` on `.workbench__cta--console` + hide button bg (not recommended — loses real button semantics)

## Responsive Notes

| Breakpoint | Action |
|------------|--------|
| `max-width: 640px` | Panel already `width: 100%`; ensure `background-size: 100% 100%` or `contain` if vertical crop appears |
| Short viewports | Outer art is 3:1; increase `min-height` if note + button feel cramped |

## QA Checklist (when wiring)

- [ ] Note text readable on parchment (contrast ≥ 4.5:1)
- [ ] Button focus ring visible on sakura chrome (`:focus-visible`)
- [ ] Loading state `.is-loading` still dims button + swaps label via `CreateFlow.js`
- [ ] No double borders from old `::before`/`::after` corner rules
- [ ] `?v=2` on CSS + image URLs after deploy

## Tokens Reference

From `frontend/css/tokens.css`: `--cream`, `--paper`, `--sky`, `--sky-soft`, `--sakura`, `--meadow`, `--ink`.

Replace remaining gold/dark console palette in `workbench-console-cta.css` with these when implementing.
