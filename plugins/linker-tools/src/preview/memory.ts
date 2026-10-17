/**
 * What the preview card remembers, in the visitor's own browser
 * (localStorage, shared by every tab of the site; nothing leaves the
 * browser):
 *
 * - the visit: when the visitor was last active, and whether the card has
 *   appeared or Genie was opened during it. A visit ends after
 *   VISIT_IDLE_MS without activity, so "once per visit" holds across tabs.
 * - until when a closed card stays away.
 *
 * Every access is guarded: a browser that blocks site storage throws on the
 * getter itself, not only on getItem. Unreadable storage answers "yes, shown"
 * and "closed", so the card stays away.
 */

/**
 * Inactivity that ends a visit: 30 minutes, Google Analytics 4's default
 * session timeout ("By default, a session ends (times out) after 30 minutes
 * of user inactivity", support.google.com/analytics/answer/12798876, read
 * 2026-10-18).
 */
export const VISIT_IDLE_MS = 30 * 60 * 1_000;

/**
 * Activity is written at most this often (scroll fires many times a
 * second); far below VISIT_IDLE_MS, so a visit never lapses between writes.
 */
export const TOUCH_EVERY_MS = 60 * 1_000;

/** The keys, one per record. */
export const KEYS = {
	visit: 'linker-genie-peek-visit',
	dismissedUntil: 'linker-genie-peek-dismissed-until',
} as const;

/** The visit record. */
export interface Visit {
	/** Last activity, ms since the epoch. */
	last: number;
	/** The card (or the mobile mark) appeared during this visit. */
	shown: boolean;
	/** Genie was opened during this visit. */
	opened: boolean;
}

/**
 * The browser storage the card reads and writes.
 */
export class Memory {
	/**
	 * @param win The window whose storage is used.
	 */
	constructor( private readonly win: Window ) {}

	/**
	 * The current visit, null when the storage cannot be read. A record
	 * older than VISIT_IDLE_MS, or none, is a fresh visit.
	 *
	 * @param now ms since the epoch.
	 */
	visit( now: number ): Visit | null {
		const raw = this.read( KEYS.visit );
		if ( raw === null ) {
			return null;
		}
		const fresh: Visit = { last: now, shown: false, opened: false };
		if ( raw === '' ) {
			return fresh;
		}
		try {
			const stored = JSON.parse( raw ) as Partial< Visit >;
			const last = Number( stored.last );
			if ( ! Number.isFinite( last ) || now - last > VISIT_IDLE_MS ) {
				return fresh;
			}
			return {
				last,
				shown: stored.shown === true,
				opened: stored.opened === true,
			};
		} catch {
			return fresh;
		}
	}

	/**
	 * Records activity now, starting a new visit when the last one lapsed.
	 * Writes at most once per TOUCH_EVERY_MS unless `force`.
	 *
	 * @param now   ms since the epoch.
	 * @param force Write even if the last write is recent.
	 */
	touch( now: number, force = false ): void {
		const visit = this.visit( now );
		if ( ! visit ) {
			return;
		}
		if (
			! force &&
			now - visit.last < TOUCH_EVERY_MS &&
			visit.last !== now
		) {
			return;
		}
		this.save( { ...visit, last: now } );
	}

	/**
	 * Whether the card has appeared during this visit; unreadable counts as yes.
	 *
	 * @param now ms since the epoch.
	 */
	shown( now: number ): boolean {
		return this.visit( now )?.shown ?? true;
	}

	/**
	 * Whether Genie was opened during this visit; unreadable counts as yes.
	 *
	 * @param now ms since the epoch.
	 */
	opened( now: number ): boolean {
		return this.visit( now )?.opened ?? true;
	}

	/**
	 * Marks the card as shown for this visit.
	 *
	 * @param now ms since the epoch.
	 */
	markShown( now: number ): void {
		const visit = this.visit( now );
		if ( visit ) {
			this.save( { ...visit, last: now, shown: true } );
		}
	}

	/**
	 * Marks Genie as opened during this visit.
	 *
	 * @param now ms since the epoch.
	 */
	markOpened( now: number ): void {
		const visit = this.visit( now );
		if ( visit ) {
			this.save( { ...visit, last: now, opened: true } );
		}
	}

	/**
	 * Until when a closed card stays away; 0 when never closed, null when the
	 * storage cannot be read.
	 */
	dismissedUntil(): number | null {
		const value = this.read( KEYS.dismissedUntil );
		if ( value === null ) {
			return null;
		}
		const until = Number( value );
		return Number.isFinite( until ) ? until : 0;
	}

	/**
	 * Keeps the card away until the given time.
	 *
	 * @param until ms since the epoch.
	 */
	dismiss( until: number ): void {
		this.write( KEYS.dismissedUntil, String( until ) );
	}

	/**
	 * Stores the visit record.
	 *
	 * @param visit The record.
	 */
	private save( visit: Visit ): void {
		this.write( KEYS.visit, JSON.stringify( visit ) );
	}

	/**
	 * The stored value, '' when absent, null when the storage cannot be read.
	 *
	 * @param key The key.
	 */
	private read( key: string ): string | null {
		try {
			return this.win.localStorage.getItem( key ) ?? '';
		} catch {
			return null;
		}
	}

	/**
	 * Stores a value; a storage that refuses it is left as it is.
	 *
	 * @param key   The key.
	 * @param value The value.
	 */
	private write( key: string, value: string ): void {
		try {
			this.win.localStorage.setItem( key, value );
		} catch {
			// Unwritable storage reads back as unreadable or absent; the
			// gate already treats that as "do not show".
		}
	}
}
