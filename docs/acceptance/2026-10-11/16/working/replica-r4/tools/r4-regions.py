from PIL import Image
import numpy as np
P='/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16/.scratch/t16-closure/pairs-r4'
def region(base, x0,y0,x1,y1, search=180, label=''):
    L=np.asarray(Image.open(f'{P}/{base}-live.png').convert('RGB'), dtype=np.int16)
    T=np.asarray(Image.open(f'{P}/{base}-t16.png').convert('RGB'), dtype=np.int16)
    lr=L[y0:y1, x0:x1]
    best=None
    for dy in range(-search, search+1):
        for dx in (-2,-1,0,1,2):
            ty0, tx0 = y0+dy, x0+dx
            if ty0<0 or tx0<0: continue
            tr=T[ty0:ty0+(y1-y0), tx0:tx0+(x1-x0)]
            if tr.shape!=lr.shape: continue
            n=int((np.abs(lr-tr).max(axis=2)>0).sum())
            if best is None or n<best[0]: best=(n,dx,dy)
    total=(y1-y0)*(x1-x0)
    print(f"{base} {label:22s} {best[0]}/{total} ({100*best[0]/total:.2f}%) dx={best[1]} dy={best[2]}")
# distances taken from the live measurements (round 2/3)
region('pdp-en-1440', 40,1082,1400,1358, label='overview panel')
region('pdp-en-1440', 40,1390,1400,1490, label='benefits')
region('pdp-en-1440', 40,1543,708,1663, label='disclosures row')
region('pdp-en-1440', 986,352,1400,530, label='spec list hero')
region('pdp-en-1440', 707,1727,1400,2090, label='info deck')
region('pdp-en-1440', 40,2131,1440,2464, label='documents block')
region('pdp-en-1440', 40,2798,320,3030, label='pairing card 1')
region('pdp-en-1440', 40,2798,1440,3560, label='pairings section')
region('eta-en-1440', 40,2375,1440,3233, label='ETA documents block')
