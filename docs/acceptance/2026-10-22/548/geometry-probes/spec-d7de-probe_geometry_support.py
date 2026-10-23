from pathlib import Path
import json,copy,math
from linker_engine.planning.geometry import read_geometry,panel_poses
from linker_engine.planning.geometry_review import review_geometry
from linker_engine.planning.geometry_numerics import uv_resolution
p=Path(__file__).resolve().parent
base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text())
base['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,1])
base['roofs'][0]['origin_enu']=[0,0,0]
out=[]
for label,largest in [('below',math.nextafter(2**23,0)),('at',2**23),('above',math.nextafter(2**23,math.inf))]:
 v=copy.deepcopy(base);v['roofs'][0]['boundary_uv']=[[0,0],[largest,0],[largest,20],[0,20]]
 before=copy.deepcopy(v);r=review_geometry(v)
 assert v==before
 out.append({'case':'raw_boundary_'+label,'largest':largest,'ulp_m':math.ulp(largest),'reported_m':r['uv_resolution_m'],'status':r['geometry_status'],'complete':r['review_complete']})
v=copy.deepcopy(base)
v['obstacles']=[{'id':'swept','name':'Synthetic long sweep','source_id':'survey','roof_id':'roof','footprint_uv':[[4,4],[5,4],[5,5],[4,5]],'extrusion_axis_enu':[0.6,0,0.8],'height_m':1e14}]
r=review_geometry(v)
out.append({'case':'derived_obstacle_sweep','derived_largest_uv_m':4+0.6e14,'actual_derived_ulp_m':math.ulp(4+0.6e14),'reported_m':r['uv_resolution_m'],'budget_m':r['limits']['max_uv_resolution_m'],'status':r['geometry_status'],'complete':r['review_complete'],'issues':r['issues']})
v=copy.deepcopy(base);v['arrays'][0]['origin_uv']=[2**23-2,1];v['module_specs'][0]['width_m']=2
r=review_geometry(v);pose=panel_poses(read_geometry(v))[0];maxcorner=max(math.ulp(x) for c in pose.corners_uvn() for x in c[:2])
out.append({'case':'derived_cuboid_corner','actual_derived_ulp_m':maxcorner,'reported_m':r['uv_resolution_m'],'status':r['geometry_status'],'complete':r['review_complete'],'issues':r['issues']})
(p/'probe_geometry_support.results.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
