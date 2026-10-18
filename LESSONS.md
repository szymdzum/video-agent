# Lessons — technical gotchas

## Measuring footage
- **What he calls "szarpie" is slow wobble (0.5–2 Hz tilt/roll/pan corrections), not high-frequency jitter.** On gimbal footage HF jitter is at noise level.
  Found on za_lodka 5–26 s: tilt flips ±3–4 %/s every second. That's why `motion.py` measures band-passed (0.25 s − 2 s) wobble.
- Things that did **not** detect it: phase-correlation translation (v1 of motion.py), HF residual RMS, shotpilot `scan` (kept 98%)
  and shotpilot `jitter` (called everything "jitter", worst on the stretches he liked).
- Wobble thresholds (1 / 2 %/s) rest on ONE data point. Recalibrate whenever he flags or accepts a stretch, and write it down here.
- What also feels jerky: **cutting mid-pan/orbit** into another shot, and a pan that stops abruptly (DJI_0994 at 18–20 s).

## Music
- librosa often reports **double tempo** (136 for a ~68 BPM feel). The beat grid is still usable; pick cuts in multiples of 4/8/16 beats.
- Find section boundaries with `analyze.py` (energy per 8 s + agglomerative segments). Then look at 1 s RMS around a drop to place it exactly. Drops ramp over ~2 s.
- Keep audio part boundaries on multiples of 4 beats from each other, or the bar phase flips.

## Rendering
- `render.py` cuts hard on beats and joins audio parts with 0.25 s crossfades. Output timeline beats = parts concatenated minus crossfades.
- Temp segments go to local disk. On the exFAT external drive, macOS `._*` files break `rmtree`.
- Never pipe a long render through `| head`. SIGPIPE kills it. Use `| tail -1`.
- Preview 1080p `veryfast` ≈ 1–2 min for 2 min of 4K source; final `--4k` uses `-preset medium`.

## Scripts / shell
- `python -I` drops the script's directory from sys.path. Modules that import `timeline` insert it themselves.
- zsh: `for a b in 0 6 6 12; do …` iterates pairs. `set -- $r` does NOT word-split. Env vars don't persist between Bash tool calls, so re-export them.
- `echo =====` in zsh fails (`=cmd` expansion). Use `echo '---'`.

## Environment
- Venv: `~/Developer/video-agent/.venv` (uv, Python 3.12). uv needs `--system-certs` on this machine (TLS-intercepting proxy).
- This ffmpeg has **no drawtext** (no freetype) and **no vidstab**. It does have eq/curves/colorbalance/vibrance/lut3d/cas/xfade/deshake.
- The external disk (`/Volumes/External`, exFAT) once got a dirty flag and wouldn't mount. Fix: `sudo fsck_exfat -y /dev/rdiskNs1` (the user runs it, needs a password).
