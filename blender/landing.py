"""Rigid-body flight take shared by the editable scene, the GLB and the web player."""
import json
import math
import struct
import numpy as np
from mathutils import Vector, Quaternion
from kinematics import X, Y, Z, configure, to_web, to_web_q

FPS = 60
SECONDS = 2.4
BEAT = .8
HOVER = 2 * BEAT
TOUCHDOWN = .80
COMPRESSION = 1.10
SETTLED = 2.05
GROUND = -2.47
BIRD_TRACK = 'Two wingbeats and touchdown'


def ramp(t, start, end):
    u = max(0., min(1., (t-start)/(end-start)))
    return u*u*(3.-2.*u)


def trajectory(t, keys):
    """Cubic Hermite positions. Tangents are world units per second."""
    for (ta, a, va), (tb, b, vb) in zip(keys, keys[1:]):
        if t <= tb:
            d = tb-ta
            u = max(0., (t-ta)/d)
            return (1+2*u)*(1-u)**2*a + u*(1-u)**2*d*va + u*u*(3-2*u)*b + u*u*(u-1)*d*vb
    return keys[-1][1]


HEIGHT = ((0,.92,-.90),(.48,.33,-1.12),(TOUCHDOWN,0,-.82),
          (COMPRESSION,-.20,0),(1.70,-.055,.06),(SETTLED,-.05,0),(SECONDS,-.05,0))
RANGE = ((0,.84,-1.05),(.48,.29,-1.0),(TOUCHDOWN,.045,-.26),
         (COMPRESSION,0,0),(SECONDS,0,0))
PITCH = ((0,-9,0),(TOUCHDOWN,-7,5),(COMPRESSION,1,0),(1.72,-1.6,0),
         (SETTLED,-1,0),(SECONDS,-1,0))


def toe_on_ground(key):
    lane = int(key[-1])-2
    side = -1 if '.L.' in key else 1
    if key.endswith('.4'):
        return Z(-side*7) @ X(66)
    return Z(side*lane*14) @ X(-68+abs(lane)*3)


def sole_depth(g, side):
    """Find the support plane from the actual extended digit and heel geometry."""
    ankle = g.bind['foot.'+side]
    low = 0.
    for part in g.parts:
        joint = part.parent['joint']
        if joint != 'foot.'+side and not joint.startswith('toe.'+side+'.'):
            continue
        coords = np.empty((len(part.data.vertices), 3), np.float32)
        part.data.vertices.foreach_get('co', coords.ravel())
        m = np.asarray(part.matrix_basis)
        points = coords @ m[:3,:3].T + m[:3,3]
        if joint.startswith('toe.'):
            points = points @ np.asarray(toe_on_ground(joint).to_matrix()).T
        low = min(low, float(np.min(points[:,2])) + g.bind[joint].z-ankle.z)
    return -low


def plant_leg(g, side, body, body_rotation, ankle):
    """Solve the hip and hock in bird space. Keep the sole level in world space."""
    leg, shin, foot = ('leg.'+side, 'hock.'+side, 'foot.'+side)
    upper = g.bind[shin]-g.bind[leg]
    lower = g.bind[foot]-g.bind[shin]
    target = body_rotation.inverted() @ (ankle-body) - g.bind[leg]
    direction = target.normalized()
    a, b = upper.length, lower.length
    distance = min(a+b-.0001, max(abs(a-b)+.0001, target.length))
    along = (a*a-b*b+distance*distance)/(2*distance)
    pole = Vector((-.12 if side=='L' else .12, 1, 0))
    bend = (pole-direction*pole.dot(direction)).normalized()
    knee = direction*along + bend*math.sqrt(max(0., a*a-along*along))
    hip_q = upper.rotation_difference(knee)
    shin_q = lower.rotation_difference(direction*distance-knee)
    return {leg:hip_q, shin:hip_q.inverted() @ shin_q, foot:(body_rotation @ shin_q).inverted()}


