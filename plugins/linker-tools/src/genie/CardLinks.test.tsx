/**
 * A Genie card links to the product page of its own language (#413, #339
 * s1-card-permalink-locale). The link is the Store API permalink for the
 * locale the card asked with. The price line is the one the service filled
 * for that account; it does not choose the link.
 */

/**
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { storeClient } from '../configurator/api/store';
import type { CardPrice } from './api/turn';
import { GenieCard } from './components/GenieCard';

vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'H2-10K-T3' ),
} ) );

const LINKS = {
	en: 'https://de-linker.test/product/saj-h2-10k-t3/',
	de: 'https://de-linker.test/de/produkt/saj-h2-10k-t3/',
} as const;

const ACCOUNTS: {
	state: 'approved' | 'pending' | 'restricted' | 'guest';
	locale: 'en' | 'de';
	price: CardPrice;
}[] = [
	{
		state: 'approved',
		locale: 'en',
		price: { product_id: 4107, text: '€1,680.00' },
	},
	{
		state: 'approved',
		locale: 'de',
		price: { product_id: 4107, text: '1.680,00 €' },
	},
	{
		state: 'pending',
		locale: 'en',
		price: {
			product_id: 4107,
			text: 'Account under review. Prices after approval.',
			reason: 'pending',
		},
	},
	{
		state: 'pending',
		locale: 'de',
		price: {
			product_id: 4107,
			text: 'Ihr Konto wird geprüft. Preise nach Freigabe.',
			reason: 'pending',
		},
	},
	{
		state: 'restricted',
		locale: 'en',
		price: {
			product_id: 4107,
			text: 'Not available for your account',
			reason: 'restricted',
		},
	},
	{
		state: 'restricted',
		locale: 'de',
		price: {
			product_id: 4107,
			text: 'Für Ihr Konto nicht verfügbar',
			reason: 'restricted',
		},
	},
	{
		state: 'guest',
		locale: 'en',
		price: {
			product_id: 4107,
			text: 'Net price after partner sign-in',
			reason: 'login',
		},
	},
	{
		state: 'guest',
		locale: 'de',
		price: {
			product_id: 4107,
			text: 'Nettopreis nach Partner-Anmeldung',
			reason: 'login',
		},
	},
];

test.each( ACCOUNTS )(
	'a $state $locale card links to that language’s product page',
	async ( { locale, price } ) => {
		const products = vi.fn( async ( ids: number[], asked: 'en' | 'de' ) => [
			{
				id: ids[ 0 ],
				name: 'SAJ H2-10K-T3',
				permalink: LINKS[ asked ],
				images: [ { src: 'https://img/h2.png', alt: '' } ],
				is_in_stock: true,
			},
		] );
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
				locale={ locale }
				status={ { state: 'idle', text: '' } }
				price={ price }
				onAdd={ vi.fn() }
				onSave={ vi.fn() }
			/>
		);

		const link = await screen.findByRole( 'link', {
			name: 'SAJ H2-10K-T3',
		} );
		expect( link ).toHaveAttribute( 'href', LINKS[ locale ] );
		expect( products ).toHaveBeenCalledWith( [ 4107 ], locale );
		expect( screen.getByText( price.text ) ).toBeInTheDocument();
	}
);
