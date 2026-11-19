"""Landing gear, tail and museum perch in the shared neutral coordinate frame."""
from math import cos, sin, pi, sqrt, atan2, exp

TAU = 2 * pi


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(v, s):
    return tuple(x * s for x in v)


def lerp(a, b, t):
    return add(a, mul(sub(b, a), t))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def unit(v):
    return mul(v, 1 / max(1e-12, sqrt(dot(v, v))))


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0])


def local_point(p, q, a, n, b):
    return add(p, add(mul(q, a), mul(n, b)))


def shell_rings(g, name, parent, rows, mats, surface, asm, travel, shell, smooth):
    """Build a closed strip of transverse rings, keeping bevels and edge finishes."""
    width = len(rows[0])
    vertices = [p for ring in rows for p in ring]
    faces = []
    indices = []
    for i in range(len(rows) - 1):
        base = i * width
        for j in range(width):
            k = (j + 1) % width
            faces.append((base+j, base+k, base+width+k, base+width+j))
            indices.append(surface(i, j))
    faces.append(tuple(range(width - 1, -1, -1)))
    last = width * (len(rows)-1)
    faces.append(tuple(last+j for j in range(width)))
    indices.extend((0, 0))
    return g.mesh(name, parent, vertices, faces, mats, asm=asm, shell=shell,
                  explode=travel, face_mats=indices, smooth=smooth)


# Bent sheet with two folded returns, a raised dorsal quill and a separate ventral keel.
# Width is half the total width of the blank.
def tail_blade(g, name, parent, a, b, width, thickness, offset, camber, primary=False):
    direction = unit(sub(b, a))
    across = unit((direction[1], -direction[0], 0))
    normal = unit(cross(across, direction))
    hand = -1 if b[0] < 0 else 1
    if hand == -1:
        across = mul(across, -1)
    if primary:
        stations = [(0,.29),(.055,.50),(.14,.62),(.26,.79),(.42,.95),
                    (.59,1),(.73,.98),(.82,.91),(.881,.81),(.900,.76),
                    (.925,.73),(.956,.57),(.983,.36),(1,.045)]
    else:
        stations = [(0,.23),(.12,.63),(.31,.96),(.49,1),
                    (.69,.88),(.85,.60),(.955,.30),(1,.025)]
    # Ring traverses dorsal surface first and returns along the underside.
    profile = [(-1,-.19),(-.97,.04),(-.55,.20),(-.13,.31),
               (-.055,.67),(.018,.78),(.088,.33),(.48,.23),(.95,.06),
               (1,-.12),(.966,-.26),(.38,-.34),(.082,-.39),
               (.015,-.72),(-.054,-.59),(-.12,-.36),(-.69,-.30)]
    rows = []
    for t, apparent_width in stations:
        center = lerp(a, b, t)
        arc = sin(pi*t)
        center = add(center, (hand*.034*arc,0,camber*arc))
        h = thickness * (.48 + .52 * sin(pi*(.09+.80*t))) * (1 - .66*t**4)
        row = []
        for u, v in profile:
            breadth = width * apparent_width
            # The edge facing the next vane is the narrower face of the stamping.
            asymmetry = .92 if u < 0 else 1.03
            loss = 0
            if primary and u > .80:
                loss = .085*exp(-((t-.90)/.018)**2)
            lateral = breadth * u * (asymmetry-loss)
            roll = hand * .046 * (abs(b[0])+.14) * arc * u
            row.append(local_point(center, across, lateral, normal, v*h + roll))
        rows.append(row)

    def finish(i,j):
        if j in (0,8,9):
            return 2 if i <= 2 and primary else 1
        if j in (13,14):
            return 0 if not primary else 1
        return 0 if j < 9 else 1

    blade=shell_rings(g, name, parent, rows, ('plate_ivory','plate_bone','silver'), finish, 5, offset, True, True)
    from plume import station_uv
    station_uv(blade.data,len(profile),[t for t,_ in stations],[u for u,_ in profile])
    return blade


