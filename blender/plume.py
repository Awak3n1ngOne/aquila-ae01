"""Stamp-local finishes. Grain follows the long axis of every feather in all poses."""
import numpy as np
from math import pi
import bpy

def finish_plates(mats,image):
    # Channel x is the root-to-tip station and y is the crosswise position on the stamping.
    nx,ny=512,320
    v,u=np.mgrid[:ny,:nx]
    u=(u+.5)/nx;v=(v+.5)/ny
    rng=np.random.default_rng(181103)
    def noise(kx,ky):
        seed=rng.normal(0,1,(ny,nx))
        x=np.fft.fftfreq(nx)[None,:];y=np.fft.fftfreq(ny)[:,None]
        tile=np.fft.ifft2(np.fft.fft2(seed)*np.exp(-2*pi*pi*((x*kx)**2+(y*ky)**2))).real
        return tile/(tile.std()+1e-8)
    broad=noise(46,21); rub=noise(12,3); brushing=noise(26,.61); grain=noise(.65,.45)
    linear=np.clip(.5+.32*brushing+.12*rub,0,1)
    wear=np.zeros_like(u)
    for i in range(91):
        a,b=rng.uniform((.07,.01),(.985,.99))
        length=rng.uniform(.012,.092)*(1.85 if i%9==0 else 1)
        slope=rng.uniform(-.56,.56)
        dy=v-b-slope*(u-a)
        stroke=np.exp(-(dy/rng.uniform(.0008,.0037))**2-np.abs((u-a)/length)**6)
        wear=np.maximum(wear,stroke*rng.uniform(.32,1))
    for k in range(4):
        a=(.71,.79,.866,.937)[k]
        line=np.exp(-((u-a-.135*v)/.0013)**2)*np.exp(-(v/(.13+.034*(k%3)))**3)
        wear=np.maximum(wear,line*.52)
    margin=np.minimum(v,1-v)
    lip=np.exp(-(margin/.026)**2)*np.clip(.34+.16*rub+.21*broad+.23*linear,.04,.95)
    tip=np.exp(-((u-1)/.035)**2)*.24
    root=np.exp(-(u/.27)**2)
    spine=np.exp(-((v-.51)/(.010+.005*u))**2)*(1-u)**.74
    scum=np.exp(-((margin-.061)/.031)**2)*np.clip(.41+.23*rub+.34*broad,0,1)
    height=.19*brushing+.050*grain+.33*wear-.13*scum
    slope_u=(np.roll(height,1,1)-np.roll(height,-1,1))*.16
    slope_v=(np.roll(height,1,0)-np.roll(height,-1,0))*.25
    length=np.sqrt(1+slope_u**2+slope_v**2)
    norm=image('rolled-vane-grain',np.stack((.5+.5*slope_u/length,.5+.5*slope_v/length,.5+.5/length),-1)*255,'Non-Color')
    stocks={
        'bronze':((132,105,81),(187,158,124),.88,.275),
        'umber': ((109,91,78),(174,151,126),.86,.292),
        'dark':  ((83,73,66),(157,145,130),.82,.318),
        'ivory': ((222,215,201),(156,142,121),.23,.285),
        'bone':  ((196,184,164),(145,131,106),.27,.325)}
    for tag,(base,edge,metal,rough) in stocks.items():
        ceramic=tag in ('ivory','bone')
        label='plate_'+tag
        mat=bpy.data.materials.new(('Fired enamel · ' if ceramic else 'Hand-finished plate · ')+tag)
        mat['stock']=label;mat.use_nodes=True
        mat.diffuse_color=(*[((k/255+.055)/1.055)**2.4 for k in base],1)
        mat.metallic=metal;mat.roughness=rough
        color=np.array(base)[None,None,:]
        tone=1+(.025*broad+.013*rub+.017*brushing+.009*grain)*(.63 if ceramic else 1)-root*(.073 if ceramic else .21)
        tone-=scum*(.09 if ceramic else .16)
        tone+=spine*(.028 if ceramic else .082)
        erosion=np.clip(.57*lip+tip+.38*wear*(.30+.70*u),0,.81)
        shade=color*tone[:,:,None]
        rgb=shade+(np.asarray(edge)-shade)*erosion[:,:,None]
        # Buffing follows each feather. The raised keel and exposed hem reflect a
        # narrower light strip than the protected root and the patinated recess.
        r=np.clip(rough+.026*rub+.016*brushing+.058*root+.043*scum
                  -.088*wear-.078*lip-.045*spine,.135,.53)
        m=np.clip(metal+erosion*(.44 if ceramic else .11),0,1)
        orm=np.stack((np.ones_like(r),r,m),axis=-1)*255
        nt=mat.node_tree;shader=nt.nodes.get('Principled BSDF')
        def texture(name,arr,space):
            t=nt.nodes.new('ShaderNodeTexImage');t.image=image(name,arr,space);t.extension='EXTEND';return t
        col=texture(label+' base',rgb,'sRGB');nt.links.new(col.outputs[0],shader.inputs['Base Color'])
        rm=texture(label+' roughness-metal',orm,'Non-Color')
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(rm.outputs[0],sep.inputs[0])
        nt.links.new(sep.outputs[1],shader.inputs['Roughness']);nt.links.new(sep.outputs[2],shader.inputs['Metallic'])
        bump=nt.nodes.new('ShaderNodeTexImage');bump.image=norm;bump.extension='EXTEND'
        nm=nt.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.17 if ceramic else .41
        nt.links.new(bump.outputs[0],nm.inputs['Color']);nt.links.new(nm.outputs[0],shader.inputs['Normal'])
        shader.inputs['Coat Weight'].default_value=.35 if ceramic else .28
        shader.inputs['Coat Roughness'].default_value=.175 if ceramic else .19
        if not ceramic:
            shader.inputs['Anisotropic'].default_value=.32
        mats[label]=mat

def station_uv(mesh,per_ring,stations,cross_sections,repeat=False):
    layer=mesh.uv_layers.active
    for i,loop in enumerate(mesh.loops):
        v=loop.vertex_index
        if repeat:v%=len(stations)*per_ring
        row,col=divmod(v,per_ring)
        layer.data[i].uv=(stations[row],cross_sections[col]*.5+.5)
