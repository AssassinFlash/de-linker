import copy,itertools,json,math,random
from fractions import Fraction as F
from pathlib import Path
from linker_engine.planning.geometry_review import review_geometry
base=json.loads((Path(__file__).parent/'fixtures/planning/geometry-flat.json').read_text())
base['roofs'][0]['origin_enu']=[0,0,4]
base['roofs'][0]['boundary_uv']=[[-50,-50],[50,-50],[50,50],[-50,50]]
rng=random.Random(548);runs=0
for angle,tilt,gap in itertools.product([0,17,31,90],[0,30,60,90],[0,.01,.2]):
 v=copy.deepcopy(base);a=v['arrays'][0];a.update(origin_uv=[0,0],rotation_deg=angle,mount_tilt_deg=tilt,rows=4,columns=3,row_gap_m=gap,column_gap_m=0,excluded_slots=['0:1','2:0'])
 spec=v['module_specs'][0];spec.update(width_m=1.134,length_m=2.278,thickness_m=.04)
 s,c=(0.,1.)if tilt==0 else(1.,0.)if tilt==90 else(math.sin(tilt*math.pi/180),math.cos(tilt*math.pi/180))
 # Independent exact rational interval cross-section; no actuator/checker helpers.
 width,length,thick,rg=map(F,[spec['width_m'],spec['length_m'],spec['thickness_m'],gap]);s,c=F(s),F(c)
 rects={}
 for row,col in itertools.product(range(4),range(3)):
  if f'{row}:{col}'in a['excluded_slots']:continue
  rects[f'array:{row}:{col}']=(col*width,(col+1)*width,row*(length*c+rg)-thick*s,(row+1)*length*c+row*rg)
 expected=set()
 for(x,p),(y,q)in itertools.combinations(rects.items(),2):
  if max(p[0],q[0])<min(p[1],q[1])and max(p[2],q[2])<min(p[3],q[3]):expected.add(frozenset([x,y]))
 r=review_geometry(v);actual={frozenset([i['object_id'],i['related_id']])for i in r['issues']if i['kind']=='panel_projected_overlap'}
 assert r['review_complete'] and actual==expected,(angle,tilt,gap,actual,expected)
 runs+=1
for angle,gap in itertools.product([0,15,31,45,89,90,123,270],[.01,-.01]):
 v=copy.deepcopy(base);a=v['arrays'][0];a.update(rows=1,columns=1,excluded_slots=[],origin_uv=[0,0],rotation_deg=angle)
 rad=angle*math.pi/180;dx,dy=math.cos(rad)*(1+gap),math.sin(rad)*(1+gap)
 v['arrays'].append({**a,'id':'second','origin_uv':[dx,dy]})
 r=review_geometry(v);pairs=[i for i in r['issues']if i['kind']=='panel_projected_overlap'];assert len(pairs)==(1 if gap<0 else 0),(angle,gap,r)
 runs+=1
print(json.dumps({'independent_analytic_cases':runs,'status':'PASS','same_array_exclusions_tilt_gap':'48 exact rational interval cases','cross_array_positive_overlap_separation':'16 rotated cases'}))
