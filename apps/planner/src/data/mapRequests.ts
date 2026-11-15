/** The retained OpenFreeMap style manifest uses this one delivery origin for
 * styles, tiles, glyphs and sprites. A style cannot widen its own network grant.
 * The site's own aerial mosaic is a second, explicitly declared grant: it is
 * passed in by the caller from the server's answer, never read from a style. */
const ORIGIN = "https://tiles.openfreemap.org";

function parseAerialOrigins(aerialOrigins: readonly string[]): Set<string> {
	return new Set(
		aerialOrigins
			.map((origin) => origin.trim().toLowerCase())
			.filter((origin) => /^https:\/\/[a-z0-9.-]+(:\d+)?$/.test(origin)),
	);
}

export class MapRequestScope {
	private active = true;
	private readonly external: boolean;
	private aerial: Set<string>;

	/**
	 * @param external whether the visitor allowed external map services
	 * @param aerialOrigins origins of the site's aerial mosaic, exactly as the
	 * server named them. An empty set leaves only the style provider reachable.
	 */
	constructor(external: boolean, aerialOrigins: readonly string[] = []) {
		this.external = external;
		this.aerial = parseAerialOrigins(aerialOrigins);
	}

	/** Replace the granted aerial mosaic origins when the resolved site changes. */
	setAerialOrigins(aerialOrigins: readonly string[]): void {
		if (!this.active) return;
		this.aerial = parseAerialOrigins(aerialOrigins);
	}

	/** MapLibre invokes this boundary for worker tiles as well as main-thread
	 * resources. It is a request policy, not a claim that a packet was sent. */
	readonly transform = (url: string) => {
		if (!this.active || !this.external)
			throw new Error("map_request_not_authorized");
		const target = new URL(url);
		if (target.username || target.password)
			throw new Error("map_resource_origin_not_authorized");
		if (target.origin !== ORIGIN && !this.aerial.has(target.origin))
			throw new Error("map_resource_origin_not_authorized");
		// The pinned library supports same-origin/include. Every granted origin
		// here is cross-origin to Linker, so same-origin sends no credentials.
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
