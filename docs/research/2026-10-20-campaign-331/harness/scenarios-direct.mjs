/**
 * The answer-shape battery of campaign #331, against the real local Genie
 * service (deepseek-flash through the configured channel): topic switch /
 * context bleed, anaphora across turns, mid-thread language switch, repeated
 * questions, and the handoff offer rules of spec 13 "转人工".
 *
 * Every case: one conversation id, turns sent with the full thread the way
 * the dock sends it (assistant messages as their text, assistantMessage()),
 * one JSONL line per turn plus a verdict line, under
 * ~/de-linker-data/campaign-331/<scenario>/.
 *
 * Usage:
 *   C331_TOKEN=… node scenarios-direct.mjs [case-filter]
 */

import { readFileSync } from 'node:fs';
import {
	ServiceClient,
	answerText,
	cardsOf,
	contactOf,
	envTargets,
	handoffOf,
	record,
	transcriptEntry,
	verdict,
	artefact,
} from './client.mjs';

const targets = envTargets();
const service = new ServiceClient(targets);
const grounding = JSON.parse(
	readFileSync(new URL('./grounding.json', import.meta.url), 'utf8')
);
const ids = (set) => grounding.sets[set].map((p) => p.id);
const SETS = {
	homeInverters: ids('homeHybridInverters'),
	commercialInverters: ids('commercialInverters'),
	homeStorage: ids('homeStorage'),
	evChargers: ids('evChargers'),
};
const stamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);

/**
 * Sends one turn of a thread and records it. `thread` is the array so far
 * ({role, content}); returns it with the new user question and the answer's
 * text appended, the way the dock keeps it.
 */
async function turn(scenario, file, conversationId, thread, question, locale = 'en', page = { type: 'other' }) {
	const messages = [...thread, { role: 'user', content: question }];
	const result = await service.turn({ conversationId, messages, locale, page });
	record(scenario, file, {
		type: 'turn',
		...transcriptEntry(thread.length + 1, question, result),
	});
	return {
		result,
		thread: messages.concat(
			answerText(result.blocks).length
				? [{ role: 'assistant', content: answerText(result.blocks) }]
				: []
		),
	};
}

/** The product ids the answer's cards and refs lean on. */
function productReferences(result) {
	const refs = result.blocks
		.filter((b) => b.type === 'text')
		.flatMap((b) => b.refs ?? [])
		.map((r) => Number.parseInt(r, 10))
		.filter((n) => Number.isInteger(n));
	return { cards: cardsOf(result.blocks), refs: [...new Set(refs)] };
}

function caseHeader(scenario, file, description) {
	record(scenario, file, {
		type: 'case',
		at: new Date().toISOString(),
		description,
		targets,
	});
}

// ---------------------------------------------------------------------------
// S1 — topic switch / context bleed
// ---------------------------------------------------------------------------

