/**
 * Engine and Store API stand-ins for tests and stories, answering with the
 * real engine's recorded answers (tests/fixtures/configurator). The engine
 * writes them and keeps them current (services/engine/tests/test_ui_fixtures.py,
 * which holds the request behind each file, with the fixture feed, a real
 * PVGIS profile for Munich and the official LoD2 cut around Triftstraße 5);
 * the Store API answers were read from the live site.
 */

/**
 * Internal dependencies
 */
import type { EngineClient } from '../../src/configurator/api/engine';
import type { AddStatus, StoreClient } from '../../src/configurator/api/store';
import type {
	CommercialResult,
	Locale,
	Place,
	ResidentialResult,
	RoofResult,
	StoreProduct,
} from '../../src/configurator/types';
import commercialIndicativeDe from '../fixtures/configurator/commercial-indicative-de.json';
import commercialIndicativeEn from '../fixtures/configurator/commercial-indicative-en.json';
import commercialSizedDe from '../fixtures/configurator/commercial-sized-de.json';
import commercialSizedEn from '../fixtures/configurator/commercial-sized-en.json';
import loadProfile from '../fixtures/configurator/load-profile-15min.csv?raw';
import place from '../fixtures/configurator/place-80538.json';
import residentialDe from '../fixtures/configurator/residential-de.json';
import residentialEn from '../fixtures/configurator/residential-en.json';
import noneDe from '../fixtures/configurator/residential-none-de.json';
import noneEn from '../fixtures/configurator/residential-none-en.json';
import roofDe from '../fixtures/configurator/roof-de.json';
import roofEn from '../fixtures/configurator/roof-en.json';
import storeProducts from '../fixtures/configurator/store-products.json';

export const fixtures = {
	residential: { en: residentialEn, de: residentialDe } as unknown as Record<
		Locale,
		ResidentialResult
	>,
	none: { en: noneEn, de: noneDe } as unknown as Record<
		Locale,
		ResidentialResult
	>,
	roof: { en: roofEn, de: roofDe } as unknown as Record< Locale, RoofResult >,
	commercialSized: {
		en: commercialSizedEn,
		de: commercialSizedDe,
	} as unknown as Record< Locale, CommercialResult >,
	commercialIndicative: {
		en: commercialIndicativeEn,
		de: commercialIndicativeDe,
	} as unknown as Record< Locale, CommercialResult >,
	place: place as unknown as Place,
	products: storeProducts as unknown as StoreProduct[],
	/** The 15-minute profile behind commercial-sized-*.json. */
	loadProfile,
};

export interface FakeEngineOptions {
	locale: Locale;
	residential?:
		'solution' | 'none' | 'unavailable' | 'never' | 'stale' | 'publication';
	commercial?: 'sized' | 'indicative';
	delay?: number;
}

const wait = ( ms: number ) =>
	new Promise( ( resolve ) => setTimeout( resolve, ms ) );

export function fakeEngine( options: FakeEngineOptions ) {
	const calls: { name: string; body: unknown }[] = [];
	const { locale, delay = 0 } = options;
	const engine: EngineClient = {
		async place( plz ) {
			calls.push( { name: 'place', body: plz } );
			await wait( delay );
			return fixtures.place;
		},
		async residential( input ) {
			calls.push( { name: 'residential', body: input } );
			await wait( delay );
			if ( options.residential === 'never' ) {
				return new Promise( () => undefined );
			}
			if (
				options.residential === 'stale' ||
				options.residential === 'publication'
			) {
				const { EngineError } =
					await import( '../../src/configurator/api/engine' );
				throw new EngineError( options.residential );
			}
			if ( options.residential === 'unavailable' ) {
				const { EngineError } =
					await import( '../../src/configurator/api/engine' );
				throw new EngineError( 'unavailable' );
			}
			return options.residential === 'none'
				? fixtures.none[ locale ]
				: fixtures.residential[ locale ];
		},
		async commercial( input ) {
			calls.push( { name: 'commercial', body: input } );
			await wait( delay );
			return options.commercial === 'sized'
				? fixtures.commercialSized[ locale ]
				: fixtures.commercialIndicative[ locale ];
		},
		async roof( plz, latitude, longitude ) {
			calls.push( { name: 'roof', body: { plz, latitude, longitude } } );
			await wait( delay );
			return fixtures.roof[ locale ];
		},
		async pack( polygon, tilt, azimuth ) {
			calls.push( { name: 'pack', body: { polygon, tilt, azimuth } } );
			return { ...fixtures.roof[ locale ].planes[ 2 ], polygon };
		},
		async reportPdf( input, logo ) {
			calls.push( { name: 'pdf', body: { input, logo } } );
			return new Blob( [ '%PDF-1.4' ], { type: 'application/pdf' } );
		},
	};
	return { engine, calls };
}

export function fakeStore(
	outcome: 'added' | 'unverified' | 'retry' | 'stale' = 'added',
	/** Products WooCommerce would report as currently unavailable. */
	outOfStock: number[] = []
) {
	const added: { productId: number; quantity: number }[] = [];
	const langs: string[] = [];
	const store: StoreClient = {
		async products( ids, locale ) {
			langs.push( locale );
			return fixtures.products
				.filter( ( product ) => ids.includes( product.id ) )
				.map( ( product ) =>
					outOfStock.includes( product.id )
						? { ...product, is_in_stock: false }
						: product
				);
		},
		async addAll(
			lines,
			onStatus: ( id: number, status: AddStatus ) => void
		) {
			lines.forEach( ( line ) => onStatus( line.productId, 'pending' ) );
			await wait( 0 );
			if ( outcome !== 'stale' ) {
				added.push( ...lines );
			}
			lines.forEach( ( line ) => onStatus( line.productId, outcome ) );
			return outcome === 'added';
		},
	};
	return { store, added, langs };
}
