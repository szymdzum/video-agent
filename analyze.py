import sys, json, librosa, numpy as np
f = sys.argv[1]
y, sr = librosa.load(f, sr=22050)
d = len(y) / sr
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units='time')
names = 'C C# D D# E F F# G G# A A# B'.split()
maj = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
mi = np.array([6.33,2.68,3.52,5.38,2.6,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(1)
sc = [(np.corrcoef(np.roll(maj,i),chroma)[0,1], names[i]+' major') for i in range(12)] + \
     [(np.corrcoef(np.roll(mi,i),chroma)[0,1], names[i]+' minor') for i in range(12)]
rms = librosa.feature.rms(y=y)[0]; cen = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
tt = librosa.times_like(rms, sr=sr); on = librosa.onset.onset_strength(y=y, sr=sr)
print(f'duration {d:.1f}s  tempo {float(np.atleast_1d(tempo)[0]):.1f}  beats {len(beats)}  key {max(sc)[1]}')
print('t     energy                         bright  perc')
for s in np.arange(0, d, 8):
    m = (tt >= s) & (tt < s + 8)
    print(f'{int(s)//60}:{int(s)%60:02d}', ('#'*int(rms[m].mean()*120)).ljust(30), f'{cen[m].mean():6.0f}', f'{on[m].mean():4.2f}')
S = librosa.feature.mfcc(y=y, sr=sr)
bt = librosa.frames_to_time(librosa.segment.agglomerative(S, 8), sr=sr)
print('sections at', [f'{int(x)//60}:{int(x)%60:02d}' for x in bt])
h, p = librosa.effects.hpss(y)
print('harmonic/percussive ratio', round(float(np.sum(h**2)/np.sum(p**2)), 2))
json.dump({'duration': d, 'beats': [round(float(b),3) for b in beats]}, open(f + '.beats.json', 'w'))
