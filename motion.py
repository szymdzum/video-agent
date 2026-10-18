"""Camera motion per clip: screen pace + wobble map.
Usage: motion.py <cache_dir> clip.mp4 [...]      (cache: <cache_dir>/<stem>.motion.csv, reused if newer than clip)
       motion.py <cache_dir> clip.mp4 --from A --to B   (per-second detail table)

Tracker (features -> LK optical flow -> partial affine: dx, dy, rotation, zoom per frame at 640 px)
adapted from shotpilot pipeline/motion.py, MIT (c) 2026 Tomasz Skupinski, github.com/tskupinski/shotpilot.

Metrics, all in % of frame width per second (rotation/zoom converted at the frame edge, like shotpilot pace.py):
  pace   = |pan,tilt| + |dolly| + |roll|, per-second median.   <2 slow/contemplative, 3-8 dynamic, >8 fast
  wobble = band-passed (0.25 s smooth minus 2 s trend) pan/tilt/roll RMS. This catches the slow 0.5-2 Hz
           bobbing that reads as "szarpie". High-frequency jitter is at noise level on gimbal footage.
Calibration so far (1 data point, Tajland 2026-10-18): za_lodka 0-4 s wobble <1, 5-26 s 1-3 (he flagged "shaky at
the start" of a 0-25 s shot; a 10-35 s version was "better"). Thresholds 1/2 are provisional -- recalibrate on his notes.
"""
import csv, subprocess, sys, json
from pathlib import Path
import numpy as np, cv2

W = 640
FEATURES = dict(maxCorners=400, qualityLevel=0.01, minDistance=12, blockSize=7)
LK = dict(winSize=(21, 21), maxLevel=3, criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
WOBBLE_WARN, WOBBLE_BAD = 1.0, 2.0


def probe(f):
    o = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                   'stream=width,height,r_frame_rate', '-of', 'json', str(f)],
                                  capture_output=True, text=True).stdout)['streams'][0]
    n, d = o['r_frame_rate'].split('/')
    return o['width'], o['height'], float(n) / float(d)


def track(f):
    w0, h0, fps = probe(f)
    h = max(2, round(h0 * W / w0 / 2) * 2)
    p = subprocess.Popen(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(f), '-map', '0:v:0', '-vf', f'scale={W}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], stdout=subprocess.PIPE, bufsize=W * h * 8)
    rows, prev, i = [], None, 0
    while True:
        buf = p.stdout.read(W * h)
        if len(buf) < W * h: break
        g = np.frombuffer(buf, np.uint8).reshape(h, W)
        dx = dy = da = ds = 0.0; ok = 0
        if prev is not None:
            pts = cv2.goodFeaturesToTrack(prev, **FEATURES)
            if pts is not None and len(pts) >= 30:
                nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, pts, None, **LK)
                good = st.ravel() == 1
                if good.sum() >= 30:
                    M, _ = cv2.estimateAffinePartial2D(pts[good], nxt[good], method=cv2.RANSAC, ransacReprojThreshold=3.0)
                    if M is not None:
                        dx, dy = M[0, 2], M[1, 2]; da = np.arctan2(M[1, 0], M[0, 0])
                        ds = np.hypot(M[0, 0], M[1, 0]) - 1; ok = 1
        rows.append((i, i / fps, dx, dy, da, ds, ok)); prev = g; i += 1
        if i % 600 == 0: print(f'  {Path(f).name}: {i} frames', file=sys.stderr)
    p.wait()
    return rows, fps


def load(cache_dir, f):
    c = Path(cache_dir) / (Path(f).stem + '.motion.csv')
    if c.exists() and c.stat().st_mtime > Path(f).stat().st_mtime:
        r = list(csv.reader(open(c)))[1:]
        fps = float(r[1][0]) / float(r[1][1]) if len(r) > 1 and float(r[1][1]) else 59.94
        rows = [tuple(float(x) for x in row[:7]) for row in r]
    else:
        rows, fps = track(f)
        c.parent.mkdir(parents=True, exist_ok=True)
        with open(c, 'w', newline='') as fh:
            wr = csv.writer(fh); wr.writerow(['frame', 't', 'dx', 'dy', 'da', 'ds', 'ok'])
            wr.writerows([(r[0], f'{r[1]:.4f}', f'{r[2]:.4f}', f'{r[3]:.4f}', f'{r[4]:.6f}', f'{r[5]:.6f}', r[6]) for r in rows])
    a = np.array(rows, float)
    return {'t': a[:, 1], 'dx': a[:, 2], 'dy': a[:, 3], 'da': a[:, 4], 'ds': a[:, 5]}, fps


