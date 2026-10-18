# video-agent

Tools and working notes for editing wordless footage (drone, travel) into short films cut to music,
with a coding agent (Claude Code) as the editor and a human giving notes.

The agent **watches** footage as frame grids and **measures** it (camera motion, wobble, pace). It **analyzes**
the music (beats, sections, drop), writes a beat-locked JSON EDL, **lints** it, renders previews with ffmpeg,
and runs a review gate before the human sees anything. Every session's feedback is distilled into
`TASTE.md`, so the next edit starts closer to the human's taste.

## Files

| | |
|---|---|
| `TASTE.md` | One person's editing preferences, learned from feedback. Overrides the rules. |
| `RULES.md` | Craft rules: shot-rating rubric, pace, story and acts, cutting, review gate, grading, music. |
| `LESSONS.md` | Technical gotchas found along the way. |
| `motion.py` | Affine camera tracker → pace (% frame width/s) and band-passed **wobble** map, stable ranges. |
| `analyze.py` | Music: tempo, key, energy curve, sections, beat grid (librosa). |
| `timeline.py` | EDL → output timeline (beat-counted shots, music parts joined with crossfades). |
| `lint.py` | EDL checks: wobble, mid-pan cuts, jump cuts, reused footage, music jumps mid-shot, structure tags. |
| `render.py` | ffmpeg render: hard cuts on beats, optional speed, one grade, −14 LUFS. |
| `qa_cuts.py` / `qa_audio.py` | Review sheets: frames around every cut, waveform+spectrogram around music joins. |
| `ratings.py` | Calibrating the agent's shot ratings against the human's stars. |
| `sheets.sh` | Contact sheets. |

The agent workflow itself is an [Agent Skill](https://agentskills.io) (`video-agent/SKILL.md`), kept in the author's dotfiles.

## Setup

```sh
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python librosa soundfile opencv-python-headless
brew install ffmpeg
```

## Credits

- Camera tracker and lint ideas adapted from [shotpilot](https://github.com/tskupinski/shotpilot) (MIT, © 2026 Tomasz Skupiński).
- Rating rubric and calibration loop inspired by [ride-recap](https://github.com/ianmacomber/ride-recap) (MIT, © 2026 Ian Macomber).
- Screenwriter / Editor / Reviewer split inspired by [CutClaw](https://github.com/GVCLab/CutClaw) (idea only, no code).
- Transcript-free take on the idea behind [video-use](https://github.com/browser-use/video-use).
