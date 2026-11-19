"""Build the editable Aquila, the portable GLB, and the matching interactive asset.
blender -b --factory-startup -P blender/build.py -- --output ../aquila-solid
"""
import sys
sys.dont_write_bytecode=True
from pathlib import Path
import argparse, tempfile
import bpy
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from parts import Stock
from metal import make_finishes
from export_asset import export
from studio import init,editable,take
from kinematics import configure
import wings,fuselage,lower,landing

opts=argparse.ArgumentParser()
opts.add_argument('--output',required=True,type=Path)
opts.add_argument('--quality',choices=['proof','final'],default='proof')
opts.add_argument('--views',default='front,rear,perched')
opts.add_argument('--render-only',action='store_true')
opts.add_argument('--prepare',action='store_true',help='Save the rig and studio for rendering in a clean process.')
cfg=opts.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
out=cfg.output.resolve();out.mkdir(parents=True,exist_ok=True)
assets=HERE.parent/'dist'/'assets'
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.name='AQUILA AE-01 | mechanical bald eagle'
with tempfile.TemporaryDirectory(prefix='aquila-metal-') as tmp:
    g=Stock(sc,make_finishes(Path(tmp)))
    fuselage.build(g);wings.build(g);lower.build(g);lower.proportion_landing(g)
    bpy.context.view_layer.update()
    print('AQUILA_PARTS',len(g.parts),'joints',len(g.nodes),flush=True)
    flight=landing.bake(g)
    if not cfg.render_only:export(g,out,assets,flight)
    ground,cameras=init(g)
    for v in ([] if cfg.prepare else filter(None,cfg.views.split(','))):take(g,ground,cameras,v,out,14 if cfg.quality=='proof' else 112,45 if cfg.quality=='proof' else 100)
    if cfg.prepare or not cfg.render_only:
        sc.render.resolution_percentage=100;sc.cycles.samples=112
        editable(g,ground,cameras,out,flight)
    print('AQUILA_FINISHED',out,flush=True)
