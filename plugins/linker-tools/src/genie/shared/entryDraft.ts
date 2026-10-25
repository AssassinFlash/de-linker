/** Marketing handoff ownership. Text/filenames only; never prepared bytes. */
import type { GenieConfig } from '../config';
import { durableNativeScope } from './nativeScope';

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
 * Marketing durable handoff cannot acknowledge a memory-only tab.
 * @param config
 * @param fresh
 */
export function entryScope(
	config: Pick< GenieConfig, 'restUrl' | 'restNonce' >,
	fresh = false
): Promise< string > {
	return durableNativeScope( config, fresh );
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
export function finishEntry( draft: EntryDraft ): boolean {
	try {
		// Completion is exact removal, never a foreign-scope read with cleanup side effects.
		const raw = sessionStorage.getItem( ENTRY_KEY );
		const record = JSON.parse( raw ?? 'null' ) as Recovery | null;
		if (
			! record ||
			record.scope !== draft.scope ||
			! Array.isArray( record.entries )
		) {
			return false;
		}
		const target = record.entries.find( ( item ) => item.id === draft.id );
		if ( ! target ) {
			return true;
		}
		if (
			target.scope !== draft.scope ||
			target.text !== draft.text ||
			target.mode !== draft.mode ||
			target.sourcePath !== draft.sourcePath
		) {
			return false;
		}
		const encoded = JSON.stringify( {
			...record,
			entries: record.entries.filter( ( item ) => item.id !== draft.id ),
		} );
		if ( sessionStorage.getItem( ENTRY_KEY ) !== raw ) {
			return false;
		}
		sessionStorage.setItem( ENTRY_KEY, encoded );
		return sessionStorage.getItem( ENTRY_KEY ) === encoded;
	} catch {
		return false;
	}
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
