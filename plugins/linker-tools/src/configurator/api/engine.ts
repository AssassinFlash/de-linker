/**
 * Calls to the Solution Configurator engine (services/engine).
 */

/**
 * Internal dependencies
 */
import type {
	CommercialInput,
	CommercialResult,
	Place,
	ResidentialInput,
	ResidentialResult,
	RoofPlane,
	RoofResult,
} from '../types';

/** Why a call failed, in the terms the screens explain. */
export type EngineErrorKind =
	| 'invalid' // 422: the engine refused an input (`field` names it)
	| 'unavailable' // 503: PVGIS or the LoD2 source did not answer
	| 'not_found' // 404: unknown postcode
	| 'limited' // 429: a resource allowance or actual work slot is full
	| 'network'; // no answer at all

export class EngineError extends Error {
	constructor(
		readonly kind: EngineErrorKind,
		readonly field?: string
	) {
		super( kind );
	}
}

import { resourceFetch } from '../../protection/request';

type Fetch = typeof fetch;

async function call( response: Promise< Response > ): Promise< Response > {
	let answer: Response;
	try {
		answer = await response;
	} catch {
		throw new EngineError( 'network' );
	}
	if ( answer.ok ) {
		return answer;
	}
	let field: string | undefined;
	try {
		const body = await answer.json();
		field = body?.detail?.field;
	} catch {
		field = undefined;
	}
	if ( answer.status === 429 ) {
		throw new EngineError( 'limited' );
	}
	if ( answer.status === 422 ) {
		throw new EngineError( 'invalid', field );
	}
	if ( answer.status === 404 ) {
		throw new EngineError( 'not_found', field );
	}
	if ( answer.status === 503 || answer.status === 409 ) {
		throw new EngineError( 'unavailable' );
	}
	throw new EngineError( 'network' );
}

export interface EngineClient {
	place: ( plz: string ) => Promise< Place >;
	residential: ( input: ResidentialInput ) => Promise< ResidentialResult >;
	commercial: ( input: CommercialInput ) => Promise< CommercialResult >;
	roof: (
		plz: string,
		latitude: number,
		longitude: number,
		locale: string
	) => Promise< RoofResult >;
	pack: (
		polygon: [ number, number ][],
		tilt: number,
		azimuth: number
	) => Promise< RoofPlane >;
	reportPdf: (
		input: ResidentialInput,
		logo: string | null,
		selectionFingerprint?: string
	) => Promise< Blob >;
}

export function engineClient(
	baseUrl: string,
	fetcher: Fetch = ( ...args ) => fetch( ...args )
): EngineClient {
	const post = async ( path: string, body: unknown ) =>
		call(
			resourceFetch( fetcher, `${ baseUrl }${ path }`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify( body ),
			} )
		);
	return {
		place: async ( plz ) =>
			(
				await call(
					resourceFetch( fetcher, `${ baseUrl }/geo/plz/${ plz }` )
				)
			).json(),
		residential: async ( input ) =>
			( await post( '/design/residential', input ) ).json(),
		commercial: async ( input ) =>
			( await post( '/design/commercial', input ) ).json(),
		roof: async ( plz, latitude, longitude, locale ) =>
			(
				await post( '/roof/outline', {
					plz,
					locale,
					location: { latitude, longitude },
				} )
			).json(),
		pack: async ( polygon, tilt, azimuth ) =>
			(
				await post( '/roof/pack', {
					polygon,
					tilt_deg: tilt,
					azimuth_deg: azimuth,
				} )
			).json(),
		reportPdf: async ( input, logo, selectionFingerprint ) =>
			(
				await post( '/report/pdf', {
					input,
					logo,
					selection_fingerprint: selectionFingerprint,
				} )
			).blob(),
	};
}
