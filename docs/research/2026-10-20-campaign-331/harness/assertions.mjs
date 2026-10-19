/**
 * Checks the #331 answer-shape battery can fail.
 *
 * Next step: docs/specs/13-genie.md goal 6 and the #329 gate ("每条回答有下一步",
 * at least one clickable follow-up). The same reading as campaign #330's
 * triage (`docs/research/2026-10-20-campaign-330/harness/run_battery.py`,
 * `next_step`): an ask, a card, a compare, an action, a document, a parts
 * list, a handoff, a contact card, or a question mark in the text.
 *
 * The product id is never a literal. Callers pass the feed row
 * (`grounding.known.sajH2_10k_t3`), whose `id` is that snapshot's post.
 */

import { answerText, cardsOf } from './sse.mjs';

/** A clickable block, per the #330 triage list. */
export const CLICKABLE_TYPES = [
	'ask',
	'cards',
	'compare',
	'action',
	'document',
	'parts',
	'handoff',
	'contact',
];

/**
 * The switched pairing question (S3's twin): text plus product cards.
 * Source: the pairing example in `services/genie/prompts/en/system.md`
 * (a text block, a cards block, and the pairing documents).
 */
export const PAIRING_TYPES = ['text', 'cards'];

/**
 * The sizing follow-up ("what about 15 kWh"): text plus the configurator
 * action. Source: the Sizing paragraph of `prompts/en/system.md`
 * (`open_configurator`, no product cards).
 */
export const SIZING_TYPES = ['text', 'action'];

export function typeSet(blocks) {
	return [...new Set((blocks ?? []).map((block) => block.type))].sort();
}

export function cardSet(blocks) {
	return [...new Set(cardsOf(blocks))].sort((left, right) => left - right);
}

/** Every required type is present. Extra types (a document, an ask) may be. */
export function hasRequiredTypes(blocks, required) {
	const present = new Set(typeSet(blocks));
	return required.every((type) => present.has(type));
}

export function hasNextStep(blocks) {
	if ((blocks ?? []).some((block) => CLICKABLE_TYPES.includes(block.type))) {
		return true;
	}
	return answerText(blocks).includes('?');
}

/**
 * EN/DE twins: the same set of block types and the same set of card ids.
 * Document blocks may repeat; the set is what the gate compares
 * (#329 "EN/DE 同结构").
 */
export function structuresMatch(left, right) {
	const a = shapeOf(left);
	const b = shapeOf(right);
	return {
		typesEqual: JSON.stringify(a.types) === JSON.stringify(b.types),
		cardsEqual: JSON.stringify(a.cards) === JSON.stringify(b.cards),
		left: a,
		right: b,
	};
}

function shapeOf(value) {
	if (Array.isArray(value)) {
		return { types: typeSet(value), cards: cardSet(value) };
	}
	return {
		types: [...(value?.types ?? [])].sort(),
		cards: [...(value?.cards ?? [])].sort((left, right) => left - right),
	};
}

/**
 * The resolved product is named in the answer text (model or SKU) or shown
 * on a card. A word from the question ("warranty") is not that product.
 */
export function mentionsProduct(text, blocks, product) {
	if (!product || product.id === undefined || product.id === null) {
		return false;
	}
	const inText =
		(typeof product.model === 'string' &&
			product.model.length > 0 &&
			String(text ?? '').includes(product.model)) ||
		(typeof product.sku === 'string' &&
			product.sku.length > 0 &&
			String(text ?? '').includes(product.sku));
	return inText || cardsOf(blocks).includes(product.id);
}

export function mentionsAnyProduct(text, blocks, products) {
	return (products ?? []).some((product) => mentionsProduct(text, blocks, product));
}

/**
 * S3's switched turn. `done` is the SSE `done` event. A contact card on
 * the first asking of a pairing question is a failure, not a free pass.
 */
export function switchedStructureOk(blocks, done) {
	return (
		done === true &&
		hasRequiredTypes(blocks, PAIRING_TYPES) &&
		hasNextStep(blocks) &&
		blocks.every((block) => block.type !== 'contact')
	);
}

/** The sizing turn after the language switch. */
export function sizingStructureOk(blocks, done) {
	return done === true && hasRequiredTypes(blocks, SIZING_TYPES) && hasNextStep(blocks);
}
