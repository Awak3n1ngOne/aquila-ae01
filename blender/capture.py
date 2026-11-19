"""Render one camera or one overscanned print border from a prepared Aquila scene."""
import argparse
from pathlib import Path
import sys
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--output',required=True,type=Path)
parser.add_argument('--views',required=True)
parser.add_argument('--samples',type=int,default=128)
parser.add_argument('--scale',type=int,default=100)
parser.add_argument('--device',choices=('cpu','cuda'),default='cuda')
parser.add_argument('--border',type=int,nargs=4)
parser.add_argument('--tile-output',type=Path)
parser.add_argument('--grain',action='store_true',help='Use the samples directly.')
cfg=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
cfg.output.mkdir(parents=True,exist_ok=True)
sc=bpy.context.scene;sc.render.use_persistent_data=False;sc.cycles.device='CPU'
if cfg.device=='cuda':
    pref=bpy.context.preferences.addons['cycles'].preferences
    pref.compute_device_type='CUDA';pref.refresh_devices()
    for d in pref.devices:d.use=d.type=='CUDA'
    if any(d.use for d in pref.devices):sc.cycles.device='GPU'
sc.cycles.use_denoising=not cfg.grain
sc.cycles.denoising_use_gpu=False;sc.cycles.denoising_quality='BALANCED';sc.cycles.denoising_prefilter='FAST'
sc.cycles.use_auto_tile=True;sc.cycles.tile_size=768
sc.cycles.samples=cfg.samples;sc.render.resolution_percentage=cfg.scale
sc.render.threads_mode='FIXED';sc.render.threads=4
ground=bpy.data.objects['Contact floor']
for view in cfg.views.split(','):
    cam=bpy.data.objects['Camera · '+view];sc.camera=cam;sc.frame_set(cam['pose_frame'])
    ground.hide_render=view=='ventral';ground.location.z=cam['ground_level']
    sc.render.filepath=str(cfg.output/('Aquila-'+view+'.jpg'))
    if cfg.border:
        if cfg.tile_output is None:parser.error('--border requires --tile-output')
        w,h=sc.render.resolution_x*cfg.scale//100,sc.render.resolution_y*cfg.scale//100
        x0,y0,x1,y1=cfg.border
        sc.render.use_border=True;sc.render.use_crop_to_border=True
        sc.render.border_min_x=x0/w;sc.render.border_max_x=x1/w
        sc.render.border_min_y=y0/h;sc.render.border_max_y=y1/h
        sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.image_settings.compression=9
        sc.render.filepath=str(cfg.tile_output)
    bpy.ops.render.render(write_still=True)
    print('CAPTURE_OK',view,flush=True)
