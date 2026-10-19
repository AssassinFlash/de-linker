/**
 * Grounding for campaign #331: the real product sets the battery's product
 * references are judged against, read from the local instance's engineering
 * feed (the same data the configurator sizes against; docs/specs/7-*.md).
 *
 * Usage: node grounding.mjs <wp-base> <out.json>
 */
import { writeFileSync } from 'node:fs';

const base = process.argv[2] ?? 'http://127.0.0.1:9165';
const out = process.argv[3] ?? 'grounding.json';

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
	`wrote ${out}: ${feed.length} products; home inverters ${grounding.sets.homeHybridInverters.length}, commercial ${grounding.sets.commercialInverters.length}, home storage ${grounding.sets.homeStorage.length}, ev ${grounding.sets.evChargers.length}`
);
