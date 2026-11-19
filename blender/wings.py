"""Aquila wing cassettes in their neutral glide pose. All stations are in metres."""
from math import cos, sin, pi, sqrt, atan2

TAU = 2 * pi

def add(a, b):
    return tuple(u + v for u, v in zip(a, b))

def sub(a, b):
    return tuple(u - v for u, v in zip(a, b))

def mul(a, s):
    return tuple(u * s for u in a)

def mix(a, b, t):
    return add(a, mul(sub(b, a), t))

def unit(a):
    length = sqrt(sum(i*i for i in a))
    return tuple(i / length for i in a)

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

SHOULDER = (.88,-.03,.55)
ELBOW = (2.15,.22,.74)
WRIST = (3.55,-.32,.88)
DIGIT = (4.08,-.49,.97)

# Measured across the chord: the extra return folds describe the underside.
RIM = ((-1,-.34),(-1,-.02),(-.965,.15),(-.53,.35),(-.085,.52),
       (-.035,.91),(.015,1),(.072,.58),(.33,.43),(.93,.14),
       (.986,.015),(1,-.18),(.979,-.36),(.49,-.35),(.095,-.48),
       (.025,-.85),(-.038,-.72),(-.105,-.45),(-.60,-.32))
STATIONS = {
 'primary': ((0,.15),(.07,.29),(.16,.48),(.32,.77),(.49,.97),(.64,1),
             (.76,.92),(.833,.79),(.851,.73),(.865,.75),(.926,.50),
             (.967,.30),(.989,.13),(1,.018)),
 'secondary': ((0,.19),(.08,.40),(.23,.71),(.41,.94),(.58,1),(.73,.97),
               (.84,.86),(.916,.65),(.964,.42),(.991,.19),(1,.028)),
 'covert': ((0,.28),(.10,.59),(.29,.90),(.49,1),(.68,.91),(.82,.72),
            (.931,.42),(.977,.22),(1,.027))
}

