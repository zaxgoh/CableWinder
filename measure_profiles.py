from pathlib import Path
import numpy as np
import trimesh
from scipy.optimize import least_squares
OUT=Path(__file__).parent
bodies=[trimesh.load(OUT/f'reference_body_{i}.stl') for i in range(3)]
center=np.array([-144.682,22.603])
for i in [0,1]:
 b=bodies[i]
 print('BODY',i,flush=True)
 for z in [0.0001,.1,.2,.3,.6,1,1.3,1.6,2,2.6,3.3,3.6,4,5,6,7,8.3,13,15,16,16.5999]:
  s=b.section([0,0,1],[0,0,z])
  v=s.vertices
  # lower arc, away from channel and latch; tabulate radial extremes
  p=v[(v[:,1]<center[1]-18)&(np.abs(v[:,0]-center[0])<4)]
  r=np.linalg.norm(p[:,:2]-center,axis=1)
  print(z, np.percentile(r,[0,50,100]).round(5).tolist(),flush=True)
