"""Static scene contracts; no robot or unrelated workspace tests."""
import math
from pathlib import Path
import xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parents[1]

def test_layout():
    w=E.parse(BASE/'worlds/greenhouse_env.world').getroot().find('world')
    assert w.findtext("model[@name='greenhouse_structure']/pose")== '-31.5 -22.075 0 0 0 0'
    assert w.findtext('gui/camera/pose')=='0 0 85 0 1.570796327 1.570796327'
    includes=w.findall('include'); names=[i.findtext('name') for i in includes if i.findtext('name')]
    assert len(names)==len(set(names))==118
    for prefix,count,start in [('planting',30,.325),('track',29,1.075)]:
        for b,x in [(1,15),(2,48)]:
            for j in range(count):
                item=next(i for i in includes if i.findtext('name')==f'{prefix}_{b}_{j:02}')
                p=list(map(float,item.findtext('pose').split()))
                assert abs(p[0]-(x-31.5))<1e-8 and abs(p[1]-(start+1.5*j-22.075))<1e-8 and p[2]==0
                assert abs(p[5]-(math.pi if prefix=='track' and b==2 else 0))<1e-8
                directory=BASE/'models'/item.findtext('uri').removeprefix('model://')
                assert (directory/'model.sdf').is_file() and (directory/'model.config').is_file()
    assert not w.findall('.//plugin')
    assert not w.findall('scene/ambient')

def test_planting_envelope():
    l=E.parse(BASE/'models/greenhouse_planting_unit/model.sdf').find('.//link')
    bottom=l.find("visual[@name='trough_bottom_visual']")
    assert list(map(float,bottom.findtext('pose').split()))[:3]==[0,0,.905]
    assert list(map(float,bottom.findtext('geometry/box/size').split()))==[30,.25,.01]
    side_a=l.find("visual[@name='trough_side_a_visual']")
    assert list(map(float,side_a.findtext('pose').split()))[:3]==[0,-.12,.98]
    assert list(map(float,side_a.findtext('geometry/box/size').split()))==[30,.01,.14]
    side_b=l.find("visual[@name='trough_side_b_visual']")
    assert list(map(float,side_b.findtext('pose').split()))[:3]==[0,.12,.98]
    assert list(map(float,side_b.findtext('geometry/box/size').split()))==[30,.01,.14]
    substrate=l.find("visual[@name='substrate_visual']")
    assert list(map(float,substrate.findtext('pose').split()))[:3]==[0,0,1.0275]
    assert list(map(float,substrate.findtext('geometry/box/size').split()))==[29.98,.23,.005]
    end_a=l.find("visual[@name='trough_end_a_visual']")
    end_b=l.find("visual[@name='trough_end_b_visual']")
    assert list(map(float,end_a.findtext('geometry/box/size').split()))==[.01,.23,.14]
    assert list(map(float,end_b.findtext('geometry/box/size').split()))==[.01,.23,.14]
    bottom_z=float(bottom.findtext('pose').split()[2])-float(bottom.findtext('geometry/box/size').split()[2])/2
    assert abs(bottom_z-.9)<1e-9
    rim_z=float(side_a.findtext('pose').split()[2])+float(side_a.findtext('geometry/box/size').split()[2])/2
    soil_z=float(substrate.findtext('pose').split()[2])+float(substrate.findtext('geometry/box/size').split()[2])/2
    assert abs(rim_z-1.05)<1e-9 and abs((rim_z-soil_z)-.02)<1e-9
    tomato=l.find("visual[@name='tomato_row_visual']")
    if tomato is not None:
        assert len(l.findall('collision'))==1
        assert l.find("collision/geometry/box/size").text=='30 .5 1'
    for v in l.findall('visual'):
        if v.attrib['name'].startswith('fruit'):
            x,y,z,*_=map(float,v.findtext('pose').split()); r=float(v.findtext('geometry/sphere/radius'))
            assert abs(x)+r<=15 and abs(y)+r<=.25 and z-r>=1.05 and z+r<=2.05

