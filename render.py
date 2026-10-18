"""Render an EDL: beat-locked hard cuts, one grade, music parts with crossfades, loudness-normalized.
Usage: render.py edl.json out.mp4 [--4k]
Writes <out>.cuts.json (for qa_cuts.py / qa_audio.py). Timeline math lives in timeline.py."""
import json, subprocess, sys, os, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
import timeline

edl = timeline.load(sys.argv[1]); out = os.path.abspath(sys.argv[2])
uhd = '--4k' in sys.argv
tl = timeline.build(edl)

tmp = tempfile.mkdtemp(prefix='render_')  # local disk: faster, and exFAT ._ files break rmtree
scale = '3840:2160' if uhd else '1920:1080'
parts = []
for s in tl['shots']:
    p = os.path.join(tmp, f"{s['k']:02d}.mp4"); parts.append(p)
    speed = f"setpts=PTS/{s['speed']}," if s.get('speed', 1) != 1 else ''
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(s['at']), '-i', os.path.join(edl['src_dir'], s['src']),
                    '-map', '0:v:0', '-an', '-vf', f"{speed}scale={scale}:flags=lanczos,{edl['grade']}", '-r', '60000/1001',
                    '-frames:v', str(s['frames']), '-c:v', 'libx264', '-preset', 'medium' if uhd else 'veryfast', '-crf', '18',
                    '-pix_fmt', 'yuv420p', p], check=True)
    print(f"{s['k']:2d} {s['out'][0]:6.2f}-{s['out'][1]:6.2f}  {s['src']}@{s['at']}  {s.get('note','')}", flush=True)

lst = os.path.join(tmp, 'list.txt')
open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
fade_at = tl['total'] - 3
trims = ''.join(f"[1:a]atrim={t0}:{t1},asetpts=PTS-STARTPTS[p{k}];" for k, (t0, t1) in enumerate(tl['spans']))
chain, prev = '', 'p0'
for k in range(1, len(tl['spans'])):
    chain += f"[{prev}][p{k}]acrossfade=d={timeline.XF}[j{k}];"; prev = f'j{k}'
# -14 LUFS / -1 dBTP: streaming loudness target (shotpilot's mux default)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', edl['music'],
    '-filter_complex', trims + chain + f"[{prev}]afade=t=out:st={fade_at}:d=3,loudnorm=I=-14:TP=-1:LRA=11,aresample=48000[a]",
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-shortest', '-movflags', '+faststart', out], check=True)
shutil.rmtree(tmp, ignore_errors=True)
json.dump({'video': out, 'cuts': tl['cuts'][1:-1],
           'audio_joins': [tl['obeats'][i] for i in tl['part_start_beats']],
           'shots': edl['shots']}, open(out + '.cuts.json', 'w'), indent=1)
print('done', out, f"{tl['total']:.2f}s")