def tail_unit(g):
    axle = (0,.81,-.61)
    g.rod('Tail cross shaft','tail',(-.40,.81,-.61),(.40,.81,-.61),
          .07,'gun',asm=5,n=24,explode=(0,.24,.03))
    # Saddle and paired lower fairings cover the rectrix roots above and below the axle.
    for side in (-1,1):
        x = side*.33
        g.ring('Caudal yaw bearing','tail',(x,.81,-.61),(1,0,0),
               .115,.061,.075,'bronze',asm=5,n=24,explode=(side*.17,.14,0))
        g.ring('Tail bearing race','tail',(x+side*.042,.81,-.61),(1,0,0),
               .088,.05,.023,'silver',asm=5,n=20)
        g.bolt('Caudal bearing cap','tail',(x+side*.059,.81,-.61),(side,0,0),
               .047,asm=5,mat='gun')
    sections = [(.66,.155,-.635,.097),(.74,.25,-.651,.125),(.845,.345,-.671,.123),
                (.99,.327,-.706,.093),(1.10,.22,-.752,.068),(1.17,.105,-.78,.03)]
    rows=[]
    rim=[(-1,0),(-.93,.46),(-.61,.86),(0,1),(.61,.86),(.93,.46),(1,0),
         (.91,-.55),(.54,-.90),(0,-1),(-.54,-.90),(-.91,-.55)]
    for y,w,z,h in sections:
        rows.append([(u*w,y,z+h*v) for u,v in rim])
    shell_rings(g,'Rectrix carrier / enclosed saddle','tail',rows,('gun','bronze','edge'),
                lambda i,j: 2 if i==1 and j in (1,4,7,10) else (1 if j<6 else 0),
                5,(0,.24,.07),False,True)
    for i in range(12):
        u = (2*i - 11)/11
        au = abs(u)
        side = -1 if u<0 else 1
        joint = f'tail.vane.{i:02d}'
        root=(.265*u, .803+.048*au, -.697-.039*au + .009*(i%2))
        tip=(.87*u, 2.59 - .26*au**1.72, -1.27 + .10*au**1.6)
        tip = add(tip,(0,.018*cos(1.75*i),.009*sin(i*1.34)))
        g.joint(joint,'tail',root)
        width=.152-.018*au
        travel=(.43*u,.34+.04*(1-au),-.065-.06*au)
        tail_blade(g,f'Rectrix {i+1:02d} / hemmed shell',joint,root,tip,width,
                   .071-.009*au,travel,.055+.025*au,True)
        # Swaged mounting pad, masked in assembled views by the upper/lower covert tiers.
        pivot=(root[0],root[1]+.065,root[2]+.005)
        g.rod('Rectrix foot washer',joint,
              add(pivot,(0,0,-.033)),add(pivot,(0,0,.034)),
              .049,'gun',asm=5,n=14,explode=(side*.05,.16,.06))
        g.bolt('Rectrix barrel pin',joint,add(pivot,(0,0,.037)),(0,0,1),
               .030,asm=5,mat='edge')
        # Graduated rows cover the proximal shaft from both inspection directions.
        for back, u0, t1, w, dz in ((True,.055,.65,.128,.050),
                                    (False,.070,.55,.121,-.058)):
            p=add(lerp(root,tip,u0),(-u*.017,0,dz))
            q=add(lerp(root,tip,t1),(-u*.03,.022*(i%2),dz))
            tail_blade(g,('Upper' if back else 'Under')+' rectrix covert',
                       joint,p,q,w,.049,
                       (travel[0]*.87,.26,.15 if back else -.17),.034)
        if i in (0,3,6,9,11):
            g.bolt('Tail keeper screw',joint,add(lerp(root,tip,.29),(0,0,.088)),
                   (0,.26,.965),.018,asm=5,mat='edge')
    # The upper and lower rump overlap the tail hinge when the fan closes.
    for dorsal in (True,False):
        dz=.105 if dorsal else -.11
        for i in range(7):
            u=(i-3)/3
            a=(.225*u,.678+.032*abs(u),-.636+dz)
            b=(.43*u,1.43-.155*abs(u),-.895+dz+.01*(i%2))
            tail_blade(g,('Dorsal' if dorsal else 'Ventral')+' rump tile',
                       'tail',a,b,.117,.056,(.16*u,.22,dz*1.4),.024)


def strut(g,name,parent,a,b,r,mat='steel',asm=6):
    axis=unit(sub(b,a))
    g.rod(name+' socket',parent,a,lerp(a,b,.58),1.11*r,mat,asm=asm,n=20,r2=1.05*r)
    g.rod(name+' retainer',parent,lerp(a,b,.51),lerp(a,b,.61),1.17*r,'gun',asm=asm,n=20)
    g.rod(name+' collar',parent,lerp(a,b,.58),lerp(a,b,.65),1.08*r,'edge',asm=asm,n=20)
    g.rod(name+' piston rod',parent,lerp(a,b,.62),b,.60*r,'silver',asm=asm,n=16)


