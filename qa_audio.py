"""Audio QA for a render: we can't hear, so look at it.
Usage: qa_audio.py out.mp4 sheet.png    (reads out.mp4.cuts.json from render.py)
  - integrated loudness / true peak (ebur128): target -14 LUFS, <= -1 dBTP
  - per music join: waveform + spectrogram of +-2 s, stacked; the join is at the centre line.
    Look for: a gap or spike at the centre, an abrupt change in spectral texture (a different section
    slammed in), a beat that visibly stutters (onset spacing changes across the centre).
"""
import json, subprocess, sys, tempfile, re, os

video, sheet = sys.argv[1], sys.argv[2]
joins = json.load(open(video + '.cuts.json')).get('audio_joins', [])
r = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', video, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
summary = r[r.rfind('Summary:'):]
i = re.search(r'I:\s+(-?[\d.]+) LUFS', summary); tp = re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary)
print(f"loudness {i.group(1) if i else '?'} LUFS (target -14), true peak {tp.group(1) if tp else '?'} dBTP (<= -1)")
if not joins: print('no music joins'); sys.exit()
tmp = tempfile.mkdtemp(); parts = []
for k, t in enumerate(joins):
    a = max(0, t - 2)
    p = f'{tmp}/{k}.png'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-t', '4', '-i', video, '-filter_complex',
                    '[0:a]asplit[w][s];[w]showwavespic=s=800x120:split_channels=0:colors=white[wv];'
                    '[s]showspectrumpic=s=800x200:legend=0:scale=log[sp];[wv][sp]vstack,'
                    'drawbox=x=399:y=0:w=2:h=ih:color=red@0.8:t=fill', '-frames:v', '1', p], check=True)
    parts.append(p); print(f"join {k + 1} at {t:.2f} s")
inputs = sum((['-i', p] for p in parts), [])
subprocess.run(['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex',
                ''.join(f'[{k}]' for k in range(len(parts))) + f'vstack=inputs={len(parts)}' if len(parts) > 1 else 'null',
                '-frames:v', '1', sheet], check=True)
print('->', sheet)
