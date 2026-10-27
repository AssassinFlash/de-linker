from __future__ import annotations
import base64,copy,json,math,tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from pyproj import Geod
from linker_engine.planning.workspace import Workspace
from linker_engine.planning.assets import Assets
from linker_engine.planning.geometry_import import GeometryImport
from linker_engine.planning.geometry_import_documents import GeometryImportOptions
from linker_engine.planning.geographic import GeographicBridge
from linker_engine.planning.records import Actor
from linker_engine.planning.energy_kernel import EnergyKernel
from linker_engine.planning.energy_service import EnergyService
from linker_engine.planning.numerical_tolerance import Tolerance
from linker_engine.planning.http_app import create_private_app,HttpLimits
from linker_engine.planning.canonical import digest
ROOT=Path(__file__).resolve().parent
OPTIONS=json.loads((ROOT/'fixtures/planning/geometry-import-options.json').read_text())
TOKEN='synthetic-spec-geographic-token'
HEADERS={'X-Linker-Service-Token':TOKEN,'X-Linker-Planner-Principal-Kind':'user','X-Linker-Planner-Principal-Subject':'spec-owner'}
records=[]
def polygon(west,east,south=0,north=.00009):return {'type':'Polygon','coordinates':[[[west,south],[east,south],[east,north],[west,north],[west,south]]]}
with tempfile.TemporaryDirectory(prefix='geo-spec-runtime-',dir=ROOT)as d:
 ws=Workspace(Path(d));kernel=EnergyKernel(ws,Tolerance(1e-7,1e-7,1e-9),max_intervals=100);service=EnergyService(ws,kernel,max_attempts=1)
 with TestClient(create_private_app(ws,service,credential=lambda:TOKEN,limits=HttpLimits(100000,10000,10,32)),raise_server_exceptions=False)as c:
  def post(path,body):return c.post(path,json={'schema_version':1,**body},headers=HEADERS)
  def project(name):
   r=post('/projects/create',{'title':name,'inputs':{},'key':name});assert r.status_code==200,r.text;return r.json()['id']
  options=copy.deepcopy(OPTIONS);options['reference'].update(longitude_deg=0,latitude_deg=0);options['plane'].update(origin_enu=[0,0,5],u_axis_enu=[1,0,0],v_axis_enu=[0,1,0])
  for name,shape in [('local',polygon(.00001,.00010)),('antipodal',polygon(179.99990,179.99999)),('near_horizon',polygon(89.99990,89.99999))]:
   pid=project(name);raw=json.dumps(shape).encode();r=post('/geometry/import',{'project_id':pid,'content_base64':base64.b64encode(raw).decode(),'options':options,'key':'source'})
   row={'case':name,'status':r.status_code,'source_bounds':[shape['coordinates'][0][0],shape['coordinates'][0][2]]}
   if r.status_code==200:
    prepared=r.json()['metadata']['geometry_import'];roof=prepared['geometry']['roofs'][0];bridge=GeographicBridge(GeometryImportOptions.model_validate(options).reference);p=shape['coordinates'][0][0];enu=bridge.forward(*p,0);uv=roof['boundary_uv'][0];back=bridge.inverse(uv[0],uv[1],5)
    row.update(area_m2=prepared['area_roof_plane_m2'],boundary_uv=roof['boundary_uv'],full_source_enu=enu,roof_point_inverse=back,source_to_candidate_surface_distance_m=Geod(ellps='WGS84').inv(p[0],p[1],back[0],back[1])[2],geometry_stored=True,engineering_status=prepared['engineering_status'])
   else:row['response']=r.json()
   records.append(row)
  pid=project('hash-link');raw=(ROOT/'fixtures/planning/source-roof-wgs84.geojson').read_bytes();r=post('/geometry/import',{'project_id':pid,'content_base64':base64.b64encode(raw).decode(),'options':OPTIONS,'key':'source'});assert r.status_code==200,r.text;asset=r.json();g=copy.deepcopy(asset['metadata']['geometry_import']['geometry']);sid=g['sources'][0]['id'];inputs={'geometry':g,'geometry_imports':{'schema_version':1,'selected':{sid:asset['id']}}}
  r=post('/projects/revise',{'project_id':pid,'expected_revision':1,'inputs':inputs,'key':'attach'});assert r.status_code==200,r.text
  notes=copy.deepcopy(inputs);notes['geometry']['sources'][0]['note']='Explicit later source note';r=post('/projects/revise',{'project_id':pid,'expected_revision':2,'inputs':notes,'key':'notes'});assert r.status_code==200,r.text
  tampered=copy.deepcopy(notes);tampered['geometry']['sources'][0]['reference_sha256']='0'*64;r=post('/projects/revise',{'project_id':pid,'expected_revision':3,'inputs':tampered,'key':'repoint-original'})
  raw_reply=post('/assets/content',{'project_id':pid,'asset_id':asset['id']});assert raw_reply.status_code==200
  records.append({'case':'source_reference_hash_changed_while_bound','status':r.status_code,'source_id':sid,'asset_id':asset['id'],'original_hash':digest(raw_reply.content),'current_reference_hash':r.json()['inputs']['geometry']['sources'][0]['reference_sha256']if r.status_code==200 else None,'notes_only_status':200,'response_code':r.json().get('code')})
(ROOT/'probe_geographic_edges.results.json').write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records,indent=2))
