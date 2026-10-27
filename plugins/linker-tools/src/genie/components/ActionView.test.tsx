/**
 * open_configurator's link (#453): the tool returned the URL and it passed
 * grounding, so the shell links it in the same tab; without such a URL the
 * action links nowhere.
 */

/**
 * External dependencies
 */
import { render, screen } from '@testing-library/react';
import { expect, test } from 'vitest';

/**
 * Internal dependencies
 */
import type { ActionBlock } from '../api/turn';
import { ActionView } from './ActionView';

const CONFIGURATOR =
	'https://de-linker.com/solution-configurator/?pv_kwp=12&annual_kwh=6000';

function view( args: ActionBlock[ 'args' ], localized = false ) {
	return render(
		<ActionView
			block={ { type: 'action', name: 'open_configurator', args } }
			accountUrl="/my-account/"
			configuratorLinks={
				localized
					? {
							en: 'https://de-linker.com/solution-configurator/',
							de: 'https://de-linker.com/de/loesungskonfigurator/',
							current:
								'https://de-linker.com/de/loesungskonfigurator/',
						}
					: undefined
			}
		/>
	);
}

test( 'a grounded configurator link opens in the same tab', () => {
	view( { url: CONFIGURATOR } );
	const link = screen.getByRole( 'link', {
		name: 'Open the configurator',
	} );
	expect( link.getAttribute( 'href' ) ).toBe( CONFIGURATOR );
	expect( link.hasAttribute( 'target' ) ).toBe( false );
	const historical =
		CONFIGURATOR + '&project=abc&compare=one%2Ctwo#lp-calculations';
	const { unmount } = view( { url: historical }, true );
	expect( screen.getAllByRole( 'link' )[ 1 ].getAttribute( 'href' ) ).toBe(
		historical.replace(
			'/solution-configurator/',
			'/de/loesungskonfigurator/'
		)
	);
	unmount();
	const foreign = view(
		{ url: 'https://other.example/solution-configurator/?run=one' },
		true
	);
	expect( screen.getAllByRole( 'link' )[ 1 ].getAttribute( 'href' ) ).toBe(
		'https://other.example/solution-configurator/?run=one'
	);
	foreign.unmount();
} );

test( 'an open_configurator without a URL links nowhere', () => {
	const { container } = view( {} );
	expect( container.innerHTML ).toBe( '' );
} );

test( 'an open_configurator URL that is not a string links nowhere', () => {
	const { container } = view( { url: null } );
	expect( container.innerHTML ).toBe( '' );
} );
