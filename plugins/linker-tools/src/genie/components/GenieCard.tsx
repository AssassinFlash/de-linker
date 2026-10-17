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
 * The card's price line (#242): the price as the service filled it, or the
 * sentence the product page shows in its place, word for word (linker-commerce
 * ProductView and PriceDisplay; German in the same words as there).
 *
 * @param price The line the service filled; undefined when it filled none.
 */
export function priceLine(
	price: CardPrice | undefined
): { text: string; kind: 'net' | 'note' } | undefined {
	if ( price?.text ) {
		return { text: price.text, kind: 'net' };
	}
	switch ( price?.reason ) {
		case 'login':
			return {
				text: __( 'Net price after partner sign-in', 'linker-tools' ),
				kind: 'note',
			};
		case 'pending':
			return {
				text: __( 'Prices after approval', 'linker-tools' ),
				kind: 'note',
			};
		case 'restricted':
			return {
				text: __( 'Not available for your account', 'linker-tools' ),
				kind: 'note',
			};
		case 'project':
			return {
				text: __( 'Quoted per project', 'linker-tools' ),
				kind: 'note',
			};
		case 'unpriced':
			return {
				text: __( 'Price on request', 'linker-tools' ),
				kind: 'note',
			};
		default:
			return undefined;
	}
}

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
	const [ product, setProduct ] = useState< StoreProduct | null >( null );
	const [ model, setModel ] = useState( '' );

	useEffect( () => {
		let alive = true;
		store
			.products( [ productId ], locale as 'en' | 'de' )
			.then( ( [ first ] ) => {
				if ( alive && first ) {
					setProduct( first );
				}
			} );
		productModel( restUrl, productId, locale as 'en' | 'de' ).then(
			( name ) => {
				if ( alive ) {
					setModel( name );
				}
			}
		);
		return () => {
			alive = false;
		};
	}, [ productId, restUrl, store, locale ] );

	if ( ! product ) {
		return (
			<p className="linker-genie-app__missing">
				{ __( 'Genie could not load this product.', 'linker-tools' ) }
			</p>
		);
	}
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
			badges={
				product.is_in_stock
					? [
							{
								tone: 'ok' as const,
								text: __( 'In stock', 'linker-tools' ),
							},
						]
					: []
			}
			status={ status }
			actions={ [
				<button
					key="draft"
					type="button"
					className="linker-genie-app__card-action"
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
