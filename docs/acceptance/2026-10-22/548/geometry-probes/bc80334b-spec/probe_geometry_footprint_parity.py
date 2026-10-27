from pathlib import Path
import json,copy
from linker_engine.planning.geometry import read_geometry,panel_poses
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());out=[]
for rotation in [1,31,89,9007199254740991]:
 for tilt in [0,30,45,90]:
  v=copy.deepcopy(base);v['arrays'][0].update(rows=3,columns=2,rotation_deg=rotation,mount_tilt_deg=tilt,excluded_slots=['1:1'])
  v['roofs'][0]['origin_enu']=[1e15,0,4]
  out.append({'rotation':rotation,'tilt':tilt,'document':v,'footprints':[p.footprint_uv for p in panel_poses(read_geometry(v))]})
(p/'probe_geometry_footprint_parity.inputs.json').write_text(json.dumps(out,indent=2)+'\n');print('cases',len(out))
