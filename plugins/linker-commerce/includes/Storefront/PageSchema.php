<?php
/**
 * Localized structured data for public pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Settings\Options;
use WP_Post;

/** Extend the active SEOPress nodes and supply the missing public page types. */
final class PageSchema {
	/** Register the public metadata hooks. */
	public function register(): void {
		add_filter( 'seopress_schemas_website', array( $this, 'localized_home' ) );
		add_filter( 'seopress_get_json_data_organization', array( $this, 'organization' ) );
		add_filter( 'seopress_schemas_auto_custom_html', array( $this, 'about_publisher' ) );
		add_action( 'wp_head', array( $this, 'print_blocks' ) );
		add_action( 'wp_head', array( $this, 'print_organization' ) );
	}

	/**
	 * Use the translated homepage and its approved description.
	 *
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

	/**
	 * Enrich the site's publisher without changing product manufacturers.
	 *
	 * @param array<string,mixed> $node Existing SEOPress graph node.
	 * @return array<string,mixed>
	 */
	public function organization( array $node ): array {
		$node    = $this->localized_home( $node );
		$sales   = ( new Options() )->team_mailbox();
		$germany = str_replace( ' ', '-', ContactChannels::GERMANY_PHONE );
		$direct  = str_replace( ' ', '-', ContactChannels::DIRECT_PHONE );
		return array_merge(
			$node,
			array(
				'name'         => 'Linker',
				'legalName'    => 'Linker Technology GmbH',
				'url'          => PageUrls::home(),
				'vatID'        => 'DE367367711',
				'taxID'        => 'DE367367711',
				'identifier'   => array(
					'@type' => 'PropertyValue',
					'name'  => 'Handelsregister',
					'value' => 'Amtsgericht Stendal HRB 33824',
				),
				'address'      => array(
					'@type'           => 'PostalAddress',
					'streetAddress'   => 'Steinfeldstraße 3',
					'postalCode'      => '39179',
					'addressLocality' => 'Barleben',
					'addressCountry'  => 'DE',
				),
				'email'        => $sales,
				'telephone'    => $germany,
				'contactPoint' => array(
					array(
						'@type'             => 'ContactPoint',
						'contactType'       => 'sales',
						'telephone'         => $germany,
						'email'             => $sales,
						'areaServed'        => 'EU',
						'availableLanguage' => array( 'en', 'de' ),
					),
					array(
						'@type'             => 'ContactPoint',
						'contactType'       => 'customer support',
						'telephone'         => $direct,
						'email'             => ContactChannels::DIRECT_EMAIL,
						'url'               => ContactChannels::WHATSAPP_BASE,
						'availableLanguage' => array( 'en', 'de', 'zh' ),
					),
				),
			)
		);
	}

