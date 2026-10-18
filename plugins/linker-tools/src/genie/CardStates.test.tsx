/**
 * The four card states inside the Genie thread: the card keeps its height and
 * the actions sit inside the card (docs/specs/13-genie.md; old ticket 191).
 */

/**
 * External dependencies
 */
import { act, fireEvent, render, screen, within } from '@testing-library/react';
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
vi.mock( './api/product', () => ( {
	productModel: vi.fn( async () => 'GW10K-ETA' ),
} ) );
vi.mock( '../configurator/api/solutions', () => ( {
	saveSolution: vi.fn(),
} ) );
import { sendTurn } from './api/turn';
import { saveSolution } from '../configurator/api/solutions';
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
		mailStarted: '1800000000',
		mailStartedNonce: 'stamp-nonce',
	};
}

async function openCardTurn() {
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 1,
			failures: [],
			language: 'en',
		},
		blocks: [ { type: 'cards', product_ids: [ 3556 ] } ],
	} );
	render( <App config={ config() } /> );
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
	[ 'unverified', 'Sent, but the draft does not show it yet. Please check.' ],
	[ 'retry', 'Not added. Try again.' ],
];

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

test( 'a failed save shows the retry sentence inside the card', async () => {
	vi.mocked( saveSolution ).mockRejectedValue( new Error( 'save 500' ) );
	storeFactory = () => storeDouble();
	await openCardTurn();
	const card = screen.getByRole( 'article' );
	fireEvent.click(
		within( card ).getByRole( 'button', { name: 'Save solution' } )
	);
	await within( card ).findByText( 'Not saved. Try again.' );
	expect( card.getAttribute( 'data-state' ) ).toBe( 'retry' );
} );
