from pathlib import Path
import copy,json
from shapely.geometry import MultiPoint
from linker_engine.planning.geometry import read_geometry,panel_poses
from linker_engine.planning.geometry_review import review_geometry
p=Path(__file__).resolve().parent
b=json.loads((p/'fixtures/planning/geometry-flat.json').read_text())
b['arrays'][0].update(rows=1,columns=2,excluded_slots=[],origin_uv=[5,5],column_gap_m=0)
out=[]
for angle in [0,1,15,30,31,45,60,75,89,90,135,180,270]:
 v=copy.deepcopy(b);v['arrays'][0]['rotation_deg']=angle
 r=review_geometry(v);poses=panel_poses(read_geometry(v))
 polys=[MultiPoint([(c[0],c[1]) for c in pose.corners_uvn()]).convex_hull for pose in poses]
 area=polys[0].intersection(polys[1]).area
 ks=[x['kind'] for x in r['issues'] if x['category']=='layout_conflict']
 out.append({'angle_deg':angle,'expected_positive_area_overlap':False,'actual_intersection_m2':area,'uv_resolution_m':r['uv_resolution_m'],'status':r['geometry_status'],'kinds':ks})
(p/'probe_geometry_touch.results.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
