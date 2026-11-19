"""Head, breast, dorsal mantle and frame for the articulated Aquila.

Coordinates are in Blender bind space. Feather seats follow a measured section
envelope. Their ridged visible skins, returns and undersides are closed meshes.
"""
from math import sin, cos, pi, sqrt
from head_enamel import map_plate


TAU = 2.0 * pi
Z = (0.0, 0.0, 1.0)
LEFT = -1
RIGHT = 1

# z, y center, lateral radius, forward radius, aft radius
TORSO = [
    (-.91, .42, .17, .22, .29), (-.77, .39, .37, .40, .49),
    (-.56, .31, .54, .54, .64), (-.28, .19, .68, .66, .77),
    (.02, .06, .765, .73, .765), (.30, -.014, .798, .76, .73),
    (.53, -.066, .782, .695, .67), (.71, -.14, .68, .61, .59),
    (.88, -.24, .475, .47, .46), (.99, -.34, .285, .33, .32),
]
NECK = [
    (.43, -.26, .34, .32, .32), (.64, -.34, .465, .443, .45),
    (.84, -.445, .496, .465, .505), (1.015, -.53, .464, .47, .53),
    (1.205, -.66, .426, .47, .555), (1.40, -.76, .382, .48, .51),
]
# y, center z, lateral radius, dorsal radius, throat radius
SKULL = [
    (-1.50, 1.296, .106, .058, .076), (-1.39, 1.321, .211, .102, .116),
    (-1.225, 1.363, .324, .176, .155), (-1.035, 1.400, .400, .219, .202),
    (-.817, 1.413, .452, .263, .241), (-.592, 1.385, .453, .288, .264),
    (-.382, 1.323, .398, .279, .242), (-.19, 1.259, .313, .229, .203),
    (-.055, 1.213, .194, .149, .145), (.055, 1.196, .07, .055, .064),
]

def add(a,b): return tuple(x+y for x,y in zip(a,b))
def sub(a,b): return tuple(x-y for x,y in zip(a,b))
def mul(a,k): return tuple(x*k for x in a)
def dot(a,b): return sum(x*y for x,y in zip(a,b))
def cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit(a): return mul(a,1.0/max(1e-9,sqrt(dot(a,a))))
def lerp(a,b,t): return (1.0-t)*a+t*b
def mix(a,b,t): return tuple(lerp(x,y,t) for x,y in zip(a,b))
def offset(p,u,k): return add(p,mul(u,k))

def interp(rows,x):
    if x<=rows[0][0]: return rows[0][1:]
    for a,b in zip(rows,rows[1:]):
        if x<=b[0]:
            return mix(a[1:],b[1:],(x-a[0])/(b[0]-a[0]))
    return rows[-1][1:]

def section(rows,z,a):
    yc,rx,rf,ra=interp(rows,z)
    return (rx*sin(a),yc-(rf if cos(a)>=0 else ra)*cos(a),z)

def section_normal(rows,z,a):
    along=sub(section(rows,z+.006,a),section(rows,z-.006,a))
    rim=sub(section(rows,z,a+.005),section(rows,z,a-.005))
    if dot(along,along)<1e-8: along=Z
    return unit(cross(rim,along))

def skull(y,a):
    zc,w,rt,rb=interp(SKULL,y)
    return (sin(a)*w,y,zc+cos(a)*(rt if cos(a)>=0 else rb))

def skull_normal(y,a):
    u=sub(skull(y+.007,a),skull(y-.007,a))
    v=sub(skull(y,a+.006),skull(y,a-.006))
    return unit(cross(v,u))

def closed_loft(g,name,parent,rings,material,asm,shell=True,smooth=True,explode=None):
    n=len(rings[0]); verts=[p for ring in rings for p in ring]; faces=[]
    # For any sweep direction, choose winding from the section centers.
    center=tuple(sum(p[c] for p in rings[0])/n for c in range(3))
    nrm=cross(sub(rings[0][1],rings[0][0]),sub(rings[1][0],rings[0][0]))
    reverse=dot(nrm,sub(rings[0][0],center))<0
    for i in range(len(rings)-1):
        for j in range(n):
            idx=i*n+j; k=i*n+(j+1)%n
            faces.append((idx,k,k+n,idx+n))
    faces.extend([tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))])
    if reverse: faces=[tuple(reversed(f)) for f in faces]
    return g.mesh(name,parent,verts,faces,material,asm=asm,shell=shell,smooth=smooth,explode=explode)

