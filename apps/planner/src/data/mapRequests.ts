/** The retained OpenFreeMap style manifest uses this one delivery origin for
 * styles, tiles, glyphs and sprites. A style cannot widen its own network grant. */
const ORIGIN = "https://tiles.openfreemap.org";

export class MapRequestScope {
	private active = true;
	private readonly external: boolean;
	constructor(external: boolean) {
		this.external = external;
	}

	/** MapLibre invokes this boundary for worker tiles as well as main-thread
	 * resources. It is a request policy, not a claim that a packet was sent. */
	readonly transform = (url: string) => {
		if (!this.active || !this.external)
			throw new Error("map_request_not_authorized");
		const target = new URL(url);
		if (target.origin !== ORIGIN || target.username || target.password)
			throw new Error("map_resource_origin_not_authorized");
		// The pinned library supports same-origin/include. This exact third-party
		// origin is cross-origin to Linker, so same-origin sends no credentials.
		return {
			url: target.href,
			credentials: "same-origin" as const,
			referrerPolicy: "no-referrer" as const,
		};
	};

	release(): void {
		this.active = false;
	}
}
