<?php
/**
 * Bilingual directory of Linker's public solutions, tools and product families.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

use Linker\Commerce\Presentation\ContactChannels;
use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Storefront\AgentMarkdown;
use Linker\Commerce\Storefront\SitemapSync;

/** Serve the site-root text document before SEOPress's generic recent-posts index. */
final class LlmsTxt {
	public const HEADERS = array(
		'Content-Type'  => 'text/plain; charset=utf-8',
		'X-Robots-Tag'  => 'noindex, follow',
		'Cache-Control' => 'public, max-age=3600',
	);

	/**
	 * Handle the resource at its public path; other requests follow WordPress routing.
	 *
	 * @param bool $parse Current request parsing decision.
	 */
	public static function serve( bool $parse ): bool {
		$home = untrailingslashit( (string) get_option( 'home' ) );
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- only the parsed path is compared to a site-owned path.
		$path = wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH );
		$full = wp_parse_url( $home . '/llms-full.txt', PHP_URL_PATH ) === $path;
		if ( ! $full && wp_parse_url( $home . '/llms.txt', PHP_URL_PATH ) !== $path ) {
			return $parse;
		}
		foreach ( array( 'PT.product', 'PT.post', 'PT.page' ) as $tag ) {
			do_action( 'litespeed_tag_add', $tag ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Native LiteSpeed archive invalidation.
		}
		do_action( 'litespeed_control_force_public', 'Public bilingual resource directory' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache public API.
		do_action( 'litespeed_control_set_ttl', HOUR_IN_SECONDS ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache public API.
		foreach ( self::HEADERS as $key => $value ) {
			header( $key . ': ' . $value );
		}
		if ( 'HEAD' !== sanitize_text_field( wp_unslash( $_SERVER['REQUEST_METHOD'] ?? 'GET' ) ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the response is Markdown served as text/plain.
			echo $full ? self::full_document( $home ) : self::document( $home );
		}
		exit;
	}

	/**
	 * Build the public resource directory from both languages of the active site.
	 *
	 * @param string $home Site root without a trailing slash.
	 */
	public static function document( string $home ): string {
		$sections = array(
			'Solutions'                         => self::pages( array( 'solution', 'solution/residential-storage', 'solution/commercial-storage', 'solution/utility-storage' ) ),
			'Machine-Readable Engineering Data' => self::endpoints( $home ),
			'Manufacturers'                     => self::brands(),
			'Technical journal'                 => self::journal(),
			'Planning tools and documents'      => self::pages( array( 'inverter-battery-compatibility', 'solution-configurator', 'compare-products', 'faq-download', 'services-support', 'for-installer', 'for-epc', 'about', 'contact' ) ),
			'Product categories'                => self::categories(),
			'Product families'                  => self::product_families(),
		);
		$latest   = max( (string) get_lastpostmodified( 'gmt', 'product' ), (string) get_lastpostmodified( 'gmt', 'post' ), (string) get_lastpostmodified( 'gmt', 'page' ) );
		return self::markdown( $sections, substr( $latest, 0, 10 ), $home . '/sitemaps.xml' );
	}

	/**
	 * The company and resource sections use one stable, readable Markdown format.
	 *
	 * @param array<string,list<string>> $sections Directory headings and their bilingual links.
	 * @param string                     $updated Most recent public content date.
	 * @param string                     $sitemap Site's sitemap index.
	 */
	public static function markdown( array $sections, string $updated, string $sitemap ): string {
		$lines    = array(
			'# Linker Technology GmbH',
			'',
			'> Linker supplies hybrid inverters, battery storage systems and energy management accessories to installers and EPC contractors in Germany and across Europe. The solutions cover residential, commercial, industrial and utility-scale projects.',
			'',
			'Steinfeldstraße 3, 39179 Barleben, Germany · Amtsgericht Stendal HRB 33824 · VAT ID DE367367711',
			'',
			'Sales: ' . ( new Options() )->team_mailbox() . ' · ' . ContactChannels::GERMANY_PHONE,
			'',
			'Direct: ' . ContactChannels::DIRECT_EMAIL . ' · ' . ContactChannels::DIRECT_PHONE . ' · [WhatsApp](' . ContactChannels::WHATSAPP_BASE . ')',
			'',
		);
		$profiles = ContactChannels::company_same_as();
		foreach ( $profiles as $url ) {
			$label = match ( $url ) {
				ContactChannels::OFFICIAL_YOUTUBE => 'Official YouTube',
				ContactChannels::OFFICIAL_FACEBOOK => 'Official Facebook',
				default => (string) wp_parse_url( $url, PHP_URL_HOST ),
			};
			$lines[] = '- ' . $label . ': ' . $url;
		}
		foreach ( $sections as $heading => $rows ) {
			$lines[] = '';
			$lines[] = '## ' . $heading;
			$lines[] = '';
			foreach ( $rows as $row ) {
				$lines[] = '- ' . $row;
			}
		}
		$lines[] = '';
		$lines[] = '## Sitemaps';
		$lines[] = '';
		$lines[] = '- [Sitemap index](' . $sitemap . ')';
		$lines[] = '';
		$lines[] = 'Last updated: ' . $updated;
		return implode( "\n", $lines ) . "\n";
	}

	/**
	 * Resolve both published pages from their English page path.
	 *
	 * @param string[] $paths English hierarchical page paths.
	 * @return list<string>
	 */
	private static function pages( array $paths ): array {
		$rows = array();
		foreach ( $paths as $path ) {
			$page = get_page_by_path( $path );
			if ( $page instanceof \WP_Post && 'publish' === $page->post_status ) {
				$de = PageUrls::twin( $page->ID, 'de' );
				if ( $de > 0 && 'publish' === get_post_status( $de ) ) {
					$rows[] = self::post_pair( $page->ID, $de );
				}
			}
		}
		return $rows;
	}

	/**
	 * Link each nonempty category to its translated archive.
	 *
	 * @return list<string>
	 */
	private static function categories(): array {
		if ( ! function_exists( 'pll_get_term' ) ) {
			return array();
		}
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_cat',
				'hide_empty' => true,
				'lang'       => '',
			)
		);
		$rows  = array();
		if ( is_wp_error( $terms ) ) {
			return $rows;
		}
		$by_id = array_column( $terms, null, 'term_id' );
		foreach ( $terms as $term ) {
			if ( (int) pll_get_term( $term->term_id, 'en' ) !== $term->term_id ) {
				continue;
			}
			$twin = $by_id[ (int) pll_get_term( $term->term_id, 'de' ) ] ?? null;
			if ( $twin ) {
				$en_url = get_term_link( $term );
				$de_url = get_term_link( $twin );
				if ( is_string( $en_url ) && is_string( $de_url ) ) {
					$rows[] = self::link( $term->name, $en_url ) . ' · ' . self::link( $twin->name, $de_url );
				}
			}
		}
		return $rows;
	}

	/**
	 * Group every published model under its manufacturer and series.
	 *
	 * @return list<string>
	 */
	private static function product_families(): array {
		$visible   = wc_get_product_visibility_term_ids();
		$ids       = get_posts(
			array(
				'post_type'        => 'product',
				'post_status'      => 'publish',
				'numberposts'      => -1,
				'orderby'          => array(
					'title' => 'ASC',
					'ID'    => 'ASC',
				),
				'fields'           => 'ids',
				'lang'             => '',
				'suppress_filters' => false,
				'tax_query'        => array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- WooCommerce visibility excludes hidden engineering references.
					array(
						'taxonomy' => 'product_visibility',
						'field'    => 'term_taxonomy_id',
						'terms'    => array( $visible['exclude-from-catalog'] ),
						'operator' => 'NOT IN',
					),
				),
			)
		);
		$published = Publication::published_ids( array_map( 'intval', $ids ), true );
		$set       = array_fill_keys( $published, true );
		$english   = array_values( array_filter( $published, static fn( int $id ): bool => PageUrls::twin( $id, 'en' ) === $id ) );
		$rows      = array();
		foreach ( $english as $id ) {
			$de               = PageUrls::twin( $id, 'de' );
			$terms            = get_the_terms( $id, 'pa_brand' );
			$brand            = is_array( $terms ) && $terms ? $terms[0]->name : '';
			$series           = Materials::english_acf( $id )['product_series'] ?? '';
			$label            = implode( ' · ', array_unique( array_filter( array( $brand, is_string( $series ) ? trim( $series ) : '' ) ) ) );
			$facts            = SelectionFacts::for_product( $id );
			$figures          = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
			$figures          = is_string( $figures ) ? json_decode( $figures, true ) : $figures;
			$ratings          = array_filter( array( self::power( $facts, is_array( $figures ) ? $figures : array() ), self::energy( $facts ) ) );
			$rating           = $ratings ? ' · ' . implode( ' · ', $ratings ) : '';
			$rows[ $label ][] = isset( $set[ $de ] ) ? self::post_pair( $id, $de, $rating ) : self::link( get_the_title( $id ), (string) get_permalink( $id ) ) . $rating;
		}
		$lines = array();
		foreach ( $rows as $label => $models ) {
			$lines[] = ( '' === $label ? '' : $label . ': ' ) . implode( ' / ', $models );
		}
		return $lines;
	}

