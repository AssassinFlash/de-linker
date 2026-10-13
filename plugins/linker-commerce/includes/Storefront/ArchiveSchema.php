<?php
/**
 * The catalogue's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/**
 * Emits the CollectionPage and BreadcrumbList blocks the product archive and
 * the product categories carry.
 *
 * WHY HERE. The same reasoning as ProductSchema: the facts of these pages are
 * this plugin's — the shop's URL and word come from WooCommerce and the
 * translations, a category's name from its own term — and the previous
 * emitter lived in code the switch deletes, so the blocks are built next to
 * the catalogue head (ProductShortcodes), which reads the same sources.
 *
 * WHAT IT MIRRORS. Exactly what the visible page shows: the same shop link
 * and "Products" word as the head's breadcrumb row, the same `breadcrumb`
 * context's "Home" label, the category's own name as its H1 uses it, and the
 * one intro sentence the shop and the archives both print. The brand under
 * `isPartOf` is the site's own name.
 */
final class ArchiveSchema {

	/**
	 * Adds the blocks to the head of the catalogue pages.
	 */
	public function register(): void {
		add_action( 'wp_head', array( $this, 'print_block' ) );
	}

	/**
	 * Prints the two blocks, or nothing when this request is not the catalogue.
	 */
	public function print_block(): void {
		foreach ( array( $this->collection(), $this->breadcrumb() ) as $block ) {
			if ( array() === $block ) {
				continue;
			}
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the payload is JSON, and encoded() is where its one dangerous character is handled.
			echo '<script type="application/ld+json">' . $this->encoded( $block ) . "</script>\n";
		}
	}

	/**
	 * The CollectionPage node, or an empty array when this request is not the
	 * product archive or a product-category archive.
	 *
	 * @return array<string, mixed>
	 */
	public function collection(): array {
		$target = $this->target();
		if ( null === $target ) {
			return array();
		}
		return array(
			'@context'    => 'https://schema.org',
			'@type'       => 'CollectionPage',
			'name'        => $target['name'],
			'url'         => $target['url'],
			'description' => (string) __( 'Search products or filter by category and project requirements.', 'linker-commerce' ),
			'isPartOf'    => array(
				'@type' => 'WebSite',
				'name'  => (string) get_bloginfo( 'name' ),
				'url'   => home_url( '/' ),
			),
		);
	}

	/**
	 * The BreadcrumbList node of the same page: Home, the shop, and the
	 * category when the page is one.
	 *
	 * @return array<string, mixed>
	 */
	public function breadcrumb(): array {
		$target = $this->target();
		if ( null === $target ) {
			return array();
		}
		$items = array(
			array(
				'@type'    => 'ListItem',
				'position' => 1,
				'name'     => _x( 'Home', 'breadcrumb', 'linker-commerce' ),
				'item'     => home_url( '/' ),
			),
			array(
				'@type'    => 'ListItem',
				'position' => 2,
				'name'     => $this->shop_name(),
				'item'     => $this->shop_url(),
			),
		);
		if ( null !== $target['term'] ) {
			$items[] = array(
				'@type'    => 'ListItem',
				'position' => 3,
				'name'     => $target['name'],
				'item'     => $target['url'],
			);
		}
		return array(
			'@context'        => 'https://schema.org',
			'@type'           => 'BreadcrumbList',
			'itemListElement' => $items,
		);
	}

	/**
	 * The JSON for one node.
	 *
	 * A `<` inside a name would otherwise end the script element, and the
	 * block would leave the page as text. JSON decodes `\u003C` back to the
	 * character, so an escaping pass over the encoded string is the one place
	 * that keeps the payload out of HTML's way.
	 *
	 * @param array<string, mixed> $node The schema.org node.
	 */
	public function encoded( array $node ): string {
		return str_replace( '<', '\u003C', (string) wp_json_encode( $node, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
	}

	/**
	 * What the queried page is: the shop, a product category, or nothing.
	 *
	 * @return array{name: string, url: string, term: \WP_Term|null}|null
	 */
	private function target(): ?array {
		if ( function_exists( 'is_product_category' ) && is_product_category() ) {
			$term = get_queried_object();
			if ( $term instanceof \WP_Term ) {
				$link = get_term_link( $term );
				if ( is_string( $link ) && '' !== $link ) {
					return array(
						'name' => (string) $term->name,
						'url'  => $link,
						'term' => $term,
					);
				}
			}
			return null;
		}
		if ( ! is_post_type_archive( 'product' ) ) {
			return null;
		}
		$url = $this->shop_url();
		if ( '' === $url ) {
			return null;
		}
		return array(
			'name' => $this->shop_name(),
			'url'  => $url,
			'term' => null,
		);
	}

	/**
	 * The shop page's permalink, in the queried language.
	 */
	private function shop_url(): string {
		return (string) wc_get_page_permalink( 'shop' );
	}

	/**
	 * The shop page's own word, the head's breadcrumb and H1 source.
	 */
	private function shop_name(): string {
		return (string) __( 'Products', 'linker-commerce' );
	}
}
