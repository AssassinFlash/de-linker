import {
	installNativeIdentityFixture,
	renderOwned,
} from './testing/nativeIdentity';
/**
 * The four card states inside the Genie thread: the card keeps its height and
 * the actions sit inside the card (docs/specs/13-genie.md; old ticket 191).
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen, within } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { CardState } from '../shared/ProductCard';
import type { storeClient } from '../configurator/api/store';

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
vi.mock( './api/solution', async ( importOriginal ) => ( {
	...( await importOriginal< typeof import( './api/solution' ) >() ),
	saveGenieSolution: vi.fn(),
} ) );
import { sendTurn } from './api/turn';
import { saveGenieSolution } from './api/solution';
import { App } from './App';
import type { GenieConfig } from './config';

const PRODUCT = {
	id: 3556,
	name: 'GoodWe GW10K-ETA',
	permalink: 'https://de-linker.test/product/gw10k-eta/',
	images: [ { src: 'https://img/gw10k.png', alt: '' } ],
	is_in_stock: true,
};

function storeDouble( addAll?: ReturnType< typeof vi.fn > ) {
	return {
		products: vi.fn( async () => [ PRODUCT ] ),
		addAll: addAll ?? vi.fn( async () => true ),
	} as unknown as ReturnType< typeof storeClient >;
}

// The store client is created inside the component; route it through a module
// mock so each test installs its own double.
let storeFactory: () => ReturnType< typeof storeClient > = () => storeDouble();
vi.mock( '../configurator/api/store', () => ( {
	storeClient: () => storeFactory(),
} ) );

function config(): GenieConfig {
	return {
		surface: 'helper',
		locale: 'en',
		pageType: 'category',
		productId: 0,
		page: { type: 'category' },
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
	};
}

async function openCardTurn(
	quantities: Record< string, number > = { 3556: 1 },
	proof = quantities[ 3556 ] ? 'signed-two' : ''
) {
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
				type: 'cards',
				product_ids: [ 3556 ],
				quantities,
				draft_proofs: proof ? { 3556: proof } : {},
			},
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: 'recommend an inverter' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	await screen.findByRole( 'article' );
}

const STATES: [ CardState, string ][] = [
	[ 'pending', 'Adding…' ],
	[ 'added', 'In your solution draft.' ],
	[ 'unverified', 'Addition not confirmed.' ],
	[ 'retry', 'Not added. Try again.' ],
];

installNativeIdentityFixture();

test( 'the card walks every action state inside the card', async () => {
	let captured:
		| ( (
				id: number,
				status: 'pending' | 'added' | 'unverified' | 'retry'
		  ) => void )
		| null = null;
	const addAll = vi.fn(
		async (
			_lines: unknown[],
			onStatus: (
				id: number,
				status: 'pending' | 'added' | 'unverified' | 'retry'
			) => void
		) => {
			captured = onStatus;
			return true;
		}
	);
	storeFactory = () => storeDouble( addAll );
	await openCardTurn();
	const card = screen.getByRole( 'article' );
	fireEvent.click(
		within( card ).getByRole( 'button', {
			name: 'Add to solution draft',
		} )
	);
	expect( within( card ).getByRole( 'status' ) ).toBeInTheDocument();
	expect( captured ).not.toBeNull();
	for ( const [ state, text ] of STATES ) {
		act( () => {
			captured!( 3556, state as 'pending' );
		} );
		expect( card.getAttribute( 'data-state' ) ).toBe( state );
		expect( within( card ).getByText( text ) ).toBeInTheDocument();
	}
} );

const unresolvedCounts: Record< string, number >[] = [ { 3556: 0 }, {} ];
test.each( unresolvedCounts )(
	'an unresolved quantity leaves the product visible without draft or save actions (%j)',
	async ( quantities ) => {
		await openCardTurn( quantities );
		const card = within( screen.getByRole( 'article' ) );
		expect(
			card.getByRole( 'link', { name: PRODUCT.name } )
		).toBeVisible();
		for ( const name of [ 'Add to solution draft', 'Save solution' ] ) {
			expect(
				card.queryByRole( 'button', { name } )
			).not.toBeInTheDocument();
		}
	}
);

test( 'the customer sees and adds the quantity on the signed product card', async () => {
	const add = vi.fn( async () => true );
	storeFactory = () => storeDouble( add );
	await openCardTurn( { 3556: 2 } );
	const card = within( screen.getByRole( 'article' ) );
	expect( card.getByText( '× 2' ) ).toBeVisible();
	fireEvent.click(
		card.getByRole( 'button', { name: 'Add to solution draft' } )
	);
	expect( add ).toHaveBeenCalledWith(
		[ { productId: 3556, quantity: 2 } ],
		expect.any( Function ),
		{ kind: 'genie', token: 'signed-two' }
	);
} );

test( 'a failed save shows the retry sentence inside the card', async () => {
	vi.mocked( saveGenieSolution ).mockRejectedValue( new Error( 'save 500' ) );
	storeFactory = () => storeDouble();
	await openCardTurn();
	const card = screen.getByRole( 'article' );
	fireEvent.click(
		within( card ).getByRole( 'button', { name: 'Save solution' } )
	);
	await within( card ).findByText( 'Not saved. Try again.' );
	expect( card.getAttribute( 'data-state' ) ).toBe( 'retry' );
} );

test( 'two recommendation blocks load both brands in one request that survives editing the next question', async () => {
	const products = vi.fn( async ( ids: number[] ) =>
		ids.map( ( id ) => ( {
			id,
			name: 'Equipment ' + id,
			permalink: '/product/' + id,
			images: [],
			is_in_stock: true,
		} ) )
	);
	storeFactory = () => ( { ...storeDouble(), products } );
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: null,
		blocks: [
			{
				type: 'cards',
				product_ids: [ 3556 ],
				prices: [ { product_id: 3556, text: 'First price line' } ],
			},
			{
				type: 'cards',
				product_ids: [ 3556, 4107 ],
				prices: [ { product_id: 4107, text: 'Second price line' } ],
			},
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	const input = await screen.findByLabelText( 'Ask Genie' );
	fireEvent.change( input, { target: { value: 'compare both brands' } } );
	fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	await screen.findByRole( 'link', { name: 'Equipment 4107' } );
	expect( screen.getByText( 'Second price line' ) ).toBeVisible();
	fireEvent.change( input, { target: { value: 'follow up' } } );
	expect( products ).toHaveBeenCalledExactlyOnceWith( [ 3556, 4107 ], 'en' );
} );

test( 'historical product cards keep their quantity and details after the write proof is gone', async () => {
	storeFactory = () => storeDouble();
	await openCardTurn( { 3556: 2 }, '' );
	const card = within( screen.getByRole( 'article' ) );
	expect( card.getByText( '× 2' ) ).toBeVisible();
	expect( card.getByRole( 'link', { name: PRODUCT.name } ) ).toBeVisible();
	expect(
		card.queryByRole( 'button', { name: 'Add to solution draft' } )
	).toBeNull();
	expect(
		card.queryByRole( 'button', { name: 'Save solution' } )
	).toBeNull();
} );