	/**
	 * Authoritative public engineering endpoints.
	 *
	 * @param string $home Site root.
	 * @return list<string>
	 */
	private static function endpoints( string $home ): array {
		return array_merge(
			array(
				self::link( 'Full equipment & compatibility reference', $home . '/llms-full.txt' ),
				self::link( 'Live engineering feed JSON', $home . '/wp-json/linker/v1/engineering-feed' ),
				self::link( 'MCP Server Card', $home . '/.well-known/mcp.json' ),
				self::link( 'A2A Agent Card', $home . '/.well-known/agent-card.json' ),
			),
			self::pages( array( 'inverter-battery-compatibility' ) )
		);
	}

	/**
	 * Manufacturer archives with a published model in the linked language.
	 *
	 * @return list<string>
	 */
	private static function brands(): array {
		$rows  = array();
		$terms = get_terms(
			array(
				'taxonomy'   => 'product_brand',
				'hide_empty' => true,
			)
		);
		if ( is_wp_error( $terms ) ) {
			return $rows;
		}
		$archives = new SitemapSync();
		foreach ( $terms as $term ) {
			$link = get_term_link( $term );
			if ( is_wp_error( $link ) ) {
				continue;
			}
			$entry = $archives->brand_urls( array( 'loc' => $link ), $term );
			if ( null !== $entry ) {
				$rows[] = self::link( $term->name, $entry['loc'] ) . ( isset( $entry['linker_brand_twin'] ) ? ' · ' . self::link( $term->name . ' (DE)', $entry['linker_brand_twin'] ) : '' );
			}
		}
		return $rows;
	}

