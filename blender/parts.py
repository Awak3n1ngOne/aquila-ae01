"""Metal assembly stock. The editable model and GPU export share the same surfaces."""
import math
from mathutils import Vector, Matrix, Quaternion
import bpy
import bmesh

V=Vector
TAU=2*math.pi
SYSTEMS=('Optics & neck','Thoracic armour','Port flight array','Starboard flight array','Wing transmission','Tail fan','Landing gear','Internal chassis')
JOINTS=[
 ('bird',None,(0,0,0)),('body','bird',(0,0,0)),('core','bird',(0,0,0)),
 ('head','bird',(0,-.55,.86)),('tail','bird',(0,.76,-.68)),('stand',None,(0,0,0))]
for s,label in ((-1,'L'),(1,'R')):
    JOINTS.extend([('wing.'+label,'bird',(s*.88,-.03,.55)),
        ('elbow.'+label,'wing.'+label,(s*2.15,.22,.74)),('wrist.'+label,'elbow.'+label,(s*3.55,-.32,.88)),
        ('leg.'+label,'bird',(s*.48,.10,-.46)),('hock.'+label,'leg.'+label,(s*.512,.055,-.935)),
        ('foot.'+label,'hock.'+label,(s*.48,-.27,-1.34))])

def break_cast_edges(obj,width):
    bm=bmesh.new();bm.from_mesh(obj.data)
    edges=[e for e in bm.edges if e.is_manifold and e.calc_face_angle()>.54]
    if edges:
        result=bmesh.ops.bevel(bm,geom=edges,offset=width,segments=3,profile=.52,affect='EDGES',clamp_overlap=True)
        for face in result['faces']:face.smooth=True
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    return obj

def collection(name,scene):
    c=bpy.data.collections.new(name);scene.collection.children.link(c);return c

def geom(name,verts,faces,materials,indices=None,smooth=False,repair=True):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces)
    for m in materials:me.materials.append(m)
    for p in me.polygons:
        if indices is not None:p.material_index=indices[p.index]
        p.use_smooth=bool(smooth)
    if repair:
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    me.update()
    uv=me.uv_layers.new(name='Machining UV')
    for poly in me.polygons:
        n=poly.normal;ax=max(range(3),key=lambda i:abs(n[i]))
        for li in poly.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            coord=(p.y,p.z) if ax==0 else (p.x,p.z) if ax==1 else (p.x,p.y)
            uv.data[li].uv=(coord[0]*1.62,coord[1]*1.62)
    return me

