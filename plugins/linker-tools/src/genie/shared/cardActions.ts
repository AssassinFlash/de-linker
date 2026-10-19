/**
 * The actions inside a product card (ticket #232 review round 1, item 4):
 * add to the solution draft and save a solution, with the card's own status
 * line. One hook for the dock (App.tsx) and the home hero (Hero.tsx), so the
 * two surfaces cannot word or time the states differently.
 */

/**
 * WordPress dependencies
 */
import { useCallback, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { saveSolution } from '../../configurator/api/solutions';
import type { storeClient } from '../../configurator/api/store';
import type { Locale } from '../../configurator/types';
import type { PartsAddResult } from '../components/PartsCard';
import type { CardState } from '../../shared/ProductCard';

export interface CardItem {
	productId: number;
	status: { state: CardState; text: string };
}

export interface CardActionsOptions {
	restUrl: string;
	restNonce: string;
	locale: Locale;
	store: ReturnType< typeof storeClient >;
}

/**
 * The card statuses and their two actions.
 *
 * @param options           The card context.
 * @param options.restUrl   The WordPress REST root.
 * @param options.restNonce A wp_rest nonce.
 * @param options.locale    The page language.
 * @param options.store     The Store API client.
 */
export function useCardActions( {
	restUrl,
	restNonce,
	locale,
	store,
}: CardActionsOptions ) {
	const [ cards, setCards ] = useState< CardItem[] >( [] );

	const status = useCallback(
		( productId: number, state: CardState, text: string ) => {
			setCards( ( items ) => {
				const found = items.some(
					( item ) => item.productId === productId
				);
				return found
					? items.map( ( item ) =>
							item.productId === productId
								? { ...item, status: { state, text } }
								: item
						)
					: [ ...items, { productId, status: { state, text } } ];
			} );
		},
		[]
	);

	const addToDraft = useCallback(
		async ( productId: number ) => {
			status( productId, 'pending', __( 'Adding…', 'linker-tools' ) );
			await store.addAll( [ { productId, quantity: 1 } ], ( id, state ) =>
				status(
					id,
					state,
					{
						pending: __( 'Adding…', 'linker-tools' ),
						added: __( 'In your solution draft.', 'linker-tools' ),
						unverified: __(
							'Sent, but the draft does not show it yet. Please check.',
							'linker-tools'
						),
						retry: __( 'Not added. Try again.', 'linker-tools' ),
					}[ state ]
				)
			);
		},
		[ status, store ]
	);

	// A parts list's one write (#251): every confirmed row in one `store.addAll`
	// call, which adds each line through the Store API and reads the draft back
	// (configurator/api/store.ts). The card shows the worst outcome of the lines.
	const addPartsToDraft = useCallback(
		async (
			items: { product_id: number; quantity: number }[]
		): Promise< PartsAddResult > => {
			let result: PartsAddResult = 'added';
			const complete = await store.addAll(
				items.map( ( item ) => ( {
					productId: item.product_id,
					quantity: item.quantity,
				} ) ),
				( _id, state ) => {
					if ( state === 'retry' ) {
						result = 'retry';
					} else if ( state === 'unverified' && result !== 'retry' ) {
						result = 'unverified';
					}
				}
			);
			return complete && result === 'added' ? 'added' : result;
		},
		[ store ]
	);

	const saveCardSolution = useCallback(
		async ( productId: number, title: string ) => {
			status( productId, 'pending', __( 'Saving…', 'linker-tools' ) );
			try {
				await saveSolution( restUrl, restNonce, {
					kind: 'residential',
					title,
					input: {
						locale,
						plz: '',
						annual_kwh: 0,
						pv_kwp: 0,
						phase: 3,
						backup: 'none',
						heat_pump: false,
						electric_vehicle: false,
					},
					lines: [ { productId, quantity: 1 } ],
				} );
				status(
					productId,
					'added',
					__( 'Saved to your account.', 'linker-tools' )
				);
			} catch {
				status(
					productId,
					'retry',
					__( 'Not saved. Try again.', 'linker-tools' )
				);
			}
		},
		[ restUrl, restNonce, locale, status ]
	);

	const statusFor = useCallback(
		( productId: number ) =>
			cards.find( ( item ) => item.productId === productId )?.status ?? {
				state: 'idle' as const,
				text: '',
			},
		[ cards ]
	);

	return { cards, statusFor, addToDraft, addPartsToDraft, saveCardSolution };
}
