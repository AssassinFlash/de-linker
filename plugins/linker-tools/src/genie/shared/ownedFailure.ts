/** One synchronous owner/attempt journal for every failed-turn producer. */
import {
	FAILURE_KEY,
	draftWith,
	parseFailure,
	recordOf,
	withHeldClaims,
	type FailureOwner,
	type FailureState,
	type FailureStore,
	type StoredFailure,
} from './failure';
import type { NativeScope } from './nativeScope';

const PREFIX = 'linker-genie-turn-failure:v2:';
interface Entry {
	revision: number;
	record: StoredFailure;
}
interface Bucket {
	v: 2;
	scope: string;
	active: string | null;
	order: string[];
	records: Record< string, Entry >;
}
export interface FailureCursor {
	owner: FailureOwner;
	revision: number;
	raw: string | null;
	/** The owner may retain a window-only copy when exact durable readback fails. */
	memory?: boolean;
	/** An actual displaced window copy, identified by its complete exact entry. */
	retained?: boolean;
}
export interface FailureCandidate {
	record: StoredFailure;
	cursor: FailureCursor;
}
export interface FailureWrite {
	state: FailureState;
	cursor: FailureCursor;
	durable: boolean;
	conflict: boolean;
}

interface RetainedEntry {
	entry: Entry;
	counterpart?: { revision: number; record: string };
}
interface RuntimeJournal {
	data: Map< string, string >;
	retained: Map< string, RetainedEntry[] >;
	selected: Map< string, string >;
	order: Map< string, string[] >;
	active: Map< string, string | null >;
	latest: Map< string, boolean >;
	consumed: Set< string >;
	counterparts: Map< string, { revision: number; record: string } >;
}
function runtime(): RuntimeJournal {
	const target = window as unknown as Record< string, unknown >;
	const key = '__linkerGenieFailureJournal';
	if ( ! target[ key ] ) {
		target[ key ] = {
			data: new Map(),
			retained: new Map(),
			selected: new Map(),
			order: new Map(),
			active: new Map(),
			latest: new Map(),
			consumed: new Set(),
			counterparts: new Map(),
		};
	}
	return target[ key ] as RuntimeJournal;
}
function memoryStore(): FailureStore {
	return {
		getItem: ( key ) => runtime().data.get( key ) ?? null,
		setItem: ( key, value ) => {
			runtime().data.set( key, value );
		},
		removeItem: ( key ) => {
			runtime().data.delete( key );
		},
	};
}
/**
 * Cache an exactly read or acknowledged durable entry, never an inferred absence.
 * @param cursor The exact durable entry and revision already verified by this window.
 */
function trustDurable( cursor: FailureCursor ): void {
	if ( cursor.memory || ! cursor.raw || ! cursor.revision ) {
		return;
	}
	if (
		bucketOf(
			runtime().data.get( failureBucketKey( cursor.owner.scope ) ) ??
				null,
			cursor.owner.scope
		).records[ cursor.owner.attempt ]
	) {
		return;
	}
	const entry = JSON.parse( cursor.raw ).records[ cursor.owner.attempt ] as
		Entry | undefined;
	if ( entry?.revision === cursor.revision ) {
		runtime().counterparts.set(
			cursor.owner.scope + ':' + cursor.owner.attempt,
			{ revision: entry.revision, record: JSON.stringify( entry ) }
		);
	}
}
function ownerKey( owner: FailureOwner ): string {
	return owner.scope + ':' + owner.attempt;
}
function cursorEntry( cursor: FailureCursor ): Entry | undefined {
	return bucketOf( cursor.raw, cursor.owner.scope ).records[
		cursor.owner.attempt
	];
}
function retainedCursor( owner: FailureOwner, entry: Entry ): FailureCursor {
	const bucket = empty( owner.scope );
	bucket.active = owner.attempt;
	bucket.order = [ owner.attempt ];
	bucket.records[ owner.attempt ] = entry;
	return {
		owner,
		revision: entry.revision,
		raw: JSON.stringify( bucket ),
		memory: true,
		retained: true,
	};
}
function remember( cursor: FailureCursor ): void {
	trustDurable( cursor );
	const shared = runtime();
	const { scope, attempt } = cursor.owner;
	if ( ! cursor.retained ) {
		shared.selected.delete( ownerKey( cursor.owner ) );
	}
	const order = shared.order.get( scope ) ?? [];
	if ( ! order.includes( attempt ) ) {
		order.push( attempt );
	}
	shared.order.set( scope, order );
	shared.active.set( scope, attempt );
	shared.latest.set( scope + ':' + attempt, !! cursor.memory );
}
export function failureBucketKey( scope: string ): string {
	return PREFIX + scope;
}
/**
 * Content-free hint only; it never authorizes reading a cached body.
 * @param store The underlying tab storage adapter.
 */