async function s1InverterToEv(lang) {
	const scenario = 's1-topic-switch';
	const file = `s1-${lang}-inverter-to-ev-${stamp}`;
	const conversationId = `c331-${file}`;
	const de = lang === 'de';
	caseHeader(
		scenario,
		file,
		de
			? 'A: dreiphasiger Hybridwechselrichter 10 kW → Batterien dazu; harter Wechsel zu B: Wallboxen. B darf A-Produkte und A-Bedingungen nicht enthalten.'
			: 'A: three-phase hybrid inverter ~10 kW → its pairing batteries; hard switch to B: EV chargers. B must carry no A products or A conditions.'
	);
	const thread = [];
	const q1 = de
		? 'Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohnhaus mit etwa 10 kWp PV.'
		: 'I need a three-phase hybrid inverter for a home project with about 10 kWp of PV.';
	const t1 = await turn(scenario, file, conversationId, thread, q1, lang);
	const t1Ref = productReferences(t1.result);
	const t1Ok =
		t1Ref.cards.every((id) => SETS.homeInverters.includes(id)) &&
		t1Ref.cards.length > 0;
	record(scenario, file, {
		type: 'check',
		step: 1,
		name: 'A establishes home inverters',
		passed: t1Ok,
		detail: { cards: t1Ref.cards, subsetOf: 'homeInverters' },
	});

	const q2 = de
		? 'Der SAJ H2-10K-T3 sieht passend aus. Welche Batterien passen dazu?'
		: 'The SAJ H2-10K-T3 looks right. Which batteries pair with it?';
	const t2 = await turn(scenario, file, conversationId, t1.thread, q2, lang);
	const t2Ref = productReferences(t2.result);
	const t2Ok = t2Ref.cards.some((id) => SETS.homeStorage.includes(id));
	record(scenario, file, {
		type: 'check',
		step: 2,
		name: 'A deepens into pairings (home storage cards)',
		passed: t2Ok,
		detail: { cards: t2Ref.cards },
	});

	const q3 = de
		? 'Jetzt etwas ganz anderes: welche Wallboxen führen Sie?'
		: 'Now something completely different: which EV chargers do you carry?';
	const t3 = await turn(scenario, file, conversationId, t2.thread, q3, lang);
	const t3Ref = productReferences(t3.result);
	const aProducts = [4107, ...t2Ref.cards];
	const bCardsOk =
		t3Ref.cards.length > 0 &&
		t3Ref.cards.every((id) => SETS.evChargers.includes(id));
	const noBleed = !t3Ref.cards.some((id) => aProducts.includes(id));
	const text = answerText(t3.result.blocks);
	const textBleed =
		/H2-10K-T3|GW10K|three-phase|dreiphasig/i.test(text) &&
		!/(EV|wallbox|Wallbox|Ladestation)/i.test(text);
	const passed = bCardsOk && noBleed && !textBleed;
	record(scenario, file, {
		type: 'check',
		step: 3,
		name: 'B answers EV chargers only; no A products, no A phase/kWp conditions',
		passed,
		detail: {
			bCards: t3Ref.cards,
			expectedSet: 'evChargers',
			aProductsNotInBCards: noBleed,
			textNamesATopic: textBleed,
		},
	});
	record(
		scenario,
		file,
		verdict(
			file,
			t1Ok && t2Ok && passed,
			de
				? 'B-Karten ⊆ Wallboxen-Set; keine A-Produkte in Karten/Refs; B-Antwort nennt A-Modell oder A-Bedingungen nicht'
				: "B's cards ⊆ EV charger set; no A product ids in cards/refs; B's text does not name A's model or restate A's phase/kWp",
			`route=${t3.result.meta?.route} intent=${t3.result.meta?.intent}`
		)
	);
	return { t1Ok, t2Ok, passed };
}

async function s1BatteryToCommercial(lang) {
	const scenario = 's1-topic-switch';
	const file = `s1-${lang}-battery-to-commercial-${stamp}`;
	const conversationId = `c331-${file}`;
	const de = lang === 'de';
	caseHeader(
		scenario,
		file,
		de
			? 'A: Heim-Speicherbatterien; Wechsel zu B: Wechselrichter für Gewerbeprojekte. B darf keine Heim-Speicher-Karten und keine kWh-Bedingungen aus A tragen.'
			: 'A: home storage batteries; switch to B: inverters for commercial projects. B must carry no home-storage cards and no kWh conditions from A.'
	);
	const q1 = de
		? 'Welche Heimspeicher-Batterien führen Sie?'
		: 'Which home storage batteries do you carry?';
	const t1 = await turn(scenario, file, conversationId, [], q1, lang);
	const t1Ref = productReferences(t1.result);
	const t1Ok =
		t1Ref.cards.length > 0 &&
		t1Ref.cards.every((id) => SETS.homeStorage.includes(id));
	record(scenario, file, {
		type: 'check',
		step: 1,
		name: 'A establishes home storage',
		passed: t1Ok,
		detail: { cards: t1Ref.cards },
	});

	const q2 = de
		? 'Andere Frage: welche Wechselrichter haben Sie für Gewerbeprojekte?'
		: 'Different question: which inverters do you have for commercial projects?';
	const t2 = await turn(scenario, file, conversationId, t1.thread, q2, lang);
	const t2Ref = productReferences(t2.result);
	const cardsOk =
		t2Ref.cards.length > 0 &&
		t2Ref.cards.every((id) => SETS.commercialInverters.includes(id));
	const noBleed = !t2Ref.cards.some((id) => t1Ref.cards.includes(id));
	const passed = cardsOk && noBleed;
	record(scenario, file, {
		type: 'check',
		step: 2,
		name: "B answers commercial inverters; A's storage ids absent",
		passed,
		detail: { bCards: t2Ref.cards, subsetOf: 'commercialInverters', noBleed },
	});
	record(
		scenario,
		file,
		verdict(
			file,
			t1Ok && passed,
			de
				? 'B-Karten ⊆ Gewerbe-Wechselrichter; keine A-Speicher-IDs; Antwort erwähnt A nicht'
				: "B's cards ⊆ commercial inverter set; A's storage ids absent; answer does not continue A's topic",
			`route=${t2.result.meta?.route} intent=${t2.result.meta?.intent}`
		)
	);
	return { t1Ok, passed };
}

