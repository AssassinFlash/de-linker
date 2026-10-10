/**
 * A product card of the answer, with its actions inside the card
 * (docs/specs/13-genie.md). Display data comes from the Store API; the model
 * name comes from the get-product ability, so the card names the model and
 * never `#<id>`.
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

export function GenieCard( {
	productId,
	restUrl,
	store,
	locale,
	status,
	onAdd,
	onSave,
}: {
	productId: number;
	restUrl: string;
	store: ReturnType< typeof storeClient >;
	locale: string;
	status: { state: CardState; text: string };
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