export function hasOwnedRecovery( store: FailureStore ): boolean {
	try {
		if ( store.keys?.().some( ( key ) => key.startsWith( PREFIX ) ) ) {
			return true;
		}
		const legacy = store.getItem( FAILURE_KEY );
		return !! (
			legacy && parseFailure( JSON.parse( legacy ) )?.entryScope
		);
	} catch {
		return false;
	}
}
function empty( scope: string ): Bucket {
	return { v: 2, scope, active: null, order: [], records: {} };
}
function bucketOf( raw: string | null, scope: string ): Bucket {
	if ( raw === null ) {
		return empty( scope );
	}
	const value = JSON.parse( raw ) as Partial< Bucket >;
	if (
		value.v !== 2 ||
		value.scope !== scope ||
		! Array.isArray( value.order ) ||
		! value.records ||
		typeof value.records !== 'object'
	) {
		throw new Error( 'failure-bucket' );
	}
	const records: Record< string, Entry > = {};
	for ( const attempt of value.order ) {
		const entry = value.records[ attempt ];
		const record = parseFailure( entry?.record );
		if (
			typeof attempt !== 'string' ||
			! attempt ||
			! record ||
			record.owner?.scope !== scope ||
			record.owner.attempt !== attempt ||
			! Number.isSafeInteger( entry.revision ) ||
			entry.revision < 1 ||
			Object.hasOwn( records, attempt )
		) {
			throw new Error( 'failure-bucket' );
		}
		Object.defineProperty( records, attempt, {
			value: { ...entry, record },
			enumerable: true,
			configurable: true,
		} );
	}
	if (
		Object.keys( value.records ).length !== value.order.length ||
		( value.active !== null &&
			( typeof value.active !== 'string' ||
				! Object.hasOwn( records, value.active ) ) ) ||
		( value.order.length > 0 && ! value.active )
	) {
		throw new Error( 'failure-bucket' );
	}
	return {
		v: 2,
		scope,
		active: value.active ?? null,
		order: [ ...value.order ],
		records,
	};
}

/** Binds only a freshly verified native scope. A storage key never authorizes a read. */
export class FailureJournal {
	constructor(
		private readonly store: FailureStore,
		readonly identity: NativeScope,
		private readonly memory = false
	) {}

	/**
	 * Immutable bytes acknowledged by this cursor, never the currently newer entry.
	 * @param cursor The mounted editor's accepted cursor.
	 */
	acknowledged( cursor: FailureCursor ): StoredFailure | null {
		try {
			const entry = cursorEntry( cursor );
			return cursor.owner.scope === this.identity.scope &&
				entry?.revision === cursor.revision
				? entry.record
				: null;
		} catch {
			return null;
		}
	}

	/**
	 * Retain only an actual displaced copy; identical content never creates history.
	 * @param state    Accepted editor bytes at a demonstrated conflict.
	 * @param expected Their original acknowledged copy.
	 */
	retain( state: FailureState, expected: FailureCursor ): FailureWrite {
		const record = state.draft ? recordOf( state ) : null;
		if (
			! record ||
			expected.owner.scope !== this.identity.scope ||
			! parseFailure( record ) ||
			record.owner?.scope !== this.identity.scope ||
			record.owner.attempt !== expected.owner.attempt
		) {
			return { state, cursor: expected, durable: false, conflict: true };
		}
		const key = ownerKey( expected.owner );
		const copies = runtime().retained.get( key ) ?? [];
		let copy = copies.find(
			( item ) =>
				JSON.stringify( item.entry.record ) === JSON.stringify( record )
		);
		if ( ! copy ) {
			const entry = cursorEntry( expected );
			let counterpart = runtime().counterparts.get( key );
			if ( ! expected.memory ) {
				counterpart = entry
					? {
							revision: expected.revision,
							record: JSON.stringify( entry ),
						}
					: undefined;
			}
			copy = {
				entry: {
					revision: expected.revision + 1,
					record: JSON.parse(
						JSON.stringify( record )
					) as StoredFailure,
				},
				counterpart,
			};
			copies.push( copy );
			runtime().retained.set( key, copies );
		}
		const cursor = retainedCursor( expected.owner, copy.entry );
		runtime().selected.set( key, JSON.stringify( copy.entry ) );
		remember( cursor );
		runtime().consumed.delete( key );
		return { state, cursor, durable: false, conflict: false };
	}

