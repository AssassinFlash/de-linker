/** Native ownership plus a surface epoch: identity checks and thread changes are distinct. */
import type { FailureOwner } from './failure';
import type { GenieConfig } from '../config';
import { nativeScope, type NativeScope } from './nativeScope';

export interface DraftLease {
	scope: string;
	epoch: number;
	currentEditor?: () => boolean;
}
export type ContextPhase = 'loading' | 'ready' | 'unavailable';
export class DraftEditor {
	private generation = 0;
	private ownerValue: FailureOwner | null = null;
	private readonly leaveListeners = new Set< () => void >();
	constructor(
		readonly context: DraftContext,
		private readonly changed: () => void
	) {}
	capture(): DraftLease | null {
		const lease = this.context.capture();
		const generation = this.generation;
		return lease
			? { ...lease, currentEditor: () => generation === this.generation }
			: null;
	}
	close(): void {
		this.checkpoint();
		this.ownerValue = null;
		this.generation++;
		this.changed();
	}
	get owner(): FailureOwner | null {
		return this.ownerValue;
	}
	accept(): FailureOwner | null {
		const lease = this.context.capture();
		if ( ! lease ) {
			return null;
		}
		if ( ! this.ownerValue ) {
			this.ownerValue = {
				scope: lease.scope,
				attempt: crypto.randomUUID(),
			};
			this.changed();
		}
		return this.ownerValue;
	}
	adopt( owner: FailureOwner ): void {
		if ( this.context.capture()?.scope === owner.scope ) {
			this.ownerValue = owner;
		}
	}
	release(): void {
		this.ownerValue = null;
	}
	beforeLeave( listener: () => void ): () => void {
		this.leaveListeners.add( listener );
		return () => this.leaveListeners.delete( listener );
	}
	checkpoint(): void {
		if ( this.ownerValue && this.context.phase === 'ready' ) {
			this.leaveListeners.forEach( ( listener ) => listener() );
		}
	}
}
export class DraftContext {
	private identityValue: NativeScope | null = null;
	private epoch = 0;
	private generation = 0;
	private alive = true;
	private pending: Promise< NativeScope > | null = null;
	private listeners = new Set< () => void >();
	readonly homeEditor = new DraftEditor( this, () => this.notify() );
	readonly panelEditor = new DraftEditor( this, () => this.notify() );
	phase: ContextPhase = 'loading';
	conversationId?: number;
	constructor(
		private readonly config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
		private readonly changed: () => void
	) {}
	get identity(): NativeScope | null {
		return this.identityValue;
	}
	checkpoint(): void {
		this.homeEditor.checkpoint();
		this.panelEditor.checkpoint();
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
			lease.epoch === this.epoch &&
			( lease.currentEditor?.() ?? true )
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
	 *
	 * A transient re-verification keeps the established identity authoritative:
	 * blanking every phase-gated surface for a same-owner verify window cleared
	 * the visitor's live composer text and swallowed their Enter (production
	 * 2026-11-07, window focus/pageshow re-verify). The scope-change branch
	 * below still parks the editor and bumps the epoch when authority actually
	 * moves, and a failed verify still marks the context unavailable.
	 *
	 * @param fresh Always request a new native identity when true.
	 */
	verify( fresh = true ): Promise< NativeScope > {
		if ( ! fresh && this.pending ) {
			return this.pending;
		}
		this.checkpoint();
		const generation = ++this.generation;
		if ( ! this.identityValue ) {
			this.phase = 'loading';
		}
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
						this.conversationId = undefined;
						this.homeEditor.release();
						this.panelEditor.release();
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
		this.checkpoint();
		this.homeEditor.release();
		this.panelEditor.release();
		this.epoch += 1;
		this.notify();
	}
	dispose(): void {
		this.checkpoint();
		this.homeEditor.release();
		this.panelEditor.release();
		this.alive = false;
		this.epoch += 1;
		this.generation += 1;
		this.notify();
		this.listeners.clear();
	}
}

type PageContextSlot = {
	context: DraftContext;
	clients: number;
	release: () => void;
};
type DraftWindow = Window & { __linkerGenieDraftAuthority?: PageContextSlot };

/**
 * Both entry bundles use the same page owner and lifecycle.
 * @param config Native REST routes and nonce for this page.
 */
export function pageDraftContext(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >
): DraftContext {
	const page = window as DraftWindow;
	if ( ! page.__linkerGenieDraftAuthority ) {
		page.__linkerGenieDraftAuthority = {
			context: new DraftContext( config, () => undefined ),
			clients: 0,
			release: () => undefined,
		};
	}
	return page.__linkerGenieDraftAuthority.context;
}

export function mountPageDraftContext( context: DraftContext ): () => void {
	const page = window as DraftWindow;
	const slot = page.__linkerGenieDraftAuthority!;
	if ( slot.clients++ === 0 ) {
		const check = () => {
			void context.verify( false ).catch( () => undefined );
		};
		const newIdentity = () => {
			void context.verify( true ).catch( () => undefined );
		};
		const checkpoint = () => context.checkpoint();
		const visibility = () => {
			if ( document.visibilityState === 'hidden' ) {
				checkpoint();
			} else {
				check();
			}
		};
		const pageShown = ( event: PageTransitionEvent ) => {
			if ( event.persisted ) {
				check();
			}
		};
		void context.initialized().catch( () => undefined );
		window.addEventListener( 'focus', check );
		window.addEventListener( 'pageshow', pageShown );
		window.addEventListener( 'pagehide', checkpoint );
		window.addEventListener( 'linker-genie-identity-change', newIdentity );
		document.addEventListener( 'visibilitychange', visibility );
		slot.release = () => {
			window.removeEventListener( 'focus', check );
			window.removeEventListener( 'pageshow', pageShown );
			window.removeEventListener( 'pagehide', checkpoint );
			window.removeEventListener(
				'linker-genie-identity-change',
				newIdentity
			);
			document.removeEventListener( 'visibilitychange', visibility );
			context.dispose();
			delete page.__linkerGenieDraftAuthority;
		};
	}
	return () => {
		if ( --slot.clients === 0 ) {
			slot.release();
		}
	};
}
