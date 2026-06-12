# Scene PNG Generation Rules (2711)

**Mandatory for all agents generating `frontend/images/scenes/*.png`.**

## Pure background only

Scene images must be **PURE BACKGROUND ART** — painted environment/scenery only.

### FORBIDDEN in scene PNGs

- Dialogue boxes, text boxes, speech bubbles
- Minimap, HUD, menu buttons, UI panels
- Quest tracker, status bars, resource counters
- On-screen Chinese/English **UI** text overlays (game labels, choice buttons)
- Game interface mockups / “VN screenshot” compositions
- Protagonist close-ups (distant anonymous crowds OK)

### Required style

- Makoto Shinkai 2D anime watercolor background art
- Chinese everyday / historical / xianxia context as appropriate
- Dappled light, god rays, pastel blue/pink/mint
- NOT photorealistic, NOT 3D, NOT CGI

### Negative prompt block (append to every GenerateImage)

```
NO game UI, NO dialogue box, NO HUD, NO minimap, NO menu buttons, NO text overlay, NO speech bubble, NO interface elements, pure background illustration only
```

### Config sources

- `scripts/art-style.json` — `scene_negative`, `ui_forbidden` (do **not** use `ui_prefix` for scenes)
- `scripts/scene-crowd-rules.json` — crowd density + `pure_background_rule`
- `scripts/scene-prompts-generic.json` — per-scene prompts with NO UI suffix
- `scripts/scene-expansion-shinkai.json` — Shinkai batch suffix

### After regenerating

Bump `VERSION` in `frontend/js/scene-images.js`.
