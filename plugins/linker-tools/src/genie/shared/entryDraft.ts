/** Marketing handoff ownership. Text/filenames only; never prepared bytes. */
import type { GenieConfig } from '../config';

export type EntryMode = 'compose' | 'attach' | 'nameplate' | 'voice';
export interface EntryDraft {
	id: string;
	text: string;
	sourcePath: string;
	mode: EntryMode;
	scope: string;
}
export interface ComposerDraft {
	text: string;
	missing: string[];
}
interface Recovery {
	v: 1;
	scope: string;
	entries: EntryDraft[];
	claimed: string[];
	composer: ComposerDraft | null;
	parked: ComposerDraft | null;
}
export const ENTRY_KEY = 'linker-genie-entry-draft';
const TAB_KEY = 'linker-genie-entry-tab';
/** Same auxiliary-read budget as current product metadata; never holds a model turn. */
const CONTEXT_BUDGET_MS = 5000;

export function isEntryDraft( value: unknown ): value is EntryDraft {
	if ( ! value || typeof value !== 'object' ) {
		return false;
	}
	const item = value as Partial< EntryDraft >;
	return (
		typeof item.id === 'string' &&
		!! item.id &&
		typeof item.text === 'string' &&
		typeof item.scope === 'string' &&
		!! item.scope &&
		typeof item.sourcePath === 'string' &&
		item.sourcePath.startsWith( '/' ) &&
		! item.sourcePath.startsWith( '//' ) &&
		[ 'compose', 'attach', 'nameplate', 'voice' ].includes(
			item.mode ?? ''
		)
	);
}

export function newEntryId(): string {
	return crypto.randomUUID();
}

/**
 * Fresh server identity is required before any cached text may be rendered.
 * @param config Current native REST identity.
 */
async function readEntryScope(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >
): Promise< string > {
	let tab = sessionStorage.getItem( TAB_KEY );
	if ( ! tab ) {
		tab = newEntryId();
		sessionStorage.setItem( TAB_KEY, tab );
	}
	const controller = new AbortController();
	// `finally` clears this timer on every return and throw.
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
				body: JSON.stringify( { tab } ),
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
			! /^[a-f0-9]{64}$/.test( result.scope )
		) {
			throw new Error( 'entry-context' );
		}
		return result.scope;
	} finally {
		window.clearTimeout( timer );
	}
}

const contextReads = new Map< string, Promise< string > >();
/**
 * Coalesce only initial concurrent reads, so a new guest mints one browser epoch.
 * Transport/ownership checks bypass an earlier read that may predate an identity change.
 * @param config Current native REST identity.
 * @param fresh  Require a new server request immediately before consumption.
 */
export function entryScope(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	fresh = false
): Promise< string > {
	if ( fresh ) {
		return readEntryScope( config );
	}
	const key = `${ config.restUrl }|${ config.restNonce }`;
	const pending = contextReads.get( key );
	if ( pending ) {
		return pending;
	}
	const read = readEntryScope( config ).finally( () =>
		contextReads.delete( key )
	);
	contextReads.set( key, read );
	return read;
}

export function readEntryRecovery( scope: string ): Recovery {
	const empty: Recovery = {
		v: 1,
		scope,
		entries: [],
		claimed: [],
		composer: null,
		parked: null,
	};
	try {
		const stored = JSON.parse(
			sessionStorage.getItem( ENTRY_KEY ) ?? 'null'
		) as Recovery | null;
		if ( ! stored || stored.v !== 1 || stored.scope !== scope ) {
			sessionStorage.removeItem( ENTRY_KEY );
			return empty;
		}
		return {
			...empty,
			entries: Array.isArray( stored.entries )
				? stored.entries
						.filter( isEntryDraft )
						.filter( ( item ) => item.scope === scope )
				: [],
			claimed: Array.isArray( stored.claimed )
				? stored.claimed.filter( ( id ) => typeof id === 'string' )
				: [],
			parked:
				stored.parked &&
				typeof stored.parked.text === 'string' &&
				Array.isArray( stored.parked.missing )
					? {
							text: stored.parked.text,
							missing: stored.parked.missing.filter(
								( name ) => typeof name === 'string'
							),
						}
					: null,
			composer:
				stored.composer &&
				typeof stored.composer.text === 'string' &&
				Array.isArray( stored.composer.missing )
					? {
							text: stored.composer.text,
							missing: stored.composer.missing.filter(
								( name ) => typeof name === 'string'
							),
						}
					: null,
		};
	} catch {
		return empty;
	}
}

export function updateEntryRecovery(
	scope: string,
	change: ( record: Recovery ) => Recovery
): boolean {
	try {
		const encoded = JSON.stringify( change( readEntryRecovery( scope ) ) );
		sessionStorage.setItem( ENTRY_KEY, encoded );
		return sessionStorage.getItem( ENTRY_KEY ) === encoded;
	} catch {
		// Source/editor stays the owner if storage is unavailable. No false acknowledgement.
		return false;
	}
}

export function rememberEntry( draft: EntryDraft ): boolean {
	return updateEntryRecovery( draft.scope, ( record ) => ( {
		...record,
		entries: record.entries.some( ( item ) => item.id === draft.id )
			? record.entries
			: [ ...record.entries, draft ],
	} ) );
}
export function finishEntry( draft: EntryDraft ): void {
	updateEntryRecovery( draft.scope, ( record ) => ( {
		...record,
		entries: record.entries.filter( ( item ) => item.id !== draft.id ),
	} ) );
}
export function entryAck(
	draft: EntryDraft,
	phase: 'accepted' | 'settled' | 'failed'
): void {
	window.dispatchEvent(
		new CustomEvent( 'linker-genie-entry-state', {
			detail: { id: draft.id, phase },
		} )
	);
}
