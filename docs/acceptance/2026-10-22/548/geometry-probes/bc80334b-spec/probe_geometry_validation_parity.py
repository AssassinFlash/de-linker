import json,copy
from pathlib import Path
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.errors import InvalidInput
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());out=[]
for name,change in [('bad_acquired_at_utc',lambda v:v['sources'][0].update(acquired_at_utc='yesterday')),('duplicate_excluded_slot',lambda v:v['arrays'][0].update(excluded_slots=['0:0','0:0']))]:
 v=copy.deepcopy(base);change(v);accepted=True
 try:read_geometry(v)
 except InvalidInput:accepted=False
 out.append({'case':name,'value':v,'python_accepted':accepted})
(p/'probe_geometry_validation.inputs.json').write_text(json.dumps(out,indent=2))
