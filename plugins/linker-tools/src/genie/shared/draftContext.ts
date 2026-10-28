/** Native ownership plus a surface epoch: identity checks and thread changes are distinct. */
import type { FailureOwner } from './failure';
import type { GenieConfig } from '../config';
import { nativeScope, type NativeScope } from './nativeScope';

export interface DraftLease {
	scope: string;
	epoch: number;
}
export type ContextPhase = 'loading' | 'ready' | 'unavailable';
export class DraftContext {
	private identityValue: NativeScope | null = null;
	private epoch = 0;
	private generation = 0;
	private alive = true;
	private pending: Promise< NativeScope > | null = null;
	private listeners = new Set< () => void >();
	private leaveListeners = new Set< () => void >();
	private editorValue: FailureOwner | null = null;
	phase: ContextPhase = 'loading';
	constructor(
		private readonly config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
		private readonly changed: () => void
	) {}
	get identity(): NativeScope | null {
		return this.identityValue;
	}
	get editor(): FailureOwner | null {
		return this.editorValue;
	}
	/** Called synchronously before accepting text/file/dictation bytes. */
	acceptEditor(): FailureOwner | null {
		const lease = this.capture();
		if ( ! lease ) {
			return null;
		}
		if ( ! this.editorValue ) {
			this.editorValue = {
				scope: lease.scope,
				attempt: crypto.randomUUID(),
			};
			this.notify();
		}
		return this.editorValue;
	}
	adoptEditor( owner: FailureOwner ): void {
		if ( this.capture()?.scope === owner.scope ) {
			this.editorValue = owner;
		}
	}
	releaseEditor(): void {
		this.editorValue = null;
	}
	beforeLeave( listener: () => void ): () => void {
		this.leaveListeners.add( listener );
		return () => this.leaveListeners.delete( listener );
	}
	checkpoint(): void {
		this.preserveEditor();
	}
	private preserveEditor(): void {
		if ( this.phase === 'ready' && this.editorValue ) {
			this.leaveListeners.forEach( ( listener ) => listener() );
		}
	}

	subscribe( listener: () => void ): () => void {
		this.listeners.add( listener );
		return () => this.listeners.delete( listener );
	}
	private notify(): void {
		this.listeners.forEach( ( listener ) => listener() );
	}
	capture(): DraftLease | null {
		return this.alive && this.phase === 'ready' && this.identityValue
			? { scope: this.identityValue.scope, epoch: this.epoch }
			: null;
	}
	owns( lease: DraftLease | null ): boolean {
		return (
			!! lease &&
			this.alive &&
			lease.scope === this.identityValue?.scope &&
			lease.epoch === this.epoch
		);
	}
	valid( lease: DraftLease | null ): boolean {
		return this.owns( lease ) && this.phase === 'ready';
	}

	/** Wait across a superseded cold lookup without treating its old response as authority. */
	async ready(): Promise< DraftLease | null > {
		while ( this.pending ) {
			const pending = this.pending;
			try {
				await pending;
			} catch {
				if ( this.pending === pending ) {
					return null;
				}
				// A newer check may already have settled. Only its current
				// capture can authorize readiness, never this stale response.
			}
		}
		return this.capture();
	}
	async initialized(): Promise< NativeScope > {
		if (
			! this.pending &&
			( this.phase !== 'ready' || ! this.identityValue )
		) {
			void this.verify( false ).catch( () => undefined );
		}
		if ( ! ( await this.ready() ) || ! this.identityValue ) {
			throw new Error( 'draft-context-unavailable' );
		}
		return this.identityValue;
	}

	/**
	 * Revalidation quarantines already mounted text, filenames and bytes until authority returns.
	 * @param fresh Always request a new native identity when true.
	 */
	verify( fresh = true ): Promise< NativeScope > {
		this.preserveEditor();
		const generation = ++this.generation;
		this.phase = 'loading';
		this.notify();
		const read = nativeScope( this.config, fresh )
			.then(
				( identity ) => {
					if ( ! this.alive || generation !== this.generation ) {
						throw new Error( 'draft-context-superseded' );
					}
					if (
						this.identityValue &&
						this.identityValue.scope !== identity.scope
					) {
						this.epoch += 1;
						this.editorValue = null;
						this.changed();
					}
					this.identityValue = identity;
					this.phase = 'ready';
					this.notify();
					return identity;
				},
				( error: unknown ) => {
					if ( this.alive && generation === this.generation ) {
						this.phase = 'unavailable';
						this.notify();
					}
					throw error;
				}
			)
			.finally( () => {
				if ( this.pending === read ) {
					this.pending = null;
				}
			} );
		this.pending = read;
		return read;
	}
	/**
	 * Same-owner work may finish while a check is pending, but may settle only after it.
	 * @param lease The owner and surface epoch captured before the asynchronous operation.
	 */
	async settle( lease: DraftLease | null ): Promise< boolean > {
		while ( this.pending ) {
			const pending = this.pending;
			try {
				await pending;
			} catch {
				if ( this.pending === pending ) {
					return false;
				}
			}
			if ( ! this.owns( lease ) ) {
				return false;
			}
		}
		return this.valid( lease );
	}
	/**
	 * Accepted file preparation can wait through an outage; it is painted only for its original owner.
	 * @param lease The owner and surface epoch captured before the asynchronous operation.
	 */
	async whenVerified( lease: DraftLease | null ): Promise< boolean > {
		if ( this.valid( lease ) ) {
			return true;
		}
		if ( ! this.owns( lease ) ) {
			return false;
		}
		return new Promise( ( resolve ) => {
			const unsubscribe = this.subscribe( () => {
				if ( ! this.owns( lease ) || this.phase === 'ready' ) {
					unsubscribe();
					resolve( this.valid( lease ) );
				}
			} );
		} );
	}

	async authorize( lease: DraftLease | null ): Promise< boolean > {
		if ( ! lease || lease.epoch !== this.epoch || ! this.alive ) {
			return false;
		}
		try {
			await this.verify( true );
		} catch {
			return false;
		}
		return this.valid( lease );
	}
	/** New/Select/Delete invalidates old callbacks even under the same native account. */
	invalidate(): void {
		this.preserveEditor();
		this.editorValue = null;
		this.epoch += 1;
		this.notify();
	}
	dispose(): void {
		this.preserveEditor();
		this.editorValue = null;
		this.alive = false;
		this.epoch += 1;
		this.generation += 1;
		this.notify();
		this.listeners.clear();
		this.leaveListeners.clear();
	}
}
