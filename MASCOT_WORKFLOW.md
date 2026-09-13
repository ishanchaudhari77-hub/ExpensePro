# Rupy Mascot Workflow (Beginner Friendly)

This project now supports a PNG-based mascot system with expression states.

## What is already done

- `login` and `register` pages use `Rupy` expression images.
- `dashboard` assistant also uses the same image pack.
- `expenses`, `reports`, `settings`, and `account` contextual Rupy panels also use the same image pack.
- State changes are automatic (`idle`, `thinking`, `warning`, `error`, `celebrate`) from existing JS logic.
- Floating bottom-right Rupy widget is available on auth pages plus login/register.
- Speech bubble reactions are event-driven (`login_success`, `high_spending`, `budget_planning`, `saving_money`, `idle`).
- Coin FX assets are available in `static/mascot/rupy/fx/` for burst and money-rain effects.
- Generated mascot assets are in `static/mascot/rupy/`.
- Rupy interaction copy is intentionally English-only.
- Runtime image paths currently point to the custom files in `mascot/` copied to `static/mascot/rupy/` (`png/jpeg` set).

## Current source image

- Source collage:  
  `References/different-expressions_ndGWLgHWQr-_fiBEhd5ITw_J-XBt_lJRGi9DelUqe4epw_cover.jpeg`

The source is a 2x2 expression grid and is mapped as:

- top-left -> `thinking`
- top-right -> `error`
- bottom-left -> `warning`
- bottom-right -> `celebrate` (also reused as `idle`)

Additional derived variants:

- `confused` (generated from `warning`)
- `proud` (generated from `celebrate`)

## Rebuild mascot pack (when you add new expression sheet)

Run from project root:

```bash
python tools/build_mascot_pack.py
```

Optional custom input/output:

```bash
python tools/build_mascot_pack.py --source "References/your-sheet.jpeg" --output "static/mascot/rupy"
```

## Generated files

- `static/mascot/rupy/rupy_idle.webp`
- `static/mascot/rupy/rupy_thinking.webp`
- `static/mascot/rupy/rupy_warning.webp`
- `static/mascot/rupy/rupy_error.webp`
- `static/mascot/rupy/rupy_celebrate.webp`
- `static/mascot/rupy/rupy_confused.webp`
- `static/mascot/rupy/rupy_proud.webp`
- `static/mascot/rupy/manifest.json`

## Floating controller

- Runtime controller: `static/mascot-controller.js`
- Templates that include floating widget:
  - `templates/base.html`
  - `templates/login.html`
  - `templates/register.html`
- Core styles:
  - `static/style.css` (`FLOATING RUPY WIDGET` section)
- Emit custom reactions from anywhere:

```js
window.RupyMascot.emit("high_spending", { message: "Bro... budget crossed." });
window.RupyMascot.emit("saving_money", { message: "Nice! Budget under control." });
```

## FX asset generation

Run:

```bash
python tools/generate_coin_fx_assets.py
```

## Where integration is wired

- Login page: `templates/login.html`
- Register page: `templates/register.html`
- Dashboard assistant: `templates/dashboard.html`
- Mascot logic: `static/script.js`
- Mascot styles: `static/style.css`
- Heavy pipeline guide: `MASCOT_HEAVY_PIPELINE.md`
