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
		add_filter( 'woocommerce_structured_data_type_for_page', array( $this, 'strip_online_store_type' ) );
		add_filter( 'woocommerce_structured_data_online_store', '__return_false' );
		add_filter( 'seopress_schemas_website', array( $this, 'website' ) );
		add_filter( 'seopress_get_json_data_organization', array( $this, 'organization' ) );
		add_filter( 'seopress_schemas_auto_article_json', array( $this, 'article_schema' ) );
		add_filter( 'seopress_pro_get_json_data_author', array( $this, 'author_schema' ), 10, 2 );
		add_filter( 'seopress_schemas_auto_custom_html', array( $this, 'about_publisher' ) );
		add_action( 'wp_head', array( $this, 'print_blocks' ) );
		add_action( 'wp_head', array( $this, 'print_organization' ) );
	}

	/**
	 * Woo's retail return policy does not describe the inquiry site.
	 *
	 * @param string[] $types Woo schema types for the current page.
	 * @return list<string>
	 */
	public function strip_online_store_type( array $types ): array {
		return array_values( array_diff( $types, array( 'onlinestore' ) ) );
	}

	/** Canonical publisher across all languages. */
	private static function organization_id(): string {
		return PageUrls::root() . '#organization';
	}

	/** Canonical author across all languages. */
	private static function chester_id(): string {
		return PageUrls::root() . '#chester-john';
	}

	/**
	 * Use the journal or homepage's public language for the site's identity.
	 *
	 * @param array<string,mixed> $node SEOPress website node.
	 * @return array<string,mixed>
	 */
	public function website( array $node ): array {
		$node['url']           = PageUrls::home();
		$node['description']   = self::site_description();
		$node['alternateName'] = 'Linker Technology GmbH';
		$node['inLanguage']    = self::is_german() ? 'de' : 'en';
		$node['publisher']     = array( '@id' => self::organization_id() );
		return $node;
	}

	/** Public site description in the current language. */
	private static function site_description(): string {
		return self::is_german()
			? 'PV- und Batteriespeichersysteme für Wohngebäude, Gewerbe und Industrie mit dokumentierter Kompatibilität und technischer Unterstützung in Europa.'
			: 'Residential and C&I solar and battery storage systems with documented compatibility and technical support for installers and EPCs across Europe.';
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
		$node['inLanguage'] ??= self::is_german() ? 'de' : 'en';
		if ( isset( $node['author'] ) && is_array( $node['author'] ) ) {
			$node['author'] = $this->author_schema( $node['author'] );
		}
		if ( isset( $node['publisher'] ) && is_array( $node['publisher'] ) ) {
			$node['publisher']['@id']    = self::organization_id();
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
		return array_merge(
			$node,
			array(
				'@type'      => 'Person',
				'@id'        => self::chester_id(),
				'name'       => 'Chester John',
				'url'        => $about,
				'image'      => plugins_url( 'assets/chester-john.webp', dirname( __DIR__, 2 ) . '/linker-commerce.php' ),
				'knowsAbout' => array( 'Battery Energy Storage Systems (BESS)', 'Inverter-Battery Pairing', 'Commercial and Industrial Energy Storage', 'VDE-AR-N 4105', 'PV System Sizing' ),
				'jobTitle'   => self::is_german() ? 'Spezialist für Speicherlösungen' : 'Storage Solutions Specialist',
				'worksFor'   => array(
					'@type' => 'Organization',
					'@id'   => self::organization_id(),
					'name'  => 'Linker Technology GmbH',
					'url'   => PageUrls::root(),
				),
				'sameAs'     => ContactChannels::chester_same_as(),
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
		unset( $node['taxID'] );
		$social = get_option( 'seopress_social_option_name', array() );
		$logo   = $social['seopress_social_knowledge_img'] ?? ( $node['logo'] ?? '' );
		if ( is_string( $logo ) && '' !== $logo ) {
			$metadata     = wp_get_attachment_metadata( attachment_url_to_postid( $logo ) );
			$node['logo'] = array(
				'@type' => 'ImageObject',
				'url'   => $logo,
			);
			if ( ! empty( $metadata['width'] ) && ! empty( $metadata['height'] ) ) {
				$node['logo']['width']  = $metadata['width'];
				$node['logo']['height'] = $metadata['height'];
			} elseif ( str_ends_with( $logo, '/2026/07/linker-logo-full.png' ) ) {
				$node['logo']['width']  = 717;
				$node['logo']['height'] = 354;
			}
		}
		$sales   = ( new Options() )->team_mailbox();
		$germany = str_replace( ' ', '-', ContactChannels::GERMANY_PHONE );
		$direct  = str_replace( ' ', '-', ContactChannels::DIRECT_PHONE );
		return array_merge(
			$node,
			array(
				'@id'           => self::organization_id(),
				'url'           => PageUrls::root(),
				'name'          => 'Linker',
				'description'   => self::site_description(),
				'alternateName' => array( 'Linker Technology GmbH', 'de-linker.com' ),
				'foundingDate'  => '2024-01-24',
				'areaServed'    => array( 'DE', 'AT', 'CH', 'EU' ),
				'knowsAbout'    => array( 'Battery Energy Storage Systems (BESS)', 'Hybrid Solar Inverters', 'Residential Battery Storage', 'Commercial and Industrial Energy Storage', 'Utility-Scale Battery Storage', 'LFP Battery Technology', 'VDE-AR-N 4105', 'VDE-AR-N 4110' ),
				'legalName'     => 'Linker Technology GmbH',
				'sameAs'        => ContactChannels::company_same_as(),
				'vatID'         => 'DE367367711',
				'identifier'    => array(
					'@type'      => 'PropertyValue',
					'name'       => 'Handelsregister',
					'propertyID' => 'DE-HRB',
					'value'      => 'Amtsgericht Stendal HRB 33824',
				),
				'address'       => array(
					'@type'           => 'PostalAddress',
					'streetAddress'   => 'Steinfeldstraße 3',
					'postalCode'      => '39179',
					'addressLocality' => 'Barleben',
					'addressRegion'   => 'Sachsen-Anhalt',
					'addressCountry'  => 'DE',
				),
				'email'         => $sales,
				'telephone'     => $germany,
				'contactPoint'  => array(
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
	 * Connect the English AboutPage and ContactPage schemas to the identified publisher.
	 *
	 * @param string $html A resolved SEOPress automatic custom schema.
	 */
	public function about_publisher( string $html ): string {
		if ( ! is_page( array( 'about', 'contact' ) ) || ! preg_match( '~^\s*<script\b[^>]*>(.*?)</script>\s*$~is', $html, $script ) ) {
			return $html;
		}
		$node  = json_decode( $script[1], true );
		$types = (array) ( $node['@type'] ?? array() );
		if ( is_page( 'about' ) && in_array( 'AboutPage', $types, true ) ) {
			$node['about']    = array( '@id' => self::organization_id() );
			$node['mentions'] = array( array( '@id' => self::chester_id() ) );
		} elseif ( is_page( 'contact' ) && in_array( 'ContactPage', $types, true ) ) {
			$node['mainEntity'] = array( '@id' => self::organization_id() );
		} else {
			return $html;
		}
		$node['isPartOf']  = array( '@id' => PageUrls::home() . '#website' );
		$node['publisher'] = array( '@id' => self::organization_id() );
		return '<script type="application/ld+json">' . wp_json_encode( $node, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "</script>\n";
	}

	/** SEOPress prints its Knowledge Graph organization only on the front page. */
	public function print_organization(): void {
		if ( ! is_front_page() ) {
			$this->print_node(
				$this->organization( array( '@type' => 'Organization' ) )
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
					'provider'            => array( '@id' => self::organization_id() ),
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
		} elseif ( is_page( array( 'compare-products', 'produkte-vergleichen', 'solution', 'loesung', 'residential-storage', 'heimspeicher', 'commercial-storage', 'gewerbespeicher', 'utility-storage', 'grossspeicher', 'about', 'ueber-uns', 'services-support', 'kundendienst', 'capability', 'leistungsfaehigkeit', 'imprint', 'impressum', 'privacy-policy', 'datenschutz', 'terms-of-sale', 'verkaufsbedingungen', 'refund-returns', 'rueckgabe-erstattung', 'for-installer', 'fuer-installateur', 'for-epc', 'fuer-epc' ) ) ) {
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
				'isPartOf'    => array( '@id' => $home . '#website' ),
				'publisher'   => array( '@id' => self::organization_id() ),
				'@type'       => 'ueber-uns' === $post->post_name ? array( 'AboutPage', 'WebPage' ) : 'WebPage',
				'@id'         => $url . '#webpage',
				'name'        => $title,
				'url'         => $url,
				'description' => (string) get_post_meta( $post->ID, '_seopress_titles_desc', true ),
			);
			if ( in_array( $post->post_name, array( 'about', 'ueber-uns' ), true ) ) {
				$this->print_node( $this->author_schema( array( 'name' => 'Chester John' ) ) );
			}
			if ( in_array( $post->post_name, array( 'capability', 'leistungsfaehigkeit' ), true ) ) {
				$trail[] = array(
					'label' => (string) get_the_title( $post->post_parent ),
					'url'   => PageUrls::page( 'about' ),
				);
			}
			if ( 'ueber-uns' === $post->post_name ) {
				$node['mentions'] = array( array( '@id' => self::chester_id() ) );
				$node['about']    = array( '@id' => self::organization_id() );
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
					'provider'    => array( '@id' => self::organization_id() ),
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
		} elseif ( is_page( array( 'contact', 'kontakt', 'faq-dokumente' ) ) ) {
			$contact = 'faq-dokumente' !== $post->post_name;
			if ( $contact ) {
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
			}
			// The English contact page uses the SEOPress custom ContactPage.
			if ( 'contact' !== $post->post_name ) {
				$node = array(
					'@type'       => array( $contact ? 'ContactPage' : 'CollectionPage', 'WebPage' ),
					'@id'         => $url . '#webpage',
					'name'        => $title,
					'url'         => $url,
					'description' => (string) get_post_meta( $post->ID, '_seopress_titles_desc', true ),
					'isPartOf'    => array( '@id' => $home . '#website' ),
					'publisher'   => array( '@id' => self::organization_id() ),
				);
				if ( $contact ) {
					$node['mainEntity'] = array( '@id' => self::organization_id() );
				}
				$this->print_node( $node );
			}
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
