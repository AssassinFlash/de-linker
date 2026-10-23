/**
 * The parts list card (#251): every row's state, the first unclear row's
 * question, and the one add that writes all confirmed rows to the draft.
 */

/**
 * External dependencies
 */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { expect, test, vi } from 'vitest';

/**
 * Internal dependencies
 */
import type { PartsBlock } from '../api/turn';
import { PartsCard } from './PartsCard';

const BLOCK: PartsBlock = {
	type: 'parts',
	ask_line: 3,
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
			text: 'SMA Sunny Boy 5.0',
			quantity: 1,
			status: 'missing',
		},
		{
			line: 3,
			text: 'SAJ H2',
			quantity: 4,
			status: 'uncertain',
			options: [
				{ product_id: 2063, label: 'H2-15K-T3' },
				{ product_id: 2064, label: 'H2-20K-T3' },
			],
		},
		{
			line: 4,
			text: 'GoodWe GW10K-ET',
			quantity: 2,
			status: 'uncertain',
		},
	],
};

// The service sends an add only when no row is uncertain (`parts.PartsList.add`):
// a settled list, never the block above with an open question.
const SETTLED: PartsBlock = {
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
			text: 'SAJ H2-15K-T3',
			quantity: 4,
			status: 'matched',
			product_id: 2063,
			label: 'H2-15K-T3',
		},
	],
	add: {
		items: [
			{ product_id: 4107, quantity: 2 },
			{ product_id: 2063, quantity: 4 },
		],
		products: 2,
		rows: 2,
	},
};

test( 'every row shows what code made of it and the first unclear row asks', () => {
	render(
		<PartsCard
			block={ BLOCK }
			onAsk={ vi.fn() }
			onAdd={ vi.fn( async () => 'added' as const ) }
			onTypeModel={ vi.fn() }
		/>
	);
	expect( screen.getByText( 'In our range: H2-10K-T3' ) ).toBeInTheDocument();
	expect( screen.getByText( 'Not in our range.' ) ).toBeInTheDocument();
	expect(
		screen.getByText( 'Which model does this line mean?' )
	).toBeInTheDocument();
	// The second unclear row waits while the first is asked.
	expect(
		screen.getByText( 'This line needs your confirmation.' )
	).toBeInTheDocument();
	// The second unclear row names no candidates of its own.
	expect(
		screen.queryByRole( 'button', { name: 'GW10K-ET' } )
	).not.toBeInTheDocument();
	// No write while a row is still open.
	expect(
		screen.queryByRole( 'button', { name: /Add .* solution draft/ } )
	).not.toBeInTheDocument();
} );

test( 'a candidate chip answers in the message the service reads', () => {
	const onAsk = vi.fn();
	render(
		<PartsCard
			block={ BLOCK }
			onAsk={ onAsk }
			onAdd={ vi.fn( async () => 'added' as const ) }
			onTypeModel={ vi.fn() }
		/>
	);
	fireEvent.click( screen.getByRole( 'button', { name: 'H2-15K-T3' } ) );
	expect( onAsk ).toHaveBeenCalledWith( 'Row 3: H2-15K-T3' );
	fireEvent.click( screen.getByRole( 'button', { name: 'Skip this line' } ) );
	expect( onAsk ).toHaveBeenLastCalledWith( 'Row 3: skip' );
	fireEvent.click( screen.getByRole( 'button', { name: 'Type the model' } ) );
} );

test( 'one click writes every confirmed row once', async () => {
	const onAdd = vi.fn( async () => 'added' as const );
	render(
		<PartsCard
			block={ SETTLED }
			onAsk={ vi.fn() }
			onAdd={ onAdd }
			onTypeModel={ vi.fn() }
		/>
	);
	fireEvent.click(
		screen.getByRole( 'button', {
			name: 'Add 2 products to the solution draft',
		} )
	);
	expect( onAdd ).toHaveBeenCalledTimes( 1 );
	expect( onAdd ).toHaveBeenCalledWith(
		[
			{ product_id: 4107, quantity: 2 },
			{ product_id: 2063, quantity: 4 },
		],
		undefined
	);
	expect(
		await screen.findByText( 'In your solution draft.' )
	).toBeInTheDocument();
} );

test( 'a failed write says so inside the card', async () => {
	render(
		<PartsCard
			block={ SETTLED }
			onAsk={ vi.fn() }
			onAdd={ vi.fn( async () => 'retry' as const ) }
			onTypeModel={ vi.fn() }
		/>
	);
	fireEvent.click(
		screen.getByRole( 'button', {
			name: 'Add 2 products to the solution draft',
		} )
	);
	expect(
		await screen.findByText( 'Not added. Try again.' )
	).toBeInTheDocument();
} );

test.each( [ 'added', 'unverified' ] as const )(
	'a %s parts-list write stays disabled but leaves the busy phase',
	async ( result ) => {
		let complete!: ( value: typeof result ) => void;
		const onAdd = vi.fn(
			() =>
				new Promise< typeof result >( ( resolve ) => {
					complete = resolve;
				} )
		);
		render(
			<PartsCard
				block={ SETTLED }
				onAsk={ vi.fn() }
				onAdd={ onAdd }
				onTypeModel={ vi.fn() }
			/>
		);
		const button = screen.getByRole( 'button', {
			name: 'Add 2 products to the solution draft',
		} );
		fireEvent.click( button );
		expect( button ).toBeDisabled();
		expect( button ).toHaveAttribute( 'aria-busy', 'true' );
		await act( async () => complete( result ) );
		expect( button ).toBeDisabled();
		expect( button ).not.toHaveAttribute( 'aria-busy' );
		fireEvent.click( button );
		expect( onAdd ).toHaveBeenCalledTimes( 1 );
	}
);