	/**
	 * Pair published posts, including posts with only one language.
	 *
	 * @return list<string>
	 */
	private static function journal(): array {
		$ids       = get_posts(
			array(
				'post_type'    => 'post',
				'post_status'  => 'publish',
				'has_password' => false,
				'numberposts'  => -1,
				'fields'       => 'ids',
				'orderby'      => 'date',
				'order'        => 'DESC',
				'lang'         => '',
			)
		);
		$published = array_fill_keys( $ids, true );
		$seen      = array();
		$rows      = array();
		foreach ( $ids as $id ) {
			if ( isset( $seen[ $id ] ) ) {
				continue;
			}
			$en = PageUrls::twin( $id, 'en' );
			$de = PageUrls::twin( $id, 'de' );
			if ( isset( $published[ $en ], $published[ $de ] ) ) {
				$entry       = self::post_pair( $en, $de );
				$seen[ $en ] = true;
				$seen[ $de ] = true;
			} else {
				$entry = self::link( get_the_title( $id ), (string) get_permalink( $id ) );
			}
			if ( false === stripos( $entry, 'EcoFlow' ) ) {
				$rows[] = $entry;
			}
		}
		return $rows;
	}

	/**
	 * Public engineering tables with linked models and their release conditions.
	 *
	 * @param string $home Site root.
	 */
	public static function full_document( string $home ): string {
		$manifest     = Publication::manifest();
		$declarations = CompatibilityIndex::declarations( $manifest );
		$equipment    = array();
		$names        = array();
		$documents    = array_column( $manifest['documents'], null, 'document_id' );
		foreach ( $manifest['products'] as $product ) {
			if ( '' !== $product['engineering_role'] ) {
				continue;
			}
			$id           = $product['product_id'];
			$names[ $id ] = '' !== $product['model'] ? $product['model'] : $product['title'];
			$locales      = $product['locale_product_ids'];
			$figures      = Publication::figures_in_manifest( $id, $manifest );
			$facts        = SelectionFacts::from_figures( $id, $figures );
			$material     = Materials::material_for_product( $id );
			$downloads    = array();
			foreach ( $product['documents'] as $key ) {
				$downloads[] = $documents[ $key ];
			}
			$equipment[] = AgentMarkdown::row(
				array(
					$product['brand'],
					$names[ $id ],
					$material['identity']['manufacturer_part_number'] ?? '',
					str_replace( '_', ' ', $facts->device_class ),
					$facts->application,
					self::power( $facts, $figures ),
					self::energy( $facts ),
					'unknown' === $facts->phase ? '' : (string) $facts->phase,
					(string) ( $figures['ip_rating']['value'] ?? '' ),
					implode( ', ', CompatibilityIndex::grid_standards( $id, $downloads ) ),
					isset( $locales['en'] ) ? (string) get_permalink( $locales['en'] ) : '',
					isset( $locales['de'] ) ? (string) get_permalink( $locales['de'] ) : '',
				)
			);
		}
		$intro = self::markdown( array( 'Machine-Readable Engineering Data' => self::endpoints( $home ) ), substr( (string) get_lastpostmodified( 'gmt' ), 0, 10 ), $home . '/sitemaps.xml' );
		$lines = array(
			$intro,
			'## Published Equipment Index',
			'',
			'| Brand | Model | MPN | Category | Application | Power | Energy | Phase | IP | Grid standards | EN URL | DE URL |',
			AgentMarkdown::row( array_fill( 0, 12, '---' ) ),
			...$equipment,
			'',
			'## Verified Inverter & Battery Compatibility',
			'',
			'| Inverter | Battery | Verdict | Required accessory | Notes |',
			'| --- | --- | --- | --- | --- |',
		);
		foreach ( $declarations['pairs'] as $pair ) {
			$inverter = $names[ $pair['inverter_product_id'] ] ?? '';
			$battery  = $names[ $pair['battery_product_id'] ] ?? '';
			if ( '' === $inverter || '' === $battery || ! in_array( $pair['verdict'], array( 'released', 'released_with_accessory' ), true ) ) {
				continue;
			}
			$lines[] = AgentMarkdown::row( array( $inverter, $battery, str_replace( '_', ' ', $pair['verdict'] ), self::accessories( $pair, $names ), self::conditions( $pair ) ) );
		}
		$lines[] = "\n## Meter, Backup & Parallel Controller Rules\n";
		$lines[] = '| Inverter | Rule type | Status | Accessories | Summary |';
		$lines[] = '| --- | --- | --- | --- | --- |';
		foreach ( $declarations['requirements'] as $rule ) {
			$inverter = $names[ $rule['inverter_product_id'] ] ?? '';
			if ( '' !== $inverter ) {
				$lines[] = AgentMarkdown::row( array( $inverter, str_replace( '_', ' ', $rule['kind'] ), $rule['included'] ? 'Included' : 'Supplied separately', self::accessories( $rule, $names ), self::conditions( $rule ) ) );
			}
		}
		$lines[] = "\n## Key Documentation & Compliance Pages\n";
		foreach ( self::pages( array( 'inverter-battery-compatibility', 'faq-download', 'solution-configurator' ) ) as $page ) {
			$lines[] = '- ' . $page;
		}
		return implode( "\n", $lines ) . "\n";
	}

