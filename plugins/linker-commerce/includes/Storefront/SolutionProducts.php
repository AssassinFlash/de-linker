<?php
/**
 * Published equipment for the site's solution pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;

/** Resolve the editorial selection by Woo item number in the visitor's language. */
final class SolutionProducts {
	private const SKUS = array(
		'hub'         => array( 'DLK-GOODWE-GW10KETAG20', 'DLK-SAJ-B2100HV1', 'DLK-SAJ-CHS250KT6X', 'DLK-GOODWE-GW2612BATLCDG10', 'DLK-GOODWE-ETR125', 'DLK-PYLONTECH-OPTIMUSL260OMNI' ),
		'residential' => array( 'DLK-GOODWE-GW10KETAG20', 'DLK-GOODWE-GW83BATDG20', 'DLK-SAJ-HS26KT2X', 'DLK-SAJ-HS38KT2WP', 'DLK-SAJ-H210KT3', 'DLK-SAJ-B2100HV1' ),
		'commercial'  => array( 'DLK-GOODWE-GW100KETRG10', 'DLK-GOODWE-GW75KETG10', 'DLK-GOODWE-GW1126BATACG10', 'DLK-SAJ-CHS250KT6X', 'DLK-SAJ-CB21003HV5', 'DLK-PYLONTECH-OPTIMUSL260OMNI' ),
		'utility'     => array( 'DLK-GOODWE-GW2612BATLCDG10', 'DLK-GOODWE-GW2089BATLCDG10', 'DLK-GOODWE-GW100KETRG10', 'DLK-GOODWE-ETR125', 'DLK-PYLONTECH-OPTIMUSL260OMNI' ),
	);

	/**
	 * Cache only within this page render so the visible links and ItemList agree.
	 *
	 * @var array<string,list<array{id:int,name:string,url:string,rating:string}>>
	 */
	private static array $selections = array();

	/**
	 * Localized featured products, in editorial order.
	 *
	 * @param string $scope Solution scope.
	 * @return list<array{id:int,name:string,url:string,rating:string}>
	 */
	public static function featured( string $scope ): array {
		if ( ! isset( self::SKUS[ $scope ] ) ) {
			return array();
		}
		$lang = function_exists( 'pll_current_language' ) ? (string) pll_current_language() : '';
		$key  = $lang . ':' . $scope;
		if ( ! isset( self::$selections[ $key ] ) ) {
			$ids = array();
			foreach ( self::SKUS[ $scope ] as $sku ) {
				$id = wc_get_product_id_by_sku( $sku );
				if ( $id ) {
					$ids[] = '' !== $lang ? (int) pll_get_post( $id, $lang ) : $id;
				}
			}
			self::$selections[ $key ] = self::links( Publication::published_ids( $ids ) );
		}
		return self::$selections[ $key ];
	}

	/**
	 * Display names and rated power or energy for published models.
	 *
	 * @param int[] $ids Published localized product IDs.
	 * @return list<array{id:int,name:string,url:string,rating:string}>
	 */
	public static function links( array $ids ): array {
		$rows = array();
		foreach ( $ids as $id ) {
			$product = wc_get_product( $id );
			if ( ! $product instanceof \WC_Product || 'hidden' === $product->get_catalog_visibility() ) {
				continue;
			}
			$model = trim( $product->get_attribute( 'pa_brand' ) . ' ' . $product->get_attribute( 'pa_model' ) );
			$facts = SelectionFacts::for_product( $id );
			$power = is_float( $facts->ac_power_kw );
			$value = $power ? $facts->ac_power_kw : $facts->nominal_kwh;
			if ( ! is_float( $value ) ) {
				$value = $facts->usable_kwh;
			}
			$rows[] = array(
				'id'     => $id,
				'name'   => '' !== $product->get_attribute( 'pa_model' ) ? $model : wp_specialchars_decode( $product->get_name(), ENT_QUOTES ),
				'url'    => $product->get_permalink(),
				'rating' => is_float( $value ) ? wc_format_localized_decimal( (string) $value ) . ( $power ? ' kW' : ' kWh' ) : '',
			);
		}
		return $rows;
	}
}
