from pathlib import Path
import nbformat as nbf
import shutil

OUT=Path(__file__).parent
SRC=Path(r'D:\OneDrive\Documents\3D_Models\Containers+Covers\Cable winder case\FromInternet\earbud_winder_100pct.stl')
shutil.copy2(SRC,OUT/'reference.stl')
nb=nbf.v4.new_notebook()
cells=[]
def md(s):cells.append(nbf.v4.new_markdown_cell(s))
def code(s):cells.append(nbf.v4.new_code_cell(s))
md('# Earphone cable winder reconstruction\nMillimetres; original coordinates preserved. Three separate bodies. Target: sampled bidirectional Hausdorff ≤0.5 mm, volume within 1%, matching Euler number. The compound channel and latch transitions use measured section lofts; this is an approximate redesign, not a recovery of the original CAD history.')
md('## 0. Setup')
code('''from pathlib import Path
import json, hashlib
import numpy as np
import trimesh
import build123d
from build123d import *
import matplotlib.pyplot as plt
from IPython.display import display, Image

OUT = Path.cwd()
if not (OUT / 'reference.stl').exists():
    OUT = OUT / 'CableWinder'
SRC = OUT / 'reference.stl'
TOL_MM = 0.5
VOLUME_TOL = 0.01
RUN_DETECT = False
RUN_MESH_IMPORT = False
RUN_REMEASURE = False
RUN_MODEL = True
RUN_VERIFY = True
SHOW_RECON = False
print('build123d:', build123d.__version__)
HAS_DETECT = hasattr(build123d, 'detect_primitives')
print('detect_primitives:', HAS_DETECT)
print('Reference SHA256:', hashlib.sha256(SRC.read_bytes()).hexdigest())
if SHOW_RECON:
    from ocp_vscode import show, set_defaults, Camera
    set_defaults(reset_camera=Camera.KEEP)
''')
md('## 1. Triage')
code('''m = trimesh.load(SRC, force='mesh')
bodies = sorted(m.split(only_watertight=False), key=lambda b: -b.volume)
def mesh_info(mesh):
    return dict(faces=len(mesh.faces),vertices=len(mesh.vertices),watertight=mesh.is_watertight,
      winding_ok=mesh.is_winding_consistent,volume=float(mesh.volume),area=float(mesh.area),
      bounds=mesh.bounds.tolist(),extents=mesh.extents.tolist(),euler=int(mesh.euler_number))
triage = mesh_info(m)
triage['bodies'] = [mesh_info(b) for b in bodies]
display(triage)
assert m.is_watertight and m.is_winding_consistent
''')
md('Assessment: moderately difficult mechanical assembly. Core, retaining ring, and pin have Euler numbers 0, 0, 2. No mesh repairs. The asymmetric channel and ring opening prevent global symmetry reduction. Z is the stacking axis. Retain the native XY placement and Z=0 floor.')
md('## 2. Orientation')
code('''TRANSFORM = np.eye(4)  # identity: no recentering, rotation, or scale conversion
def symmetric_about(mesh, axis, count=1000):
    pts,_ = trimesh.sample.sample_surface(mesh,count,seed=42)
    pts[:,axis] = 2*mesh.bounds[:,axis].mean()-pts[:,axis]
    d = trimesh.proximity.closest_point(mesh,pts)[1]
    return dict(max=float(d.max()),mean=float(d.mean()))
symmetry = {str(i): {name:symmetric_about(b,j) for j,name in enumerate('XYZ')}
            for i,b in enumerate(bodies)}
display(symmetry)
''')
md('## 3. Structure')
code('''for i,b in enumerate(bodies):
    n=b.face_normals
    aligned = np.abs(n).max(axis=1) > 0.999
    levels = {name:len(np.unique(b.vertices[:,j].round(3))) for j,name in enumerate('XYZ')}
    horizontal = np.abs(n[:,2]) > .99999
    z=np.round(b.triangles_center[:,2],3)
    checksums={float(h):float(b.area_faces[horizontal & (z==h)].sum()) for h in np.unique(z[horizontal])}
    print(i,levels,'axis aligned area share',float(b.area_faces[aligned].sum()/b.area))
    display(dict(sorted(checksums.items(),key=lambda item:-item[1])[:12]))
display(Image(filename=str(OUT/'sections.png')))
''')
md('The core changes topology at Z=0.6 mm; the ring opening begins at Z=2.6 mm. Model these as separate additive features. The pin and core bore use radial stations with a straight waist, conical shoulders, head lands, and end bevels. Compound channel and latch boundaries are approximated by periodic section splines at 0.5 mm height spacing, with extra stations near topology changes.')
md('## 4. Working section')
code('''WORKING_BREP = OUT / 'working_pin.brep'
if RUN_MESH_IMPORT or not WORKING_BREP.exists():
    importer = Mesher()
    working = importer.read(str(OUT/'reference_body_2.stl'))[0]
    export_brep(working,str(WORKING_BREP))
else:
    working = None  # avoid loading a faceted BREP unless detection is requested
print('Cached isolated pin:',WORKING_BREP.name)
''')
md('A half-pin split was attempted in MCP but returned an empty section. Detection therefore uses the isolated 2,264-face pin, reducing the full 46,428-face mesh by 95%. The cached BREP preserves this working region.')
md('## 5. Primitive detection')
code('''if RUN_DETECT and HAS_DETECT:
    working=import_brep(str(WORKING_BREP))
    primitives,leftovers,code_lines=detect_primitives(working)
    detection=dict(code=code_lines,leftovers=len(leftovers),faces=len(working.faces()))
    (OUT/'primitive_detection.json').write_text(json.dumps(detection,indent=2))
elif not HAS_DETECT:
    print('detect_primitives unavailable: use levels, sections, and normals above.')
detection=json.loads((OUT/'primitive_detection.json').read_text())
print('leftovers:',detection['leftovers'],'of',detection['faces'])
print('\\n'.join(detection['code'][-4:]))
''')
md('Detection is a report only. It recognized the main pin cylinders but left 43.9% unclassified and emitted spurious tilted cylinders. None of its code fragments is used in the final model.')
md('## 6. Parameters')
template=(OUT/'model_template.py').read_text()
params=template[template.index('# Dimensions'):template.index('def section_face')]
code(params+'''\nPROFILES=json.loads((OUT/'measured_profiles.json').read_text())
if RUN_REMEASURE:
    # Rebuild measured profile cache from the reference, then reload it.
    import runpy
    runpy.run_path(str(OUT/'prepare_sections.py'))
    PROFILES=json.loads((OUT/'measured_profiles.json').read_text())
''')
md('Each profile record names its Z station and contains measured XY control points. Global width/height and feature dimensions are editable; the profile coordinates remain explicit approximation controls. No transform is applied. Dimensions and assumptions are listed in report.md.')
md('## 7. Model')
methods=template[template.index('def section_face'):template.index('# PROFILE_DATA')]
code(methods+'''\nif RUN_MODEL or not (OUT/'rebuilt.brep').exists():
    core,ring,pin=build_model()
else:
    cached=import_brep(str(OUT/'rebuilt.brep'))
    core,ring,pin=sorted(cached.solids(),key=lambda s:-s.volume)
result=Compound(children=[core,ring,pin])
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
adaptive_volumes={}
for name,part in [('core',core),('ring',ring),('pin',pin)]:
    assert part.is_valid and part.volume>0, name
    properties=GProp_GProps()
    BRepGProp.VolumeProperties_s(part.wrapped,properties,1e-6,True,False)
    adaptive_volumes[name]=properties.Mass()
    print(name,'adaptive volume',properties.Mass(),'faces',len(part.faces()))
if SHOW_RECON: show(core,ring,pin,names=['core','ring','pin'])
''')
md('## 8. Verify')
code('''# Verification always examines the exported STL, rather than the live BREP.
export_stl(result,str(OUT/'rebuilt.stl'),tolerance=0.015,angular_tolerance=0.08)
exported=trimesh.load(OUT/'rebuilt.stl',force='mesh')
raw_face_count=len(exported.faces)
exported.update_faces(exported.nondegenerate_faces())
exported.update_faces(exported.unique_faces())
exported.remove_unreferenced_vertices()
exported.export(OUT/'rebuilt.stl')
print('Removed numerical zero-area/duplicate triangles:',raw_face_count-len(exported.faces))
if RUN_VERIFY:
    import sys
    if str(OUT) not in sys.path:sys.path.insert(0,str(OUT))
    from verify_mesh import verify
    verification=verify(SRC,OUT/'rebuilt.stl')
else:
    verification=json.loads((OUT/'verification.json').read_text())
    assert verification['reference_sha256']==hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert verification['rebuilt_sha256']==hashlib.sha256((OUT/'rebuilt.stl').read_bytes()).hexdigest(), 'Cached verification is stale; set RUN_VERIFY=True'
display(verification)
verification['adaptive_brep_volumes']=adaptive_volumes
(OUT/'verification.json').write_text(json.dumps(verification,indent=2))
display(Image(filename=str(OUT/'deviation.png')))
assert verification['pass'], 'One or more acceptance criteria failed; inspect worst points.'
''')
code('''# Section overlays in native coordinates: reference solid versus export.
r=trimesh.load(OUT/'rebuilt.stl',force='mesh')
fig,axs=plt.subplots(1,4,figsize=(16,4))
for ax,z in zip(axs,[.4,2.8,8.3,16.2]):
    for mesh,color,label in [(m,'black','reference'),(r,'tomato','rebuild')]:
        sec=mesh.section(plane_normal=[0,0,1],plane_origin=[0,0,z])
        for pts in sec.discrete: ax.plot(pts[:,0],pts[:,1],color=color,lw=.7,label=label)
    ax.set_aspect('equal');ax.set_title(f'Z={z} mm')
fig.tight_layout();fig.savefig(OUT/'section_overlays.png',dpi=160);plt.show()
''')
md('Distance statistics are deterministic sampled estimates: 50,000 surface points per direction plus every mesh vertex. They are not a certified continuous Hausdorff upper bound. See report.md for achieved values, local corrections, and remaining approximation error.')
md('## 9. Export')
code('''assert verification['pass']
export_step(result,str(OUT/'rebuilt.step'))
export_brep(result,str(OUT/'rebuilt.brep'))
print('STEP, STL, and BREP exported in',OUT)
''')
nb.cells=cells
nb.metadata.kernelspec={'display_name':'Build123d project .venv','language':'python','name':'python3'}
nbf.write(nb,OUT/'reconstruction.ipynb')
print('Notebook cells',len(cells))
