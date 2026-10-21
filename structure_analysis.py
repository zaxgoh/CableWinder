from analyze_mesh import m,bodies,OUT
import numpy as np
import trimesh
import json
from scipy.optimize import least_squares
np.random.seed(42)
for i,b in enumerate(bodies):
    pts=b.sample(1500)
    for ax in range(3):
        q=pts.copy();q[:,ax]=2*b.bounds[:,ax].mean()-q[:,ax]
        d=trimesh.proximity.closest_point(b,q)[1]
        print('sym',i,'XYZ'[ax],np.max(d),np.mean(d),flush=True)
    b.export(OUT/f'reference_body_{i}.stl')
    print('z levels and radius range',i,flush=True)
    center=b.bounds.mean(axis=0)[:2]
    for z in [0.001,.1,.2,.3,.6,1,1.3,2.6,3.3,4,6,8.3,10,13.3,14,15.3,16,16.4,16.599]:
        s=b.section([0,0,1],[0,0,z])
        if s is None:continue
        curves=s.discrete
        print(z,[(len(p),np.min(np.linalg.norm(p[:,:2]-center,axis=1)).round(4),np.max(np.linalg.norm(p[:,:2]-center,axis=1)).round(4)) for p in curves],flush=True)
    np.savez(OUT/f'body_{i}.npz',vertices=b.vertices,faces=b.faces)