	/**
	 * Display the manufacturer conditions in the English reference.
	 *
	 * @param array<string,mixed> $rule Engineering declaration.
	 */
	private static function conditions( array $rule ): string {
		return Materials::apply_terms( implode( ' ', array_column( $rule['conditions'], 'en' ) ), false );
	}

	/**
	 * Display authorized accessories with quantities and basis.
	 *
	 * @param array<string,mixed> $rule Engineering declaration.
	 * @param array<int,string>   $names Public models.
	 */
	private static function accessories( array $rule, array $names ): string {
		$items = array();
		foreach ( $rule['accessories'] as $accessory ) {
			if ( isset( $names[ $accessory['product_id'] ] ) ) {
				$items[] = trim( $names[ $accessory['product_id'] ] . ' × ' . $accessory['quantity'] . ' ' . ( empty( $accessory['per'] ) ? '' : 'per ' . $accessory['per'] ) );
			}
		}
		return implode( ', ', $items );
	}

	/**
	 * Keep real and apparent power and the conditions on switchgear ratings.
	 *
	 * @param SelectionFactSet    $facts Published selection facts.
	 * @param array<string,mixed> $figures Current model figures.
	 */
	private static function power( SelectionFactSet $facts, array $figures ): string {
		if ( is_float( $facts->ac_power_kw ) ) {
			return $facts->ac_power_kw . ' kW';
		}
		if ( null !== $facts->ac_apparent_kva ) {
			return $facts->ac_apparent_kva . ' kVA';
		}
		$rated = $figures['rated_power_kw'] ?? array();
		return isset( $rated['value'], $rated['citation'] ) && 'kW' === ( $rated['unit'] ?? '' ) ? $rated['value'] . ' kW' : '';
	}

