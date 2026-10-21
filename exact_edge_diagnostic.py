"""Read-only diagnostic: match the gate's topology stitch and report coordinates."""
from build123d import *
from collections import defaultdict
import numpy as np
import math
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepTools import BRepTools
from OCP.TopLoc import TopLoc_Location
from OCP.TopExp import TopExp
from OCP.TopAbs import TopAbs_REVERSED

result=import_step(r'D:\Projects\Build123d\CableWinder\compatible_diagnostic.step')
bb=result.bounding_box()
deflection=min(.5,max(.005,bb.size.length*.001))
BRepTools.Clean_s(result.wrapped)
BRepMesh_IncrementalMesh(result.wrapped,deflection,False,.5,True)
faces=list(result.faces())
edges=list(result.edges())
brep_vertices=list(result.vertices())
edge_ids={hash(e.wrapped):i for i,e in enumerate(edges)}
vertex_ids={hash(v.wrapped):i for i,v in enumerate(brep_vertices)}
adj=defaultdict(list)
vertices=[];triangles=[];owners=[];base={};face_tri={}
for fi,face in enumerate(faces):
    for e in face.edges():
        ei=edge_ids[hash(e.wrapped)]
        if fi not in adj[ei]:adj[ei].append(fi)
    loc=TopLoc_Location()
    tri=BRep_Tool.Triangulation_s(face.wrapped,loc)
    if tri is None:continue
    start=len(vertices);base[fi]=start;face_tri[fi]=(tri,loc)
    trsf=loc.Transformation()
    for j in range(1,tri.NbNodes()+1):
        p=tri.Node(j).Transformed(trsf)
        vertices.append((p.X(),p.Y(),p.Z()))
    for j in range(1,tri.NbTriangles()+1):
        a,b,c=tri.Triangle(j).Get()
        a,b,c=start+a-1,start+b-1,start+c-1
        if face.wrapped.Orientation()==TopAbs_REVERSED:a,b=b,a
        triangles.append((a,b,c));owners.append(fi)
verts=np.array(vertices)
parent=list(range(len(vertices)))
def find(i):
    while parent[i]!=i:
        parent[i]=parent[parent[i]];i=parent[i]
    return i
def union(a,b):
    a,b=find(a),find(b)
    if a!=b:parent[max(a,b)]=min(a,b)
vertex_nodes=defaultdict(list)
for ei,edge in enumerate(edges):
    node_lists=[]
    for fi in adj[ei]:
        if fi not in face_tri:continue
        tri,loc=face_tri[fi]
        poly=BRep_Tool.PolygonOnTriangulation_s(edge.wrapped,tri,loc)
        if poly is None:continue
        arr=np.fromiter(poly.Nodes(),dtype=np.int64,count=poly.NbNodes())+base[fi]-1
        node_lists.append(arr)
    if not node_lists:continue
    ref=node_lists[0]
    for other in node_lists[1:]:
        if len(other)!=len(ref):continue
        fwd=np.abs(verts[ref]-verts[other]).max()
        rev=np.abs(verts[ref]-verts[other[::-1]]).max()
        seq=other if fwd<=rev else other[::-1]
        for a,b in zip(ref,seq):union(int(a),int(b))
    first=vertex_ids.get(hash(TopExp.FirstVertex_s(edge.wrapped)))
    last=vertex_ids.get(hash(TopExp.LastVertex_s(edge.wrapped)))
    for arr in node_lists:
        if first is not None:vertex_nodes[first].append(int(arr[0]))
        if last is not None:vertex_nodes[last].append(int(arr[-1]))
for nodes in vertex_nodes.values():
    for n in nodes[1:]:union(nodes[0],n)
roots=np.array([find(j) for j in range(len(vertices))])
uniq,inv=np.unique(roots,return_inverse=True)
mf=inv[np.array(triangles)]
owner=np.array(owners)
keep=(mf[:,0]!=mf[:,1])&(mf[:,1]!=mf[:,2])&(mf[:,0]!=mf[:,2])
mf=mf[keep];owner=owner[keep]
groups=defaultdict(lambda:[[],[]])
for i,t in enumerate(mf):
    a,b,c=map(int,t);s=tuple(sorted((a,b,c)))
    even=(a,b,c) in [(s[0],s[1],s[2]),(s[1],s[2],s[0]),(s[2],s[0],s[1])]
    groups[s][0 if even else 1].append(i)
keep=np.ones(len(mf),dtype=bool)
for ev,od in groups.values():
    count=min(len(ev),len(od))
    keep[ev[:count]]=False;keep[od[:count]]=False
mf=mf[keep];owner=owner[keep]
all_edges=np.sort(np.concatenate([mf[:,[0,1]],mf[:,[1,2]],mf[:,[2,0]]]),axis=1)
ue,counts=np.unique(all_edges,axis=0,return_counts=True)
bad=ue[counts>2]
print('Exact base mesh triangles',len(mf),'nonmanifold edges',len(bad),'deflection',deflection)
evidence=[]
for a,b in bad:
    incident=np.any(mf==a,axis=1)&np.any(mf==b,axis=1)
    fi=np.unique(owner[incident])
    entry=dict(where=verts[uniq[[a,b]]].mean(axis=0).tolist(),
               endpoints=verts[uniq[[a,b]]].tolist(),
               faces=[dict(area=faces[int(j)].area,center=tuple(faces[int(j)].center()),
                           geom=faces[int(j)].geom_type.name) for j in fi])
    evidence.append(entry)
print(evidence[:12])
