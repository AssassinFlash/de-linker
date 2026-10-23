import json, copy
from pathlib import Path
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_review import review_geometry
base=json.loads((Path(__file__).parent/'fixtures/planning/geometry-flat.json').read_text())
base['roofs'][0]['origin_enu']=[0,0,4]
base['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,2])
base['arrays'].append({**base['arrays'][0],'id':'second','origin_uv':[1.99,2]})
for left in [0,-1e15]:
 v=copy.deepcopy(base);v['roofs'][0]['boundary_uv']=[[left,0],[20,0],[20,20],[left,20]]
 read_geometry(v);r=review_geometry(v)
 print(json.dumps({'left_boundary':left,'geometry_status':r['geometry_status'],'conflicts':r['conflict_count'],'complete':r['review_complete'],'kinds':[i['kind']for i in r['issues']]}))
