/**
 * The R1–R14 expectations (docs/acceptance/protocol.md §5, wordings and
 * expected sets from docs/acceptance/genie-panel.md and
 * docs/research/2026-10-09/old-repo-live-catalogue-facts.md).
 *
 * The sets are the protocol's source of truth, not a reading of the
 * catalogue under test: a row fails when the answer leaves its set, and the
 * suite never derives the set from the instance it is judging. R1's German
 * wording is the protocol's R2.
 */

/** The 28 home/three-phase hybrid inverter ids (genie-panel §记号 HOME-3φ). */
export const HOME_THREE_PHASE = new Set([
	6512, 6514, 3555, 3556, 4107, 1182, 2199, 6513, 3574, 1183, 1186, 3575,
	3583, 1184, 1187, 3576, 3584, 4108, 1185, 3585, 2063, 6515, 2064, 6516,
	6517, 6518, 2198, 4109,
]);

/** The six ETR commercial inverters; they never enter a residential answer. */
export const ETR = new Set([6507, 6508, 6509, 6510, 6511, 3595]);

/** The six GoodWe ESA battery modules (no pa_phase; unknown keeps them in). */
export const ESA = new Set([6519, 6521, 3611, 6520, 6522, 3612]);

/** The batteries with a documented pairing for H2-10K-T3 (4107) — R5's set. */
export const PAIRED_WITH_H2_10K = new Set([
	1832, 2067, 2068, 2069, 2070, 2090, 2092,
]);

/** The batteries released for the GW10K-ET retrofit — R10's set. */
export const PAIRED_WITH_GW10K_ET = new Set([
	3611, 3612, 6519, 6520, 6521, 6522,
]);

/** The H2-10K-T3, the product page R5 and R13 are asked from. */
export const H2_10K_T3 = 4107;

/** A commercial ETR unit: the wrong pick every swap offers. */
export const WRONG_PICK = 6507;

/** Words an answer may never carry: Incoterms and delivery terms. */
export const FORBIDDEN_TERMS = [
	'incoterm',
	'dap ',
	'fob',
	'exw',
	'cif',
	'lieferzeit',
	'delivery time',
	'lead time',
	'liefertermin',
	'working days',
	'werktage',
	'business days',
];

/** The team mailbox every out-of-scope turn points at. */
export const TEAM_MAIL = 'sales@de-linker.com';

export type Locale = 'en' | 'de';

export interface Row {
	/** R-number of docs/acceptance/protocol.md §5. */
	id: string;
	/** The route the row is asked from. */
	entry: 'category' | 'product' | 'draft' | 'account';
	/** The product page the row is asked from, when the entry is one. */
	productId?: number;
	/** The draft the row is asked about, when the entry is one. */
	draftIds?: number[];
	question: Record<Locale, string>;
	/** Every card id must be in here (the row's qualified set). */
	allowed: Set<number>;
	/** No card id may be in here. */
	forbidden: Set<number>;
	/**
	 * When set, the judge also gets the wrong-pick variant: one offered card
	 * that is in `allowed` is replaced by this id, and the real answer must
	 * win `better_pick`.
	 */
	swapTo?: number;
	/** The ability call the turn must make (from the turn log's tool_calls). */
	expectedCall: string;
	/**
	 * The answer must name these, whatever else it says: the model the
	 * customer asked about has to be answered about, not silently swapped.
	 */
	mustMention?: string[];
	/** The row's own pass criteria, in the protocol's words. */
	notes: string;
}

const NOTHING = new Set<number>();

