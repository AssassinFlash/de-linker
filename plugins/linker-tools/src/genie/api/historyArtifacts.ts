/** Current artifact presentation for live and restored turns; transcript stays intact. */
import { __ } from '@wordpress/i18n';
import type { Locale } from '../../configurator/types';
import {
	ARTIFACT_TIMEOUT_MS,
	productPresentation,
	type ProductPresentation,
} from './product';
import type { CardPrice, DocumentBlock, Turn } from './turn';

export interface ArtifactContext {
	restUrl: string;
	locale: Locale;
}

/**
 * The document library's existing vocabulary (Materials::document_kind_label).
 *
 * @param kind The authoritative document type.
 */
function documentKind( kind: string | undefined ): string {
	const labels: Record< string, string > = {
		datasheet: __( 'Datasheet', 'linker-tools' ),
		manual: __( 'Manual', 'linker-tools' ),
		warranty: __( 'Warranty', 'linker-tools' ),
		certificate: __( 'Certificate', 'linker-tools' ),
		compatibility: __( 'Compatibility list', 'linker-tools' ),
		brochure: __( 'Brochure', 'linker-tools' ),
	};
	return labels[ kind ?? '' ] ?? __( 'Document', 'linker-tools' );
}

/**
 * Legacy/current pagination is UI text; the URL and cited page numbers stay.
 *
 * @param block  The original document block.
 * @param locale Current page language.
 */
