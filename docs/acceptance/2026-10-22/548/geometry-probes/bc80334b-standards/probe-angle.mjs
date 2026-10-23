import fs from 'node:fs';
import {panelPoses} from './apps/planner/src/domain/panelPoses.ts';
const value=JSON.parse(fs.readFileSync(new URL('./fixtures/planning/geometry-flat.json',import.meta.url)));
value.roofs[0].origin_enu=[0,0,4];value.arrays[0].rotation_deg=6898968225049280;
console.log(JSON.stringify(panelPoses(value)[0]));