def bake(g):
    open_wing = configure(g, 'front')
    folded = configure(g, 'perched')
    digits = [k for k in g.nodes if k.startswith('toe.')]
    vanes = [k for k in g.nodes if k.startswith('tail.vane.')]
    feathers = {k:node.parent['joint'] for k,node in g.nodes.items() if 'vane_kind' in node}
    depths = {side:sole_depth(g,side) for side in ('L','R')}
    touchdown_z = GROUND + max(depths.values()) + 1.23 - g.bind['leg.L'].z
    arms = [part+'.'+s for s in ('L','R') for part in ('wing','elbow','wrist')]
    # On the ground the trailing primaries must clear the floor below the ankles.
    for side in ('L','R'):
        shoulder = 'wing.'+side
        folded[shoulder] = X(7) @ folded[shoulder]

    def wing_frames(rotations):
        frames = {}
        for k in arms:
            parent = g.nodes[k].parent['joint']
            frames[k] = frames[parent] @ rotations[k] if parent in frames else rotations[k]
        return frames

    spread_frames, closed_frames = wing_frames(open_wing), wing_frames(folded)
    feather_paths = {}
    identity = Quaternion((1,0,0,0))
    for key,parent in feathers.items():
        spread = spread_frames[parent] @ open_wing[key]
        tucked = closed_frames[parent] @ folded[key]
        axis = Vector(g.nodes[key]['vane_axis']).normalized()
        # Swing the long axis along its shortest arc, then roll about that axis.
        # Combining the two rotations in a single slerp can send a tip above the wing.
        swing = (spread @ axis).rotation_difference(tucked @ axis)
        twist = (swing @ spread).inverted() @ tucked
        feather_paths[key] = (spread,swing,twist)
    samples = []
    for frame in range(round(SECONDS*FPS)+1):
        t = frame/FPS
        lift, travel = trajectory(t,HEIGHT), trajectory(t,RANGE)
        body = Vector((-.20*travel, travel, touchdown_z+lift))
        attitude = X(trajectory(t,PITCH))
        q = {'bird':attitude, 'head':open_wing['head'] @ X(-.50*trajectory(t,PITCH)),
             'tail':open_wing['tail'].slerp(folded['tail'] @ X(10),ramp(t,0,1.70)) @ X(38*(1-ramp(t,0,1.70)))}
        for key in vanes:
            q[key] = Z((int(key.split('.')[-1])-5.5)*(2.2-1.9*ramp(t,.25,1.55)))
        for key in arms:
            delay = 0 if key.startswith('wing.') else .09 if key.startswith('elbow.') else .18
            q[key] = open_wing[key].slerp(folded[key],ramp(t,delay,SETTLED-.24+delay))
        # Interpolate each plate in body space so elbow rotation cannot flip its tip mid-fold.
        current_frames = wing_frames(q)
        folding = ramp(t,.16,SETTLED)
        for key,parent in feathers.items():
            spread,swing,twist = feather_paths[key]
            plate = identity.slerp(swing,folding) @ spread @ identity.slerp(twist,folding)
            q[key] = current_frames[parent].inverted() @ plate
        for side,sign in (('L',-1),('R',1)):
            ankle = Vector((sign*.61,-.28+sign*.065,GROUND+depths[side]))
            if t < TOUCHDOWN:
                lead = max(0.,travel-.045)*ramp(travel,.045,.48)
                ankle += Vector((-.20*lead,lead,lift))
            q.update(plant_leg(g,side,body,attitude,ankle))
        for key in digits:
            q[key] = open_wing[key].slerp(toe_on_ground(key),.60+.40*ramp(t,0,TOUCHDOWN))
        if samples:
            for key in q:
                q[key].make_compatible(samples[-1][1][key])
        samples.append((body,q))
    return hover(g, samples[0]) + samples


def hover(g, landing_start):
    origin, start = landing_start
    tucked = configure(g,'side')
    samples = []
    for frame in range(round(HOVER*FPS)):
        t = frame/FPS
        phase = (t/BEAT) % 1
        stroke = math.sin(math.pi*phase)**2
        wrist = stroke*(1-.38*math.sin(2*math.pi*phase))
        airborne = 1-ramp(t,BEAT+.14,HOVER)
        body = origin + Vector((0,.10*airborne,.12*airborne+.10*stroke))
        q = start.copy()
        for side,sign in (('L',-1),('R',1)):
            shoulder,elbow,tip = (part+'.'+side for part in ('wing','elbow','wrist'))
            q[shoulder] = Y(sign*47*stroke) @ start[shoulder]
            q[elbow] = start[elbow] @ Z(sign*7*stroke)
            q[tip] = Y(sign*8*wrist) @ start[tip]
            for joint in ('leg.','hock.','foot.'):
                key = joint+side
                q[key] = start[key].slerp(tucked[key],.66*airborne)
        for key in q:
            if key.startswith('toe.'):
                q[key] = start[key].slerp(tucked[key],.75*airborne)
        samples.append((body,q))
    return samples


