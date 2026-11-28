import { genieFetch } from '../api/restFetch';
/** The same published selection facts and product identities as the catalog comparison. */
import { useEffect, useState } from '@wordpress/element';
import { __, sprintf } from '@wordpress/i18n';
import type { ReactNode } from 'react';
import type { CardState } from '../../shared/ProductCard';
import type { Locale } from '../types';
import { brandSeries } from '../shared/brandSeries';
import './catalog.css';

interface PairingDocument {
	title: string;
	url: string;
	page?: number;
}
interface Pairing {
	model: string;
	verdict: string;
	conditions: string[];
	accessories: string[];
	documents?: PairingDocument[];
}
interface Column {
	product_id: number;
	title: string;
	url: string;
	facts: { device_class: string };
	presentation: {
		model: string | null;
		brand: string | null;
		series: string | null;
		image: string;
		sku: string;
		storage: Pairing[];
		in_stock: boolean;
		in_draft: boolean;
		price_line: string;
		price_reason: string | null;
		datasheet: { title: string; url: string } | null;
	};
}
interface Spec {
	field: string;
	label: string;
	values: Record< string, string | number | { min: number; max: number } >;
}
interface Comparison {
	products: Column[];
	rows: Spec[];
}
interface Props {
	products: number[];
	locale: Locale;
	restUrl: string;
	nonce: string;
	proofs: Record< string, string >;
	quantities: Record< string, number >;
	statusFor: ( id: number ) => { state: CardState; text: string };
	onAdd: ( id: number, quantity: number ) => void;
}
function valueText(
	value: Spec[ 'values' ][ string ] | undefined,
	locale: Locale
): string {
	if ( value === undefined || value === 'unknown' ) {
		return '—';
	}
	const format = new Intl.NumberFormat( locale, {
		maximumFractionDigits: 6,
	} );
	if ( typeof value === 'number' ) {
		return format.format( value );
	}
	if ( typeof value === 'object' ) {
		return format.format( value.min ) + '–' + format.format( value.max );
	}
	if ( value === 'home' ) {
		return __( 'Residential', 'linker-tools' );
	}
	if ( value === 'commercial' ) {
		return __( 'Commercial', 'linker-tools' );
	}
	return value;
}

function unavailableComparison() {
	return (
		<p>
			{ __(
				'These products are no longer available for comparison.',
				'linker-tools'
			) }
		</p>
	);
}

export function Compare( props: Props ) {
	return props.products.length < 2 ? (
		unavailableComparison()
	) : (
		<PublishedComparison { ...props } />
	);
}

function PublishedComparison( {
	products,
	restUrl,
	nonce,
	locale,
	quantities,
	proofs,
	statusFor,
	onAdd,
}: Props ) {
	const [ attempt, retry ] = useState( 0 );
	const query = new URLSearchParams( {
		'input[lang]': locale,
		'input[presentation]': 'true',
	} );
	products.forEach( ( id ) =>
		query.append( 'input[product_ids][]', String( id ) )
	);
	const url =
		restUrl.replace( /\/?$/, '/' ) +
		'wp-abilities/v1/abilities/linker/compare-products/run?' +
		query;
	const [ result, setResult ] = useState< {
		url: string;
		nonce: string;
		attempt: number;
		data: Comparison | null;
	} >();
	useEffect( () => {
		const controller = new AbortController();
		async function load() {
			try {
				const response = await genieFetch( url, {
					credentials: 'same-origin',
					cache: 'no-store',
					headers: nonce ? { 'X-WP-Nonce': nonce } : undefined,
					signal: controller.signal,
				} );
				if ( ! response.ok ) {
					throw Error( String( response.status ) );
				}
				const data: Comparison = await response.json();
				if ( ! controller.signal.aborted ) {
					setResult( { url, nonce, attempt, data } );
				}
			} catch {
				if ( ! controller.signal.aborted ) {
					setResult( { url, nonce, attempt, data: null } );
				}
			}
		}
		void load();
		return () => controller.abort();
	}, [ url, nonce, attempt ] );
	if (
		result?.url !== url ||
		result.nonce !== nonce ||
		result.attempt !== attempt
	) {
		return <p>{ __( 'Loading comparison…', 'linker-tools' ) }</p>;
	}
	if ( ! result.data ) {
		return (
			<p role="alert">
				{ __( 'Could not load this comparison.', 'linker-tools' ) }{ ' ' }
				<button type="button" onClick={ () => retry( ( n ) => n + 1 ) }>
					{ __( 'Try again', 'linker-tools' ) }
				</button>
			</p>
		);
	}
	if ( ! result.data.products.length ) {
		return unavailableComparison();
	}
	const { products: columns, rows } = result.data;
	const groups = [
		{
			name: __( 'Inverters', 'linker-tools' ),
			columns: columns.filter( ( c ) =>
				[ 'inverters', 'all-in-one-systems' ].includes(
					c.facts.device_class
				)
			),
			keys: [ 'application', 'phase', 'ac_power_kw', 'pv_input_kw' ],
			storage: true,
		},
		{
			name: __( 'Battery storage', 'linker-tools' ),
			columns: columns.filter(
				( c ) =>
					[ 'home-storage', 'battery-systems' ].includes(
						c.facts.device_class
					) ||
					( c.facts.device_class === 'all-in-one-systems' &&
						rows.some(
							( row ) =>
								[
									'usable_kwh',
									'nominal_kwh',
									'kwh_range',
								].includes( row.field ) &&
								row.values[ c.product_id ] !== undefined &&
								row.values[ c.product_id ] !== 'unknown'
						) )
			),
			keys: [ 'application', 'usable_kwh', 'nominal_kwh', 'kwh_range' ],
			storage: false,
		},
		{
			name: __( 'Equipment', 'linker-tools' ),
			columns: columns.filter(
				( c ) =>
					! [
						'inverters',
						'all-in-one-systems',
						'home-storage',
						'battery-systems',
					].includes( c.facts.device_class )
			),
			keys: [ 'application' ],
			storage: false,
		},
	];
	return (
		<div className="genie-comparisons">
			{ groups
				.filter( ( group ) => group.columns.length > 0 )
				.map( ( group ) => (
					<SpecTable
						key={ group.name }
						group={ group }
						rows={ rows }
						locale={ locale }
						draftAction={ ( c ) => (
							<DraftButton
								column={ c }
								proof={ proofs[ c.product_id ] }
								quantity={ quantities[ c.product_id ] }
								status={ statusFor( c.product_id ) }
								onAdd={ onAdd }
							/>
						) }
					/>
				) ) }
		</div>
	);
}

