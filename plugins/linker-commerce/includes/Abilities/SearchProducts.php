<?php
/**
 * Ability linker/search-products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Compatibility;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;
use WC_Product;

/**
 * Deterministic product selection (docs/specs/13-genie.md): qualify, sort, why,
 * excluded counts, unknown_fields. unknown is kept, never treated as a conflict.
 * Sorting is full match before any unknown, then |ac_power_kw − pv_kwp|, then price.
 * future=['battery'] only annotates pairing on inverters; it does not search batteries.
 */
final class SearchProducts {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/search-products';

	/**
	 * Most products one answer may list (docs/specs/13-genie.md).
	 */
	public const MAX_LIMIT = 12;

	/**
	 * Filter fields, in the order a failing product is counted under excluded.by_reason.
	 */
	private const FILTERS = array( 'device_class', 'application', 'phase', 'pv_input', 'kwh', 'brand', 'series', 'text' );

	/**
	 * Device classes whose pairings with batteries are documented.
	 */
	private const INVERTER_CLASSES = array( 'inverters', 'all-in-one-systems' );

	/**
	 * Device classes that are the battery side of a pairing.
	 */
	private const BATTERY_CLASSES = array( 'home-storage', 'battery-systems' );

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$why       = array(
			'type'                 => 'object',
			'properties'           => array(
				'field' => array( 'type' => 'string' ),
				'value' => array(),
				'match' => array(
					'anyOf' => array(
						array(
							'type' => 'boolean',
							'enum' => array( true ),
						),
						array(
							'type' => 'string',
							'enum' => array( SelectionFactSet::UNKNOWN ),
						),
					),
				),
			),
			'required'             => array( 'field', 'value', 'match' ),
			'additionalProperties' => false,
		);
		$qualified = array(
			'type'                 => 'object',
			'properties'           => array(
				'product_id' => array( 'type' => 'integer' ),
				'title'      => array( 'type' => 'string' ),
				'url'        => array( 'type' => 'string' ),
				'why'        => array(
					'type'  => 'array',
					'items' => $why,
				),
				'facts'      => array( 'type' => 'object' ),
				'commerce'   => ProductCommerce::schema(),
				'pairings'   => array(
					'type'  => 'array',
					'items' => array(
						'type'                 => 'object',
						'properties'           => array(
							'product_id' => array( 'type' => 'integer' ),
							'verdict'    => array(
								'type' => 'string',
								'enum' => array( 'released', 'released_with_accessory', 'not_released', 'unknown' ),
							),
							'conditions' => array(
								'type'  => 'array',
								'items' => array( 'type' => 'object' ),
							),
							'documents'  => array(
								'type'  => 'array',
								'items' => array( 'type' => 'object' ),
							),
						),
						'required'             => array( 'product_id', 'verdict', 'conditions' ),
						'additionalProperties' => false,
					),
				),
			),
			'required'             => array( 'product_id', 'title', 'url', 'why', 'facts', 'commerce' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'Search products', 'linker-commerce' ),
			'description'         => __( 'Qualifies published products against selection facts, sorts them, and explains each match.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'device_class'  => array(
						'type' => 'string',
						'enum' => SelectionFacts::DEVICE_CLASSES,
					),
					'application'   => array(
						'type' => 'string',
						'enum' => SelectionFacts::APPLICATIONS,
					),
					'phase'         => array(
						'type' => 'integer',
						'enum' => array( 1, 3 ),
					),
					'pv_kwp'        => array(
						'type'    => 'number',
						'minimum' => 0,
					),
					'kwh_min'       => array(
						'type'    => 'number',
						'minimum' => 0,
					),
					'kwh_max'       => array(
						'type'    => 'number',
						'minimum' => 0,
					),
					'brand'         => array( 'type' => 'string' ),
					'series'        => array( 'type' => 'string' ),
					'future'        => array(
						'type'  => 'array',
						'items' => array(
							'type' => 'string',
							'enum' => array( 'battery' ),
						),
					),
					'text'          => array( 'type' => 'string' ),
					'with_pairings' => array( 'type' => 'boolean' ),
					'lang'          => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
					'limit'         => array(
						'type'    => 'integer',
						'minimum' => 1,
						'maximum' => self::MAX_LIMIT,
					),
				),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'qualified'      => array(
						'type'  => 'array',
						'items' => $qualified,
					),
					'excluded'       => array(
						'type'                 => 'object',
						'properties'           => array(
							'by_reason' => array(
								'type'                 => 'object',
								'additionalProperties' => array( 'type' => 'integer' ),
							),
						),
						'required'             => array( 'by_reason' ),
						'additionalProperties' => false,
					),
					'unknown_fields' => array(
						'type'  => 'array',
						'items' => array( 'type' => 'string' ),
					),
				),
				'required'             => array( 'qualified', 'excluded', 'unknown_fields' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may search published products. Prices follow CommerceState.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * Qualify, sort and explain the published catalogue against the filters.
	 *
	 * @param array<string, mixed>|object $input Filters of docs/specs/13-genie.md.
	 * @return array{qualified: list<array<string, mixed>>, excluded: array{by_reason: array<string, int>}, unknown_fields: string[]}
	 */
	public function execute( $input = array() ): array {
		$input = (array) $input;
		$lang  = ProductText::lang( $input['lang'] ?? null );
		$limit = isset( $input['limit'] ) ? min( self::MAX_LIMIT, max( 1, (int) $input['limit'] ) ) : self::MAX_LIMIT;
		$ids   = array_values(
			array_map(
				'intval',
				get_posts(
					array(
						'post_type'      => 'product',
						'post_status'    => 'publish',
						'fields'         => 'ids',
						'posts_per_page' => -1,
						'orderby'        => 'ID',
						'order'          => 'ASC',
					)
				)
			)
		);
		update_postmeta_cache( $ids );
		update_object_term_cache( $ids, 'product' );

		return $this->select( $ids, $input, $lang, $limit );
	}

	/**
	 * Qualify and sort already-loaded product IDs. Tests call this with the live fixture.
	 *
	 * @param int[]                $ids    Published product IDs.
	 * @param array<string, mixed> $input  Filters.
	 * @param 'en'|'de'            $lang   Language of titles.
	 * @param int                  $limit  At most MAX_LIMIT.
	 * @return array{qualified: list<array<string, mixed>>, excluded: array{by_reason: array<string, int>}, unknown_fields: string[]}
	 */
	public function select( array $ids, array $input, string $lang, int $limit ): array {
		$excluded  = array();
		$qualified = array();
		foreach ( $ids as $id ) {
			$facts  = SelectionFacts::for_product( $id );
			$reason = $this->exclusion( $facts, $id, $input );
			if ( null !== $reason ) {
				$excluded[ $reason ] = ( $excluded[ $reason ] ?? 0 ) + 1;
				continue;
			}
			$product     = wc_get_product( $id );
			$qualified[] = array(
				'id'      => $id,
				'facts'   => $facts,
				'product' => $product instanceof WC_Product ? $product : null,
			);
		}
		usort(
			$qualified,
			function ( array $a, array $b ) use ( $input ): int {
				return $this->order( $a, $b, $input );
			}
		);
		$unknown_fields = $this->unknown_fields( $qualified, $input );
		$want_pairings  = ! empty( $input['with_pairings'] );
		$want_future    = in_array( 'battery', (array) ( $input['future'] ?? array() ), true );
		$batteries      = ( $want_pairings || $want_future ) ? $this->battery_ids( $ids ) : array();
		$out            = array();
		foreach ( array_slice( $qualified, 0, $limit ) as $row ) {
			$out[] = $this->card( $row, $input, $lang, $want_pairings, $want_future, $batteries );
		}

		return array(
			'qualified'      => $out,
			'excluded'       => array( 'by_reason' => $excluded ),
			'unknown_fields' => $unknown_fields,
		);
	}

	/**
	 * Why a product is out, or null when it stays. First failing filter wins.
	 *
	 * @param SelectionFactSet     $facts Facts.
	 * @param int                  $id    Product ID.
	 * @param array<string, mixed> $input Filters.
	 */
	private function exclusion( SelectionFactSet $facts, int $id, array $input ): ?string {
		foreach ( self::FILTERS as $filter ) {
			$verdict = $this->matches( $filter, $facts, $id, $input );
			if ( false === $verdict ) {
				return $filter;
			}
		}

		return null;
	}

	/**
	 * Whether the product matches a filter: true, false, or unknown (kept).
	 *
	 * @param string               $filter One of FILTERS.
	 * @param SelectionFactSet     $facts  Facts.
	 * @param int                  $id     Product ID.
	 * @param array<string, mixed> $input  Filters.
	 */
	private function matches( string $filter, SelectionFactSet $facts, int $id, array $input ): bool|string {
		return match ( $filter ) {
			'device_class' => $this->same_or_unknown( $facts->device_class, $input['device_class'] ?? null ),
			'application'  => $this->same_or_unknown( $facts->application, $input['application'] ?? null ),
			'phase'        => $this->same_or_unknown( $facts->phase, $input['phase'] ?? null ),
			'pv_input'     => $this->pv_ok( $facts, $input['pv_kwp'] ?? null ),
			'kwh'          => $this->kwh_ok( $facts, $input['kwh_min'] ?? null, $input['kwh_max'] ?? null ),
			'brand'        => $this->term_ok( $id, 'pa_brand', $input['brand'] ?? null ),
			'series'       => $this->term_ok( $id, 'pa_series', $input['series'] ?? null ),
			'text'         => $this->text_ok( $id, $input['text'] ?? null ),
			default        => true,
		};
	}

	/**
	 * An equality filter: omitted → true; product unknown → unknown; else equality.
	 *
	 * @param mixed $actual   Fact.
	 * @param mixed $expected Requested value, or null when the filter is off.
	 */
	private function same_or_unknown( mixed $actual, mixed $expected ): bool|string {
		if ( null === $expected || '' === $expected ) {
			return true;
		}
		if ( SelectionFactSet::UNKNOWN === $actual ) {
			return SelectionFactSet::UNKNOWN;
		}

		return $actual == $expected; // phpcs:ignore Universal.Operators.StrictComparisons.LooseEqual -- phase is int, JSON may send 3.0.
	}

	/**
	 * PV input must be at least the stated kWp; unknown is kept.
	 *
	 * @param SelectionFactSet $facts  Facts.
	 * @param mixed            $pv_kwp Requested kWp, or null.
	 */
	private function pv_ok( SelectionFactSet $facts, mixed $pv_kwp ): bool|string {
		if ( ! is_numeric( $pv_kwp ) ) {
			return true;
		}
		if ( ! is_float( $facts->pv_input_kw ) ) {
			return SelectionFactSet::UNKNOWN;
		}

		return (float) $facts->pv_input_kw >= (float) $pv_kwp;
	}

	/**
	 * Usable or nominal energy, or the stated range, overlaps [kwh_min, kwh_max].
	 *
	 * @param SelectionFactSet $facts Facts.
	 * @param mixed            $min   Lower bound, or null.
	 * @param mixed            $max   Upper bound, or null.
	 */
	private function kwh_ok( SelectionFactSet $facts, mixed $min, mixed $max ): bool|string {
		$min = is_numeric( $min ) ? (float) $min : null;
		$max = is_numeric( $max ) ? (float) $max : null;
		if ( null === $min && null === $max ) {
			return true;
		}
			$scalar = is_float( $facts->usable_kwh )
				? $facts->usable_kwh
				: ( is_float( $facts->nominal_kwh ) ? $facts->nominal_kwh : null );
		if ( null !== $scalar ) {
			return ( null === $min || $scalar >= $min ) && ( null === $max || $scalar <= $max );
		}
		if ( is_array( $facts->kwh_range ) ) {
			$low  = $facts->kwh_range['min'];
			$high = $facts->kwh_range['max'];

			return ( null === $max || $low <= $max ) && ( null === $min || $high >= $min );
		}

		return SelectionFactSet::UNKNOWN;
	}

	/**
	 * Brand or series: the product's term slug or name equals the request, case-insensitive.
	 * No term is unknown and is kept.
	 *
	 * @param int    $id       Product ID.
	 * @param string $taxonomy pa_brand or pa_series.
	 * @param mixed  $wanted   Requested value, or null.
	 */
	private function term_ok( int $id, string $taxonomy, mixed $wanted ): bool|string {
		if ( ! is_string( $wanted ) || '' === $wanted ) {
			return true;
		}
		$slugs = ProductText::term_slugs( $id, $taxonomy );
		$name  = ProductText::term_name( $id, $taxonomy );
		if ( array() === $slugs && null === $name ) {
			return SelectionFactSet::UNKNOWN;
		}
		$wanted = strtolower( $wanted );
		foreach ( $slugs as $slug ) {
			if ( strtolower( $slug ) === $wanted ) {
				return true;
			}
		}

		return is_string( $name ) && strtolower( $name ) === $wanted;
	}

	/**
	 * Free-text filter against title, SKU and model. Omitted → true.
	 *
	 * @param int   $id    Product ID.
	 * @param mixed $text  Needle, or null.
	 */
	private function text_ok( int $id, mixed $text ): bool {
		if ( ! is_string( $text ) || '' === trim( $text ) ) {
			return true;
		}
		$needle  = strtolower( trim( $text ) );
		$hay     = strtolower( (string) get_the_title( $id ) );
		$model   = ProductText::term_name( $id, 'pa_model' );
		$product = wc_get_product( $id );
		$sku     = $product instanceof WC_Product ? (string) $product->get_sku() : '';

		return str_contains( $hay, $needle )
			|| str_contains( strtolower( $sku ), $needle )
			|| ( is_string( $model ) && str_contains( strtolower( $model ), $needle ) );
	}

	/**
	 * Sort: fewer unknowns first, then closer AC power to pv_kwp, then cheaper, then ID.
	 *
	 * @param array{id: int, facts: SelectionFactSet, product: WC_Product|null} $a     Left.
	 * @param array{id: int, facts: SelectionFactSet, product: WC_Product|null} $b     Right.
	 * @param array<string, mixed>                                              $input Filters.
	 */
	private function order( array $a, array $b, array $input ): int {
		$unknown = $this->unknowns( $a['facts'], $a['id'], $input ) <=> $this->unknowns( $b['facts'], $b['id'], $input );
		if ( 0 !== $unknown ) {
			return $unknown;
		}
		$distance = $this->distance( $a['facts'], $input ) <=> $this->distance( $b['facts'], $input );
		if ( 0 !== $distance ) {
			return $distance;
		}
		$price = $this->price( $a['product'] ) <=> $this->price( $b['product'] );

		return 0 !== $price ? $price : $a['id'] <=> $b['id'];
	}

	/**
	 * How many applied filters this product satisfies only as unknown.
	 *
	 * @param SelectionFactSet     $facts Facts.
	 * @param int                  $id    Product ID.
	 * @param array<string, mixed> $input Filters.
	 */
	private function unknowns( SelectionFactSet $facts, int $id, array $input ): int {
		$n = 0;
		foreach ( self::FILTERS as $filter ) {
			if ( SelectionFactSet::UNKNOWN === $this->matches( $filter, $facts, $id, $input ) ) {
				++$n;
			}
		}

		return $n;
	}

	/**
	 * |ac_power_kw − pv_kwp|; without pv_kwp every product ties; unknown AC power sorts last.
	 *
	 * @param SelectionFactSet     $facts Facts.
	 * @param array<string, mixed> $input Filters.
	 */
	private function distance( SelectionFactSet $facts, array $input ): float {
		if ( ! is_numeric( $input['pv_kwp'] ?? null ) ) {
			return 0.0;
		}
		if ( ! is_float( $facts->ac_power_kw ) ) {
			return PHP_FLOAT_MAX;
		}

		return abs( (float) $facts->ac_power_kw - (float) $input['pv_kwp'] );
	}

	/**
	 * Stored price for sorting; products without a number sort last. Visibility
	 * does not change the order (CommerceState still hides the number on the card).
	 *
	 * @param WC_Product|null $product Product.
	 */
	private function price( ?WC_Product $product ): float {
		if ( ! $product instanceof WC_Product ) {
			return PHP_FLOAT_MAX;
		}
		$raw = $product->get_price( 'edit' );

		return is_numeric( $raw ) ? (float) $raw : PHP_FLOAT_MAX;
	}

	/**
	 * Applied filter keys that at least one qualified product answers as unknown.
	 *
	 * @param list<array{id: int, facts: SelectionFactSet, product: WC_Product|null}> $qualified Qualified rows.
	 * @param array<string, mixed>                                                    $input     Filters.
	 * @return string[]
	 */
	private function unknown_fields( array $qualified, array $input ): array {
		$fields = array();
		foreach ( $qualified as $row ) {
			foreach ( self::FILTERS as $filter ) {
				if ( SelectionFactSet::UNKNOWN === $this->matches( $filter, $row['facts'], $row['id'], $input ) ) {
					$fields[ $filter ] = true;
				}
			}
		}

		return array_keys( $fields );
	}

	/**
	 * One qualified card.
	 *
	 * @param array{id: int, facts: SelectionFactSet, product: WC_Product|null} $row          Qualified row.
	 * @param array<string, mixed>                                              $input        Filters.
	 * @param 'en'|'de'                                                         $lang         Language.
	 * @param bool                                                              $want_pairings with_pairings.
	 * @param bool                                                              $want_future  future battery.
	 * @param int[]                                                             $batteries    Published battery IDs.
	 * @return array<string, mixed>
	 */
	private function card( array $row, array $input, string $lang, bool $want_pairings, bool $want_future, array $batteries ): array {
		$id   = $row['id'];
		$card = array(
			'product_id' => $id,
			'title'      => ProductText::title( $id, $lang ),
			'url'        => ProductText::url( $id, $lang ),
			'why'        => $this->why( $row['facts'], $id, $input, $want_future, $batteries ),
			'facts'      => $row['facts']->to_array(),
			'commerce'   => ProductCommerce::of( $id, $row['product'] ),
		);
		if ( $want_pairings ) {
			$card['pairings'] = $this->pairings( $id, $row['facts']->device_class, $batteries );
		}

		return $card;
	}

	/**
	 * Why entries for the filters that were applied, plus a battery pairing note
	 * when future=['battery'].
	 *
	 * @param SelectionFactSet     $facts       Facts.
	 * @param int                  $id          Product ID.
	 * @param array<string, mixed> $input       Filters.
	 * @param bool                 $want_future future battery.
	 * @param int[]                $batteries   Published battery IDs.
	 * @return list<array{field: string, value: mixed, match: true|'unknown'}>
	 */
	private function why( SelectionFactSet $facts, int $id, array $input, bool $want_future, array $batteries ): array {
		$why = array();
		$map = array(
			'device_class' => array( $facts->device_class, $input['device_class'] ?? null ),
			'application'  => array( $facts->application, $input['application'] ?? null ),
			'phase'        => array( $facts->phase, $input['phase'] ?? null ),
			'pv_input_kw'  => array( $facts->pv_input_kw, $input['pv_kwp'] ?? null ),
		);
		foreach ( $map as $field => list( $value, $requested ) ) {
			if ( null === $requested || '' === $requested ) {
				continue;
			}
			$why[] = array(
				'field' => $field,
				'value' => $value,
				'match' => SelectionFactSet::UNKNOWN === $value ? SelectionFactSet::UNKNOWN : true,
			);
		}
		if ( is_numeric( $input['kwh_min'] ?? null ) || is_numeric( $input['kwh_max'] ?? null ) ) {
				$energy = is_float( $facts->usable_kwh )
					? $facts->usable_kwh
					: ( is_float( $facts->nominal_kwh ) ? $facts->nominal_kwh : ( $facts->kwh_range ?? SelectionFactSet::UNKNOWN ) );
			$why[]      = array(
				'field' => 'kwh',
				'value' => $energy,
				'match' => SelectionFactSet::UNKNOWN === $energy ? SelectionFactSet::UNKNOWN : true,
			);
		}
		if ( $want_future && in_array( $facts->device_class, self::INVERTER_CLASSES, true ) ) {
			$documented = array() !== $this->documented_batteries( $id, $batteries );
			$why[]      = array(
				'field' => 'battery_pairing',
				'value' => $documented ? 'documented' : SelectionFactSet::UNKNOWN,
				'match' => $documented ? true : SelectionFactSet::UNKNOWN,
			);
		}

		return $why;
	}

	/**
	 * Documented pairings of an inverter (released or released_with_accessory).
	 *
	 * @param int    $id            Inverter ID.
	 * @param string $device_class  Device class.
	 * @param int[]  $batteries     Published battery IDs.
	 * @return list<array{product_id: int, verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>}>
	 */
	private function pairings( int $id, string $device_class, array $batteries ): array {
		if ( ! in_array( $device_class, self::INVERTER_CLASSES, true ) ) {
			return array();
		}
		$out = array();
		foreach ( $batteries as $battery_id ) {
			$answer = Compatibility::for_products( $id, $battery_id );
			if ( null === $answer || 'not_released' === $answer['verdict'] ) {
				continue;
			}
			$out[] = array(
				'product_id' => $battery_id,
				'verdict'    => $answer['verdict'],
				'conditions' => $answer['conditions'],
				// The pairing documents ride along, so one search answers
				// "what pairs with which files" without one
				// check-compatibility call per battery.
				'documents'  => $answer['documents'],
			);
		}

		return $out;
	}

	/**
	 * Battery IDs with a documented (not not_released) pairing to this inverter.
	 *
	 * @param int   $id        Inverter ID.
	 * @param int[] $batteries Published battery IDs.
	 * @return int[]
	 */
	private function documented_batteries( int $id, array $batteries ): array {
		$found = array();
		foreach ( $batteries as $battery_id ) {
			$answer = Compatibility::for_products( $id, $battery_id );
			if ( is_array( $answer ) && 'not_released' !== $answer['verdict'] ) {
				$found[] = $battery_id;
			}
		}

		return $found;
	}

	/**
	 * Published battery product IDs among `$ids`.
	 *
	 * @param int[] $ids Catalogue.
	 * @return int[]
	 */
	private function battery_ids( array $ids ): array {
		$batteries = array();
		foreach ( $ids as $id ) {
			$class = SelectionFacts::for_product( $id )->device_class;
			if ( in_array( $class, self::BATTERY_CLASSES, true ) ) {
				$batteries[] = $id;
			}
		}

		return $batteries;
	}
}