def plated_feather(g,name,parent,surface,normal,start,end,center,turn,half_width,mat,asm,
                   lift=.028,thick=.020,quill=.013,widths=None):
    # Narrow turned hem and chevron on the face. The surfaces along the rim
    # are shared with the underside, including the clipped tip and root cap.
    if widths is None:
        if asm==1 or name.startswith(('Gorget','Cheek')):
            widths=((0,.51),(.15,.86),(.32,1),(.51,.945),(.72,.701),(.877,.409),(1,.025))
        else:
            widths=((0,.52),(.105,.77),(.245,.995),(.43,1),(.60,.86),
                    (.75,.67),(.87,.46),(.947,.245),(1,.028))
    across=(-1,-.932,-.50,-.085,0,.105,.57,.945,1)
    crown=(.02,.19,.51,.69,1,.62,.41,.15,.018)
    head_plate = parent == 'head' and mat in ('ivory','bone')
    if head_plate:
        # Raised central fold and two narrow shoulders catch light during a turn.
        across=(-1,-.94,-.59,-.26,-.090,-.045,0,.041,.086,.26,.57,.94,1)
        crown=(.018,.18,.47,.60,.62,.54,1.26,.64,.53,.56,.42,.16,.018)
    verts=[]; lower=[]; normals=[]
    for t,span in widths:
        distance=lerp(start,end,t)
        mid=center+turn*(.35*t+.65*t*t)
        for j,(u,bow) in enumerate(zip(across,crown)):
            # A swept center rib and a clipped outside corner vary the
            # planform without turning paired feathers into mirror noise.
            a=mid+half_width*span*u
            q=surface(distance,a); n=normal(distance,a)
            height=(lift*(.30+.70*t)+quill*bow*(.25+.75*sin(pi*(.08+.82*t))))
            verts.append(offset(q,n,height));lower.append(offset(q,n,height-thick-.003*bow))
            normals.append(n)
    m=len(across); k=len(widths); count=len(verts)
    faces=[]; mats=[]; outline={}
    ids=[0,0,0,1,1,0,0,2]
    if mat=='ivory': palette=['ivory','ivory','bone','bone']
    elif mat=='bone': palette=['bone','ivory','bone','bone']
    elif mat=='umber': palette=['umber','umber','bronze','dark']
    elif mat=='dark': palette=['dark','umber','bronze','black']
    else: palette=[mat,mat,'edge','dark']
    palette[0]='plate_'+mat
    if palette[1] in ('bronze','umber','dark','ivory','bone'):
        palette[1]='plate_'+palette[1]
    if head_plate:
        palette=['head_enamel','bone','bone','bone']
        ids=[0]*(m-1)
    for i in range(k-1):
        for j in range(m-1):
            a=i*m+j; f=(a,a+1,a+1+m,a+m)
            if dot(cross(sub(verts[f[1]],verts[a]),sub(verts[f[3]],verts[a])),normals[a])<0:
                f=tuple(reversed(f))
            faces.append(f); mats.append(ids[j])
            faces.append(tuple(v+count for v in reversed(f)));mats.append(3)
            for v,w in zip(f,f[1:]+(f[0],)):
                key=(min(v,w),max(v,w))
                if key in outline: del outline[key]
                else: outline[key]=(v,w)
    for a,b in outline.values(): faces.append((b,a,a+count,b+count));mats.append(2)
    shove=normal(lerp(start,end,.62),center+.5*turn)
    shift=add(mul(shove,.24 if asm==0 else .34),(0,.012,-.038))
    vane=g.mesh(name,parent,verts+lower,faces,palette,face_mats=mats,asm=asm,shell=True,explode=shift,smooth=True)
    # Continuous highlights follow the curved skin while the folded axis
    # and the machined hems retain their defined crease.
    for poly in vane.data.polygons:
        if any(v>=count for v in poly.vertices): poly.use_smooth=False
    for edge in vane.data.edges:
        v,w=edge.vertices
        if v<count and w<count and v%m==w%m and v%m in (1,m//2,m-2):
            edge.use_edge_sharp=True
    if head_plate:
        chart=[(t,.5+.5*u) for t,_ in widths for u in across]
        map_plate(vane,chart+chart,shadow_ivory=mat=='bone')
    else:
        from plume import station_uv
        station_uv(vane.data,m,[t for t,_ in widths],across,repeat=True)
    stamp=sum(ord(c)*(i+1) for i,c in enumerate(name))
    if stamp%(5 if asm==0 else 3)==0 or (name.startswith('Crown') and stamp%3==0):
        u=.31 if stamp%2 else -.34
        t=.77; station=lerp(start,end,t); angle=center+turn*(.35*t+.65*t*t)+half_width*.66*u
        norm=normal(station,angle)
        seat=offset(surface(station,angle),norm,lift*(.30+.70*t)+quill*.47+.001)
        radius=.0089 if asm==0 else .0129
        g.bolt('Flush rivet | '+name,parent,seat,norm,radius,asm=asm,mat='steel' if asm==0 else 'edge')
    return vane

def line_on_section(rows,z,a,out): return offset(section(rows,z,a),section_normal(rows,z,a),out)

def frame(g):
    # Elliptical rib stations wrap the cavity; rails and saddle tie them into a single frame.
    for i,z in enumerate((-.70,-.49,-.24,.02,.27,.50,.69,.82)):
        angles=[TAU*k/36 for k in range(37)]
        ring=[]
        for a in angles:
            p=section(TORSO,z,a)
            ring.append(offset(p,section_normal(TORSO,z,a),-.103))
        g.tube('Thorax | transverse rib %02d'%i,'core',ring,.033 if i%3 else .047,'gun' if i%2 else 'steel',asm=7,n=8)
        if i%2==0:
            for j in range(10):
                a=TAU*(j+.45)/10
                v=line_on_section(TORSO,z,a,-.115)
                g.bolt('Rib | clamp %02d.%02d'%(i,j),'core',v,section_normal(TORSO,z,a),.026,asm=7,mat='edge')
    for i,a in enumerate((.02,.72,1.42,2.16,2.78,3.5,4.06,4.90,5.54)):
        coords=[line_on_section(TORSO,z,a,-.109) for z in (-.73,-.52,-.29,.03,.32,.57,.73,.84)]
        g.tube('Longeron | %02d'%i,'core',coords,.026 if i%2 else .032,'steel' if i%2 else 'edge',asm=7,n=8)
    g.rod('Thorax | shoulder through-shaft','core',(-.855,-.03,.55),(.855,-.03,.55),.129,'steel',asm=7,n=28)
    g.rod('Thorax | longitudinal power shaft','core',(0,.42,-.72),(0,-.31,.75),.138,'gun',asm=7,n=24)
    for j in range(8):
        a=mix((0,.42,-.72),(0,-.31,.75),.10+j*.11)
        axis=(0,-.445,.897)
        g.ring('Power shaft | heat fin %02d'%j,'core',a,axis,.204 if j%3 else .225,.129,.046,'gun' if j%2 else 'steel',asm=7,n=28)
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        axis=(s,0,0)
        g.rod('Scapula | axle seat '+tag,'core',(s*.59,-.03,.55),(s*.788,-.03,.55),.225,'black',asm=7,n=32)
        for j,(x,ro,ri,d,metal) in enumerate(((.715,.303,.213,.083,'bronze'),(.757,.291,.201,.039,'gun'),(.785,.255,.165,.035,'steel'),(.801,.216,.159,.018,'edge'))):
            g.ring('Shoulder carrier | %s.%d'%(tag,j),'core',(s*x,-.03,.55),axis,ro,ri,d,metal,asm=7,n=36)
        for k in range(8):
            a=TAU*k/8+.10
            g.bolt('Carrier | locking stud %s%02d'%(tag,k),'core',(s*.774,-.03+.262*cos(a),.55+.262*sin(a)),axis,.025,asm=7,mat='steel')
        g.rod('Keel | diagonal strut '+tag,'core',(s*.62,-.09,.43),(s*.21,-.25,-.45),.054,'edge',asm=7)
        g.rod('Mantle | upper cross brace '+tag,'core',(s*.17,.47,.20),(s*.76,.115,.56),.071,'steel',asm=7)
        for j in range(3):
            g.tube('Torso | braided lead %s.%d'%(tag,j),'core',
                [(s*(.17+j*.052),.43,-.58),(s*(.30+.046*j),.55,-.28),(s*(.54+.03*j),.44,.10),(s*(.67+.025*j),.16,.47)],.017,'orange' if j==1 else 'black',asm=7,n=7)
    g.ring('Cervical | rotating sill','core',(0,-.445,.844),(0,-.23,.973),.342,.264,.073,'bronze',asm=7,n=40)
    g.ring('Cervical | thrust race','core',(0,-.453,.887),(0,-.23,.973),.311,.246,.038,'gun',asm=7,n=40)
def mantle(g):
    # The charcoal monocoque is just the thin substrate below the individual
    # metal vanes. Dorsal windows and the central spine sit above it.
    rings=[]
    for row in TORSO:
        z=row[0]
        rings.append([line_on_section(TORSO,z,TAU*k/32,-.041) for k in range(32)])
    closed_loft(g,'Breast | inner fairing','body',rings,'dark',1,smooth=True)
    surface=lambda z,a:section(TORSO,z,a)
    normal=lambda z,a:section_normal(TORSO,z,a)
    # Progress from rectrices toward shoulder so the trailing course tucks
    # under the forward one, like the breast of a raptor.
    courses=[(-.45,-.870,11),(-.205,-.702,13),(.020,-.495,14),
             (.244,-.278,15),(.455,-.060,15),(.657,.139,14),(.843,.358,13)]
    chest_stock=('umber','dark','umber','bronze','umber','dark','umber','umber','dark')
    for row,(start,stop,n) in enumerate(courses):
        for j in range(n):
            a=lerp(-2.13,2.13,(j+(.26 if row%2 else .74))/n)
            # Courses fork at the keel, turn towards the flanks, and overlap
            # the root fasteners of the next course down the breast.
            side=1 if sin(a)>=0 else -1
            sweep=side*(.09+.145*abs(sin(a)))+.019*sin(j*1.51)
            wave=.075*(1-cos(a))+.020*cos(2.3*j+.63*row)
            root=start+.55*wave
            end=stop+wave
            width=(2.13/n)*1.19
            mat=chest_stock[(j+row*3)%len(chest_stock)]
            stand=.048+.006*row
            plated_feather(g,'Breast | contour %d.%02d'%(row+1,j+1),'body',surface,normal,
                          root,end,a,sweep,width,mat,1,lift=stand,thick=.017,quill=.014)
            if row in (4,6) and (j+row)%3==0:
                z=lerp(root,end,.24);ang=a+sweep*.116
                g.bolt('Scapular | locking rivet %d.%d'%(row,j),'body',line_on_section(TORSO,z,ang,stand*.47+.012),
                       normal(z,ang),.013,asm=1,mat='bronze')
    # Paired elongate scapulars. The negative space between the two sheets
    # retains a useful view of the articulated spine.
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        for row,(start,end) in enumerate(((-.34,-.85),(-.047,-.65),(.23,-.38),(.48,-.118),(.72,.14),(.885,.355))):
            for j in range(3):
                a=s*(2.20+j*.287+(.096 if row%2 else -.027))
                sweep=s*(.184+.028*j)
                mat=('umber','dark','umber','bronze','umber')[(2*row+j)%5]
                plated_feather(g,'Mantle | scapular %s%d.%d'%(tag,row,j),'body',surface,normal,
                              start-.038*j,end+.043*j,a,sweep,.198,mat,1,
                              lift=.049+.007*row,thick=.017,quill=.015)
        # A row of pointed shoulder coverts overlapping the skirts of the shaft
        # sockets. Their outside edges cant away, showing the metal underside.
        for j in range(3):
            a=s*(1.40+.245*j)
            plated_feather(g,'Mantle | shoulder covert %s.%d'%(tag,j),'body',surface,normal,
                          .887-.023*j,.504-.051*j,a,s*(.32+.024*j),.175,'umber' if j!=2 else 'dark',1,
                          lift=.112-.005*j,thick=.018,quill=.018)
    # Separate sternum plates give the underside a keel and split the rows.
    for j in range(6):
        plated_feather(g,'Sternum | sternal lap %d'%j,'body',surface,normal,
                      -.417+.216*j,-.796+.215*j,.032*(-1)**j,.018*(-1)**j,.085 if j else .060,'dark',1,
                      lift=.067+.006*j,thick=.016,quill=.016)
    # The dorsal channel connects the shoulder yoke and tail fork.
    def back(x,z):
        yc,rx,rf,ra=interp(TORSO,z)
        return yc+ra*sqrt(max(.005,1.0-(x/rx)**2))
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        rail=[(s*w,back(s*w,z)+.025,z) for z,w in
              ((-.78,.042),(-.59,.079),(-.32,.098),(.0,.109),(.30,.105),(.55,.099),(.74,.075))]
        g.tube('Spine | bronze runner '+tag,'body',rail,.015,'bronze',asm=1,n=9)
        g.tube('Spine | oil return '+tag,'core',
               [(x*.83,y-.006,z) for x,y,z in rail],.013,'black',asm=7,n=7)
    for i,zc in enumerate((-.61,-.388,-.151,.085,.315,.532,.723)):
        # Pierced beam. The aperture passes entirely through the ring.
        w=(.095+.010*sin((i+1)*pi/7))*(.78 if i==0 else 1)
        hz=.141 if i<5 else .133
        outer=[(-.65,-.52),(-.13,-.98),(.13,-.98),(.65,-.52),
               (1,.27),(.59,.91),(-.59,.91),(-1,.27)]
        slot=.37 if i in (2,4,6) else .14
        inner=[(-slot*.72,-.15),(-slot*.2,-.42),(slot*.2,-.42),(slot*.72,-.15),
               (slot,.25),(slot*.50,.44),(-slot*.50,.44),(-slot,.25)]
        verts=[]
        for rim,lift in ((outer,.055),(inner,.061),(inner,.032),(outer,.026)):
            for a,t in rim:
                x=a*w; z=zc+hz*t;verts.append((x,back(x,z)+lift,z))
        faces=[];mats=[]
        for row,mat in enumerate((0,1,2,1)):
            for j in range(8):
                nxt=(j+1)%8;k=(row+1)%4
                faces.append((row*8+nxt,row*8+j,k*8+j,k*8+nxt));mats.append(mat)
        g.mesh('Dorsal | fenestrated saddle %02d'%i,'body',verts,faces,
               ['umber' if i%2 else 'gun','bronze','black'],face_mats=mats,asm=1,shell=True,explode=(0,.32,.035))
        for s in (LEFT,RIGHT):
            x=s*w*.715;z=zc+.036
            g.bolt('Dorsal | captive fastener %02d.%s'%(i,'L' if s<0 else 'R'),'body',
                   (x,back(x,z)+.058,z),(0,1,.16),.012,asm=1,mat='gun')
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        # Interlocking nuchal yokes carry loads between the neck and
        # scapulae. The inner window has its own lip, sidewalls and return.
        outside=[(.02,.17),(.15,.025),(.69,.04),(.965,.23),(.99,.65),(.81,.95),(.47,1),(.055,.854)]
        aperture=[(.318,.433),(.382,.344),(.524,.349),(.624,.428),(.635,.536),(.536,.612),(.421,.592),(.325,.518)]
        def yoke(u,v,lift):
            a=s*lerp(pi-.070,2.24,u)
            z=lerp(.915,.705,v)-.035*u+.015*sin(pi*u)
            return line_on_section(TORSO,z,a,lift)
        rings=[outside,aperture,aperture,outside];raises=(.049,.061,.028,.014)
        vs=[yoke(u,v,h) for ring,h in zip(rings,raises) for u,v in ring];fs=[];mi=[]
        for k in range(4):
            for j in range(8):
                j1=(j+1)%8;k1=(k+1)%4
                fs.append((k*8+j,k*8+j1,k1*8+j1,k1*8+j));mi.append((0,1,2,1)[k])
        g.mesh('Nuchal | vented upper yoke '+tag,'body',vs,fs,['umber','bronze','black'],face_mats=mi,asm=1,shell=True,explode=(s*.13,.24,.095))
        for j,(u,v) in enumerate(((.17,.19),(.80,.71),(.18,.74))):
            z=lerp(.915,.705,v)-.035*u+.015*sin(pi*u);a=s*lerp(pi-.070,2.24,u)
            g.bolt('Nuchal | yoke retainer %s%d'%(tag,j),'body',yoke(u,v,.053),normal(z,a),.013,asm=1,mat='gun')
        for j in range(3):
            g.rod('Nuchal | strainer %s%d'%(tag,j),'core',
                  yoke(.35+j*.108,.275,.019),yoke(.35+j*.108,.72,.019),.008,'bronze',asm=7,n=7)
        # Layered, three-point wing buttresses visible from above and behind.
        p=(s*.135,back(.135,.62)+.075,.62);q=(s*.67,.32,.545);r=(s*.28,.60,.245)
        for k,(a,b) in enumerate(((p,q),(q,r),(r,p))):
            g.rod('Shoulder | dorsal yoke %s.%d'%(tag,k),'body',a,b,.041 if k==0 else .032,'bronze' if k!=1 else 'gun',asm=1,n=10)
        g.ring('Mantle | hinge cap '+tag,'body',q,(s*.46,.85,.24),.085,.043,.052,'steel',asm=1,n=24)

def neck_and_crown(g):
    rings=[[skull(row[0],TAU*k/36) for k in range(36)] for row in SKULL]
    closed_loft(g,'Cranium | ivory ceramic case','head',rings,'bone',0,smooth=True)
    rings=[[offset(section(NECK,row[0],TAU*k/28),section_normal(NECK,row[0],TAU*k/28),-.043)
            for k in range(28)] for row in NECK]
    closed_loft(g,'Throat | undercollar','head',rings,'bone',0,smooth=True)
    ns=lambda z,a:section(NECK,z,a)
    nn=lambda z,a:section_normal(NECK,z,a)
    # Long nape scales at the back, pointed gorget at the front; each is
    # curved around the neck and has a separate rolled edge and underside.
    for row,(z0,n) in enumerate(((.839,16),(.984,18),(1.133,18),(1.290,16))):
        for j in range(n):
            a=TAU*(j+(.49 if row%2 else .02))/n
            s=1 if sin(a)>=0 else -1
            swing=s*(.105+.125*abs(sin(a)))
            length=.265+.060*(.5-.5*cos(a))+.030*cos(j*2.34+row)
            root=z0+.021*cos(a*2+.55*row)
            mat='bone' if row<2 and (j+2*row)%7==0 else 'ivory'
            plated_feather(g,'Gorget | neck vane %d.%02d'%(row+1,j+1),'head',ns,nn,
                root,root-length,a,swing,pi/n*1.22,mat,0,lift=.060+.019*row,thick=.021,quill=.021)
    # Cranial vanes from forehead across the crown to the nape, opening
    # laterally at the cheek to leave a purposeful orbital window.
    for row,(y0,y1,n,arc) in enumerate(((-.80,.003,10,2.28),(-1.00,-.338,10,1.99),
                                       (-1.198,-.604,8,1.40),(-1.333,-.870,7,.862))):
        for j in range(n):
            a=-arc+(j+.5)*arc*2/n
            if y0<-.86 and abs(a)>1.16: continue
            swing=(1 if a>=0 else -1)*(.045+.23*abs(sin(a)))
            plated_feather(g,'Crown | sagittal vane %d.%02d'%(row+1,j+1),'head',skull,skull_normal,
                          y0,y1+.04*cos(j*2.1),a,swing,arc/n*1.21,'ivory',0,
                          lift=.045+.027*row,thick=.021,quill=.020)
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        cheek_fan=[(-1.29,-.866,2.16,.13),(-1.185,-.718,2.28,.14),(-1.17,-.695,2.01,.23),
                   (-1.034,-.562,2.25,.18),(-.980,-.482,1.91,.25),(-.934,-.463,1.65,.28),
                   (-.802,-.308,1.92,.31),(-.750,-.235,1.62,.32)]
        for i,(y0,y1,a,b) in enumerate(cheek_fan):
            plated_feather(g,'Cheek | malar vane %s.%d'%(tag,i),'head',skull,skull_normal,
                          y0,y1,s*a,s*b,.157,'ivory',0,lift=.055+.007*(i%3),thick=.015,quill=.012)

def bill(g):
    # An upper maxilla with broad cere, convex roof, thin tomial edge and
    # a recurved last segment. Lower mandibular sections have a separate bite line.
    upper=[
        (-1.145,.253,1.486,1.226),(-1.29,.255,1.481,1.225),
        (-1.424,.226,1.464,1.229),(-1.557,.192,1.441,1.226),
        (-1.69,.158,1.402,1.214),(-1.792,.126,1.354,1.191),
        (-1.865,.096,1.288,1.138),(-1.899,.070,1.201,1.062),
        (-1.902,.043,1.117,.995),(-1.879,.020,1.031,.963),(-1.842,.002,.972,.952)]
    ring=[(0,1),(.36,.94),(.65,.79),(.85,.59),(.99,.30),(1,.11),
          (.95,.015),(.69,-.025),(0,-.067),(-.69,-.025),(-.95,.015),
          (-1,.11),(-.99,.30),(-.85,.59),(-.65,.79),(-.36,.94)]
    verts=[];faces=[];ids=[];n=len(ring)
    for y,w,top,low in upper:
        for x,t in ring: verts.append((w*x,y,lerp(low,top,t)))
    for k in range(len(upper)-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n
            faces.append((a,b,b+n,a+n));ids.append(1 if 6<=j<=9 else 0)
    faces.extend((tuple(reversed(range(n))),tuple(range(len(verts)-n,len(verts)))));ids.extend((0,0))
    g.mesh('Rostrum | hooked upper mandible','head',verts,[tuple(reversed(f)) for f in faces],['gold','edge'],face_mats=ids,
           asm=0,shell=True,smooth=True,explode=(0,-.36,.072))
    lower=[(-1.148,.212,1.217,1.084),(-1.325,.220,1.214,1.105),
           (-1.493,.178,1.216,1.131),(-1.641,.130,1.209,1.143),
           (-1.755,.078,1.185,1.131),(-1.825,.038,1.16,1.122),(-1.856,.009,1.14,1.125)]
    rs=[]
    for y,w,top,low in lower:
        rs.append([(w*x,y,lerp(low,top,t)) for x,t in
                   ((0,.99),(.67,1),(.94,.85),(1,.61),(.83,.34),(.47,.10),(0,0),
                    (-.47,.10),(-.83,.34),(-1,.61),(-.94,.85),(-.67,1))])
    closed_loft(g,'Rostrum | lower mandible','head',rs,'gold',0,explode=(0,-.19,-.16))
    for s,tag in [(LEFT,'L'),(RIGHT,'R')]:
        # Dark lining continues the opening toward the corner of the mouth.
        g.tube('Bill | tomial seam '+tag,'head',[(s*.253,-1.14,1.217),(s*.248,-1.28,1.215),
               (s*.22,-1.423,1.218),(s*.185,-1.557,1.216),(s*.145,-1.69,1.208),
               (s*.095,-1.791,1.181)],.0068,'black',asm=0,n=7,explode=(0,-.16,-.01))
        for i,(x,y,z) in enumerate(((.263,-1.166,1.183),(.318,-1.106,1.210))):
            g.bolt('Rostrum | hinge pin %s%d'%(tag,i),'head',(s*x,y,z),(s*.95,-.24,-.1),.015,asm=0,mat='edge')
        na=unit((s*.88,-.30,.37)); horiz=unit((.31*s,.951,0)); up=unit(cross(na,horiz))
        if up[2]<0: up=mul(up,-1)
        center=(s*.199,-1.469,1.377)
        outer=[(.050,.023,.007),(.043,.019,.014),(.034,.0125,.015),(.031,.011,.003)]
        rows=[]
        for rx,rz,push in outer:
            rows.append([add(offset(center,na,push),add(mul(horiz,rx*cos(t*TAU/20)),mul(up,rz*sin(t*TAU/20)))) for t in range(20)])
        verts=[v for row in rows for v in row];faces=[];mi=[]
        for k in range(3):
            for z in range(20):
                j=(z+1)%20
                f=(k*20+z,k*20+j,(k+1)*20+j,(k+1)*20+z)
                faces.append(f if s>0 else tuple(reversed(f)));mi.append((0,0,1)[k])
        f=tuple(range(60,80))
        faces.append(f if s>0 else tuple(reversed(f)));mi.append(1)
        # Close the narrow, turned return below the dark recessed socket.
        verts.extend(offset(p,na,-.010) for p in rows[0])
        for j in range(20):
            k=(j+1)%20; rim=(k,j,80+j,80+k)
            faces.append(rim if s>0 else tuple(reversed(rim)));mi.append(0)
        cap=tuple(reversed(range(80,100)));faces.append(cap if s>0 else tuple(reversed(cap)));mi.append(0)
        g.mesh('Cere | inset naris '+tag,'head',verts,faces,['gold','black'],face_mats=mi,asm=0,smooth=True,explode=(s*.12,-.18,.05))
def visor(g,tag,s,c,n,t):
    group='lid.'+tag
    g.joint(group,'head',c)
    angles=(-1.24,-.99,-.70,-.39,0,.39,.70,.99,1.24)
    lat=(.65,.68,.715,.85,1.07,1.31,1.58,1.86,2.17,2.42,2.62)
    R=.150; verts=[]
    for radius in (R,R-.011):
        for phi in lat:
            for ang in angles:
                arm=add(mul(n,cos(phi)),mul(Z,sin(phi)))
                verts.append(add(c,add(mul(t,radius*sin(ang)),mul(arm,radius*cos(ang)))))
    cols=len(angles); rows=len(lat); ct=cols*rows; faces=[]; mi=[]; bounds={}
    for k in range(rows-1):
        for j in range(cols-1):
            a=k*cols+j; f=(a,a+1,a+1+cols,a+cols)
            if dot(cross(sub(verts[a+1],verts[a]),sub(verts[a+cols],verts[a])),sub(verts[a],c))<0:
                f=tuple(reversed(f))
            faces.append(f);mi.append(2 if k==0 else 1 if k==1 else 0)
            faces.append(tuple(q+ct for q in reversed(f)));mi.append(3)
            for e,v in zip(f,f[1:]+(f[0],)):
                key=(min(e,v),max(e,v))
                if key in bounds:del bounds[key]
                else:bounds[key]=(e,v)
    for a,b in bounds.values():faces.append((b,a,a+ct,b+ct));mi.append(1)
    lid=g.mesh('Optics | articulated upper lid '+tag,group,verts,faces,['head_enamel','bone','gun','black'],asm=0,
               shell=True,face_mats=mi,smooth=True,explode=(s*.18,-.07,.11))
    chart=[(.20+.60*(ang-angles[0])/(angles[-1]-angles[0]), .53+.36*(phi-lat[0])/(lat[-1]-lat[0]))
           for phi in lat for ang in angles]
    map_plate(lid,chart+chart)

def optics(g):
    for s,tag in ((LEFT,'L'),(RIGHT,'R')):
        n=unit((s*.882666,-.47,0));t=unit((s*.47,.882666,0)); c=(s*.367,-1.062,1.368)
        shift=(s*.24,-.073,.018)
        for label,dist,ro,ri,d,mat in (
            ('orbital seat',-.001,.155,.102,.060,'black'),
            ('machined orbit',.020,.145,.108,.028,'gun'),
            ('brass seat',.036,.134,.111,.018,'edge'),
            ('ocular gasket',.047,.120,.103,.017,'black')):
            g.ring('Optics | '+label+' '+tag,'head',offset(c,n,dist),n,ro,ri,d,mat,
                   asm=0,n=40,explode=shift)
        rings=[(.001,.125,0),(.032,.123,0),(.044,.119,0),(.050,.117,1),
               (.058,.114,2),(.073,.109,2),(.086,.101,2),(.097,.092,3),
               (.104,.084,1),(.109,.076,1),(.115,.056,4)]
        count=72; verts=[]; faces=[]; mi=[]
        for ri,(r,z,band) in enumerate(rings):
            for j in range(count):
                a=TAU*j/count;flute=.0018*(j%2) if 4<=ri<8 else 0
                verts.append(add(offset(c,n,z+flute),add(mul(t,r*cos(a)),mul(Z,r*sin(a)))))
        for k in range(len(rings)-1):
            for j in range(count):
                b=k*count+j;bn=k*count+(j+1)%count;f=(b,b+count,bn+count,bn)
                if s<0:f=tuple(reversed(f))
                faces.append(f); band=rings[k][2]
                if band==2: band=(2,2,3,2,0,2,2,1,2,2,3,2,2,2,3,2,2)[j%17]
                mi.append(band)
        cap=tuple(range(count));faces.append(cap if s>0 else tuple(reversed(cap)));mi.append(0)
        back=tuple(range((len(rings)-1)*count,len(verts)))
        faces.append(tuple(reversed(back)) if s>0 else back);mi.append(4)
        g.mesh('Optics | fluted iris and pupil '+tag,'head',verts,faces,
               ['lens','edge','amber','gold','black'],face_mats=mi,asm=0,smooth=True,explode=shift)
        # A single small polished return on the lens reads at orbit distance.
        glint=add(offset(c,n,.120),add(mul(t,-.022),mul(Z,.031)))
        g.ball('Optics | corneal highlight '+tag,'head',glint,(.0065,.0065,.0065),'silver',asm=0,explode=shift)
        visor(g,tag,s,c,n,t)
        # A shaped overhanging supraorbital ledge creates the eagle's gaze.
        stations=[
            (-1.45,.090,.183,1.321,1.424),(-1.335,.102,.315,1.349,1.480),
            (-1.220,.126,.431,1.391,1.524),(-1.100,.144,.522,1.415,1.550),
            (-.974,.180,.543,1.457,1.600),(-.841,.207,.484,1.509,1.639),
            (-.691,.235,.446,1.527,1.631),(-.570,.296,.392,1.549,1.603)]
        rs=[]
        for y,inner,outer,low,top in stations:
            width=outer-inner
            low-=.016;top-=.005
            rs.append([(s*lerp(inner,outer,u),y,lerp(low,top,h)) for u,h in
                       ((0,.83),(.30,1),(.67,.78),(.91,.33),(1,.10),(.97,0),
                        (.85,-.027),(.62,.22),(.18,.51),(0,.52))])
        brow=closed_loft(g,'Brow | overhanging supraorbital shield '+tag,'head',rs,'head_enamel',0,
                         smooth=True,explode=(s*.185,-.038,.20))
        # Sweep the enamel along the orbit with the returned edge under the brow.
        brow_co=(.36,.46,.62,.78,.91,.97,.89,.73,.46,.36)
        map_plate(brow,[((y-stations[0][0])/(stations[-1][0]-stations[0][0]),v)
                        for y,*_ in stations for v in brow_co])
        cheek=[
            (-1.251,.298,.346,1.293),(-1.157,.374,.427,1.268),
            (-1.022,.401,.488,1.256),(-.865,.404,.485,1.276),
            (-.694,.386,.463,1.303),(-.475,.326,.409,1.323)]
        rs=[]
        for y,i,o,z in cheek:
            rs.append([(s*lerp(i,o,u),y,z+dz) for u,dz in ((0,.021),(.41,.031),(.93,.016),(1,-.002),(.65,-.033),(.11,-.020))])
        closed_loft(g,'Orbital | lower cheek rail '+tag,'head',rs,'bone',0,smooth=True,explode=(s*.14,.015,-.05))
        for j,(yy,xx,z) in enumerate(((-.778,.442,1.503),(-.557,.408,1.423))):
            g.bolt('Cranial | flush retainer %s.%d'%(tag,j),'head',(s*xx,yy,z),(s*.91,.11,.39),.014,asm=0,mat='steel')

def build(g):
    frame(g)
    mantle(g)
    neck_and_crown(g)
    bill(g)
    optics(g)
