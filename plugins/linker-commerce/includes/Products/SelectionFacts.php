<?php
/**
 * Reading the selection facts of a product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * The one reading of selection facts (docs/specs/7-selection-facts.md): the
 * product category, the attributes pa_application and pa_phase, and the
 * figures in the product meta _tv_b2b_figures, a JSON object of
 * key => {value, unit, citation?, value_de?}. The Solution Configurator,
 * Genie's search-products and the category filters all use it.
 */
final class SelectionFacts {

	/**
	 * Product meta that holds the figures.
	 */
	public const FIGURES_META_KEY = '_tv_b2b_figures';

	/**
	 * Product categories that are device classes (docs/specs/7-selection-facts.md).
	 * A product in another category takes its nearest listed ancestor: on the
	 * live site (2026-10-09) meters-current-transformers and backup-power are
	 * children of accessories.
	 */
	public const DEVICE_CLASSES = array(
		'inverters',
		'home-storage',
		'battery-systems',
		'all-in-one-systems',
		'ems-monitoring',
		'ev-chargers',
		'accessories',
	);

	/**
	 * Slugs of the pa_application terms that are applications. The third live
	 * term, commercial-industrial, has no product (2026-10-09).
	 */
	public const APPLICATIONS = array( 'home', 'commercial' );

	/**
	 * Figure keys of the rated AC power, in the spec's order; the first present
	 * one decides (docs/specs/7-selection-facts.md).
	 */
	private const AC_POWER_KEYS = array(
		'ac_output_kw_nominal',
		'ac_output_w_nominal',
		'rated_ac_power_kw',
		'nominal_ac_power_kw',
		'rated_power_kw',
		'power_kw',
	);

	/**
	 * Figure key of the maximum PV input power.
	 */
	private const PV_INPUT_KEY = 'max_pv_input_power_w';

	/**
	 * Figure keys of the usable energy; the first present one decides. The
	 * spec's keys (docs/specs/7-selection-facts.md) with a system figure before a
	 * module figure, as in NOMINAL_KEYS, and usable_energy, the key of the SAJ
	 * CB2 batteries (4103–4106); usable_energy_kwh is on draft products only.
	 */
	private const USABLE_KEYS = array(
		'system_usable_energy_kwh',
		'usable_energy_kwh',
		'usable_energy',
		'module_energy_kwh_usable',
	);

	/**
	 * Figure keys of the nominal energy; the first present one decides. The
	 * spec's keys (docs/specs/7-selection-facts.md) and rated_energy_kwh, with the
	 * product's own figure before the figure of one of its modules: GoodWe
	 * GW61.4-BAT-AC-G10 (1954) states module_energy_kwh_nominal 10.24 and
	 * system_nominal_energy_kwh 61.4, GW208.9-BAT-LC-G10 (1956) states 52.24 per
	 * module and rated_energy_kwh 208.9.
	 */
	private const NOMINAL_KEYS = array(
		'system_capacity_kwh_nominal',
		'system_nominal_energy_kwh',
		'system_energy_kwh_nominal',
		'rated_energy_kwh',
		'rated_energy',
		'energy_kwh',
		'battery_rated_energy',
		'module_energy_kwh_nominal',
	);

	/**
	 * Figure key of the energy range a system can be built to; ranges never go
	 * into a scalar (docs/specs/7-selection-facts.md).
	 */
	private const ENERGY_RANGE_KEY = 'system_energy_kwh_range';

	/**
	 * Figure keys of the grid connection; the first present one decides.
	 */
	private const PHASE_KEYS = array( 'phase', 'phases' );

	/**
	 * The selection facts of a product. A product of another language than
	 * the facts' source carries no facts of its own; the
	 * `linker_commerce_facts_product_id` filter lets the language layer swap
	 * in the source-language twin (one fact per product: the English one).
	 *
	 * @param int $product_id Product ID.
	 */
	public static function for_product( int $product_id ): SelectionFactSet {
		if ( \function_exists( 'has_filter' ) && has_filter( 'linker_commerce_facts_product_id' ) ) {
			/**
			 * Filters the product the selection facts answer for: the language
			 * layer swaps in the source-language twin of a translated product.
			 * Without a listener (no language layer, unit tests) the asked-for
			 * product answers itself.
			 *
			 * @since 0.1.0
			 *
			 * @param int $product_id The product ID asked for.
			 */
			$product_id = (int) apply_filters( 'linker_commerce_facts_product_id', $product_id );
		}
		return self::from_figures( $product_id, self::figures( $product_id ) );
	}

