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

interface RuntimeJournal {
	data: Map< string, string >;
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
	const entry = JSON.parse( cursor.raw ).records[ cursor.owner.attempt ] as
		Entry | undefined;
	if ( entry?.revision === cursor.revision ) {
		runtime().counterparts.set(
			cursor.owner.scope + ':' + cursor.owner.attempt,
			{ revision: entry.revision, record: JSON.stringify( entry ) }
		);
	}
}
function remember( cursor: FailureCursor ): void {
	trustDurable( cursor );
	const shared = runtime();
	const { scope, attempt } = cursor.owner;
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
			if ( shared.consumed.has( scope + ':' + attempt ) ) {
				return null;
			}
			const inMemory =
				shared.latest.get( scope + ':' + attempt ) ??
				!! memory.records[ attempt ];
			const entry = inMemory
				? memory.records[ attempt ]
				: bucket.records[ attempt ];
			return entry
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
		if ( durable?.revision && ! durable.memory ) {
			const entry = bucketOf( durable.raw, owner.scope ).records[
				owner.attempt
			];
			if (
				entry &&
				! runtime().counterparts.has(
					owner.scope + ':' + owner.attempt
				)
			) {
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

	matches( cursor: FailureCursor ): boolean {
		const current = this.rebase( cursor );
		return !! current && current.cursor.raw === cursor.raw;
	}

	/**
	 * Explicit exchange may rebase over another attempt, never over this record's revision.
	 * @param expected The immutable owner expected by this operation.
	 */
	rebase( expected: FailureCursor ): FailureCandidate | null {
		if ( expected.memory && ! this.memory ) {
			return new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			).rebase( expected );
		}
		const latest = runtime().latest.get(
			expected.owner.scope + ':' + expected.owner.attempt
		);
		if ( latest !== undefined && latest !== this.memory ) {
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
		} catch {
			return null;
		}
	}

	/**
	 * Consume only this revision. Repair active in the same CAS using insertion order.
	 * @param cursor The exact owner, revision, raw bucket and storage kind read earlier.
	 */
	consume( cursor: FailureCursor ): boolean {
		if ( cursor.owner.scope !== this.identity.scope ) {
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
						if ( this.store.getItem( key ) !== raw ) {
							return false;
						}
						this.store.setItem( key, encoded );
						if ( this.store.getItem( key ) !== encoded ) {
							return false;
						}
					}
					runtime().counterparts.delete(
						cursor.owner.scope + ':' + cursor.owner.attempt
					);
				} catch {
					return false;
				}
			}
			return new FailureJournal(
				memoryStore(),
				{ ...this.identity, persistent: true },
				true
			).consume( cursor );
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
				if (
					shared.active.get( cursor.owner.scope ) ===
					cursor.owner.attempt
				) {
					shared.active.set( cursor.owner.scope, null );
				}
			}
			return consumed;
		} catch {
			return false;
		}
	}
}