	/**
	 * Connect the existing English AboutPage schema to the identified publisher.
	 *
	 * @param string $html A resolved SEOPress automatic custom schema.
	 */
	public function about_publisher( string $html ): string {
		if ( ! is_page( 'about' ) || ! preg_match( '~^\s*<script\b[^>]*>(.*?)</script>\s*$~is', $html, $script ) ) {
			return $html;
		}
		$node = json_decode( $script[1], true );
		if ( ! is_array( $node ) || ! in_array( 'AboutPage', (array) ( $node['@type'] ?? array() ), true ) ) {
			return $html;
		}
		$node['about'] = array( '@id' => PageUrls::home() . '#organization' );
		return '<script type="application/ld+json">' . wp_json_encode( $node, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "</script>\n";
	}

	/** SEOPress prints its Knowledge Graph organization only on the front page. */
	public function print_organization(): void {
		if ( ! is_front_page() ) {
			$this->print_node(
				$this->organization(
					array(
						'@type' => 'Organization',
						'@id'   => PageUrls::home() . '#organization',
					)
				)
			);
		}
	}

	/** Print breadcrumbs and page identities for the visible public page. */
	public function print_blocks(): void {
		$post = get_queried_object();
		if ( ! $post instanceof WP_Post ) {
			return;
		}

		$url   = (string) get_permalink( $post );
		$title = html_entity_decode( wp_strip_all_tags( get_the_title( $post ) ), ENT_QUOTES | ENT_HTML5, 'UTF-8' );
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
		} elseif ( is_page( array( 'solution', 'loesung', 'residential-storage', 'heimspeicher', 'commercial-storage', 'gewerbespeicher', 'utility-storage', 'grossspeicher', 'about', 'ueber-uns', 'services-support', 'kundendienst', 'for-installer', 'fuer-installateur', 'for-epc', 'fuer-epc' ) ) ) {
			$trail = array(
				array(
					'label' => _x( 'Home', 'breadcrumb', 'linker-commerce' ),
					'url'   => $home,
				),
			);
			$type  = match ( $post->post_name ) {
				'solution', 'loesung'             => __( 'Solar and battery storage solutions', 'linker-commerce' ),
				'residential-storage', 'heimspeicher' => __( 'Residential Solar Battery Storage', 'linker-commerce' ),
				'commercial-storage', 'gewerbespeicher' => __( 'Commercial & Industrial Battery Storage', 'linker-commerce' ),
				'utility-storage', 'grossspeicher' => __( 'Utility-Scale Battery Energy Storage Systems', 'linker-commerce' ),
				default                           => '',
			};
			$node = array(
				'@type'       => 'ueber-uns' === $post->post_name ? array( 'AboutPage', 'WebPage' ) : 'WebPage',
				'@id'         => $url . '#webpage',
				'name'        => $title,
				'url'         => $url,
				'description' => (string) get_post_meta( $post->ID, '_seopress_titles_desc', true ),
			);
			if ( 'ueber-uns' === $post->post_name ) {
				$node['about'] = array( '@id' => $home . '#organization' );
			}
			if ( '' !== $type ) {
				$hub     = in_array( $post->post_name, array( 'solution', 'loesung' ), true );
				$trail[] = array(
					'label' => __( 'Solutions', 'linker-commerce' ),
					'url'   => PageUrls::page( 'solution' ),
				);
				if ( ! $hub ) {
					$trail[] = array(
						'label' => $title,
						'url'   => $url,
					);
				}
				$node['mainEntity'] = array(
					'@type'       => 'Service',
					'@id'         => $url . '#service',
					'name'        => $title,
					'url'         => $url,
					'description' => $node['description'],
					'provider'    => array( '@id' => $home . '#organization' ),
					'areaServed'  => 'EU',
					'serviceType' => $type,
				);
				if ( preg_match( '/' . get_shortcode_regex( array( 'linker_solution_products' ) ) . '/s', $post->post_content, $match ) && '[' !== $match[1] && ']' !== $match[6] ) {
					$atts = shortcode_parse_atts( $match[3] );
					$rows = SolutionProducts::featured( (string) ( $atts['scope'] ?? 'hub' ) );
					if ( $rows ) {
						$items = array();
						foreach ( $rows as $index => $row ) {
							$items[] = array(
								'@type'    => 'ListItem',
								'position' => $index + 1,
								'name'     => trim( $row['name'] . ' ' . $row['rating'] ),
								'url'      => $row['url'],
							);
						}
						$node['mentions'] = array(
							'@type'           => 'ItemList',
							'itemListElement' => $items,
						);
					}
				}
			} else {
				$trail[] = array(
					'label' => $title,
					'url'   => $url,
				);
			}
			// SEOPress already supplies the English AboutPage and WebPage.
			if ( 'about' !== $post->post_name ) {
				$this->print_node( $node );
			}
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
				$node['mainEntity'] = array( '@id' => $home . '#organization' );
			}
			$this->print_node( $node );
		}
		if ( $trail ) {
			$items = array();
			foreach ( $trail as $index => $crumb ) {
				$items[] = array(
					'@type'    => 'ListItem',
					'position' => $index + 1,
					'name'     => html_entity_decode( $crumb['label'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ),
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

	/**
	 * Encode a public structured-data block.
	 *
	 * @param array<string,mixed> $node Schema.org entity.
	 */
	private function print_node( array $node ): void {
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON_HEX_TAG keeps JSON inside the script element.
		echo '<script type="application/ld+json">' . wp_json_encode( array( '@context' => 'https://schema.org' ) + $node, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "</script>\n";
	}
}
