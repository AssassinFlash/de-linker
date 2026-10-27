import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { geoJsonChoices } from '../src/domain/geoJsonChoices.ts';

test('independent valid source name does not become an unpaired surrogate at a display cap',()=>{
 const value=JSON.parse(readFileSync(new URL('../../../fixtures/planning/source-roof-wgs84.geojson',import.meta.url),'utf8'));
 const original='a'.repeat(255)+'\u{1f642}';
 value.properties={name:original};
 const raw=Buffer.from(JSON.stringify(value),'utf8');
 const choice=geoJsonChoices(raw.toString('base64'))[0];
 console.log(JSON.stringify({probe:'choice-unicode',input_name_well_formed:original.isWellFormed(),input_utf16_units:original.length,output_utf16_units:choice.name.length,output_name_well_formed:choice.name.isWellFormed(),last_code_unit:choice.name.charCodeAt(choice.name.length-1)}));
 assert.ok(choice.name.isWellFormed(),'a valid source name must not be split inside a Unicode character');
});