def journal(g,name,parent,c,side,r,depth):
    axis=(side,0,0)
    p=lambda t:add(c,mul(axis,t))
    g.rod(name+' barrel',parent,p(-.48*depth),p(.48*depth),r,'gun',asm=6,n=20)
    for sign in (-1,1):
        normal=(side*sign,0,0)
        g.ring(name+' outer race',parent,p(sign*.51*depth),normal,
               r*1.03,r*.54,.023,'steel',asm=6,n=22)
        g.ring(name+' spacer',parent,p(sign*(.51*depth+.016)),normal,
               r*.81,r*.53,.017,'edge',asm=6,n=18)
        g.bolt(name+' axle cap',parent,p(sign*(.51*depth+.027)),normal,r*.46,asm=6,mat='gun')


def limb_plate(g,name,parent,a,b,width,thickness,normal,mat,asm=6):
    tangent=unit(sub(b,a))
    v=unit(sub(normal,mul(tangent,dot(normal,tangent))))
    u=unit(cross(tangent,v))
    profile=[(-1,-.04),(-.96,.11),(-.54,.44),(-.14,.61),
             (.08,.65),(.60,.43),(.94,.14),(1,-.03),(.91,-.26),
             (.48,-.37),(0,-.40),(-.57,-.33),(-.94,-.24)]
    rows=[]
    for t,w in ((0,.38),(.08,.78),(.25,.98),(.44,1),(.67,.87),(.82,.62),(.94,.30),(1,.035)):
        center=add(lerp(a,b,t),mul(v,thickness*.28*sin(t*pi)))
        rows.append([local_point(center,u,width*w*s,v,thickness*z) for s,z in profile])
    return shell_rings(g,name,parent,rows,(mat,'edge','dark'),
                       lambda i,j: 1 if j in (0,6,7) and i<6 else (2 if j>=8 else 0),
                       asm,mul(v,.26),True,True)


def leg_unit(g,side):
    label='L' if side<0 else 'R'
    leg='leg.'+label
    shin='hock.'+label
    foot='foot.'+label
    c=lambda x,y,z:(side*x,y,z)
    hip=c(.48,.10,-.46)
    knee=c(.515,-.005,-.77)
    hock=c(.512,.055,-.935)
    ankle=c(.48,-.27,-1.34)
    journal(g,'Hip gearbox',leg,hip,side,.125,.234)
    g.rod('Femoral load shaft',leg,hip,knee,.110,'gun',asm=6,r2=.083,n=16)
    g.rod('Posterior tibial link',leg,knee,hock,.076,'gun',asm=6,r2=.083,n=16)
    journal(g,'Tibial journal',leg,hock,side,.115,.198)
    # Thigh feathers are stamped convex shields; the reverse side also has a metal shell.
    for i in range(8):
        a=TAU*i/8
        v=(cos(a),sin(a),.10)
        root=add(lerp(hip,knee,.06),(cos(a)*.097,sin(a)*.119,0))
        tip=add(lerp(knee,hock,.72),(cos(a)*.12,sin(a)*.14,.039*(i%2)))
        limb_plate(g,'Thigh shield',leg,root,tip,.089,.051,v,
                   ('bronze','umber','dark','bronze')[i%4])
    for i in range(5):
        a=TAU*i/5+.25
        v=(cos(a),sin(a),.04)
        root=add(hip,(.095*cos(a),.116*sin(a),.023))
        tip=add(lerp(hip,knee,.78),(.136*cos(a),.150*sin(a),0))
        limb_plate(g,'Proximal thigh fairing',leg,root,tip,.106,.051,v,'umber')
    # Offset hydraulic jack plus a separate blackened chassis rib make the shin legible edge-on.
    g.rod('Tarsal tie bar',shin,add(hock,c(-.052,.025,0)),
          add(ankle,c(-.052,.018,.006)),.049,'gun',asm=6,n=12,r2=.042)
    strut(g,'Landing jack',shin,add(ankle,c(.027,0,.028)),
          add(hock,c(.028,0,-.02)),.058)
    for shift,mat in ((-.065,'black'),(-.078,'edge')):
        pts=[add(lerp(hock,ankle,t),c(shift,.041+.04*sin(pi*t),-.018))
             for t in (0,.12,.28,.50,.76,.92,1)]
        g.tube('Brake return hose' if mat=='black' else 'Hydraulic feed',shin,pts,
               .012 if mat=='black' else .007,mat,asm=6,n=7)
    top=add(hock,c(.027,-.082,-.028));end=add(ankle,c(.027,-.060,.085))
    limb_plate(g,'Crested tibial guard',shin,top,end,.116,.051,(0,-1,.15),'steel')
    for face in (-1,1):
        n=(side*face*.78,-.58,.17)
        start=add(hock,(side*face*.064,-.044,-.013))
        endplate=add(ankle,(side*face*.057,-.035,.073))
        limb_plate(g,'Rolled tibial side plate',shin,start,endplate,.074,.046,n,'umber' if face<0 else 'bronze')
        g.bolt('Recessed shin stud',shin,add(lerp(start,endplate,.30),mul(n,.021)),n,.016,asm=6,mat='gun')
    for t in (.14,.45):
        p=add(lerp(top,end,t),c(.048,-.018,0))
        g.bolt('Tibial guard countersink',shin,p,(0,-.87,.49),.019,asm=6,mat='gun')
    journal(g,'Ankle trunnion',foot,ankle,side,.101,.181)
    pad=c(.48,-.32,-1.618)
    g.rod('Tarsometatarsus spindle',foot,add(ankle,(0,0,-.043)),pad,
          .063,'gun',asm=6,n=16,r2=.083)
    for t in (.23,.42,.61,.79):
        p=lerp(ankle,pad,t)
        axis=unit(sub(ankle,pad))
        g.rod('Greave band',foot,add(p,mul(axis,-.024)),add(p,mul(axis,.024)),
              .066+t*.020,'gold',asm=6,r2=.072+t*.018,n=18)
    g.ball('Foot palm / bronze casting',foot,pad,(.153,.118,.056),'gold',asm=6)
    g.ball('Metatarsal grip pad',foot,add(pad,(0,0,-.031)),(.125,.100,.022),'black',asm=6)
    for toe in range(4):
        digit(g,side,toe,foot)


