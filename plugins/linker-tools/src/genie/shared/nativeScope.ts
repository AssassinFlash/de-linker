/** Native principal comparison shared by the independently built Hero and dock. */
import type { GenieConfig } from '../config';

type Config = Pick< GenieConfig, 'restUrl' | 'restNonce' >;
export interface NativeScope {
	scope: string;
	/** False means this window can use its editor, but cannot claim stored drafts. */
	persistent: boolean;
}
interface SharedScope {
	memoryTab?: string;
	knownTab?: string;
	generation: number;
	pending: Map< string, Promise< NativeScope > >;
	durable: WeakMap< Promise< NativeScope >, Promise< string > >;
}
const WINDOW_KEY = '__linkerGenieNativeScope';
export const TAB_KEY = 'linker-genie-entry-tab';
/** Existing auxiliary metadata deadline; independent of model transport. */
const CONTEXT_BUDGET_MS = 5000;

function shared(): SharedScope {
	const target = window as unknown as Record< string, unknown >;
	if ( ! target[ WINDOW_KEY ] ) {
		target[ WINDOW_KEY ] = {
			generation: 0,
			pending: new Map(),
			durable: new WeakMap(),
		};
	}
	const lifecycleKey = '__linkerGenieNativeScopeLifecycle';
	if ( ! target[ lifecycleKey ] ) {
		const invalidate = () => {
			const state = target[ WINDOW_KEY ] as SharedScope | undefined;
			if ( state ) {
				state.generation += 1;
				state.pending.clear();
			}
		};
		target[ lifecycleKey ] = invalidate;
		window.addEventListener( 'linker-genie-identity-change', invalidate );
	}
	return target[ WINDOW_KEY ] as SharedScope;
}
function tabIdentity(): { tab: string; persistent: boolean } {
	const state = shared();
	if ( state.memoryTab ) {
		return { tab: state.memoryTab, persistent: false };
	}
	try {
		let tab = window.sessionStorage.getItem( TAB_KEY );
		if ( ! tab ) {
			tab = crypto.randomUUID();
			window.sessionStorage.setItem( TAB_KEY, tab );
			if ( window.sessionStorage.getItem( TAB_KEY ) !== tab ) {
				throw new Error( 'tab-readback' );
			}
		}
		state.knownTab = tab;
		return { tab, persistent: true };
	} catch {
		state.memoryTab = state.knownTab ?? crypto.randomUUID();
		return { tab: state.memoryTab, persistent: false };
	}
}

async function lookup(
	config: Config,
	generation: number
): Promise< NativeScope > {
	const identity = tabIdentity();
	const controller = new AbortController();
	// The finally block consumes this timer even when the validated response returns early.
	// eslint-disable-next-line @wordpress/no-unused-vars-before-return
	const timer = window.setTimeout(
		() => controller.abort(),
		CONTEXT_BUDGET_MS
	);
	try {
		const response = await fetch(
			`${ config.restUrl }linker-ai/v1/genie/entry-context`,
			{
				method: 'POST',
				credentials: 'same-origin',
				cache: 'no-store',
				headers: {
					'Content-Type': 'application/json',
					'X-WP-Nonce': config.restNonce,
				},
				body: JSON.stringify( { tab: identity.tab } ),
				signal: controller.signal,
			}
		);
		if ( ! response.ok ) {
			throw new Error( 'entry-context' );
		}
		const result: unknown = await response.json();
		if (
			! result ||
			typeof result !== 'object' ||
			! ( 'scope' in result ) ||
			typeof result.scope !== 'string' ||
			! /^[a-f0-9]{64}$/.test( result.scope ) ||
			generation !== shared().generation
		) {
			throw new Error( 'entry-context' );
		}
		return { scope: result.scope, persistent: identity.persistent };
	} finally {
		window.clearTimeout( timer );
	}
}

/**
 * Coalesce only a cold pending bootstrap. Every fresh send/retry gets its own read.
 * @param config The currently mounted native routes and REST nonce.
 * @param fresh  Always request a new native identity when true.
 */
export function nativeScope(
	config: Config,
	fresh = false
): Promise< NativeScope > {
	const state = shared();
	if ( fresh ) {
		return lookup( config, state.generation );
	}
	const key = `${ config.restUrl }|${ config.restNonce }`;
	const pending = state.pending.get( key );
	if ( pending ) {
		return pending;
	}
	const read = lookup( config, state.generation ).finally( () => {
		if ( state.pending.get( key ) === read ) {
			state.pending.delete( key );
		}
	} );
	state.pending.set( key, read );
	return read;
}

/**
 * Preserve coalescing at the marketing adapter while forbidding a false durable claim.
 * @param config The currently mounted native routes and REST nonce.
 * @param fresh  Always request a new native identity when true.
 */
export function durableNativeScope(
	config: Config,
	fresh = false
): Promise< string > {
	const read = nativeScope( config, fresh );
	const state = shared();
	const existing = state.durable.get( read );
	if ( existing ) {
		return existing;
	}
	const adapted = read.then( ( identity ) => {
		if ( ! identity.persistent ) {
			throw new Error( 'entry-storage' );
		}
		return identity.scope;
	} );
	state.durable.set( read, adapted );
	return adapted;
}

/** Known native lifecycle changes invalidate even a shared in-progress bootstrap. */
export function invalidateNativeScope(): void {
	const state = shared();
	state.generation += 1;
	state.pending.clear();
}
