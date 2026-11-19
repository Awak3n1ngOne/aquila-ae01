"""Camera-neutral product lighting and orthographic turntable evidence."""
import bpy, numpy as np
from mathutils import Vector, Matrix
from kinematics import CAMERAS,configure,DISTANCE,photographic_frame
from parts import collection

def init(g):
    sc=g.scene;sc.render.engine='CYCLES';sc.cycles.samples=28;sc.cycles.use_denoising=True
    sc.cycles.use_auto_tile=True;sc.cycles.tile_size=480
    sc.cycles.denoising_quality='BALANCED';sc.cycles.denoising_prefilter='FAST'
    sc.cycles.adaptive_threshold=.010;sc.cycles.max_bounces=9;sc.cycles.glossy_bounces=5
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='CUDA';prefs.refresh_devices()
        gpu=False
        for d in prefs.devices:
            d.use=d.type=='CUDA';gpu=gpu or d.use
        if gpu:sc.cycles.device='GPU'
        print('AQUILA_CYCLES',[(d.name,d.type,bool(d.use)) for d in prefs.devices],flush=True)
    except Exception as e:print('Cycles uses available CPU',e,flush=True)
    sc.render.resolution_x=2048;sc.render.resolution_y=1280;sc.render.resolution_percentage=100
    sc.render.image_settings.file_format='JPEG';sc.render.image_settings.quality=96
    sc.render.film_transparent=False;sc.view_settings.view_transform='AgX'
    sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=-.16
    sc.world=bpy.data.worlds.new('Ivory cyclorama');sc.world.use_nodes=True
    nt=sc.world.node_tree
    from pathlib import Path
    from lightbank import write_studio,ENVIRONMENT_INTENSITY
    cardfile=Path(__file__).resolve().parents[1]/'dist'/'assets'/'studio-radiance.png'
    write_studio(cardfile)
    illumination=bpy.data.images.load(str(cardfile));illumination.colorspace_settings.name='sRGB';illumination.pack()
    env=nt.nodes.new('ShaderNodeTexEnvironment');env.image=illumination
    amb=nt.nodes.get('Background');amb.inputs[1].default_value=ENVIRONMENT_INTENSITY
    nt.links.new(env.outputs['Color'],amb.inputs[0])
    camera_bg=nt.nodes.new('ShaderNodeBackground');camera_bg.inputs[0].default_value=(1,.76,.555,1);camera_bg.inputs[1].default_value=2.4
    lightpath=nt.nodes.new('ShaderNodeLightPath');mix=nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lightpath.outputs['Is Camera Ray'],mix.inputs[0]);nt.links.new(amb.outputs[0],mix.inputs[1]);nt.links.new(camera_bg.outputs[0],mix.inputs[2]);nt.links.new(mix.outputs[0],nt.nodes.get('World Output').inputs[0])
    c=collection('Studio · turntable cameras and softboxes',sc)
    def area(name,p,power,size,sy,color):
        l=bpy.data.lights.new(name,'AREA');l.energy=power;l.shape='RECTANGLE';l.size=size;l.size_y=sy;l.color=color
        o=bpy.data.objects.new(name,l);c.objects.link(o);o.location=p;o.rotation_euler=(-Vector(p)).to_track_quat('-Z','Y').to_euler()
    area('Key · overhead silk',(-4.8,-5.4,7.1),710,4.4,3.2,(1,.92,.83))
    area('Rim · cool softbox',(4.8,3.5,4.9),840,3.45,1.1,(.88,.94,1))
    area('Strip · leading edge',(4.9,-3.8,2.2),510,.70,4.8,(1,.97,.91))
    area('Back · long reflection',(-4,4,2.7),440,4.3,.92,(1,.87,.69))
    area('Strip · port feathers',(-4.7,-3.9,1.9),275,.55,3.8,(.91,.96,1))
    area('Bounce · belly',(-.6,-4.8,-1.7),38,2.1,1.4,(.88,.93,1))
    mat=bpy.data.materials.new('Warm studio floor');mat.diffuse_color=(.47,.334,.212,1);mat.use_nodes=True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=mat.diffuse_color
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.81
    ft=mat.node_tree;floor_bs=ft.nodes.get('Principled BSDF');em=ft.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value=(1.0,.773,.540,1);em.inputs[1].default_value=3.6
    # The bounced-light pedestal includes short-range contact shading. Its background
    # reflectance stays independent of the reflective metal under studio illumination.
    ao=ft.nodes.new('ShaderNodeAmbientOcclusion');ao.samples=6;ao.inputs['Distance'].default_value=2.1
    power=ft.nodes.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=2.15
    ft.links.new(ao.outputs['AO'],power.inputs[0])
    level=ft.nodes.new('ShaderNodeMath');level.operation='MULTIPLY';level.inputs[1].default_value=3.6
    ft.links.new(power.outputs[0],level.inputs[0]);ft.links.new(level.outputs[0],em.inputs[1])
    weight=ft.nodes.new('ShaderNodeMath');weight.operation='MULTIPLY';weight.inputs[1].default_value=.47
    ft.links.new(ft.nodes.new('ShaderNodeLightPath').outputs['Is Camera Ray'],weight.inputs[0])
    fm=ft.nodes.new('ShaderNodeMixShader');ft.links.new(weight.outputs[0],fm.inputs[0])
    ft.links.new(floor_bs.outputs[0],fm.inputs[1]);ft.links.new(em.outputs[0],fm.inputs[2]);ft.links.new(fm.outputs[0],ft.nodes.get('Material Output').inputs[0])
    # The sweep recedes into the same world radiance, independent of camera angle.
    ray=ft.nodes.new('ShaderNodeLightPath')
    haze=ft.nodes.new('ShaderNodeMapRange');haze.interpolation_type='SMOOTHERSTEP'
    haze.inputs['From Min'].default_value=20;haze.inputs['From Max'].default_value=63
    ft.links.new(ray.outputs['Ray Length'],haze.inputs['Value'])
    far=ft.nodes.new('ShaderNodeMath');far.operation='MULTIPLY'
    ft.links.new(haze.outputs[0],far.inputs[0]);ft.links.new(ray.outputs['Is Camera Ray'],far.inputs[1])
    haze_shader=ft.nodes.new('ShaderNodeEmission');haze_shader.inputs[0].default_value=(1,.76,.555,1);haze_shader.inputs[1].default_value=2.4
    sweep=ft.nodes.new('ShaderNodeMixShader');ft.links.new(far.outputs[0],sweep.inputs[0])
    ft.links.new(fm.outputs[0],sweep.inputs[1]);ft.links.new(haze_shader.outputs[0],sweep.inputs[2])
    ft.links.new(sweep.outputs[0],ft.nodes.get('Material Output').inputs[0])
    me=bpy.data.meshes.new('Cyclorama floor');me.from_pydata([(-150,-150,0),(150,-150,0),(150,150,0),(-150,150,0)],[],[(0,1,2,3)])
    me.materials.append(mat);ground=bpy.data.objects.new('Contact floor',me);c.objects.link(ground);ground.location.z=-2.2
    cams={}
    for key in CAMERAS:
        data=bpy.data.cameras.new(key);data.type='PERSP';data.sensor_width=36;data.sensor_fit='HORIZONTAL';data.clip_end=270
        cam=bpy.data.objects.new('Camera · '+key,data);c.objects.link(cam);cams[key]=cam
    return ground,cams

