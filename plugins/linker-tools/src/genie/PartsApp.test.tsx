import {
	installNativeIdentityFixture,
	renderOwned,
} from './testing/nativeIdentity';
/**
 * The parts list inside the dock (#251): the service's block reaches the card,
 * and its one button calls the store once with every confirmed row.
 */

/**
 * External dependencies
 */
import { act, fireEvent, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
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
import { App } from './App';
import type { GenieConfig } from './config';

const addAll = vi.fn( async () => true );

vi.mock( '../configurator/api/store', () => ( {
	storeClient: () =>
		( {
			products: vi.fn( async () => [] ),
			addAll,
		} ) as unknown as ReturnType< typeof storeClient >,
} ) );

function config(): GenieConfig {
	return {
		surface: 'helper',
		locale: 'en',
		pageType: 'other',
		productId: 0,
		page: { type: 'other' },
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

installNativeIdentityFixture();

test( 'the parts block reaches the card and its add is one store call', async () => {
	vi.mocked( sendTurn ).mockResolvedValue( {
		meta: {
			grounded: true,
			fallback: false,
			attempts: 0,
			failures: [],
			language: 'en',
		},
		blocks: [
			{
				type: 'text',
				text: 'I checked your list.',
				refs: [],
			},
			{
				type: 'parts',
				ask_line: null,
				rows: [
					{
						line: 1,
						text: 'SAJ H2-10K-T3',
						quantity: 2,
						status: 'matched',
						product_id: 4107,
						label: 'H2-10K-T3',
					},
					{
						line: 2,
						text: 'GoodWe GW10K-ETA-G20',
						quantity: 3,
						status: 'matched',
						product_id: 3556,
						label: 'GW10K-ETA-G20',
					},
				],
				add: {
					items: [
						{ product_id: 4107, quantity: 2 },
						{ product_id: 3556, quantity: 3 },
					],
					products: 2,
					rows: 2,
				},
			},
		],
	} );
	await renderOwned( <App config={ config() } /> );
	fireEvent.click( screen.getByRole( 'button', { name: 'Open' } ) );
	await act( async () => {
		fireEvent.change( screen.getByLabelText( 'Ask Genie' ), {
			target: { value: '2x SAJ H2-10K-T3\n3 x GoodWe GW10K-ETA-G20' },
		} );
		fireEvent.click( screen.getByRole( 'button', { name: 'Send' } ) );
	} );
	const add = await screen.findByRole( 'button', {
		name: 'Add 2 products to the solution draft',
	} );
	fireEvent.click( add );
	expect( addAll ).toHaveBeenCalledTimes( 1 );
	expect( addAll ).toHaveBeenCalledWith(
		[
			{ productId: 4107, quantity: 2 },
			{ productId: 3556, quantity: 3 },
		],
		expect.any( Function ),
		{ kind: 'genie', token: '' }
	);
} );
