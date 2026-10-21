"""Mesh measurement only: design profiles, not triangulated CAD geometry."""
from pathlib import Path
import json
import numpy as np
import trimesh
from shapely.geometry import Polygon, LineString

OUT=Path(__file__).parent
EPS=1e-4
PROFILE_STEP=.5
CURVE_SPACING=.5
BODY_CENTER=(-144.682,22.603)

def contours(body,z):
    sec=body.section(plane_normal=[0,0,1],plane_origin=[0,0,np.clip(z,EPS,16.6-EPS)])
    paths=sec.discrete
    return sorted(paths,key=lambda p: -Polygon(p[:,:2]).area)

def profile(body,z,which=0,spacing=CURVE_SPACING):
    p=contours(body,z)[which][:,:2]
    # CCW and start at northernmost ray: stable registration between sections.
    poly=Polygon(p)
    if not poly.exterior.is_ccw:p=p[::-1]
    idx=np.argmax(p[:,1]);p=np.concatenate([p[idx:-1],p[:idx],p[idx:idx+1]])
    line=LineString(p)
    return line

def profiles(body,zs,n):
    result=[]
    for z in zs:
        line=profile(body,z)
        pts=np.array([line.interpolate(t,normalized=True).coords[0] for t in np.arange(n)/n])
        result.append({'z':round(float(z),5),'points':np.round(pts,5).tolist()})
    return result

core=trimesh.load(OUT/'reference_body_0.stl')
ring=trimesh.load(OUT/'reference_body_1.stl')
# Separate topology changes as additive feature groups. Closed skirts below the
# openings are modeled independently, and their holes are subtracted afterwards.
core_floor_z=[0,.099,.101,.2,.3,.5999]
core_hook_z=np.unique(np.r_[.6001,np.arange(1,16.6,.5),16.4,16.6])
ring_floor_z=[0,.099,.101,.3,.6,1,1.3,1.6,2,2.5999]
ring_open_z=np.unique(np.r_[2.6001,np.arange(3,16.6,.5),16.4,16.6])
data={'center':BODY_CENTER,'height':16.6,
      'core_floor':profiles(core,core_floor_z,256),
      'core_hook':profiles(core,core_hook_z,400),
      'ring_floor_outer':profiles(ring,ring_floor_z,256),
      'ring_open':profiles(ring,ring_open_z,500)}
# Ring floor bore is a rotational surface; measure it from inner loops.
data['ring_floor_inner']=[]
for z in ring_floor_z:
    q=contours(ring,z)[1][:,:2]
    r=np.median(np.linalg.norm(q-np.array(BODY_CENTER),axis=1))
    data['ring_floor_inner'].append([z,float(r)])
# Main bore is concentric with the separate pin. Round dimensions used in model.
data['pin_center']=[-132.756,34.177]
(OUT/'measured_profiles.json').write_text(json.dumps(data))
print('profiles saved',[(k,len(v)) for k,v in data.items() if isinstance(v,list)])