function DraftButton( {
	column,
	proof,
	quantity,
	status,
	onAdd,
}: {
	column: Column;
	proof?: string;
	quantity?: number;
	status: ReturnType< Props[ 'statusFor' ] >;
	onAdd: Props[ 'onAdd' ];
} ) {
	const added =
		column.presentation.in_draft ||
		( status.state === 'added' &&
			status.text === __( 'In your solution draft.', 'linker-tools' ) );
	if ( ! added && ( ! quantity || ! proof ) ) {
		return (
			<a href={ column.url }>{ __( 'View product', 'linker-tools' ) }</a>
		);
	}
	return (
		<>
			<button
				type="button"
				className="genie-comparison__add"
				disabled={ added || status.state === 'pending' }
				onClick={ () => {
					if ( quantity && proof ) {
						onAdd( column.product_id, quantity );
					}
				} }
			>
				{ added
					? __( '✓ In draft', 'linker-tools' )
					: __( '+ Add to draft', 'linker-tools' ) }
			</button>
			{ status.text && ! added && (
				<small role="status">{ status.text }</small>
			) }
		</>
	);
}

function ModelHeading( { product }: { product: Column } ) {
	const { presentation: item } = product;
	return (
		<th scope="col">
			<a href={ product.url }>
				<span className="genie-comparison__brand">
					{ item.image && (
						<img
							alt=""
							src={ item.image }
							width={ 32 }
							height={ 32 }
						/>
					) }
					{ item.brand }
				</span>
				<strong className="genie-comparison__model">
					{ item.model || product.title }
				</strong>
				{ item.sku && (
					<span className="genie-comparison__sku">{ item.sku }</span>
				) }
			</a>
		</th>
	);
}

