#!/usr/bin/env python3
"""Deterministically generate the static greenhouse (design v1.4). No robot."""
import math
import random
import struct
import zlib
from pathlib import Path
import xml.etree.ElementTree as E
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'src/ai_robot_sim'

def sub(p, tag, value=None, **attrs):
    e = E.SubElement(p, tag, attrs)
    if value is not None: e.text = str(value)
    return e

def save(path, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    E.indent(root)
    path.write_text(E.tostring(root, encoding='unicode') + '\n')

def model(name):
    s = E.Element('sdf', version='1.6'); m = sub(s, 'model', name=name)
    sub(m, 'static', 'true'); return s, sub(m, 'link', name='body')

def shape(link, name, pose, kind, size, color, collision=True):
    for tag in (['visual', 'collision'] if collision else ['visual']):
        el = sub(link, tag, name=name + '_' + tag); sub(el, 'pose', pose)
        g = sub(el, 'geometry'); geo = sub(g, kind)
        if kind == 'box': sub(geo, 'size', size)
        elif kind == 'sphere': sub(geo, 'radius', size)
        else: sub(geo, 'uri', size)
        if tag == 'visual':
            mat = sub(el, 'material'); sub(mat, 'ambient', color); sub(mat, 'diffuse', color)
            texture = 'soil' if name == 'soil' else 'substrate' if name == 'substrate' else 'concrete' if name in ('base', 'passage') else 'foliage' if name == 'tomato_row' else None
            if texture:
                mat.find('ambient').text='1 1 1 1'
                mat.find('diffuse').text='1 1 1 1'
                script = sub(mat, 'script')
                owner = 'greenhouse_track_pair' if texture == 'concrete' else 'greenhouse_planting_unit'
                sub(script, 'uri', f'model://{owner}/materials/scripts')
                sub(script, 'uri', f'model://{owner}/materials/textures')
                sub(script, 'name', f'Greenhouse/{texture}')
            sub(mat, 'specular', '0.16 0.16 0.12 1' if name == 'rail' else '0.015 0.015 0.015 1')
        else:
            surface = sub(el, 'surface'); fr = sub(surface, 'friction'); ode = sub(fr, 'ode')
            sub(ode, 'mu', '0.8'); sub(ode, 'mu2', '0.8')

def config(name):
    m = E.Element('model'); sub(m, 'name', name); sub(m, 'version', '1.0')
    sub(m, 'sdf', 'model.sdf', version='1.6'); sub(m, 'description', 'Static greenhouse design v1.4; generated locally.')
    save(BASE/'models'/name/'model.config', m)

def rail_mesh(path):
    # One closed tube, no overlapping primitive joints. Outer far end x=-15;
    # near connector centre x=15.23. Rounded rectangle centreline R=.06.
    r=.06; tube=.025; left=-15+tube; right=15.23; y=.275
    pts=[]
    corners=[(right-r,y-r,0), (left+r,y-r,90), (left+r,-y+r,180), (right-r,-y+r,270)]
    # CCW path: right-upper corner then upper straight, etc.
    for cx,cy,start in corners:
        for k in range(33):
            a=math.radians(start+90*k/32)
            pts.append((cx+r*math.cos(a),cy+r*math.sin(a),math.cos(a),math.sin(a)))
    verts=[]
    for x,yy,nx,ny in pts:
        for k in range(32):
            a=2*math.pi*k/32
            verts.append((x+tube*math.cos(a)*nx, yy+tube*math.cos(a)*ny, .325+tube*math.sin(a)))
    faces=[]; n=len(pts)
    for i in range(n):
        for j in range(32):
            a=i*32+j; b=((i+1)%n)*32+j; c=((i+1)%n)*32+(j+1)%32; d=i*32+(j+1)%32
            # outward winding for this CCW tube
            faces.extend([(a,b,c),(a,c,d)])
    # Collada asset with explicit metre units and Z-up.
    ns='http://www.collada.org/2005/11/COLLADASchema'
    root=E.Element('COLLADA', xmlns=ns, version='1.4.1'); asset=sub(root,'asset')
    sub(asset,'unit',name='meter',meter='1'); sub(asset,'up_axis','Z_UP')
    lib=sub(root,'library_geometries'); geom=sub(lib,'geometry',id='rail'); mesh=sub(geom,'mesh')
    source=sub(mesh,'source',id='positions'); sub(source,'float_array',' '.join(f'{v:.9f}' for p in verts for v in p),id='positions-array',count=str(len(verts)*3))
    tech=sub(source,'technique_common'); acc=sub(tech,'accessor',source='#positions-array',count=str(len(verts)),stride='3')
    for axis in 'XYZ': sub(acc,'param',name=axis,type='float')
    vs=sub(mesh,'vertices',id='vertices'); sub(vs,'input',semantic='POSITION',source='#positions')
    tris=sub(mesh,'triangles',count=str(len(faces))); sub(tris,'input',semantic='VERTEX',source='#vertices',offset='0')
    sub(tris,'p',' '.join(str(v) for f in faces for v in f))
    scenes=sub(root,'library_visual_scenes'); scene=sub(scenes,'visual_scene',id='Scene'); node=sub(scene,'node',id='rail-node'); sub(node,'instance_geometry',url='#rail')
    sub(sub(root,'scene'),'instance_visual_scene',url='#Scene'); save(path,root)

def textures():
    for name, rgb, amplitude, owner in [('soil',(91,57,29),12,'greenhouse_planting_unit'),('substrate',(53,29,13),9,'greenhouse_planting_unit'),('foliage',(28,91,25),15,'greenhouse_planting_unit'),('concrete',(158,158,149),5,'greenhouse_track_pair')]:
        rng=random.Random(name); width=256
        rows=[]
        for y in range(width):
            row=bytearray([0])
            for x in range(width):
                noise=rng.randint(-amplitude,amplitude)
                row.extend(max(0,min(255,c+noise)) for c in rgb)
            rows.append(bytes(row))
        def chunk(tag,data):
            return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
        png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,width,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')
        directory=BASE/'models'/owner/'materials'
        (directory/'textures').mkdir(parents=True,exist_ok=True)
        (directory/'textures'/f'{name}.png').write_bytes(png)
        (directory/'scripts').mkdir(parents=True,exist_ok=True)
        # White modulation preserves texture colour; matte specular.
        material = ("material Greenhouse/"+name+"\n{\n"
                    "  technique\n  {\n    pass\n    {\n"
                    "      ambient 1 1 1 1\n      diffuse 1 1 1 1\n"
                    "      specular 0.01 0.01 0.01 1 8\n"
                    "      texture_unit\n      {\n        texture "+name+".png\n"
                    "        scale 12 12\n      }\n    }\n  }\n}\n")
        (directory/'scripts'/f'{name}.material').write_text(material)

def generate():
    textures()
    s,l=model('greenhouse_planting_unit')
    shape(l,'substrate','0 0 1.045 0 0 0','box','30 .25 .01','.16 .075 .025 1',False)
    shape(l,'tomato_row','0 0 1.55 0 0 0','box','30 .5 1','.075 .28 .065 1')
    for i in range(10):
        # All accents fully inside the specified row envelope.
        shape(l,f'fruit_{i}',f'{-13.5+3*i} {(.215 if i%2 else -.215)} {1.25+(i%3)*.22} 0 0 0','sphere','.035','.72 .035 .02 1',False)
    save(BASE/'models/greenhouse_planting_unit/model.sdf',s); config('greenhouse_planting_unit')
    s,l=model('greenhouse_track_pair')
    shape(l,'base','0 0 .15 0 0 0','box','30 .7 .3','.58 .58 .55 1')
    shape(l,'rail','0 0 0 0 0 0','mesh','model://greenhouse_track_pair/meshes/rail.dae','.95 .67 .035 1')
    save(BASE/'models/greenhouse_track_pair/model.sdf',s); config('greenhouse_track_pair')
    rail_mesh(BASE/'models/greenhouse_track_pair/meshes/rail.dae')
    s=E.Element('sdf',version='1.6'); w=sub(s,'world',name='greenhouse_env')
    sub(sub(w,'include'),'uri','model://sun')
    gui=sub(w,'gui'); camera=sub(gui,'camera',name='user_camera')
    sub(camera,'pose','0 0 85 0 1.570796327 0'); sub(camera,'view_controller','orbit'); sub(camera,'projection_type','perspective')
    physics=sub(w,'physics',name='default_physics',type='ode'); sub(physics,'max_step_size','.001'); sub(physics,'real_time_update_rate','1000')
    env=sub(w,'model',name='greenhouse_structure'); sub(env,'static','true'); sub(env,'pose','-31.5 -22.075 0 0 0 0'); l=sub(env,'link',name='structure')
    shape(l,'soil','31.5 22.075 -.1 0 0 0','box','63 44.15 .2','.29 .17 .085 1')
    shape(l,'passage','31.5 22.075 .15 0 0 0','box','3 44.15 .3','.58 .58 .55 1')
    for name,pose,size in [('west','-.0575 22.075 1 0 0 0','.115 44.38 2'),('east','63.0575 22.075 1 0 0 0','.115 44.38 2'),('north','31.5 44.2075 1 0 0 0','63 .115 2'),('south_a','15 -.0575 1 0 0 0','30 .115 2'),('south_b','48 -.0575 1 0 0 0','30 .115 2')]:
        shape(l,name,pose,'box',size,'.48 .25 .17 1')
    for b,x in enumerate([15,48],1):
        for i in range(30):
            inc=sub(w,'include'); sub(inc,'uri','model://greenhouse_planting_unit'); sub(inc,'name',f'planting_{b}_{i:02}'); sub(inc,'pose',f'{x-31.5} {.325+1.5*i-22.075:.3f} 0 0 0 0')
        for j in range(29):
            inc=sub(w,'include'); sub(inc,'uri','model://greenhouse_track_pair'); sub(inc,'name',f'track_{b}_{j:02}'); sub(inc,'pose',f'{x-31.5} {1.075+1.5*j-22.075:.3f} 0 0 0 {0 if b==1 else math.pi:.9f}')
    save(BASE/'worlds/greenhouse_env.world',s)
if __name__=='__main__': generate()
