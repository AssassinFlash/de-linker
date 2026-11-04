/**
 * The card's own content load is three states: pending is not loaded-empty
 * is not failed (#901). The first frame must not be the error copy, and the
 * wait must not be a live region.
 *
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { storeClient } from '../configurator/api/store';
import type { Locale } from '../configurator/types';
import { GenieCard } from './components/GenieCard';

vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'H2-10K-T3' ),
} ) );

const PRODUCT = {
	id: 4107,
	name: 'SAJ H2-10K-T3',
	permalink: 'https://de-linker.test/product/saj-h2-10k-t3/',
	images: [],
	is_in_stock: true,
};

function card(
	products: ( ids: number[], locale: Locale ) => Promise< unknown[] >
) {
	render(
		<GenieCard
			productId={ 4107 }
			restUrl="/wp-json/"
			store={
				{
					products,
					addAll: vi.fn(),
				} as unknown as ReturnType< typeof storeClient >
			}
			locale="en"
			status={ { state: 'idle', text: '' } }
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

test( 'a read that returns no product is the same failure', async () => {
	card( async () => [] );

	expect( await screen.findByRole( 'alert' ) ).toHaveTextContent(
		'Genie could not load this product.'
	);
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