def apply(g,pose,frame=None):
    for name,q in configure(g,pose).items():
        o=g.nodes[name];o.rotation_mode='QUATERNION';o.rotation_quaternion=q
        if frame is not None:o.keyframe_insert(data_path='rotation_quaternion',frame=frame,group='Rest pose')
    stand=g.nodes['stand'];stand.scale=(1,)*3 if pose=='perched' else (.00001,)*3
    if frame is not None:stand.keyframe_insert(data_path='scale',frame=frame,group='Display')
    bpy.context.view_layer.update()

def point_cloud(g,stand):
    points=[]
    for o in g.parts:
        if not stand and o['assembly']<0:continue
        v=np.empty((len(o.data.vertices),3),np.float32);o.data.vertices.foreach_get('co',v.ravel())
        m=np.asarray(o.matrix_world);points.append(v@m[:3,:3].T+m[:3,3])
    return np.concatenate(points)

def fit(sc,cam,key,points,camera_override=None):
    p,target=CAMERAS[key] if camera_override is None else camera_override
    focus,forward,q,width,height=photographic_frame(points,p,target)
    cam.location=Vector(focus)-forward*DISTANCE;cam.rotation_euler=q.to_euler()
    aspect=sc.render.resolution_x/sc.render.resolution_y
    aperture=max(width,height*aspect)*1.105
    cam.data.lens=cam.data.sensor_width*DISTANCE/aperture
    sc.camera=cam