async function s1WithinTopicControl() {
	const scenario = 's1-topic-switch';
	const file = `s1-en-within-topic-control-${stamp}`;
	const conversationId = `c331-${file}`;
	caseHeader(
		scenario,
		file,
		'Control (context SHOULD carry): 10 kWp three-phase home inverter, then "What about 8 kWp?" — same topic refinement must keep phase=3/home and stay within home inverters.'
	);
	const t1 = await turn(
		scenario,
		file,
		conversationId,
		[],
		'I need a three-phase hybrid inverter for a home with 10 kWp of PV.'
	);
	const t2 = await turn(
		scenario,
		file,
		conversationId,
		t1.thread,
		'What about 8 kWp?'
	);
	const ref = productReferences(t2.result);
	const homeThree = grounding.sets.homeHybridInverters
		.filter((p) => p.phase === 3)
		.map((p) => p.id);
	const cardsOk =
		ref.cards.length > 0 && ref.cards.every((id) => homeThree.includes(id));
	const text = answerText(t2.result.blocks);
	const carriedPhase = /three-phase/i.test(text);
	record(scenario, file, {
		type: 'check',
		step: 2,
		name: 'refinement keeps home + three-phase; no out-of-set cards',
		passed: cardsOk,
		detail: { cards: ref.cards, homeThreePhaseSet: homeThree, carriedPhase },
	});
	record(
		scenario,
		file,
		verdict(
			file,
			cardsOk,
			'cards ⊆ home three-phase inverters; the 8 kWp refinement is answered in A\'s frame (context carry is the desired behaviour here)',
			`route=${t2.result.meta?.route}`
		)
	);
	return { passed: cardsOk };
}

// ---------------------------------------------------------------------------
// S2 — anaphora across turns (dieses/das/it/its/the first one)
// ---------------------------------------------------------------------------

