"""One armature of rigid machining centres for every camera and rest pose."""
from math import radians as D
from mathutils import Vector as V, Quaternion as Q, Matrix
import math

def spin(axis,angle):return Q(V(axis),D(angle))
def X(a):return spin((1,0,0),a)
def Y(a):return spin((0,1,0),a)
def Z(a):return spin((0,0,1),a)
def frame(ray,normal):
    x=V(ray).normalized();z=(V(normal)-x*x.dot(V(normal))).normalized();y=z.cross(x).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()
def aim(a,b,n):
    return frame(b,n) @ frame(a,(0,0,1)).inverted()
def configure(g,name):
    rots={k:Q((1,0,0,0)) for k in g.nodes}
    landing=name=='front';perch=name=='perched';rear=name=='rear'
    rots['bird']=X(0 if perch else 6 if landing else 11)
    rots['head']=Z(-29 if landing else 13 if perch else 3 if rear else 5) @ X(5 if landing else -5 if not perch else 0)
    rots['tail']=Z(-24 if landing else 0) @ X(-60 if landing else -8 if perch else 5)
    for s,k in ((-1,'L'),(1,'R')):
        arm='wing.'+k;fore='elbow.'+k;hand='wrist.'+k
        if perch:
            # The elbow goes aft, the wrist returns to the front, and the primaries stream back.
            # The feather sheet rolls on edge to lie along the flank.
            direction_a=(s*.20,1.04,-.71);direction_b=(s*.18,-1.39,.40);direction_c=(s*.04,1.0,-.69)
            qa=aim(g.bind[fore]-g.bind[arm],direction_a,(s*.99,.08,.26))
            qb=aim(g.bind[hand]-g.bind[fore],direction_b,(s*.99,.02,.12))
            qc=aim((s,0,0),direction_c,(s*.99,0,.12))
            rots[arm]=qa;rots[fore]=qa.inverted()@qb;rots[hand]=qb.inverted()@qc
        elif landing:
            rots[arm]=Y(-s*(30 if s>0 else 25)) @ X(-56) @ Z(s*3.0)
            rots[fore]=Y(-s*6) @ Z(-s*7)
            rots[hand]=Y(s*4) @ Z(s*7)
        else:
            rots[arm]=Y(-s*(15 if rear else 12)) @ X(-10 if rear else -6)
            rots[fore]=Y(s*5) @ Z(-s*3);rots[hand]=Y(-s*8)
        rots['leg.'+k]=Y(-s*11 if landing else 0) @ X(0 if perch else (-35 if s>0 else -45) if landing else 67)
        rots['foot.'+k]=Z(s*10 if landing else 0) @ X(0 if perch else 8 if landing else 13)
    for key in rots:
        if key.startswith('toe.') and not perch:
            hallux=key.endswith('.4')
            side=-1 if '.L.' in key else 1
            lane=(int(key[-1])-2) if not hallux else 0
            rots[key]=Z(side*lane*19 if landing else 0) @ X((-1 if hallux else 1)*(-18 if landing else 16))
        if key.startswith('tail.vane.'):
            idx=int(key.split('.')[-1])
            rots[key]=Z(((idx-5.5)/5.5)*(17 if perch else 0 if landing else 7))
    if perch:
        from wings import fold_feathers
        fold_feathers(g,rots)
    return rots

CAMERAS={
    'front':((7.15,-12.1,1.88),(0,.04,.33)),
    'side':((-9.3,-7.7,3.65),(0,.02,.2)),
    'rear':((1.25,12.4,4.85),(0,.0,.05)),
    'perched':((-9.1,-7.3,2.6),(0,.0,-.56)),
    'detail':((6.1,-10.34,2.5),(.12,-.51,.77)),
    'axial':((0,-13,1),(0,0,.15)),
    'left':((-13,0,1.15),(0,0,.14)),
    'right':((13,0,1.15),(0,0,.14)),
    'overhead':((.16,1.1,13.5),(0,.0,.05)),
    'ventral':((-2.1,-5.0,-12),(0,.0,.05))
}
DISTANCE=15.8

def photographic_frame(points,position,target):
    import numpy as np
    axis=(V(target)-V(position)).normalized()
    q=axis.to_track_quat('-Z','Y')
    right=np.asarray(q@V((1,0,0)));up=np.asarray(q@V((0,1,0)));depth=np.asarray(axis)
    xx=points@right;yy=points@up;zz=points@depth
    cx=(xx.min()+xx.max())*.5;cy=(yy.min()+yy.max())*.5;cz=(zz.min()+zz.max())*.5
    scale=DISTANCE/(DISTANCE+zz-cz)
    for _ in range(4):
        xp=(xx-cx)*scale;yp=(yy-cy)*scale
        dx=(xp.max()+xp.min())*.5;dy=(yp.max()+yp.min())*.5
        cx+=dx;cy+=dy
    xp=(xx-cx)*scale;yp=(yy-cy)*scale
    focus=right*cx+up*cy+depth*cz
    return focus,axis,q,float(np.ptp(xp)),float(np.ptp(yp))

def to_web(v):return [v[0],v[2],-v[1]]
def to_web_q(q):return [q.x,q.z,-q.y,q.w]
