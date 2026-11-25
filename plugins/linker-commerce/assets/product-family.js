/**
 * The catalogue family cards' model picker (docs/acceptance/2026-10-11/16/
 * working/replica-r4/EVIDENCE.md §6-2: the live shop lists one card per
 * family, the card's picker switches the article it shows).
 *
 * Everything is read from the markup the family grid printed: the card's
 * `data-linker-products` payload holds each member article's values, the
 * picker's buttons carry the member ids, and the card's own data attributes
 * and elements ([data-card-title], [data-card-sku], [data-card-selection],
 * the media link and image, price, availability) are the fields a switch
 * updates — the same contract the live page's catalogue script reads.
 */
( function ( window, document ) {
	'use strict';

	function memberRows( card ) {
		var node = card.querySelector( '[data-linker-products]' );
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

	function memberById( rows, id ) {
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

	function select( card, member ) {
		if ( ! card || ! member ) {
			return;
		}
		card.setAttribute( 'data-product-id', String( member.id ) );
		card.setAttribute( 'data-sku', String( member.sku || '' ) );

		var image = card.querySelector( '[data-card-image]' );
		if ( image && member.image ) {
			image.setAttribute( 'width', String( member.imageWidth ) );
			image.setAttribute( 'height', String( member.imageHeight ) );
			image.setAttribute( 'src', String( member.image ) );
			if ( member.name ) {
				image.setAttribute( 'alt', String( member.name ) );
			}
		}
		setHref( card.querySelector( '[data-card-media-link]' ), member.url );

		var title = card.querySelector( '[data-card-title]' );
		setText( title, member.name );
		setHref( title, member.url );
		setText( card.querySelector( '[data-card-sku]' ), member.sku );
		setText( card.querySelector( '[data-card-selection]' ), member.selection );
		setHref( card.querySelector( '[data-card-view]' ), member.url );
		setText( card.querySelector( '[data-card-availability]' ), member.availability );
		var draft = card.querySelector( '[data-card-atc]' );
		if ( draft ) {
			draft.hidden = ! member.addToCartUrl;
			if ( draft.hidden ) {
				draft.removeAttribute( 'href' );
			} else {
				setHref( draft, member.addToCartUrl );
			}
		}
		setHref( card.querySelector( '[data-card-gate]' ), member.accountUrl );


		var price = card.querySelector( '[data-card-price]' );
		if ( price && member.priceHtml ) {
			price.innerHTML = member.priceHtml;
		}
		var facts = card.querySelector( '[data-card-facts]' );
		if ( facts && member.factsHtml ) {
			facts.innerHTML = member.factsHtml;
		}

		var checkbox = card.querySelector( '[data-compare-product]' );
		if ( checkbox ) {
			checkbox.setAttribute( 'data-compare-product', String( member.compareId || member.id ) );
			checkbox.setAttribute( 'aria-label', String( member.compareLabel || checkbox.getAttribute( 'aria-label' ) || '' ) );
			if ( typeof window.linkerComparePaint === 'function' ) {
				window.linkerComparePaint();
			}
		}
	}

	document.addEventListener( 'click', function ( event ) {
		var button = event.target.closest?.( '[data-linker-select-product]' );
		var card = button?.closest( '[data-linker-family-card]' );
		if ( ! card ) return;
		var member = memberById( memberRows( card ), button.getAttribute( 'data-linker-select-product' ) );
		if ( ! member ) return;
		select( card, member );
		card.querySelectorAll( '[data-linker-select-product]' ).forEach( function ( other ) {
			if ( other === button ) {
				other.setAttribute( 'aria-current', 'true' );
			} else {
				other.removeAttribute( 'aria-current' );
			}
		} );
		var picker = card.querySelector( '.card-product-picker' );
		if ( picker ) picker.open = false;
	} );
} )( window, document );
