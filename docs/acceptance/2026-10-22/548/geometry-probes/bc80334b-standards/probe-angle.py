import json
from pathlib import Path
from dataclasses import asdict
from linker_engine.planning.geometry import read_geometry,panel_poses
v=json.loads((Path(__file__).parent/'fixtures/planning/geometry-flat.json').read_text());v['roofs'][0]['origin_enu']=[0,0,4];v['arrays'][0]['rotation_deg']=6898968225049280
print(json.dumps(asdict(panel_poses(read_geometry(v))[0])))