function storageList( items: Pairing[] ) {
	if ( ! items.length ) {
		return '—';
	}
	const models = items.map( ( item ) => item.model );
	const conditions = new Map< string, Set< string > >();
	const accessories = new Map< string, Set< string > >();
	const sources = new Map<
		string,
		{ label: string; models: Set< string > }
	>();
	for ( const item of items ) {
		if ( item.verdict === 'released_with_accessory' ) {
			const parts = item.accessories.join( ', ' );
			const label =
				__( 'Accessory required', 'linker-tools' ) +
				( parts ? ' · ' + parts : '' );
			const applicable = accessories.get( label ) ?? new Set< string >();
			applicable.add( item.model );
			accessories.set( label, applicable );
		}
		for ( const note of item.conditions ) {
			const applicable = conditions.get( note ) ?? new Set< string >();
			applicable.add( item.model );
			conditions.set( note, applicable );
		}
		for ( const doc of item.documents ?? [] ) {
			const url = doc.page
				? doc.url.split( '#' )[ 0 ] + '#page=' + doc.page
				: doc.url;
			const label = doc.page
				? doc.title +
					' · ' +
					sprintf(
						/* translators: %d is the source page inside a manufacturer PDF. */
						__( 'page %d', 'linker-tools' ),
						doc.page
					)
				: doc.title;
			const source = sources.get( url ) ?? {
				label,
				models: new Set< string >(),
			};
			source.models.add( item.model );
			sources.set( url, source );
		}
	}
	const names = [
		...new Set( [
			...models,
			...items.flatMap( ( item ) => item.accessories ),
		] ),
	]
		.filter( Boolean )
		.sort( ( a, b ) => b.length - a.length );
	const pattern = new RegExp(
		'(' +
			names
				.map( ( name ) => name.replace( /[^a-z0-9 ]/gi, '\\$&' ) )
				.join( '|' ) +
			')',
		'g'
	);
	const keepModelsTogether = ( text: string ) =>
		text.split( pattern ).map( ( part, i ) =>
			i % 2 ? (
				<span key={ i } className="genie-comparison__identifier">
					{ part }
				</span>
			) : (
				part
			)
		);
	const scope = ( applicable: Set< string > ) =>
		applicable.size < models.length && (
			<strong>
				{ keepModelsTogether( [ ...applicable ].join( ', ' ) ) }{ ' ' }
				·{ ' ' }
			</strong>
		);
	return (
		<>
			<span>{ keepModelsTogether( models.join( ', ' ) ) }</span>
			{ Array.from( accessories, ( [ label, applicable ] ) => (
				<div key={ label }>
					{ scope( applicable ) }
					{ keepModelsTogether( label ) }
				</div>
			) ) }
			{ ( conditions.size > 0 || sources.size > 0 ) && (
				<details className="genie-comparison__notes">
					<summary>{ __( 'Notes', 'linker-tools' ) }</summary>
					<ul>
						{ Array.from( conditions, ( [ note, applicable ] ) => (
							<li key={ note }>
								{ scope( applicable ) }
								{ keepModelsTogether( note ) }
							</li>
						) ) }
					</ul>
					{ sources.size > 0 && (
						<ul>
							{ Array.from( sources, ( [ url, source ] ) => (
								<li key={ url }>
									{ scope( source.models ) }
									<a
										href={ url }
										target="_blank"
										rel="noreferrer"
									>
										{ source.label }
									</a>
								</li>
							) ) }
						</ul>
					) }
				</details>
			) }
		</>
	);
}

interface Group {
	name: string;
	columns: Column[];
	keys: string[];
	storage: boolean;
}
function SpecTable( {
	group,
	rows,
	locale,
	draftAction,
}: {
	group: Group;
	rows: Spec[];
	locale: Locale;
	draftAction: ( c: Column ) => ReactNode;
} ) {
	const { columns, name } = group;
	const row = (
		key: string,
		label: string,
		cell: ( c: Column ) => ReactNode
	) => (
		<tr key={ key }>
			<th scope="row">{ label }</th>
			{ columns.map( ( c ) => (
				<td key={ c.product_id }>{ cell( c ) }</td>
			) ) }
		</tr>
	);
	const brand = row(
		'brand',
		__( 'Brand / Series', 'linker-tools' ),
		( { presentation: p } ) => brandSeries( p.brand, p.series ) || '—'
	);
	const specs = rows
		.filter( ( r ) => group.keys.includes( r.field ) )
		.map( ( r ) =>
			row( r.field, r.label, ( c ) =>
				valueText( r.values[ c.product_id ], locale )
			)
		);
	const storage =
		group.storage &&
		row( 'storage', __( 'Compatible storage', 'linker-tools' ), ( c ) =>
			storageList( c.presentation.storage )
		);
	const availability = row(
		'availability',
		__( 'Availability', 'linker-tools' ),
		( { presentation: p } ) => (
			<span
				className="genie-comparison__stock"
				data-available={ p.in_stock }
			>
				{ p.in_stock
					? __( 'In stock', 'linker-tools' )
					: __( 'Currently unavailable', 'linker-tools' ) }
			</span>
		)
	);
	const price = row(
		'price',
		__( 'Partner pricing', 'linker-tools' ),
		( { presentation: p } ) =>
			p.price_reason === 'login'
				? __( 'Net price after sign-in', 'linker-tools' )
				: p.price_line || '—'
	);
	const pdf = row(
		'pdf',
		__( 'Datasheet', 'linker-tools' ),
		( { presentation: { datasheet } } ) =>
			datasheet ? (
				<a
					className="genie-comparison__pdf"
					href={ datasheet.url }
					title={ datasheet.title }
					target="_blank"
					rel="noopener noreferrer"
				>
					{ __( 'Datasheet', 'linker-tools' ) } ↗
				</a>
			) : (
				'—'
			)
	);
	return (
		<section className="genie-comparison">
			<h3>
				{ __( 'Product comparison', 'linker-tools' ) } · { name }
			</h3>
			<div
				className="genie-comparison__scroll"
				role="region"
				aria-label={ name }
				tabIndex={ 0 }
			>
				<table aria-label={ name }>
					<thead>
						<tr>
							<th scope="col">
								{ __( 'Specification', 'linker-tools' ) }
							</th>
							{ columns.map( ( c ) => (
								<ModelHeading
									key={ c.product_id }
									product={ c }
								/>
							) ) }
						</tr>
					</thead>
					<tbody>
						{ brand }
						{ specs }
						{ storage }
						{ availability }
						{ price }
						{ pdf }
						{ row(
							'draft',
							__( 'Solution draft', 'linker-tools' ),
							draftAction
						) }
					</tbody>
				</table>
			</div>
		</section>
	);
}
