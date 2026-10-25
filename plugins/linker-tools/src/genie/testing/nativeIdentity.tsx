/**
 * Explicit native-principal fixture for UI units whose model/history clients are doubles.
 * This does not migrate or authorize unknown stored v1 bytes. Ownership integration
 * consumers use their own native HTTP/identity transition fixtures instead.
 */
import { act, render } from '@testing-library/react';
import { beforeEach, afterEach, vi } from 'vitest';
import type { ReactElement } from 'react';
import { FailureJournal } from '../shared/ownedFailure';
import { pageFailureStore, type StoredFailure } from '../shared/failure';
export const NATIVE_SCOPE = 'a'.repeat( 64 );
export function installNativeIdentityFixture(): void {
	beforeEach( () => {
		delete ( window as unknown as Record< string, unknown > )
			.__linkerGenieFailureJournal;
		delete ( window as unknown as Record< string, unknown > )
			.__linkerGenieNativeScope;
		vi.stubGlobal(
			'fetch',
			vi.fn( async ( url: unknown ) => {
				if ( String( url ).includes( '/entry-context' ) ) {
					return {
						ok: true,
						json: async () => ( { scope: NATIVE_SCOPE } ),
					};
				}
				throw new Error( `Unexpected unit HTTP: ${ String( url ) }` );
			} )
		);
	} );
	afterEach( () => vi.unstubAllGlobals() );
}
/**
 * Wait for the real component's asynchronous native initialization, including React effects.
 * @param element The actual component under its native identity fixture.
 */
export async function renderOwned( element: ReactElement ) {
	let mounted!: ReturnType< typeof render >;
	await act( async () => {
		mounted = render( element );
	} );
	return mounted;
}
/**
 * A deliberate current-principal producer fixture, never a rebind of cached legacy bytes.
 * @param record The deliberate owned producer fixture, never unknown legacy bytes.
 * @param scope  The explicitly verified native principal fixture.
 */
export function seedOwnedFailure(
	record: Pick< StoredFailure, 'text' | 'question' > &
		Partial< StoredFailure > &
		Record< string, unknown >,
	scope = NATIVE_SCOPE
): void {
	new FailureJournal( pageFailureStore(), { scope, persistent: true } ).begin(
		{
			phase: record.kind === null ? 'pending' : 'failed',
			kind: record.kind === null ? null : ( record.kind ?? 'upstream' ),
			draft: {
				...record,
				uploads: record.uploads ?? [],
				omitted: record.omitted ?? [],
			},
		}
	);
}

/**
 * Assertion helper for this explicitly fixed native-principal fixture.
 * @param scope The explicitly verified native principal fixture.
 */
export function currentOwnedRaw( scope = NATIVE_SCOPE ): string | null {
	const current = new FailureJournal( pageFailureStore(), {
		scope,
		persistent: true,
	} ).candidate();
	return current ? JSON.stringify( current.record ) : null;
}
