/**
 * The Genie card states stock the way the product page does (#415):
 * "In stock" or "Currently unavailable", never a blank badge.
 */

/**
 * External dependencies
 */
import { act, render, screen } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';

/**
 * WordPress dependencies
 */
import { resetLocaleData, setLocaleData } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import germanGenie from '../../languages/linker-tools-de_DE_formal-c2be3a742ec1f5e619cd2beb8d234138.json';
import type { storeClient } from '../configurator/api/store';
import { GenieCard } from './components/GenieCard';

vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'H2-10K-T3' ),
} ) );

afterEach( () => {
	resetLocaleData( {}, 'linker-tools' );
} );

function store( inStock: boolean ): ReturnType< typeof storeClient > {
	return {
		products: vi.fn( async () => [
			{
				id: 4107,
				name: 'SAJ H2-10K-T3',
				permalink: 'https://de-linker.test/product/saj-h2-10k-t3/',
				images: [],
				is_in_stock: inStock,
			},
		] ),
	} as unknown as ReturnType< typeof storeClient >;
}

async function card( inStock: boolean, locale: 'en' | 'de' ) {
	await act( async () => {
		render(
			<GenieCard
				productId={ 4107 }
				restUrl="/wp-json/"
				store={ store( inStock ) }
				locale={ locale }
				status={ { state: 'idle', text: '' } }
				onAdd={ () => undefined }
				onSave={ () => undefined }
			/>
		);
	} );
}

test( 'an in-stock card says In stock', async () => {
	await card( true, 'en' );
	const badge = screen.getByText( 'In stock' );
	expect( badge.className ).toContain( 'linker-card__badge--ok' );
	expect( screen.queryByText( 'Currently unavailable' ) ).toBeNull();
} );

test( 'an out-of-stock card says Currently unavailable', async () => {
	await card( false, 'en' );
	const badge = screen.getByText( 'Currently unavailable' );
	expect( badge.className ).toContain( 'linker-card__badge--warn' );
	expect( screen.queryByText( 'In stock' ) ).toBeNull();
} );

test( 'the German card uses the product-page stock words', async () => {
	setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
	await card( true, 'de' );
	expect( screen.getByText( 'Auf Lager' ).className ).toContain(
		'linker-card__badge--ok'
	);
	expect( screen.queryByText( 'In stock' ) ).toBeNull();
} );

test( 'the German out-of-stock card says Derzeit nicht verfügbar', async () => {
	setLocaleData( germanGenie.locale_data.messages, 'linker-tools' );
	await card( false, 'de' );
	const badge = screen.getByText( 'Derzeit nicht verfügbar' );
	expect( badge.className ).toContain( 'linker-card__badge--warn' );
	expect( screen.queryByText( 'Currently unavailable' ) ).toBeNull();
} );