def take(g,ground,cams,view,folder,samples=28,res=100):
    # Every diagnostic angle uses the exact same landing pose and assembly.
    pose='perched' if view=='perched' else 'front'
    apply(g,pose);sc=g.scene;points=point_cloud(g,pose=='perched')
    ground.location.z=points[:,2].min()-(.004 if pose=='perched' else .32)
    ground.hide_render=view=='ventral'
    fit(sc,cams[view],view,points)
    sc.render.resolution_percentage=res;sc.cycles.samples=samples;sc.render.filepath=str(folder/('Aquila-'+view+'.jpg'))
    bpy.ops.render.render(write_still=True);print('AQUILA_PLATE',view,flush=True)

def head_portraits(head,studio_camera,ground_level):
    target=head.matrix_world @ Vector((0,-.38,.39))
    for name,eye,width in (('plumage',(.68,-.83,.45),2.33),('profile',(.98,.04,.27),2.54)):
        camera=studio_camera.copy()
        camera.data=studio_camera.data.copy()
        camera.name='Camera · '+name
        studio_camera.users_collection[0].objects.link(camera)
        direction=(head.matrix_world.to_quaternion() @ Vector(eye)).normalized()
        camera.location=target+direction*DISTANCE
        camera.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
        camera.data.lens=camera.data.sensor_width*DISTANCE/width
        camera['pose_frame']=1
        camera['ground_level']=ground_level

def editable(g,ground,cams,folder,flight):
    sc=g.scene
    poses=[(1,'front','Landing · extended wings'),(45,'side','Gliding · tucked feet'),
           (92,'perched','Perching · folded wings'),(142,'rear','Dorsal flight'),(190,'front','Landing')]
    for n,key,label in poses:
        apply(g,key,n);sc.timeline_markers.new(label,frame=n)
    sc.frame_start=1;sc.frame_end=190;sc.frame_set(1)
    sc['floor_landing']=float(point_cloud(g,False)[:,2].min())
    for k,cam in cams.items():
        pose='perched' if k=='perched' else 'side' if k=='side' else 'front'
        apply(g,pose);points=point_cloud(g,pose=='perched')
        cam['ground_level']=float(points[:,2].min()-(.006 if pose=='perched' else .24))
        cam['pose_frame']=92 if pose=='perched' else 45 if pose=='side' else 1
        fit(sc,cam,k,points)
        if k=='detail':
            target=Vector((.12,-.51,.77));direction=(Vector(CAMERAS[k][0])-target).normalized()
            cam.location=target+direction*DISTANCE;cam.rotation_euler=(-direction).to_track_quat('-Z','Y').to_euler()
            cam.data.lens=cam.data.sensor_width*DISTANCE/3.68
    sc.frame_set(1);apply(g,'front');sc.camera=cams['front'];ground.hide_render=False;ground.location.z=point_cloud(g,False)[:,2].min()-.32
    head_portraits(g.nodes['head'],cams['front'],ground.location.z)
    from landing import animate_scene
    animate_scene(g,ground,cams['front'],flight)
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False
                a.spaces.active.shading.color_type='MATERIAL'
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Aquila-AE01.blend'),compress=True)