class Wing:
    def __init__(self,g,side):
        self.g=g
        self.s=side
        self.suffix='L' if side<0 else 'R'
        self.asm=2 if side<0 else 3
        self.arm='wing.'+self.suffix
        self.fore='elbow.'+self.suffix
        self.hand='wrist.'+self.suffix
        self.vane_number=0

    def p(self,point):
        return (self.s*point[0],point[1],point[2])

    def name(self,label):
        return self.suffix+' '+label

    def mesh(self,name,parent,vertices,faces,materials,asm,ids,shift=None,shell=False,smooth=False):
        # All primitives are authored on the starboard side; preserve outward winding after reflection.
        faces=faces if self.s>0 else [tuple(reversed(face)) for face in faces]
        return self.g.mesh(self.name(name),parent,[self.p(v) for v in vertices],faces,materials,
                           asm=asm,face_mats=ids,shell=shell,smooth=smooth,
                           explode=self.p(shift) if shift is not None else None)

    def rod(self,name,group,a,b,r,metal,r2=None,n=14,shift=None):
        return self.g.rod(self.name(name),group,self.p(a),self.p(b),r,metal,r2=r2,n=n,asm=4,
                          explode=self.p(shift) if shift is not None else None)

    def ring(self,name,group,at,axis,outer,inner,depth,metal,n=28,shift=None):
        return self.g.ring(self.name(name),group,self.p(at),self.p(axis),outer,inner,depth,metal,n=n,asm=4,
                           explode=self.p(shift) if shift is not None else None)

    def bolt(self,name,group,at,axis,r,asm=4,metal='steel'):
        return self.g.bolt(self.name(name),group,self.p(at),self.p(axis),r,asm=asm,mat=metal)

    def tube(self,name,group,points,r,metal):
        return self.g.tube(self.name(name),group,[self.p(p) for p in points],r,metal,asm=4,n=8)

    def bearing(self,name,group,at,r,width,full=False):
        axis=(0,1,0)
        self.ring(name+' cross journal',group,at,axis,r*.91,r*.29,width,'gun',32)
        self.rod(name+' axle',group,add(at,(0,-width*.66,0)),add(at,(0,width*.65,0)),
                 r*.285,'steel',n=16)
        for end in [-1,1]:
            face=add(at,(0,end*width*.49,0))
            self.ring(name+' thrust collar',group,face,axis,r,r*.70,.034 if full else .025,'edge',32)
            self.ring(name+' ground race',group,add(face,(0,end*.022,0)),axis,r*.78,r*.43,.031,'silver',32)
            self.ring(name+' oil seal',group,add(face,(0,end*.038,0)),axis,r*.63,r*.53,.014,'orange',28)
            self.ring(name+' retainer',group,add(face,(0,end*.047,0)),axis,r*.48,r*.23,.035,'gun',20)
            self.bolt(name+' centre lock',group,add(face,(0,end*.067,0)),(0,end,0),r*.22,metal='bronze')
            if full:
                for j in range(6):
                    a=TAU*j/6+.22
                    self.bolt(name+' flange screw',group,add(face,(r*.865*cos(a),end*.018,r*.865*sin(a))),
                              (0,end,0),r*.052,metal='gun')

    def cog(self,name,group,at,r,teeth,width,metal='steel',phase=0,web=False):
        # Two concentric annuli, a toothed rim with end chamfers and five open webs.
        verts=[]; faces=[]; mats=[]
        def face(*idx,mat=0):
            faces.append(idx);mats.append(mat)
        profiles=[(-width/2,.72),(-width/2,1-width/r*.085),(-width*.32,1),
                  (width*.32,1),(width/2,1-width/r*.085),(width/2,.72)]
        angles=[(TAU*(i+ph)/teeth+phase, k) for i in range(teeth)
                for ph,k in ((.03,.91),(.23,.91),(.36,1),(.69,1),(.83,.91))]
        N=len(angles)
        for y,k in profiles:
            for angle,tooth in angles:
                rad=r*k*(1 if k<.78 else tooth)
                verts.append(add(at,(rad*cos(angle),y,rad*sin(angle))))
        for row in range(len(profiles)):
            nxt=(row+1)%len(profiles)
            for j in range(N):
                q=(j+1)%N
                face(row*N+j,nxt*N+j,nxt*N+q,row*N+q,mat=(1 if row in (1,3) else 0))
        # A light pinion has five individual spokes. The flywheel has a bored continuous spider.
        for i in range(0 if web else 5):
            angle=TAU*i/5+.10
            poly=[]
            for radial,delta in [(.28,-.25),(.76,-.125),(.76,.105),(.28,.26)]:
                a=angle+delta
                poly.append((r*radial*cos(a),r*radial*sin(a)))
            o=len(verts)
            for y in [-width*.31,width*.31]:
                verts.extend([add(at,(x,y,z)) for x,z in poly])
            face(o,o+1,o+2,o+3);face(o+7,o+6,o+5,o+4)
            for k in range(4):
                j=(k+1)%4;face(o+j,o+k,o+4+k,o+4+j)
        self.mesh(name,group,verts,faces,[metal,'edge'],4,mats,(.17,-.13 if at[1]<0 else .13,.08))
        self.ring(name+' keyed hub',group,at,(0,1,0),r*.32,r*.13,width*1.45,'gun',24)
        if web:
            self.spider(name+' pierced web',at,r,width,phase,metal)

    def spider(self,name,at,r,thickness,phase,metal):
        # Subdivide the 72° sectors and weld their radial boundaries. Each window
        # has a chamfer on both faces and a machined return surface through the plate.
        verts=[];faces=[];ids=[];seen={}
        perimeter=((0,0),(.25,0),(.5,0),(.75,0),(1,0),(1,.5),(1,1),
                   (.75,1),(.5,1),(.25,1),(0,1),(0,.5))
        window=((.22,.25),(.33,.17),(.46,.15),(.56,.18),(.62,.26),(.77,.47),
                (.84,.70),(.80,.83),(.61,.87),(.37,.84),(.21,.75),(.15,.48))
        def ring(sector,profile,y,mouth=1):
            poly=[]
            for t,h in profile:
                u=.5+(t-.5)*mouth;v=.5+(h-.5)*mouth
                a=phase+(sector+u)*TAU/5
                rad=r*(.285+.451*v)
                pt=add(at,(rad*cos(a),y,rad*sin(a)))
                key=tuple(round(x,8) for x in pt)
                if key not in seen:seen[key]=len(verts);verts.append(pt)
                poly.append(seen[key])
            return poly
        def face(points,material):
            faces.append(points);ids.append(material)
        for sector in range(5):
            half=thickness*.37
            low=ring(sector,perimeter,-half);high=ring(sector,perimeter,half)
            m0=ring(sector,window,-half,1.055);b0=ring(sector,window,-half*.71)
            b1=ring(sector,window,half*.71);m1=ring(sector,window,half,1.055)
            for j in range(12):
                k=(j+1)%12
                for a,b,mat in ((low,m0,0),(m0,b0,1),(b0,b1,2),(b1,m1,1),(m1,high,0)):
                    face((a[j],b[j],b[k],a[k]),mat)
                if j in (0,1,2,3,6,7,8,9):
                    face((low[j],low[k],high[k],high[j]),0)
        self.mesh(name,self.arm,verts,faces,[metal,'edge','gun'],4,ids,(.14,.11 if at[1]>0 else -.11,.07))

    def crescent(self,name,center,outer,inner,width,ystep):
        # The open 198° carrier exposes the working teeth from each viewing side.
        verts=[];faces=[];ids=[];n=37
        for j in range(n):
            a=(128+198*j/(n-1))*pi/180
            for r,y in ((inner,-width*.36),(inner+.010,-width*.5),(outer-.012,-width*.5),
                        (outer,-width*.25),(outer,width*.25),(outer-.012,width*.5),
                        (inner+.010,width*.5),(inner,width*.36)):
                verts.append(add(center,(r*cos(a),ystep+y,r*sin(a))))
        m=8
        for j in range(n-1):
            for k in range(m):
                a=j*m+k;b=j*m+(k+1)%m;faces.append((a,b,b+m,a+m))
                ids.append(1 if k in (1,4,6) else 0)
        faces.extend((tuple(reversed(range(m))),tuple((n-1)*m+k for k in range(m))))
        ids.extend([0,0])
        self.mesh(name,self.arm,verts,faces,['gun','edge'],4,ids,(.08,.16 if ystep>0 else -.16,.03))

    def shoulder(self):
        group=self.arm;axis=(0,1,0)
        center=add(SHOULDER,(.038,.0,.004))
        reach=.650;rise=.093
        idler=add(center,(reach,0,rise))
        contact=atan2(rise,reach)
        r=.500;pin=.188
        self.bearing('shoulder pillow block',group,center,.266,.47,True)
        self.ring('countershaft through-bushing',group,idler,axis,.129,.056,.538,'gun',28)
        self.rod('shoulder cross axle',group,add(center,(0,-.40,0)),add(center,(0,.40,0)),.063,'steel',n=16)
        self.rod('countershaft cross axle',group,add(idler,(0,-.392,0)),add(idler,(0,.392,0)),.052,'steel',n=16)
        for f in (-1,1):
            label='front' if f<0 else 'rear'
            mid=.286*f
            self.cog(label+' shoulder crown gear',group,add(center,(0,mid,0)),r,40,.075,
                     'gun' if f<0 else 'steel',contact-.51*TAU/40,web=True)
            self.cog(label+' meshing pinion',group,add(idler,(0,mid,0)),pin,15,.073,
                     'gun' if f<0 else 'steel',contact+pi-.12*TAU/15)
            self.crescent(label+' open shoulder carrier',center,.575,.513,.085,.242*f)
            output=add(center,(0,.365*f,0))
            self.cog(label+' concentric reduction sun',group,output,.286,32,.048,'gun',phase=.045,web=True)
            self.ring(label+' ground sun face',group,add(output,(0,.019*f,0)),axis,.241,.174,.023,'steel',48)
            self.ring(label+' central bronze journal',group,add(output,(0,.038*f,0)),axis,.167,.078,.051,'edge',40)
            self.ring(label+' inner spiral retaining clip',group,add(output,(0,.068*f,0)),axis,.112,.084,.011,'gun',40)
            self.ring(label+' lathe track on outer crown',group,add(center,(0,.326*f,0)),axis,.438,.425,.007,'gun',64)
            for n in range(8):
                t=(n+.37)*TAU/8
                p=add(output,(.213*cos(t),.034*f,.213*sin(t)))
                self.bolt(label+' countersunk face screw '+str(n),group,p,(0,f,0),.014,metal='gun')
            # The idler runs inside the common housing, with a separate bearing ear on each cheek.
            y=.176*f
            a=add(center,(.31,y,-.37));b=add(idler,(.009,y,-.002))
            self.cheek(label+' bored countershaft mounting ear',group,a,b,.100,.074,'bronze',2)
            self.ring(label+' countershaft boss',group,b,axis,.153,.082,.084,'bronze',26)
            self.ring(label+' countershaft bearing seal',group,add(b,(0,.052*f,0)),axis,.127,.090,.018,'black',22)
            self.ring(label+' shoulder locknut',group,add(center,(0,.348*f,0)),axis,.110,.045,.042,'bronze',12)
            self.ring(label+' pinion locknut',group,add(idler,(0,.341*f,0)),axis,.081,.033,.041,'edge',12)
            # An eccentric crank, a bored connecting rod and two captive clevis pins sit outside the mesh.
            a=add(center,(.015,.453*f,-.168))
            b=add(idler,(-.013,.453*f,-.067))
            self.cheek(label+' external dogbone',group,a,b,.054,.042,'steel',2)
            for j,(p,rad) in enumerate(((a,.084),(b,.068))):
                self.ring(label+' crank eye '+str(j),group,p,axis,rad,rad*.46,.058,'steel',22)
                self.rod(label+' captive clevis pin '+str(j),group,add(p,(0,-.082*f,0)),add(p,(0,.056*f,0)),
                         rad*.43,'edge',n=14)
                self.ring(label+' pin retainer '+str(j),group,add(p,(0,.039*f,0)),axis,rad*.64,rad*.36,.014,'gun',18)
                self.bolt(label+' clevis socket cap '+str(j),group,add(p,(0,.057*f,0)),(0,f,0),rad*.42,metal='gun')
        for j,deg in enumerate((143,184,232,278,313)):
            t=deg*pi/180;at=add(center,(.543*cos(t),0,.543*sin(t)))
            self.rod('cast carrier cross stay %d'%j,group,add(at,(0,-.252,0)),add(at,(0,.252,0)),
                     .033,'gun',n=12)
            for f in (-1,1):
                self.bolt('carrier ear screw %d'%j,group,add(at,(0,f*.29,0)),(0,f,0),.022,metal='edge')

    def cheek(self,name,group,a,b,height,depth,material,count):
        # Each half shell has actual through-apertures, a bevel at both mouths, and a closed inner wall.
        tangent=unit(sub(b,a))
        normal=unit(cross((0,0,1),tangent))
        up=unit(cross(tangent,normal))
        V=[];F=[];I=[]; index={}
        def vert(p):
            key=tuple(round(x,7) for x in p)
            if key not in index:
                index[key]=len(V);V.append(p)
            return index[key]
        def surface(t,h,thick):
            center=mix(a,b,t)
            camber=.10*height*sin(pi*t)
            return vert(add(add(center,mul(up,height*h*(1-.30*t)+camber)),mul(normal,thick)))
        def push(v,idx):
            F.append(v);I.append(idx)
        for cell in range(count):
            u0=cell/count; length=1/count
            outer=[(0,-1),(.5,-1),(1,-1),(1,0),(1,1),(.5,1),(0,1),(0,0)]
            if cell%2:
                hole=[(.23,-.43),(.55,-.53),(.76,-.43),(.80,-.15),(.70,.47),(.46,.49),(.20,.26),(.16,.03)]
            else:
                hole=[(.18,-.48),(.46,-.55),(.79,-.34),(.83,-.06),(.74,.28),(.44,.52),(.29,.47),(.16,-.09)]
            def ring(points,thickness,expand=1):
                return [surface(u0+(.5+(x-.5)*expand)*length,z*expand,thickness) for x,z in points]
            out1=ring(outer,-depth/2);out2=ring(outer,depth/2)
            mouth1=ring(hole,-depth/2,1.07);bore1=ring(hole,-depth*.31)
            bore2=ring(hole,depth*.31);mouth2=ring(hole,depth/2,1.07)
            for j in range(8):
                k=(j+1)%8
                push((out1[j],out1[k],mouth1[k],mouth1[j]),0)
                push((out2[j],mouth2[j],mouth2[k],out2[k]),0)
                push((mouth1[j],mouth1[k],bore1[k],bore1[j]),1)
                push((bore1[j],bore1[k],bore2[k],bore2[j]),2)
                push((bore2[j],bore2[k],mouth2[k],mouth2[j]),1)
                if (j in (0,1,4,5)) or (cell==0 and j in (6,7)) or (cell==count-1 and j in (2,3)):
                    push((out1[j],out2[j],out2[k],out1[k]),1)
        sign=1 if a[1]>0 else -1
        from parts import break_cast_edges
        cheek=self.mesh(name,group,V,F,[material,'edge','gun'],4,I,(.19,sign*.24,.12),shell=True)
        break_cast_edges(cheek,min(.009,depth*.13))

    def hydraulic(self,name,group,a,b,r):
        intervals=((0,.065,.70,'gun'),(.06,.14,.99,'edge'),(.125,.52,.92,'steel'),
                   (.20,.235,.969,'gun'),(.405,.447,.965,'edge'),(.50,.57,1.0,'gun'),
                   (.556,.59,.95,'orange'),(.59,.63,.91,'silver'),(.615,.918,.39,'silver'),
                   (.89,.949,.64,'gun'),(.935,1,.48,'edge'))
        for j,(start,end,rad,metal) in enumerate(intervals):
            self.rod(name+' '+str(j+1),group,mix(a,b,start),mix(a,b,end),r*rad,metal,
                     n=32 if r>.09 else 24 if r>.06 else 16)
        for j,t in enumerate([.245,.27,.295,.32]):
            self.rod(name+' gland groove '+str(j+1),group,mix(a,b,t),mix(a,b,t+.009),r*.947,'gun',n=32 if r>.09 else 24 if r>.06 else 16)

    def feather(self,name,group,a,b,width,kind,metal,idx,sweep=0,bank=0,side='top',rib=True):
        chord=sub(b,a); flat=unit((chord[0],chord[1],0))
        lat=(flat[1],-flat[0],0)
        self.vane_number+=1
        socket='feather.'+self.suffix+'.%02d'%self.vane_number
        hinge=self.g.joint(socket,group,self.p(a))
        hinge['vane_kind']=kind
        hinge['vane_side']=self.s
        hinge['vane_index']=idx
        hinge['vane_ventral']=side=='under'
        hinge['vane_axis']=self.p(chord)
        # The smooth crown rolls with the plate; its normal removes twist ambiguity at the wrist.
        hinge['vane_normal']=self.p(unit(cross(add(lat,(0,0,bank)),chord)))
        group=socket
        stations=STATIONS[kind]
        verts=[];faces=[];mats=[]
        side_dir=1 if side=='top' else -1
        # The rounded over-camber differs on the port and starboard halves of the vane.
        for i,(t,w) in enumerate(stations):
            arch=sin(pi*t)
            point=add(add(mix(a,b,t),mul(lat,sweep*arch)),(0,0,side_dir*(.043 if kind!='covert' else .025)*arch))
            thickness=(width*(.084 if kind=='covert' else .073))*(.55+.45*w)
            for j,(u,h) in enumerate(RIM):
                asym=.39 if u<0 else .61
                across=u*width*w*asym
                if kind=='primary' and t in (.833,.851) and u>.93:
                    across-=width*(.085 if t==.851 else .018)
                across+=.045*width*w*arch
                bias=bank*across + side_dir*thickness*h
                verts.append(add(add(point,mul(lat,across)),(0,0,bias)))
        n=len(RIM)
        for i in range(len(stations)-1):
            for j in range(n):
                k=(j+1)%n
                f=(i*n+j,(i+1)*n+j,(i+1)*n+k,i*n+k)
                # lat x length points upward for the dorsal patch on this winding.
                faces.append(f if side_dir<0 else tuple(reversed(f)))
                if j in (0,10,11,12,18):
                    mat=2
                elif j==1 or (j==9 and kind=='primary'):
                    mat=1
                elif j in (5,6) and i<len(stations)*.65 and rib:
                    mat=0
                elif side=='under' and j in (14,15):
                    mat=1
                else:
                    mat=0
                mats.append(mat)
        for ids in [list(range(n)),[(len(stations)-1)*n+j for j in reversed(range(n))]]:
            faces.append(tuple(ids if side_dir<0 else reversed(ids)));mats.append(2)
        dy=.10 if kind=='primary' else .04
        off=(.105+idx*.010,.22+dy+.023*(idx%5),side_dir*(.22+.017*(idx%5)))
        vane=self.mesh(name,group,verts,faces,['plate_'+metal,'edge','dark'],self.asm,mats,off,shell=True,smooth=True)
        from plume import station_uv
        station_uv(vane.data,n,[t for t,_ in stations],[u for u,_ in RIM])
        for poly in vane.data.polygons:
            if len(poly.vertices)!=4:poly.use_smooth=False
        for edge in vane.data.edges:
            u,v=edge.vertices
            if u%n==v%n and u%n in (0,1,6,10,12,16):
                edge.use_edge_sharp=True
        # One flush antirotation pin sits in the exposed lap.
        if kind=='primary' or (kind=='covert' and idx%3==1):
            t=.63 if kind=='primary' else .72;across=width*(.15 if idx%2 else -.16)
            centre=add(add(mix(a,b,t),mul(lat,sweep*sin(pi*t)+across)),(0,0,side_dir*(.043 if kind!='covert' else .025)*sin(pi*t)+bank*across+side_dir*width*.034))
            self.bolt(name+' antirotation pin',group,centre,(0,-.12*side_dir,side_dir),width*.034,self.asm,'gun')
        # Exposed, dished eyelet roots have real returns on the underside.
        if kind!='covert' and rib:
            seat=add(mix(a,b,.095),(0,0,-.027))
            self.ring(name+' threaded root liner',group,seat,(0,0,1),width*.116,width*.062,.027,'edge',14,shift=off)
            self.bolt(name+' root pin',group,add(seat,(0,0,.026)),(0,0,1),width*.046,self.asm,'gun')

    def flight_stock(self):
        # Long basal feathers issue from separate knuckles on the hand rather than one common point.
        primary_tips=[
            (5.26,-.84,1.28),(5.53,-.46,1.24),(5.57,-.01,1.17),(5.46,.43,1.04),
            (5.26,.88,.93),(5.00,1.28,.81),(4.69,1.61,.66),(4.34,1.85,.55),
            (3.98,1.97,.48),(3.59,1.96,.42)]
        primary_width=[.30,.352,.38,.408,.434,.453,.46,.465,.462,.45]
        for j,tip in enumerate(primary_tips):
            q=j/9
            root=(4.02-.65*q,-.44+.46*q,1.030-.159*q)
            metal=['dark','umber','dark','umber','dark','umber','umber','dark','umber','umber'][j]
            self.feather('P%02d slotted flight vane'%(10-j),self.hand,root,tip,primary_width[j],
                         'primary',metal,j,-.042-.012*q,.16+.04*q)
        n=13
        for j in range(n):
            q=j/(n-1)
            x=.77+2.63*q
            root=self.station(x)
            root=add(root,(0,.115,-.021))
            tip=(.88+2.46*q+.08*sin(pi*q),1.26+.70*sin(pi*q*.62)+.06*q,.11+.31*q-.055*sin(pi*q))
            width=.382+.115*sin(pi*q*.92)
            self.feather('S%02d trailing flight vane'%(j+1),self.subgroup(x),root,tip,width,'secondary',
                         'umber' if j%4 in (0,2,3) else 'bronze',j,.045-.07*q,.16+.04*q)
        # Coverts are arranged by tract, in staggered rows with returns on both wing surfaces.
        # Bottom row is shorter so the broad flight plates still show their underside faces and keels.
        for surface in ('top','under'):
            up=1 if surface=='top' else -1
            for row,(count,start,end,maxlen) in enumerate(((17,.78,4.02,1.36),(15,.78,3.75,.95),(12,.83,3.50,.57))):
                if surface=='under':
                    count-=1;maxlen*=.97
                for j in range(count):
                    q=j/(count-1);x=start+(end-start)*q+(.032 if surface=='under' else 0)
                    base=self.station(x)
                    # Underside rows start farther aft so the conduit and actuators remain in view.
                    fore=(.13 if up==1 else .22)+.026*sin(j)
                    if row:
                        fore-=.069*row
                    z=(.059+.048*row)*up
                    a=add(base,(-.065*q,fore,z))
                    length=maxlen*(.69+.32*sin(q*2.36))*(1-.21*max(0,(q-.78)/.22))
                    descent=(-.17 if up==1 else -.36-.12*sin(pi*q))*length
                    b=add(a,(.13+.29*q+.04*sin(j*1.3),length,descent+up*.019))
                    w=(.37,.335,.32)[row]*(.93+.16*sin(pi*q))
                    material=('bronze' if (j+row)%4 in (0,1) else 'umber') if up==1 else ('umber' if j%4 else 'bronze')
                    self.feather(('dorsal' if up==1 else 'ventral')+' covert %d.%02d'%(row+1,j+1),
                                 self.subgroup(x),a,b,w,'covert',material,j,.045*(1-q),.15+.025*row,surface,False)
            # The wrist's splayed lesser coverts bridge from the duct to the long primaries.
            for j in range(8 if surface=='top' else 5):
                t=j/(7 if surface=='top' else 4);x=3.40+.59*t
                a=add(self.station(x),(0,.035,up*.105))
                b=add(a,(.40+.57*t,.73-.79*t,-.09+.12*t))
                self.feather(('upper' if up==1 else 'lower')+' manus shield %d'%j,self.hand,a,b,
                             .25+.07*(1-t),'covert','bronze' if j%3==0 else 'umber',j,
                             -.035,.16,surface,False)

    @staticmethod
    def station(x):
        if x<ELBOW[0]:
            a,b=SHOULDER,ELBOW
        elif x<WRIST[0]:
            a,b=ELBOW,WRIST
        else:
            a,b=WRIST,DIGIT
        return mix(a,b,(x-a[0])/(b[0]-a[0]))

    def subgroup(self,x):
        return self.arm if x<ELBOW[0] else self.fore if x<WRIST[0] else self.hand

    def mechanisms(self):
        s,e,w=SHOULDER,ELBOW,WRIST
        from mathutils import Matrix,Vector
        from math import radians
        start=len(self.g.parts)
        self.shoulder()
        # Cant the gearbox about its mounting seat, independently of the feather sheet.
        shaft=Vector((self.s,0,.14)).normalized()
        tilt=Matrix.Rotation(radians(24*self.s),4,shaft)
        pivot=Vector(self.p(SHOULDER))-self.g.bind[self.arm]
        for item in self.g.parts[start:]:
            item.rotation_mode='QUATERNION'
            item.location=pivot+tilt.to_3x3()@(item.location-pivot)
            item.rotation_quaternion=tilt.to_quaternion()@item.rotation_quaternion
            item['part_travel']=list(tilt.to_3x3()@Vector(item['part_travel']))
        self.bearing('elbow flexion pin',self.fore,e,.183,.30,True)
        self.bearing('carpal gimbal',self.hand,w,.151,.249,True)
        self.rod('humeral axle tenon',self.arm,add(s,(-.32,.008,-.003)),add(s,(.06,.011,.015)),.141,'gun',.125,20)
        for group,first,last,h,n,label in [(self.arm,s,e,.155,3,'humeral'),(self.fore,e,w,.120,4,'radioulnar')]:
            for side in [-1,1]:
                delta=side*(.147 if label=='humeral' else .112)
                a=add(mix(first,last,.03),(0,delta,-.006))
                b=add(mix(first,last,.96),(0,delta,.006))
                self.cheek(label+(' anterior' if side<0 else ' dorsal')+' web',group,a,b,h,
                           .048 if label=='humeral' else .038,'bronze' if side>0 else 'umber',n)
                for point,t in [(a,.135),(b,.83)]:
                    self.bolt(label+' skin retainer',group,add(mix(a,b,t),(0,side*.027,h*.70)),
                              (0,side,0),.023 if side>0 else .018)
            a=add(mix(first,last,.155),(0,-.001,-.055));b=add(mix(first,last,.91),(0,-.016,.034))
            self.hydraulic(label+' polished servo',group,a,b,.118 if group==self.arm else .086)
            # Reversible linkage under the spar, visible in the reverse/underside orbit.
            a2=add(mix(first,last,.12),(0,.146,-.11));b2=add(mix(first,last,.90),(0,.159,-.072))
            self.hydraulic(label+' return damper',group,a2,b2,.064 if group==self.arm else .049)
            for k,t in enumerate([.13,.40,.73,.89]):
                a3=add(mix(first,last,t),(0,-.142,-h*.7))
                b3=add(mix(first,last,t),(0,.141,-h*.7))
                self.rod(label+' cross spacer '+str(k+1),group,a3,b3,.023,'gun',n=10)
            for j,metal in enumerate(['black','edge','black']):
                z=-h-.034-.024*j
                pts=[add(mix(first,last,k),(0,.14+.016*j,z-.073*sin(pi*k))) for k in (0,.09,.25,.51,.68,.86,.96,1)]
                self.tube(label+' pressure line '+str(j+1),group,pts,.016 if j!=1 else .009,metal)
        # Two pinned clevises retain the large, exposed cylinder on the outside cheek.
        a=add(s,(.34,-.328,-.174));b=add(e,(-.035,-.296,.098))
        self.hydraulic('outer shoulder actuator',self.arm,a,b,.125)
        for num,(seat,hub) in enumerate(((a,add(s,(.28,-.159,-.18))),(b,add(e,(-.045,-.145,.063))))):
            self.rod('outer ram clevis boss '+str(num),self.arm,hub,seat,.081,'gun',.067,24)
            self.ring('outer ram clevis eye '+str(num),self.arm,seat,(0,1,0),.103,.042,.095,'steel',30)
            self.bolt('outer ram pivot '+str(num),self.arm,add(seat,(0,-.052,0)),(0,-1,0),.045,metal='gun')
        for side in (-1,1):
            lower=add(s,(.07,side*.247,-.524));upper=add(e,(-.08,side*.18,-.13))
            self.cheek('pierced gearbox lower cheek '+str(side),self.arm,lower,upper,.106,.063,'umber',3)
            for k in (0,.52,1):
                point=add(mix(lower,upper,k),(0,side*.037,0))
                self.bolt('lower cheek flush fastener',self.arm,point,(0,side,0),.028,metal='gun')
        p=add(e,(.07,-.18,-.02));q=add(w,(-.08,-.16,.072))
        self.hydraulic('wrist extension piston',self.fore,p,q,.101)
        self.cheek('carpometacarpal yoke',self.hand,add(w,(.016,-.01,.024)),DIGIT,.078,.109,'bronze',2)
        self.rod('carpal fairlead shaft',self.hand,add(w,(-.04,-.08,-.025)),add(DIGIT,(.11,-.015,-.013)),
                 .047,'steel',.018,16)
        # Knuckle bridge combs and pins connect the vane roots to the segmented leading edge.
        for j in range(8):
            q=j/7;anchor=mix(w,DIGIT,q)
            toe=add(anchor,(.19+.062*q,.22-.23*q,-.008))
            self.rod('digital fork %02d'%j,self.hand,anchor,toe,.032,'gun',.022,12)
            self.bolt('digital pivot %02d'%j,self.hand,add(toe,(0,0,.026)),(0,0,1),.020,metal='edge')
        self.tube('carpal cable loop',self.hand,[add(w,(0,.11,-.10)),add(w,(.045,.20,-.149)),
                  add(w,(.22,.18,-.145)),add(DIGIT,(-.04,.14,-.064)),add(DIGIT,(.04,.079,-.043))],.018,'black')

