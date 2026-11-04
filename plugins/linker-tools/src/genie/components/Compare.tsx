/**
 * The comparison the turn asked for (docs/specs/13-genie.md: battery energy
 * and inverter output never share a row).
 */

/**
 * External dependencies
 */
import { useEffect, useState } from '@wordpress/element';
import { __ } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { storeClient } from '../../configurator/api/store';
import type { StoreProduct } from '../../configurator/types';

export function Compare( {
	products,
	store,
	locale,
}: {
	products: number[];
	store: ReturnType< typeof storeClient >;
	locale: string;
} ) {
	const [ rows, setRows ] = useState< StoreProduct[] >( [] );

	useEffect( () => {
		let alive = true;
		store
			.products( products, locale as 'en' | 'de' )
			.then( ( found ) => {
				if ( alive ) {
					setRows( found );
				}
			} )
			.catch( () => {
				// A refused Store API read keeps the table empty; the answer's
				// own error surface tells the customer what failed.
				if ( alive ) {
					setRows( [] );
				}
			} );
		return () => {
			alive = false;
		};
	}, [ products, store, locale ] );

	return (
		<table className="linker-genie-app__compare">
			<thead>
				<tr>
					<th scope="col">{ __( 'Model', 'linker-tools' ) }</th>
					{ rows.map( ( product ) => (
						<th key={ product.id } scope="col">
							{ product.name }
						</th>
					) ) }
				</tr>
			</thead>
			<tbody>
				<tr>
					<th scope="row">{ __( 'In stock', 'linker-tools' ) }</th>
					{ rows.map( ( product ) => (
						<td key={ product.id }>
							{ product.is_in_stock
								? __( 'Yes', 'linker-tools' )
								: __( 'On request', 'linker-tools' ) }
						</td>
					) ) }
				</tr>
			</tbody>
		</table>
	);
}
