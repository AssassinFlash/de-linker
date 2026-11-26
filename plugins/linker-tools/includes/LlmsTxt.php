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
use Linker\Commerce\Storefront\ProductFamilies;

/** Serve the site-root text document before SEOPress's generic recent-posts index. */
final class LlmsTxt {
	public const HEADERS = array(
		'Content-Type'  => 'text/plain; charset=utf-8',
		'X-Robots-Tag'  => 'noindex',
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
		if ( wp_parse_url( $home . '/llms.txt', PHP_URL_PATH ) !== $path ) {
			return $parse;
		}
		do_action( 'litespeed_tag_add', 'PT.product' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- use LiteSpeed's native product archive invalidation.
		do_action( 'litespeed_control_force_public', 'Public bilingual resource directory' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache public API.
		do_action( 'litespeed_control_set_ttl', HOUR_IN_SECONDS ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache public API.
		foreach ( self::HEADERS as $key => $value ) {
			header( $key . ': ' . $value );
		}
		if ( 'HEAD' !== sanitize_text_field( wp_unslash( $_SERVER['REQUEST_METHOD'] ?? 'GET' ) ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the response is Markdown served as text/plain.
			echo self::document( $home );
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
			'Solutions'                    => self::pages( array( 'solution', 'solution/residential-storage', 'solution/commercial-storage', 'solution/utility-storage' ) ),
			'Planning tools and documents' => self::pages( array( 'solution-configurator', 'compare-products', 'faq-download', 'services-support', 'for-installer', 'for-epc', 'about', 'contact' ) ),
			'Product categories'           => self::categories(),
			'Product families'             => self::product_families(),
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
		$lines = array(
			'# Linker Technology GmbH',
			'',
			'> Linker supplies hybrid inverters, battery storage systems and energy management accessories to installers and EPC contractors in Germany and across Europe. The solutions cover residential, commercial, industrial and utility-scale projects.',
			'',
			'Steinfeldstraße 3, 39179 Barleben, Germany · Amtsgericht Stendal HRB 33824 · VAT ID DE367367711',
			'',
			'Sales: ' . ( new Options() )->team_mailbox() . ' · ' . ContactChannels::GERMANY_PHONE,
			'',
			'Direct: ' . ContactChannels::DIRECT_EMAIL . ' · ' . ContactChannels::DIRECT_PHONE . ' · [WhatsApp](' . ContactChannels::WHATSAPP_BASE . ')',
		);
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
	 * List a published representative of each reciprocal model family.
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
		$listed    = array();
		foreach ( ( new ProductFamilies( $english, 'en' ) )->rows( $english ) as $family ) {
			$id = $family['lead'];
			$de = PageUrls::twin( $id, 'de' );
			if ( ! isset( $set[ $de ] ) ) {
				continue;
			}
			$terms  = get_the_terms( $id, 'pa_brand' );
			$brand  = is_array( $terms ) && $terms ? $terms[0]->name : '';
			$series = Materials::english_acf( $id )['product_series'] ?? '';
			$series = is_string( $series ) ? trim( $series ) : '';
			$label  = implode( ' · ', array_unique( array_filter( array( $brand, $series ) ) ) );
			if ( '' !== $series && 0 !== strcasecmp( $brand, $series ) ) {
				if ( isset( $listed[ $label ] ) ) {
					continue;
				}
				$listed[ $label ] = true;
			}
			$facts  = SelectionFacts::for_product( $id );
			$rating = is_float( $facts->ac_power_kw ) ? ' · ' . $facts->ac_power_kw . ' kW' : '';
			if ( is_float( $facts->nominal_kwh ) ) {
				$rating .= ' · ' . $facts->nominal_kwh . ' kWh';
			}
			$rows[] = ( '' !== $label ? $label . ': ' : '' ) . self::post_pair( $id, $de ) . $rating;
		}
		return $rows;
	}

	/**
	 * Pair the native titles and permalinks.
	 *
	 * @param int $en English post ID.
	 * @param int $de German post ID.
	 */
	private static function post_pair( int $en, int $de ): string {
		return self::link( get_the_title( $en ), (string) get_permalink( $en ) ) . ' · ' . self::link( get_the_title( $de ), (string) get_permalink( $de ) );
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
