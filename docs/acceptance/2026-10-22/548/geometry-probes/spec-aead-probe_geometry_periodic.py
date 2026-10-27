import json,copy,math
from pathlib import Path
from linker_engine.planning.geometry import read_geometry,panel_poses
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());base['roofs'][0]['origin_enu']=[0,0,0];base['arrays'][0].update(rows=1,columns=1,excluded_slots=[])
out=[]
for deg in [360,360000000031,9007199254740991]:
 v=copy.deepcopy(base);v['arrays'][0]['rotation_deg']=deg;a=panel_poses(read_geometry(v))[0];w=copy.deepcopy(v);w['arrays'][0]['rotation_deg']=deg%360;b=panel_poses(read_geometry(w))[0]
 out.append({'rotation_deg':deg,'same_rotation_mod360':deg%360,'centre_error_m':math.dist(a.centre_enu,b.centre_enu),'axis_error':math.dist(a.u_axis_enu,b.u_axis_enu),'actual_axis':a.u_axis_enu,'mod360_axis':b.u_axis_enu})
(p/'probe_geometry_periodic.results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