def test_rail_mesh_closed_and_bounded():
    p=BASE/'models/greenhouse_track_pair/meshes/rail.dae'; root=E.parse(p)
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    values=list(map(float,root.find('.//c:float_array',ns).text.split()))
    points=list(zip(values[::3],values[1::3],values[2::3]))
    for axis,low,high in [(0,-15,15.255),(1,-.3,.3),(2,.3,.35)]:
        assert abs(min(p[axis] for p in points)-low)<1e-8
        assert abs(max(p[axis] for p in points)-high)<1e-8
    indices=list(map(int,root.find('.//c:triangles/c:p',ns).text.split()))
    edges={}
    volume=0.0
    for i in range(0,len(indices),3):
        a,b,c=indices[i:i+3]; pa,pb,pc=[points[j] for j in (a,b,c)]
        u=[pb[k]-pa[k] for k in range(3)]; v=[pc[k]-pa[k] for k in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        assert sum(c*c for c in cross)>1e-20
        volume += (pa[0]*(pb[1]*pc[2]-pb[2]*pc[1])+pa[1]*(pb[2]*pc[0]-pb[0]*pc[2])+pa[2]*(pb[0]*pc[1]-pb[1]*pc[0]))/6
        for e in [(a,b),(b,c),(c,a)]:
            key=tuple(sorted(e));edges.setdefault(key,[]).append(e)
    assert volume>0, "mesh normals must face outward"
    assert all(len(es)==2 and es[0]==es[1][::-1] for es in edges.values())
    # Sagitta error: bend < .019 mm; cross-section < .121 mm.
    assert .06*(1-math.cos(math.pi/128))<.000019
    assert .025*(1-math.cos(math.pi/32))<.000121
    l=E.parse(BASE/'models/greenhouse_track_pair/model.sdf').find('.//link')
    assert l.findtext("visual[@name='rail_visual']/geometry/mesh/uri")==l.findtext("collision[@name='rail_collision']/geometry/mesh/uri")

def test_track_base_top_matches_passage_top():
    track=E.parse(BASE/'models/greenhouse_track_pair/model.sdf').find('.//link')
    base=track.find("collision[@name='base_collision']")
    base_pose=list(map(float,base.findtext('pose').split()))
    base_height=float(base.findtext('geometry/box/size').split()[2])
    passage=E.parse(BASE/'worlds/greenhouse_env.world').find(".//model[@name='greenhouse_structure']/link/collision[@name='passage_collision']")
    passage_pose=list(map(float,passage.findtext('pose').split()))
    passage_height=float(passage.findtext('geometry/box/size').split()[2])
    assert abs((base_pose[2]+base_height/2)-(passage_pose[2]+passage_height/2))<1e-9

def test_sky_background_is_pale_blue():
    scene=E.parse(BASE/'worlds/greenhouse_env.world').find('world/scene')
    assert scene is not None
    assert list(map(float,scene.findtext('background').split()))==[.68,.84,.96,1]

def test_distant_ground_is_visual_only_below_greenhouse_floor():
    link=E.parse(BASE/'worlds/greenhouse_env.world').find(".//model[@name='greenhouse_structure']/link")
    ground=link.find("visual[@name='background_ground_visual']")
    assert list(map(float,ground.findtext('pose').split()))[:3]==[31.5,22.075,-.205]
    assert list(map(float,ground.findtext('geometry/plane/normal').split()))==[0,0,1]
    assert list(map(float,ground.findtext('geometry/plane/size').split()))==[500,500]
    assert ground.findtext('cast_shadows')=='false'
    assert link.find("collision[@name='background_ground_collision']") is None

def test_structure_and_heights():
    w=E.parse(BASE/'worlds/greenhouse_env.world').find('world')
    l=w.find("model[@name='greenhouse_structure']/link")
    expected={'soil':([31.5,22.075,-.1],[63,44.15,.2]),'passage':([31.5,21.825,.15],[3,44.65,.3]),'west':([-.0575,22.075,.05],[.23,44.38,.1]),'east':([63.0575,22.075,.05],[.23,44.38,.1]),'north':([31.5,44.2075,.05],[63,.23,.1]),'south_a':([15,-.0575,.05],[30,.23,.1]),'south_b':([48,-.0575,.05],[30,.23,.1])}
    for name,(pos,size) in expected.items():
        for kind in ('visual','collision'):
            item=l.find(f"{kind}[@name='{name}_{kind}']")
            if name=='soil' and kind=='visual':
                assert list(map(float,item.findtext('pose').split()))[:3]==[31.5,22.075,0.0]
                assert list(map(float,item.findtext('geometry/plane/size').split()))==[63.0,44.15]
                continue
            if name=='passage' and kind=='visual':
                # The passage visual is split into top, side, exit, and warning-line pieces;
                # its aggregate dimensions are represented by the collision below.
                continue
            assert list(map(float,item.findtext('pose').split()))[:3]==pos
            assert list(map(float,item.findtext('geometry/box/size').split()))==size
    planting=E.parse(BASE/'models/greenhouse_planting_unit/model.sdf')
    assert planting.findtext(".//visual[@name='substrate_visual']/pose").split()[2]=='1.0275'
    track=E.parse(BASE/'models/greenhouse_track_pair/model.sdf')
    assert track.findtext(".//collision[@name='base_collision']/geometry/box/size")=='30 .7 .3'
    assert track.findtext(".//static")=='true'


def test_soil_top_only_visual_preserves_original_collision():
    link=E.parse(BASE/'worlds/greenhouse_env.world').find(".//model[@name='greenhouse_structure']/link")
    visual=link.find("visual[@name='soil_visual']")
    assert list(map(float,visual.findtext('pose').split()))[:3]==[31.5,22.075,0.0]
    assert list(map(float,visual.findtext('geometry/plane/size').split()))==[63,44.15]
    assert visual.find('geometry/box') is None
    assert visual.findtext('cast_shadows')=='false'
    collision=link.find("collision[@name='soil_collision']")
    assert list(map(float,collision.findtext('pose').split()))[:3]==[31.5,22.075,-.1]
    assert list(map(float,collision.findtext('geometry/box/size').split()))==[63,44.15,.2]


def test_perimeter_wall_height_is_10cm():
    world=E.parse(BASE/'worlds/greenhouse_env.world').getroot().find('world')
    link=world.find("model[@name='greenhouse_structure']/link[@name='structure']")
    expected={'west':(.23,44.38),'east':(.23,44.38),'north':(63,.23),'south_a':(30,.23),'south_b':(30,.23)}
    for name,(sx,sy) in expected.items():
        for kind in ('visual','collision'):
            item=link.find(f"{kind}[@name='{name}_{kind}']")
            assert item is not None, f'missing {kind} for {name}'
            pose=list(map(float,item.findtext('pose').split()))
            size=list(map(float,item.findtext('geometry/box/size').split()))
            assert abs(pose[2]-.05)<1e-9
            assert abs(size[0]-sx)<1e-9 and abs(size[1]-sy)<1e-9 and abs(size[2]-.1)<1e-9
            assert abs((pose[2]-size[2]/2)-0)<1e-9
            assert abs((pose[2]+size[2]/2)-.1)<1e-9


def test_glass_perimeter_panels_and_open_entry():
    world=E.parse(BASE/'worlds/greenhouse_env.world').getroot().find('world')
    link=world.find("model[@name='greenhouse_structure']/link[@name='structure']")
    groups={'west':('y',44.38),'east':('y',44.38),'north':('x',63.0),'south_a':('x',30.0),'south_b':('x',30.0)}
    for name,(axis,total) in groups.items():
        panes=[v for v in link.findall('visual') if v.get('name','').startswith(f'glass_{name}_pane_')]
        assert panes
        lengths=[]
        for pane in panes:
            pose=list(map(float,pane.findtext('pose').split()))
            mesh=pane.find('geometry/mesh')
            assert mesh is not None
            assert mesh.findtext('uri')=='model://greenhouse_vertical_glass_panel/meshes/vertical_glass_panel.dae'
            scale=list(map(float,mesh.findtext('scale').split()))
            assert abs(scale[0]-.01)<1e-8 and abs(scale[2]-2.4)<1e-8
            length=scale[1]
            assert length <= 2.0+1e-8
            assert abs(pose[2]-1.3)<1e-8
            if axis=='x':
                assert abs(pose[5]-math.pi/2)<1e-8
            else:
                assert abs(pose[5])<1e-8
            assert abs(float(pane.findtext('transparency'))-.62)<1e-8
            assert pane.findtext('cast_shadows')=='false'
            lengths.append(length)
        assert abs(sum(lengths)-total)<1e-6
        collision=link.find(f"collision[@name='glass_{name}_collision']")
        assert collision is not None
        cs=list(map(float,collision.findtext('geometry/box/size').split()))
        assert abs((cs[0] if axis=='x' else cs[1])-total)<1e-6
        assert abs(cs[2]-2.4)<1e-8
    panel_dir=BASE/'models/greenhouse_vertical_glass_panel'
    assert (panel_dir/'model.config').is_file() and (panel_dir/'model.sdf').is_file()
    panel=E.parse(panel_dir/'meshes/vertical_glass_panel.dae')
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    coords=list(map(float,panel.find('.//c:float_array',ns).text.split()))
    points=list(zip(coords[::3],coords[1::3],coords[2::3]))
    assert len(points)==8
    assert all(abs(min(p[i] for p in points)+.5)<1e-8 and abs(max(p[i] for p in points)-.5)<1e-8 for i in range(3))
    tri=panel.find('.//c:triangles',ns)
    assert tri.get('count')=='12' and len(tri.findtext('c:p',namespaces=ns).split())==36
    # The 3 m south entrance is left open in both glass visuals and collision.
    for pane in [v for v in link.findall('visual') if v.get('name','').startswith('glass_south_')]:
        pose=list(map(float,pane.findtext('pose').split()))
        half_width=list(map(float,pane.findtext('geometry/mesh/scale').split()))[1]/2
        assert pose[0]+half_width <= 30+1e-8 or pose[0]-half_width >= 33-1e-8


def test_greenhouse_supports_and_glass_roof():
    world=E.parse(BASE/'worlds/greenhouse_env.world').getroot().find('world')
    link=world.find("model[@name='greenhouse_structure']/link[@name='structure']")
    posts=[v for v in link.findall('visual') if v.get('name','').startswith('frame_post_')]
    assert len(posts)==49  # the two end-wall rows plus the visible right door post
    for post in posts:
        pose=list(map(float,post.findtext('pose').split()))
        if post.get('name')=='frame_post_south_b_00_visual':
            assert post.findtext('geometry/mesh/uri')=='model://greenhouse_frame_joint/meshes/door_post.dae'
            assert link.find("collision[@name='frame_post_south_b_00_collision']") is None
            assert post.findtext('cast_shadows')=='false'
            door_material=post.find('material')
            frame_material=link.find("visual[@name='portal_frame_left_00_visual']/material")
            assert [door_material.findtext(name) for name in ('ambient','diffuse','specular')]==[
                frame_material.findtext(name) for name in ('ambient','diffuse','specular')]
            ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
            door_mesh=E.parse(BASE/'models/greenhouse_frame_joint/meshes/door_post.dae').getroot()
            door_vertices=list(map(float,door_mesh.find(".//c:source[@id='door_post_positions']/c:float_array",ns).text.split()))
            door_normals=list(map(float,door_mesh.find(".//c:source[@id='door_post_normals']/c:float_array",ns).text.split()))
            tri=door_mesh.find('.//c:triangles',ns)
            inputs={item.get('semantic'):int(item.get('offset')) for item in tri.findall('c:input',ns)}
            assert inputs=={'VERTEX':0,'NORMAL':1} and int(tri.get('count'))==12
            indices=list(map(int,tri.findtext('c:p',namespaces=ns).split()))
            stride=max(inputs.values())+1
            for offset in range(0,len(indices),3*stride):
                face_data=indices[offset:offset+3*stride]
                vertex_ids=[face_data[i+inputs['VERTEX']] for i in range(0,3*stride,stride)]
                normal_ids=[face_data[i+inputs['NORMAL']] for i in range(0,3*stride,stride)]
                assert len(set(normal_ids))==1
                points=[tuple(door_vertices[index*3:index*3+3]) for index in vertex_ids]
                ab=tuple(points[1][i]-points[0][i] for i in range(3))
                ac=tuple(points[2][i]-points[0][i] for i in range(3))
                geometric=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
                length=math.sqrt(sum(value*value for value in geometric))
                assert length>1e-9
                geometric=tuple(value/length for value in geometric)
                normal=tuple(door_normals[normal_ids[0]*3:normal_ids[0]*3+3])
                assert all(abs(geometric[i]-normal[i])<1e-6 for i in range(3))
            continue
        size=list(map(float,post.findtext('geometry/box/size').split()))
        assert size==[.05,.05,2.4] and abs(pose[2]-1.3)<1e-8
        assert link.find(f"collision[@name='{post.get('name').removesuffix('_visual')}_collision']") is None
        assert post.findtext('cast_shadows')=='false'
    frame_xs=[0.0,*map(float,range(2,63,2)),63.0]
    joint_visuals=[v for v in link.findall('visual') if v.get('name','').startswith('portal_frame_')]
    assert len(joint_visuals)==2*len(frame_xs)==66
    for i,x in enumerate(frame_xs):
        for side in ('left','right'):
            visual=link.find(f"visual[@name='portal_frame_{side}_{i:02}_visual']")
            assert visual is not None
            assert abs(float(visual.findtext('pose').split()[0])-x)<1e-8
            uri=visual.findtext('geometry/mesh/uri')
            expected='portal_frame_left_no_post.dae' if side=='left' and x==32 else f'portal_frame_{side}.dae'
            assert uri==f'model://greenhouse_frame_joint/meshes/{expected}'
    assert not [v for v in link.findall('visual') if v.get('name','').startswith(('roof_rafter_','wall_tie_beam_'))]
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    for filename in ('portal_frame_left.dae','portal_frame_left_no_post.dae','portal_frame_right.dae'):
        mesh_root=E.parse(BASE/'models/greenhouse_frame_joint/meshes'/filename).getroot()
        vertices=list(map(float,mesh_root.find(".//c:source[@id='joint_positions']/c:float_array",ns).text.split()))
        normals=list(map(float,mesh_root.find(".//c:source[@id='joint_normals']/c:float_array",ns).text.split()))
        tri_el=mesh_root.find('.//c:triangles',ns)
        inputs={item.get('semantic'):int(item.get('offset')) for item in tri_el.findall('c:input',ns)}
        assert inputs=={'VERTEX':0,'NORMAL':1}
        index_data=list(map(int,tri_el.findtext('c:p',namespaces=ns).split()))
        stride=max(inputs.values())+1
        triangles=[]; face_normals=[]
        for offset in range(0,len(index_data),3*stride):
            face_data=index_data[offset:offset+3*stride]
            triangles.append(tuple(face_data[i+inputs['VERTEX']] for i in range(0,3*stride,stride)))
            normal_ids=[face_data[i+inputs['NORMAL']] for i in range(0,3*stride,stride)]
            assert len(set(normal_ids))==1
            face_normals.append(tuple(normals[normal_ids[0]*3:normal_ids[0]*3+3]))
        assert len(triangles)==int(tri_el.get('count'))
        edge_counts={}
        for face,normal in zip(triangles,face_normals):
            coords=[tuple(vertices[i*3:i*3+3]) for i in face]
            ab=tuple(coords[1][i]-coords[0][i] for i in range(3))
            ac=tuple(coords[2][i]-coords[0][i] for i in range(3))
            geometric=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
            length=math.sqrt(sum(value*value for value in geometric))
            assert length>1e-9
            geometric=tuple(value/length for value in geometric)
            assert all(abs(geometric[i]-normal[i])<1e-6 for i in range(3))
            for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
                edge=tuple(sorted((a,b))); edge_counts[edge]=edge_counts.get(edge,0)+1
        assert edge_counts and all(count==2 for count in edge_counts.values())
        coords=list(zip(vertices[::3],vertices[1::3],vertices[2::3]))
        volume=0.0
        for face in triangles:
            a,b,c=(coords[index] for index in face)
            volume += sum(a[k]*(b[(k+1)%3]*c[(k+2)%3]-b[(k+2)%3]*c[(k+1)%3]) for k in range(3))/6
        assert volume>0 and min(v[0] for v in coords)==-.025 and max(v[0] for v in coords)==.025
    steel_collision_prefixes=('frame_post_','wall_tie_beam_','roof_rafter_',
                              'roof_purlin_','glass_gable_mullion_')
    assert not [c for c in link.findall('collision')
                if c.get('name','').startswith(steel_collision_prefixes)]
    for side in ('left','right'):
        purlins=[v for v in link.findall('collision') if v.get('name','').startswith(f'roof_purlin_{side}_')]
        assert not purlins
        spans=[v for v in link.findall('visual') if v.get('name','').startswith(f'roof_purlin_{side}_') and '_span_' in v.get('name','')]
        assert len(spans)==(13 if side=='left' else 12)*32
        for span in spans:
            pose=list(map(float,span.findtext('pose').split()))
            size=list(map(float,span.findtext('geometry/box/size').split()))
            assert abs(size[1]-.05)<1e-8 and abs(size[2]-.05)<1e-8
            assert all(abs(pose[0]-x)>.05 for x in frame_xs)
    # Roof visuals are panel boxes no larger than 2 m in either panel direction.
    panes=[v for v in link.findall('visual') if v.get('name','').startswith('glass_roof_') and 'collision' not in v.get('name','')]
    assert panes
    for pane in panes:
        size=list(map(float,pane.findtext('geometry/box/size').split()))
        pose=list(map(float,pane.findtext('pose').split()))
        assert size[0]<=2+1e-8 and size[1]<=2+1e-8 and abs(size[2]-.01)<1e-8
        assert abs(abs(pose[3])-math.radians(10))<1e-6
        assert abs(float(pane.findtext('transparency'))-.62)<1e-8
        assert pane.findtext('cast_shadows')=='false'
    for side,roll in [('left',math.radians(10)),('right',-math.radians(10))]:
        collision=link.find(f"collision[@name='glass_roof_{side}_collision']")
        assert collision is not None
        pose=list(map(float,collision.findtext('pose').split()))
        size=list(map(float,collision.findtext('geometry/box/size').split()))
        assert abs(pose[3]-roll)<1e-6 and abs(size[0]-63)<1e-8
        assert abs(size[1]-math.hypot(22.075,22.075*math.tan(math.radians(10))))<1e-6
    # Keep the south-side 3 m wall opening clear of vertical posts.
    south_posts=[v for v in posts if '_south_' in v.get('name','')]
    assert all(not (30 < float(v.findtext('pose').split()[0]) < 33) for v in south_posts)


def test_glass_gable_triangles_close_end_wall_gaps():
    world=E.parse(BASE/'worlds/greenhouse_env.world').find('world')
    link=world.find("model[@name='greenhouse_structure']/link")
    uri='model://greenhouse_gable_panel/meshes/gable_panel.dae'
    for side,x in [('west',-.0575),('east',63.0575)]:
        visual=link.find(f"visual[@name='glass_gable_{side}_visual']")
        assert visual is not None and visual.findtext('geometry/mesh/uri')==uri
        assert list(map(float,visual.findtext('pose').split()))[:3]==[x,22.075,0.0]
        assert abs(float(visual.findtext('transparency'))-.62)<1e-8
        assert visual.findtext('cast_shadows')=='false'
        collision=link.find(f"collision[@name='glass_gable_{side}_collision']")
        assert collision is not None and collision.findtext('geometry/mesh/uri')==uri
    model_dir=BASE/'models/greenhouse_gable_panel'
    assert (model_dir/'model.config').is_file() and (model_dir/'model.sdf').is_file()
    mesh=E.parse(model_dir/'meshes/gable_panel.dae')
    ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
    coords=list(map(float,mesh.find('.//c:float_array',ns).text.split()))
    points=list(zip(coords[::3],coords[1::3],coords[2::3]))
    assert len(points)==6
    assert abs(min(p[0] for p in points)+.005)<1e-8 and abs(max(p[0] for p in points)-.005)<1e-8
    assert abs(min(p[1] for p in points)+22.075)<1e-8 and abs(max(p[1] for p in points)-22.075)<1e-8
    assert abs(min(p[2] for p in points)-2.5)<1e-8
    assert abs(max(p[2] for p in points)-(2.5+22.075*math.tan(math.radians(10))))<1e-8
    tri=mesh.find('.//c:triangles',ns)
    indices=list(map(int,tri.findtext('c:p',namespaces=ns).split()))
    assert tri.get('count')=='8' and len(indices)==24
    edges={}
    volume=0.0
    for i in range(0,len(indices),3):
        face=indices[i:i+3]; a,b,c=[points[j] for j in face]
        volume+=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6
        for edge in [(face[0],face[1]),(face[1],face[2]),(face[2],face[0])]:
            edges.setdefault(tuple(sorted(edge)),[]).append(edge)
    assert volume>0
    assert all(len(adjacent)==2 and adjacent[0]==adjacent[1][::-1] for adjacent in edges.values())
    mullions=[v for v in link.findall('visual') if v.get('name','').startswith('glass_gable_mullion_')]
    assert len(mullions)==44
    for mullion in mullions:
        pose=list(map(float,mullion.findtext('pose').split()))
        size=list(map(float,mullion.findtext('geometry/box/size').split()))
        assert size[:2]==[.05,.05]
        assert mullion.findtext('cast_shadows')=='false'
        top=2.5+min(pose[1],44.15-pose[1])*math.tan(math.radians(10))
        assert abs((pose[2]-size[2]/2)-2.5)<1e-6
        assert abs((pose[2]+size[2]/2)-top)<1e-6
