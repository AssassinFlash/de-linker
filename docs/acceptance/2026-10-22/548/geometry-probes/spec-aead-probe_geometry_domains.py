import json,copy,math,time
from pathlib import Path
from linker_engine.planning.geometry import read_geometry
from linker_engine.planning.geometry_review import review_geometry
from linker_engine.planning.errors import InvalidInput
p=Path(__file__).resolve().parent;base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text());base['roofs'][0]['origin_enu']=[0,0,0];base['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[1,1]);results=[]
def check(name,v,want=(),unwanted=()):
 before=copy.deepcopy(v);r=review_geometry(v);kinds={i['kind']for i in r['issues']};assert set(want)<=kinds,(name,kinds);assert not(set(unwanted)&kinds),(name,kinds);assert r['engineering_status']=='not_evaluated';assert v==before
 results.append({'case':name,'passed':True,'status':r['geometry_status'],'conflicts':r['conflict_count'],'complete':r['review_complete'],'candidate_checks':r['candidate_checks']});return r
v=copy.deepcopy(base);v['roofs'][0]['boundary_uv']=[[0,0],[4,0],[4,1],[1,1],[1,4],[0,4]];v['arrays'][0]['origin_uv']=[1.5,1.5];check('concave_roof_recess_not_filled',v,['panel_outside_roof'])
v=copy.deepcopy(base);v['roofs'][0]['holes_uv']=[[[1.2,1.2],[1.8,1.2],[1.8,2.5],[1.2,2.5]]];check('hole_not_filled',v,['panel_over_opening'])
v=copy.deepcopy(base);v['module_specs'][0]['thickness_m']=.1;v['arrays'][0].update(mount_tilt_deg=45,origin_uv=[1,.05]);check('cuboid_thickness_crosses_edge',v,['panel_outside_roof']);v['arrays'][0]['origin_uv']=[1,.08];check('cuboid_thickness_inside_edge',v,unwanted=['panel_outside_roof'])
v=copy.deepcopy(base);v['roofs'][0]['v_axis_enu']=[0,math.sqrt(3)/2,.5];v['obstacles']=[{'id':'vent','name':'Vertical vent','source_id':'survey','roof_id':'roof','footprint_uv':[[1,0],[2,0],[2,.75],[1,.75]],'extrusion_axis_enu':[0,0,1],'height_m':1}];check('world_vertical_extrusion_projects_on_sloped_face',v,['panel_projected_obstacle_overlap'])
v=copy.deepcopy(base);v['keepouts']=[{'id':'access','name':'Touch only','source_id':'survey','roof_id':'roof','footprint_uv':[[2,1],[3,1],[3,3],[2,3]],'reason':'Synthetic analytic boundary'}];check('zero_clearance_boundary_contact_permitted',v,unwanted=['panel_in_keepout'])
v=copy.deepcopy(base);v['arrays'][0].update(rows=5000,mount_tilt_deg=90,row_gap_m=0);start=time.monotonic();r=check('real_candidate_budget_is_explicitly_incomplete',v);assert r['geometry_status']=='incomplete'and r['review_complete']is False and r['module_count']==5000 and r['candidate_checks']==200000;results[-1]['elapsed_s']=time.monotonic()-start
v['arrays'][0]['rows']=5001
try:read_geometry(v);raise AssertionError('5001 accepted')
except InvalidInput:results.append({'case':'slot_budget_5001_refused','passed':True})
(p/'probe_geometry_domains.results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
