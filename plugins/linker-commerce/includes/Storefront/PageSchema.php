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
		add_filter( 'seopress_schemas_website', array( $this, 'website' ) );
		add_filter( 'seopress_get_json_data_organization', array( $this, 'organization' ) );
		add_filter( 'seopress_schemas_auto_article_json', array( $this, 'article_schema' ) );
		add_filter( 'seopress_pro_get_json_data_author', array( $this, 'author_schema' ), 10, 2 );
		add_filter( 'seopress_schemas_auto_custom_html', array( $this, 'about_publisher' ) );
		add_action( 'wp_head', array( $this, 'print_blocks' ) );
		add_action( 'wp_head', array( $this, 'print_organization' ) );
	}

	/**
	 * Use the journal or homepage's public language for the site's identity.
	 *
	 * @param array<string,mixed> $node SEOPress website node.
	 * @return array<string,mixed>
	 */
	public function website( array $node ): array {
		$node['url']         = PageUrls::home();
		$node['description'] = self::is_german()
			? 'PV- und Batteriespeichersysteme für Wohngebäude, Gewerbe und Industrie mit dokumentierter Kompatibilität und technischer Unterstützung in Europa.'
			: 'Residential and C&I solar and battery storage systems with documented compatibility and technical support for installers and EPCs across Europe.';
		return $node;
	}

	/**
	 * Resolve the public site identity for callers of the original filter.
	 *
	 * @param array<string,mixed> $node Site node.
	 * @return array<string,mixed>
	 */
	public function localized_home( array $node ): array {
		return $this->website( $node );
	}

	/** Current Polylang language. */
	private static function is_german(): bool {
		return function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
	}

	/**
	 * Identify the article's publisher and preserve the post's byline.
	 *
	 * @param array<string,mixed> $node Automatic Article or BlogPosting node.
	 * @return array<string,mixed>
	 */
	public function article_schema( array $node ): array {
		if ( isset( $node['author'] ) && is_array( $node['author'] ) ) {
			$node['author'] = $this->author_schema( $node['author'] );
		}
		if ( isset( $node['publisher'] ) && is_array( $node['publisher'] ) ) {
			$node['publisher']['@id']    = PageUrls::home() . '#organization';
			$node['publisher']['sameAs'] = ContactChannels::company_same_as();
		}
		return $node;
	}

	/**
	 * Chester's public profile in SEOPress's resolved article or Person template.
	 *
	 * @param array<string,mixed>      $node Author node.
	 * @param array<string,mixed>|null $context SEOPress template context.
	 * @return array<string,mixed>
	 */
	public function author_schema( array $node, ?array $context = null ): array {
		$name = $node['name'] ?? '';
		if ( '[[name]]' === $name ) {
			$post = $context['post'] ?? get_post();
			$user = $post instanceof WP_Post ? get_userdata( (int) $post->post_author ) : false;
			if ( ! $user || 'chester-john' !== $user->user_nicename ) {
				return $node;
			}
		} elseif ( 'Chester John' !== $name ) {
			return $node;
		}
		$about = PageUrls::page( 'about' );
		$home  = PageUrls::home();
		return array_merge(
			$node,
			array(
				'@type'    => 'Person',
				'@id'      => $about . '#chester-john',
				'name'     => 'Chester John',
				'url'      => $about,
				'jobTitle' => self::is_german() ? 'Spezialist für Speicherlösungen' : 'Storage Solutions Specialist',
				'worksFor' => array(
					'@type' => 'Organization',
					'@id'   => $home . '#organization',
					'name'  => 'Linker Technology GmbH',
					'url'   => $home,
				),
				'sameAs'   => ContactChannels::chester_same_as(),
			)
		);
	}

	/**
	 * Enrich the site's publisher without changing product manufacturers.
	 *
	 * @param array<string,mixed> $node Existing SEOPress graph node.
	 * @return array<string,mixed>
	 */
	public function organization( array $node ): array {
		$node    = $this->website( $node );
		$sales   = ( new Options() )->team_mailbox();
		$germany = str_replace( ' ', '-', ContactChannels::GERMANY_PHONE );
		$direct  = str_replace( ' ', '-', ContactChannels::DIRECT_PHONE );
		return array_merge(
			$node,
			array(
				'name'         => 'Linker',
				'legalName'    => 'Linker Technology GmbH',
				'sameAs'       => ContactChannels::company_same_as(),
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
		} elseif ( is_page( array( 'compare-products', 'produkte-vergleichen', 'solution', 'loesung', 'residential-storage', 'heimspeicher', 'commercial-storage', 'gewerbespeicher', 'utility-storage', 'grossspeicher', 'about', 'ueber-uns', 'services-support', 'kundendienst', 'for-installer', 'fuer-installateur', 'for-epc', 'fuer-epc' ) ) ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Match the public comparison selection policy, including empty query values.
			if ( in_array( $post->post_name, array( 'compare-products', 'produkte-vergleichen' ), true ) && ( isset( $_GET['ids'] ) || isset( $_GET['capped'] ) ) ) {
				return;
			}
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
