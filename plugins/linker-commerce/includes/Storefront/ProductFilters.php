<?php
/**
 * The product archive's filter rail.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\ProductSearch;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Products\SelectionFacts;

/**
 * The facets of the product category pages and the shop page, and the
 * filtering and sorting they ask for (docs/specs/12-site-chrome.md item 5).
 * Both the counts and the filtering derive from the selection facts — the
 * one reader of what a product is (#7) — so the configurator and Genie
 * select by the same numbers the visitor filters by.
 *
 * The visitor's request states the facets as the old filter's addresses
 * did (application, brand, phase, power, kw_min, kw_max, kwh_min, kwh_max,
 * sort), so an indexed link keeps working.
 */
final class ProductFilters {

	/**
	 * The power buckets, as the old filter's addresses named them: low up
	 * to 6 kW, mid 6 to 15, high 15 to 30, top over 30.
	 */
	private const POWER_BUCKETS = array(
		'low'  => array( null, 6.0 ),
		'mid'  => array( 6.0, 15.0 ),
		'high' => array( 15.0, 30.0 ),
		'top'  => array( 30.0, null ),
	);

	/**
	 * The sorts the old results strip offered, minus the one that has no
	 * source anymore: `efficiency` read the old registry; the selection
	 * facts carry no efficiency (#7), so the option waits for a fact that
	 * states one.
	 */
	private const SORTS = array( 'recommended', 'newest', 'name', 'power-desc', 'power-asc' );

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'pre_get_posts', array( $this, 'filter' ), 99 );
	}

	/**
	 * Narrows and orders the product archive's query to the products the
	 * request's facets select.
	 *
	 * @param \WP_Query $query The running query.
	 */
	public function filter( \WP_Query $query ): void {
		if ( is_admin() || ! $query->is_main_query() ) {
			return;
		}
		if ( ! $query->is_post_type_archive( 'product' ) && ! $query->is_tax( get_object_taxonomies( 'product', 'names' ) ) ) {
			return;
		}
		$selected = $this->requested();
		$sort     = $this->requested_sort();
		if ( array() === $selected && 'recommended' === $sort ) {
			return;
		}
		$matching = $this->matching( $this->archive_product_ids(), $selected );
		// The empty set is a real answer ("no product matches"): an empty
		// result, not the unfiltered archive, must show.
		$query->set( 'post__in', array() === $matching ? array( 0 ) : $this->ordered( $matching, $sort ) );
		$query->set( 'posts_per_page', -1 );
		if ( 'power-desc' === $sort || 'power-asc' === $sort ) {
			$query->set( 'orderby', 'post__in' );
		}
	}

	/**
	 * The facets the request states, and the search box's `q`.
	 *
	 * @return array{application?: string, brand?: string, phase?: string, power?: string, kw_min?: float, kw_max?: float, kwh_min?: float, kwh_max?: float, q?: string} The selected facet values.
	 */
	public function requested(): array {
		$selected = array();
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the filter rail is a plain GET navigation, like the addresses it keeps.
		$get = wp_unslash( $_GET );
		foreach ( array( 'application', 'brand', 'phase', 'power' ) as $facet ) {
			$value = isset( $get[ $facet ] ) ? sanitize_key( (string) $get[ $facet ] ) : '';
			if ( '' !== $value ) {
				$selected[ $facet ] = $value;
			}
		}
		foreach ( array( 'kw_min', 'kw_max', 'kwh_min', 'kwh_max' ) as $bound ) {
			$value = isset( $get[ $bound ] ) ? (float) str_replace( ',', '.', (string) $get[ $bound ] ) : 0.0;
			if ( $value > 0.0 ) {
				$selected[ $bound ] = $value;
			}
		}
		$q = isset( $get['q'] ) ? sanitize_text_field( (string) $get['q'] ) : '';
		if ( '' !== $q ) {
			$selected['q'] = $q;
		}
		return $selected;
	}

	/**
	 * The sort the request asks for, `recommended` when it names none.
	 *
	 * @return value-of<self::SORTS>
	 */
	public function requested_sort(): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the sort select is a plain GET navigation.
		$sort = isset( $_GET['sort'] ) ? sanitize_key( (string) wp_unslash( $_GET['sort'] ) ) : 'recommended';
		return \in_array( $sort, self::SORTS, true ) ? $sort : 'recommended';
	}

	/**
	 * Which of the archive's products a facet selection keeps.
	 *
	 * @param int[]                       $product_ids The archive's products, before the facets.
	 * @param array<string, string|float> $selected    The selected facet values.
	 * @return int[] The product IDs that match every selected facet.
	 */
	public function matching( array $product_ids, array $selected ): array {
		$matching = array();
		foreach ( $product_ids as $product_id ) {
			$facts = SelectionFacts::for_product( (int) $product_id );
			if ( $this->matches( (int) $product_id, $facts, $selected ) ) {
				$matching[] = (int) $product_id;
			}
		}
		return $matching;
	}

	/**
	 * Whether one product's facts answer a facet selection.
	 *
	 * @param int                         $product_id The product.
	 * @param SelectionFactSet            $facts      The product's facts.
	 * @param array<string, string|float> $selected   The selected facet values.
	 */
	private function matches( int $product_id, SelectionFactSet $facts, array $selected ): bool {
		if ( isset( $selected['q'] ) ) {
			$product = wc_get_product( $product_id );
			// The search box's rule, one implementation for the archive and
			// the instant lookup (ProductSearch, ticket #68).
			if ( ! $product instanceof \WC_Product || ! ProductSearch::matches( $product, ProductSearch::normalize( (string) $selected['q'] ) ) ) {
				return false;
			}
		}
		if ( isset( $selected['application'] ) && $facts->application !== (string) $selected['application'] ) {
			return false;
		}
		if ( isset( $selected['brand'] ) && ! has_term( (string) $selected['brand'], 'pa_brand', $product_id ) ) {
			return false;
		}
		if ( isset( $selected['phase'] ) && (string) $facts->phase !== (string) $selected['phase'] ) {
			return false;
		}
		if ( isset( $selected['power'] ) ) {
			$bucket = (string) $selected['power'];
			if ( ! isset( self::POWER_BUCKETS[ $bucket ] ) || ! \is_float( $facts->ac_power_kw ) || ! $this->in_bucket( $facts->ac_power_kw, self::POWER_BUCKETS[ $bucket ] ) ) {
				return false;
			}
		}
		if ( isset( $selected['kw_min'], $selected['kw_max'] ) && $selected['kw_min'] > $selected['kw_max'] ) {
			return false;
		}
		foreach ( array( 'kw_min', 'kw_max' ) as $bound ) {
			if ( isset( $selected[ $bound ] ) ) {
				if ( ! \is_float( $facts->ac_power_kw ) ) {
					return false;
				}
				if ( 'kw_min' === $bound && $facts->ac_power_kw < (float) $selected[ $bound ] ) {
					return false;
				}
				if ( 'kw_max' === $bound && $facts->ac_power_kw > (float) $selected[ $bound ] ) {
					return false;
				}
			}
		}
		if ( isset( $selected['kwh_min'], $selected['kwh_max'] ) && $selected['kwh_min'] > $selected['kwh_max'] ) {
			return false;
		}
		foreach ( array( 'kwh_min', 'kwh_max' ) as $bound ) {
			if ( isset( $selected[ $bound ] ) ) {
				$energy = \is_float( $facts->usable_kwh ) ? $facts->usable_kwh : $facts->nominal_kwh;
				if ( ! \is_float( $energy ) ) {
					return false;
				}
				if ( 'kwh_min' === $bound && $energy < (float) $selected[ $bound ] ) {
					return false;
				}
				if ( 'kwh_max' === $bound && $energy > (float) $selected[ $bound ] ) {
					return false;
				}
			}
		}
		return true;
	}

	/**
	 * Whether a power sits in a bucket. A range holds the values from its
	 * floor (exclusive) to its ceiling (inclusive): 6 kW is mid, not low.
	 *
	 * @param float                 $power The power in kW.
	 * @param array<int,float|null> $bucket The bucket's floor and ceiling, null for open.
	 */
	private function in_bucket( float $power, array $bucket ): bool {
		$floor   = $bucket[0];
		$ceiling = $bucket[1];
		if ( null !== $floor && $power <= $floor ) {
			return false;
		}
		if ( null !== $ceiling && $power > $ceiling ) {
			return false;
		}
		return true;
	}

	/**
	 * The product IDs in the order a sort asks for. The power sorts order
	 * by the facts' AC power; "Name A-Z" orders by the product's title,
	 * case-insensitively (the live shop's own order under sort=name reads
	 * GW10K-EHA…, GW10K-ETA…, GW125/261…, GW20K-ETA… — plain character
	 * order, not natural-number order: 2026-10-12 capture of
	 * /products/?brand=goodwe&sort=name); the rest keep the archive's own
	 * order (menu order, then title), which WordPress applies when no facet
	 * has narrowed the query.
	 *
	 * @param int[]  $product_ids The matching products.
	 * @param string $sort        One of self::SORTS.
	 * @return int[] The ordered IDs.
	 */
	public function ordered( array $product_ids, string $sort ): array {
		if ( 'name' === $sort ) {
			$titles = array();
			foreach ( $product_ids as $product_id ) {
				$titles[ (int) $product_id ] = (string) get_the_title( (int) $product_id );
			}
			uksort(
				$titles,
				static fn( int $a, int $b ): int => strcasecmp( $titles[ $a ], $titles[ $b ] )
			);
			return array_map( 'intval', array_keys( $titles ) );
		}
		if ( 'power-desc' !== $sort && 'power-asc' !== $sort ) {
			return $product_ids;
		}
		$powers = array();
		foreach ( $product_ids as $product_id ) {
			$facts                 = SelectionFacts::for_product( (int) $product_id );
			$powers[ $product_id ] = \is_float( $facts->ac_power_kw ) ? $facts->ac_power_kw : -1.0;
		}
		if ( 'power-asc' === $sort ) {
			asort( $powers );
		} else {
			arsort( $powers );
		}
		return array_map( 'intval', array_keys( $powers ) );
	}

	/**
	 * The catalogue's default ("Recommended") order, the live page's own:
	 * articles the visitor can act on first, newest within each group, name as
	 * the stable tail (measured on the live shop 2026-10-12: the first card
	 * is the newest invoicable model).
	 *
	 * @param int[] $ids The catalogue's product ids.
	 * @return int[]
	 */
	private function recommended_order( array $ids ): array {
		$rows = array();
		foreach ( $ids as $id ) {
			$product = wc_get_product( $id );
			$rows[]  = array(
				'id'        => (int) $id,
				'can_order' => $product instanceof \WC_Product && $product->is_purchasable() && '' !== (string) $product->get_price() ? 1 : 0,
				'ts'        => (int) get_post_time( 'U', true, (int) $id ),
				'name'      => (string) get_the_title( (int) $id ),
			);
		}
		usort(
			$rows,
			static function ( array $a, array $b ): int {
				if ( $a['can_order'] !== $b['can_order'] ) {
					return $b['can_order'] <=> $a['can_order'];
				}
				if ( $a['ts'] !== $b['ts'] ) {
					return $b['ts'] <=> $a['ts'];
				}
				return strcasecmp( $a['name'], $b['name'] );
			}
		);
		return array_map( static fn( array $row ): int => (int) $row['id'], $rows );
	}

	/**
	 * The facets with the counts and labels the rail shows, for the
	 * archive's products. A facet section lists when the view's own data
	 * answers at least two of its values (the live rail hides a facet whose
	 * every product sits in one value: no Application and no Phase on the
	 * all-in-one archive, Application on the shop and on the accessories
	 * archive — measured 2026-10-12 on the live rail); the power buckets
	 * stay listed, the empty one disabled. Under an active filter the
	 * counts converge: each facet is counted over the products the OTHER
	 * facets select (the live rail's own behaviour — under brand=goodwe the
	 * Phase rows read the goodwe subset, a value nothing answers stays
	 * listed, disabled, at 0), while the sections themselves stay those of
	 * the unfiltered view.
	 *
	 * @param int[]                       $product_ids The archive's products.
	 * @param array<string, string|float> $selected    The request's facet selections.
	 * @return array<string, array<string, array{label: string, count: int}>> The facets with their labels
	 *                                                                        and counts, the thin sections
	 *                                                                        gone. The range folds' presence
	 *                                                                        is range_folds(), not a facet.
	 */
	public function facet_counts( array $product_ids, array $selected = array() ): array {
		$facts = array();
		$by_id = array();
		foreach ( $product_ids as $product_id ) {
			$fact                       = SelectionFacts::for_product( (int) $product_id );
			$facts[]                    = array( (int) $product_id, $fact );
			$by_id[ (int) $product_id ] = $fact;
		}
		$active = \array_diff_key( $selected, array( 'q' => '' ) );

		$counts = array(
			'application' => array(),
			'brand'       => array(),
			'phase'       => array(),
			'power'       => array(),
		);
		foreach ( array(
			'home'       => 'Home',
			'commercial' => 'Commercial',
		) as $value => $label ) {
			$counts['application'][ $value ] = array(
				'label' => __( $label, 'linker-commerce' ), // phpcs:ignore WordPress.WP.I18n.NonSingularStringLiteralText
				'count' => 0,
			);
		}
		foreach ( $facts as $pair ) {
			list( $product_id, $fact ) = $pair;
			if ( SelectionFactSet::UNKNOWN !== $fact->application ) {
				++$counts['application'][ $fact->application ]['count'];
			}
			if ( \is_int( $fact->phase ) ) {
				$key                     = (string) $fact->phase;
				$counts['phase'][ $key ] = $counts['phase'][ $key ] ?? array(
					'label' => sprintf( /* translators: %d: number of grid phases. */ _n( '%d-phase', '%d-phase', $fact->phase, 'linker-commerce' ), $fact->phase ), // phpcs:ignore WordPress.WP.I18n.NonSingularStringLiteralText
					'count' => 0,
				);
				++$counts['phase'][ $key ]['count'];
			}
			if ( \is_float( $fact->ac_power_kw ) ) {
				foreach ( self::POWER_BUCKETS as $bucket => $range ) {
					if ( $this->in_bucket( $fact->ac_power_kw, $range ) ) {
						$counts['power'][ $bucket ] = $counts['power'][ $bucket ] ?? array(
							'label' => $this->power_labels()[ $bucket ],
							'count' => 0,
						);
						++$counts['power'][ $bucket ]['count'];
					}
				}
			}
			$terms = wp_get_post_terms( $pair[0], 'pa_brand' );
			foreach ( \is_array( $terms ) ? $terms : array() as $term ) {
				$counts['brand'][ $term->slug ] = $counts['brand'][ $term->slug ] ?? array(
					'label' => $term->name,
					'count' => 0,
				);
				++$counts['brand'][ $term->slug ]['count'];
			}
		}
		foreach ( $this->power_labels() as $bucket => $label ) {
			$counts['power'][ $bucket ] = $counts['power'][ $bucket ] ?? array(
				'label' => $label,
				'count' => 0,
			);
		}
		// The rail's own order, not the order the products arrived in: the live
		// rail prints Phase as 3-phase then 1-phase and Power from "Up to 6 kW"
		// down to "Over 30 kW" (its $phase_labels / $power_labels arrays,
		// catalogue-archive.php; measured on the live rail 2026-10-12 — t16
		// listed 1-phase first and the power buckets descending, which is the
		// first-encountered order of the archive list).
		$counts['phase'] = $this->in_value_order( $counts['phase'], array( '3', '1' ) );
		$counts['power'] = $this->in_value_order( $counts['power'], array_keys( self::POWER_BUCKETS ) );
		// The brands read A-Z, as the live rail lists them (Chint / EcoFlow /
		// GoodWe / Pylontech / SAJ — measured 2026-10-12).
		uasort(
			$counts['brand'],
			static fn( array $a, array $b ): int => strcasecmp( (string) $a['label'], (string) $b['label'] )
		);
		// The sections themselves come from the view's own data: a section
		// lists when two of the view's values answer on the UNFILTERED set
		// (the live rail's filtered sections are those of the unfiltered
		// page — a value its subset answers zero times stays listed,
		// disabled). Snapshot the full counts before they converge.
		$full_counts = array();
		foreach ( array( 'application', 'brand', 'phase', 'power' ) as $facet ) {
			$full_counts[ $facet ] = $counts[ $facet ];
		}
		// The converged counts: each facet counted over the products every
		// OTHER selected facet keeps.
		foreach ( array( 'application', 'brand', 'phase', 'power' ) as $facet ) {
			$others  = \array_diff_key( $active, array( $facet => '' ) );
			$context = $product_ids;
			if ( array() !== $others ) {
				$context = $this->matching( $product_ids, $others );
			}
			$context_ids = array_fill_keys( array_map( 'intval', $context ), true );
			foreach ( $counts[ $facet ] as $value => $option ) {
				$counts[ $facet ][ $value ]['count'] = $this->facet_value_count( $facet, (string) $value, $product_ids, $context_ids, $by_id );
			}
		}
		// A facet section lists when two of the view's own values answer
		// (power's buckets are exempt — they always list); with a filter
		// active the listed sections keep their zero rows, disabled.
		$keep_empty = array() !== $active;
		foreach ( array( 'application', 'brand', 'phase' ) as $facet ) {
			$answered = \array_filter(
				$full_counts[ $facet ],
				static fn( array $value ): bool => $value['count'] > 0
			);
			if ( \count( $answered ) < 2 ) {
				unset( $counts[ $facet ] );
				continue;
			}
			if ( ! $keep_empty ) {
				$counts[ $facet ] = $answered;
			}
		}
		/** The facets with their labels and counts, the thin sections gone.
		 *
		 * @var array<string, array<string, array{label: string, count: int}>> $facets
		 */
		$facets = $counts;
		return $facets;
	}

	/**
	 * How many of the view's products carry a scalar energy and AC power
	 * value: the live shelf rendered each range fold only when at least
	 * three rows carried the value (ranges alone did not count), so the rail
	 * asks these two numbers before it prints the "AC power" and "Usable
	 * energy" forms.
	 *
	 * @param int[] $product_ids The archive's products.
	 * @return array{has_energy: int, has_power: int} The folds' row counts.
	 */
	public function range_folds( array $product_ids ): array {
		$has_energy = 0;
		$has_power  = 0;
		foreach ( $product_ids as $product_id ) {
			$fact = SelectionFacts::for_product( (int) $product_id );
			if ( \is_float( $fact->usable_kwh ) || \is_float( $fact->nominal_kwh ) ) {
				++$has_energy;
			}
			if ( \is_float( $fact->ac_power_kw ) ) {
				++$has_power;
			}
		}
		return array(
			'has_energy' => $has_energy,
			'has_power'  => $has_power,
		);
	}

	/**
	 * One facet value's converged count: the products the other facets keep
	 * whose facts answer the value.
	 *
	 * @param string                       $facet       The facet's query parameter.
	 * @param string                       $value       The facet value.
	 * @param int[]                        $product_ids The archive's products.
	 * @param array<int, true>             $context_ids The products the other facets keep.
	 * @param array<int, SelectionFactSet> $by_id      Every archive product's facts.
	 */
	private function facet_value_count( string $facet, string $value, array $product_ids, array $context_ids, array $by_id ): int {
		$count = 0;
		foreach ( $product_ids as $product_id ) {
			$product_id = (int) $product_id;
			if ( ! isset( $context_ids[ $product_id ] ) ) {
				continue;
			}
			$fact = $by_id[ $product_id ];
			$keep = false;
			switch ( $facet ) {
				case 'application':
					$keep = SelectionFactSet::UNKNOWN !== $fact->application && (string) $fact->application === $value;
					break;
				case 'phase':
					$keep = \is_int( $fact->phase ) && (string) $fact->phase === $value;
					break;
				case 'power':
					$keep = \is_float( $fact->ac_power_kw ) && isset( self::POWER_BUCKETS[ $value ] ) && $this->in_bucket( $fact->ac_power_kw, self::POWER_BUCKETS[ $value ] );
					break;
				case 'brand':
					$keep = has_term( $value, 'pa_brand', $product_id );
					break;
			}
			if ( $keep ) {
				++$count;
			}
		}
		return $count;
	}

	/**
	 * How many filters the rail reports as applied: the category the visitor
	 * is on counts as one, every selected facet adds one (the live badge and
	 * summary's own arithmetic — measured 2026-10-12: "Filters · 0" on the
	 * shop, "Filters · 1" on a category, "· 1" with brand=goodwe on the
	 * shop, "· 2" with brand=goodwe on the Inverters archive; the search
	 * term is the search box's, not a filter). The sort is not a filter.
	 *
	 * @param bool                        $is_term  Whether the view is a category archive.
	 * @param array<string, string|float> $selected The request's facet selections.
	 */
	public function applied_count( bool $is_term, array $selected = array() ): int {
		$count = \count( \array_diff_key( $selected, array( 'q' => '' ) ) );
		return $is_term ? $count + 1 : $count;
	}

	/**
	 * A facet's values in the order the live rail lists them: the values the
	 * live names first, then whatever else was counted, in its own order.
	 *
	 * @param array<int|string, array{label: string, count: int}> $values The counted values.
	 * @param string[]                                            $order  The live rail's value order.
	 * @return array<int|string, array{label: string, count: int}> The values in that order.
	 */
	private function in_value_order( array $values, array $order ): array {
		$ordered = array();
		foreach ( $order as $value ) {
			if ( isset( $values[ $value ] ) ) {
				$ordered[ $value ] = $values[ $value ];
			}
		}

		return $ordered + $values;
	}

	/**
	 * The power buckets' labels, in bucket order.
	 *
	 * @return array<string, string> Bucket key => label.
	 */
	private function power_labels(): array {
		return array(
			'low'  => __( 'Up to 6 kW', 'linker-commerce' ),
			'mid'  => __( '6 to 15 kW', 'linker-commerce' ),
			'high' => __( '15 to 30 kW', 'linker-commerce' ),
			'top'  => __( 'Over 30 kW', 'linker-commerce' ),
		);
	}

	/**
	 * The facet values' printed labels, the rail's own words: the chips that
	 * carry an applied selection print the same words the rail lists
	 * (docs/specs/12-site-chrome.md item 5). The brands are the terms' own
	 * names, read where the chips render.
	 *
	 * @return array<string, array<int|string, string>> Labels by facet and value. The phase values are
	 *                                                   PHP's numeric strings: '3' lives under the int key 3,
	 *                                                   and lookups by either spelling reach it.
	 */
	public function value_labels(): array {
		$phase = array();
		foreach ( array( 3, 1 ) as $phases ) {
			$phase[ (string) $phases ] = sprintf( /* translators: %d: number of grid phases. */ _n( '%d-phase', '%d-phase', $phases, 'linker-commerce' ), $phases );
		}
		return array(
			'application' => array(
				'home'       => __( 'Home', 'linker-commerce' ),
				'commercial' => __( 'Commercial', 'linker-commerce' ),
			),
			'phase'       => $phase,
			'power'       => $this->power_labels(),
		);
	}

	/**
	 * The archive's products before the facets and before pagination: the
	 * list the rail's counts describe, also when the page shows one slice.
	 * Products WooCommerce hides from the shop (out of stock, ticket
	 * #69's "only show in stock") are not in the list, so the rail's counts
	 * and the facet filtering describe what the page can show.
	 *
	 * @return int[] The product IDs.
	 */
	public function archive_product_ids(): array {
		$tax_query = array();
		$object    = get_queried_object();
		if ( $object instanceof \WP_Term ) {
			// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the queried category's products, one query per archive render.
			$tax_query[] = array(
				'taxonomy' => $object->taxonomy,
				'field'    => 'term_id',
				'terms'    => $object->term_id,
			);
		}
		if ( 'yes' === get_option( 'woocommerce_hide_out_of_stock_items' ) ) {
			$outofstock = wc_get_product_visibility_term_ids()['outofstock'] ?? 0;
			if ( $outofstock ) {
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the same exclusion WooCommerce's own shop query applies.
				$tax_query[] = array(
					'taxonomy' => 'product_visibility',
					'field'    => 'term_taxonomy_id',
					'terms'    => array( (int) $outofstock ),
					'operator' => 'NOT IN',
				);
			}
		}
		$args = array(
			'post_type'      => 'product',
			'post_status'    => 'publish',
			'posts_per_page' => -1,
			'fields'         => 'ids',
			'orderby'        => 'menu_order title',
			'order'          => 'ASC',
		);
		if ( array() !== $tax_query ) {
			$args['tax_query'] = $tax_query; // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- one query per archive render.
		}
		// Woo's own catalogue visibility: a product excluded from the
		// catalogue is not part of this set (the live shop omits it too).
		$visibility = function_exists( 'wc_get_product_visibility_term_ids' ) ? wc_get_product_visibility_term_ids() : array();
		$hidden     = (int) ( $visibility['exclude-from-catalog'] ?? 0 );
		if ( $hidden > 0 ) {
			$args['tax_query'][] = array( // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_tax_query -- the catalogue's own visibility filter, one query per archive render.
				'taxonomy' => 'product_visibility',
				'field'    => 'term_taxonomy_id',
				'terms'    => array( $hidden ),
				'operator' => 'NOT IN',
			);
		}
		$ids = get_posts( $args );
		return $this->recommended_order( array_map( 'intval', $ids ) );
	}

	/**
	 * The archive's products with the request's facets applied — the list the
	 * family view renders, so a facet link narrows the grid the same way the
	 * main query is narrowed. No selection is the whole archive; a selection
	 * with no match is an empty list, never the unfiltered archive.
	 *
	 * @return int[] The product IDs.
	 */
	public function filtered_product_ids(): array {
		$selected = $this->requested();
		if ( array() === $selected ) {
			return $this->archive_product_ids();
		}
		return $this->matching( $this->archive_product_ids(), $selected );
	}
}