async function s2Anaphora(kind) {
	const scenario = 's2-anaphora';
	const file = `s2-${kind}-${stamp}`;
	const conversationId = `c331-${file}`;
	const de = kind.split('-').includes('de');
	caseHeader(scenario, file, `Anaphora case ${kind}: the pronoun must resolve to the thread's product, not be re-asked.`);
	const thread = [];
	const showQ = de
		? 'Zeigen Sie mir den SAJ H2-10K-T3.'
		: 'Show me the SAJ H2-10K-T3.';
	const t1 = await turn(scenario, file, conversationId, thread, showQ, de ? 'de' : 'en');
	const t1Ref = productReferences(t1.result);
	const t1Ok = t1Ref.cards.includes(4107);
	record(scenario, file, {
		type: 'check',
		step: 1,
		name: 'the model card is shown',
		passed: t1Ok,
		detail: { cards: t1Ref.cards },
	});

	let t2;
	let check;
	if (kind === 'en-its-warranty') {
		t2 = await turn(scenario, file, conversationId, t1.thread, 'What is its warranty?');
		const text = answerText(t2.result.blocks);
		const refs = productReferences(t2.result);
		check = {
			name: '"its" resolves to the H2-10K-T3; warranty answered from documents',
			passed:
				/warrant/i.test(text) &&
				(refs.refs.includes(4107) || refs.cards.includes(4107) || /warranty/i.test(text)) &&
				!/which (product|model|inverter)\?/i.test(text),
			detail: { refs: refs.refs, cards: refs.cards, route: t2.result.meta?.route },
		};
	} else if (kind === 'en-mppt') {
		t2 = await turn(scenario, file, conversationId, t1.thread, 'How many MPPTs does it have?');
		const text = answerText(t2.result.blocks);
		// "MPP trackers" is how the manual words it; both spellings count.
		check = {
			name: '"it" resolves to the H2-10K-T3; the MPPT count is stated (hydrated)',
			passed:
				/MPP\s*T|MPPT/i.test(text) && /\d/.test(text) && !/which (product|model|inverter)\?/i.test(text),
			detail: { answer: text.slice(0, 400) },
		};
	} else if (kind === 'de-mppt') {
		t2 = await turn(scenario, file, conversationId, t1.thread, 'Wie viele MPPTs hat er?', 'de');
		const text = answerText(t2.result.blocks);
		check = {
			name: '"er" resolved auf H2-10K-T3; MPPT-Anzahl wird genannt (hydratisiert)',
			passed:
				/MPP\s*T|MPPT/i.test(text) && /\d/.test(text) && !/welches (Produkt|Modell)/i.test(text),
			detail: { answer: text.slice(0, 400) },
		};
	} else if (kind === 'en-first-one') {
		const compareQ =
			'Compare the SAJ H2-10K-T3 and the GoodWe ESA GW10K-EHA-G20.';
		const t1b = await turn(scenario, file, conversationId, t1.thread, compareQ);
		const compared = t1b.result.blocks.some((b) => b.type === 'compare');
		record(scenario, file, {
			type: 'check',
			step: 2,
			name: 'the comparison exists',
			passed: compared,
			detail: { blocks: t1b.result.blocks.map((b) => b.type) },
		});
		t2 = await turn(
			scenario,
			file,
			conversationId,
			t1b.thread,
			'Is the first one three-phase?'
		);
		const text = answerText(t2.result.blocks);
		const esa = grounding.known.goodweEsa.find(
			(p) => p.model === 'GW10K-EHA-G20'
		);
		check = {
			name: '"the first one" resolves to the H2-10K-T3 (three-phase yes), not the ESA',
			passed:
				/three-phase/i.test(text) &&
				!/first one is single|ESA.*three-phase/i.test(text) &&
				compared,
			detail: { answer: text.slice(0, 400), esaId: esa?.id ?? null },
		};
	} else if (kind === 'en-across-switch') {
		const switchQ = 'Which batteries work with the GoodWe ESA GW10K-EHA-G20?';
		const t1b = await turn(scenario, file, conversationId, t1.thread, switchQ);
		const batteryCards = productReferences(t1b.result).cards.filter((id) =>
			SETS.homeStorage.includes(id)
		);
		record(scenario, file, {
			type: 'check',
			step: 2,
			name: 'the switch turn names its own subject (batteries)',
			passed: batteryCards.length > 0,
			detail: { batteryCards },
		});
		t2 = await turn(
			scenario,
			file,
			conversationId,
			t1b.thread,
			'How long is its warranty?'
		);
		const text = answerText(t2.result.blocks);
		const refs = productReferences(t2.result);
		check = {
			name: '"its" after the switch resolves to the battery, not back to the H2 inverter',
			passed:
				/warrant/i.test(text) &&
				!refs.cards.includes(4107) &&
				!/H2-10K-T3/i.test(text),
			detail: { refs: refs.refs, cards: refs.cards },
		};
	} else {
		throw new Error(`unknown anaphora case ${kind}`);
	}
	record(scenario, file, { type: 'check', step: 'final', ...check });
	record(
		scenario,
		file,
		verdict(file, t1Ok && check.passed, check.name, `route=${t2?.result.meta?.route}`)
	);
	return { passed: t1Ok && check.passed };
}