	/**
	 * Read all actual distinct copies in stable explicit Restore order.
	 * @param owner The verified original scope and attempt.
	 */
	private copies( owner: FailureOwner ): FailureCandidate[] {
		if ( owner.scope !== this.identity.scope ) {
			return [];
		}
		const key = ownerKey( owner );
		const copies: FailureCandidate[] = [];
		const memoryRaw = memoryStore().getItem(
			failureBucketKey( owner.scope )
		);
		const inMemory = bucketOf( memoryRaw, owner.scope ).records[
			owner.attempt
		];
		if ( inMemory ) {
			copies.push( {
				record: inMemory.record,
				cursor: {
					owner,
					revision: inMemory.revision,
					raw: memoryRaw,
					memory: true,
				},
			} );
		}
		for ( const copy of runtime().retained.get( key ) ?? [] ) {
			copies.push( {
				record: JSON.parse(
					JSON.stringify( copy.entry.record )
				) as StoredFailure,
				cursor: retainedCursor( owner, copy.entry ),
			} );
		}
		try {
			if ( this.identity.persistent ) {
				const raw = this.store.getItem(
					failureBucketKey( owner.scope )
				);
				const entry = bucketOf( raw, owner.scope ).records[
					owner.attempt
				];
				const baseline = runtime().counterparts.get( key );
				// A single fallback's unchanged durable ancestor is not a second draft.
				if (
					entry &&
					( ! inMemory ||
						copies.length > 1 ||
						baseline?.record !==
							JSON.stringify(
								JSON.parse( raw! ).records[ owner.attempt ]
							) )
				) {
					copies.push( {
						record: entry.record,
						cursor: {
							owner,
							revision: entry.revision,
							raw,
							memory: false,
						},
					} );
				}
			}
		} catch {
			/* Memory copies remain usable with an honest unsaved state. */
		}
		return copies.filter(
			( copy, index ) =>
				copies.findIndex(
					( other ) =>
						JSON.stringify( other.record ) ===
						JSON.stringify( copy.record )
				) === index
		);
	}

	private selectedCopy( owner: FailureOwner ): FailureCandidate | null {
		const selected = runtime().selected.get( ownerKey( owner ) );
		const copy = ( runtime().retained.get( ownerKey( owner ) ) ?? [] ).find(
			( item ) => JSON.stringify( item.entry ) === selected
		);
		return copy
			? {
					record: JSON.parse(
						JSON.stringify( copy.entry.record )
					) as StoredFailure,
					cursor: retainedCursor( owner, copy.entry ),
				}
			: null;
	}

	/**
	 * After an exact consumption, no attempt tombstone may hide a surviving real copy.
	 * @param owner The attempt whose selected exact copy was consumed.
	 */
	private remaining( owner: FailureOwner ): void {
		const next = this.copies( owner )[ 0 ];
		if ( next ) {
			runtime().consumed.delete( ownerKey( owner ) );
			this.select( next.cursor );
		}
	}

	/**
	 * v2 wins. Unknown v1 stays byte-identical; only scoped v1 can migrate.
	 * @param editingAttempt Prefer another retained attempt while this verified editor is already on screen.
	 */
	candidate( editingAttempt?: string ): FailureCandidate | null {
		const scope = this.identity.scope;
		let raw: string | null = null;
		let bucket = empty( scope );
		let readFailed = false;
		if ( this.memory || this.identity.persistent ) {
			try {
				raw = this.store.getItem( failureBucketKey( scope ) );
				bucket = bucketOf( raw, scope );
			} catch {
				readFailed = true;
			}
		}
		if ( this.memory ) {
			const attempt = bucket.active;
			if ( ! attempt ) {
				return null;
			}
			const entry = bucket.records[ attempt ];
			return {
				record: entry.record,
				cursor: {
					owner: entry.record.owner!,
					revision: entry.revision,
					raw,
					memory: true,
				},
			};
		}
		const shared = runtime();
		const memoryRaw = memoryStore().getItem( failureBucketKey( scope ) );
		const memory = bucketOf( memoryRaw, scope );
		const order = shared.order.get( scope ) ?? [];
		for ( const attempt of [ ...bucket.order, ...memory.order ] ) {
			if ( ! order.includes( attempt ) ) {
				order.push( attempt );
			}
		}
		shared.order.set( scope, order );
		if ( ! shared.active.has( scope ) ) {
			shared.active.set( scope, bucket.active ?? memory.active );
		}
		const available = ( attempt: string ) => {
			const retained = this.selectedCopy( { scope, attempt } );
			if ( retained ) {
				return attempt === editingAttempt
					? ( this.alternative( retained.cursor ) ?? retained )
					: retained;
			}
			if ( shared.consumed.has( scope + ':' + attempt ) ) {
				return null;
			}
			const inMemory =
				shared.latest.get( scope + ':' + attempt ) ??
				!! memory.records[ attempt ];
			const entry = inMemory
				? memory.records[ attempt ]
				: bucket.records[ attempt ];
			const selected = entry
				? {
						record: entry.record,
						cursor: {
							owner: entry.record.owner!,
							revision: entry.revision,
							raw: inMemory ? memoryRaw : raw,
							memory: inMemory,
						},
					}
				: null;
			return selected && attempt === editingAttempt
				? ( this.alternative( selected.cursor ) ?? selected )
				: selected;
		};
		const active = shared.active.get( scope );
		const selected =
			active && active !== editingAttempt ? available( active ) : null;
		const candidate =
			selected ??
			[ ...order ]
				.reverse()
				.filter( ( attempt ) => attempt !== editingAttempt )
				.map( available )
				.find( ( item ) => item !== null ) ??
			( active ? available( active ) : null );
		if ( candidate ) {
			trustDurable( candidate.cursor );
			return candidate;
		}
		if ( readFailed ) {
			throw new Error( 'failure-storage-read' );
		}
		if ( ! this.identity.persistent ) {
			return null;
		}

		const legacyRaw = this.store.getItem( FAILURE_KEY );
		if ( ! legacyRaw ) {
			return null;
		}
		let legacy: StoredFailure | null;
		try {
			legacy = parseFailure( JSON.parse( legacyRaw ) );
		} catch {
			return null;
		}
		if ( ! legacy?.entryId || legacy.entryScope !== scope ) {
			return null;
		}
		const owner = { scope, attempt: crypto.randomUUID() };
		const record = { ...legacy, owner };
		const cursor = { owner, revision: 0, raw };
		const result = this.save(
			{ phase: 'failed', draft: record, kind: legacy.kind ?? 'upstream' },
			cursor
		);
		if ( ! result.durable || ! result.state.draft ) {
			throw new Error( 'failure-migration-storage' );
		}
		if ( this.store.getItem( FAILURE_KEY ) === legacyRaw ) {
			this.store.removeItem( FAILURE_KEY );
		}
		return { record: recordOf( result.state ), cursor: result.cursor };
	}

