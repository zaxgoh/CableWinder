from pathlib import Path
import numpy as np
import trimesh
from scipy.spatial import cKDTree

OUT=Path(__file__).parent
for name in ['revision4.stl','aligned.stl']:
    original=trimesh.load(OUT/name)
    original.update_faces(original.nondegenerate_faces())
    original.update_faces(original.unique_faces())
    original.remove_unreferenced_vertices()
    for tolerance in [1e-5,3e-5,1e-4,1e-3]:
        m=original.copy()
        counts=np.bincount(m.edges_unique_inverse,minlength=len(m.edges_unique))
        boundary=np.unique(m.edges_unique[counts!=2])
        coords=m.vertices[boundary]
        pairs=cKDTree(coords).query_pairs(tolerance)
        roots=np.arange(len(boundary))
        def root(a):
            while roots[a]!=a:
                roots[a]=roots[roots[a]];a=roots[a]
            return a
        for a,b in pairs:roots[root(b)]=root(a)
        mapping=np.arange(len(m.vertices))
        for j,v in enumerate(boundary):mapping[v]=boundary[root(j)]
        m.faces=mapping[m.faces]
        m.update_faces(m.nondegenerate_faces());m.update_faces(m.unique_faces());m.remove_unreferenced_vertices()
        print(name,tolerance,len(boundary),len(pairs),m.is_watertight,m.euler_number,flush=True)
        if m.is_watertight and m.euler_number==2:
            m.export(OUT/(name.replace('.stl','_welded.stl')))
            break