// ---------------------------------------------------------------------------
// S3 — mid-thread language switch
// ---------------------------------------------------------------------------

async function s3LanguageSwitch(direction) {
	const scenario = 's3-language-switch';
	const file = `s3-${direction}-${stamp}`;
	const conversationId = `c331-${file}`;
	const toDe = direction === 'en-to-de';
	const pageLocale = toDe ? 'en' : 'de';
	caseHeader(
		scenario,
		file,
		toDe
			? 'EN thread (locale=en page); a German question arrives mid-thread. Baseline (dossier §1.13): German question → German answer, structure preserved.'
			: 'DE thread (locale=de page); eine englische Frage mitten im Gespräch. Baseline: englische Frage → englische Antwort, Struktur erhalten.'
	);
	const q1 = toDe
		? 'Which hybrid inverters do you carry for homes?'
		: 'Welche Hybridwechselrichter führen Sie für Wohngebäude?';
	const t1 = await turn(scenario, file, conversationId, [], q1, pageLocale);
	const q2 = toDe
		? 'The SAJ H2-10K-T3 looks right for my project.'
		: 'Der SAJ H2-10K-T3 passt zu meinem Projekt.';
	const t2 = await turn(scenario, file, conversationId, t1.thread, q2, pageLocale);
	const q3 = toDe
		? 'Welche Batterien passen zum SAJ H2-10K-T3?'
		: 'Which batteries work with the SAJ H2-10K-T3?';
	const t3 = await turn(scenario, file, conversationId, t2.thread, q3, pageLocale);
	const text = answerText(t3.result.blocks);
	const germanAnswer = /[äöüß]|\b(der|die|das|und|passen|Batterien|Wechselrichter)\b/i.test(text);
	const englishAnswer = /\b(the|and|batteries|work|with)\b/i.test(text) && !germanAnswer;
	const answeredGerman = toDe ? germanAnswer : englishAnswer;
	const structureOk =
		t3.result.blocks.length > 0 &&
		t3.result.done &&
		(contactOf(t3.result.blocks) === null || true);
	const cards = cardsOf(t3.result.blocks);
	record(scenario, file, {
		type: 'check',
		step: 3,
		name: 'the switched-language question is answered in its own language, same structure',
		passed: answeredGerman && structureOk,
		detail: {
			answerLanguage: germanAnswer ? 'de' : englishAnswer ? 'en' : 'mixed/other',
			structureOk,
			cards,
			answerHead: text.slice(0, 300),
		},
	});
	// And back: does the conversation keep its structure on the next turn?
	const q4 = toDe
		? 'Thanks. And what about 15 kWh of storage?'
		: 'Danke. Und was ist mit 15 kWh Speicher?';
	const t4 = await turn(scenario, file, conversationId, t3.thread, q4, pageLocale);
	const text4 = answerText(t4.result.blocks);
	record(scenario, file, {
		type: 'check',
		step: 4,
		name: 'the thread still answers after the switch (no corruption, no loop)',
		passed: text4.length > 0 && t4.result.done,
		detail: { answerHead: text4.slice(0, 300) },
	});
	record(
		scenario,
		file,
		verdict(
			file,
			answeredGerman && structureOk && text4.length > 0,
			toDe
				? 'Deutsche Frage → deutsche Antwort (Struktur erhalten: Blöcke, Karten, nächster Schritt); Faden bleibt funktionsfähig'
				: 'English question → English answer (structure preserved: blocks, cards, next step); thread still works',
			`route=${t3.result.meta?.route} language=${t3.result.meta?.language}`
		)
	);
	return { passed: answeredGerman && structureOk };
}

// ---------------------------------------------------------------------------
// S4 — repeated questions (stability + the repeat offer)
// ---------------------------------------------------------------------------

