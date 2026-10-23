from __future__ import annotations
import base64,copy,json,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
import linker_engine.planning.geometry_import as gm
from linker_engine.planning.workspace import Workspace
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.http_app import create_private_app,HttpLimits
ROOT=Path(__file__).resolve().parent
SOURCE=(ROOT/'fixtures/planning/source-roof-wgs84.geojson').read_bytes();BASE=json.loads(SOURCE);OPTIONS=json.loads((ROOT/'fixtures/planning/geometry-import-options.json').read_text())
TOKEN='synthetic-spec-geographic-token';HEADERS={'X-Linker-Service-Token':TOKEN,'X-Linker-Planner-Principal-Kind':'user','X-Linker-Planner-Principal-Subject':'spec-parser-owner'}
def changed(fn):d=copy.deepcopy(BASE);fn(d);return json.dumps(d).encode()
cases=[('invalid_json',b'{'),('duplicate_members',b'{"type":"Feature","type":"Polygon"}'),('unknown_crs',changed(lambda d:d.update(crs={'type':'name'}))),('geometry_crs',changed(lambda d:d['geometry'].update(crs={}))),('boolean_id',changed(lambda d:d.update(id=True))),('unsafe_integer_id',changed(lambda d:d.update(id=2**53+1))),('invalid_unicode_id',changed(lambda d:d.update(id='\ud800'))),('overflow_exponent_id',changed(lambda d:d.update(id='__NUM__')).replace(b'"__NUM__"',b'1e400')),('boolean_coordinate',changed(lambda d:d['geometry']['coordinates'][0][0].__setitem__(0,True))),('string_coordinate',changed(lambda d:d['geometry']['coordinates'][0][0].__setitem__(0,'6.96'))),('third_coordinate',changed(lambda d:d['geometry']['coordinates'][0][0].append(0))),('unclosed_ring',changed(lambda d:d['geometry']['coordinates'][0][-1].__setitem__(0,6.9)))]
records=[]
with tempfile.TemporaryDirectory(dir=ROOT,prefix='parser-runtime-')as d:
 ws=Workspace(Path(d));kernel=EnergyKernel(ws,Tolerance(1e-7,1e-7,1e-9),max_intervals=100);service=EnergyService(ws,kernel,max_attempts=1)
 with TestClient(create_private_app(ws,service,credential=lambda:TOKEN,limits=HttpLimits(100000,10000,10,32)),raise_server_exceptions=False)as c:
  def post(path,body,headers=HEADERS):return c.post(path,json={'schema_version':1,**body},headers=headers)
  r=post('/projects/create',{'title':'Independent parser/replay checks','inputs':{},'key':'create'});assert r.status_code==200;pid=r.json()['id'];before={p.relative_to(ws.blobs.directory).as_posix()for p in ws.blobs.directory.rglob('*')if p.is_file()}
  for name,raw in cases:
   r=post('/geometry/import',{'project_id':pid,'content_base64':base64.b64encode(raw).decode(),'options':OPTIONS,'key':name});after={p.relative_to(ws.blobs.directory).as_posix()for p in ws.blobs.directory.rglob('*')if p.is_file()};records.append({'case':name,'status':r.status_code,'code':r.json().get('code'),'published_bytes':after!=before});assert r.status_code==422,(name,r.text);assert before==after
  for name,axis in [('nonunit',[2,0,0]),('nonorthogonal',[.6,.8,0]),('vertical',[0,0,-1])]:
   o=copy.deepcopy(OPTIONS);o['plane']['u_axis_enu'if name=='nonunit'else'v_axis_enu']=axis;r=post('/geometry/import',{'project_id':pid,'content_base64':base64.b64encode(SOURCE).decode(),'options':o,'key':name});assert r.status_code==422,(name,r.text);after={p.relative_to(ws.blobs.directory).as_posix()for p in ws.blobs.directory.rglob('*')if p.is_file()};assert after==before;records.append({'case':name,'status':r.status_code,'published_bytes':False})
  command={'project_id':pid,'content_base64':base64.b64encode(SOURCE).decode(),'options':OPTIONS,'key':'stable-source'};r=post('/geometry/import',command);assert r.status_code==200;asset=r.json()
  previous=gm.GeographicBridge
  def unexpected(*a,**kw):raise AssertionError('Projection must not rerun while resolving a permanent receipt')
  gm.GeographicBridge=unexpected
  try:
   again=post('/geometry/import',command);replay=post('/operations/replay/geometry/import',command);assert again.status_code==200 and again.json()==asset;assert replay.status_code==200 and replay.json()['result']==asset
   changed_body=copy.deepcopy(command);changed_body['options']['roof_name']='Changed command';conflict=post('/geometry/import',changed_body);assert conflict.status_code==409
   foreign=dict(HEADERS);foreign['X-Linker-Planner-Principal-Subject']='spec-parser-foreign';foreign_reply=post('/geometry/import',{**command,'content_base64':'!'},foreign);assert foreign_reply.status_code==404
   raw=c.post('/assets/content',json={'schema_version':1,'project_id':pid,'asset_id':asset['id']},headers=HEADERS);assert raw.content==SOURCE
   ws.blobs._path(asset['content_sha256']).unlink();missing=post('/operations/replay/geometry/import',command);assert missing.status_code==503
   records.append({'case':'receipt_under_changed_runtime','same_import_status':again.status_code,'permanent_replay_status':replay.status_code,'changed_body_status':conflict.status_code,'foreign_malformed_status':foreign_reply.status_code,'raw_bytes_identical':True,'missing_original_replay_status':missing.status_code})
  finally:gm.GeographicBridge=previous
(ROOT/'probe_parser_and_replay.results.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps({'invalid_cases':len(cases)+3,'all_typed422_without_publication':True,'receipt_replay_and_ownership':'passed'}))
