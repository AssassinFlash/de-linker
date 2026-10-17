/**
 * What the preview card remembers, in the visitor's own browser: whether it
 * appeared or Genie was opened during this visit (sessionStorage, which ends
 * with the browser session), and until when a closed card stays away
 * (localStorage). Nothing leaves the browser.
 *
 * Every access is guarded: a browser that blocks site storage throws on the
 * getter itself, not only on getItem.
 */

/** The keys, one per fact. */
export const KEYS = {
	shown: 'linker-genie-peek-shown',
	opened: 'linker-genie-peek-opened',
	dismissedUntil: 'linker-genie-peek-dismissed-until',
} as const;

type Area = 'localStorage' | 'sessionStorage';

/**
 * The browser storage the card reads and writes.
 */
export class Memory {
	/**
	 * @param win The window whose storage is used.
	 */
	constructor( private readonly win: Window ) {}

	/**
	 * Whether the card has appeared during this visit; unreadable counts as yes.
	 */
	shown(): boolean {
		return this.read( 'sessionStorage', KEYS.shown ) !== '';
	}

	/**
	 * Whether the visitor opened Genie during this visit; unreadable counts as yes.
	 */
	opened(): boolean {
		return this.read( 'sessionStorage', KEYS.opened ) !== '';
	}

	/**
	 * Until when a closed card stays away; 0 when never closed, null when the
	 * storage cannot be read.
	 */
	dismissedUntil(): number | null {
		const value = this.read( 'localStorage', KEYS.dismissedUntil );
		if ( value === null ) {
			return null;
		}
		const until = Number( value );
		return Number.isFinite( until ) ? until : 0;
	}

	/** Marks the card as shown for this visit. */
	markShown(): void {
		this.write( 'sessionStorage', KEYS.shown, '1' );
	}

	/** Marks Genie as opened during this visit. */
	markOpened(): void {
		this.write( 'sessionStorage', KEYS.opened, '1' );
	}

	/**
	 * Keeps the card away until the given time.
	 *
	 * @param until ms since the epoch.
	 */
	dismiss( until: number ): void {
		this.write( 'localStorage', KEYS.dismissedUntil, String( until ) );
	}

	/**
	 * The stored value, '' when absent, null when the storage cannot be read.
	 *
	 * @param area The storage area.
	 * @param key  The key.
	 */
	private read( area: Area, key: string ): string | null {
		try {
			return this.win[ area ].getItem( key ) ?? '';
		} catch {
			return null;
		}
	}

	/**
	 * Stores a value; a storage that refuses it is left as it is.
	 *
	 * @param area  The storage area.
	 * @param key   The key.
	 * @param value The value.
	 */
	private write( area: Area, key: string, value: string ): void {
		try {
			this.win[ area ].setItem( key, value );
		} catch {
			// Unwritable storage reads back as unreadable or absent; the
			// gate already treats that as "do not show".
		}
	}
}
