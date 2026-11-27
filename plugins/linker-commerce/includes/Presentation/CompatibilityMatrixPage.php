<?php
/**
 * Public inverter and battery declarations, accessories and grid certificates.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Storefront\ProductView;

/** Server-rendered compatibility reference in the current page language. */
final class CompatibilityMatrixPage {
	/** Register the matrix and its localized entry. */
	public function register(): void {
		add_shortcode( 'linker_compatibility_matrix', array( $this, 'render' ) );
		add_shortcode( 'linker_compatibility_matrix_link', array( $this, 'link' ) );
	}

	/**
	 * Link to the published language twin.
	 *
	 * @param string|array<string,string> $atts LiveCanvas attributes.
	 */
	public function link( $atts = array() ): string {
		$url = PageUrls::translated( 'inverter-battery-compatibility' );
		if ( '' === $url ) {
			return '';
		}
		$atts = shortcode_atts(
			array(
				'class' => '',
				'label' => __( 'Compatibility matrix', 'linker-commerce' ),
			),
			$atts
		);
		return '<a class="' . esc_attr( $atts['class'] ) . '" href="' . esc_url( $url ) . '">' . esc_html( $atts['label'] ) . '</a>';
	}

	/** Project the current public Woo revision into the reference tables. */
	public function render(): string {
		do_action( 'litespeed_tag_add', 'PT.product' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Invalidate the matrix when a product changes.
		$manifest = CompatibilityIndex::manifest();
		$claims   = CompatibilityIndex::declarations( $manifest );
		$language = Materials::locale();
		$view     = new ProductView();
		$products = array();
		foreach ( $manifest['products'] as $item ) {
			$source = (int) $item['product_id'];
			$id     = $item['locale_product_ids'][ $language ] ?? 0;
			if ( ! $id || ! in_array( $id, $item['published_locale_ids'], true ) || '' !== $item['engineering_role'] ) {
				continue;
			}
			$facts   = SelectionFacts::for_product( $source );
			$ratings = array();
			if ( is_float( $facts->ac_power_kw ) ) {
				$ratings[] = Materials::de_number( (string) $facts->ac_power_kw ) . ' kW';
			}
			if ( is_int( $facts->phase ) ) {
				$ratings[] = 3 === $facts->phase ? __( 'Three-phase', 'linker-commerce' ) : __( 'Single-phase', 'linker-commerce' );
			}
			$certificates = array();
			foreach ( $view->downloads( $id, $manifest ) as $doc ) {
				$standards = CompatibilityIndex::document_standards( $doc );
				if ( $standards ) {
					$certificates[] = array(
						'url'       => $doc['url'],
						'standards' => $standards,
					);
				}
			}
			$categories          = get_the_terms( $id, 'product_cat' );
			$products[ $source ] = array(
				'name'         => trim( $item['brand'] . ' ' . $item['model'] ),
				'url'          => get_permalink( $id ),
				'application'  => $facts->application,
				'series'       => $item['brand'] . ' ' . ( Materials::english_acf( $source )['product_series'] ?? $item['model'] ),
				'rating'       => implode( ' · ', $ratings ),
				'category'     => is_array( $categories ) ? implode( ', ', wp_list_pluck( $categories, 'name' ) ) : '',
				'certificates' => $certificates,
			);
		}
		$documents = array();
		foreach ( $manifest['documents'] as $doc ) {
			$path               = (string) wp_parse_url( $doc['url'], PHP_URL_PATH );
			$documents[ $path ] = array(
				'url'  => $doc['url'],
				'name' => Materials::localized_document_title( $doc['title'], null, $doc['url'] ),
			);
		}
		return self::body( $products, $claims, $documents );
	}

	/**
	 * Localized public models, declarations and their document references.
	 *
	 * @param array<int,array<string,mixed>>     $products Sales models keyed by canonical ID.
	 * @param array<string,mixed>                $claims Current declarations.
	 * @param array<string,array<string,string>> $documents Published PDFs keyed by uploads path.
	 */
	public static function body( array $products, array $claims, array $documents ): string {
		$sections        = array(
			'residential-pairings'    => __( 'Residential inverter and battery pairings', 'linker-commerce' ),
			'commercial-pairings'     => __( 'Commercial and industrial pairings', 'linker-commerce' ),
			'system-requirements'     => __( 'Meters, backup switches and parallel controllers', 'linker-commerce' ),
			'grid-certificates'       => __( 'European grid-code certificates', 'linker-commerce' ),
			'not-released-boundaries' => __( 'Documented non-released combinations', 'linker-commerce' ),
		);
		$tables          = array_fill_keys( array_keys( $sections ), array() );
		$pairs           = array();
		$accessory_pairs = array();
		$boundaries      = array();
		foreach ( $claims['pairs'] as $pair ) {
			$i = $pair['inverter_product_id'];
			$b = $pair['battery_product_id'];
			if ( ! isset( $products[ $i ], $products[ $b ] ) ) {
				continue;
			}
			$inverter = $products[ $i ];
			$battery  = $products[ $b ];
			if ( 'not_released' === $pair['verdict'] ) {
				$group = $inverter['series'] . ' × ' . $battery['series'];
				$boundaries[ $group ][ $inverter['name'] ][ $battery['name'] ] = true;
				continue;
			}
			$section = match ( $inverter['application'] ) {
				'home' => 'residential-pairings',
				'commercial' => 'commercial-pairings',
				default => '',
			};
			if ( '' === $section || ! in_array( $pair['verdict'], array( 'released', 'released_with_accessory' ), true ) || array_diff( array_column( $pair['accessories'], 'product_id' ), array_keys( $products ) ) ) {
				continue;
			}
			$key             = $i . ':' . $b;
			$pairs[ $key ]   = true;
			$needs_accessory = 'released_with_accessory' === $pair['verdict'];
			if ( $needs_accessory ) {
				$accessory_pairs[ $key ] = true;
			}
			$status               = $needs_accessory ? __( 'Accessory required', 'linker-commerce' ) : __( 'Released', 'linker-commerce' );
			$tables[ $section ][] = array(
				self::product_link( $inverter ) . '<small>' . esc_html( $inverter['rating'] ) . '</small>',
				self::product_link( $battery ),
				'<span class="lk-matrix-status' . ( $needs_accessory ? ' lk-matrix-accessory' : '' ) . '">' . esc_html( $status ) . '</span>',
				self::conditions( $pair, $products ),
				self::sources( $pair['documents'], $documents ),
			);
		}
		$kinds = array(
			'meter'               => __( 'Smart meter', 'linker-commerce' ),
			'backup'              => __( 'Backup switch', 'linker-commerce' ),
			'parallel_controller' => __( 'Parallel controller', 'linker-commerce' ),
		);
		foreach ( $claims['requirements'] as $rule ) {
			$id = $rule['inverter_product_id'];
			if ( ! isset( $products[ $id ] ) || array_diff( array_column( $rule['accessories'], 'product_id' ), array_keys( $products ) ) ) {
				continue;
			}
			$tables['system-requirements'][] = array(
				self::product_link( $products[ $id ] ),
				esc_html( $kinds[ $rule['kind'] ] ),
				$rule['included'] ? esc_html__( 'Included', 'linker-commerce' ) : esc_html__( 'Supplied separately', 'linker-commerce' ),
				self::conditions( $rule, $products ),
				self::sources( $rule['documents'], $documents ),
			);
		}
		$certificate_urls = array();
		foreach ( $products as $product ) {
			$standards = array();
			$links     = array();
			foreach ( $product['certificates'] as $pdf ) {
				$certificate_urls[ $pdf['url'] ] = true;
				$standards                       = array_merge( $standards, $pdf['standards'] );
				$links[]                         = self::sources( array( $pdf ), $documents );
			}
			if ( $links ) {
				$tables['grid-certificates'][] = array( self::product_link( $product ), esc_html( implode( ' · ', array_filter( array( $product['category'], $product['rating'] ) ) ) ), esc_html( implode( ', ', array_unique( $standards ) ) ), implode( '', $links ) );
			}
		}
		$kpis  = array(
			__( 'Released model pairs', 'linker-commerce' ) => count( $pairs ),
			__( 'Pairs requiring an accessory', 'linker-commerce' ) => count( $accessory_pairs ),
			__( 'System requirements', 'linker-commerce' ) => count( $tables['system-requirements'] ),
			__( 'Grid-code certificate PDFs', 'linker-commerce' ) => count( $certificate_urls ),
		);
		$title = __( 'Inverter & HV Battery Compatibility Matrix', 'linker-commerce' );
		$html  = '<div id="linker-compatibility-matrix" class="lk-matrix"><nav class="lk-matrix-crumb" aria-label="' . esc_attr__( 'Breadcrumb', 'linker-commerce' ) . '"><a href="' . esc_url( PageUrls::home() ) . '">' . esc_html_x( 'Home', 'breadcrumb', 'linker-commerce' ) . '</a> / <span aria-current="page">' . esc_html__( 'Compatibility matrix', 'linker-commerce' ) . '</span></nav><header><h1>' . esc_html( $title ) . '</h1><p>' . sprintf(
			/* translators: 1: number of distinct model pairs, 2: number requiring an accessory. */
			esc_html__( 'The manufacturer documents cover %1$d inverter and battery combinations. Of these, %2$d require an accessory. Find the inverter model to see which batteries it supports and which control modules it needs. Each entry links to its source. The meter and backup requirements and grid-code certificates are listed separately for the models they cover.', 'linker-commerce' ),
			count( $pairs ),
			count( $accessory_pairs )
		) . '</p><dl class="lk-matrix-kpis">';
		foreach ( $kpis as $label => $value ) {
			$html .= '<div><dt>' . esc_html( $label ) . '</dt><dd>' . (int) $value . '</dd></div>';
		}
		$html .= '</dl></header><nav class="lk-matrix-anchors" aria-label="' . esc_attr__( 'On this page', 'linker-commerce' ) . '">';
		foreach ( $sections as $id => $label ) {
			$html .= '<a href="#' . esc_attr( $id ) . '">' . esc_html( $label ) . '</a>';
		}
		$html                          .= '</nav>';
		$headers                        = array(
			'residential-pairings' => array( __( 'Inverter (power and phase)', 'linker-commerce' ), __( 'Compatible HV battery', 'linker-commerce' ), __( 'Release status', 'linker-commerce' ), __( 'Accessory and conditions', 'linker-commerce' ), __( 'Manufacturer document', 'linker-commerce' ) ),
			'system-requirements'  => array( __( 'Inverter', 'linker-commerce' ), __( 'Accessory role', 'linker-commerce' ), __( 'Scope', 'linker-commerce' ), __( 'Accessory and conditions', 'linker-commerce' ), __( 'Manufacturer document', 'linker-commerce' ) ),
			'grid-certificates'    => array( __( 'Brand and model', 'linker-commerce' ), __( 'Category and rating', 'linker-commerce' ), __( 'Verified standards', 'linker-commerce' ), __( 'Certificate PDFs', 'linker-commerce' ) ),
		);
		$headers['commercial-pairings'] = $headers['residential-pairings'];
		foreach ( $sections as $id => $label ) {
			$html .= '<section id="' . esc_attr( $id ) . '"><h2>' . esc_html( $label ) . '</h2>';
			if ( 'not-released-boundaries' === $id ) {
				$html .= '<p>' . esc_html__( 'For the specific models below, the cited documents do not establish a release. Open a series to see the exact models.', 'linker-commerce' ) . '</p>';
				ksort( $boundaries, SORT_NATURAL | SORT_FLAG_CASE );
				foreach ( $boundaries as $group => $models ) {
					$html .= '<details class="lk-matrix-details"><summary>' . esc_html( $group ) . '</summary><dl>';
					ksort( $models, SORT_NATURAL | SORT_FLAG_CASE );
					foreach ( $models as $name => $batteries ) {
						ksort( $batteries, SORT_NATURAL | SORT_FLAG_CASE );
						$html .= '<dt>' . esc_html( $name ) . '</dt><dd>' . esc_html( implode( ', ', array_keys( $batteries ) ) ) . '</dd>';
					}
					$html .= '</dl></details>';
				}
			} else {
				$html .= self::table( $label, $headers[ $id ], $tables[ $id ] );
			}
			$html .= '</section>';
		}
		$html .= '<footer class="lk-matrix-handoff">';
		foreach ( array(
			'solution-configurator' => __( 'Solution Configurator', 'linker-commerce' ),
			'faq-download'          => __( 'FAQ and documents', 'linker-commerce' ),
			'contact'               => __( 'Contact', 'linker-commerce' ),
		) as $slug => $label ) {
			$url = PageUrls::translated( $slug );
			if ( '' !== $url ) {
				$html .= '<a href="' . esc_url( $url ) . '">' . esc_html( $label ) . '</a>';
			}
		}
		return $html . '</footer></div>';
	}

	/**
	 * Published product permalink and model.
	 *
	 * @param array<string,mixed> $product Localized public model.
	 */
	private static function product_link( array $product ): string {
		return '<a href="' . esc_url( $product['url'] ) . '">' . esc_html( $product['name'] ) . '</a>';
	}

	/**
	 * Quantities and manufacturer conditions applying to the declaration.
	 *
	 * @param array<string,mixed>            $row Manufacturer declaration.
	 * @param array<int,array<string,mixed>> $products Sales models.
	 */
	private static function conditions( array $row, array $products ): string {
		$lines = array();
		$basis = array(
			'stack'  => __( 'per stack', 'linker-commerce' ),
			'system' => __( 'per system', 'linker-commerce' ),
			'unit'   => __( 'per unit', 'linker-commerce' ),
		);
		foreach ( $row['accessories'] as $part ) {
			$lines[] = self::product_link( $products[ $part['product_id'] ] ) . ' × ' . (int) $part['quantity'] . ' ' . esc_html( $basis[ $part['per'] ] );
		}
		if ( isset( $row['modules'] ) ) {
			/* translators: 1 and 2: minimum and maximum number of battery modules. */
			$lines[] = sprintf( esc_html__( '%1$d–%2$d battery modules', 'linker-commerce' ), $row['modules']['min'], $row['modules']['max'] );
		}
		foreach ( $row['conditions'] as $condition ) {
			$lines[] = esc_html( Materials::apply_terms( $condition[ Materials::locale() ] ) );
		}
		return implode( '<br>', $lines );
	}

	/**
	 * Link each statement to its cited file and page.
	 *
	 * @param array<int,array<string,mixed>>     $sources Document URLs and optional cited page.
	 * @param array<string,array<string,string>> $documents Public documents keyed by local path.
	 */
	private static function sources( array $sources, array $documents ): string {
		$html = '';
		foreach ( $sources as $source ) {
			$doc = $documents[ (string) wp_parse_url( $source['url'], PHP_URL_PATH ) ] ?? null;
			if ( ! $doc ) {
				continue;
			}
			$url  = $doc['url'];
			$name = $doc['name'];
			if ( isset( $source['page'] ) ) {
				$url .= '#page=' . (int) $source['page'];
				/* translators: %d: PDF page number. */
				$name .= ', ' . sprintf( __( 'p. %d', 'linker-commerce' ), $source['page'] );
			}
			$html .= '<a class="lk-matrix-source" href="' . esc_url( $url ) . '" target="_blank" rel="noopener">' . esc_html( $name ) . '</a>';
		}
		return $html;
	}

	/**
	 * Semantic comparison with a scrollable table on narrow screens.
	 *
	 * @param string                  $title Section title.
	 * @param array<int,string>       $columns Column headings.
	 * @param array<int,list<string>> $rows Escaped display cells.
	 */
	private static function table( string $title, array $columns, array $rows ): string {
		$html = '<div class="lk-matrix-table-wrap" role="region" tabindex="0" aria-label="' . esc_attr( $title ) . '"><table><thead><tr>';
		foreach ( $columns as $column ) {
			$html .= '<th scope="col">' . esc_html( $column ) . '</th>';
		}
		$html .= '</tr></thead><tbody>';
		usort( $rows, static fn ( $a, $b ) => strnatcasecmp( wp_strip_all_tags( $a[0] . ' ' . $a[1] ), wp_strip_all_tags( $b[0] . ' ' . $b[1] ) ) );
		foreach ( $rows as $row ) {
			$html .= '<tr><th scope="row">' . array_shift( $row ) . '</th><td>' . implode( '</td><td>', $row ) . '</td></tr>';
		}
		return $html . '</tbody></table></div>';
	}
}
