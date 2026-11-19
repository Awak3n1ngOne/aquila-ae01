"""Batch the editable solids by joint and shell and export the flight performance."""
import bpy, numpy as np, gzip, json, shutil
import occlusion
import landing
from studio import point_cloud,apply
from collections import defaultdict
from mathutils import Vector, Quaternion
from kinematics import configure,to_web,to_web_q,CAMERAS,DISTANCE,photographic_frame
from parts import SYSTEMS
from lightbank import ENVIRONMENT_INTENSITY

def export(g,folder,assets,flight):
    groups=defaultdict(list)
    for o in g.parts:groups[(o.parent['joint'],int(o['assembly']),bool(o['shell']))].append(o)
    ambient=occlusion.build(g)
    s=bpy.data.scenes.new('Aquila · glTF production')
    bpy.context.window.scene=s
    joints={}
    for key,orig in g.nodes.items():
        n=bpy.data.objects.new('Rig '+key,None);s.collection.objects.link(n)
        n['joint']=key;n.rotation_mode='QUATERNION';n.location=orig.location
        if orig.parent:n.parent=joints[orig.parent['joint']]
        joints[key]=n
    for (key,aid,shell),parts in groups.items():
        verts=[];faces=[];ids=[];smooth=[];uv=[];mats=[];ao=[];corner_normals=[];base=0
        for obj in parts:
            data=obj.data;mat=obj.matrix_basis;remap=[]
            for m in data.materials:
                if m not in mats:mats.append(m)
                remap.append(mats.index(m))
            # Transform every vertex to the joint's coordinate frame, preserving independent bevels and seams.
            coords=np.empty((len(data.vertices),3),np.float32);data.vertices.foreach_get('co',coords.ravel())
            trans=np.asarray(mat);coords=coords@trans[:3,:3].T+trans[:3,3]
            verts.extend(coords.tolist())
            world=obj.matrix_world;normal_world=world.to_3x3().inverted_safe().transposed()
            ao.extend([ambient(world@v.co,(normal_world@v.normal).normalized()) for v in data.vertices] if aid>=0 else [1.]*len(coords))
            # Tangent generation needs triangles or quads, including the end caps.
            # Use Blender's tessellation and retain the original per-corner UVs and
            # split normals so a polished surface stays continuous across diagonals.
            data.calc_loop_triangles()
            triangles=data.loop_triangles
            corners=np.empty(3*len(triangles),np.int32)
            triangles.foreach_get('loops',corners)
            uvs=np.empty((len(data.loops),2),np.float32);data.uv_layers.active.data.foreach_get('uv',uvs.ravel())
            uv.append(uvs[corners])
            normals=np.empty((len(data.loops),3),np.float32)
            data.corner_normals.foreach_get('vector',normals.ravel())
            normals=normals@np.linalg.inv(trans[:3,:3])
            normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
            corner_normals.append(normals[corners])
            for tri in triangles:
                f=data.polygons[tri.polygon_index]
                faces.append(tuple(base+i for i in tri.vertices));ids.append(remap[f.material_index]);smooth.append(f.use_smooth)
            base+=len(coords)
        name=f'{key} | '+(SYSTEMS[aid] if aid>=0 else 'Perch')+(' | Panels' if shell else ' | Stock')
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
        for m in mats:mesh.materials.append(m)
        mesh.polygons.foreach_set('material_index',np.array(ids,dtype=np.int32))
        mesh.polygons.foreach_set('use_smooth',np.array(smooth,dtype=np.bool_))
        mesh.normals_split_custom_set(np.concatenate(corner_normals))
        colors=mesh.color_attributes.new(name='Seam occlusion',type='BYTE_COLOR',domain='POINT')
        values=np.ones((len(verts),4),dtype=np.float32);values[:,:3]=np.array(ao)[:,None]
        colors.data.foreach_set('color',values.ravel());mesh.color_attributes.active_color=colors
        uvdata=mesh.uv_layers.new(name='Machining UV').data
        uvdata.foreach_set('uv',np.concatenate(uv).ravel())
        obj=bpy.data.objects.new(name,mesh);s.collection.objects.link(obj);obj.parent=joints[key]
        obj['assembly']=aid;obj['shell']=shell;obj['partCount']=len(parts)
    # The packaged GLB opens in the default landing pose in standard glTF applications.
    poses={key:configure(g,key) for key in ('front','side','perched','rear')}
    for key,n in joints.items():n.rotation_quaternion=poses['front'][key]
    joints['stand'].scale=(.00001,)*3
    bpy.context.view_layer.update()
    glb=folder/'Aquila-AE01.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_active_scene=True,
        export_animations=False,export_extras=True,export_morph=False,
        export_yup=True,export_vertex_color='ACTIVE',export_cameras=False,export_lights=False,export_tangents=True)
    landing.attach_clip(glb,flight)
    compressed=assets/'aquila-metal.glb.gz'
    with glb.open('rb') as src,compressed.open('wb') as target:
        with gzip.GzipFile(fileobj=target,mode='wb',compresslevel=8,mtime=0) as gz:shutil.copyfileobj(src,gz)
    roundv=lambda values:[round(float(v),7) for v in values]
    meta={'distance':DISTANCE,'poses':{k:{n:roundv(to_web_q(v)) for n,v in rot.items()} for k,rot in poses.items()},
        'camera':{k:[roundv(to_web(p)) for p in pair] for k,pair in CAMERAS.items()},
        'environmentIntensity':ENVIRONMENT_INTENSITY,
        'counts':[sum(int(x['assembly'])==i for x in g.parts) for i in range(8)],
        'landing':{'name':landing.BIRD_TRACK,'ground':landing.GROUND,'seconds':landing.HOVER+landing.SECONDS,
                   'beat':landing.BEAT,'descent':landing.HOVER,'touchdown':landing.HOVER+landing.TOUCHDOWN,
                   'compression':landing.HOVER+landing.COMPRESSION,'settled':landing.HOVER+landing.SETTLED}}
    bpy.context.window.scene=g.scene
    meta['frames']={}
    extra={'axial':((0,-13,1),(0,0,.15)), 'sideview':((-13,0,1.2),(0,0,.12)), 'rightview':((13,0,1.2),(0,0,.12)), 'back':((0,13,2),(0,0,.1))}
    for pose in poses:
        apply(g,pose)
        points=point_cloud(g,pose=='perched')
        frames={}
        for view,(p,t) in dict(hero=CAMERAS[pose],top=CAMERAS['overhead'],bottom=CAMERAS['ventral'],**extra).items():
            center,forward,q,width,height=photographic_frame(points,p,t)
            frames[view]={'center':roundv(to_web(center)),'eye':roundv(to_web(-forward)),
                'width':round(width,5),'height':round(height,5)}
        frames['ground']=round(float(points[:,2].min()),5)
        meta['frames'][pose]=frames
    for node in g.nodes.values():node.rotation_quaternion=Quaternion((1,0,0,0))
    g.nodes['stand'].scale=(1,1,1);bpy.context.view_layer.update()
    (assets/'aquila-rig.js').write_text('export const rig = '+json.dumps(meta,separators=(',',':'))+';\n',encoding='utf8')
    bpy.context.window.scene=g.scene
    for obj in list(s.objects):
        data=obj.data if obj.type=='MESH' else None
        bpy.data.objects.remove(obj,do_unlink=True)
        if data and not data.users:bpy.data.meshes.remove(data)
    bpy.data.scenes.remove(s)
    print('AQUILA_EXPORT',len(g.parts),len(groups),glb.stat().st_size,compressed.stat().st_size,meta['counts'],flush=True)
