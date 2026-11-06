#!/usr/bin/env python3
"""Deterministically generate the static greenhouse (design v1.8). No robot."""
import argparse
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

def gable_panel_mesh(path, half_width, eave_z, ridge_z, thickness=.01):
    """Write a closed triangular glass-panel prism in local X/Y/Z coordinates."""
    ns='http://www.collada.org/2005/11/COLLADASchema'
    E.register_namespace('',ns)
    def tag(parent, tag_name, **attrs):
        return E.SubElement(parent, f'{{{ns}}}{tag_name}', attrs)
    root=E.Element(f'{{{ns}}}COLLADA', {'version':'1.4.1'})
    asset=tag(root,'asset'); unit=tag(asset,'unit',name='meter',meter='1'); tag(asset,'up_axis').text='Z_UP'
    lib=tag(root,'library_geometries'); geom=tag(lib,'geometry',id='gable_panel'); mesh=tag(geom,'mesh')
    vertices=[(-thickness/2,-half_width,eave_z),(-thickness/2,half_width,eave_z),(-thickness/2,0,ridge_z),
              ( thickness/2,-half_width,eave_z),( thickness/2,half_width,eave_z),( thickness/2,0,ridge_z)]
    src=tag(mesh,'source',id='gable_positions')
    vals=' '.join(f'{v:.9f}' for point in vertices for v in point)
    tag(src,'float_array',id='gable_positions_array',count=str(len(vertices)*3)).text=vals
    common=tag(src,'technique_common'); accessor=tag(common,'accessor',source='#gable_positions_array',count=str(len(vertices)),stride='3')
    for axis in 'XYZ': tag(accessor,'param',name=axis,type='float')
    verts=tag(mesh,'vertices',id='gable_vertices'); tag(verts,'input',semantic='POSITION',source='#gable_positions')
    tris=[(0,2,1),(3,4,5),(0,1,4),(0,4,3),(1,2,5),(1,5,4),(2,0,3),(2,3,5)]
    tri=tag(mesh,'triangles',count=str(len(tris))); tag(tri,'input',semantic='VERTEX',source='#gable_vertices',offset='0')
    tag(tri,'p').text=' '.join(str(i) for face in tris for i in face)
    scene=tag(root,'library_visual_scenes'); visual_scene=tag(scene,'visual_scene',id='Scene')
    node=tag(visual_scene,'node',id='gable-panel-node'); tag(node,'instance_geometry',url='#gable_panel')
    scene_root=tag(root,'scene'); tag(scene_root,'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True); E.indent(root)
    path.write_text(E.tostring(root,encoding='unicode')+'\n')

def vertical_glass_panel_mesh(path):
    """Write a centered, closed unit rectangular prism for vertical glass."""
    ns='http://www.collada.org/2005/11/COLLADASchema'
    E.register_namespace('',ns)
    def tag(parent, tag_name, **attrs):
        return E.SubElement(parent, f'{{{ns}}}{tag_name}', attrs)
    root=E.Element(f'{{{ns}}}COLLADA', {'version':'1.4.1'})
    asset=tag(root,'asset'); tag(asset,'unit',name='meter',meter='1'); tag(asset,'up_axis').text='Z_UP'
    # Local X is panel thickness, Y is panel width, Z is panel height.
    vertices=[(-.5,-.5,-.5),(-.5,.5,-.5),(-.5,.5,.5),(-.5,-.5,.5),
              (.5,-.5,-.5),(.5,.5,-.5),(.5,.5,.5),(.5,-.5,.5)]
    lib=tag(root,'library_geometries'); geom=tag(lib,'geometry',id='vertical_glass_panel'); mesh=tag(geom,'mesh')
    src=tag(mesh,'source',id='vertical_glass_positions')
    tag(src,'float_array',id='vertical_glass_positions_array',count=str(len(vertices)*3)).text=' '.join(f'{v:.1f}' for p in vertices for v in p)
    common=tag(src,'technique_common'); accessor=tag(common,'accessor',source='#vertical_glass_positions_array',count=str(len(vertices)),stride='3')
    for axis in 'XYZ': tag(accessor,'param',name=axis,type='float')
    verts=tag(mesh,'vertices',id='vertical_glass_vertices'); tag(verts,'input',semantic='POSITION',source='#vertical_glass_positions')
    faces=[(0,3,2),(0,2,1),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
           (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    tri=tag(mesh,'triangles',count=str(len(faces))); tag(tri,'input',semantic='VERTEX',source='#vertical_glass_vertices',offset='0')
    tag(tri,'p').text=' '.join(str(i) for face in faces for i in face)
    scene=tag(root,'library_visual_scenes'); visual_scene=tag(scene,'visual_scene',id='Scene')
    node=tag(visual_scene,'node',id='vertical-glass-panel-node'); tag(node,'instance_geometry',url='#vertical_glass_panel')
    scene_root=tag(root,'scene'); tag(scene_root,'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True); E.indent(root)
    path.write_text(E.tostring(root,encoding='unicode')+'\n')

def greenhouse_door_post_mesh(path):
    """Write a post-only DAE so the entrance jamb uses the frame mesh renderer."""
    ns='http://www.collada.org/2005/11/COLLADASchema'
    E.register_namespace('',ns)
    def tag(parent, tag_name, **attrs):
        return E.SubElement(parent, f'{{{ns}}}{tag_name}', attrs)
    root=E.Element(f'{{{ns}}}COLLADA', {'version':'1.4.1'})
    asset=tag(root,'asset'); tag(asset,'unit',name='meter',meter='1'); tag(asset,'up_axis').text='Z_UP'
    vertices=[(-.025,-.025,-1.2),(-.025,.025,-1.2),(-.025,.025,1.2),(-.025,-.025,1.2),
              (.025,-.025,-1.2),(.025,.025,-1.2),(.025,.025,1.2),(.025,-.025,1.2)]
    lib=tag(root,'library_geometries'); geom=tag(lib,'geometry',id='door_post'); mesh=tag(geom,'mesh')
    src=tag(mesh,'source',id='door_post_positions')
    tag(src,'float_array',id='door_post_positions_array',count=str(len(vertices)*3)).text=' '.join(f'{v:.9f}' for p in vertices for v in p)
    common=tag(src,'technique_common'); accessor=tag(common,'accessor',source='#door_post_positions_array',count=str(len(vertices)),stride='3')
    for axis in 'XYZ': tag(accessor,'param',name=axis,type='float')
    verts=tag(mesh,'vertices',id='door_post_vertices'); tag(verts,'input',semantic='POSITION',source='#door_post_positions')
    faces=[(0,3,2),(0,2,1),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
           (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    normals=[]
    for a,b,c in faces:
        pa,pb,pc=vertices[a],vertices[b],vertices[c]
        ab=tuple(pb[i]-pa[i] for i in range(3)); ac=tuple(pc[i]-pa[i] for i in range(3))
        normal=(ab[1]*ac[2]-ab[2]*ac[1],
                ab[2]*ac[0]-ab[0]*ac[2],
                ab[0]*ac[1]-ab[1]*ac[0])
        magnitude=math.sqrt(sum(value*value for value in normal))
        if magnitude<1e-9: raise ValueError('door post contains a degenerate triangle')
        normals.append(tuple(value/magnitude for value in normal))
    normal_src=tag(mesh,'source',id='door_post_normals')
    tag(normal_src,'float_array',id='door_post_normals_array',count=str(len(normals)*3)).text=' '.join(f'{v:.9f}' for n in normals for v in n)
    normal_common=tag(normal_src,'technique_common'); normal_accessor=tag(normal_common,'accessor',source='#door_post_normals_array',count=str(len(normals)),stride='3')
    for axis in 'XYZ': tag(normal_accessor,'param',name=axis,type='float')
    tri=tag(mesh,'triangles',count=str(len(faces)))
    tag(tri,'input',semantic='VERTEX',source='#door_post_vertices',offset='0')
    tag(tri,'input',semantic='NORMAL',source='#door_post_normals',offset='1')
    tag(tri,'p').text=' '.join(f'{vertex} {face_index}' for face_index,face in enumerate(faces) for vertex in face)
    scenes=tag(root,'library_visual_scenes'); scene=tag(scenes,'visual_scene',id='Scene')
    node=tag(scene,'node',id='door-post-node'); tag(node,'instance_geometry',url='#door_post')
    tag(tag(root,'scene'),'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True); E.indent(root)
    path.write_text(E.tostring(root,encoding='unicode')+'\n')

def greenhouse_eave_joint_mesh(path, side='left', include_eave_post=True):
    """Write one watertight half-portal visual with a rounded eave joint."""
    eps=1e-9
    def sub2(a,b): return (a[0]-b[0],a[1]-b[1])
    def cross(a,b): return a[0]*b[1]-a[1]*b[0]
    def clipped_interval(a,b,poly):
        d=sub2(b,a); lo,hi=0.0,1.0
        for p,q in zip(poly,poly[1:]+poly[:1]):
            edge=sub2(q,p); f0=cross(edge,sub2(a,p)); fd=cross(edge,d)
            if abs(fd)<1e-12:
                if f0 < -eps: return None
            elif fd>0: lo=max(lo,-f0/fd)
            else: hi=min(hi,-f0/fd)
            if lo>hi+eps: return None
        lo=max(0.0,lo); hi=min(1.0,hi)
        return (lo,hi) if hi-lo>eps else None
    def union_outline(polygons):
        segments=[]
        for i,poly in enumerate(polygons):
            for a,b in zip(poly,poly[1:]+poly[:1]):
                covered=[]
                for j,other in enumerate(polygons):
                    if j==i: continue
                    interval=clipped_interval(a,b,other)
                    if interval: covered.append(interval)
                covered.sort(); merged=[]
                for lo,hi in covered:
                    if merged and lo<=merged[-1][1]+eps:
                        merged[-1]=(merged[-1][0],max(merged[-1][1],hi))
                    else: merged.append((lo,hi))
                kept=[]; cursor=0.0
                for lo,hi in merged:
                    if lo-cursor>eps: kept.append((cursor,lo))
                    cursor=max(cursor,hi)
                if 1.0-cursor>eps: kept.append((cursor,1.0))
                d=sub2(b,a)
                for lo,hi in kept:
                    segments.append(((a[0]+d[0]*lo,a[1]+d[1]*lo),
                                     (a[0]+d[0]*hi,a[1]+d[1]*hi)))
        def key(p): return tuple(round(v,8) for v in p)
        outgoing={}
        for i,(a,_) in enumerate(segments): outgoing.setdefault(key(a),[]).append(i)
        used=set(); loops=[]
        for first,(a,_) in enumerate(segments):
            if first in used: continue
            loop=[a]; current=first
            for _ in range(len(segments)+1):
                used.add(current); _,end=segments[current]; loop.append(end)
                if key(end)==key(loop[0]): break
                choices=[idx for idx in outgoing.get(key(end),[]) if idx not in used]
                if len(choices)!=1: raise ValueError('eave joint outline is not a simple closed boundary')
                current=choices[0]
            if key(loop[-1])!=key(loop[0]): raise ValueError('open eave joint boundary')
            loops.append(loop[:-1])
        if not loops: raise ValueError('portal frame has no closed boundary')
        return loops
    def add_roundovers(poly,radius=.005):
        result=[]; n=len(poly)
        for i,v in enumerate(poly):
            near_eave=min(abs(v[0]+.0575),abs(v[0]-44.2075))<.5
            if not ((abs(v[1]-2.55)<1e-7 and near_eave) or
                    (min(abs(v[0]+.0575),abs(v[0]-44.2075))<1e-7 and abs(v[1]-2.5)<1e-7)):
                result.append(v); continue
            prev=poly[(i-1)%n]; nxt=poly[(i+1)%n]
            u=sub2(prev,v); w=sub2(nxt,v)
            lu=math.hypot(*u); lw=math.hypot(*w); u=(u[0]/lu,u[1]/lu); w=(w[0]/lw,w[1]/lw)
            angle=math.acos(max(-1.0,min(1.0,u[0]*w[0]+u[1]*w[1])))
            if angle<1e-5 or math.pi-angle<1e-5: result.append(v); continue
            distance=radius/math.tan(angle/2)
            center_distance=radius/math.sin(angle/2)
            bis=(u[0]+w[0],u[1]+w[1]); bl=math.hypot(*bis); bis=(bis[0]/bl,bis[1]/bl)
            center=(v[0]+bis[0]*center_distance,v[1]+bis[1]*center_distance)
            start=(v[0]+u[0]*distance,v[1]+u[1]*distance)
            finish=(v[0]+w[0]*distance,v[1]+w[1]*distance)
            a0=math.atan2(start[1]-center[1],start[0]-center[0])
            a1=math.atan2(finish[1]-center[1],finish[0]-center[0])
            delta=(a1-a0+math.pi)%(2*math.pi)-math.pi
            result.append(start)
            for k in range(1,4):
                a=a0+delta*k/4
                result.append((center[0]+radius*math.cos(a),center[1]+radius*math.sin(a)))
            result.append(finish)
        return result
    def triangulate(poly):
        ids=list(range(len(poly))); triangles=[]
        orient=sum(cross(poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly)))/2
        if orient<0: ids.reverse()
        def in_tri(p,a,b,c):
            return cross(sub2(b,a),sub2(p,a))>=-eps and cross(sub2(c,b),sub2(p,b))>=-eps and cross(sub2(a,c),sub2(p,c))>=-eps
        while len(ids)>3:
            found=False
            for j in range(len(ids)):
                ia,ib,ic=ids[j-1],ids[j],ids[(j+1)%len(ids)]; a,b,c=poly[ia],poly[ib],poly[ic]
                if cross(sub2(b,a),sub2(c,b))<=eps: continue
                if any(in_tri(poly[k],a,b,c) for k in ids if k not in (ia,ib,ic)): continue
                triangles.append((ia,ib,ic)); ids.pop(j); found=True; break
            if not found: raise ValueError('could not triangulate eave joint outline')
        triangles.append(tuple(ids))
        return triangles

    theta=math.radians(10.0); z0=2.5; y_south=-.0575; y_north=44.2075; y_ridge=22.075
    z_ridge=z0+(y_ridge-y_south)*math.tan(theta)
    if side not in ('left','right'): raise ValueError('portal side must be left or right')
    eave=y_south if side=='left' else y_north
    tip=y_ridge
    polygons=[]
    if include_eave_post:
        polygons.append([(eave-.025,.1),(eave+.025,.1),(eave+.025,2.5),(eave-.025,2.5)])
    tie_lo,tie_hi=sorted((eave,tip))
    polygons.append([(tie_lo,2.45),(tie_hi,2.45),(tie_hi,2.55),(tie_lo,2.55)])
    dy,dz=tip-eave,z_ridge-z0; length=math.hypot(dy,dz)
    normal=(-dz/length,dy/length); half=.05
    polygons.append([(eave-half*normal[0],z0-half*normal[1]),
                     (tip-half*normal[0],z_ridge-half*normal[1]),
                     (tip+half*normal[0],z_ridge+half*normal[1]),
                     (eave+half*normal[0],z0+half*normal[1])])
    gable_stations=[y for y in positions(-.115,44.265,2.0) if 0<y<44.15]
    purlin_ys=([-0.08625,*[y for y in gable_stations if y<y_ridge],y_ridge]
               if side=='left' else [y_ridge,*[y for y in gable_stations if y>y_ridge],44.23625])
    for y in purlin_ys:
        z=z0+min(max(y,0.0),max(44.15-y,0.0))*math.tan(theta)
        polygons.append([(y-.025,z-.025),(y+.025,z-.025),(y+.025,z+.025),(y-.025,z+.025)])
    outlines=union_outline(polygons)
    vertices=[]; faces=[]
    for raw_outline in outlines:
        outline=add_roundovers(raw_outline)
        cap_tris=triangulate(outline); count=len(outline); base=len(vertices)
        vertices.extend([(-.025,y,z) for y,z in outline]+[(.025,y,z) for y,z in outline])
        for a,b,c in cap_tris: faces.append((base+a,base+c,base+b))
        for a,b,c in cap_tris: faces.append((base+count+a,base+count+b,base+count+c))
        for i in range(count):
            j=(i+1)%count; faces.extend(((base+i,base+j,base+count+j),(base+i,base+count+j,base+count+i)))
    normals=[]
    for a,b,c in faces:
        pa,pb,pc=vertices[a],vertices[b],vertices[c]
        ab=tuple(pb[i]-pa[i] for i in range(3)); ac=tuple(pc[i]-pa[i] for i in range(3))
        normal=(ab[1]*ac[2]-ab[2]*ac[1],
                ab[2]*ac[0]-ab[0]*ac[2],
                ab[0]*ac[1]-ab[1]*ac[0])
        magnitude=math.sqrt(sum(value*value for value in normal))
        if magnitude<eps: raise ValueError('portal frame contains a degenerate triangle')
        normals.append(tuple(value/magnitude for value in normal))

    ns='http://www.collada.org/2005/11/COLLADASchema'; E.register_namespace('',ns)
    def tag(parent,tag_name,**attrs): return E.SubElement(parent,f'{{{ns}}}{tag_name}',attrs)
    root=E.Element(f'{{{ns}}}COLLADA',{'version':'1.4.1'}); asset=tag(root,'asset')
    tag(asset,'unit',name='meter',meter='1'); tag(asset,'up_axis').text='Z_UP'
    lib=tag(root,'library_geometries'); geom=tag(lib,'geometry',id='portal_frame_joints'); mesh=tag(geom,'mesh')
    src=tag(mesh,'source',id='joint_positions')
    tag(src,'float_array',id='joint_positions_array',count=str(len(vertices)*3)).text=' '.join(f'{v:.9f}' for p in vertices for v in p)
    common=tag(src,'technique_common'); accessor=tag(common,'accessor',source='#joint_positions_array',count=str(len(vertices)),stride='3')
    for axis in 'XYZ': tag(accessor,'param',name=axis,type='float')
    normal_src=tag(mesh,'source',id='joint_normals')
    tag(normal_src,'float_array',id='joint_normals_array',count=str(len(normals)*3)).text=' '.join(f'{v:.9f}' for n in normals for v in n)
    normal_common=tag(normal_src,'technique_common')
    normal_accessor=tag(normal_common,'accessor',source='#joint_normals_array',count=str(len(normals)),stride='3')
    for axis in 'XYZ': tag(normal_accessor,'param',name=axis,type='float')
    verts=tag(mesh,'vertices',id='joint_vertices'); tag(verts,'input',semantic='POSITION',source='#joint_positions')
    tris=tag(mesh,'triangles',count=str(len(faces)))
    tag(tris,'input',semantic='VERTEX',source='#joint_vertices',offset='0')
    tag(tris,'input',semantic='NORMAL',source='#joint_normals',offset='1')
    tag(tris,'p').text=' '.join(f'{vertex} {face_index}' for face_index,face in enumerate(faces) for vertex in face)
    scenes=tag(root,'library_visual_scenes'); scene=tag(scenes,'visual_scene',id='Scene')
    node=tag(scene,'node',id='joint-node'); tag(node,'instance_geometry',url='#portal_frame_joints')
    tag(tag(root,'scene'),'instance_visual_scene',url='#Scene')
    path.parent.mkdir(parents=True,exist_ok=True); E.indent(root); path.write_text(E.tostring(root,encoding='unicode')+'\n')

def model(name):
    s = E.Element('sdf', version='1.6'); m = sub(s, 'model', name=name)
    sub(m, 'static', 'true'); return s, sub(m, 'link', name='body')

def shape(link, name, pose, kind, size, color, collision=True, visual=True,
          visual_pose=None, visual_size=None, specular=None):
    if name == 'passage':
        # Keep the textured top face on the original concrete material. Give
        # the two long vertical faces a shared ambient-dominant material so
        # opposite face normals receive nearly equal illumination.
        px, py, pz, rr, rp, ry = map(float, pose.split())
        sx, sy, sz = map(float, size.split())
        for suffix, side_pose, side_size, material_name in [
            ('top', f'{px} {py} {pz + sz / 2 - .0025} {rr} {rp} {ry}',
             f'{sx} {sy} .005', 'passage_concrete'),
            ('side_west', f'{px - sx / 2 + .0025} {py} {pz} {rr} {rp} {ry}',
             f'.005 {sy} {sz}', 'passage_side'),
            ('side_east', f'{px + sx / 2 - .0025} {py} {pz} {rr} {rp} {ry}',
             f'.005 {sy} {sz}', 'passage_side')]:
            visual = sub(link, 'visual', name=f'passage_{suffix}_visual')
            sub(visual, 'pose', side_pose)
            sub(visual, 'cast_shadows', 'false')
            geo = sub(sub(visual, 'geometry'), 'box')
            sub(geo, 'size', side_size)
            mat = sub(visual, 'material')
            if suffix.startswith('side_'):
                sub(mat, 'lighting', 'false')
            sub(mat, 'ambient', '1 1 1 1')
            sub(mat, 'diffuse', '1 1 1 1')
            script = sub(mat, 'script')
            for uri in ('materials/scripts', 'materials/textures'):
                sub(script, 'uri', f'model://greenhouse_track_pair/{uri}')
            sub(script, 'name', f'Greenhouse/{material_name}')
            sub(mat, 'specular', '0.015 0.015 0.015 1')
        exit_cap = sub(link, 'visual', name='passage_exit_end_visual')
        sub(exit_cap, 'pose', f'{px} {py - sy / 2 + .0025} {pz} {rr} {rp} {ry}')
        sub(exit_cap, 'cast_shadows', 'false')
        cap_geo = sub(sub(exit_cap, 'geometry'), 'box')
        sub(cap_geo, 'size', f'{sx} .005 {sz}')
        cap_mat = sub(exit_cap, 'material')
        sub(cap_mat, 'lighting', 'false')
        sub(cap_mat, 'ambient', '1 1 1 1')
        sub(cap_mat, 'diffuse', '1 1 1 1')
        cap_script = sub(cap_mat, 'script')
        for uri in ('materials/scripts', 'materials/textures'):
            sub(cap_script, 'uri', f'model://greenhouse_track_pair/{uri}')
        sub(cap_script, 'name', 'Greenhouse/passage_side')
        sub(cap_mat, 'specular', '0.015 0.015 0.015 1')
        for suffix, line_pose in [
            ('west', f'{px - sx / 2 + .05} {py} {pz + sz / 2 + .001} {rr} {rp} {ry}'),
            ('east', f'{px + sx / 2 - .05} {py} {pz + sz / 2 + .001} {rr} {rp} {ry}')]:
            visual = sub(link, 'visual', name=f'passage_warning_{suffix}_visual')
            sub(visual, 'pose', line_pose)
            sub(visual, 'cast_shadows', 'false')
            geo = sub(sub(visual, 'geometry'), 'box')
            sub(geo, 'size', f'.1 {sy} .002')
            mat = sub(visual, 'material')
            sub(mat, 'ambient', '.98 .86 .08 1')
            sub(mat, 'diffuse', '.98 .86 .08 1')
            sub(mat, 'specular', '0 0 0 1')
        collision_el = sub(link, 'collision', name='passage_collision')
        sub(collision_el, 'pose', pose)
        collision_geo = sub(sub(collision_el, 'geometry'), 'box')
        sub(collision_geo, 'size', size)
        surface = sub(collision_el, 'surface')
        fr = sub(surface, 'friction'); ode = sub(fr, 'ode')
        sub(ode, 'mu', '0.8'); sub(ode, 'mu2', '0.8')
        return
    tags = (['visual'] if visual else []) + (['collision'] if collision else [])
    for tag in tags:
        element_pose=visual_pose if tag=='visual' and visual_pose is not None else pose
        element_size=visual_size if tag=='visual' and visual_size is not None else size
        el = sub(link, tag, name=name + '_' + tag); sub(el, 'pose', element_pose)
        g = sub(el, 'geometry'); geo = sub(g, kind)
        if kind == 'box': sub(geo, 'size', element_size)
        elif kind == 'sphere': sub(geo, 'radius', element_size)
        elif kind == 'plane':
            sub(geo, 'normal', '0 0 1'); sub(geo, 'size', element_size)
        else: sub(geo, 'uri', element_size)
        if tag == 'visual':
            # Greenhouse visuals, including planting beds and both track models,
            # must not cast shadows onto any other scene object.
            sub(el, 'cast_shadows', 'false')
            mat = sub(el, 'material'); sub(mat, 'ambient', color); sub(mat, 'diffuse', color)
            if name in {'west', 'east', 'north', 'south_a', 'south_b'}:
                # Warm light-grey masonry with strong ambient fill and restrained
                # directional response, keeping differently oriented faces closer in tone.
                mat.find('ambient').text = '.78 .76 .72 1'
                mat.find('diffuse').text = '.12 .12 .11 1'
            texture = 'soil' if name == 'soil' else 'substrate' if name == 'substrate' else 'concrete' if name == 'base' else 'passage_concrete' if name == 'passage' else 'foliage' if name == 'tomato_row' else None
            if texture:
                mat.find('ambient').text='1 1 1 1'
                mat.find('diffuse').text='1 1 1 1'
                script = sub(mat, 'script')
                owner = 'greenhouse_track_pair' if texture in {'concrete', 'passage_concrete'} else 'greenhouse_planting_unit'
                sub(script, 'uri', f'model://{owner}/materials/scripts')
                sub(script, 'uri', f'model://{owner}/materials/textures')
                sub(script, 'name', f'Greenhouse/{texture}')
            sub(mat, 'specular', specular or ('0.16 0.16 0.12 1' if name == 'rail' else '0.015 0.015 0.015 1'))
        else:
            surface = sub(el, 'surface'); fr = sub(surface, 'friction'); ode = sub(fr, 'ode')
            sub(ode, 'mu', '0.8'); sub(ode, 'mu2', '0.8')

def glass_wall(link, name, axis, fixed, start, end):
    """Add transparent DAE visual panes and one simple box collision panel."""
    pane_height = 2.4
    thickness = .01
    bottom = .1
    cursor = start
    index = 0
    while cursor < end - 1e-9:
        span = min(2.0, end - cursor)
        center = cursor + span / 2
        if axis == 'x':
            pose = f'{center:.6f} {fixed:.6f} {bottom + pane_height / 2:.6f} 0 0 1.570796327'
        else:
            pose = f'{fixed:.6f} {center:.6f} {bottom + pane_height / 2:.6f} 0 0 0'
        visual = sub(link, 'visual', name=f'glass_{name}_pane_{index:02}')
        sub(visual, 'pose', pose)
        sub(visual, 'cast_shadows', 'false')
        sub(visual, 'transparency', '.62')
        mesh = sub(sub(visual, 'geometry'), 'mesh')
        sub(mesh, 'uri', 'model://greenhouse_vertical_glass_panel/meshes/vertical_glass_panel.dae')
        sub(mesh, 'scale', f'{thickness:.6f} {span:.6f} {pane_height:.6f}')
        mat = sub(visual, 'material')
        sub(mat, 'ambient', '.68 .88 .90 1')
        sub(mat, 'diffuse', '.68 .88 .90 1')
        sub(mat, 'specular', '.82 .94 .96 1')
        cursor += span
        index += 1
    span = end - start
    center = (start + end) / 2
    if axis == 'x':
        pose = f'{center:.6f} {fixed:.6f} {bottom + pane_height / 2:.6f} 0 0 0'
        size = f'{span:.6f} {thickness} {pane_height}'
    else:
        pose = f'{fixed:.6f} {center:.6f} {bottom + pane_height / 2:.6f} 0 0 0'
        size = f'{thickness} {span:.6f} {pane_height}'
    collision = sub(link, 'collision', name=f'glass_{name}_collision')
    sub(collision, 'pose', pose)
    geo = sub(sub(collision, 'geometry'), 'box')
    sub(geo, 'size', size)


def positions(start, end, step):
    values=[]
    value=start
    while value <= end + 1e-9:
        values.append(value)
        value += step
    if not values or end-values[-1] > 1e-6:
        values.append(end)
    return values

def frame_beam(link, name, p1, p2, section_y, section_z, color='.42 .47 .48 1', visual=True, visual_start=None, collision=True):
    """Add a shadow-free box beam aligned between two world points."""
    def beam_pose_size(start, end):
        dx,dy,dz=(end[i]-start[i] for i in range(3))
        length=math.sqrt(dx*dx+dy*dy+dz*dz)
        horizontal=math.hypot(dx,dy)
        yaw=math.atan2(dy,dx)
        pitch=-math.atan2(dz,horizontal)
        pose=f'{(start[0]+end[0])/2:.6f} {(start[1]+end[1])/2:.6f} {(start[2]+end[2])/2:.6f} 0 {pitch:.9f} {yaw:.9f}'
        return pose,f'{length:.6f} {section_y:.6f} {section_z:.6f}'
    if visual:
        visual_pose,visual_size=beam_pose_size(visual_start or p1,p2)
        visual_el=sub(link,'visual',name=f'{name}_visual'); sub(visual_el,'pose',visual_pose); sub(visual_el,'cast_shadows','false')
        geo=sub(sub(visual_el,'geometry'),'box'); sub(geo,'size',visual_size)
        mat=sub(visual_el,'material'); sub(mat,'ambient',color); sub(mat,'diffuse',color); sub(mat,'specular','.12 .13 .13 1')
    if collision:
        pose,size=beam_pose_size(p1,p2)
        collision_el=sub(link,'collision',name=f'{name}_collision'); sub(collision_el,'pose',pose)
        geo=sub(sub(collision_el,'geometry'),'box'); sub(geo,'size',size)

def glass_roof(link, side, x0, x1, y_eave, z_eave, ridge_y, z_ridge, slope_angle):
    """Add 2 m roof glazing, a continuous collision sheet, and eave-to-ridge geometry."""
    direction=1 if y_eave < ridge_y else -1
    slope_length=math.hypot(ridge_y-y_eave,z_ridge-z_eave)
    roll=slope_angle*direction
    xcuts=positions(x0,x1,2.0)
    for ix,(xa,xb) in enumerate(zip(xcuts,xcuts[1:])):
        for js in range(math.ceil(slope_length/2.0)):
            d0=js*2.0; d1=min(slope_length,(js+1)*2.0); dc=(d0+d1)/2
            yy=y_eave+direction*dc*math.cos(slope_angle)
            zz=z_eave+dc*math.sin(slope_angle)
            visual=sub(link,'visual',name=f'glass_roof_{side}_{ix:02}_{js:02}')
            sub(visual,'pose',f'{(xa+xb)/2:.6f} {yy:.6f} {zz:.6f} {roll:.9f} 0 0')
            sub(visual,'cast_shadows','false'); sub(visual,'transparency','.62')
            geo=sub(sub(visual,'geometry'),'box'); sub(geo,'size',f'{xb-xa:.6f} {d1-d0:.6f} .01')
            mat=sub(visual,'material'); sub(mat,'ambient','.68 .88 .90 1'); sub(mat,'diffuse','.68 .88 .90 1'); sub(mat,'specular','.82 .94 .96 1')
    collision=sub(link,'collision',name=f'glass_roof_{side}_collision')
    center_y=(y_eave+ridge_y)/2; center_z=(z_eave+z_ridge)/2
    sub(collision,'pose',f'{(x0+x1)/2:.6f} {center_y:.6f} {center_z:.6f} {roll:.9f} 0 0')
    geo=sub(sub(collision,'geometry'),'box'); sub(geo,'size',f'{x1-x0:.6f} {slope_length:.6f} .01')

def greenhouse_frame(link):
    """Add perimeter posts and a light gable roof frame aligned to glazing modules."""
    z_eave=2.5; half_width=44.15/2; pitch=math.radians(10.0)
    z_ridge=z_eave+half_width*math.tan(pitch); y_ridge=22.075
    post_size='.05 .05 2.4'; post_color='.42 .47 .48 1'
    wall_runs=[('west','y',-.0575,-.115,44.265),('east','y',63.0575,-.115,44.265),
               ('north','x',44.2075,0,63),('south_a','x',-.0575,0,30),('south_b','x',-.0575,33,63)]
    for wall,axis,fixed,start,end in wall_runs:
        for i,v in enumerate(positions(start,end,2.0)):
            pose=f'{fixed:.6f} {v:.6f} 1.3 0 0 0' if axis=='y' else f'{v:.6f} {fixed:.6f} 1.3 0 0 0'
            door_right_post = wall == 'south_b' and i == 0
            shape(link,f'frame_post_{wall}_{i:02}',pose,'box',post_size,post_color,
                  collision=False,visual=(axis=='y'),specular='.12 .13 .13 1')
            if door_right_post:
                visual=sub(link,'visual',name='frame_post_south_b_00_visual')
                sub(visual,'pose',pose); sub(visual,'cast_shadows','false')
                mesh=sub(sub(visual,'geometry'),'mesh')
                sub(mesh,'uri','model://greenhouse_frame_joint/meshes/door_post.dae')
                mat=sub(visual,'material'); sub(mat,'ambient',post_color); sub(mat,'diffuse',post_color)
                sub(mat,'specular','.12 .13 .13 1')
    # Keep the interior roof frames on the long-wall post grid. At each end,
    # place the frame midway between the long-wall and gable-wall post axes;
    # the existing 50 mm sections then overlap both corner post rows.
    xs=[0.0,*positions(2.0,62.0,2.0),63.0]
    for i,x in enumerate(xs):
        # Horizontal tie at eave height, connecting the opposing long-side
        # walls. Align each tie with the existing 2 m roof-frame stations.
        frame_beam(link,f'wall_tie_beam_{i:02}',
                   (x,-.0575,z_eave),(x,44.2075,z_eave),.05,.10,
                   visual=False,collision=False)
        frame_beam(link,f'roof_rafter_left_{i:02}',(x,-.0575,z_eave),(x,y_ridge,z_ridge),.05,.10,
                   visual=False,collision=False)
        frame_beam(link,f'roof_rafter_right_{i:02}',(x,44.2075,z_eave),(x,y_ridge,z_ridge),.05,.10,
                   visual=False,collision=False)
        for side in ('left','right'):
            joint=sub(link,'visual',name=f'portal_frame_{side}_{i:02}_visual')
            sub(joint,'pose',f'{x:.6f} 0 0 0 0 0'); sub(joint,'cast_shadows','false')
            mesh=sub(sub(joint,'geometry'),'mesh')
            variant='portal_frame_left_no_post.dae' if side=='left' and abs(x-32.0)<1e-8 else f'portal_frame_{side}.dae'
            sub(mesh,'uri',f'model://greenhouse_frame_joint/meshes/{variant}')
            sub(mesh,'scale','1 1 1')
            mat=sub(joint,'material'); sub(mat,'ambient',post_color); sub(mat,'diffuse',post_color)
            sub(mat,'specular','.12 .13 .13 1')
    # Align the roof purlins with the gable-wall mullion/post stations. The
    # eave members sit midway between the perpendicular corner-post axes.
    gable_stations=[y for y in positions(-.115,44.265,2.0) if 0 < y < 44.15]
    purlin_x0=0.0; purlin_x1=63.0
    for side, ys in [
        ('left',[-.08625,*[y for y in gable_stations if y<y_ridge],y_ridge]),
        ('right',[y_ridge,*[y for y in gable_stations if y>y_ridge],44.23625]),
    ]:
        for i,y in enumerate(ys):
            z=z_eave+min(max(y,0.0),max(44.15-y,0.0))*math.tan(pitch)
            # Keep the ridge point exact and extend the eave points only enough
            # to meet the existing corner-post axes.
            if abs(y-y_ridge)<1e-9:
                z=z_ridge
            size='.05 .05 .05'
            pose=f'{(purlin_x0+purlin_x1)/2:.6f} {y:.6f} {z:.6f} 0 0 0'
            duplicate_ridge=(side=='right' and abs(y-y_ridge)<1e-8)
            integrated=not duplicate_ridge
            shape(link,f'roof_purlin_{side}_{i:02}',pose,'box',f'{purlin_x1-purlin_x0:.6f} .05 .05',post_color,
                  collision=False,visual=not integrated,specular='.12 .13 .13 1')
            if integrated:
                for j,(left,right) in enumerate(zip(xs,xs[1:])):
                    xa=left+.025; xb=right-.025
                    if xb-xa<=1e-6: continue
                    segment_pose=f'{(xa+xb)/2:.6f} {y:.6f} {z:.6f} 0 0 0'
                    shape(link,f'roof_purlin_{side}_{i:02}_span_{j:02}',segment_pose,'box',f'{xb-xa:.6f} .05 .05',post_color,
                          collision=False,specular='.12 .13 .13 1')
    glass_roof(link,'left',0,63,0,z_eave,y_ridge,z_ridge,pitch)
    glass_roof(link,'right',0,63,44.15,z_eave,y_ridge,z_ridge,pitch)


def glass_gables(link):
    """Close and frame both triangular end-wall gaps above the vertical glazing."""
    uri='model://greenhouse_gable_panel/meshes/gable_panel.dae'
    half_width=22.075; eave_z=2.5; pitch=math.radians(10.0)
    for side,x in [('west',-.0575),('east',63.0575)]:
        visual=sub(link,'visual',name=f'glass_gable_{side}_visual')
        sub(visual,'pose',f'{x:.6f} 22.075 0 0 0 0')
        sub(visual,'cast_shadows','false'); sub(visual,'transparency','.62')
        mesh=sub(sub(visual,'geometry'),'mesh'); sub(mesh,'uri',uri); sub(mesh,'scale','1 1 1')
        mat=sub(visual,'material'); sub(mat,'ambient','.68 .88 .90 1'); sub(mat,'diffuse','.68 .88 .90 1'); sub(mat,'specular','.82 .94 .96 1')
        collision=sub(link,'collision',name=f'glass_gable_{side}_collision')
        sub(collision,'pose',f'{x:.6f} 22.075 0 0 0 0')
        mesh=sub(sub(collision,'geometry'),'mesh'); sub(mesh,'uri',uri); sub(mesh,'scale','1 1 1')
        # Continue the existing 2 m end-wall glazing grid through the gable.
        # The steel mullions make the transparent pane readable against sky.
        for i,y in enumerate(positions(-.115,44.265,2.0)):
            if not 0 < y < 44.15:
                continue
            top=eave_z+min(y,44.15-y)*math.tan(pitch)
            height=top-eave_z
            shape(link,f'glass_gable_mullion_{side}_{i:02}',
                  f'{x:.6f} {y:.6f} {eave_z+height/2:.6f} 0 0 0',
                  'box',f'.05 .05 {height:.6f}','.42 .47 .48 1',collision=False,specular='.12 .13 .13 1')


def config(name):
    m = E.Element('model'); sub(m, 'name', name); sub(m, 'version', '1.0')
    sub(m, 'sdf', 'model.sdf', version='1.6'); sub(m, 'description', 'Static greenhouse design v1.8; generated locally.')
    save(BASE/'models'/name/'model.config', m)

def vertical_glass_model():
    """Generate the reusable unit DAE panel model used by all vertical glazing."""
    directory=BASE/'models/greenhouse_vertical_glass_panel'
    vertical_glass_panel_mesh(directory/'meshes/vertical_glass_panel.dae')
    config('greenhouse_vertical_glass_panel')
    sdf,link=model('greenhouse_vertical_glass_panel')
    for kind,name in [('visual','vertical_glass_panel_visual'),('collision','vertical_glass_panel_collision')]:
        element=sub(link,kind,name=name)
        mesh=sub(sub(element,'geometry'),'mesh')
        sub(mesh,'uri','model://greenhouse_vertical_glass_panel/meshes/vertical_glass_panel.dae')
    save(directory/'model.sdf',sdf)

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
    for name, rgb, amplitude, owner in [('soil',(127,94,60),12,'greenhouse_planting_unit'),('substrate',(112,78,50),9,'greenhouse_planting_unit'),('foliage',(28,91,25),15,'greenhouse_planting_unit'),('concrete',(158,158,149),5,'greenhouse_track_pair'),('passage_concrete',(145,145,143),7,'greenhouse_track_pair')]:
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
    side_material = ("material Greenhouse/passage_side\n{\n"
                     "  technique\n  {\n    pass\n    {\n"
                     "      ambient 1 1 1 1\n      diffuse 1 1 1 1\n"
                     "      specular 0.01 0.01 0.01 1 8\n"
                     "      texture_unit\n      {\n        texture passage_concrete.png\n"
                     "        scale 12 12\n      }\n    }\n  }\n}\n")
    side_path = BASE/'models/greenhouse_track_pair/materials/scripts/passage_side.material'
    side_path.write_text(side_material)

def generate(hide_tomato_rows=False, walls_and_passage_only=False, include_soil=False,
             planting_areas_only=False):
    textures()
    greenhouse_eave_joint_mesh(BASE/'models/greenhouse_frame_joint/meshes/portal_frame_left.dae','left')
    greenhouse_eave_joint_mesh(BASE/'models/greenhouse_frame_joint/meshes/portal_frame_left_no_post.dae','left',False)
    greenhouse_eave_joint_mesh(BASE/'models/greenhouse_frame_joint/meshes/portal_frame_right.dae','right')
    greenhouse_door_post_mesh(BASE/'models/greenhouse_frame_joint/meshes/door_post.dae')
    s,l=model('greenhouse_planting_unit')
    # Open pale trough: its rim and end walls surround a recessed soil surface,
    # rather than a solid box that would hide the soil from above.
    shape(l,'trough_bottom','0 0 .905 0 0 0','box','30 .25 .01','.82 .81 .78 1',False)
    shape(l,'trough_side_a','0 -.12 .98 0 0 0','box','30 .01 .14','.82 .81 .78 1',False)
    shape(l,'trough_side_b','0 .12 .98 0 0 0','box','30 .01 .14','.82 .81 .78 1',False)
    shape(l,'trough_end_a','-14.995 0 .98 0 0 0','box','.01 .23 .14','.82 .81 .78 1',False)
    shape(l,'trough_end_b','14.995 0 .98 0 0 0','box','.01 .23 .14','.82 .81 .78 1',False)
    shape(l,'substrate','0 0 1.0275 0 0 0','box','29.98 .23 .005','.16 .075 .025 1',False)
    if not hide_tomato_rows:
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
    gable_dir=BASE/'models/greenhouse_gable_panel'
    gable_uri='model://greenhouse_gable_panel/meshes/gable_panel.dae'
    gable_panel_mesh(gable_dir/'meshes/gable_panel.dae',22.075,2.5,2.5+22.075*math.tan(math.radians(10)))
    config('greenhouse_gable_panel')
    panel_sdf,panel_link=model('greenhouse_gable_panel')
    panel_visual=sub(panel_link,'visual',name='gable_panel_visual')
    panel_mesh=sub(sub(panel_visual,'geometry'),'mesh'); sub(panel_mesh,'uri',gable_uri)
    panel_collision=sub(panel_link,'collision',name='gable_panel_collision')
    panel_mesh=sub(sub(panel_collision,'geometry'),'mesh'); sub(panel_mesh,'uri',gable_uri)
    save(gable_dir/'model.sdf',panel_sdf)
    vertical_glass_model()
    s=E.Element('sdf',version='1.6'); w=sub(s,'world',name='greenhouse_env')
    sub(sub(w,'include'),'uri','model://sun')
    gui=sub(w,'gui'); camera=sub(gui,'camera',name='user_camera')
    # Keep the passage vertical on screen and place its south-side opening at the bottom.
    sub(camera,'pose','0 0 85 0 1.570796327 1.570796327'); sub(camera,'view_controller','orbit'); sub(camera,'projection_type','perspective')
    scene=sub(w,'scene'); sub(scene,'background','.68 .84 .96 1')
    physics=sub(w,'physics',name='default_physics',type='ode'); sub(physics,'max_step_size','.001'); sub(physics,'real_time_update_rate','1000')
    env=sub(w,'model',name='greenhouse_structure'); sub(env,'static','true'); sub(env,'pose','-31.5 -22.075 0 0 0 0'); l=sub(env,'link',name='structure')
    # A visual-only distant ground surface fills the outer background and
    # creates a natural horizon in side views, without changing collisions.
    shape(l,'background_ground','31.5 22.075 -.205 0 0 0','plane','500 500','.34 .40 .30 1',False)
    if not walls_and_passage_only or include_soil:
        # Render soil as a top-only plane so the floor slab's vertical sides
        # cannot appear as a dark band below the 10 cm perimeter wall. Keep
        # the original full-depth collision box for ground contact.
        shape(l,'soil','31.5 22.075 0 0 0 0','plane','63 44.15','.29 .17 .085 1',False)
        soil_collision = sub(l, 'collision', name='soil_collision')
        sub(soil_collision, 'pose', '31.5 22.075 -.1 0 0 0')
        soil_geo = sub(sub(soil_collision, 'geometry'), 'box')
        sub(soil_geo, 'size', '63 44.15 .2')
        soil_surface = sub(soil_collision, 'surface')
        soil_friction = sub(soil_surface, 'friction'); soil_ode = sub(soil_friction, 'ode')
        sub(soil_ode, 'mu', '0.8'); sub(soil_ode, 'mu2', '0.8')
    shape(l,'passage','31.5 21.825 .15 0 0 0','box','3 44.65 .3','.58 .58 .55 1')
    for name,pose,size in [('west','-.0575 22.075 .05 0 0 0','.23 44.38 .1'),('east','63.0575 22.075 .05 0 0 0','.23 44.38 .1'),('north','31.5 44.2075 .05 0 0 0','63 .23 .1'),('south_a','15 -.0575 .05 0 0 0','30 .23 .1'),('south_b','48 -.0575 .05 0 0 0','30 .23 .1')]:
        shape(l,name,pose,'box',size,'.78 .76 .72 1')
    for wall_name, axis, fixed, start, end in [
        ('west', 'y', -.0575, -.115, 44.265),
        ('east', 'y', 63.0575, -.115, 44.265),
        ('north', 'x', 44.2075, 0, 63),
        ('south_a', 'x', -.0575, 0, 30),
        ('south_b', 'x', -.0575, 33, 63)]:
        glass_wall(l, wall_name, axis, fixed, start, end)
    greenhouse_frame(l)
    glass_gables(l)
    if not walls_and_passage_only:
        for b,x in enumerate([15,48],1):
            for i in range(30):
                inc=sub(w,'include'); sub(inc,'uri','model://greenhouse_planting_unit'); sub(inc,'name',f'planting_{b}_{i:02}'); sub(inc,'pose',f'{x-31.5} {.325+1.5*i-22.075:.3f} 0 0 0 0')
            if not planting_areas_only:
                for j in range(29):
                    inc=sub(w,'include'); sub(inc,'uri','model://greenhouse_track_pair'); sub(inc,'name',f'track_{b}_{j:02}'); sub(inc,'pose',f'{x-31.5} {1.075+1.5*j-22.075:.3f} 0 0 0 {0 if b==1 else math.pi:.9f}')
    save(BASE/'worlds/greenhouse_env.world',s)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hide-tomato-rows',action='store_true',
                        help='temporarily omit tomato row visuals and collisions for planting-bed inspection')
    parser.add_argument('--walls-and-passage-only',action='store_true',
                        help='temporarily omit planting units and track units from the World')
    parser.add_argument('--include-soil',action='store_true',
                        help='include the soil ground while using --walls-and-passage-only')
    parser.add_argument('--planting-areas-only',action='store_true',
                        help='include planting units but omit track units for planting-area inspection')
    args=parser.parse_args()
    generate(hide_tomato_rows=args.hide_tomato_rows,
             walls_and_passage_only=args.walls_and_passage_only,
             include_soil=args.include_soil,
             planting_areas_only=args.planting_areas_only)