/** The rows; every one is asked in both languages. */
export const ROWS: Row[] = [
	{
		id: 'R1',
		entry: 'category',
		question: {
			en: 'I need a three-phase hybrid inverter for a home with 10 kWp PV and a future battery.',
			de: 'Ich brauche einen dreiphasigen Hybridwechselrichter für ein Wohngebäude mit 10 kWp PV und späterer Batterie.',
		},
		allowed: HOME_THREE_PHASE,
		forbidden: new Set([...ETR, ...ESA]),
		swapTo: WRONG_PICK,
		expectedCall: 'linker/search-products',
		notes: 'qualified ⊆ the 28; no ETR/ESA; cards ⊆ the body refs; one ask',
	},
	{
		id: 'R3',
		entry: 'category',
		question: {
			en: 'We have 12 kWp on a three-phase home — is the HS3-5K enough for that?',
			de: 'Wir haben 12 kWp auf drei Phasen im Wohnhaus — reicht der HS3-5K dafür?',
		},
		allowed: HOME_THREE_PHASE,
		forbidden: new Set([...ETR, ...ESA]),
		swapTo: WRONG_PICK,
		expectedCall: 'linker/search-products',
		mustMention: ['HS3-5K'],
		// Protocol R3: "HS3-5K 不推荐，说明 PV 上限 10 kWp" — the answer has to
		// decline the model the customer asked about. The card it asked about
		// may stay on screen (the panel's own rerun offered 2198 among the
		// alternatives and passed on the wording); what may not happen is a
		// turn that never addresses it, which the mention and the cascade's
		// grounded/better_pick verdicts together catch.
		notes: 'the HS3-5K is addressed and declined (PV cap 10 kWp)',
	},
	{
		id: 'R4',
		entry: 'category',
		question: {
			en: 'I need a hybrid inverter for my home.',
			de: 'Ich brauche einen Hybridwechselrichter für mein Wohngebäude.',
		},
		allowed: HOME_THREE_PHASE,
		forbidden: new Set([...ETR, ...ESA]),
		expectedCall: 'linker/search-products',
		notes: 'exactly one ask, on phase or kWp',
	},
	{
		id: 'R5',
		entry: 'product',
		productId: H2_10K_T3,
		question: {
			en: 'Which batteries have documented pairing with this model?',
			de: 'Welche Batterien haben ein dokumentiertes Pairing mit diesem Modell?',
		},
		allowed: new Set([H2_10K_T3, ...PAIRED_WITH_H2_10K]),
		forbidden: NOTHING,
		swapTo: WRONG_PICK,
		expectedCall: 'linker/search-products',
		notes: 'only documented pairings, with their documents',
	},
	{
		id: 'R6',
		entry: 'draft',
		// The released pair the draft holds: GW10K-ET plus an ESA module. A
		// draft page without its ids gives the model nothing to check.
		draftIds: [3556, 3611],
		question: {
			en: 'Can the items in my solution draft work together?',
			de: 'Passen die Positionen in meinem Lösungsentwurf zusammen?',
		},
		allowed: new Set([...HOME_THREE_PHASE, ...PAIRED_WITH_GW10K_ET]),
		forbidden: new Set([...ETR]),
		expectedCall: 'linker/check-compatibility',
		notes: 'reads the draft and judges each pair',
	},
	{
		id: 'R7',
		entry: 'account',
		question: {
			en: 'Where does my Proforma stand?',
			de: 'Wo steht meine Proforma?',
		},
		allowed: new Set([...HOME_THREE_PHASE, ...PAIRED_WITH_GW10K_ET]),
		forbidden: NOTHING,
		expectedCall: 'linker/inquiry-status',
		notes: 'signed in: the inquiry stage; signed out: a login request and no inquiry data',
	},
	{
		id: 'R8',
		entry: 'category',
		question: {
			en: 'Do you do installations?',
			de: 'Bieten Sie Installationen an?',
		},
		allowed: NOTHING,
		forbidden: NOTHING,
		expectedCall: 'linker/handoff-team',
		notes: 'only the team mailbox sentence, no cards',
	},
	{
		id: 'R9',
		entry: 'category',
		question: {
			en: 'What does the H2-10K-T3 cost, and how many do you have in stock?',
			de: 'Was kostet der H2-10K-T3, und wie viele haben Sie auf Lager?',
		},
		allowed: new Set([H2_10K_T3]),
		forbidden: new Set([...ETR]),
		expectedCall: 'linker/handoff-team',
		notes: 'no Incoterms, no quantities, no dates; the price stays gated for a guest',
	},
	{
		id: 'R10',
		entry: 'category',
		question: {
			en: 'I already have a GoodWe GW10K-ET and want to add a battery.',
			de: 'Ich habe bereits einen GoodWe GW10K-ET und möchte eine Batterie ergänzen.',
		},
		allowed: new Set([...PAIRED_WITH_GW10K_ET, 3556]),
		forbidden: new Set([...ETR]),
		swapTo: WRONG_PICK,
		expectedCall: 'linker/search-products',
		notes: 'only batteries with a release document for the ET, with the file',
	},
	{
		id: 'R11',
		entry: 'category',
		question: {
			en: 'I need a 48 V battery for a single-phase home.',
			de: 'Ich brauche eine 48-V-Batterie für ein Einphasen-Haus.',
		},
		allowed: new Set([...ESA, ...PAIRED_WITH_GW10K_ET]),
		forbidden: new Set([...ETR]),
		expectedCall: 'linker/search-products',
		notes: 'no high-voltage model presented as 48 V; at most one ask',
	},
	{
		id: 'R12',
		entry: 'category',
		question: {
			en: 'I need a three-phase hybrid with backup for a home.',
			de: 'Ich brauche einen dreiphasigen Hybrid mit Notstrom für ein Wohnhaus.',
		},
		allowed: new Set([...HOME_THREE_PHASE]),
		forbidden: new Set([...ETR, ...ESA]),
		expectedCall: 'linker/search-products',
		notes: 'only backup-capable models, with the condition stated',
	},
];

/** R14: the disclosure on open, then one out-of-scope question. */
export const R14 = {
	id: 'R14',
	entry: 'category' as const,
	question: { en: 'Lieferzeit?', de: 'Lieferzeit?' },
	expectedCall: 'linker/handoff-team',
	notes: 'the disclosure sentence appears once; the answer is only the mailbox sentence',
};