	/**
	 * Synchronous checkpoint lookup for an accepted editor, including a non-active one.
	 * @param owner The immutable owner of the editor being explicitly emptied.
	 */
	editing( owner: FailureOwner ): FailureCandidate | null | undefined {
		if ( owner.scope !== this.identity.scope ) {
			return null;
		}
		const retained = this.selectedCopy( owner );
		if ( retained ) {
			return retained.record.editing ? retained : null;
		}
		const inMemory =
			runtime().latest.get( owner.scope + ':' + owner.attempt ) === true;
		if ( ! inMemory && ! this.identity.persistent ) {
			return null;
		}
		try {
			const raw = ( inMemory ? memoryStore() : this.store ).getItem(
				failureBucketKey( owner.scope )
			);
			const entry = bucketOf( raw, owner.scope ).records[ owner.attempt ];
			return entry?.record.editing
				? {
						record: entry.record,
						cursor: {
							owner,
							revision: entry.revision,
							raw,
							memory: inMemory,
						},
					}
				: null;
		} catch {
			return undefined;
		}
	}

	/**
	 * A new explicit send allocates a distinct attempt, preserving older records.
	 * @param state  The complete proposed machine state.
	 * @param editor The existing editing owner to promote without replacing older failed attempts.
	 */
	begin( state: FailureState, editor?: FailureOwner ): FailureWrite {
		const owner =
			editor?.scope === this.identity.scope
				? editor
				: {
						scope: this.identity.scope,
						attempt: crypto.randomUUID(),
					};
		const draft = state.draft ? { ...state.draft, owner } : null;
		if ( ! draft || ! parseFailure( recordOf( { ...state, draft } ) ) ) {
			return {
				state: { ...state, draft },
				cursor: { owner, revision: 0, raw: null },
				durable: false,
				conflict: true,
			};
		}
		const retained = this.selectedCopy( owner );
		if ( retained ) {
			return state.phase === 'editing' && ! retained.record.editing
				? {
						state,
						cursor: retained.cursor,
						durable: false,
						conflict: true,
					}
				: this.save( { ...state, draft }, retained.cursor );
		}
		if (
			! this.memory &&
			runtime().latest.get( owner.scope + ':' + owner.attempt ) === true
		) {
			const result = new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			).begin( { ...state, draft }, owner );
			return { ...result, durable: false };
		}
		if ( ! this.identity.persistent && ! this.memory ) {
			return this.keepMemory( { ...state, draft }, owner );
		}
		let raw: string | null;
		let revision = 0;
		try {
			raw = this.store.getItem( failureBucketKey( owner.scope ) );
			const bucket = bucketOf( raw, owner.scope );
			const existing = bucket.records[ owner.attempt ];
			if ( existing && ! existing.record.editing ) {
				// A late editing checkpoint cannot turn an already promoted send
				// into a second attempt. Explicit sends retain their allocation rule.
				if ( state.phase === 'editing' ) {
					return {
						state: { ...state, draft },
						cursor: {
							owner,
							revision: existing.revision,
							raw,
							memory: this.memory,
						},
						durable: false,
						conflict: true,
					};
				}
				return this.begin( state );
			}
			revision = existing?.revision ?? 0;
		} catch {
			return this.keepMemory( { ...state, draft }, owner );
		}
		return this.save(
			{ ...state, draft },
			{ owner, revision, raw, memory: this.memory }
		);
	}

	private keepMemory(
		state: FailureState,
		owner: FailureOwner,
		durable?: FailureCursor
	): FailureWrite {
		const previousCounterpart = runtime().counterparts.get(
			ownerKey( owner )
		);
		if ( durable?.revision && ! durable.memory ) {
			const entry = bucketOf( durable.raw, owner.scope ).records[
				owner.attempt
			];
			if ( entry ) {
				runtime().counterparts.set( owner.scope + ':' + owner.attempt, {
					revision: entry.revision,
					record: JSON.stringify(
						JSON.parse( durable.raw! ).records[ owner.attempt ]
					),
				} );
			}
		}
		const memory = memoryStore();
		const raw = memory.getItem( failureBucketKey( owner.scope ) );
		const bucket = bucketOf( raw, owner.scope );
		const existing = bucket.records[ owner.attempt ];
		if (
			existing &&
			durable &&
			! durable.memory &&
			JSON.stringify( existing.record ) !==
				JSON.stringify( recordOf( state ) )
		) {
			const key = ownerKey( owner );
			const copies = runtime().retained.get( key ) ?? [];
			if (
				! copies.some(
					( copy ) =>
						JSON.stringify( copy.entry.record ) ===
						JSON.stringify( existing.record )
				)
			) {
				copies.push( {
					entry: existing,
					counterpart: previousCounterpart,
				} );
				runtime().retained.set( key, copies );
			}
		}
		const cursor = {
			owner,
			revision: bucket.records[ owner.attempt ]?.revision ?? 0,
			raw,
			memory: true,
		};
		remember( cursor );
		const result = new FailureJournal(
			memory,
			{ ...this.identity, persistent: true },
			true
		).save(
			{ ...state, draft: state.draft ? { ...state.draft, owner } : null },
			cursor
		);
		return { ...result, durable: false };
	}

	/**
	 * Exact bucket bytes AND attempt revision are compared without an await.
	 * @param state  The complete proposed machine state.
	 * @param cursor The exact owner, revision, raw bucket and storage kind read earlier.
	 */
	save( state: FailureState, cursor: FailureCursor ): FailureWrite {
		state = withHeldClaims( state );
		if ( ! state.draft || ! parseFailure( recordOf( state ) ) ) {
			return { state, cursor, durable: false, conflict: true };
		}
		if ( cursor.retained ) {
			const key = ownerKey( cursor.owner );
			const expected = cursorEntry( cursor );
			const copies = runtime().retained.get( key ) ?? [];
			const index = copies.findIndex(
				( copy ) =>
					JSON.stringify( copy.entry ) === JSON.stringify( expected )
			);
			if (
				cursor.owner.scope !== this.identity.scope ||
				state.draft.owner?.scope !== cursor.owner.scope ||
				state.draft.owner.attempt !== cursor.owner.attempt ||
				index < 0 ||
				runtime().selected.get( key ) !== JSON.stringify( expected )
			) {
				return { state, cursor, durable: false, conflict: true };
			}
			const entry = {
				revision: cursor.revision + 1,
				record: JSON.parse(
					JSON.stringify( recordOf( state ) )
				) as StoredFailure,
			};
			copies[ index ] = { ...copies[ index ], entry };
			const written = retainedCursor( cursor.owner, entry );
			runtime().selected.set( key, JSON.stringify( entry ) );
			remember( written );
			return { state, cursor: written, durable: false, conflict: false };
		}
		if ( runtime().selected.has( ownerKey( cursor.owner ) ) ) {
			return { state, cursor, durable: false, conflict: true };
		}
		if ( cursor.memory && ! this.memory ) {
			const result = new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			).save( state, cursor );
			return { ...result, durable: false };
		}

		const failed = ( conflict: boolean ): FailureWrite => ( {
			state,
			cursor,
			durable: false,
			conflict,
		} );
		const latest = runtime().latest.get(
			cursor.owner.scope + ':' + cursor.owner.attempt
		);
		if ( latest !== undefined && latest !== this.memory ) {
			return failed( true );
		}

		if (
			cursor.owner.scope !== this.identity.scope ||
			! state.draft ||
			state.draft.owner?.attempt !== cursor.owner.attempt ||
			state.draft.owner.scope !== cursor.owner.scope
		) {
			return failed( true );
		}
		if ( ! this.identity.persistent ) {
			return failed( false );
		}
		const key = failureBucketKey( this.identity.scope );
		let bucket: Bucket;
		try {
			if ( this.store.getItem( key ) !== cursor.raw ) {
				return failed( true );
			}
			bucket = bucketOf( cursor.raw, this.identity.scope );
			if (
				( bucket.records[ cursor.owner.attempt ]?.revision ?? 0 ) !==
				cursor.revision
			) {
				return failed( true );
			}
		} catch {
			return failed( false );
		}
		const attempt = cursor.owner.attempt;
		const revision = cursor.revision + 1;
		const write = ( next: FailureState ): FailureWrite | null => {
			// The whole proposed bucket is needed only after exact CAS succeeds.

			const updated: Bucket = {
				...bucket,
				active: attempt,
				order: cursor.revision
					? bucket.order
					: [ ...bucket.order, attempt ],
				records: {
					...bucket.records,
					[ attempt ]: { revision, record: recordOf( next ) },
				},
			};
			try {
				if ( this.store.getItem( key ) !== cursor.raw ) {
					return failed( true );
				}
				const encoded = JSON.stringify( updated );
				this.store.setItem( key, encoded );
				if ( this.store.getItem( key ) !== encoded ) {
					return null;
				}
				const written = {
					owner: cursor.owner,
					revision,
					raw: encoded,
					memory: this.memory,
				};
				remember( written );
				return {
					state: next,
					cursor: written,
					durable: ! this.memory,
					conflict: false,
				};
			} catch {
				return null;
			}
		};
		const whole = write( state );
		if ( whole ) {
			return whole;
		}
		if ( state.phase === 'editing' && ! this.memory ) {
			return this.keepMemory( state, cursor.owner, cursor );
		}
		// File-specific degradation is explicit; the current mount still owns its bytes.
		for (
			let count = state.draft.uploads.length - 1;
			count >= 0;
			count--
		) {
			const reduced = draftWith(
				state,
				state.draft.uploads.slice( 0, count )
			);
			const result = write( reduced );
			if ( result ) {
				return result;
			}
		}
		return this.memory
			? failed( false )
			: this.keepMemory( state, cursor.owner, cursor );
	}

	/**
	 * Preserve already accepted editing bytes across unrelated attempt writes or unavailable storage.
	 * @param state    Proposed editing bytes, still bound to their original owner.
	 * @param expected The last exact checkpoint of that operation.
	 */
	checkpoint( state: FailureState, expected: FailureCursor ): FailureWrite {
		const failed = ( conflict: boolean ): FailureWrite => ( {
			state,
			cursor: expected,
			durable: false,
			conflict,
		} );
		if (
			state.phase !== 'editing' ||
			expected.owner.scope !== this.identity.scope ||
			state.draft?.owner?.scope !== expected.owner.scope ||
			state.draft.owner.attempt !== expected.owner.attempt
		) {
			return failed( true );
		}
		let current: FailureCandidate | null;
		try {
			current = this.rebase( expected, true );
		} catch {
			// An unreadable bucket proves no replacement revision. Retain only
			// this accepted owner in memory, with its known durable counterpart.
			return this.memory
				? failed( false )
				: this.keepMemory( state, expected.owner, expected );
		}
		if (
			! current?.record.editing ||
			! this.sameCheckpoint( expected, current.cursor )
		) {
			return failed( true );
		}
		if (
			JSON.stringify( recordOf( state ) ) ===
			JSON.stringify( current.record )
		) {
			return {
				state,
				cursor: current.cursor,
				durable: ! current.cursor.memory,
				conflict: false,
			};
		}
		return this.save( state, current.cursor );
	}

	/**
	 * Rebase may advance a bucket, never this attempt's entire accepted entry.
	 * @param expected
	 * @param current
	 */
	sameCheckpoint( expected: FailureCursor, current: FailureCursor ): boolean {
		try {
			const attempt = expected.owner.attempt;
			return (
				JSON.stringify(
					JSON.parse( expected.raw! ).records[ attempt ]
				) ===
				JSON.stringify( JSON.parse( current.raw! ).records[ attempt ] )
			);
		} catch {
			return false;
		}
	}

	/**
	 * Read the other existing divergent copy; the caller still needs native restore authority.
	 * @param current
	 */
	alternative( current: FailureCursor ): FailureCandidate | null {
		const copies = this.copies( current.owner );
		const currentEntry = cursorEntry( current );
		const record = currentEntry?.record;
		const index = copies.findIndex(
			( copy ) =>
				JSON.stringify( copy.record ) === JSON.stringify( record )
		);
		return copies.length > 1
			? copies[ ( index + 1 ) % copies.length ]
			: ( copies.find(
					( copy ) =>
						JSON.stringify( copy.record ) !==
						JSON.stringify( record )
				) ?? null );
	}

	/**
	 * Exact read only; asynchronous writers keep the ordinary active-copy gate.
	 * @param expected
	 */
	variant( expected: FailureCursor ): FailureCandidate | null {
		const current = this.rebase( expected, false, true );
		return current && this.sameCheckpoint( expected, current.cursor )
			? current
			: null;
	}

	/**
	 * Only a freshly authorized explicit Restore may select an existing variant.
	 * @param expected
	 */
	select( expected: FailureCursor ): FailureCandidate | null {
		const current = this.variant( expected );
		if ( current ) {
			const key = expected.owner.scope + ':' + expected.owner.attempt;
			if ( current.cursor.retained ) {
				runtime().selected.set(
					key,
					JSON.stringify( cursorEntry( current.cursor ) )
				);
			} else {
				runtime().selected.delete( key );
			}
			runtime().latest.set( key, !! current.cursor.memory );
			runtime().active.set(
				expected.owner.scope,
				expected.owner.attempt
			);
		}
		return current;
	}

	matches( cursor: FailureCursor ): boolean {
		const current = this.rebase( cursor );
		return !! current && current.cursor.raw === cursor.raw;
	}

	/**
	 * Explicit exchange may rebase over another attempt, never over this record's revision.
	 * @param expected    The immutable owner expected by this operation.
	 * @param throwOnRead Distinguish unavailable storage for an accepted editing checkpoint.
	 * @param inactive    Permit only an exact read for a verified explicit variant exchange.
	 */
	rebase(
		expected: FailureCursor,
		throwOnRead = false,
		inactive = false
	): FailureCandidate | null {
		const selected = runtime().selected.get( ownerKey( expected.owner ) );
		if ( expected.retained ) {
			if (
				expected.owner.scope !== this.identity.scope ||
				( ! inactive &&
					selected !== JSON.stringify( cursorEntry( expected ) ) )
			) {
				return null;
			}
			const copy = (
				runtime().retained.get( ownerKey( expected.owner ) ) ?? []
			).find(
				( item ) =>
					JSON.stringify( item.entry ) ===
					JSON.stringify( cursorEntry( expected ) )
			);
			return copy
				? {
						record: JSON.parse(
							JSON.stringify( copy.entry.record )
						) as StoredFailure,
						cursor: retainedCursor( expected.owner, copy.entry ),
					}
				: null;
		}
		if ( ! inactive && selected ) {
			return null;
		}
		if ( expected.memory && ! this.memory ) {
			return new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			).rebase( expected, throwOnRead, inactive );
		}
		const latest = runtime().latest.get(
			expected.owner.scope + ':' + expected.owner.attempt
		);
		if ( ! inactive && latest !== undefined && latest !== this.memory ) {
			return null;
		}
		if (
			expected.owner.scope !== this.identity.scope ||
			! this.identity.persistent
		) {
			return null;
		}
		try {
			const raw = this.store.getItem(
				failureBucketKey( this.identity.scope )
			);
			const bucket = bucketOf( raw, this.identity.scope );
			const entry = bucket.records[ expected.owner.attempt ];
			return entry?.revision === expected.revision
				? {
						record: entry.record,
						cursor: { ...expected, raw },
					}
				: null;
		} catch ( error ) {
			if ( throwOnRead ) {
				throw error;
			}
			return null;
		}
	}

	/**
	 * Consume only this revision. Repair active in the same CAS using insertion order.
	 * @param cursor        The exact owner, revision, raw bucket and storage kind read earlier.
	 * @param retainUpdated A verified UI operation may consume its selected copy while retaining an updated opposite variant.
	 */
	consume( cursor: FailureCursor, retainUpdated = false ): boolean {
		if ( cursor.owner.scope !== this.identity.scope ) {
			return false;
		}
		if ( cursor.retained ) {
			if ( ! this.matches( cursor ) ) {
				return false;
			}
			const key = ownerKey( cursor.owner );
			const copies = runtime().retained.get( key ) ?? [];
			const copy = copies.find(
				( item ) =>
					JSON.stringify( item.entry ) ===
					JSON.stringify( cursorEntry( cursor ) )
			);
			try {
				if ( this.identity.persistent ) {
					const bucketKey = failureBucketKey( cursor.owner.scope );
					const raw = this.store.getItem( bucketKey );
					const bucket = bucketOf( raw, cursor.owner.scope );
					const entry = bucket.records[ cursor.owner.attempt ];
					const exact =
						entry &&
						copy?.counterpart?.revision === entry.revision &&
						copy.counterpart.record ===
							JSON.stringify(
								JSON.parse( raw! ).records[
									cursor.owner.attempt
								]
							);
					if ( entry && ! exact && ! retainUpdated ) {
						return false;
					}
					if ( exact ) {
						delete bucket.records[ cursor.owner.attempt ];
						bucket.order = bucket.order.filter(
							( attempt ) => attempt !== cursor.owner.attempt
						);
						if ( bucket.active === cursor.owner.attempt ) {
							bucket.active = bucket.order.at( -1 ) ?? null;
						}
						const encoded = JSON.stringify( bucket );
						if ( this.store.getItem( bucketKey ) !== raw ) {
							return false;
						}
						this.store.setItem( bucketKey, encoded );
						if ( this.store.getItem( bucketKey ) !== encoded ) {
							return false;
						}
					}
				}
			} catch {
				return false;
			}
			runtime().retained.set(
				key,
				copies.filter( ( item ) => item !== copy )
			);
			runtime().selected.delete( key );
			this.remaining( cursor.owner );
			return true;
		}
		if ( runtime().selected.has( ownerKey( cursor.owner ) ) ) {
			return false;
		}
		if ( cursor.memory && ! this.memory ) {
			const memory = new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			);
			if ( ! memory.matches( cursor ) ) {
				return false;
			}
			let retainedDurable = false;
			const counterpart = runtime().counterparts.get(
				cursor.owner.scope + ':' + cursor.owner.attempt
			);
			if ( ! counterpart ) {
				try {
					const raw = this.store.getItem(
						failureBucketKey( cursor.owner.scope )
					);
					if (
						bucketOf( raw, cursor.owner.scope ).records[
							cursor.owner.attempt
						]
					) {
						return false;
					}
				} catch {
					return false;
				}
			}
			if ( counterpart ) {
				try {
					const key = failureBucketKey( cursor.owner.scope );
					const raw = this.store.getItem( key );
					const bucket = bucketOf( raw, cursor.owner.scope );
					const entry = bucket.records[ cursor.owner.attempt ];
					if ( entry ) {
						if (
							entry.revision !== counterpart.revision ||
							JSON.stringify(
								JSON.parse( raw! ).records[
									cursor.owner.attempt
								]
							) !== counterpart.record
						) {
							if ( ! retainUpdated ) {
								return false;
							}
							retainedDurable = true;
						}
						if ( ! retainedDurable ) {
							delete bucket.records[ cursor.owner.attempt ];
							bucket.order = bucket.order.filter(
								( attempt ) => attempt !== cursor.owner.attempt
							);
							if ( bucket.active === cursor.owner.attempt ) {
								bucket.active = bucket.order.at( -1 ) ?? null;
							}
							const encoded = JSON.stringify( bucket );
							if ( this.store.getItem( key ) !== raw ) {
								return false;
							}
							this.store.setItem( key, encoded );
							if ( this.store.getItem( key ) !== encoded ) {
								return false;
							}
						}
					}
				} catch {
					return false;
				}
			}
			const consumed = memory.consume( cursor );
			if ( consumed ) {
				runtime().counterparts.delete(
					cursor.owner.scope + ':' + cursor.owner.attempt
				);
			}
			if ( consumed && retainedDurable ) {
				const key = cursor.owner.scope + ':' + cursor.owner.attempt;
				runtime().consumed.delete( key );
				runtime().latest.set( key, false );
				runtime().active.set(
					cursor.owner.scope,
					cursor.owner.attempt
				);
			}
			if ( consumed ) {
				this.remaining( cursor.owner );
			}
			return consumed;
		}
		const latest = runtime().latest.get(
			cursor.owner.scope + ':' + cursor.owner.attempt
		);
		if ( latest !== undefined && latest !== this.memory ) {
			return false;
		}
		if (
			cursor.owner.scope !== this.identity.scope ||
			! this.identity.persistent
		) {
			return false;
		}
		const key = failureBucketKey( this.identity.scope );
		const retainedMemory =
			! this.memory &&
			!! bucketOf( memoryStore().getItem( key ), this.identity.scope )
				.records[ cursor.owner.attempt ];
		if ( retainedMemory && ! retainUpdated ) {
			return false;
		}
		try {
			if ( this.store.getItem( key ) !== cursor.raw ) {
				return false;
			}
			const bucket = bucketOf( cursor.raw, this.identity.scope );
			if (
				bucket.records[ cursor.owner.attempt ]?.revision !==
				cursor.revision
			) {
				return false;
			}
			delete bucket.records[ cursor.owner.attempt ];
			bucket.order = bucket.order.filter(
				( attempt ) => attempt !== cursor.owner.attempt
			);
			if ( bucket.active === cursor.owner.attempt ) {
				bucket.active = bucket.order.at( -1 ) ?? null;
			}
			const encoded = JSON.stringify( bucket );
			this.store.setItem( key, encoded );
			const consumed = this.store.getItem( key ) === encoded;
			if ( consumed ) {
				const shared = runtime();
				shared.latest.delete(
					cursor.owner.scope + ':' + cursor.owner.attempt
				);
				shared.consumed.add(
					cursor.owner.scope + ':' + cursor.owner.attempt
				);
				if ( retainedMemory ) {
					shared.consumed.delete(
						cursor.owner.scope + ':' + cursor.owner.attempt
					);
					shared.latest.set(
						cursor.owner.scope + ':' + cursor.owner.attempt,
						true
					);
					shared.counterparts.delete(
						cursor.owner.scope + ':' + cursor.owner.attempt
					);
				}
				if (
					shared.active.get( cursor.owner.scope ) ===
					cursor.owner.attempt
				) {
					shared.active.set(
						cursor.owner.scope,
						retainedMemory ? cursor.owner.attempt : null
					);
				}
			}
			if ( consumed && ! this.memory ) {
				this.remaining( cursor.owner );
			}
			return consumed;
		} catch {
			return false;
		}
	}
}
