/** Safe answer formatting; verified destinations remain structured document/cards. */
import { useMemo } from '@wordpress/element';
import MarkdownIt from 'markdown-it';

const markdown = new MarkdownIt( {
	html: false,
	linkify: false,
	typographer: false,
} );
// Narrative model text does not introduce destinations or external image loads.
// Verified links/images already arrive through the document and product blocks.
markdown.renderer.rules.link_open = () => '<span>';
markdown.renderer.rules.link_close = () => '</span>';
markdown.renderer.rules.image = ( tokens, index ) =>
	markdown.utils.escapeHtml( tokens[ index ].content );

export function MessageBody( {
	text,
	progress = 1,
	locale = 'en',
}: {
	text: string;
	progress?: number;
	locale?: 'en' | 'de';
} ) {
	const complete = useMemo( () => {
		const document = new DOMParser().parseFromString(
			markdown.render( text ),
			'text/html'
		);
		// #223 owner typography correction: only long unformatted prose is
		// grouped at existing sentence boundaries. 360/280/80 characters are
		// local reading-rhythm choices; words and canonical answers stay intact.
		for ( const paragraph of document.body.querySelectorAll(
			':scope > p'
		) ) {
			if (
				paragraph.children.length ||
				( paragraph.textContent?.length ?? 0 ) <= 360
			) {
				continue;
			}
			const sentences = new Intl.Segmenter( locale, {
				granularity: 'sentence',
			} ).segment( paragraph.textContent ?? '' );
			const groups: string[] = [];
			let group = '';
			for ( const { segment } of sentences ) {
				if (
					group.length >= 80 &&
					group.length + segment.length > 280
				) {
					groups.push( group.trim() );
					group = '';
				}
				group += segment;
			}
			if ( group.trim() ) {
				groups.push( group.trim() );
			}
			if ( groups.length > 1 ) {
				paragraph.replaceWith(
					...groups.flatMap( ( value ) => {
						const next = document.createElement( 'p' );
						next.textContent = value;
						return [ next, document.createTextNode( '\n' ) ];
					} )
				);
			}
		}
		return document.body.innerHTML;
	}, [ text, locale ] );
	const html = useMemo( () => {
		if ( progress >= 1 ) {
			return complete;
		}
		// Parse the complete, escaped Markdown first: partial Markdown tokens
		// never flash on screen. Only text nodes are progressively revealed.
		const document = new DOMParser().parseFromString(
			complete,
			'text/html'
		);
		const walker = document.createTreeWalker(
			document.body,
			NodeFilter.SHOW_TEXT
		);
		const nodes: Text[] = [];
		while ( walker.nextNode() ) {
			nodes.push( walker.currentNode as Text );
		}
		let remaining = Math.ceil(
			nodes.reduce(
				( count, node ) => count + Array.from( node.data ).length,
				0
			) * progress
		);
		for ( const node of nodes ) {
			const characters = Array.from( node.data );
			node.data = characters
				.slice( 0, Math.max( 0, remaining ) )
				.join( '' );
			remaining -= characters.length;
		}
		// Future list items/headings must not leave blank bullets or margins.
		for ( const element of Array.from(
			document.body.querySelectorAll( '*' )
		).reverse() ) {
			if ( ! element.textContent?.trim() ) {
				element.remove();
			}
		}
		return document.body.innerHTML;
	}, [ complete, progress ] );
	return (
		<div
			className="linker-genie-message-body"
			dangerouslySetInnerHTML={ { __html: html } }
		/>
	);
}
