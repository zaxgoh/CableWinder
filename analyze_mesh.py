from pathlib import Path
import json
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).parent
SRC = Path(r'D:\OneDrive\Documents\3D_Models\Containers+Covers\Cable winder case\FromInternet\earbud_winder_100pct.stl')
m = trimesh.load(SRC, force='mesh')
bodies = sorted(m.split(only_watertight=False), key=lambda b: -b.volume)
for i,b in enumerate(bodies):
    print('BODY',i,dict(faces=len(b.faces),volume=b.volume,euler=b.euler_number,bounds=b.bounds.tolist(),center=b.center_mass.tolist(),watertight=b.is_watertight),flush=True)
    n=b.face_normals
    print('axis aligned share',b.area_faces[np.abs(n).max(axis=1)>.999].sum()/b.area)
    zs=np.round(b.triangles_center[:,2],3)
    planar=np.abs(n[:,2])>.99999
    levels={float(z):float(b.area_faces[planar & (zs==z)].sum()) for z in np.unique(zs[planar])}
    print('horizontal areas',sorted(levels.items(),key=lambda p:-p[1])[:25],flush=True)
fig,axs=plt.subplots(3,3,figsize=(15,15))
for i,b in enumerate(bodies):
    for j,(a,c) in enumerate([(0,1),(0,2),(1,2)]):
        ax=axs[i,j]
        ax.triplot(b.vertices[:,a],b.vertices[:,c],b.faces,lw=.08)
        ax.set_aspect('equal');ax.set_title(f'Body {i} {"XYZ"[a]}{"XYZ"[c]}')
fig.tight_layout();fig.savefig(OUT/'triage.png',dpi=160)
fig,axs=plt.subplots(3,6,figsize=(20,11))
section_data={}
for i,b in enumerate(bodies):
    for j,z in enumerate([.5,2,4,8.3,13,16.1]):
        s=b.section([0,0,1],[0,0,z]);ax=axs[i,j]
        if s is not None:
            for p in s.discrete: ax.plot(p[:,0],p[:,1],lw=.7)
            section_data[f'{i}:{z}']=[p.tolist() for p in s.discrete]
        ax.set_aspect('equal');ax.set_title(f'{i} z={z}')
fig.tight_layout();fig.savefig(OUT/'sections.png',dpi=160)
(OUT/'sections.json').write_text(json.dumps(section_data))
