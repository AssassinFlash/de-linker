<?php
/**
 * Buttons and page titles in the site's words.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Vocabulary;

use WC_Product;

/**
 * The texts WooCommerce passes through filters of their own: the product
 * button, the send button, the confirmation, the login request on the Proforma
 * request page, the privacy text, and the titles of the solution draft and
 * Proforma request pages (docs/specs/11-commerce.md, journey steps 3 and 4).
 */
final class Labels {

	/**
	 * "Add to solution draft" on a product a customer can add; WooCommerce's
	 * text otherwise (e.g. "Read more" for a product out of stock).
	 *
	 * @param string          $text    WooCommerce's text.
	 * @param WC_Product|null $product Product.
	 */
	public function add_to_draft( string $text, $product = null ): string {
		if ( $product instanceof WC_Product && ! ( $product->is_purchasable() && $product->is_in_stock() && $product->is_type( array( 'simple', 'variation' ) ) ) ) {
			return $text;
		}
		return __( 'Add to solution draft', 'linker-commerce' );
	}

	/**
	 * The send button of the Proforma request page.
	 */
	public function send_inquiry(): string {
		return __( 'Request Proforma', 'linker-commerce' );
	}

	/**
	 * The first line of the confirmation page.
	 */
	public function inquiry_received(): string {
		return __( 'Thank you. Your inquiry has been received.', 'linker-commerce' );
	}

	/**
	 * What a visitor who is not logged in reads on the Proforma request page.
	 */
	public function log_in_to_send(): string {
		return __( 'Please log in to request a Proforma invoice. No account yet? Register on the account page.', 'linker-commerce' );
	}

	/**
	 * The privacy texts under the send and register buttons, in the visitor's
	 * language (WooCommerce stores them as settings, in one language).
	 *
	 * @param string $text WooCommerce's text (from its settings).
	 * @param string $type "checkout" or "registration".
	 */
	public function privacy_text( string $text, string $type ): string {
		if ( 'checkout' === $type ) {
			return __( 'We use your personal data to process your inquiry and for the other purposes described in our [privacy_policy].', 'linker-commerce' );
		}
		if ( 'registration' === $type ) {
			return __( 'We use your personal data to manage your account and for the other purposes described in our [privacy_policy].', 'linker-commerce' );
		}
		return $text;
	}

	/**
	 * Titles of the solution draft and Proforma request pages; runs on the_title
	 * before WooCommerce sets endpoint titles.
	 *
	 * @param string $title   Title.
	 * @param int    $post_id Post.
	 */
	public function page_title( string $title, $post_id = 0 ): string {
		return $this->title_of( (int) $post_id ) ?? $title;
	}

		/**
		 * The solution-draft page's SEO title, when SEOPress has stored the
		 * WooCommerce page name ("Your Cart | Linker" / "Ihr Warenkorb | Linker").
		 *
		 * SEOPress does not read document_title_parts. The replacement is the
		 * page name this plugin already uses, plus the site suffix SEOPress
		 * already appended. Any other title is returned unchanged.
		 *
		 * @param string $title SEOPress title.
		 */
	public function seo_title( string $title ): string {
		$draft    = __( 'Solution draft', 'linker-commerce' );
		$replaced = preg_replace( '/^(Your Cart|Ihr Warenkorb|Warenkorb|Cart)(?=\s*\|)/', $draft, $title, 1 );
		return is_string( $replaced ) ? $replaced : $title;
	}

		/**
		 * The solution-draft page's SEO description, when it still speaks of a
		 * cart, a basket or a catalogue.
		 *
		 * The stored English and German descriptions name the basket and the
		 * catalogue. This returns the same facts in the site's words. Any other
		 * description is returned unchanged, so a page that does not carry those
		 * sentences is not rewritten. The German sentence is the msgstr of the
		 * stored English sentence, matched literally: a variable passed to __()
		 * is not a translatable string.
		 *
		 * @param string $description SEOPress description.
		 */
	public function seo_description( string $description ): string {
		$replacements = array(
			'Review the lines in your basket, adjust quantities and check the totals. Approved partner accounts see net pricing, tax and delivery terms before checkout.' => __( 'Review the lines in your solution draft, adjust quantities and check the totals. Approved partner accounts see net prices, tax and delivery terms before the Proforma request.', 'linker-commerce' ),
			'Build a cart from catalog products or SKU rows. Approved partner accounts can review pricing, delivery, tax, and checkout details.' => __( 'Build a solution draft from products or product numbers. Approved partner accounts can review prices, delivery, tax and the Proforma request.', 'linker-commerce' ),
			'Überprüfen Sie die Positionen in Ihrem Warenkorb, passen Sie die Mengen an und prüfen Sie die Gesamtsummen. Zugelassene Partnerkonten sehen Nettopreise, Steuern und Lieferbedingungen vor dem Checkout.' => __( 'Prüfen Sie die Positionen in Ihrem Lösungsentwurf, passen Sie die Mengen an und prüfen Sie die Summen. Freigegebene Partnerkonten sehen Nettopreise, Steuern und Lieferbedingungen vor der Proforma-Anfrage.', 'linker-commerce' ),
		);
			// seopress_titles_desc passes the sentence. seopress_social_og_desc
			// passes the whole meta tag, so the sentence is replaced inside it.
			return strtr( $description, $replacements );
	}

		/**
		 * The same titles in the browser tab.
		 *
		 * @param array<string, string> $parts Parts of the document title.
		 * @return array<string, string>
		 */
	public function document_title( array $parts ): array {
		// On an endpoint (the confirmation) WooCommerce's own title stays.
		if ( is_page() && ! is_wc_endpoint_url() ) {
			$title = $this->title_of( (int) get_queried_object_id() );
			if ( null !== $title ) {
				$parts['title'] = $title;
			}
		}
		return $parts;
	}

	/**
	 * The same titles in the breadcrumb: on an endpoint (the confirmation)
	 * WooCommerce takes the page's stored title for its crumb, not the_title.
	 *
	 * @param array<int, array{0: string, 1?: string}> $crumbs Crumbs: name and address.
	 * @return array<int, array{0: string, 1?: string}>
	 */
	public function breadcrumb( array $crumbs ): array {
		foreach ( array( wc_get_page_id( 'cart' ), wc_get_page_id( 'checkout' ) ) as $page_id ) {
			$url = get_permalink( $page_id );
			foreach ( $crumbs as $index => $crumb ) {
				if ( false !== $url && ( $crumb[1] ?? '' ) === $url ) {
					$crumbs[ $index ][0] = (string) $this->title_of( $page_id );
				}
			}
		}
		return $crumbs;
	}

	/**
	 * Title of a WooCommerce page this plugin names, or null.
	 *
	 * @param int $post_id Post.
	 */
	private function title_of( int $post_id ): ?string {
		if ( $post_id <= 0 ) {
			return null;
		}
		if ( wc_get_page_id( 'cart' ) === $post_id ) {
			return __( 'Solution draft', 'linker-commerce' );
		}
		if ( wc_get_page_id( 'checkout' ) === $post_id ) {
			return __( 'Proforma request', 'linker-commerce' );
		}
		return null;
	}
}