def attach_clip(path, samples):
    """Bind a single portable glTF clip to the named rigid nodes, preserving all PBR data."""
    raw = path.read_bytes()
    size = struct.unpack_from('<I',raw,12)[0]
    doc = json.loads(raw[20:20+size])
    binary = bytearray(raw[28+size:28+size+doc['buffers'][0]['byteLength']])
    nodes = {n.get('extras',{}).get('joint'):i for i,n in enumerate(doc['nodes'])}
    def accessor(values, kind):
        while len(binary)%4:binary.append(0)
        data = np.asarray(values, dtype='<f4').reshape(len(values),-1)
        view = len(doc['bufferViews'])
        doc['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':data.nbytes})
        binary.extend(data.tobytes())
        entry = {'bufferView':view,'componentType':5126,'count':len(values),'type':kind}
        if kind=='SCALAR':entry.update(min=[float(data.min())],max=[float(data.max())])
        doc['accessors'].append(entry)
        return len(doc['accessors'])-1
    times = accessor([i/FPS for i in range(len(samples))],'SCALAR')
    clip = {'name':BIRD_TRACK,'samplers':[],'channels':[]}
    def channel(node, prop, values, kind):
        clip['channels'].append({'sampler':len(clip['samplers']),'target':{'node':nodes[node],'path':prop}})
        clip['samplers'].append({'input':times,'output':accessor(values,kind),'interpolation':'LINEAR'})
    channel('bird','translation',[to_web(v) for v,_ in samples],'VEC3')
    for key in samples[0][1]:
        channel(key,'rotation',[to_web_q(q[key]) for _,q in samples],'VEC4')
    doc['animations']=[clip]
    doc['buffers'][0]['byteLength']=len(binary)
    header = json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode()
    header += b' '*((-len(header))%4)
    binary += b'\0'*((-len(binary))%4)
    chunks = struct.pack('<II',len(header),0x4e4f534a)+header+struct.pack('<II',len(binary),0x004e4942)+binary
    path.write_bytes(struct.pack('<4sII',b'glTF',2,12+len(chunks))+chunks)


def animate_scene(g, ground, reference_camera, samples):
    """Keep the catalogue poses at their existing frames and open on the flight take."""
    scene = g.scene
    start = 221
    camera = reference_camera.copy()
    camera.name = 'Camera · Flight'
    scene.collection.objects.link(camera)
    home = camera.location.copy()
    frame_tuck = camera.rotation_euler.to_quaternion() @ Vector((-.38,-.88,-1.7))

    bird = g.nodes['bird']
    bird.location = (0,0,0)
    for f in (1,190):bird.keyframe_insert(data_path='location',frame=f,group='Flight path')
    for i,(body,rotations) in enumerate(samples):
        frame = start+i
        bird.location = body
        bird.keyframe_insert(data_path='location',frame=frame,group='Flight path')
        for key,rotation in rotations.items():
            joint=g.nodes[key]
            joint.rotation_quaternion=rotation
            joint.keyframe_insert(data_path='rotation_quaternion',frame=frame,group='Landing')
        camera.location = home + body*.60 + frame_tuck*ramp(i/FPS-HOVER,.32,SETTLED)
        camera.keyframe_insert(data_path='location',frame=frame,group='Tracking')
    for t,label in ((0,'First wingbeat'),(BEAT,'Second wingbeat'),(HOVER,'Wing fold'),
                    (HOVER+TOUCHDOWN,'Touchdown'),(HOVER+COMPRESSION,'Recovery'),(HOVER+SETTLED,'Wings tucked')):
        scene.timeline_markers.new(label,frame=start+round(t*FPS))
    ground.hide_render=False
    ground.location.z=GROUND
    scene.camera=camera
    scene.render.fps=FPS
    scene.frame_start=start
    scene.frame_end=start+len(samples)-1
    scene.frame_set(start)