def fold_feathers(g, rotations):
    """Solve the socket of each flight plate in its moving joint frame for the perched pose."""
    from math import radians
    from mathutils import Vector, Matrix, Quaternion
    poses={}
    def world(key):
        if key in poses:
            return poses[key]
        node=g.nodes[key]
        q=rotations[key]
        if node.parent is None:
            global_pose=(g.bind[key].copy(),q)
        else:
            parent=node.parent['joint']
            pos,rot=world(parent)
            global_pose=(pos+rot@(g.bind[key]-g.bind[parent]),rot@q)
        poses[key]=global_pose
        return global_pose
    def frame(direction,normal):
        x=direction.normalized()
        z=(normal-x*normal.dot(x)).normalized()
        return Matrix((x,z.cross(x),z)).transposed().to_quaternion()
    bird_pos,bird_rot=world('bird')
    bird_inv=bird_rot.inverted()
    for key,hinge in g.nodes.items():
        if 'vane_kind' not in hinge:
            continue
        side=hinge['vane_side'];i=hinge['vane_index'];kind=hinge['vane_kind']
        p,parent_rot=world(hinge.parent['joint'])
        rest_origin=g.bind[key]-g.bind[hinge.parent['joint']]
        origin=bird_inv@(p+parent_rot@rest_origin-bird_pos)
        ray=Vector(hinge['vane_axis']);length=ray.length
        under=bool(hinge['vane_ventral'])
        # Folded vanes follow the flank in three overlapping courses. The loaded
        # inner wing folds back on itself; binding each plate at its own socket
        # prevents the secondaries on that reversed forearm from pointing up.
        if kind=='primary':
            t=i/9
            angle=45+14*t+8*max(0,origin.y-.45)
            tip_width=.83+.16*t
        elif kind=='secondary':
            t=i/12
            angle=48+7*t+15*max(-.45,min(1.0,origin.y-.37))
            tip_width=.86+.18*t
        else:
            station=min(1.0,max(0.0,(abs(g.bind[key].x)-.80)/3.30))
            angle=45+14*station+11*max(-.5,min(.9,origin.y-.35))
            tip_width=(.91 if under else 1.00)+.13*station
        # The skeleton holds the roots away from the thorax. As the body tapers,
        # the tips nest further inboard; tiny index variation preserves the lap.
        dx=max(-.34,min(.22,(tip_width-abs(origin.x))/max(.20,length)))
        yz=sqrt(max(0,1-dx*dx))
        target=Vector((side*dx,yz*cos(radians(angle)),-yz*sin(radians(angle))))
        outward=Vector((side,-.15+.08*min(1,max(-1,origin.y)),.17))
        # Ventral and dorsal tracts retain their physical face orientation here.
        desired=frame(target,outward)@frame(ray,Vector(hinge['vane_normal'])).inverted()
        q=parent_rot.inverted()@bird_rot@desired
        if q.w<0:q.negate()
        rotations[key]=q.normalized()
    return rotations

def build(g):
    for side in (-1,1):
        wing=Wing(g,side)
        wing.flight_stock()
        wing.mechanisms()