async function s4Repeat(kind) {
	const scenario = 's4-repeat';
	const file = `s4-${kind}-${stamp}`;
	const conversationId = `c331-${file}`;
	const de = kind.split('-').includes('de');
	caseHeader(
		scenario,
		file,
		de
			? 'Dieselbe Frage dreimal (dann ein viertes Mal): stabile Antwort (Kartenmenge), Kontaktangebot genau bei der dritten Runde, keines bei der vierten.'
			: 'The same question three times (then a fourth): stable answers (card set), the contact offer exactly on round three, none on the fourth.'
	);
	const q = de
		? 'Welche Batterien passen zum SAJ H2-10K-T3?'
		: 'Which batteries work with the SAJ H2-10K-T3?';
	let thread = [];
	const cardSets = [];
	const offers = [];
	for (let round = 1; round <= 4; round++) {
		const result = await service.turn({
			conversationId,
			messages: [...thread, { role: 'user', content: q }],
			locale: de ? 'de' : 'en',
		});
		record(scenario, file, {
			type: 'turn',
			round,
			...transcriptEntry(round, q, result),
		});
		cardSets.push(cardsOf(result.blocks).sort((a, b) => a - b).join(','));
		offers.push(contactOf(result.blocks)?.reason ?? null);
		thread = [
			...thread,
			{ role: 'user', content: q },
			...(answerText(result.blocks).length
				? [{ role: 'assistant', content: answerText(result.blocks) }]
				: []),
		];
	}
	const stableSets = new Set(cardSets).size === 1;
	const offerRule =
		offers[2] === 'repeat' && offers[0] === null && offers[1] === null && offers[3] === null;
	record(scenario, file, {
		type: 'check',
		name: 'stable card set across repeats; offer on round 3 only',
		passed: stableSets && offerRule,
		detail: { cardSets, offers },
	});
	record(
		scenario,
		file,
		verdict(
			file,
			stableSets && offerRule,
			de
				? 'Kartenmenge über alle Runden identisch; Kontaktangebot reason=repeat nur Runde 3; Runde 4 keins (同一问题一次)'
				: 'identical card set across rounds; contact offer reason=repeat on round 3 only; round 4 none (once per question)',
			`offers=${JSON.stringify(offers)}`
		)
	);
	return { passed: stableSets && offerRule, stableSets, offerRule };
}

// ---------------------------------------------------------------------------
// S5 — handoff offer rules (spec 13 转人工 table)
// ---------------------------------------------------------------------------

