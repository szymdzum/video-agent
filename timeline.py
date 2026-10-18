"""EDL -> output timeline. Shared by render.py and lint.py so both see the same cuts.

EDL paths (music, src_dir) resolve relative to the EDL file.
audio: [{from_beat, to_beat}..., {from_beat, to_time}] -- music parts joined with XF crossfades.
shots: [{src, at, beats, speed?, tags?, note?}...] -- the last shot has beats=null and runs to the end.
"""
import json, os

XF = 0.25  # audio crossfade at each music jump
FPS = 60000 / 1001


def load(edl_path):
    edl_path = os.path.abspath(edl_path)
    edl = json.load(open(edl_path)); base = os.path.dirname(edl_path)
    edl['music'] = os.path.join(base, edl['music'])
    edl['src_dir'] = os.path.join(base, edl['src_dir'])
    edl['_base'] = base
    return edl


def build(edl):
    beats = json.load(open(edl['music'] + '.beats.json'))['beats']
    parts = edl['audio']
    spans = [(beats[a['from_beat']], beats[a['to_beat']] if 'to_beat' in a else a['to_time']) for a in parts]
    # beats on the output timeline: each part shifted to follow the previous one (minus crossfade)
    obeats, pos, part_starts = [], 0.0, []
    for k, (a, (t0, t1)) in enumerate(zip(parts, spans)):
        last = a.get('to_beat', len(beats) - 1)
        first = a['from_beat'] if k == 0 else a['from_beat'] + 1
        if k: part_starts.append(len(obeats) - 1)  # output beat index where part k begins
        obeats += [b - t0 + pos for b in beats[first:last + 1] if b <= t1]
        pos += (t1 - t0) - XF
    total = pos + XF
    cuts, bi, cut_beats = [0.0], 0, [0]
    for s in edl['shots'][:-1]:
        bi += s['beats']; cuts.append(obeats[bi]); cut_beats.append(bi)
    cuts.append(total)
    frames = [round(t * FPS) for t in cuts]
    shots = []
    for k, s in enumerate(edl['shots']):
        dur = (frames[k + 1] - frames[k]) / FPS
        sp = s.get('speed', 1)
        shots.append({**s, 'k': k, 'out': (cuts[k], cuts[k + 1]), 'frames': frames[k + 1] - frames[k],
                      'src_range': (s['at'], s['at'] + dur * sp), 'dur': dur})
    return {'spans': spans, 'obeats': obeats, 'total': total, 'cuts': cuts, 'cut_beats': cut_beats,
            'part_start_beats': part_starts, 'shots': shots}
