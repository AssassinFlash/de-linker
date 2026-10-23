from __future__ import annotations
import copy,json,tempfile
from pathlib import Path
import pytest
from linker_engine.planning.workspace import Workspace
from linker_engine.planning.assets import Assets
from linker_engine.planning.records import Actor
from linker_engine.planning.errors import InvalidInput,VersionUnavailable
from linker_engine.planning.geometry_import import GeometryImport
from linker_engine.planning.geometry_import_documents import GeometryImportOptions,ImportedPlane
from linker_engine.planning.geometry_import_selections import check_geometry_imports
from linker_engine.planning.geographic import horizontal_on_roof
ROOT=Path(__file__).resolve().parent
USER=Actor('user','spec-counter-owner')
def options():return json.loads((ROOT/'fixtures/planning/geometry-import-options.json').read_text())
@pytest.mark.parametrize('west,east',[(179.99990,179.99999),(89.99990,89.99999)],ids=['back-facing-antipode','near-horizon-numerically-unsupported'])
def test_horizontal_intake_refuses_a_folded_or_singular_chart(west,east):
 o=options();o['reference'].update(longitude_deg=0,latitude_deg=0);o['plane'].update(origin_enu=[0,0,5],u_axis_enu=[1,0,0],v_axis_enu=[0,1,0]);raw=json.dumps({'type':'Polygon','coordinates':[[[west,0],[east,0],[east,.00009],[west,.00009],[west,0]]]}).encode()
 with tempfile.TemporaryDirectory(dir=ROOT,prefix='counter-runtime-')as d:
  w=Workspace(Path(d));p=w.create(USER,'Synthetic local-chart counterexample',{},key='create');assets=Assets(w)
  with pytest.raises(InvalidInput):GeometryImport(assets).prepare(USER,p.id,raw,GeometryImportOptions.model_validate(o),key='source')
def test_horizontal_plane_local_metric_result_is_translation_invariant():
 normal=ImportedPlane(origin_enu=[0,0,0],u_axis_enu=[1,0,0],v_axis_enu=[0,.8,-.6],basis_note='Analytic 3-4-5 plane')
 huge=normal.model_copy(update={'origin_enu':[0,0,1e15]})
 assert horizontal_on_roof(normal,0,.1)==pytest.approx((0,.125),abs=1e-12)
 assert horizontal_on_roof(huge,0,.1)==pytest.approx((0,.125),abs=1e-12)
def test_bound_source_reference_hash_cannot_be_repointed_to_another_original():
 with tempfile.TemporaryDirectory(dir=ROOT,prefix='counter-runtime-')as d:
  w=Workspace(Path(d));p=w.create(USER,'Synthetic bound source',{},key='create');assets=Assets(w);raw=(ROOT/'fixtures/planning/source-roof-wgs84.geojson').read_bytes();a=GeometryImport(assets).prepare(USER,p.id,raw,GeometryImportOptions.model_validate(options()),key='source');geometry=copy.deepcopy(a.metadata['geometry_import']['geometry']);source=geometry['sources'][0];source['note']='A later note is intentionally editable';inputs={'geometry':geometry,'geometry_imports':{'schema_version':1,'selected':{source['id']:a.id}}};check_geometry_imports(assets,USER,p.id,inputs);source['reference_sha256']='0'*64
  with pytest.raises((InvalidInput,VersionUnavailable)):check_geometry_imports(assets,USER,p.id,inputs)