def claw(g,name,parent,points,radius,hand):
    # A tapered, keeled falconry hook. Each centreline station follows the return under the bar.
    t0=unit(sub(points[1],points[0]))
    ref=unit(sub((1,0,0),mul(t0,t0[0])))
    rows=[]
    last=len(points)-1
    for i,p in enumerate(points):
        t=i/last
        axis=unit(sub(points[min(last,i+1)],points[max(0,i-1)]))
        ref=unit(sub(ref,mul(axis,dot(ref,axis))))
        v=unit(cross(axis,ref))
        w=radius*(1-t)**.92+.0008
        row=[]
        for j in range(10):
            a=TAU*j/10
            row.append(local_point(p,ref,.77*w*cos(a),v,w*(1.08 if sin(a)>.65 else .82)*sin(a)))
        rows.append(row)
    return shell_rings(g,name,parent,rows,('dark','gun','black'),
                       lambda i,j: 1 if j in (1,2) and i<last-1 else (2 if j in (6,7) else 0),
                       6,(hand*.07,-.10,-.15),False,True)


def bezier(a,b,c,d,t):
    u=1-t
    return tuple(u*u*u*p+3*u*u*t*q+3*u*t*t*r+t*t*t*s for p,q,r,s in zip(a,b,c,d))


def digit(g,side,index,foot):
    label='L' if side<0 else 'R'
    x=.48*side
    # Digit IV is the opposing hallux, set behind and medial to the other three.
    if index==3:
        root=(x-.044*side,-.269,-1.616)
        first=(x-.098*side,-.177,-1.666)
        second=(x-.124*side,-.121,-1.733)
        socket=(x-.133*side,-.103,-1.815)
        bend1=(x-.143*side,-.076,-1.935)
        bend2=(x-.155*side,-.141,-2.017)
        tip=(x-.128*side,-.248,-2.014)
        r=.050
    else:
        lane=(index-1)*side
        root=(x+lane*.081,-.355,-1.614)
        first=(x+lane*.137,-.436+.018*abs(lane),-1.655)
        second=(x+lane*.177,-.505+.012*abs(lane),-1.715)
        socket=(x+lane*.205,-.536+.012*abs(lane),-1.816+.026*abs(lane))
        bend1=(x+lane*.230,-.575+.013*abs(lane),-1.925+.013*abs(lane))
        bend2=(x+lane*.200,-.546+.02*abs(lane),-2.014+.01*abs(lane))
        tip=(x+lane*.139,-.375+.012*abs(lane),-2.018+.019*abs(lane))
        r=.060 if index==1 else .055
    joint=f'toe.{label}.{index+1}'
    g.joint(joint,foot,root)
    # Three gold phalanges have raised collars on each link, with recessed pins at the hinges.
    for i,(a,b) in enumerate(zip((root,first,second),(first,second,socket))):
        start=r*(1.05-.075*i)
        end=r*(.99-.08*i)
        g.rod('Digit phalanx',joint,a,b,start,'gold',asm=6,r2=end,n=14)
        for t in (.12,.74):
            g.rod('Rolled phalanx seam',joint,lerp(a,b,t),lerp(a,b,t+.085),
                  start*.98+.003,'edge',asm=6,r2=start+.002,n=14)
        if i<2:
            axis=(1,0,0)
            g.rod('Phalange hinge',joint,add(b,(-end*.83,0,0)),add(b,(end*.83,0,0)),
                  end*.89,'gold',asm=6,n=14)
            g.bolt('Digit hinge pin',joint,add(b,(side*end*.87,0,0)),(side,0,0),
                   end*.34,asm=6,mat='gun')
    g.ring('Unguis ferrule',joint,socket,unit(sub(socket,second)),
           r*.85,r*.45,.023,'edge',asm=6,n=14)
    points=[bezier(socket,bend1,bend2,tip,i/12) for i in range(13)]
    claw(g,'Recurved tempered talon',joint,points,r*.88,side)


