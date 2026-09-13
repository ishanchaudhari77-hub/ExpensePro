# Rupy Heavy Pipeline (Rive / Lottie / Sprite)

This project already runs a PNG state system in production.
Use this heavy pipeline only when you want richer character motion quality.

## Target output contracts

Place outputs here:

- `static/mascot/rupy/lottie/`
- `static/mascot/rupy/rive/`
- `static/mascot/rupy/sprites/`

Keep these animation names consistent:

- `idle`
- `thinking`
- `warning`
- `error`
- `celebrate`
- `confused`
- `proud`

## Option A: Rive (best for interactive app states)

1. Build one rigged Rupy file with state machine transitions.
2. Export `.riv` file to `static/mascot/rupy/rive/rupy_state_machine.riv`.
3. Keep state input names exactly matching the list above.
4. Add click/input triggers from existing JS events (login, budget alerts, tips).

## Option B: Lottie (best for lightweight polished loops)

1. Create short loops in After Effects.
2. Export JSON with Bodymovin.
3. Save each file as:
   - `static/mascot/rupy/lottie/rupy_idle.json`
   - `static/mascot/rupy/lottie/rupy_thinking.json`
   - `static/mascot/rupy/lottie/rupy_warning.json`
   - `static/mascot/rupy/lottie/rupy_error.json`
   - `static/mascot/rupy/lottie/rupy_celebrate.json`

## Option C: Sprite/WebM (best fallback)

1. Export short transparent loops.
2. Keep duration under 1.2s for state transitions.
3. Use WebM for quality/size balance, then fallback to PNG state if unavailable.

## Integration rule

- Keep PNG state system as fallback.
- Only switch to heavy animations when file exists and runtime is supported.
- Preserve `prefers-reduced-motion` behavior.