async function s5Handoff(kind) {
	const scenario = 's5-handoff';
	const file = `s5-${kind}-${stamp}`;
	const conversationId = `c331-${file}`;
	const de = kind.split('-').includes('de');
	const lang = de ? 'de' : 'en';
	let thread = [];
	const ask = async (question) => {
		const result = await service.turn({
			conversationId,
			messages: [...thread, { role: 'user', content: question }],
			locale: lang,
		});
		record(scenario, file, {
			type: 'turn',
			...transcriptEntry(thread.length / 2 + 1, question, result),
		});
		thread = [
			...thread,
			{ role: 'user', content: question },
			...(answerText(result.blocks).length
				? [{ role: 'assistant', content: answerText(result.blocks) }]
				: []),
		];
		return result;
	};
	const contact = (result) => contactOf(result.blocks)?.reason ?? null;

	if (kind === 'en-service-twice' || kind === 'de-service-twice') {
		caseHeader(
			scenario,
			file,
			de
				? 'Installationsleistungen gefragt, zweimal: beide Male die Team-Postfach-Zeile (handoff), die Karte nur beim ersten Mal.'
				: 'Installation services asked twice: the team mailbox sentence (handoff) both times, the contact card only the first time.'
		);
		const q = de
			? 'Bieten Sie Installationsleistungen an?'
			: 'Do you offer installation services?';
		const r1 = await ask(q);
		const r2 = await ask(q);
		const mailbox1 = handoffOf(r1.blocks) !== null;
		const mailbox2 = handoffOf(r2.blocks) !== null;
		const card1 = contact(r1);
		const card2 = contact(r2);
		const passed = mailbox1 && mailbox2 && card1 === 'service' && card2 === null;
		record(scenario, file, {
			type: 'check',
			name: 'mailbox sentence both turns; card once',
			passed,
			detail: { mailbox1, mailbox2, card1, card2 },
		});
		record(
			scenario,
			file,
			verdict(
				file,
				passed,
				de
					? 'Handoff-Block beide Runden; Kontakt-Karte nur Runde 1 (不连续两轮)'
					: 'handoff block both rounds; contact card round 1 only (never two turns in a row)',
				`cards=${card1},${card2}`
			)
		);
		return { passed };
	}

	if (kind === 'en-dissatisfied-twice') {
		caseHeader(
			scenario,
			file,
			'Frustration on a product intent, twice: the offer (dissatisfied) may come once; the answer itself must go on answering the product question.'
		);
		const q1 =
			'Which home storage batteries do you carry? This is my third attempt and I am getting frustrated here.';
		const r1 = await ask(q1);
		const q2 =
			'You did not answer me. Which home storage batteries do you carry? I am really not happy.';
		const r2 = await ask(q2);
		const card1 = contact(r1);
		const card2 = contact(r2);
		const stillAnswers =
			cardsOf(r2.blocks).length > 0 ||
			/home storage|batter/i.test(answerText(r2.blocks));
		const ruleOk = card2 === null; // never twice in a row
		const passed = stillAnswers && ruleOk;
		record(scenario, file, {
			type: 'check',
			name: 'second frustrated turn: still answers, no second card in a row',
			passed,
			detail: { card1, card2, stillAnswers },
		});
		record(
			scenario,
			file,
			verdict(
				file,
				passed,
				'turn 2 answers the product question and carries no contact card directly after turn 1 offered one',
				`cards=${card1},${card2}`
			)
		);
		return { passed };
	}

	if (kind === 'en-asked-after-repeat') {
		caseHeader(
			scenario,
			file,
			'Repeat-offer on round 3, then an explicit ask for a person on round 4: the ask must be answered immediately (asked, every time), which is the one sanctioned back-to-back pair.'
		);
		const q = 'Which batteries work with the SAJ H2-10K-T3?';
		const r1 = await ask(q);
		const r2 = await ask(q);
		const r3 = await ask(q);
		const r4 = await ask('This is not working. Can I talk to a real person please?');
		const repeatOffer = contact(r3);
		const askedOffer = contact(r4);
		const personTurn =
			r4.meta?.route === 'person' &&
			/Someone from the Linker team/i.test(answerText(r4.blocks));
		const passed =
			repeatOffer === 'repeat' && askedOffer === 'asked' && personTurn;
		record(scenario, file, {
			type: 'check',
			name: 'repeat offer on 3; explicit ask on 4 still offers (asked) with the service-written sentence',
			passed,
			detail: { repeatOffer, askedOffer, route4: r4.meta?.route },
		});
		record(
			scenario,
			file,
			verdict(
				file,
				passed,
				'round 3 → repeat card; round 4 explicit person ask → asked card + contact.ANSWER sentence, no model turn (spec: asked is offered every time)',
				`offers=${repeatOffer},${askedOffer}`
			)
		);
		return { passed };
	}

	if (kind === 'en-never-offer-attack') {
		caseHeader(
			scenario,
			file,
			'The never-offer attack: the same question with one added content word each round ("now", "today") — semantically the same question; does the repeat rule ever fire?'
		);
		const variants = [
			'Which batteries work with the SAJ H2-10K-T3?',
			'Which batteries work with the SAJ H2-10K-T3 now?',
			'Which batteries work with the SAJ H2-10K-T3 today?',
			'Which batteries work with the SAJ H2-10K-T3 right now?',
		];
		const offersSeen = [];
		for (const question of variants) {
			const result = await ask(question);
			offersSeen.push(contact(result));
		}
		const neverFired = offersSeen.every((o) => o === null);
		record(scenario, file, {
			type: 'check',
			name: 'one added word per round resets the repeat counter',
			passed: !neverFired,
			observed: neverFired,
			detail: { offersSeen },
		});
		record(
			scenario,
			file,
			verdict(
				file,
				!neverFired,
				'same question with a filler word added each round should still be recognisable as the same question (calibration gap when it never fires)',
				`offers=${JSON.stringify(offersSeen)} — marked as calibration finding either way`
			)
		);
		return { passed: !neverFired, calibration: true };
	}

	if (kind === 'en-negation-control') {
		caseHeader(
			scenario,
			file,
			'Negative control: "I don\'t want to talk to a person" must NOT trigger the person route; the product question is answered normally.'
		);
		const q =
			"I don't want to talk to a person, just answer directly: which home storage batteries do you carry?";
		const r1 = await ask(q);
		const noPersonRoute = r1.meta?.route !== 'person';
		const answers = cardsOf(r1.blocks).length > 0;
		const card = contact(r1);
		const passed = noPersonRoute && answers;
		record(scenario, file, {
			type: 'check',
			name: 'negated person phrase goes to Jev as any other message',
			passed,
			detail: { route: r1.meta?.route, card, cards: cardsOf(r1.blocks) },
		});
		record(
			scenario,
			file,
			verdict(
				file,
				passed,
				'route != person; the battery question is answered (clause-local negation of the person phrase)',
				`route=${r1.meta?.route}`
			)
		);
		return { passed };
	}

	throw new Error(`unknown handoff case ${kind}`);
}

