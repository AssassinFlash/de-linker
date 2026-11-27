<?php
/**
 * Model-specific descriptions for shared product photographs.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;

/** Product gallery and social card image descriptions. */
final class ProductImageAlt {
	/**
	 * Describe the model pictured using its published figures and localized category.
	 *
	 * @param int    $id Product in the reader's language.
	 * @param string $title Localized product title.
	 */
	public static function main( int $id, string $title ): string {
		$title = trim( wp_strip_all_tags( $title ) );
		if ( preg_match( '/\([^)]*\d[^)]*\)/', $title ) ) {
			return $title;
		}
		$details = array();
		$source  = Publication::canonical_id( $id );
		if ( get_post_meta( $source, SelectionFacts::FIGURES_META_KEY, true ) ) {
			$facts = SelectionFacts::from_figures( $source, Publication::figures_in_manifest( $source, CompatibilityIndex::manifest() ) );
			if ( is_float( $facts->ac_power_kw ) ) {
				$details[] = Materials::de_number( (string) $facts->ac_power_kw ) . ' kW';
			} elseif ( is_float( $facts->usable_kwh ) || is_float( $facts->nominal_kwh ) ) {
				$details[] = Materials::de_number( (string) ( is_float( $facts->usable_kwh ) ? $facts->usable_kwh : $facts->nominal_kwh ) ) . ' kWh';
			} elseif ( null !== $facts->kwh_range ) {
				$details[] = Materials::de_number( (string) $facts->kwh_range['min'] ) . '–' . Materials::de_number( (string) $facts->kwh_range['max'] ) . ' kWh';
			}
			if ( is_int( $facts->phase ) ) {
				$details[] = 3 === $facts->phase ? __( 'three-phase', 'linker-commerce' ) : __( 'single-phase', 'linker-commerce' );
			}
		}
		$categories = get_the_terms( $id, 'product_cat' );
		if ( is_array( $categories ) && $categories ) {
			$parents = wp_list_pluck( $categories, 'parent' );
			foreach ( $categories as $category ) {
				if ( in_array( $category->term_id, $parents, true ) ) {
					continue;
				}
				if ( false === stripos( $title, $category->name ) ) {
					$details[] = $category->name;
				}
				break;
			}
		}
		return $details ? $title . ' — ' . implode( ', ', $details ) : $title;
	}
}
