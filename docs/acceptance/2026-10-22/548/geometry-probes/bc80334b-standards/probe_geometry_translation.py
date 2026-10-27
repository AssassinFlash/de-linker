import json, copy
from pathlib import Path
from linker_engine.planning.geometry import read_geometry,panel_poses,roof_coordinates
from linker_engine.planning.geometry_review import review_geometry
root=Path(__file__).parent
v=json.loads((root/'fixtures/planning/geometry-flat.json').read_text())
v['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,2])
v['arrays'].append({**v['arrays'][0],'id':'second','origin_uv':[1.99,2]})
for origin in ([0,0,4],[1e15,0,4]):
 value=copy.deepcopy(v);value['roofs'][0]['origin_enu']=origin
 doc=read_geometry(value);report=review_geometry(value)
 print(json.dumps({'origin':origin,'status':report['geometry_status'],'conflict_count':report['conflict_count'],'issues':[i['kind'] for i in report['issues']],'panel_bounds':[[min(p[0] for p in [roof_coordinates(doc.roofs[0],pt) for pt in pose.corners()]),max(p[0] for p in [roof_coordinates(doc.roofs[0],pt) for pt in pose.corners()])] for pose in panel_poses(doc)]}))