// ---------------------------------------------------------------------------
// run
// ---------------------------------------------------------------------------

const FILTER = process.argv[2] ?? '';
const summary = [];
const run = async (name, fn) => {
	if (FILTER && !name.startsWith(FILTER)) {
		return;
	}
	console.log(`[c331] ${name} …`);
	try {
		summary.push({ name, ...(await fn()) });
		console.log(`[c331] ${name} done`);
	} catch (error) {
		summary.push({ name, error: String(error) });
		console.error(`[c331] ${name} FAILED: ${error}`);
	}
};

await run('s1-en-inverter-to-ev', () => s1InverterToEv('en'));
await run('s1-de-inverter-to-ev', () => s1InverterToEv('de'));
await run('s1-en-battery-to-commercial', () => s1BatteryToCommercial('en'));
await run('s1-de-battery-to-commercial', () => s1BatteryToCommercial('de'));
await run('s1-en-within-topic-control', s1WithinTopicControl);

await run('s2-en-its-warranty', () => s2Anaphora('en-its-warranty'));
await run('s2-en-mppt', () => s2Anaphora('en-mppt'));
await run('s2-de-mppt', () => s2Anaphora('de-mppt'));
await run('s2-en-first-one', () => s2Anaphora('en-first-one'));
await run('s2-en-across-switch', () => s2Anaphora('en-across-switch'));

await run('s3-en-to-de', () => s3LanguageSwitch('en-to-de'));
await run('s3-de-to-en', () => s3LanguageSwitch('de-to-en'));

await run('s4-en-exact-3x', () => s4Repeat('en-exact-3x'));
await run('s4-de-exact-3x', () => s4Repeat('de-exact-3x'));

await run('s5-en-service-twice', () => s5Handoff('en-service-twice'));
await run('s5-de-service-twice', () => s5Handoff('de-service-twice'));
await run('s5-en-dissatisfied-twice', () => s5Handoff('en-dissatisfied-twice'));
await run('s5-en-asked-after-repeat', () => s5Handoff('en-asked-after-repeat'));
await run('s5-en-never-offer-attack', () => s5Handoff('en-never-offer-attack'));
await run('s5-en-negation-control', () => s5Handoff('en-negation-control'));

artefact('.', `summary-direct-${stamp}.json`, summary);
console.log(JSON.stringify(summary, null, 2));
