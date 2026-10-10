/**
 * Links to the documents a release or a rule cites; all of them are files we host.
 */

/**
 * WordPress dependencies
 */
import { __, sprintf } from '@wordpress/i18n';

/**
 * Internal dependencies
 */
import type { Doc } from '../types';

export function documentName( url: string ): string {
	const file = decodeURIComponent( url.split( '/' ).pop() ?? url );
	return file.replace( /\.pdf$/i, '' ).replace( /[-_]+/g, ' ' );
}

export function Documents( { documents }: { documents: Doc[] } ) {
	if ( documents.length === 0 ) {
		return null;
	}
	return (
		<ul className="linker-documents">
			{ documents.map( ( doc ) => (
				<li key={ `${ doc.url }#${ doc.page ?? '' }` }>
					<a
						href={
							doc.page
								? `${ doc.url }#page=${ doc.page }`
								: doc.url
						}
					>
						{ documentName( doc.url ) }
					</a>
					{ doc.page
						? /* translators: %d: page number in a PDF */
							` · ${ sprintf( __( 'page %d', 'linker-tools' ), doc.page ) }`
						: '' }
				</li>
			) ) }
		</ul>
	);
}
