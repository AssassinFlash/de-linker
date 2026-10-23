import copy,json,math
from pathlib import Path
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_review import review_geometry
root=Path(__file__).parent
v=json.loads((root/'fixtures/planning/geometry-flat.json').read_text())
v['roofs'][0]['origin_enu']=[0,0,4]
v['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,2])
v['obstacles']=[{'id':'swept','name':'Synthetic diagonal extrusion','source_id':'survey','roof_id':'roof','footprint_uv':[[5,5],[6,5],[6,6],[5,6]],'extrusion_axis_enu':[math.sqrt(.5),0,math.sqrt(.5)],'height_m':1e15}]
read_geometry(v);r=review_geometry(v)
actual_endpoint=6+math.sqrt(.5)*1e15
print(json.dumps({'case':'derived_obstacle_projection','status':r['geometry_status'],'complete':r['review_complete'],'reported_resolution_m':r['uv_resolution_m'],'derived_endpoint':actual_endpoint,'derived_endpoint_ulp_m':math.ulp(actual_endpoint),'policy_m':r['limits']['max_uv_resolution_m'],'kinds':[i['kind']for i in r['issues']]}))
v['obstacles']=[];v['module_specs'][0]['width_m']=1e7
read_geometry(v);r=review_geometry(v)
print(json.dumps({'case':'derived_cuboid_corner','status':r['geometry_status'],'complete':r['review_complete'],'reported_resolution_m':r['uv_resolution_m'],'derived_corner_ulp_m':math.ulp(1+1e7),'policy_m':r['limits']['max_uv_resolution_m'],'kinds':[i['kind']for i in r['issues']]}))
