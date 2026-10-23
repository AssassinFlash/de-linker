import assert from 'node:assert/strict';
import test from 'node:test';
import React,{act} from 'react';
import {readFileSync} from 'node:fs';
import {setupDom} from './dom-fixture.mjs';
import {ProjectOverview} from '../src/components/ProjectOverview.tsx';
import {emptyBrief} from '../src/domain/brief.ts';
import {emptyGeometry} from '../src/domain/geometryCommands.ts';
const flat=JSON.parse(readFileSync(new URL('../../../fixtures/planning/geometry-flat.json',import.meta.url),'utf8'));
const catalog=JSON.parse(readFileSync(new URL('../../../plugins/linker-tools/languages/linker-tools-de_DE_formal-cf89287c9001d7518d0d20e58c3eb721.json',import.meta.url),'utf8')).locale_data.messages;
async function mount(t,geometry,brief,locale='en-US'){
 const fixture=setupDom();
 if(locale.startsWith('de'))window.wp.i18n.__=(message)=>catalog[message]?.[0]||message;
 const {createRoot}=await import('react-dom/client');const root=createRoot(fixture.element);
 t.after(()=>fixture.dispose(root));
 const actions=[];
 await act(async()=>root.render(React.createElement(ProjectOverview,{geometry,brief,config:{locale,countries:{FR:locale.startsWith('de')?'Frankreich':'France'}},choose:(next)=>actions.push(next)})));
 return{fixture,actions,root};
}
for(const locale of ['en-US','de-DE']){
 test('empty overview retains unknown layout and actual explicit zero consumption '+locale,async(t)=>{
  const brief=emptyBrief();brief.site.country_code='FR';brief.annual_load={kwh:0,basis:'bill_total',source_note:'Synthetic bill total'};
  await mount(t,emptyGeometry(),brief,locale);
  const values=[...document.querySelectorAll('.lp-overview-metrics dd')].map(x=>x.textContent.trim());
  assert.deepEqual(values,[locale.startsWith('de')?'Frankreich':'France','0 kWh','—','—']);
  assert.equal(document.querySelector('svg.lp-plan-svg'),null);
  assert.equal(document.querySelector('input,textarea,select'),null);
  assert.ok(document.querySelector('.lp-overview-empty'));
 });
 test('multi-roof summary spans all layouts while preview names and draws only first roof '+locale,async(t)=>{
  const geometry=structuredClone(flat);const first=geometry.roofs[0];const original=geometry.arrays[0];
  geometry.roofs.push({...structuredClone(first),id:'second_roof',name:'Independent second roof'});
  geometry.arrays.push({...structuredClone(original),id:'second_array',roof_id:'second_roof',rows:1,columns:2,excluded_slots:['0:1']});
  const brief=emptyBrief();brief.annual_load={kwh:1234.5,basis:'user_estimate',source_note:'Synthetic estimate'};
  const before=structuredClone(geometry);
  const app=await mount(t,geometry,brief,locale);
  const expected=geometry.arrays.reduce((sum,array)=>sum+array.rows*array.columns-array.excluded_slots.length,0);
  const spec=geometry.module_specs.find(x=>x.id===original.module_spec_id);
  const values=[...document.querySelectorAll('.lp-overview-metrics dd')].map(x=>x.textContent.trim());
  assert.equal(values[2],new Intl.NumberFormat(locale,{maximumFractionDigits:20,useGrouping:false}).format(expected));
  assert.equal(Number(values[3].replace(' kWp','').replace(',','.')),expected*spec.stc_power_w/1000);
  assert.ok(document.querySelector('.lp-overview-preview-title').textContent.includes(first.name));
  assert.ok(!document.querySelector('[data-array="second_array"]'));
  assert.ok(document.querySelector('[data-array="'+original.id+'"]'));
  assert.equal(document.querySelector('.lp-overview-preview .lp-canvas-tools'),null);
  assert.equal(document.querySelector('.lp-overview-preview .lp-canvas-caption'),null);
  assert.equal(document.querySelector('.lp-overview-preview .lp-profile-help'),null);
  assert.deepEqual(geometry,before);
  const button=[...document.querySelectorAll('.lp-overview-preview button')][0];
  await act(async()=>button.click());assert.deepEqual(app.actions,['design']);
 });
}