	/**
	 * Derive facts from the caller's authorized figure set without rereading raw meta.
	 *
	 * Engineering/knowledge consumers supply only current permitted evidence.
	 * Native Woo categories and attributes remain the source for classification.
	 *
	 * @param int          $product_id Canonical product ID.
	 * @param array<mixed> $figures Authorized figure entries.
	 */
	public static function from_figures( int $product_id, array $figures ): SelectionFactSet {
		list( $ac_power_kw, $ac_apparent )   = self::ac_power( $figures );
		list( $usable_kwh, $usable_range )   = self::energy( $figures, self::USABLE_KEYS );
		list( $nominal_kwh, $nominal_range ) = self::energy( $figures, self::NOMINAL_KEYS );

		return new SelectionFactSet(
			self::device_class( $product_id ),
			self::application( $product_id ),
			self::phase( $product_id, $figures ),
			$ac_power_kw,
			self::power_kw( $figures, self::PV_INPUT_KEY ),
			$usable_kwh,
			$nominal_kwh,
			self::energy_range( $figures ) ?? $nominal_range ?? $usable_range,
			$ac_apparent
		);
	}

	/**
	 * The device class: the product category, or its nearest ancestor, that is
	 * listed in DEVICE_CLASSES; unknown when there is none or the product's
	 * categories lead to more than one.
	 *
	 * @param int $product_id Product ID.
	 * @return value-of<self::DEVICE_CLASSES>|'unknown'
	 */
	private static function device_class( int $product_id ): string {
		$terms   = get_the_terms( $product_id, 'product_cat' );
		$classes = array();
		foreach ( is_array( $terms ) ? $terms : array() as $term ) {
			$class = self::listed_category( $term->term_id, $term->slug );
			if ( null !== $class ) {
				$classes[ $class ] = true;
			}
		}
		$class = array_key_first( $classes );

		return 1 === count( $classes ) && null !== $class ? $class : SelectionFactSet::UNKNOWN;
	}

	/**
	 * The category itself when it is a device class, otherwise its nearest
	 * ancestor that is one.
	 *
	 * @param int    $term_id Category term ID.
	 * @param string $slug    Category slug.
	 * @return value-of<self::DEVICE_CLASSES>|null
	 */
	private static function listed_category( int $term_id, string $slug ): ?string {
		if ( in_array( $slug, self::DEVICE_CLASSES, true ) ) {
			return $slug;
		}
		foreach ( get_ancestors( $term_id, 'product_cat', 'taxonomy' ) as $ancestor_id ) {
			$ancestor = get_term_field( 'slug', $ancestor_id, 'product_cat' );
			if ( is_string( $ancestor ) && in_array( $ancestor, self::DEVICE_CLASSES, true ) ) {
				return $ancestor;
			}
		}

		return null;
	}

	/**
	 * The application: the product's single pa_application term when it is one
	 * of APPLICATIONS, otherwise unknown.
	 *
	 * @param int $product_id Product ID.
	 * @return 'home'|'commercial'|'unknown'
	 */
	private static function application( int $product_id ): string {
		$slugs = self::term_slugs( $product_id, 'pa_application' );
		if ( 1 === count( $slugs ) ) {
			foreach ( self::APPLICATIONS as $application ) {
				if ( $application === $slugs[0] ) {
					return $application;
				}
			}
		}

		return SelectionFactSet::UNKNOWN;
	}

	/**
	 * The number of phases: from the pa_phase terms, otherwise from the first
	 * present phase figure.
	 *
	 * @param int          $product_id Product ID.
	 * @param array<mixed> $figures    Decoded figures.
	 * @return 1|3|'unknown'
	 */
	private static function phase( int $product_id, array $figures ): int|string {
		$phase = self::phase_count( implode( ' ', self::term_slugs( $product_id, 'pa_phase' ) ) );
		if ( null !== $phase ) {
			return $phase;
		}
		foreach ( self::PHASE_KEYS as $key ) {
			$entry = self::entry( $figures, $key );
			if ( null !== $entry ) {
				return ( is_string( $entry['value'] ) ? self::phase_count( $entry['value'] ) : null ) ?? SelectionFactSet::UNKNOWN;
			}
		}

		return SelectionFactSet::UNKNOWN;
	}

	/**
	 * Reads the number of phases from a text. It knows the words ("three-phase",
	 * "Three Phase", "single-phase") and the conductor notation ("3L+N+PE",
	 * "3/N/PE", "3+N+PE", "1/N/PE", "L+N+PE"); a voltage such as "230 V" says
	 * nothing about it. A text that names both counts says nothing either.
	 *
	 * @param string $text Attribute slugs or a figure value.
	 * @return 1|3|null
	 */
	private static function phase_count( string $text ): ?int {
		$counts = array();
		if ( 1 === preg_match( '/\bthree[\s-]*phase/i', $text ) ) {
			$counts[3] = true;
		}
		if ( 1 === preg_match( '/\bsingle[\s-]*phase/i', $text ) ) {
			$counts[1] = true;
		}
		// Datasheet wiring notation like 1P2W or 3P3W/3P4W: the conductor
		// count before P is the grid phase count (the live facet counted it).
		if ( preg_match_all( '/(?<![\w.])([13])P[234]W/i', $text, $wiring ) > 0 ) {
			foreach ( $wiring[1] as $lines ) {
				$counts[ '3' === $lines ? 3 : 1 ] = true;
			}
		}
		// The line conductors come first: a digit not inside a number, or a bare L (one line).
		if ( preg_match_all( '/(?<![\w.])(?:([13])\s*L?|L)\s*[+\/]\s*N\s*[+\/]\s*PE\b/i', $text, $matches ) > 0 ) {
			foreach ( $matches[1] as $lines ) {
				$counts[ '3' === $lines ? 3 : 1 ] = true;
			}
		}

		return 1 === count( $counts ) ? array_key_first( $counts ) : null;
	}

