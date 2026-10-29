<?php
/**
 * The catalogue and journal archive structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;

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
		$this->print_blocks( array( $this->collection(), $this->breadcrumb() ) );
	}

	/**
	 * Prints the two blocks for an indexable blog category archive.
	 *
	 * The child theme owns the category template hook, but the schema facts
	 * and encoding stay beside the catalogue's other archive schema. A
	 * noindexed category is deliberately skipped: it is neither in the
	 * sitemap nor a page search engines are asked to understand.
	 */
	public function print_blog_category_block(): void {
		$this->print_blocks( array( $this->blog_category_collection(), $this->blog_category_breadcrumb() ) );
	}

	/**
	 * Print the non-empty nodes in one sequence.
	 *
	 * @param list<array<string, mixed>> $blocks Schema.org nodes.
	 */
	private function print_blocks( array $blocks ): void {
		foreach ( $blocks as $block ) {
			if ( array() === $block ) {
				continue;
			}
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- encoded() keeps the JSON inside its script element.
			echo '<script type="application/ld+json">' . $this->encoded( $block ) . "</script>\n";
		}
	}

	/**
	 * CollectionPage for an indexable blog category, or an empty array.
	 *
	 * @return array<string, mixed>
	 */
	public function blog_category_collection(): array {
		$target = $this->blog_category_target();
		if ( null === $target ) {
			return array();
		}
		return array(
			'@context' => 'https://schema.org',
			'@type'    => 'CollectionPage',
			'name'     => $target['name'],
			'url'      => $target['url'],
			'isPartOf' => array(
				'@type' => 'WebSite',
				'name'  => (string) get_bloginfo( 'name' ),
				'url'   => PageUrls::home(),
			),
		);
	}

	/**
	 * The blog category's breadcrumb: home, the blog index and the term.
	 *
	 * @return array<string, mixed>
	 */
	public function blog_category_breadcrumb(): array {
		$target = $this->blog_category_target();
		if ( null === $target ) {
			return array();
		}
		$items = array(
			array(
				'@type'    => 'ListItem',
				'position' => 1,
				'name'     => _x( 'Home', 'breadcrumb', 'linker-commerce' ),
				'item'     => PageUrls::home(),
			),
		);
		$posts = get_posts(
			array(
				'post_type'      => 'page',
				'name'           => 'blog',
				'post_status'    => 'publish',
				'posts_per_page' => 1,
				'no_found_rows'  => true,
			)
		);
		$blog  = $posts[0] ?? null;
		if ( $blog instanceof \WP_Post ) {
			$items[] = array(
				'@type'    => 'ListItem',
				'position' => 2,
				'name'     => (string) $blog->post_title,
				'item'     => (string) get_permalink( $blog->ID ),
			);
		}
		$items[] = array(
			'@type'    => 'ListItem',
			'position' => count( $items ) + 1,
			'name'     => $target['name'],
			'item'     => $target['url'],
		);
		return array(
			'@context'        => 'https://schema.org',
			'@type'           => 'BreadcrumbList',
			'itemListElement' => $items,
		);
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
				'url'   => PageUrls::home(),
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
				'item'     => PageUrls::home(),
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
	 * The queried blog category when it is published and indexable.
	 *
	 * @return array{name: string, url: string, term: \WP_Term}|null
	 */
	private function blog_category_target(): ?array {
		if ( ! is_category() ) {
			return null;
		}
		$term = get_queried_object();
		if ( ! $term instanceof \WP_Term ) {
			return null;
		}
		$noindex = function_exists( 'seopress_titles_noindex_bypass' )
			? seopress_titles_noindex_bypass()
			: get_term_meta( $term->term_id, '_seopress_robots_index', true );
		if ( ! empty( $noindex ) ) {
			return null;
		}
		$link = get_term_link( $term );
		if ( ! is_string( $link ) || '' === $link ) {
			return null;
		}
		return array(
			'name' => (string) $term->name,
			'url'  => $link,
			'term' => $term,
		);
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
