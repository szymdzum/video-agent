# Rules — editing craft

General craft rules. **TASTE.md** holds what *he* likes and overrides this file. **LESSONS.md** holds technical gotchas.
Sources: shotpilot `docs/decision-rules.md` (MIT, Tomasz Skupiński), ride-recap's scoring rubric (MIT, Ian Macomber),
CutClaw's Screenwriter/Editor/Reviewer split, Murch's rule of six, and the 2026-10-18 research brief.
Change rules here, not in SKILL.md. Thresholds that code enforces live in `lint.py` / `motion.py`.

## 1. Rating shots (selection)

Rate **candidate stretches** (src + from–to), not whole clips. Look at a 1 s frame grid of the stretch, not just the 2 s contact sheet.
Five **independent** axes, 1–10. **Use the full range.** Most footage is 3–5. A trip usually has a handful of 7+ stretches.
Don't be diplomatic: a 2 is a useful answer.

| axis | 10 | 7 | 4 | 1 |
|---|---|---|---|---|
| **light** | golden hour, raking side light, storm light, fog with sun | clean directional light, shape in clouds | flat midday or overcast, readable | blown white sky, muddy |
| **composition** | strong leading line (wake, coast, road), layered depth, subject placed with intent | solid framing, depth visible | point-and-shoot horizon in the middle | tilted, dead foreground, subject cut off |
| **motion** | smooth move that *reveals* something (rise over a ridge, push through a gate) | smooth, purposeful forward move | slow drift, hover | wobble, mid-correction, takeoff/landing |
| **scenery** | unmistakable place (karst bay, ridge line, landmark) | pleasant place with character | generic land/sea | ground, grass, blocked view |
| **subject** | clear moving subject in a story beat (boat leaving port, wake curving past a rock) | identifiable subject | something small happening | nothing: transit footage |

**Openness gate:** scenery needs sky, horizon or open landscape. A shot looking straight down at trees or ground caps scenery at 3.
**Hard gates:** wobble ≥ 2 anywhere in the stretch (motion.py) → motion ≤ 3, re-check whether a shorter range avoids it.
A camera turned back toward where the story came from (e.g. land while heading out to sea) → subject ≤ 3 for that story.

**Stars** (what he sees): ★5 ≈ two axes ≥ 9 and none < 6 · ★4 ≈ mean ≥ 7 · ★3 ≈ mean 5–7 · ★2 / ★1 below. Use ≥ ★3.
**Twins:** of a family of similar stretches keep only the best. Note the rejects as "weaker twin of X".
**Notes carry a decision, not a description:** "best boat shot, use on the drop", not "boat on water".

### Calibration loop (from ride-recap)
Ratings live in `<project>/edit/ratings.json`. He gives stars to a sample of stretches (`ratings.py ask`), and `ratings.py compare`
shows where we disagree. Each disagreement of ≥ 2 stars becomes either a named rule in this rubric or a TASTE.md entry,
with the clip that caused it ("rule: … — from Tajland za_lodka 0-10"). Re-rate after changing the rubric.

## 2. Pace (from shotpilot, % of frame width per second, `motion.py`)
< 2 slow/contemplative · 3–8 dynamic · > 8 fast.
- Contrast between neighbours is a value. Don't even it out. After 2–3 dynamic shots comes a breather (slow, calm).
- Speed-ups (`speed` in EDL, setpts): at most ×2.5, round to 0.25. Use them for a dull approach before something happens.
  Use lower multipliers when boats, people or cars are in frame (they turn into a timelapse fast). Sometimes a shorter cut beats a speed-up.
- Dull stretch = ≥ 4 s at < 50% of the clip's median pace. Trim it unless a subject is entering the frame.

## 3. Story and order (Screenwriter)
- **Idea first, shots second.** Write the guiding idea and 3–5 acts before choosing shots (e.g. land → port → gate → open sea → exit).
  One motif recurs 3–4× and changes the last time (Tajland: the boat's wake, which ends in an empty bay).
- **Map acts onto music sections** (`analyze.py`): intro = establishing + slow approach, breakdown = one held shot,
  drop = the best shot, starting exactly on the drop, outro = pull back / rise / empty frame.
- **Tags per shot** in the EDL (`lint.py` checks them): `shot` ∈ top-down, panorama, reveal, flyover, orbit, dolly-in, rise, chase, follow ·
  `scene` free · `role` ∈ hook, breather, transition, final · `zone` = journey stage number (must not decrease).
- **Hook:** the first 5 s decide. Use a clear subject and natural pace. Don't open with the widest dead panorama.
- **Closer:** wide and calm, a rise-away or empty frame. A feeling of an ending, not just music stopping.
- No two adjacent shots with the same `shot` type or `scene`, unless it is a deliberate wide→detail pair.
- One shot type ≤ 40% of the film. The same scene ≤ 2×. Spread the most common shot type first, then place the rest around it.
- **Group into acts, order the acts, and only then order shots inside each act.** Don't sort 20 shots as one list.

## 4. Cutting (Editor)
- **Cut on phrase boundaries** (4/8/16 beats), not every beat. Vary shot length: holds of 7–25 s, connectors of 3–4 s.
- **Cut at the start or end of a move, never mid-pan or mid-orbit** (`lint cut_mid_pan`). Start a clip after the drone settles.
- **Carry motion across the cut:** forward push → forward push, same direction of travel. To reverse direction, put a neutral shot in between.
- **Eye trace:** keep the subject in a similar screen area across the cut. Graphic matches (curve → curve) are the strongest cuts.
- Every music jump lands on a cut (`lint audio_jump_mid_shot`).
- You don't have to use all the footage. A shorter film with only strong shots beats coverage.

## 5. Review gate (Reviewer, before he sees anything)
After each preview render, run **`lint.py`**, **`qa_cuts.py`** and **`qa_audio.py`**, then a **fresh reviewer subagent**
(it hasn't seen your reasoning) with RULES.md + TASTE.md + lint output + the QA sheets + the EDL. It returns pass/fail per shot and per cut.
Fix the failures (max 3 rounds), then show him. Tell him which warnings you accepted, and why.

## 6. Look (grading, from shotpilot)
- Default is TASTE's grade. Correct outliers, not every clip: within an act keep mean luma within ±0.08 and colour cast within ±0.02 of the neighbours.
- Saturation ≤ ~1.15, contrast ≤ ~1.1. Never "fix" log footage with eq: apply a log→709 LUT first.
- Judge on a still grid, then ask him after he has watched it in motion. Stills undersell how a grade pumps.

## 7. Music
- He generates it in Suno from our prompt. Write the prompt from the story: acts → `[Section: …]` lines, plus pace (slow footage → slow build).
- We can't hear. Use `analyze.py` energy curve + `qa_audio.py` at the joins. Leave the final judgment of the sound to him.
- Loudness: −14 LUFS integrated, −1 dBTP (render.py does this).
