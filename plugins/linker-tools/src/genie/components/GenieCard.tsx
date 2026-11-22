/**
 * A product card of the answer, with its actions inside the card
 * (docs/specs/13-genie.md). Display data and product identity come from one Store API list.
 * The price line comes with the answer, filled by the service
 * for this customer's account (#242).
 */

/**
 * External dependencies
 */
import { useEffect, useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import { ProductCard, type CardState } from '../../shared/ProductCard';
import type { storeClient } from '../../configurator/api/store';
import type { Locale, StoreProduct } from '../../configurator/types';
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

interface CardActions {
	onAdd: ( id: number, quantity: number ) => void;
	onSave: ( id: number, title: string ) => void;
}

interface GenieCardsProps extends CardActions {
	products: number[];
	store: ReturnType< typeof storeClient >;
	locale: Locale;
	prices?: CardPrice[];
	quantities?: Record< string, number >;
	statusFor: ( id: number ) => { state: CardState; text: string };
}

export function GenieCards( {
	products,
	store,
	locale,
	prices,
	quantities,
	statusFor,
	onAdd,
	onSave,
}: GenieCardsProps ) {
	const [ attempt, setAttempt ] = useState( 0 );
	const [ result, setResult ] = useState< {
		products: number[];
		locale: Locale;
		attempt: number;
		rows: StoreProduct[] | null;
	} >();
	useEffect( () => {
		let active = true;
		store.products( products, locale ).then(
			( rows ) => {
				if ( active ) {
					setResult( { products, locale, attempt, rows } );
				}
			},
			() => {
				if ( active ) {
					setResult( { products, locale, attempt, rows: null } );
				}
			}
		);
		return () => {
			active = false;
		};
	}, [ products, store, locale, attempt ] );
	if (
		result?.products !== products ||
		result.locale !== locale ||
		result.attempt !== attempt
	) {
		return null;
	}
	if ( result.rows === null ) {
		return (
			<div className="linker-product-card" role="alert">
				<span>
					{ __(
						'Genie could not load this product.',
						'linker-tools'
					) }
				</span>
				<button
					type="button"
					className="linker-genie-app__card-action"
					onClick={ () => setAttempt( ( a ) => a + 1 ) }
				>
					{ __( 'Try again', 'linker-tools' ) }
				</button>
			</div>
		);
	}
	const rows = new Map(
		result.rows.map( ( product ) => [ product.id, product ] )
	);
	return (
		<>
			{ products.map( ( id ) => {
				const product = rows.get( id );
				if ( ! product ) {
					return (
						<p key={ id } className="linker-product-card">
							{ __( 'Currently unavailable', 'linker-tools' ) }
						</p>
					);
				}
				return (
					<GenieCard
						key={ id }
						product={ product }
						quantity={ quantities?.[ id ] }
						status={ statusFor( id ) }
						price={ prices?.find( ( p ) => p.product_id === id ) }
						onAdd={ onAdd }
						onSave={ onSave }
					/>
				);
			} ) }
		</>
	);
}

function GenieCard( {
	product,
	quantity,
	status,
	price,
	onAdd,
	onSave,
}: CardActions & {
	product: StoreProduct;
	quantity?: number;
	status: { state: CardState; text: string };
	price?: CardPrice;
} ) {
	const productId = product.id;
	const term = ( taxonomy: string ) => {
		const terms = product.attributes?.find(
			( attribute ) => attribute.taxonomy === taxonomy
		)?.terms;
		return terms?.length === 1 ? terms[ 0 ].name : '';
	};
	const model = term( 'pa_model' );
	const brand = term( 'pa_brand' );
	const series = term( 'pa_series' );
	const shortSeries =
		brand && series.startsWith( brand + ' ' )
			? series.slice( brand.length + 1 )
			: series;
	const identity = [ brand, shortSeries ].filter( Boolean ).join( ' · ' );

	return (
		<ProductCard
			id={ `linker-genie-card-${ productId }` }
			role={ identity || __( 'Product', 'linker-tools' ) }
			title={ model || product.name }
			linkLabel={ model ? product.name : undefined }
			model=""
			quantity={
				quantity
					? sprintf(
							/* translators: %d is the product quantity. */
							__( '× %d', 'linker-tools' ),
							quantity
						)
					: undefined
			}
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
			actions={
				quantity !== 0 && [
					<button
						key="draft"
						type="button"
						className="linker-genie-app__card-action linker-genie-app__card-action--primary"
						disabled={ 'pending' === status.state }
						onClick={ () => onAdd( productId, quantity ?? 1 ) }
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
				]
			}
		/>
	);
}
