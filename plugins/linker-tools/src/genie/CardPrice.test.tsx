import {
	installNativeIdentityFixture,
	renderOwned,
} from './testing/nativeIdentity';
/**
 * Prices follow the account (#242, docs/specs/13-genie.md 目标 8): the card
 * renders the price line the service filled from the customer's own product
 * ability — the price as the product page prints it for an approved partner
 * account, the product page's own sentence for everybody else — word for word;
 * it holds no sentence of its own.
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen, within } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { storeClient } from '../configurator/api/store';
import type { CardPrice } from './api/turn';

vi.mock( './api/turn', async ( importOriginal ) => {
	const actual = await importOriginal< typeof import( './api/turn' ) >();
	return {
		assistantMessage: actual.assistantMessage,
		readThread: vi.fn( async () => ( { messages: [], turn: null } ) ),
		listConversations: vi.fn( async () => ( {
			currentId: 0,
			conversations: [],
			ok: true,
		} ) ),
		selectConversation: vi.fn(),
		sendTurn: vi.fn(),
		sendVote: vi.fn( async () => true ),
	};
} );
vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'H2-10K-T3' ),
} ) );
vi.mock( '../configurator/api/store', () => ( {
	storeClient: () =>
		( {
			products: vi.fn( async () => [
				{
					id: 4107,
					name: 'SAJ H2-10K-T3 (10 kW three-phase hybrid inverter)',
					permalink: 'https://de-linker.test/product/saj-h2-10k-t3/',
					images: [ { src: 'https://img/h2.png', alt: '' } ],
					is_in_stock: true,
				},
			] ),
			addAll: vi.fn( async () => true ),
		} ) as unknown as ReturnType< typeof storeClient >,
} ) );
import { sendTurn } from './api/turn';
import { App } from './App';
import type { GenieConfig } from './config';

function config(): GenieConfig {
	return {
		surface: 'helper',
		locale: 'en',
		pageType: 'product',
		productId: 4107,
		page: { type: 'product', product_id: 4107 },
		turnUrl: '/wp-json/linker-ai/v1/genie/turn',
		threadUrl: '/wp-json/linker-ai/v1/genie/conversation',
		conversationsUrl: '/wp-json/linker-ai/v1/genie/conversations',
		voteUrl: '/wp-json/linker-ai/v1/genie/turn',
		restUrl: '/wp-json/',
		restNonce: 'n',
		disclosure: "Hi, I'm Genie.",
		accountUrl: '/my-account/',
		workspaceUrl: '/genie/',
		contactUrl: '/wp-json/linker-ai/v1/genie/contact',
		inquiryUrl: '/wp-json/linker-ai/v1/genie/inquiry',
		prompts: [],
		signedIn: false,
		retentionDays: 90,
		mailStarted: '1800000000',
		mailStartedNonce: 'stamp-nonce',
	};
}

async function cardWith( prices: CardPrice[] | null ) {
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [
			{
				type: 'text',
				text: 'Its card shows the price.',
				refs: [ '4107' ],
			},
			{ type: 'cards', product_ids: [ 4107 ], prices },
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'What does the H2-10K-T3 cost?' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	return screen.findByRole( 'article' );
}

// What the service sends: the product page's own line for the account, in the
// page's language (linker-commerce ProductView), and why there is no price.
test.each( [
	[ 'login', 'Net price after partner sign-in' ],
	[ 'pending', 'Preise nach Freigabe' ],
	[ 'restricted', 'Not available for your account' ],
	[ 'project', 'Angebot pro Projekt' ],
	[ 'unpriced', 'Price on request' ],
] as const )(
	'a card without a price shows the line the service sent (%s)',
	async ( reason, sentence ) => {
		const card = await cardWith( [
			{ product_id: 4107, text: sentence, reason },
		] );
		const line = within( card ).getByText( sentence );
		expect( line ).toHaveClass( 'linker-card__price--note' );
		expect( within( card ).queryByText( /€/ ) ).toBeNull();
	}
);

installNativeIdentityFixture();

test( 'an approved account reads the price as the product page prints it', async () => {
	const card = await cardWith( [ { product_id: 4107, text: '1.680,00 €' } ] );
	expect( within( card ).getByText( '1.680,00 €' ) ).toHaveClass(
		'linker-card__price--net'
	);
} );

test( 'a card the service did not price shows no price line', async () => {
	const card = await cardWith( null );
	expect( card.querySelector( '.linker-card__price' ) ).toBeNull();
} );