def perch(g):
    c=(0,-.32,-1.82)
    g.rod('Perch / ceramic-grip crossbar','stand',(-1.04,c[1],c[2]),(1.04,c[1],c[2]),
          .150,'black',asm=-1,n=40)
    for side in (-1,1):
        g.ring('Perch end ring','stand',(side*1.024,c[1],c[2]),(1,0,0),
               .151,.132,.033,'gun',asm=-1,n=36)
        g.rod('Perch end plug','stand',(side*1.04,c[1],c[2]),(side*1.055,c[1],c[2]),
              .14,'gun',asm=-1,n=36)
        g.bolt('Perch spindle screw','stand',(side*1.059,c[1],c[2]),(side,0,0),
               .035,asm=-1,mat='gun')
    g.rod('Display column','stand',(0,-.32,-2.87),(0,-.32,-1.85),.082,'gun',asm=-1,n=32)
    g.rod('Perch clamp boss','stand',(0,-.32,-2.075),(0,-.32,-1.90),
          .115,'black',asm=-1,n=28,r2=.124)
    for z,r in ((-2.07,.116),(-2.865,.123)):
        g.ring('Column register','stand',(0,-.32,z),(0,0,1),r,.078,.021,'steel',asm=-1,n=30)
    g.rod('Pedestal / rolled outer shell','stand',(0,-.32,-2.956),(0,-.32,-2.851),
          .79,'gun',asm=-1,n=64,r2=.775)
    g.rod('Recessed foot','stand',(0,-.32,-2.980),(0,-.32,-2.950),
          .758,'black',asm=-1,n=64)
    g.ring('Plinth inlay','stand',(0,-.32,-2.849),(0,0,1),.739,.732,.0035,'edge',asm=-1,n=64)
    g.ring('Column flanged socket','stand',(0,-.32,-2.846),(0,0,1),
           .164,.082,.028,'gun',asm=-1,n=36)
    for i in range(3):
        a=TAU*i/3
        g.bolt('Baseplate screw','stand',(.126*cos(a),-.32+.126*sin(a),-2.830),
               (0,0,1),.019,asm=-1,mat='steel')


def proportion_landing(g):
    # Scale each rigid leg about its own hip. Update the bind pivots, toes and bar in
    # the same coordinate transform so standing still produces true pad/bar contact.
    from mathutils import Vector
    original={k:v.copy() for k,v in g.bind.items()}
    factor=1.44
    def adjust(p,s):
        hip=Vector((s*.48,.10,-.46))
        return hip+(p-hip)*factor+Vector((s*.074,-.045,-.035))
    legs={}
    for name,node in g.nodes.items():
        chain=node
        while chain:
            if chain.name in ('leg.L','leg.R'):
                legs[name]=-1 if chain.name.endswith('.L') else 1
                break
            chain=chain.parent
    for name,side in legs.items():g.bind[name]=adjust(original[name],side)
    for name in legs:
        node=g.nodes[name];node.location=g.bind[name]-g.bind[node.parent['joint']]
    for obj in g.parts:
        asm=obj['assembly']
        if asm not in (6,-1):continue
        key=obj.parent['joint'];side=legs[key] if asm==6 else 0
        center=adjust(original[key]+obj.location,side)
        obj.location=center-g.bind[key];obj.scale*=factor
        obj['part_travel']=[v*factor for v in obj['part_travel']]

def build(g):
    tail_unit(g)
    leg_unit(g,-1)
    leg_unit(g,1)
    perch(g)
