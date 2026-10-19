/**
 * The Genie service's SSE text, one parser for every #331 driver.
 *
 * The shape matches tests/e2e/lib/genie.ts and the shell's parseStream
 * (plugins/linker-tools/src/genie/api/turn.ts): one `meta` event, one
 * `block` event per block, then `done`.
 */

/** The SSE text -> { meta, blocks, events, done }. */
export function parseStream(stream) {
	let meta = null;
	const blocks = [];
	const events = [];
	for (const event of String(stream ?? '').split('\n\n')) {
		const name = /^event: (.+)$/m.exec(event)?.[1];
		const data = /^data: (.+)$/m.exec(event)?.[1];
		if (!name || !data) {
			continue;
		}
		let payload;
		try {
			payload = JSON.parse(data);
		} catch {
			continue;
		}
		events.push({ event: name, data: payload });
		if (name === 'meta') {
			meta = payload;
		} else if (name === 'block') {
			blocks.push(payload);
		}
	}
	return {
		meta,
		blocks,
		events,
		done: events.some((item) => item.event === 'done'),
	};
}

/** The text the customer reads (text blocks joined), per assistantMessage(). */
export function answerText(blocks) {
	return (blocks ?? [])
		.filter((block) => block.type === 'text')
		.map((block) => block.text)
		.join('\n');
}

export function cardsOf(blocks) {
	return (blocks ?? [])
		.filter((block) => block.type === 'cards')
		.flatMap((block) => block.product_ids ?? []);
}

export function contactOf(blocks) {
	return (blocks ?? []).find((block) => block.type === 'contact') ?? null;
}

export function handoffOf(blocks) {
	return (blocks ?? []).find((block) => block.type === 'handoff') ?? null;
}

/** Block types in arrival order, repeats kept. */
export function blockTypes(blocks) {
	return (blocks ?? []).map((block) => block.type);
}
