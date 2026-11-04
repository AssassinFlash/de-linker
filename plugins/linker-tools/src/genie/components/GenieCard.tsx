/**
 * A product card of the answer, with its actions inside the card
 * (docs/specs/13-genie.md). Display data comes from the Store API; the model
 * name comes from the get-product ability, so the card names the model and
 * never `#<id>`; the price line comes with the answer, filled by the service
 * for this customer's account (#242).
 */

/**
 * External dependencies
 */
import { useEffect, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { ProductCard, type CardState } from '../../shared/ProductCard';
import type { storeClient } from '../../configurator/api/store';
import type { StoreProduct } from '../../configurator/types';
import { productModel } from '../api/product';
import type { CardPrice } from '../api/turn';

/**
 * The card's price line (#242), exactly as the service filled it: the product
 * page's own line for this customer, already in the page's language (the price,
 * or the page's sentence when `reason` says why there is none). The shell words
 * nothing itself.
 *
 * @param price The line the service filled; undefined when it filled none.
 */
export function priceLine(
	price: CardPrice | undefined
): { text: string; kind: 'net' | 'note' } | undefined {
	if ( ! price?.text ) {
		return undefined;
	}
	return { text: price.text, kind: price.reason ? 'note' : 'net' };
}

/**
 * The card's own content load, separate from the card-action feedback
 * (`CardState`): pending is not loaded-empty is not failed (#901). The same
 * shape as draftContext's phase and RoofStep's Status union. The state is
 * keyed by the requested product id: a re-render that re-runs the effect
 * keeps the loaded card on screen instead of flashing back to pending, the
 * way the former single `StoreProduct | null` did. `loading` carries no live
 * region: a live region would announce the wait, and only a true failure is
 * announced (`role="alert"`).
 */
type Load =
	| { id: number; phase: 'loading' }
	| { id: number; phase: 'ready'; product: StoreProduct }
	| { id: number; phase: 'failed' };

export function GenieCard( {
	productId,
	restUrl,
	store,
	locale,
	status,
	price,
	onAdd,
	onSave,
}: {
	productId: number;
	restUrl: string;
	store: ReturnType< typeof storeClient >;
	locale: string;
	status: { state: CardState; text: string };
	price?: CardPrice;
	onAdd: ( productId: number ) => void;
	onSave: ( productId: number, title: string ) => void;
} ) {
	const [ load, setLoad ] = useState< Load >( {
		id: productId,
		phase: 'loading',
	} );
	const [ model, setModel ] = useState( '' );

	useEffect( () => {
		let alive = true;
		store
			.products( [ productId ], locale as 'en' | 'de' )
			.then( ( [ first ] ) => {
				if ( ! alive ) {
					return;
				}
				setLoad(
					first
						? { id: productId, phase: 'ready', product: first }
						: { id: productId, phase: 'failed' }
				);
			} )
			.catch( () => {
				if ( alive ) {
					setLoad( { id: productId, phase: 'failed' } );
				}
			} );
		productModel( restUrl, productId, locale as 'en' | 'de' )
			.then( ( name ) => {
				if ( alive ) {
					setModel( name );
				}
			} )
			.catch( () => {
				// The model line is optional decoration; a failed read just
				// leaves it empty, the card still renders.
			} );
		return () => {
			alive = false;
		};
	}, [ productId, restUrl, store, locale ] );

	if ( load.id !== productId || 'loading' === load.phase ) {
		return null;
	}
	if ( 'failed' === load.phase ) {
		return (
			<p className="linker-genie-app__missing" role="alert">
				{ __( 'Genie could not load this product.', 'linker-tools' ) }
			</p>
		);
	}
	const product = load.product;
	const modelText = model
		? `${ __( 'Model', 'linker-tools' ) } ${ model }`
		: '';
	return (
		<ProductCard
			id={ `linker-genie-card-${ productId }` }
			role={ __( 'Product', 'linker-tools' ) }
			title={ product.name }
			model={ modelText }
			price={ priceLine( price ) }
			url={ product.permalink }
			image={ product.images[ 0 ] }
			badges={ [
				product.is_in_stock
					? {
							tone: 'ok' as const,
							text: __( 'In stock', 'linker-tools' ),
						}
					: {
							tone: 'warn' as const,
							text: __( 'Currently unavailable', 'linker-tools' ),
						},
			] }
			status={ status }
			actions={ [
				<button
					key="draft"
					type="button"
					className="linker-genie-app__card-action linker-genie-app__card-action--primary"
					disabled={ 'pending' === status.state }
					onClick={ () => onAdd( productId ) }
				>
					{ __( 'Add to solution draft', 'linker-tools' ) }
				</button>,
				<button
					key="save"
					type="button"
					className="linker-genie-app__card-action"
					disabled={ 'pending' === status.state }
					onClick={ () => onSave( productId, product.name ) }
				>
					{ __( 'Save solution', 'linker-tools' ) }
				</button>,
			] }
		/>
	);
}
