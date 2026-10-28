export * from "three/webgpu";
export const renderers = [];
export const behavior = { mode: "fail" };
export class WebGPURenderer {
	initialized = false;
	backend = {
		dispose: async () => {
			this.initialDisposed = true;
		},
	};
	constructor() {
		renderers.push(this);
	}
	async init() {
		this.backend = {
			isWebGLBackend: true,
			dispose: async () => {
				this.fallbackDisposed = true;
			},
		};
		if (behavior.mode === "ready") {
			this.initialized = true;
			return;
		}
		throw new TypeError(
			"Cannot read properties of null (reading 'getSupportedExtensions')",
		);
	}
	async dispose() {
		this.disposed = true;
	}
}
