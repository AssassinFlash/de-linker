import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { GeographicBridge, horizontalOnRoof, geographicOnRoof } from './geographic.ts';
import {readGeometryImportCommand, readPreparedGeometryImport} from './geometryImports.ts';
const reference=(latitude=0,height=0)=>({schema_version:1,method:'wgs84_cart_topocentric_v1',longitude_deg:0,latitude_deg:latitude,ellipsoid_height_m:height,height_basis:'known_wgs84_ellipsoid'});

test('both polar branches refuse unsupported computed heights and retain valid negative heights',()=>{
  for(const latitude of [-90,90]) {
    for(const height of [0,Number.MAX_SAFE_INTEGER]) {
      const bridge=new GeographicBridge(reference(latitude,height));
      assert.throws(()=>bridge.inverse([0,0,Number.MAX_SAFE_INTEGER]),/numeric_support/);
    }
    const bridge=new GeographicBridge(reference(latitude));
    const point=bridge.inverse([0,0,-100]);
    assert.equal(point[1],latitude);assert.equal(point[2],-100);
  }
});
test('large absolute Up does not change local horizontal slope and geographic branch remains distinct',()=>{
 const plane={origin_enu:[0,0,1e15],u_axis_enu:[1,0,0],v_axis_enu:[0,.8,-.6]};
 assert.deepEqual(horizontalOnRoof(plane,[0,.1]),[0,.125]);
 const bridge=new GeographicBridge({...reference(),height_basis:'zero_height_horizontal_convention'});
 assert.throws(()=>geographicOnRoof(bridge,plane,[0,.001]));
 for(const longitude of [179.9999,89.9999,90])assert.throws(()=>geographicOnRoof(bridge,{...plane,origin_enu:[0,0,0],v_axis_enu:[0,1,0]},[longitude,0]));
});
test('legacy method declaration is never defaulted into a newly attachable result',()=>{
 const fixture=JSON.parse(readFileSync(new URL('../../../../fixtures/planning/geometry-import-asset.json',import.meta.url),'utf8'));
 for(const absent of ['missing','null']) {
   const candidate=structuredClone(fixture);
   if(absent==='missing') {
     delete candidate.metadata.geometry_import_options.plane_intersection_method;
     delete candidate.metadata.geometry_import.plane_intersection_method;
   } else {
     candidate.metadata.geometry_import_options.plane_intersection_method=null;
     candidate.metadata.geometry_import.plane_intersection_method=null;
   }
   const body={schema_version:1,project_id:fixture.project_id,key:'independent-exact-intent',content_base64:'eA==',options:candidate.metadata.geometry_import_options};
   const before=structuredClone(body);
   assert.equal(readGeometryImportCommand(body),body);
   assert.deepEqual(body,before);
   assert.throws(()=>readPreparedGeometryImport(candidate,fixture.project_id),/invalid_geometry_import_reply/);
 }
});
