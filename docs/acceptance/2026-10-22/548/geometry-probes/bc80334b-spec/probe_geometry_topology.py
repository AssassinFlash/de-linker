from pathlib import Path
from decimal import Decimal,localcontext
from itertools import combinations
import copy,json
from linker_engine.planning.geometry_review import review_geometry
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text())
base['roofs'][0]['boundary_uv']=[[0,0],[200,0],[200,200],[0,200]]

def reference_pairs(rows,cols,width,length,thick,tilt,rowgap,colgap,excluded):
 with localcontext() as ctx:
  ctx.prec=60;D=lambda x:Decimal(str(x))
  sine,cosine={0:(D(0),D(1)),30:(D('.5'),D(3).sqrt()/2),45:(D(2).sqrt()/2,D(2).sqrt()/2),90:(D(1),D(0))}[tilt]
  rectangles={}
  for row in range(rows):
   for col in range(cols):
    if f'{row}:{col}' in excluded:continue
    left=D(col)*(D(width)+D(colgap));right=left+D(width)
    low=D(row)*(D(length)*cosine+D(rowgap))-D(thick)*sine
    high=D(row)*(D(length)*cosine+D(rowgap))+D(length)*cosine
    rectangles[f'array:{row}:{col}']=(left,right,low,high)
  pairs=set()
  for (a,x),(b,y) in combinations(rectangles.items(),2):
   if min(x[1],y[1])>max(x[0],y[0]) and min(x[3],y[3])>max(x[2],y[2]):pairs.add(tuple(sorted([a,b])))
  return pairs
out=[]
cases=[('flat',4,3,.04,0,0,0,[]),('adjacent_thick',4,3,.04,30,0,0,[]),('row_contact',4,3,.04,30,.02,0,[]),('row_gap',4,3,.04,30,.03,.1,[]),('multirow_thick',5,2,5,30,.1,0,['2:0','1:1']),('vertical_nonadjacent',7,2,2.5,90,.5,0,['2:0','4:1']),('inclined_nonadjacent',5,2,5,45,.1,.1,['1:0'])]
for label,rows,cols,t,tilt,rg,cg,excluded in cases:
 for rotation in [1,31,89]:
  v=copy.deepcopy(base);v['module_specs'][0]['thickness_m']=t
  v['arrays'][0].update(rows=rows,columns=cols,excluded_slots=excluded,origin_uv=[50,50],column_gap_m=cg,row_gap_m=rg,mount_tilt_deg=tilt,rotation_deg=rotation)
  expected=reference_pairs(rows,cols,1,2,t,tilt,rg,cg,excluded);r=review_geometry(v)
  actual={tuple(sorted([i['object_id'],i['related_id']])) for i in r['issues'] if i['kind']=='panel_projected_overlap'}
  ok=r['review_complete'] and actual==expected
  out.append({'case':label,'rotation':rotation,'expected_pairs':len(expected),'actual_pairs':len(actual),'passed':ok,'missing':sorted(expected-actual),'extra':sorted(actual-expected)})
for rotation in [1,30,45,89]:
 v=copy.deepcopy(base);a=v['arrays'][0];a.update(rows=1,columns=2,origin_uv=[50,50],column_gap_m=0,rotation_deg=rotation,excluded_slots=['0:1'])
 v['arrays'].append({**a,'id':'other','excluded_slots':['0:0']});r=review_geometry(v)
 actual=[i for i in r['issues'] if i['kind']=='panel_projected_overlap'];out.append({'case':'cross_array_shared_edge_same_grid','rotation':rotation,'passed':not actual and r['review_complete'],'actual_pairs':len(actual)})
v=copy.deepcopy(base);v['arrays'][0].update(rows=1,columns=1,origin_uv=[50,50],excluded_slots=[]);v['arrays'].append({**v['arrays'][0],'id':'other'})
r=review_geometry(v);actual=[i for i in r['issues'] if i['kind']=='panel_projected_overlap'];out.append({'case':'cross_array_identical_positive_area','passed':len(actual)==1,'actual_pairs':len(actual)})
v['arrays'][1]['excluded_slots']=['0:0'];r=review_geometry(v);actual=[i for i in r['issues'] if i['kind']=='panel_projected_overlap'];out.append({'case':'cross_array_excluded_absent','passed':not actual,'actual_pairs':len(actual)})
(p/'probe_geometry_topology.results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'cases':len(out),'passed':sum(x['passed'] for x in out),'failures':[x for x in out if not x['passed']]},indent=2))
assert all(x['passed'] for x in out)
