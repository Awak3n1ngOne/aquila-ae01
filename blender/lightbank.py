"""A calibrated, latitude-longitude product studio shared by Cycles and the web viewer."""
from pathlib import Path
import struct
import zlib
import numpy as np

RANGE = 24.0
# Both renderers decode the same linear radiance from the compact sRGB panorama.
ENVIRONMENT_INTENSITY = RANGE * .65

def write_studio(path):
    width, height = 1024, 512
    x = 2*np.pi*(.5-(np.arange(width)+.5)/width)
    z = np.pi*(.5-(np.arange(height)+.5)/height)
    zz, xx = np.meshgrid(z,x,indexing='ij')
    rays = np.stack((np.cos(zz)*np.cos(xx), np.cos(zz)*np.sin(xx), np.sin(zz)), axis=-1)
    sky = .025+.03*np.clip(rays[:,:,2],0,1)
    floor = np.clip((-rays[:,:,2]-.12)/.80,0,1)
    field = sky[:,:,None]*np.array([.94,.95,1.00])+floor[:,:,None]*np.array([.22,.16,.105])

    def panel(direction, width, height, tint, intensity, edge, tilt=0):
        direction = np.asarray(direction,dtype=float)
        direction /= np.linalg.norm(direction)
        right = np.cross((0,0,1),direction)
        right /= np.linalg.norm(right)
        up = np.cross(direction,right)
        c,s = np.cos(tilt),np.sin(tilt)
        right,up = c*right+s*up,c*up-s*right
        toward = rays@direction
        divisor = np.maximum(toward,.001)
        u = (rays@right)/divisor/width
        v = (rays@up)/divisor/height
        rect = np.maximum(np.abs(u),np.abs(v))
        coverage = np.clip((1-rect)/edge+.5,0,1)
        coverage *= (toward>0)
        # A diffusion frame with a brighter end and a visible narrow aluminium rim.
        grad = np.clip(.68+.22*v-.12*u,.38,1.10)
        rim = np.exp(-((rect-.955)/.022)**2)*.21
        field[:] += (coverage*(grad+rim)*intensity)[:,:,None]*tint

    panel((-3.8,-4.8,6.8),.62,.37,np.array([1.0,.925,.82]),8.6,.23,-.22)
    panel((4.8,-1.9,2.0),.110,.78,np.array([1.0,.97,.91]),14.3,.16,.16)
    panel((4.3,3.3,4.3),.52,.145,np.array([.82,.91,1.0]),10.8,.19,-.36)
    panel((-4.1,3.4,.8),.135,.65,np.array([1.0,.86,.71]),8.5,.19,-.10)
    panel((.1,3.5,-2.8),.39,.20,np.array([.78,.83,.88]),1.0,.26,.08)
    panel((.6,-6.2,-.1),.49,.235,np.array([1.0,.95,.88]),2.7,.43,-.05)
    # Separated stripboxes leave dark bands between their reflections. The tall
    # strip travels along the wing vanes; the low rear strip catches the dorsal side.
    panel((-4.6,-3.7,1.45),.094,.66,np.array([.86,.94,1.0]),14.6,.20,-.20)
    panel((1.7,-5.9,3.4),.47,.093,np.array([1.0,.97,.91]),10.4,.22,.32)
    panel((.9,5.8,1.3),.49,.100,np.array([.89,.94,1.0]),9.4,.22,.12)
    data = np.clip(field/RANGE,0,1)
    encoded=np.where(data<=.0031308,12.92*data,1.055*data**(1/2.4)-.055)
    raw=b''.join(b'\0'+row.tobytes() for row in np.uint8(encoded*255+.5))
    def chunk(name,body):
        return struct.pack('>I',len(body))+name+body+struct.pack('>I',zlib.crc32(name+body)&0xffffffff)
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))