function documentPages(
	block: DocumentBlock,
	locale: Locale
): {
	title: string;
	suffix: string;
} {
	const match = block.label?.match(
		/\s*(?:·|,)\s*(?:p{1,2}\.|S\.|pages?|Seiten?)\s*(\d+(?:\s*,\s*\d+)*)$/iu
	);
	const pages =
		match?.[ 1 ].split( /\s*,\s*/ ) ??
		block.url?.match( /#page=(\d+)$/ )?.slice( 1 ) ??
		[];
	let word = pages.length > 1 ? 'pp.' : 'p.';
	if ( locale === 'de' ) {
		word = 'S.';
	}
	return {
		title: match
			? block.label!.slice( 0, match.index ).trim()
			: ( block.label ?? '' ),
		suffix: pages.length ? ` · ${ word }\u00a0${ pages.join( ', ' ) }` : '',
	};
}

function documentLabel(
	block: DocumentBlock,
	products: ProductPresentation[],
	locale: Locale
): DocumentBlock {
	if ( ! block.url || ! block.label ) {
		return block;
	}
	const baseUrl = block.url.split( '#' )[ 0 ];
	const { title, suffix } = documentPages( block, locale );
	const owner = block.ref.match( /^p(\d+)\.document\.\d+$/ );
	const candidates = owner
		? products.filter(
				( product ) => product.product_id === Number( owner[ 1 ] )
			)
		: products;
	const matches = candidates.filter( ( product ) =>
		product.documents?.some(
			( document ) => document.url?.split( '#' )[ 0 ] === baseUrl
		)
	);
	for ( const product of matches ) {
		const document = product.documents?.find(
			( item ) => item.url?.split( '#' )[ 0 ] === baseUrl
		);
		if ( ! document ) {
			continue;
		}
		const language = document.lang?.toUpperCase();
		const name =
			matches.length > 1
				? baseUrl.split( '/' ).pop()?.split( '?' )[ 0 ] || title
				: product.model || document.title || title;
		return {
			...block,
			label: `${ name } · ${ documentKind( document.type ) }${ language ? ` (${ language })` : '' }${ suffix }`,
			sourceTitle: document.title || title,
		};
	}
	// An unknown historic title is source material, not text to guess-translate.
	// Use the actual filename in the current-language Document UI; keep its
	// original title as the link's title attribute and leave the URL untouched.
	let filename = baseUrl.split( '/' ).pop()?.split( '?' )[ 0 ] ?? '';
	try {
		filename = decodeURIComponent( filename );
	} catch {
		// Malformed percent-encoding still names the original file verbatim.
	}
	return {
		...block,
		label: `${ documentKind( undefined ) }${ filename ? ` · ${ filename }` : '' }${ suffix }`,
		sourceTitle: title,
	};
}

/** Current permission and content identity; settles even if a transport ignores abort. */
async function publicationManifest(
	context: ArtifactContext,
	nonce: string,
	fetcher: typeof fetch
): Promise< {
	schema_version: number;
	products: Array< { product_id: number; published_locale_ids: number[] } >;
	documents: Array< {
		document_id: string;
		document_revision: string;
		url: string;
		aliases?: string[];
	} >;
} | null > {
	const controller = new AbortController();
	let timer: ReturnType< typeof setTimeout > | undefined;
	const timeout = new Promise< null >( ( resolve ) => {
		timer = setTimeout( () => {
			controller.abort();
			resolve( null );
		}, ARTIFACT_TIMEOUT_MS );
	} );
	const attempt = async () => {
		try {
			const response = await fetcher(
				`${ context.restUrl.replace( /\/?$/, '/' ) }linker/v1/publication/manifest`,
				{
					credentials: 'same-origin',
					cache: 'no-store',
					headers: { 'X-WP-Nonce': nonce },
					signal: controller.signal,
				}
			);
			const manifest = response.ok ? await response.json() : null;
			return manifest?.schema_version === 1 &&
				Array.isArray( manifest.products ) &&
				Array.isArray( manifest.documents )
				? manifest
				: null;
		} catch {
			return null;
		}
	};
	try {
		return await Promise.race( [ attempt(), timeout ] );
	} finally {
		if ( timer !== undefined ) {
			clearTimeout( timer );
		}
	}
}

/**
 * Reuse current get-product authority, never translating or trusting a saved
 * price sentence. Failed/missing authority removes that snapshot's price.
 *
 * @param turn                  Parsed turn, left untouched.
 * @param context               Current page REST root and locale.
 * @param nonce                 Current page REST nonce.
 * @param fetcher               Fetch for tests.
 * @param options               Refresh stored prices; live turns retain their service-filled prices.
 * @param options.refreshPrices Whether to replace historical prices with current authority.
 */
export async function restoreArtifacts(
	turn: Turn,
	context: ArtifactContext,
	nonce: string,
	fetcher: typeof fetch,
	options: { refreshPrices: boolean } = { refreshPrices: true }
): Promise< Turn > {
	const ids = new Set< number >();
	for ( const block of turn.blocks ) {
		if ( block.type === 'cards' || block.type === 'compare' ) {
			block.product_ids.forEach( ( id ) => ids.add( id ) );
		} else if ( block.type === 'document' ) {
			const product = block.ref.match( /^p(\d+)\.document\.\d+$/ );
			if ( product ) {
				ids.add( Number( product[ 1 ] ) );
			}
		}
	}
	const permission = publicationManifest( context, nonce, fetcher );
	const products = (
		await Promise.all(
			[ ...ids ].map( ( id ) =>
				productPresentation(
					context.restUrl,
					id,
					context.locale,
					nonce,
					fetcher
				)
			)
		)
	).filter( ( product ): product is ProductPresentation => product !== null );
	// Historical text remains a snapshot; active links require matching content identity.
	const manifest = await permission;
	const documents = manifest?.documents ?? [];
	const allowed = new Set< number >(
		manifest?.products.flatMap( ( product ) => [
			product.product_id,
			...product.published_locale_ids,
		] ) ?? []
	);
	const prices = new Map< number, CardPrice >();
	for ( const product of products ) {
		const commerce = product.commerce;
		const reason = commerce?.price_reason;
		const knownReason = [
			'login',
			'pending',
			'restricted',
			'project',
			'unpriced',
		].includes( reason ?? '' );
		if (
			typeof commerce?.price_line === 'string' &&
			commerce.price_line.trim() &&
			( ( commerce.price_visible === true &&
				( reason === undefined || reason === null ) ) ||
				( commerce.price_visible === false && knownReason ) )
		) {
			prices.set( product.product_id, {
				product_id: product.product_id,
				text: commerce.price_line,
				...( knownReason
					? { reason: reason as CardPrice[ 'reason' ] }
					: {} ),
			} );
		}
	}
	return {
		...turn,
		blocks: turn.blocks.map( ( block ) => {
			if ( block.type === 'cards' ) {
				return {
					...block,
					...( options.refreshPrices ? { draft_proofs: {} } : {} ),
					product_ids: block.product_ids.filter( ( id ) =>
						allowed.has( id )
					),
					prices: options.refreshPrices
						? block.product_ids.flatMap( ( id ) =>
								allowed.has( id ) && prices.has( id )
									? [ prices.get( id )! ]
									: []
							)
						: block.prices?.filter( ( price ) =>
								allowed.has( price.product_id )
							),
				};
			}
			if ( block.type === 'compare' ) {
				return {
					...block,
					product_ids: block.product_ids.filter( ( id ) =>
						allowed.has( id )
					),
				};
			}
			if (
				block.type === 'parts' &&
				options.refreshPrices &&
				block.add
			) {
				return { ...block, add: { ...block.add, proof: undefined } };
			}
			if ( block.type === 'document' ) {
				const current = documents.find(
					( item ) =>
						item.document_id === block.document_id &&
						item.document_revision === block.document_revision &&
						[ item.url, ...( item.aliases ?? [] ) ].includes(
							block.url?.split( '#' )[ 0 ] ?? ''
						)
				);
				return current
					? documentLabel( block, products, context.locale )
					: { ...block, url: null };
			}
			return block;
		} ),
	};
}
