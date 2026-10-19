/**
 * Grounding for campaign #331: the real product sets the battery's product
 * references are judged against, read from the local instance's engineering
 * feed (the same data the configurator sizes against; docs/specs/7-*.md).
 *
 * The written file names the snapshot the instance was loaded from
 * (`~/de-linker-local/<instance>/snapshot.json`, written by linker-pull)
 * and the git revision of this checkout. A later reader can see which
 * catalogue and which code the ids belong to.
 *
 * Usage: node grounding.mjs <wp-base> <out.json>
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// harness/ -> campaign-331 -> research -> docs -> repo root.
const REPO_ROOT = fileURLToPath(new URL('../../../../', import.meta.url));

/**
 * Provenance fields. `snapshotJson` is the instance's snapshot.json text
 * (null when that file is absent). `gitRev` is `git rev-parse HEAD`.
 */
export function provenanceFields(snapshotJson, gitRev) {
	let note = null;
	if (snapshotJson) {
		note = JSON.parse(snapshotJson);
	}
	return {
		snapshot: note?.name ?? null,
		snapshot_taken: note?.taken ?? null,
		snapshot_loaded: note?.loaded ?? null,
		git_rev: gitRev ?? null,
	};
}

function readSnapshot(instance) {
	const path = `${process.env.HOME}/de-linker-local/${instance}/snapshot.json`;
	try {
		return readFileSync(path, 'utf8');
	} catch {
		return null;
	}
}

function gitRev() {
	try {
		return execFileSync('git', ['rev-parse', 'HEAD'], {
			cwd: REPO_ROOT,
			encoding: 'utf8',
		}).trim();
	} catch {
		return null;
	}
}

const invokedDirectly =
	process.argv[1] !== undefined &&
	resolve(process.argv[1]) === fileURLToPath(import.meta.url);

if (invokedDirectly) {
	await main();
}

async function main() {
const base = process.argv[2] ?? 'http://127.0.0.1:9165';
const out = process.argv[3] ?? 'grounding.json';
const instance = process.env.C331_INSTANCE ?? process.env.LINKER_E2E_INSTANCE ?? 'c331';

const response = await fetch(`${base}/wp-json/linker/v1/engineering-feed`);
if (!response.ok) {
	throw new Error(`feed answered ${response.status}`);
}
const feed = (await response.json()).products;

const byClass = (deviceClass, application) =>
	feed
		.filter((p) => p.device_class === deviceClass)
		.filter((p) => application === undefined || p.application === application)
		.map((p) => ({
			id: p.id,
			brand: p.brand,
			model: p.model,
			series: p.series,
			phase: p.phase,
			ac_power_kw: p.ac_power_kw,
			usable_kwh: p.usable_kwh,
		}));

const grounding = {
	fetched_at: new Date().toISOString(),
	base,
	...provenanceFields(readSnapshot(instance), gitRev()),
	count: feed.length,
	sets: {
		homeHybridInverters: byClass('inverters', 'home'),
		commercialInverters: byClass('inverters', 'commercial'),
		homeStorage: byClass('home-storage', 'home'),
		batterySystems: byClass('battery-systems'),
		evChargers: byClass('ev-chargers'),
		ems: byClass('ems-monitoring'),
	},
	known: {
		/** The R13 product (genie-dock.spec.ts): SAJ H2-10K-T3, home, three-phase. */
		sajH2_10k_t3: feed.find((p) => p.model === 'H2-10K-T3'),
		goodweEsa: feed.filter((p) => p.series === 'ESA' || (p.model ?? '').startsWith('GW')),
	},
};
writeFileSync(out, JSON.stringify(grounding, null, 2));
console.log(
	`wrote ${out}: ${feed.length} products; home inverters ${grounding.sets.homeHybridInverters.length}, commercial ${grounding.sets.commercialInverters.length}, home storage ${grounding.sets.homeStorage.length}, ev ${grounding.sets.evChargers.length}; snapshot ${grounding.snapshot}; git ${grounding.git_rev}`
);
}