class Stock:
    def __init__(self,scene,materials):
        self.scene=scene;self.materials=materials;self.nodes={};self.bind={};self.parts=[];self.cache={}
        self.rig=collection('00 · Kinematics',scene)
        self.collections={i:collection(f'{i+1:02d} · '+s,scene) for i,s in enumerate(SYSTEMS)}
        self.collections[-1]=collection('09 · Display plinth',scene)
        for name,parent,p in JOINTS:self.joint(name,parent,p)

    def joint(self,name,parent,origin):
        if name in self.nodes:return self.nodes[name]
        o=bpy.data.objects.new(name,None);o.empty_display_type='PLAIN_AXES';o.empty_display_size=.12
        self.rig.objects.link(o);o.parent=self.nodes.get(parent);o.location=V(origin)-self.bind.get(parent,V((0,0,0)))
        o.rotation_mode='QUATERNION';o['joint']=name
        self.nodes[name]=o;self.bind[name]=V(origin);return o

    def link(self,name,parent,data,center,asm,shell,explode):
        center=V(center);o=bpy.data.objects.new(name,data);self.collections[asm].objects.link(o)
        o.parent=self.nodes[parent];o.location=center-self.bind[parent];o['assembly']=asm;o['shell']=bool(shell)
        if explode is None:
            x,y,z=center;s=1 if x>=0 else -1
            base={-1:(0,0,0),0:(x*.24,-.16,(z-.84)*.22),1:(x*.45,y*.23,z*.26),
                  2:(-.15,.13,.11),3:(.15,.13,.11),4:(s*.15,-.23,.18),5:(x*.21,.28,-.08),
                  6:(s*.15,-.16,-.16),7:(x*.23,y*.26,z*.27)}
            explode=base[asm]
        o['part_travel']=list(explode);self.parts.append(o);return o

    def mesh(self,name,parent,verts,faces,mat,*,asm,shell=False,explode=None,face_mats=None,smooth=False):
        verts=[V(v) for v in verts];center=sum(verts,V((0,0,0)))/len(verts)
        keys=mat if isinstance(mat,(list,tuple)) else [mat]
        data=geom(name,[v-center for v in verts],faces,[self.materials[k] for k in keys],face_mats,smooth)
        return self.link(name,parent,data,center,asm,shell,explode)

    def cylinder(self,k,ratio,n,mat):
        name=(k,round(ratio,4),n,mat)
        if name not in self.cache:
            if k=='ring':
                chamfer=min(.026,(1-ratio)*.16)
                rows=[(ratio+chamfer,-.5),(1-chamfer,-.5),(1,-.41),(1,.41),
                      (1-chamfer,.5),(ratio+chamfer,.5),(ratio,.41),(ratio,-.41)]
            else:
                rows=[(.94,-.5),(1,-.47),(ratio,.47),(.94*ratio,.5)]
            vs=[(r*math.cos(TAU*j/n),r*math.sin(TAU*j/n),z) for r,z in rows for j in range(n)]
            fs=[(i*n+j,i*n+(j+1)%n,((i+1)%len(rows))*n+(j+1)%n,((i+1)%len(rows))*n+j)
                for i in range(len(rows) if k=='ring' else 3) for j in range(n)]
            if k!='ring':fs += [tuple(reversed(range(n))),tuple(range(3*n,4*n))]
            data=geom(str(name),vs,fs,[self.materials[mat]])
            for p in data.polygons:
                row=p.index//n
                if k=='ring':p.use_smooth=n>8 and row not in (0,4)
                else:p.use_smooth=n>8 and row==1
            # A turned surface has one unwrapped circumference, including its seam.
            # End faces keep planar coordinates, so the lathe finish stays circular.
            layer=data.uv_layers.active
            for face in data.polygons:
                if abs(face.normal.z)>.95:continue
                circum=[(i%n)/n for i in face.vertices];wrap=max(circum)-min(circum)>.5
                for li,t in zip(face.loop_indices,circum):
                    v=data.vertices[data.loops[li].vertex_index].co
                    layer.data[li].uv=(v.z+.5,t+(1 if wrap and t<.5 else 0))
            self.cache[name]=data
        return self.cache[name]

    def rod(self,name,parent,a,b,r,mat,*,asm,r2=None,n=16,shell=False,explode=None):
        a,b=V(a),V(b);axis=b-a
        o=self.link(name,parent,self.cylinder('rod',1 if r2 is None else r2/r,n,mat),(a+b)*.5,asm,shell,explode)
        o.scale=(r,r,max(.00001,axis.length));o.rotation_mode='QUATERNION';o.rotation_quaternion=V((0,0,1)).rotation_difference(axis.normalized());return o

    def ring(self,name,parent,center,axis,outer,inner,depth,mat,*,asm,n=36,explode=None):
        o=self.link(name,parent,self.cylinder('ring',inner/outer,n,mat),center,asm,False,explode)
        o.scale=(outer,outer,depth);o.rotation_mode='QUATERNION';o.rotation_quaternion=V((0,0,1)).rotation_difference(V(axis).normalized());return o

    def bolt(self,name,parent,center,axis,r,*,asm,mat='steel'):
        center=V(center);axis=V(axis).normalized()
        key=('socket',mat)
        if key not in self.cache:
            # Recessed hexagonal socket, circular shoulder and bevel.
            n=12;rows=[(.91,-.35),(1,-.21),(1,.19),(.87,.32),(.48,.32),(.40,.24),(.40,-.12)]
            vs=[]
            for i,(rad,z) in enumerate(rows):
                for j in range(n):
                    angle=TAU*j/n;factor=.866 if i>=4 and j%2 else 1
                    vs.append((rad*factor*math.cos(angle),rad*factor*math.sin(angle),z))
            fs=[];ids=[]
            for i in range(len(rows)-1):
                for j in range(n):
                    fs.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j));ids.append(int(i>=5))
            fs.extend([tuple(reversed(range(n))),tuple(range((len(rows)-1)*n,len(rows)*n))]);ids.extend([0,1])
            self.cache[key]=geom('Socket head '+mat,vs,fs,[self.materials[mat],self.materials['black']],ids)
        o=self.link(name,parent,self.cache[key],center,asm,False,axis*.16)
        o.scale=(r,r,r);o.rotation_mode='QUATERNION';o.rotation_quaternion=V((0,0,1)).rotation_difference(axis);return o

    def ball(self,name,parent,center,radii,mat,*,asm,shell=False,explode=None):
        key=('ball',mat)
        if key not in self.cache:
            n,k=20,12;vs=[(0,0,1)]
            for i in range(1,k):
                t=math.pi*i/k
                for j in range(n):vs.append((math.sin(t)*math.cos(TAU*j/n),math.sin(t)*math.sin(TAU*j/n),math.cos(t)))
            bottom=len(vs);vs.append((0,0,-1))
            fs=[(0,1+j,1+(j+1)%n) for j in range(n)]
            fs += [(1+i*n+j,1+(i+1)*n+j,1+(i+1)*n+(j+1)%n,1+i*n+(j+1)%n) for i in range(k-2) for j in range(n)]
            fs += [(bottom,1+(k-2)*n+(j+1)%n,1+(k-2)*n+j) for j in range(n)]
            self.cache[key]=geom('Turned '+mat,vs,fs,[self.materials[mat]],smooth=True)
        o=self.link(name,parent,self.cache[key],center,asm,shell,explode);o.scale=radii;return o

    def tube(self,name,parent,points,r,mat,*,asm,n=8,explode=None):
        pts=[V(p) for p in points];tangent=(pts[1]-pts[0]).normalized()
        ref=V((0,0,1)) if abs(tangent.z)<.9 else V((0,1,0));ref=tangent.cross(ref).normalized()
        vs=[];fs=[]
        for i,p in enumerate(pts):
            t=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();ref=(ref-t*ref.dot(t)).normalized();b=t.cross(ref)
            vs.extend([p+r*(ref*math.cos(TAU*j/n)+b*math.sin(TAU*j/n)) for j in range(n)])
            if i:fs.extend([((i-1)*n+j,(i-1)*n+(j+1)%n,i*n+(j+1)%n,i*n+j) for j in range(n)])
        end=(len(pts)-1)*n;fs.extend([tuple(reversed(range(n))),tuple(end+j for j in range(n))])
        return self.mesh(name,parent,vs,fs,mat,asm=asm,explode=explode,smooth=True)
