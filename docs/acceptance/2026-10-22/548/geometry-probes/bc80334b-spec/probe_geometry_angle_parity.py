import json,copy,math
from pathlib import Path
from linker_engine.planning.geometry import read_geometry,panel_poses
from linker_engine.planning.geometry_review import review_geometry
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());base['roofs'][0]['origin_enu']=[0,0,0];base['arrays'][0].update(rows=1,columns=1,excluded_slots=[])
browser=json.loads((p/'apps/planner/probe_geometry_angles.browser.json').read_text());out=[]
for case in browser:
 v=copy.deepcopy(base);v['arrays'][0]['rotation_deg']=case['deg'];a=panel_poses(read_geometry(v))[0]
 out.append({'deg':case['deg'],'python_centre':a.centre_enu,'browser_centre':case['pose']['centre_enu'],'centre_distance_m':math.dist(a.centre_enu,case['pose']['centre_enu']),'u_axis_distance':math.dist(a.u_axis_enu,case['pose']['u_axis_enu'])})
(p/'probe_geometry_angle_parity.results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
