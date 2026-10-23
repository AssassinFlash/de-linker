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
import { SolutionWriteError } from '../../configurator/api/solutions';
import { saveGenieSolution, GenieSaveUnconfirmedError } from '../api/solution';
import { additionStatusText } from '../../configurator/publication';
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
		async ( productId: number, token = '' ) => {
			status( productId, 'pending', __( 'Adding…', 'linker-tools' ) );
			await store.addAll(
				[ { productId, quantity: 1 } ],
				( id, state ) =>
					status(
						id,
						state === 'stale' ? 'retry' : state,
						{
							pending: __( 'Adding…', 'linker-tools' ),
							added: __(
								'In your solution draft.',
								'linker-tools'
							),
							unverified: additionStatusText(),
							retry: __(
								'Not added. Try again.',
								'linker-tools'
							),
							stale: __(
								'Genie needs to check this product list again before it can be saved or added.',
								'linker-tools'
							),
						}[ state ]
					),
				{ kind: 'genie', token }
			);
		},
		[ status, store ]
	);

	// A parts list's one write (#251): every confirmed row in one `store.addAll`
	// call, which adds each line through the Store API and reads the draft back
	// (configurator/api/store.ts). The card shows the worst outcome of the lines.
	const addPartsToDraft = useCallback(
		async (
			items: { product_id: number; quantity: number }[],
			token = ''
		): Promise< PartsAddResult > => {
			let result: PartsAddResult = 'added';
			const complete = await store.addAll(
				items.map( ( item ) => ( {
					productId: item.product_id,
					quantity: item.quantity,
				} ) ),
				( _id, state ) => {
					if ( state === 'stale' ) {
						result = 'stale';
					} else if ( state === 'retry' && result !== 'stale' ) {
						result = 'retry';
					} else if (
						state === 'unverified' &&
						result !== 'retry' &&
						result !== 'stale'
					) {
						result = 'unverified';
					}
				},
				{ kind: 'genie', token }
			);
			return complete && result === 'added' ? 'added' : result;
		},
		[ store ]
	);

	const saveCardSolution = useCallback(
		async ( productId: number, _title: string, token = '' ) => {
			status( productId, 'pending', __( 'Saving…', 'linker-tools' ) );
			try {
				await saveGenieSolution( restUrl, restNonce, token, locale );
				status(
					productId,
					'added',
					__( 'Saved to your account.', 'linker-tools' )
				);
			} catch ( error ) {
				if ( error instanceof GenieSaveUnconfirmedError ) {
					status(
						productId,
						'unverified',
						__(
							'The request status could not be confirmed. Please check before sending it again.',
							'linker-tools'
						)
					);
					return;
				}
				status(
					productId,
					'retry',
					error instanceof SolutionWriteError && error.changed
						? __(
								'Genie needs to check this product list again before it can be saved or added.',
								'linker-tools'
							)
						: __( 'Not saved. Try again.', 'linker-tools' )
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
