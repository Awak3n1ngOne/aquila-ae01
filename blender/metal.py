"""Seamless material-coordinate finishes. All bitmap channels are independent of camera and pose."""
import bpy
import numpy as np
from math import pi
from pathlib import Path

# Albedo values are sRGB as seen on a neutral studio card. Metallic and roughness are linear.
STOCK = {
    'bronze': ('Brushed antique bronze', (135,103,74), .89,.245),
    'umber':  ('Smoked manganese bronze',(107,87,72), .85,.285),
    'dark':   ('Blackened bronze',      (77,67,60), .81,.305),
    'edge':   ('Machined bronze lip',   (171,140,104), .94,.183),
    'gun':    ('Phosphate gunmetal',    (91,96,99), .87,.275),
    'black':  ('Graphite gasket',       (34,33,31), .36,.49),
    'steel':  ('Satin stainless',       (163,170,172),.94,.19),
    'silver': ('Polished spindle',      (212,213,207),.97,.142),
    'ivory':  ('Ivory ceramic enamel',  (215,207,187),.23,.275),
    'bone':   ('Shadow ivory enamel',   (180,169,148),.27,.32),
    'gold':   ('Gilded bronze',         (210,161,75), .91,.202),
    'orange': ('Vermilion seal',        (187,63,21),  .36,.41),
    'amber':  ('Amber iris',           (130,84,32), .30,.26),
    'lens':   ('Smoked optical glass',  (13,17,19),   .38,.09)
}

def make_finishes(tex_dir):
    tex_dir=Path(tex_dir)
    tex_dir.mkdir(parents=True,exist_ok=True)
    n=384
    rng=np.random.default_rng(90117)
    y,x=np.mgrid[:n,:n]
    u=x/n;v=y/n
    def blur_noise(sx,sy):
        seed=rng.normal(0,1,(n,n))
        kx=np.fft.fftfreq(n)[None,:];ky=np.fft.fftfreq(n)[:,None]
        val=np.fft.ifft2(np.fft.fft2(seed)*np.exp(-2*pi*pi*((kx*sx)**2+(ky*sy)**2))).real
        return val/(val.std()+1e-8)
    brushed=blur_noise(14,.42)
    cloud=blur_noise(12,10)*.55+blur_noise(32,42)*.45
    pore=blur_noise(.48,.48)
    scuff=np.zeros((n,n))
    for i in range(75):
        ax,ay=rng.uniform(0,1,2);length=rng.uniform(.022,.27)
        dx=(u-ax+.5)%1-.5;dy=(v-ay+.5)%1-.5
        fall=np.exp(-((dy-rng.uniform(-.22,.22)*dx)/rng.uniform(.0007,.0022))**2)
        scuff+=fall*np.exp(-(abs(dx)/(length/2))**6)*rng.uniform(.2,1)
    # PNG is written directly from bytes to preserve exact data and sRGB values.
    import zlib,struct
    def png(path,pixels):
        by=np.uint8(np.clip(pixels,0,255))
        def chunk(k,v):return struct.pack('>I',len(v))+k+v+struct.pack('>I',zlib.crc32(k+v)&0xffffffff)
        h,w=by.shape[:2];raw=b''.join(b'\0'+row.tobytes() for row in by)
        path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,7))+chunk(b'IEND',b''))
    def image(name,arr,color):
        file=tex_dir/(name+'.png');png(file,arr)
        img=bpy.data.images.load(str(file));img.colorspace_settings.name=color;img.pack();return img
    h=.6*brushed+scuff*.52+.18*pore
    nx=(np.roll(h,1,1)-np.roll(h,-1,1))*.11
    ny=(np.roll(h,1,0)-np.roll(h,-1,0))*.11
    ln=np.sqrt(1+nx*nx+ny*ny)
    normal=image('fine-metal-grain-normal',np.stack([(nx/ln*.5+.5)*255,(ny/ln*.5+.5)*255,(1/ln*.5+.5)*255],axis=-1),'Non-Color')
    gains=np.array([.95,1.02,1.06])
    mats={}
    for name,(label,base,metal,rough) in STOCK.items():
        m=bpy.data.materials.new(label);m['stock']=name;m.use_nodes=True
        tree=m.node_tree;bs=tree.nodes.get('Principled BSDF')
        m.diffuse_color=(*[max(.001,((k/255+.055)/1.055)**2.4) for k in base],1)
        m.metallic=metal;m.roughness=rough
        bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
        # Optical and rubber parts stay clean. Enamel has much lighter grain than unfinished bronze.
        if name in ('amber','lens','black','orange'):
            bs.inputs['Base Color'].default_value=m.diffuse_color
        else:
            enamel=name in ('ivory','bone')
            amp=.32 if enamel else .45 if name=='gold' else .64 if name in ('steel','silver') else 1
            pat=(.057*cloud+.018*pore+.036*brushed+.075*scuff)*amp
            baseimage=np.array(base)[None,None,:]*(1+pat[:,:,None]*gains)
            tex=tree.nodes.new('ShaderNodeTexImage');tex.image=image(name+'-albedo',baseimage,'sRGB')
            tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
            # Neutral metal flux varies with polish and fine tooling marks.
            mr=np.zeros((n,n,3));mr[:,:,0]=255;mr[:,:,1]=255*np.clip(rough+amp*(.024*cloud+.024*brushed-.053*scuff),.095,.67);mr[:,:,2]=255*metal
            t=tree.nodes.new('ShaderNodeTexImage');t.image=image(name+'-rough-metal',mr,'Non-Color')
            sep=tree.nodes.new('ShaderNodeSeparateColor');tree.links.new(t.outputs['Color'],sep.inputs[0])
            tree.links.new(sep.outputs['Green'],bs.inputs['Roughness']);tree.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
            bump=tree.nodes.new('ShaderNodeTexImage');bump.image=normal
            nm=tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.16 if enamel else .32
            tree.links.new(bump.outputs['Color'],nm.inputs['Color']);tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        if name in ('lens','amber','ivory','bone','gold'):
            coat,coat_rough={'lens':(.55,.07),'amber':(.23,.19),'ivory':(.33,.175),
                             'bone':(.29,.20),'gold':(.19,.14)}[name]
            bs.inputs['Coat Weight'].default_value=coat
            bs.inputs['Coat Roughness'].default_value=coat_rough
        if name in ('steel','silver','edge'):
            bs.inputs['Anisotropic'].default_value=.24
        mats[name]=m
    from plume import finish_plates
    finish_plates(mats,image)
    from head_enamel import add_material
    add_material(mats,image)
    return mats