	/**
	 * The rated AC power in kW from the first present AC power figure, and that
	 * figure in kVA when its unit is an apparent-power unit.
	 *
	 * @param array<mixed> $figures Decoded figures.
	 * @return array{0: float|'unknown', 1: float|null}
	 */
	private static function ac_power( array $figures ): array {
		foreach ( self::AC_POWER_KEYS as $key ) {
			$entry = self::entry( $figures, $key );
			if ( null === $entry ) {
				continue;
			}
			$kw = Units::power_kw( $entry['value'], $entry['unit'] );

			return null === $kw
				? array( SelectionFactSet::UNKNOWN, Units::apparent_power_kva( $entry['value'], $entry['unit'] ) )
				: array( $kw, null );
		}

		return array( SelectionFactSet::UNKNOWN, null );
	}

	/**
	 * A power figure in kW.
	 *
	 * @param array<mixed> $figures Decoded figures.
	 * @param string       $key     Figure key.
	 * @return float|'unknown'
	 */
	private static function power_kw( array $figures, string $key ): float|string {
		$entry = self::entry( $figures, $key );

		return ( null === $entry ? null : Units::power_kw( $entry['value'], $entry['unit'] ) ) ?? SelectionFactSet::UNKNOWN;
	}

	/**
	 * The energy in kWh from the first present of the keys. When that figure is
	 * a range, the scalar stays unknown and the range is returned beside it.
	 *
	 * @param array<mixed> $figures Decoded figures.
	 * @param string[]     $keys    Figure keys in order of precedence.
	 * @return array{0: float|'unknown', 1: array{min: float, max: float}|null}
	 */
	private static function energy( array $figures, array $keys ): array {
		foreach ( $keys as $key ) {
			$entry = self::entry( $figures, $key );
			if ( null === $entry ) {
				continue;
			}
			$range = Units::energy_range_kwh( $entry['value'], $entry['unit'] );

			return null === $range
				? array( Units::energy_kwh( $entry['value'], $entry['unit'] ) ?? SelectionFactSet::UNKNOWN, null )
				: array( SelectionFactSet::UNKNOWN, $range );
		}

		return array( SelectionFactSet::UNKNOWN, null );
	}

	/**
	 * The system energy range figure in kWh.
	 *
	 * @param array<mixed> $figures Decoded figures.
	 * @return array{min: float, max: float}|null
	 */
	private static function energy_range( array $figures ): ?array {
		$entry = self::entry( $figures, self::ENERGY_RANGE_KEY );

		return null === $entry ? null : Units::energy_range_kwh( $entry['value'], $entry['unit'] );
	}

	/**
	 * A figure that is present: an object with a value that is not empty.
	 *
	 * @param array<mixed> $figures Decoded figures.
	 * @param string       $key     Figure key.
	 * @return array{value: mixed, unit: mixed}|null
	 */
	private static function entry( array $figures, string $key ): ?array {
		$entry = $figures[ $key ] ?? null;
		if ( ! is_array( $entry ) ) {
			return null;
		}
		$value = $entry['value'] ?? null;
		if ( null === $value || ( is_string( $value ) && '' === trim( $value ) ) ) {
			return null;
		}

		return array(
			'value' => $value,
			'unit'  => $entry['unit'] ?? null,
		);
	}

	/**
	 * The product's figures, decoded.
	 *
	 * @param int $product_id Product ID.
	 * @return array<mixed>
	 */
	private static function figures( int $product_id ): array {
		$figures = get_post_meta( $product_id, self::FIGURES_META_KEY, true );
		if ( is_string( $figures ) ) {
			$figures = json_decode( $figures, true );
		}

		return is_array( $figures ) ? $figures : array();
	}

	/**
	 * Slugs of the product's terms in a taxonomy.
	 *
	 * @param int    $product_id Product ID.
	 * @param string $taxonomy   Taxonomy.
	 * @return list<string>
	 */
	private static function term_slugs( int $product_id, string $taxonomy ): array {
		$terms = get_the_terms( $product_id, $taxonomy );
		$slugs = array();
		foreach ( is_array( $terms ) ? $terms : array() as $term ) {
			$slugs[] = $term->slug;
		}

		return $slugs;
	}
}
