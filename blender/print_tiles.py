"""Render full-size Cycles product photographs with bounded peak memory."""
import argparse
from pathlib import Path
import subprocess
import tempfile
from PIL import Image

def render(cfg,view):
    w,h=2048,1280
    result=Image.new('RGB',(w,h))
    with tempfile.TemporaryDirectory(prefix='aquila-print-') as tmp:
        for row in range(2):
            for col in range(3):
                a,b,c,d=col*w//3,row*h//2,(col+1)*w//3,(row+1)*h//2
                # Each tile includes neighbouring samples for the reconstruction filter.
                x0,y0,x1,y1=max(0,a-40),max(0,b-40),min(w,c+40),min(h,d+40)
                tile=Path(tmp)/f'{row}-{col}.png'
                args=[cfg.blender,'-b',str(cfg.scene),'-t','4','--python-exit-code','31','-P',
                      str(Path(__file__).with_name('capture.py')),'--','--views',view,'--output',tmp,
                      '--border',*map(str,(x0,y0,x1,y1)),'--tile-output',str(tile)]
                last_trace=''
                for device,raw in (('cuda',False),('cpu',False),('cuda',True)):
                    command=args+['--samples',str(max(384,cfg.samples) if raw else cfg.samples),'--device',device]
                    if raw:command.append('--grain')
                    proc=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                    trace=proc.stdout.decode('utf-8','replace')
                    if proc.returncode==0 and tile.is_file() and 'out of memory' not in trace.lower():
                        break
                    last_trace=trace[-680:]
                else:raise RuntimeError(f'{view} tile {row},{col}: {last_trace}')
                with Image.open(tile) as piece:
                    if abs(piece.width-(x1-x0))>1 or abs(piece.height-(y1-y0))>1:
                        raise ValueError('Unexpected Cycles render border dimensions')
                    patch=(a-x0,piece.height-(d-y0),c-x0,piece.height-(b-y0))
                    result.paste(piece.crop(patch),(a,h-d))
    dest=cfg.output/('Aquila-'+view+'.jpg')
    local=dest.with_suffix('.tmp');result.save(local,format='JPEG',quality=96,subsampling=0,optimize=True)
    local.replace(dest)
    print('PRINT_READY',view,dest.stat().st_size,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--scene',required=True,type=Path);p.add_argument('--blender',required=True)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--views',required=True)
    p.add_argument('--samples',type=int,default=128)
    cfg=p.parse_args();cfg.output.mkdir(parents=True,exist_ok=True)
    for v in cfg.views.split(','):render(cfg,v)
