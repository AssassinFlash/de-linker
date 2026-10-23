"""Independent fixed-SHA Standards probes; synthetic local ASGI/storage only."""
from __future__ import annotations
import base64
import copy
import json
from pathlib import Path
import pytest
from test_private_http import Rig, USER, FOREIGN, TEAM, headers, rig
from linker_engine.planning.assets import Assets
from linker_engine.planning.geometry_import import GeometryImport
from linker_engine.planning.geometry_import_documents import GeometryImportOptions
from linker_engine.planning.http_views import asset_view

ROOT = Path(__file__).resolve().parents[4]

def command(project_id: str, key: str = 'independent-import') -> dict:
    return {'schema_version': 1, 'project_id': project_id,
            'content_base64': base64.b64encode((ROOT/'fixtures/planning/source-roof-wgs84.geojson').read_bytes()).decode(),
            'options': json.loads((ROOT/'fixtures/planning/geometry-import-options.json').read_text()), 'key': key}

@pytest.mark.parametrize('actor', [FOREIGN, TEAM])
@pytest.mark.parametrize('path', ['/geometry/import', '/operations/replay/geometry/import'])
def test_acl_precedes_decoder_and_durable_storage(rig: Rig, monkeypatch, actor, path):
    project = rig.create('decoder-guard')
    body=command(project)
    body['content_base64']='!'
    before=set(rig.workspace.blobs.directory.rglob('*'))
    def forbidden_decoder(_content):
        raise AssertionError('decoder executed before ownership')
    monkeypatch.setattr(GeometryImport, 'decode', staticmethod(forbidden_decoder))
    result=rig.client.post(path,json=body,headers=headers(actor))
    assert result.status_code == 404, result.text
    assert set(rig.workspace.blobs.directory.rglob('*')) == before

@pytest.mark.parametrize('method', ['missing', None])
def test_no_implicit_method_or_new_blob(rig: Rig, method):
    project=rig.create('explicit-method')
    body=command(project)
    if method == 'missing': del body['options']['plane_intersection_method']
    else: body['options']['plane_intersection_method']=method
    before=set(rig.workspace.blobs.directory.rglob('*'))
    refused=rig.client.post('/geometry/import',json=body,headers=headers())
    assert refused.status_code == 503, refused.text
    assert refused.json()['error']['code']=='version_unavailable'
    assert set(rig.workspace.blobs.directory.rglob('*')) == before

def test_real_legacy_http_receipt_replays_without_new_conversion(rig: Rig, monkeypatch):
    project=rig.create('legacy-method')
    body=command(project)
    del body['options']['plane_intersection_method']
    options=GeometryImportOptions.model_validate(body['options'])
    intake=GeometryImport(Assets(rig.workspace))
    content=base64.b64decode(body['content_base64'])
    # Server-trusted pre-upgrade immutable record, deliberately not a newly prepared candidate.
    logical=intake.logical(options)
    assert logical['geometry_import_options']==body['options']
    old=intake.assets.add(USER,project,content,'application/geo+json','geometry_import_v1',
                         {**logical,'review_legacy_marker':'must-remain-identical'},
                         key=body['key'],logical_metadata=logical)
    def forbidden_conversion(*args,**kwargs): raise AssertionError('legacy receipt was recalculated')
    monkeypatch.setattr('linker_engine.planning.geometry_import.GeographicBridge', forbidden_conversion)
    expected=asset_view(old)
    assert rig.post('/geometry/import',body)==expected
    replay=rig.post('/operations/replay/geometry/import',body)
    assert replay['status']=='replayed' and replay['result']==expected
    null=copy.deepcopy(body);null['options']['plane_intersection_method']=None
    assert rig.client.post('/geometry/import',json=null,headers=headers()).status_code==409
    explicit=copy.deepcopy(body);explicit['options']['plane_intersection_method']='geodetic_vertical_line_v1'
    assert rig.client.post('/geometry/import',json=explicit,headers=headers()).status_code==409

def test_bound_current_hash_refusal_preserves_revision_but_notes_remain_editable(rig: Rig):
    project=rig.create('bound-hash')
    asset=rig.post('/geometry/import',command(project))
    prepared=asset['metadata']['geometry_import']
    geometry=prepared['geometry'];source_id=geometry['sources'][0]['id']
    inputs={'geometry':geometry,'geometry_imports':{'schema_version':1,'selected':{source_id:asset['id']}}}
    saved=rig.post('/projects/revise',{'project_id':project,'expected_revision':1,'key':'attach','inputs':inputs})
    assert saved['revision']==2
    tampered=copy.deepcopy(inputs);tampered['geometry']['sources'][0]['reference_sha256']='f'*64
    refused=rig.client.post('/projects/revise',json={'schema_version':1,'project_id':project,'expected_revision':2,'key':'bad-hash','inputs':tampered},headers=headers())
    assert refused.status_code==422,refused.text
    assert rig.post('/projects/read',{'project_id':project,'revision':None})['revision']==2
    notes=copy.deepcopy(inputs);notes['geometry']['sources'][0]['note']='Independent synthetic amended source note'
    allowed=rig.post('/projects/revise',{'project_id':project,'expected_revision':2,'key':'notes','inputs':notes})
    assert allowed['revision']==3
    raw=rig.client.post('/assets/content',json={'schema_version':1,'project_id':project,'asset_id':asset['id']},headers=headers())
    assert raw.content==base64.b64decode(command(project)['content_base64'])

def test_same_source_conversion_other_key_has_same_domain_ids_and_missing_raw_is_refused(rig: Rig):
    project=rig.create('stable-source')
    first=rig.post('/geometry/import',command(project,'key-a'))
    second=rig.post('/geometry/import',command(project,'key-b'))
    assert first['id']!=second['id']
    assert first['metadata']['geometry_import']['geometry']==second['metadata']['geometry_import']['geometry']
    geometry=first['metadata']['geometry_import']['geometry'];source=geometry['sources'][0]['id']
    sha=first['content_sha256']
    (rig.workspace.blobs.directory/sha[:2]/sha).unlink()
    inputs={'geometry':geometry,'geometry_imports':{'schema_version':1,'selected':{source:first['id']}}}
    refused=rig.client.post('/projects/revise',json={'schema_version':1,'project_id':project,'expected_revision':1,'key':'missing-original','inputs':inputs},headers=headers())
    assert refused.status_code==503,refused.text
    assert rig.post('/projects/read',{'project_id':project,'revision':None})['revision']==1
