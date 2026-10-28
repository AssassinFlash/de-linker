/** A wedged GPU process never settles `WebGPURenderer.init`, so an unbounded
 * wait leaves the surface permanently claiming progress with no way out. Real
 * initialisation on the reference machine settled in 380–410 ms over six
 * repeated mounts (WebGPU, Apple M3 Pro); fifteen seconds is far outside that
 * spread and still short enough that a stuck device becomes a usable failure. */
export const SCENE_INIT_DEADLINE_MS = 15_000;

/** Startup did not settle inside the deadline; the viewport reports the same
 * failure it reports for a rejected initialisation. */
export class SceneInitTimeout extends Error {
	constructor() {
		super("scene_init_timeout");
		this.name = "SceneInitTimeout";
	}
}

/** Resolve `start` or reject with SceneInitTimeout, whichever happens first.
 * A result that arrives after the deadline belongs to an abandoned renderer, so
 * it is handed to `late` instead of being dropped with its GPU device intact. */
export function withInitDeadline<T>(
	start: Promise<T>,
	deadlineMs: number,
	late: (value: T) => void,
): Promise<T> {
	return new Promise<T>((resolve, reject) => {
		let settled = false;
		const timer = setTimeout(() => {
			if (settled) return;
			settled = true;
			reject(new SceneInitTimeout());
		}, deadlineMs);
		start.then(
			(value) => {
				if (settled) {
					try {
						late(value);
					} catch {
						/* Cleanup of an abandoned renderer cannot replace the verdict. */
					}
					return;
				}
				settled = true;
				clearTimeout(timer);
				resolve(value);
			},
			(error: unknown) => {
				if (settled) return;
				settled = true;
				clearTimeout(timer);
				reject(error);
			},
		);
	});
}
