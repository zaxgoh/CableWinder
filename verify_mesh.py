"""Deterministic bidirectional point-to-triangle comparison with vertex checks."""
from pathlib import Path
import json, hashlib
import numpy as np
import trimesh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).parent
SRC=Path(r'D:\OneDrive\Documents\3D_Models\Containers+Covers\Cable winder case\FromInternet\earbud_winder_100pct.stl')
SAMPLE_COUNT=50000
BATCH_SIZE=1000
SEED=20261020
TOL_MM=.5
VOLUME_TOL=.01

def distances(target, points):
    return np.concatenate([trimesh.proximity.closest_point(target,p)[1]
                           for p in np.array_split(points,max(1,int(np.ceil(len(points)/BATCH_SIZE))))])

def verify(src=SRC, rebuilt=OUT/'rebuilt.stl', write=True):
    a=trimesh.load(src,force='mesh');b=trimesh.load(rebuilt,force='mesh')
    pa,_=trimesh.sample.sample_surface(a,SAMPLE_COUNT,seed=SEED)
    pb,_=trimesh.sample.sample_surface(b,SAMPLE_COUNT,seed=SEED+1)
    print('Comparing original surface to rebuild',flush=True)
    da=distances(b,pa)
    print('Comparing rebuild surface to original',flush=True)
    db=distances(a,pb);d=np.r_[da,db]
    # Include every original/rebuilt mesh vertex to catch edges missed by random sampling.
    print('Checking mesh vertices',flush=True)
    va=distances(b,a.vertices);vb=distances(a,b.vertices)
    hausdorff=float(max(d.max(),va.max(),vb.max()))
    components_a=sorted(a.split(only_watertight=False),key=lambda q:-q.volume)
    components_b=sorted(b.split(only_watertight=False),key=lambda q:-q.volume)
    report=dict(mean=float(d.mean()),p95=float(np.percentile(d,95)),p99=float(np.percentile(d,99)),
        max=float(d.max()),hausdorff=hausdorff,vertex_max=[float(va.max()),float(vb.max())],
        directional_max=[float(da.max()),float(db.max())],sample_count_per_direction=SAMPLE_COUNT,
        volume_original=float(a.volume),volume_rebuilt=float(b.volume),volume_ratio=float(b.volume/a.volume),
        extent_delta=(b.extents-a.extents).tolist(),euler=[int(a.euler_number),int(b.euler_number)],
        watertight=[bool(a.is_watertight),bool(b.is_watertight)],
        bodies=[len(components_a),len(components_b)],
        body_euler=[[int(q.euler_number) for q in components_a],[int(q.euler_number) for q in components_b]],
        body_volumes=[[float(q.volume) for q in components_a],[float(q.volume) for q in components_b]],
        reference_sha256=hashlib.sha256(Path(src).read_bytes()).hexdigest(),
        rebuilt_sha256=hashlib.sha256(Path(rebuilt).read_bytes()).hexdigest(),
        bounds_original=a.bounds.tolist(),bounds_rebuilt=b.bounds.tolist(),
        worst_original=pa[np.argsort(da)[-20:]].tolist(),worst_rebuilt=pb[np.argsort(db)[-20:]].tolist())
    report['pass']=bool(hausdorff<=TOL_MM and abs(report['volume_ratio']-1)<=VOLUME_TOL
        and np.max(np.abs(report['extent_delta']))<=TOL_MM and report['euler'][0]==report['euler'][1]
        and all(report['watertight']) and report['body_euler'][0]==report['body_euler'][1]
        and report['bodies'][0]==report['bodies'][1])
    if write:
        (OUT/'verification.json').write_text(json.dumps(report,indent=2))
        np.savez(OUT/'deviation_samples.npz',original_points=pa,rebuilt_points=pb,original_d=da,rebuilt_d=db)
        fig,axs=plt.subplots(1,2,figsize=(14,6))
        for ax,pts,ds,title in zip(axs,[pa,pb],[da,db],['Original → rebuild','Rebuild → original']):
            s=ax.scatter(pts[:,0],pts[:,1],c=ds,s=1,vmin=0,vmax=TOL_MM,cmap='turbo')
            ax.set_aspect('equal');ax.set_title(title);fig.colorbar(s,ax=ax,label='distance (mm)')
        fig.tight_layout();fig.savefig(OUT/'deviation.png',dpi=160);plt.close(fig)
    print(json.dumps({k:v for k,v in report.items() if not k.startswith('worst')},indent=2),flush=True)
    return report

if __name__=='__main__':verify()
