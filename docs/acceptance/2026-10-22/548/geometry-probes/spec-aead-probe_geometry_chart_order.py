import json,copy
from pathlib import Path
from linker_engine.planning.geometry_review import review_geometry
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());base['roofs'][0]['origin_enu']=[0,0,4];base['module_specs'][0]['width_m']=2;base['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,1]);base['arrays'].append({**base['arrays'][0],'id':'second','origin_uv':[2.99,1]});ring=[[-9e15,-10],[10,-10],[10,10],[-9e15,10]];out=[]
for first in range(4):
 v=copy.deepcopy(base);v['roofs'][0]['boundary_uv']=ring[first:]+ring[:first];r=review_geometry(v);out.append({'ring_first_index':first,'expected_overlap_m2':.02,'status':r['geometry_status'],'conflicts':r['conflict_count'],'kinds':[i['kind']for i in r['issues']if i['category']=='layout_conflict']})
(p/'probe_geometry_chart_order.results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
