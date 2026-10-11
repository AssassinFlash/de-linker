/**
 * The catalogue family cards' model picker (docs/acceptance/2026-10-11/16/
 * working/replica-r4/EVIDENCE.md §6-2: the live shop lists one card per
 * family, the card's picker switches the article it shows).
 *
 * Everything is read from the markup the family grid printed: the card's
 * `data-linker-articles` payload holds each member article's values, the
 * picker's buttons carry the member ids, and the card's own data attributes
 * and elements ([data-card-title], [data-card-sku], [data-card-selection],
 * the media link and image, price, availability) are the fields a switch
 * updates — the same contract the live page's catalogue script reads.
 */
( function ( window, document ) {
	'use strict';

	function articles( card ) {
		var node = card.querySelector( '[data-linker-articles]' );
		if ( ! node ) {
			return [];
		}
		try {
			var rows = JSON.parse( node.textContent || '[]' );
			return Array.isArray( rows ) ? rows : [];
		} catch ( error ) {
			return [];
		}
	}

	function articleById( rows, id ) {
		for ( var i = 0; i < rows.length; i += 1 ) {
			if ( String( rows[ i ].id ) === String( id ) ) {
				return rows[ i ];
			}
		}
		return null;
	}

	function setText( node, value ) {
		if ( node ) {
			node.textContent = value === null || value === undefined ? '' : String( value );
		}
	}

	function setHref( node, value ) {
		if ( node && value ) {
			node.setAttribute( 'href', String( value ) );
		}
	}

	function select( card, article ) {
		if ( ! card || ! article ) {
			return;
		}
		card.setAttribute( 'data-product-id', String( article.id ) );
		card.setAttribute( 'data-sku', String( article.sku || '' ) );

		var image = card.querySelector( '[data-card-image]' );
		if ( image && article.image ) {
			image.setAttribute( 'src', String( article.image ) );
			if ( article.name ) {
				image.setAttribute( 'alt', String( article.name ) );
			}
		}
		setHref( card.querySelector( '[data-card-media-link]' ), article.url );

		var title = card.querySelector( '[data-card-title]' );
		setText( title, article.name );
		setHref( title, article.url );
		setText( card.querySelector( '[data-card-sku]' ), article.sku );
		setText( card.querySelector( '[data-card-selection]' ), article.selection );
		setHref( card.querySelector( '[data-card-view]' ), article.url );
		setText( card.querySelector( '[data-card-availability]' ), article.availability );

		var price = card.querySelector( '[data-card-price]' );
		if ( price && article.priceHtml ) {
			price.innerHTML = article.priceHtml;
		}
		var facts = card.querySelector( '[data-card-facts]' );
		if ( facts && article.factsHtml ) {
			facts.innerHTML = article.factsHtml;
		}

		var checkbox = card.querySelector( '[data-compare-article]' );
		if ( checkbox ) {
			checkbox.setAttribute( 'data-compare-article', String( article.id ) );
			checkbox.setAttribute( 'aria-label', 'Compare: ' + String( article.name || '' ) );
		}
	}

	var cards = document.querySelectorAll( '[data-linker-family-card]' );
	Array.prototype.forEach.call( cards, function ( card ) {
		var rows = articles( card );
		Array.prototype.forEach.call(
			card.querySelectorAll( '[data-linker-select-article]' ),
			function ( button ) {
				button.addEventListener( 'click', function () {
					var article = articleById( rows, button.getAttribute( 'data-linker-select-article' ) );
					if ( ! article ) {
						return;
					}
					select( card, article );
					Array.prototype.forEach.call(
						card.querySelectorAll( '[data-linker-select-article]' ),
						function ( other ) {
							if ( other === button ) {
								other.setAttribute( 'aria-current', 'true' );
							} else {
								other.removeAttribute( 'aria-current' );
							}
						}
					);
					var picker = card.querySelector( '.card-article-picker' );
					if ( picker ) {
						picker.open = false;
					}
				} );
			}
		);
	} );
} )( window, document );
