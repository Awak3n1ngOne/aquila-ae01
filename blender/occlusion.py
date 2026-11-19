"""Short-range, object-space ambient occlusion for the web model's seams and recessed hardware."""
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def build(g):
    verts=[];faces=[]
    for obj in g.parts:
        if obj['assembly']<0:continue
        idx=len(verts);m=obj.matrix_world
        verts.extend(m@v.co for v in obj.data.vertices)
        faces.extend([idx+j for j in f.vertices] for f in obj.data.polygons)
    bvh=BVHTree.FromPolygons(verts,faces)
    cache={}
    def sample(p,n):
        key=tuple(round(v*42) for v in p)+tuple(round(v*3.2) for v in n)
        if key in cache:return cache[key]
        ref=Vector((0,0,1)) if abs(n.z)<.82 else Vector((1,0,0));u=n.cross(ref).normalized();v=n.cross(u)
        occ=0;point=p+.0018*n
        for a,b in ((0,0),(.88,.27),(-.67,.69),(-.26,-.92)):
            ray=(n+u*a+v*b).normalized()
            hit=bvh.ray_cast(point,ray,.195)[3]
            if hit is not None:occ+=(1-min(1,hit/.195))**.55
        value=1-.44*occ/4
        cache[key]=value;return value
    return sample
