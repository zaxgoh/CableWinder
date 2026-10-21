"""Measure feature-corresponding outer/inner chains for the thin C-shaped ring."""
from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString

OUT=Path(__file__).parent
data=json.loads((OUT/'measured_profiles.json').read_text())
mesh=trimesh.load(OUT/'reference_body_1.stl')
center=np.array(data['center'])
CHAIN_SAMPLES=250
EPS=1e-4
result=[]
for rec in data['ring_open']:
    z=rec['z']
    p=mesh.section(plane_normal=[0,0,1],plane_origin=[0,0,min(z,16.6-EPS)]).discrete[0][:,:2]
    if not Polygon(p).exterior.is_ccw:p=p[::-1]
    line=LineString(p)
    length=line.length
    r=np.linalg.norm(p-center,axis=1)
    threshold=(np.percentile(r,20)+np.percentile(r,75))/2
    steps=np.linalg.norm(np.diff(p,axis=0),axis=1)
    stations=np.r_[0,np.cumsum(steps)]
    crossings=[]
    for j in range(len(p)-1):
        a,b=r[j]-threshold,r[j+1]-threshold
        if a*b<0:crossings.append(stations[j]+steps[j]*(-a)/(b-a))
    runs=[]
    for j,a in enumerate(crossings):
        b=crossings[(j+1)%len(crossings)]
        span=(b-a)%length
        q=np.array(line.interpolate((a+span/2)%length).coords[0])
        runs.append((a,b,span,np.linalg.norm(q-center)>threshold))
    outer=max((q for q in runs if q[3]),key=lambda q:q[2])
    inner=max((q for q in runs if not q[3]),key=lambda q:q[2])
    start=(inner[1]+((outer[0]-inner[1])%length)/2)%length
    turn=(outer[1]+((inner[0]-outer[1])%length)/2)%length
    outer_length=(turn-start)%length
    inner_length=length-outer_length
    samples=np.r_[start+np.arange(CHAIN_SAMPLES)/CHAIN_SAMPLES*outer_length,
                  turn+np.arange(CHAIN_SAMPLES)/CHAIN_SAMPLES*inner_length]%length
    pts=[list(line.interpolate(float(t)).coords[0]) for t in samples]
    result.append(dict(z=z,points=np.round(pts,5).tolist()))
    print(z,'crossings',len(crossings),'chains',round(outer_length,2),round(inner_length,2),flush=True)
data['ring_open']=result
(OUT/'measured_profiles.json').write_text(json.dumps(data))
