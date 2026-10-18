"""EDL lint: mechanical checks before rendering / before showing him a cut. Non-blocking warnings.
Usage: lint.py edl.json [--motion <dir>]   (motion dir default: <edl dir>/motion, from motion.py)

Ideas and several thresholds adapted from shotpilot pipeline/lint.py, MIT (c) 2026 Tomasz Skupinski.
Criteria are described in RULES.md; thresholds live here. A warning can be accepted, but say why in notes.md.

Optional per-shot tags: {"shot": top-down|panorama|reveal|flyover|orbit|dolly-in|rise|chase|follow,
  "scene": free kebab-case, "role": hook|breather|transition|final, "zone": int (journey stage, should not decrease)}
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I drops the script dir
import timeline

MIN_SHOT_S, LONG_SHOT_S = 3.0, 25.0
WOBBLE_WARN, WOBBLE_BAD = 1.0, 2.0      # motion.py thresholds (%/s, provisional)
WOBBLE_SHARE = 0.3                      # warn if >30% of a shot's seconds wobble
FAST_PAN_AT_CUT = 8.0                   # |pan| %/s in the first/last second -> cutting mid-pan
SHOT_OVERUSE_SHARE, SHOT_OVERUSE_MIN = 0.4, 6
SCENE_OVERUSE = 3
MONOTONY_LEN, MONOTONY_RATIO = 4, 1.5
DYNAMIC, BREATH, BREATH_AFTER = 4.0, 2.5, 3


def clip_duration(path):
    import subprocess
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                                capture_output=True, text=True).stdout)


def main():
    args = sys.argv[1:]
    edl = timeline.load(args[0]); tl = timeline.build(edl)
    mdir = args[args.index('--motion') + 1] if '--motion' in args else os.path.join(edl['_base'], 'motion')
    shots, W = tl['shots'], []
    warn = lambda k, kind, msg: W.append((k, kind, msg))
    secs_cache, dur_cache = {}, {}

    def seconds(src):
        if src not in secs_cache:
            p = os.path.join(mdir, os.path.splitext(src)[0] + '.seconds.json')
            secs_cache[src] = json.load(open(p)) if os.path.exists(p) else None
        return secs_cache[src]

    paces = []
    for s in shots:
        k, (a, b) = s['k'], s['src_range']
        if s['src'] not in dur_cache: dur_cache[s['src']] = clip_duration(os.path.join(edl['src_dir'], s['src']))
        if b > dur_cache[s['src']] + 0.05:
            warn(k, 'out_of_clip', f"needs {a:.1f}-{b:.1f} s but {s['src']} ends at {dur_cache[s['src']]:.1f} s")
        if s['dur'] < MIN_SHOT_S: warn(k, 'too_short', f"{s['dur']:.1f} s")
        if s['dur'] > LONG_SHOT_S and (s.get('tags') or {}).get('role') != 'breather':
            warn(k, 'long_shot', f"{s['dur']:.1f} s with no role=breather; anything new entering the frame?")
        sec = seconds(s['src'])
        if sec is None:
            warn(k, 'no_motion_data', f"run motion.py on {s['src']}"); paces.append(None); continue
        used = [x for x in sec if a - 0.5 <= x['t'] < b - 0.5]
        if not used: paces.append(None); continue
        bad = [x['t'] for x in used if x['wobble'] >= WOBBLE_BAD]
        shaky = [x['t'] for x in used if x['wobble'] >= WOBBLE_WARN]
        if bad: warn(k, 'wobble', f"strong wobble at src {bad} s")
        elif len(shaky) > WOBBLE_SHARE * len(used): warn(k, 'wobble', f"{len(shaky)}/{len(used)} s wobbly (src {shaky[0]}-{shaky[-1]})")
        if abs(used[0]['pan']) > FAST_PAN_AT_CUT: warn(k, 'cut_mid_pan', f"starts during a {used[0]['pan']:+.0f} %/s pan")
        if abs(used[-1]['pan']) > FAST_PAN_AT_CUT: warn(k, 'cut_mid_pan', f"ends during a {used[-1]['pan']:+.0f} %/s pan")
        pace = sorted(x['pace'] for x in used)[len(used) // 2] * s.get('speed', 1)
        paces.append(pace)

    for s, t in zip(shots, shots[1:]):
        if s['src'] == t['src']:
            warn(t['k'], 'same_clip_adjacent', f"{s['src']} again right after shot {s['k']} -> jump cut unless continuous")
    for i, s in enumerate(shots):
        for t in shots[i + 1:]:
            if s['src'] == t['src'] and s['src_range'][0] < t['src_range'][1] and t['src_range'][0] < s['src_range'][1]:
                warn(t['k'], 'reused_footage', f"overlaps shot {s['k']} in {s['src']}")

    # music jumps should land on cuts
    for bi in tl['part_start_beats']:
        if bi not in tl['cut_beats']:
            warn(-1, 'audio_jump_mid_shot', f"music jumps at {tl['obeats'][bi]:.2f} s inside a shot")

    tags = [s.get('tags') or {} for s in shots]
    if any(tags):
        for s, t, u in zip(shots, tags, tags[1:]):
            for dim in ('shot', 'scene'):
                if t.get(dim) and t.get(dim) == u.get(dim):
                    warn(s['k'] + 1, f'adjacent_same_{dim}', t[dim])
            if isinstance(t.get('zone'), int) and isinstance(u.get('zone'), int) and u['zone'] < t['zone']:
                warn(s['k'] + 1, 'journey_backwards', f"zone {t['zone']} -> {u['zone']}")
        if tags[0].get('role') != 'hook': warn(0, 'weak_hook', 'first shot has no role=hook')
        if tags[-1].get('role') != 'final': warn(len(shots) - 1, 'weak_closer', 'last shot has no role=final')
        from collections import Counter
        tagged = [t for t in tags if t.get('shot')]
        if len(tagged) >= SHOT_OVERUSE_MIN:
            for v, c in Counter(t['shot'] for t in tagged).items():
                if c / len(tagged) > SHOT_OVERUSE_SHARE: warn(-1, 'shot_overuse', f"{v}: {c}/{len(tagged)}")
        for v, c in Counter(t['scene'] for t in tags if t.get('scene')).items():
            if c >= SCENE_OVERUSE: warn(-1, 'scene_overuse', f"{v} x{c}")

    i = 0  # pace monotony: >=4 consecutive shots within a 1.5x band
    while i < len(paces):
        j, lo, hi = i, paces[i], paces[i]
        while lo and j + 1 < len(paces) and paces[j + 1] and max(hi, paces[j + 1]) / min(lo, paces[j + 1]) < MONOTONY_RATIO:
            j += 1; lo, hi = min(lo, paces[j]), max(hi, paces[j])
        if j - i + 1 >= MONOTONY_LEN: warn(i, 'tempo_monotony', f"shots {i}-{j} all {lo:.1f}-{hi:.1f} %/s"); i = j + 1
        else: i += 1
    run = 0  # breather after a run of dynamic shots
    for k, p in enumerate(paces):
        if p is not None and p >= DYNAMIC: run += 1; continue
        if run >= BREATH_AFTER and not (p is not None and p < BREATH) and tags[k].get('role') != 'breather':
            warn(k, 'missing_breath', f"{run} dynamic shots with no breather after")
        run = 0
    if edl.get('target_s') and abs(tl['total'] - edl['target_s']) > max(10, 0.1 * edl['target_s']):
        warn(-1, 'duration_off_target', f"{tl['total']:.0f} s vs target {edl['target_s']} s")

    print(f"{len(shots)} shots, {tl['total']:.1f} s, music parts {len(tl['spans'])}")
    for s, p in zip(shots, paces):
        print(f"  {s['k']:2d} {s['out'][0]:6.1f}-{s['out'][1]:6.1f}  {s['dur']:5.1f}s  {s['src']}@{s['src_range'][0]:.1f}-{s['src_range'][1]:.1f}"
              f"  pace {p if p is not None else '?'}  {s.get('note', '')}")
    print(f"\n{len(W)} warning(s)" if W else '\nclean')
    for k, kind, msg in sorted(W, key=lambda w: w[0]):
        print(f"  [{'-' if k < 0 else k}] {kind}: {msg}")


if __name__ == '__main__':
    main()
