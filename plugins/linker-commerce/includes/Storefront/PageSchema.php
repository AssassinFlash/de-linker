<?php
/**
 * Localized structured data for public pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use WP_Post;

/** Extend the active SEOPress nodes and supply the missing public page types. */
final class PageSchema {
	/** Register the public metadata hooks. */
	public function register(): void {
		add_filter( 'seopress_schemas_website', array( $this, 'localized_home' ) );
		add_filter( 'seopress_get_json_data_organization', array( $this, 'localized_home' ) );
		add_action( 'wp_head', array( $this, 'print_blocks' ) );
	}

	/**
	 * @param array<string,mixed> $node SEOPress's existing organization or website.
	 * @return array<string,mixed>
	 */
	public function localized_home( array $node ): array {
		if ( is_front_page() && function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			$node['url']         = PageUrls::home();
			$node['description'] = (string) get_post_meta( get_queried_object_id(), '_seopress_titles_desc', true );
		}
		return $node;
	}

	/** Print breadcrumbs and page identities for the visible public page. */
	public function print_blocks(): void {
		$post = get_queried_object();
		if ( ! $post instanceof WP_Post ) {
			return;
		}

		$url   = (string) get_permalink( $post );
		$title = wp_strip_all_tags( get_the_title( $post ) );
		$home  = PageUrls::home();
		$trail = array();
		if ( is_singular( 'product' ) ) {
			$trail = ProductView::crumbs( $post->ID );
		} elseif ( is_singular( 'post' ) ) {
			$trail = array(
				array(
					'label' => _x( 'Home', 'breadcrumb', 'linker-commerce' ),
					'url'   => $home,
				),
				array(
					'label' => get_the_title( (int) get_option( 'page_for_posts' ) ),
					'url'   => PageUrls::page( 'blog' ),
				),
				array(
					'label' => $title,
					'url'   => $url,
				),
			);
		} elseif ( is_page( array( 'solution-configurator', 'loesungskonfigurator' ) ) ) {
			$this->print_node(
				array(
					'@type'               => 'SoftwareApplication',
					'name'                => $title,
					'url'                 => $url,
					'applicationCategory' => 'BusinessApplication',
					'operatingSystem'     => 'Web',
				)
			);
			$trail = array(
				array(
					'label' => _x( 'Home', 'breadcrumb', 'linker-commerce' ),
					'url'   => $home,
				),
				array(
					'label' => $title,
					'url'   => $url,
				),
			);
		} elseif ( is_page( array( 'kontakt', 'faq-dokumente' ) ) && 'de' === pll_current_language() ) {
			$contact = is_page( 'kontakt' );
			$site    = array(
				'@type' => 'WebSite',
				'name'  => get_bloginfo( 'name' ),
				'url'   => $home,
			);
			$node    = array(
				'@type'       => array( $contact ? 'ContactPage' : 'CollectionPage', 'WebPage' ),
				'name'        => $title,
				'url'         => $url,
				'description' => (string) get_post_meta( $post->ID, '_seopress_titles_desc', true ),
				'isPartOf'    => $site,
			);
			if ( $contact ) {
				$node['mainEntity'] = array_merge( $site, array( '@type' => 'Organization' ) );
			}
			$this->print_node( $node );
		}
		if ( $trail ) {
			$items = array();
			foreach ( $trail as $index => $crumb ) {
				$items[] = array(
					'@type'    => 'ListItem',
					'position' => $index + 1,
					'name'     => $crumb['label'],
					'item'     => $crumb['url'] ?? $url,
				);
			}
			$this->print_node(
				array(
					'@type'           => 'BreadcrumbList',
					'itemListElement' => $items,
				)
			);
		}
	}

	/** @param array<string,mixed> $node Schema.org entity. */
	private function print_node( array $node ): void {
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON_HEX_TAG keeps JSON inside the script element.
		echo '<script type="application/ld+json">' . wp_json_encode( array( '@context' => 'https://schema.org' ) + $node, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "</script>\n";
	}
}
