/**
 * The card's feedback line is always there, so feedback never moves the layout.
 */

/**
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import { ProductCard } from './ProductCard';

test( 'the status line exists before, during and after an action', () => {
	const props = {
		id: 'c',
		role: 'Hybrid inverter',
		title: 'GoodWe GW10K-ETA-G20',
		model: 'Model GW10K-ETA-G20',
	};
	const { rerender } = render( <ProductCard { ...props } /> );
	expect( screen.getByRole( 'status' ) ).toHaveTextContent( '' );
	rerender(
		<ProductCard
			{ ...props }
			status={ { state: 'pending', text: 'Adding…' } }
		/>
	);
	expect(
		screen.getByRole( 'article', { name: 'GoodWe GW10K-ETA-G20' } )
	).toHaveAttribute( 'data-state', 'pending' );
	rerender(
		<ProductCard
			{ ...props }
			status={ { state: 'retry', text: 'Not added. Try again.' } }
		/>
	);
	expect( screen.getByRole( 'status' ) ).toHaveTextContent(
		'Not added. Try again.'
	);
} );
