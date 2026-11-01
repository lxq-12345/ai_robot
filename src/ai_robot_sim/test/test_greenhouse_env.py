"""Static scene contracts; no robot or unrelated workspace tests."""
import math
from pathlib import Path
import xml.etree.ElementTree as E
BASE=Path(__file__).resolve().parents[1]

def test_layout():
    w=E.parse(BASE/'worlds/greenhouse_env.world').getroot().find('world')
    assert w.findtext("model[@name='greenhouse_structure']/pose")== '-31.5 -22.075 0 0 0 0'
    assert w.findtext('gui/camera/pose')=='0 0 85 0 1.570796327 0'
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

def test_structure_and_heights():
    w=E.parse(BASE/'worlds/greenhouse_env.world').find('world')
    l=w.find("model[@name='greenhouse_structure']/link")
    expected={'soil':([31.5,22.075,-.1],[63,44.15,.2]),'passage':([31.5,22.075,.15],[3,44.15,.3]),'west':([-.0575,22.075,1],[.115,44.38,2]),'east':([63.0575,22.075,1],[.115,44.38,2]),'north':([31.5,44.2075,1],[63,.115,2]),'south_a':([15,-.0575,1],[30,.115,2]),'south_b':([48,-.0575,1],[30,.115,2])}
    for name,(pos,size) in expected.items():
        for kind in ('visual','collision'):
            item=l.find(f"{kind}[@name='{name}_{kind}']")
            assert list(map(float,item.findtext('pose').split()))[:3]==pos
            assert list(map(float,item.findtext('geometry/box/size').split()))==size
    planting=E.parse(BASE/'models/greenhouse_planting_unit/model.sdf')
    assert planting.findtext(".//visual[@name='substrate_visual']/pose").split()[2]=='1.045'
    track=E.parse(BASE/'models/greenhouse_track_pair/model.sdf')
    assert track.findtext(".//collision[@name='base_collision']/geometry/box/size")=='30 .7 .3'
    assert track.findtext(".//static")=='true'
