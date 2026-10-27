import json,math,copy
from pathlib import Path
from linker_engine.planning.geometry import read_geometry,panel_poses,roof_coordinates
from linker_engine.planning.geometry_review import review_geometry
from shapely.geometry import MultiPoint
p=Path(__file__).resolve().parent
base=json.loads((p/'fixtures/planning/geometry-flat.json').read_text())
base['arrays'][0].update(rows=1,columns=1,excluded_slots=[],origin_uv=[0,0])
base['roofs'][0]['boundary_uv']=[[0,0],[1,0],[1,2],[0,2]]
out=[]
for angle in [0,30,45,60]:
 for origin in [0,10,1e6,1e15]:
  v=copy.deepcopy(base);a=math.radians(angle)
  v['roofs'][0].update(origin_enu=[origin,origin,4],u_axis_enu=[math.cos(a),math.sin(a),0],v_axis_enu=[-math.sin(a),math.cos(a),0])
  d=read_geometry(v);pose=panel_poses(d)[0]
  foot=MultiPoint([roof_coordinates(d.roofs[0],c)for c in pose.corners()]).convex_hull
  r=review_geometry(v)
  out.append({'roof_rotation_deg':angle,'origin':origin,'conflicts':r['conflict_count'],'kinds':[i['kind']for i in r['issues']if i['category']=='layout_conflict'],'uv_bounds':list(foot.bounds)})
# A known 1 cm overlap is affine-invariant under ENU translation.
v=copy.deepcopy(base);v['roofs'][0]['boundary_uv']=[[0,0],[10,0],[10,10],[0,10]]
v['arrays'][0]['origin_uv']=[1,1];v['arrays'].append({**v['arrays'][0],'id':'second','origin_uv':[1.99,1]})
for origin in [0,1e15]:
 v['roofs'][0]['origin_enu']=[origin,0,4];r=review_geometry(v);out.append({'overlap_origin':origin,'analytic_overlap_m2':.02,'geometry_status':r['geometry_status'],'conflicts':r['conflict_count'],'kinds':[i['kind']for i in r['issues']if i['category']=='layout_conflict']})
(p/'probe_geometry_numeric.results.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
