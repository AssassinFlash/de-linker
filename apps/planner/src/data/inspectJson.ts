import { ApiError } from "./protocol.ts";

/** Check structure before a recursive validator/stringifier sees local input. */
export function inspectJson(value: unknown, maxDepth: number): void {
	if (!Number.isSafeInteger(maxDepth) || maxDepth < 1)
		throw new Error("invalid_json_policy");
	const active = new WeakSet<object>();
	type Frame = { container: object; children: IterableIterator<unknown> };
	const frames: Frame[] = [];
	let current = value;
	for (;;) {
		if (current !== null && typeof current === "object") {
			if (active.has(current)) throw new ApiError(422, "cyclic_json");
			if (frames.length + 1 > maxDepth) throw new ApiError(422, "input_depth");
			if (
				![Object.prototype, Array.prototype, null].includes(
					Object.getPrototypeOf(current),
				)
			)
				throw new ApiError(422, "invalid_json_object");
			const encoder = Object.getOwnPropertyDescriptor(current, "toJSON");
			if (
				encoder &&
				(!("value" in encoder) || typeof encoder.value === "function")
			)
				throw new ApiError(422, "invalid_json_encoder");
			active.add(current);
			// Generators avoid pushing every array element/field at once.
			const children = Array.isArray(current)
				? elements(current)
				: fields(current);
			frames.push({ container: current, children });
		} else if (
			!["string", "boolean", "number"].includes(typeof current) &&
			current !== null
		) {
			throw new ApiError(422, "invalid_json_value");
		} else if (
			typeof current === "number" &&
			(!Number.isFinite(current) || Math.abs(current) > Number.MAX_SAFE_INTEGER)
		) {
			throw new ApiError(422, "invalid_json_number");
		}
		let found = false;
		while (frames.length) {
			const frame = frames.at(-1);
			if (!frame) break;
			const next = frame.children.next();
			if (!next.done) {
				current = next.value;
				found = true;
				break;
			}
			active.delete(frame.container);
			frames.pop();
		}
		if (!found) return;
	}
}

function* elements(value: readonly unknown[]): IterableIterator<unknown> {
	for (let index = 0; index < value.length; index++) {
		const field = Object.getOwnPropertyDescriptor(value, index);
		if (!field || !("value" in field))
			throw new ApiError(422, "invalid_json_accessor");
		yield field.value;
	}
}

function* fields(value: object): IterableIterator<unknown> {
	for (const key of Object.keys(value)) {
		const field = Object.getOwnPropertyDescriptor(value, key);
		if (!field || !("value" in field))
			throw new ApiError(422, "invalid_json_accessor");
		yield field.value;
	}
}