	/**
	 * Show a system range, nominal capacity, or usable capacity as documented.
	 *
	 * @param SelectionFactSet $facts Published selection facts.
	 */
	private static function energy( SelectionFactSet $facts ): string {
		if ( null !== $facts->kwh_range ) {
			return $facts->kwh_range['min'] . '–' . $facts->kwh_range['max'] . ' kWh';
		}
		if ( is_float( $facts->nominal_kwh ) ) {
			return $facts->nominal_kwh . ' kWh';
		}
		return is_float( $facts->usable_kwh ) ? $facts->usable_kwh . ' kWh usable' : '';
	}

	/**
	 * Pair the native titles and permalinks.
	 *
	 * @param int    $en English post ID.
	 * @param int    $de German post ID.
	 * @param string $rating Published rating, using English decimal notation.
	 */
	private static function post_pair( int $en, int $de, string $rating = '' ): string {
		return self::link( get_the_title( $en ), (string) get_permalink( $en ) ) . $rating . ' · ' . self::link( get_the_title( $de ), (string) get_permalink( $de ) ) . str_replace( '.', ',', $rating );
	}

	/**
	 * Encode the display text of a Markdown link.
	 *
	 * @param string $name Public title.
	 * @param string $url Native permalink.
	 */
	private static function link( string $name, string $url ): string {
		$label = html_entity_decode( wp_strip_all_tags( $name ), ENT_QUOTES | ENT_HTML5, 'UTF-8' );
		return '[' . str_replace( array( '[', ']' ), array( '\\[', '\\]' ), $label ) . '](' . $url . ')';
	}
}
