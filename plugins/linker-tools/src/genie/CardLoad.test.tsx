/**
 * The card's own content load is three states: pending is not loaded-empty
 * is not failed (#901). The first frame must not be the error copy, and the
 * wait must not be a live region.
 *
 * External dependencies
 */
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { storeClient } from './api/store';
import type { Locale } from './types';
import { GenieCards } from './components/GenieCard';

const PRODUCT = {
	id: 4107,
	name: 'SAJ H2-10K-T3',
	permalink: 'https://de-linker.test/product/saj-h2-10k-t3/',
	images: [],
	is_in_stock: true,
};

function card(
	products: ( ids: number[], locale: Locale ) => Promise< unknown[] >,
	ids = [ 4107 ]
) {
	render(
		<GenieCards
			products={ ids }

			store={
				{
					products,
					addAll: vi.fn(),
				} as unknown as ReturnType< typeof storeClient >
			}
			locale="en"
			statusFor={ () => ( { state: 'idle', text: '' } ) }
			onAdd={ vi.fn() }
			onSave={ vi.fn() }
		/>
	);
}

test( 'the first frame is neither the failure copy nor a live region', () => {
	card( () => new Promise( () => {} ) );

	expect(
		screen.queryByText( 'Genie could not load this product.' )
	).not.toBeInTheDocument();
	expect( document.querySelector( '[role="status"]' ) ).toBeNull();
	expect( document.querySelector( '[role="alert"]' ) ).toBeNull();
} );

test( 'a refused Store API read is a failure the card announces', async () => {
	card( () => Promise.reject( new Error( 'products 403' ) ) );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie could not load this product.'
	);
} );

test( 'a product removed from the shop retains its unavailable state', async () => {
	card( async () => [] );

	expect( await screen.findByText( 'Currently unavailable' ) ).toBeVisible();
	expect( screen.queryByRole( 'button', { name: 'Try again' } ) ).toBeNull();
} );

test( 'a failed product read retries in the same conversation', async () => {
	const products = vi
		.fn()
		.mockRejectedValueOnce( new Error( 'unavailable' ) )
		.mockResolvedValueOnce( [ PRODUCT ] );
	card( products );
	fireEvent.click(
		await screen.findByRole( 'button', { name: 'Try again' } )
	);
	expect(
		await screen.findByRole( 'link', { name: PRODUCT.name } )
	).toBeVisible();
} );

test( 'a resolving read renders the card', async () => {
	card( async () => [ PRODUCT ] );

	expect(
		await screen.findByRole( 'link', { name: 'SAJ H2-10K-T3' } )
	).toHaveAttribute( 'href', PRODUCT.permalink );
	expect(
		screen.queryByText( 'Genie could not load this product.' )
	).not.toBeInTheDocument();
} );

test( 'all twelve cards use one catalog request and display its model terms', async () => {
	const ids = Array.from( { length: 12 }, ( _, index ) => 4107 + index );
	const products = vi.fn( async () =>
		ids.map( ( id ) => ( {
			...PRODUCT,
			id,
			attributes: [
				{ taxonomy: 'pa_model', terms: [ { name: 'M-' + id } ] },
			],
		} ) )
	);
	card( products, ids );
	expect( await screen.findByText( /M-4118/ ) ).toBeVisible();
	expect( products ).toHaveBeenCalledExactlyOnceWith( ids, 'en' );
} );
