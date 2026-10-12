from PIL import Image
import numpy as np
for base in ['eta-en-1440','eta-de-1440']:
    L=np.asarray(Image.open(f'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16/.scratch/t16-closure/pairs-r4/{base}-live.png').convert('RGB'), dtype=np.int16)
    T=np.asarray(Image.open(f'/Users/chesterjohn/Documents/de-linker-worktrees/de-linker-t16/.scratch/t16-closure/pairs-r4/{base}-t16.png').convert('RGB'), dtype=np.int16)
    h=min(L.shape[0],T.shape[0]); w=min(L.shape[1],T.shape[1])
    print(base, f"full {100*(np.abs(L[:h,:w]-T[:h,:w]).max(axis=2)>0).mean():.2f}%")