def per_second(m, fps):
    pct = fps / W * 100; arm = W / 2
    pan, tilt, roll, dolly = m['dx'] * pct, m['dy'] * pct, m['da'] * arm * pct, m['ds'] * arm * pct

    def ma(v, sec):
        k = max(1, int(fps * sec)); return np.convolve(v, np.ones(k) / k, mode='same')
    band = {k: ma(v, 0.25) - ma(v, 2.0) for k, v in (('pan', pan), ('tilt', tilt), ('roll', roll))}
    out = []
    for s in range(int(m['t'][-1])):
        sl = (m['t'] >= s) & (m['t'] < s + 1)
        wob = {k: float(np.sqrt((v[sl] ** 2).mean())) for k, v in band.items()}
        out.append({'t': s,
                    'pace': round(float(np.median(np.hypot(pan[sl], tilt[sl]) + np.abs(dolly[sl]) + np.abs(roll[sl]))), 2),
                    'pan': round(float(pan[sl].mean()), 2), 'tilt': round(float(tilt[sl].mean()), 2),
                    'roll': round(float(roll[sl].mean()), 2), 'dolly': round(float(dolly[sl].mean()), 2),
                    'wobble': round(max(wob.values()), 2), 'wobble_axis': max(wob, key=wob.get)})
    return out


def stable_ranges(sec, min_len=4):
    out, start = [], None
    for s in sec + [None]:
        if s is not None and s['wobble'] < WOBBLE_WARN:
            start = s['t'] if start is None else start
        else:
            end = s['t'] if s else sec[-1]['t'] + 1
            if start is not None and end - start >= min_len: out.append((start, end))
            start = None
    return out


if __name__ == '__main__':
    args = sys.argv[1:]; cache = args.pop(0)
    rng = None
    if '--from' in args:
        i = args.index('--from'); rng = (float(args[i + 1]), float(args[args.index('--to') + 1]))
        args = [a for j, a in enumerate(args) if j not in (i, i + 1, args.index('--to'), args.index('--to') + 1)]
    for f in args:
        m, fps = load(cache, f); sec = per_second(m, fps)
        json.dump(sec, open(Path(cache) / (Path(f).stem + '.seconds.json'), 'w'))
        name = Path(f).name
        if rng:
            print(f'== {name} {rng[0]:g}-{rng[1]:g} s   (%/s)   s  pace  pan  tilt  roll  dolly  wobble')
            for s in sec:
                if rng[0] <= s['t'] < rng[1]:
                    flag = ' <<' if s['wobble'] >= WOBBLE_BAD else ' <' if s['wobble'] >= WOBBLE_WARN else ''
                    print(f"   {s['t']:4d} {s['pace']:5.1f} {s['pan']:5.1f} {s['tilt']:5.1f} {s['roll']:5.1f} {s['dolly']:5.1f}  {s['wobble']:4.1f} {s['wobble_axis']}{flag}")
            continue
        print(f'== {name} ({len(sec)} s)  median pace {np.median([s["pace"] for s in sec]):.1f} %/s')
        for k in range(0, len(sec), 60):
            c = sec[k:k + 60]
            print(f'{k:4d} wobble ' + ''.join('.' if s['wobble'] < WOBBLE_WARN else 'o' if s['wobble'] < WOBBLE_BAD else 'X' for s in c))
            print(f'     pace   ' + ''.join(' ' if s['pace'] < 2 else '-' if s['pace'] < 3 else '=' if s['pace'] <= 8 else '#' for s in c))
        print('     stable (wobble<1, >=4 s): ' + ', '.join(f'{a}-{b}' for a, b in stable_ranges(sec)))
