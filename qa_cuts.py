"""Before/after frames around every cut of a render, tiled into one image for review.
Usage: qa_cuts.py out.mp4 sheet.jpg  (reads out.mp4.cuts.json from render.py)
Read the sheet in pairs: (before, after) per cut, left to right, top to bottom.
Look for: same composition on both sides (jump cut), mid-pan cuts, direction flips."""
import json, subprocess, sys, os, tempfile
video, sheet = sys.argv[1], sys.argv[2]
cuts = json.load(open(video + '.cuts.json'))['cuts']
tmp = tempfile.mkdtemp()
i = 0
for t in cuts:
    for o in (-0.1, 0.1):
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t + o:.3f}', '-i', video, '-frames:v', '1',
                        '-vf', 'scale=320:-1', f'{tmp}/{i:03d}.jpg'], check=True); i += 1
cols = 8; rows = -(-i // cols)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-pattern_type', 'glob', '-i', f'{tmp}/*.jpg',
                '-vf', f'tile={cols}x{rows}:padding=3:color=white', '-frames:v', '1', sheet], check=True)
print(f'{len(cuts)} cuts -> {sheet}  (4 cuts per row)')
