<?php
/**
 * The live catalogue's own data layer: the material registry, the
 * compatibility contract and the freight policy, read from the byte copies
 * in data/ (snapshot 20261010-0033 of the live site's plugin data), with the
 * derivation rules the live product page renders by.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use WC_Product;

/**
 * One reader for everything the product page shows that comes from the
 * registry rather than from WooCommerce's own fields. The methods mirror the
 * live derivations (reference-and-display.php, product-page.php,
 * material-facts.php, material-compatibility.php, shipping.php of the live
 * plugin) so the same inputs print the same strings.
 */
final class Materials {

	/**
	 * The registry, decoded once per request.
	 *
	 * @var array<string, mixed>|null
	 */
	private static ?array $registry = null;

	/**
	 * The compatibility contract, decoded once per request.
	 *
	 * @var array<string, mixed>|null
	 */
	private static ?array $contract = null;

	/**
	 * The operating policies, decoded once per request.
	 *
	 * @var array<string, mixed>|null
	 */
	private static ?array $policies = null;

	/**
	 * Product ID to its bound material IDs, built once per request.
	 *
	 * @var array<int, list<string>>|null
	 */
	private static ?array $product_index = null;

	/**
	 * Whether the page is German.
	 */
	public static function is_de(): bool {
		return ( \function_exists( 'linker_i18n_is_de' ) && linker_i18n_is_de() )
			|| ( \function_exists( 'get_locale' ) && \str_starts_with( (string) \get_locale(), 'de' ) && ! \function_exists( 'linker_i18n_is_de' ) );
	}

	/**
	 * The page's locale for localized registry text ('de' or 'en').
	 */
	public static function locale(): string {
		return self::is_de() ? 'de' : 'en';
	}

	/**
	 * A decoded JSON file of data/, array() when it cannot be read.
	 *
	 * @param string $name The file name.
	 * @return array<string, mixed>
	 */
	private static function read( string $name ): array {
		$path = \dirname( __DIR__, 2 ) . '/data/' . $name;
		if ( ! \is_readable( $path ) ) {
			return array();
		}
		$payload = \json_decode( (string) \file_get_contents( $path ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local plugin data file on disk, not a remote URL.
		return \is_array( $payload ) ? $payload : array();
	}

	/**
	 * The material registry.
	 *
	 * @return array<string, mixed>
	 */
	public static function registry(): array {
		if ( null === self::$registry ) {
			self::$registry = self::read( 'material-registry.json' );
		}
		return self::$registry;
	}

	/**
	 * The compatibility contract.
	 *
	 * @return array<string, mixed>
	 */
	public static function contract(): array {
		if ( null === self::$contract ) {
			self::$contract = self::read( 'compatibility-lists.json' );
		}
		return self::$contract;
	}

	/**
	 * The operating policies.
	 *
	 * @return array<string, mixed>
	 */
	public static function policies(): array {
		if ( null === self::$policies ) {
			self::$policies = self::read( 'operating-policies.json' );
		}
		return self::$policies;
	}

	/**
	 * A policy's published value, or null.
	 *
	 * @param string $id The policy id.
	 * @return array<string, mixed>|null
	 */
	public static function policy( string $id ): ?array {
		$policy = self::policies()['policies'][ $id ] ?? null;
		return \is_array( $policy ) && \is_array( $policy['value'] ?? null ) ? $policy : null;
	}

	/**
	 * The registry material bound to the product. Where several materials
	 * share a binding, only the one matching the Woo product's model can speak
	 * for it; an internal component cannot stand in for the complete product.
	 *
	 * @param int $product_id The product.
	 * @return array<string, mixed>|null
	 */
	public static function material_for_product( int $product_id ): ?array {
		if ( null === self::$product_index ) {
			self::$product_index = array();
			foreach ( self::registry()['materials'] ?? array() as $id => $material ) {
				if ( ! \is_array( $material ) ) {
					continue;
				}
				foreach ( $material['bindings']['woo_product_ids'] ?? array() as $bound ) {
					$bound = (int) $bound;
					if ( $bound > 0 && ! \in_array( (string) $id, self::$product_index[ $bound ] ?? array(), true ) ) {
						self::$product_index[ $bound ][] = (string) $id;
					}
				}
			}
		}
		$source = $product_id;
		$bound  = self::$product_index[ $source ] ?? array();
		if ( array() === $bound ) {
			// A German twin carries no registry binding of its own: the
			// English source row is the bound one.
			$source = self::source_product_id( $product_id );
			$bound  = self::$product_index[ $source ] ?? array();
		}
		if ( array() === $bound ) {
			return null;
		}
		if ( \count( $bound ) > 1 ) {
			$model   = \trim( (string) \get_post_meta( $source, '_delinker_model', true ) );
			$matches = array();
			foreach ( $bound as $material_id ) {
				$identity = self::registry()['materials'][ $material_id ]['identity'] ?? array();
				foreach ( array( 'model', 'manufacturer_part_number' ) as $field ) {
					$candidate = \is_array( $identity ) ? \trim( (string) ( $identity[ $field ] ?? '' ) ) : '';
					if ( '' !== $model && '' !== $candidate && 0 === \strcasecmp( $model, $candidate ) ) {
						$matches[] = $material_id;
						break;
					}
				}
			}
			if ( 1 !== \count( $matches ) ) {
				return null;
			}
			$bound = $matches;
		}
		$material = self::registry()['materials'][ $bound[0] ] ?? null;
		return \is_array( $material ) ? $material : null;
	}

	/**
	 * The product's identity as the live page reads it: the registry's, with
	 * the product's own model designation where it holds its own figures.
	 *
	 * @param WC_Product $product The product.
	 * @return array{brand: string, model: string, kind: string, material_id: string}
	 */
	public static function identity( WC_Product $product ): array {
		$id       = (int) $product->get_id();
		$material = self::material_for_product( $id );
		$identity = \is_array( $material ) && \is_array( $material['identity'] ?? null ) ? $material['identity'] : array();
		$brand    = (string) ( $identity['manufacturer'] ?? '' );
		$model    = (string) ( $identity['model'] ?? '' );
		$kind     = (string) ( $identity['kind'] ?? '' );
		if ( '' === $kind ) {
			// A product with no registry material (or one whose binding still
			// names a pre-migration product id) carries the old system's own
			// type: _delinker_type, the vocabulary behind the delivered
			// product sets (inverter / battery / system / meter / ems / ct —
			// 265 products on the 2026-10-15 production read). The card's
			// order table is read by this value, so without the fallback
			// every such card fell to 'other' and swapped its fourth row
			// (measured: the ESA cabinet's card showed Max. efficiency where
			// the live card shows Ingress protection IP54).
			$kind = (string) \get_post_meta( $id, '_delinker_type', true );
		}
		if ( '' === $kind ) {
			$kind = 'other';
		}
		$own_figures = \is_array( \json_decode( (string) \get_post_meta( $id, '_tv_b2b_figures', true ), true ) );
		if ( $own_figures ) {
			$own_model = \trim( (string) \get_post_meta( $id, '_delinker_model', true ) );
			if ( '' !== $own_model && 'bundle' !== (string) \get_post_meta( $id, '_delinker_sku_kind', true ) ) {
				$model = $own_model;
			}
		}
		if ( '' === $brand ) {
			$terms = \get_the_terms( $id, 'product_brand' );
			$term  = ( \is_array( $terms ) && 1 === \count( $terms ) ) ? \reset( $terms ) : null;
			if ( $term instanceof \WP_Term ) {
				$brand = (string) $term->name;
			}
		}
		return array(
			'brand'       => $brand,
			'model'       => $model,
			'kind'        => $kind,
			'material_id' => \is_array( $material ) ? (string) ( $material['material_id'] ?? '' ) : '',
		);
	}

	/**
	 * The page's contract type for a product kind (tv_woo_b2b_type's map).
	 *
	 * @param string $kind The kind.
	 */
	public static function contract_type( string $kind ): string {
		$types = array(
			'hybrid_inverter'     => 'inverter',
			'string_inverter'     => 'inverter',
			'inverter'            => 'inverter',
			'battery_system'      => 'battery',
			'battery_module'      => 'battery',
			'storage_system'      => 'system',
			'hybrid_system'       => 'system',
			'all_in_one_system'   => 'system',
			'energy_meter'        => 'meter',
			'current_transformer' => 'ct',
			'ems'                 => 'ems',
			'ev_charger'          => 'accessory',
			'accessory'           => 'accessory',
		);
		return $types[ $kind ] ?? 'other';
	}

	/**
	 * The contract facts of a product, keyed by the shop's own spec
	 * vocabulary: the registry's specifications, or the product's own figures
	 * when no material is bound. A registry value explicitly marked as a
	 * merged upper limit is not a product capacity; the native product's range
	 * is used when present, and the misleading scalar is otherwise omitted.
	 *
	 * @param WC_Product $product The product.
	 * @return array<string, array<string, mixed>>
	 */
	public static function facts( WC_Product $product ): array {
		$id       = (int) $product->get_id();
		$material = self::material_for_product( $id );
		if ( \is_array( $material ) ) {
			$specs = $material['technical']['specifications'] ?? array();
			if ( ! \is_array( $specs ) ) {
				return array();
			}
			$energy = $specs['battery_rated_energy'] ?? array();
			if ( \is_array( $energy ) && \str_contains( \strtolower( (string) ( $energy['unit'] ?? '' ) ), 'merged value' ) ) {
				$own   = \json_decode( (string) \get_post_meta( self::source_product_id( $id ), '_tv_b2b_figures', true ), true );
				$range = \is_array( $own ) ? ( $own['battery_rated_energy'] ?? null ) : null;
				if ( \is_array( $range ) && 0 === \strcasecmp( \trim( (string) ( $range['unit'] ?? '' ) ), 'kWh' )
					&& 1 === \preg_match( '/^\s*\d+(?:[.,]\d+)?\s*[-–~]\s*\d+(?:[.,]\d+)?\s*$/u', (string) ( $range['value'] ?? '' ) ) ) {
					$specs['battery_rated_energy'] = $range;
				} else {
					unset( $specs['battery_rated_energy'] );
				}
			}
			return $specs;
		}
		$own = \json_decode( (string) \get_post_meta( $id, '_tv_b2b_figures', true ), true );
		if ( ! \is_array( $own ) ) {
			$source = self::source_product_id( $id );
			$own    = $source === $id ? null : \json_decode( (string) \get_post_meta( $source, '_tv_b2b_figures', true ), true );
		}
		return \is_array( $own ) ? $own : array();
	}

	/**
	 * The registry field to spec-key map (tv_woo_b2b_fact_keys).
	 *
	 * @return array<string, string>
	 */
	public static function fact_keys(): array {
		return array(
			'rated_ac_power_kw'                => 'ac_power',
			'rated_output_power_kw'            => 'ac_power',
			'nominal_ac_power_kw'              => 'ac_power',
			'phase'                            => 'phase',
			'phases'                           => 'phase',
			'mppt_count'                       => 'mppt',
			'ac_nominal_voltage_v'             => 'ac_nom_voltage',
			'system_energy_kwh_range'          => 'system_range',
			'max_efficiency_pct'               => 'efficiency',
			'battery_voltage_range_v'          => 'batt_voltage',
			'system_operating_voltage_range_v' => 'batt_voltage',
			'module_energy_kwh_usable'         => 'usable_kwh',
			'system_usable_energy_kwh'         => 'usable_kwh',
			'usable_energy_kwh'                => 'usable_kwh',
			'module_energy_kwh_nominal'        => 'nominal_kwh',
			'system_capacity_kwh_nominal'      => 'nominal_kwh',
			'system_nominal_energy_kwh'        => 'nominal_kwh',
			'system_energy_kwh_nominal'        => 'nominal_kwh',
			'module_voltage_v_nominal'         => 'nom_voltage',
			'system_voltage_v_nominal'         => 'nom_voltage',
			// The system-level nominal voltages are the same "Nominal voltage"
			// row: the GW61.4-BAT-AC-G10 and GW112.6-BAT-AC-G10 registry rows
			// carry system_nominal_voltage_v (307.2 V / 563.2 V) and the live
			// battery cards read exactly those values (measured 2026-10-12;
			// recheck 2026-10-14 found the deployed cards without the row,
			// because this key mapped to itself where no card order reads it).
			// The system_* fields sort ahead of a module's own value in
			// specs().
			'system_nominal_voltage_v'         => 'nom_voltage',
			// The product-level nominal voltage IS the product's "Nominal
			// voltage" row: the GW261.2-BAT-LCD-G10 registry row carries it
			// (832.0 V, our hosted datasheet GW_BAT-C-208-261
			// _Datasheet_EMEA-EN_V1.1.pdf p.2, alongside the pack's 166.4 V)
			// and the live battery cards read it — the card's model line
			// showed "832.0 V · GW261.2-BAT-LCD-G10" (measured 2026-10-12;
			// recheck 2026-10-14 found the deployed card at the pack's
			// 166.4 V because this key had no mapping). The module-suppression
			// rule in specs() keeps the pack value only where no product value
			// exists.
			'nominal_voltage_v'                => 'nom_voltage',
			'chemistry'                        => 'chemistry',
			'max_charge_current_a'             => 'charge_a',
			'max_discharge_current_a'          => 'discharge_a',
			'cycle_life'                       => 'cycles',
			'ratio'                            => 'ratio',
			'accuracy_class'                   => 'accuracy',
			'accuracy_class_active'            => 'accuracy',
			'accuracy_class_voltage_current'   => 'accuracy',
			'rated_burden_va'                  => 'burden',
			'bms_comms'                        => 'interface',
			'communication'                    => 'interface',
			'protocol'                         => 'interface',
			'ip_rating'                        => 'ip',
			'operating_temp_c'                 => 'temp',
			'weight_kg'                        => 'weight',
			'dimensions_mm'                    => 'dimensions',
			'ac_output_kw_nominal'             => 'ac_power',
			'rated_ac_power'                   => 'ac_power',
			'nominal_output_power'             => 'ac_power',
			'rated_power_kw'                   => 'ac_power',
			'power_kw'                         => 'ac_power',
			'n_mppt'                           => 'mppt',
			'max_efficiency'                   => 'efficiency',
			'usable_energy'                    => 'usable_kwh',
			'rated_energy_kwh'                 => 'nominal_kwh',
			'rated_energy'                     => 'nominal_kwh',
			'energy_kwh'                       => 'nominal_kwh',
			'battery_rated_energy'             => 'nominal_kwh',
			'max_ac_output_kw'                 => 'ac_output_kw_max',
			'backup_power_kw'                  => 'backup_power_kw',
			'ac_output_kw_max'                 => 'ac_output_kw_max',
			'modules_per_stack_max'            => 'modules_per_stack_max',
			'system_voltage_vdc'               => 'system_voltage_vdc',
			'battery_type'                     => 'battery_type',
		);
	}

	/**
	 * The spec rows of a product (tv_woo_b2b_specs): the vocabulary keys, the
	 * system-before-module ordering, the module-suppression rule and the
	 * value/label text of each row in the page's language.
	 *
	 * @param WC_Product $product The product.
	 * @return array<string, array{label: string, value: string, card: string, localised: bool}>
	 */
	public static function specs( WC_Product $product ): array {
		$facts = self::facts( $product );
		$keys  = self::fact_keys();
		$de    = self::is_de();

		$system_facts = array();
		$other_facts  = array();
		foreach ( $facts as $field => $fact ) {
			if ( \str_starts_with( (string) $field, 'system_' ) ) {
				$system_facts[ $field ] = $fact;
			} else {
				$other_facts[ $field ] = $fact;
			}
		}
		$facts = $system_facts + $other_facts;

		$quantity         = array(
			'nominal_kwh' => 'energy',
			'usable_kwh'  => 'energy',
			'nom_voltage' => 'voltage',
		);
		$product_quantity = array();
		foreach ( $facts as $field => $fact ) {
			$key = $keys[ $field ] ?? (string) $field;
			if ( isset( $quantity[ $key ] ) && ! \str_starts_with( (string) $field, 'module_' )
				&& \trim( (string) ( $fact['value'] ?? '' ) ) !== '' ) {
				$product_quantity[ $quantity[ $key ] ] = true;
			}
		}

		$out = array();
		foreach ( $facts as $field => $fact ) {
			if ( ! \array_key_exists( 'value', $fact ) ) {
				continue;
			}
			$key = $keys[ $field ] ?? (string) $field;
			if ( isset( $out[ $key ] ) ) {
				continue;
			}
			if ( isset( $quantity[ $key ], $product_quantity[ $quantity[ $key ] ] ) && \str_starts_with( (string) $field, 'module_' ) ) {
				continue;
			}
			$text        = self::spec_text( $product, $key, (string) $field, $fact, $de );
			$label       = self::key_label( $text['label_key'], $text['unit'] );
			$out[ $key ] = array(
				'label'     => $label,
				'value'     => $text['value'],
				'card'      => $text['value'],
				'localised' => $text['german'],
			);
		}
		return $out;
	}

	/**
	 * One spec row's text: the German twin when the page is German, the unit
	 * joined to the value, the power class, the qualifier note.
	 *
	 * @param WC_Product           $product The product.
	 * @param string               $key     The vocabulary key.
	 * @param string               $field   The registry field.
	 * @param array<string, mixed> $fact    The fact row.
	 * @param bool                 $de      Whether the page is German.
	 * @return array{value: string, german: bool, label_key: string, unit: string}
	 */
	public static function spec_text( WC_Product $product, string $key, string $field, array $fact, bool $de ): array {
		$value  = \trim( (string) ( $fact['value'] ?? '' ) );
		$german = false;
		if ( $de && \trim( (string) ( $fact['value_de'] ?? '' ) ) !== '' ) {
			$value  = \trim( (string) $fact['value_de'] );
			$german = true;
		} elseif ( $de ) {
			$twin   = self::spec_value_de( $product, $value );
			$german = $twin !== $value;
			$value  = $twin;
		}
		if ( 'phase' === $key ) {
			$value = self::phase_words( $value, $de );
		}
		$raw_unit = (string) ( $fact['unit'] ?? '' );
		$unit     = self::unit_label( $raw_unit, $de ? 'de' : 'en' );
		$split    = self::unit_split( $unit );
		$unit     = $split[0];
		$note     = $split[1];
		if ( '' !== $note ) {
			$value = \trim( (string) \preg_replace( '/\s*[*\x{2020}\x{2021}]+\s*$/u', '', $value ) );
		}
		$value     = self::value_with_unit( $value, $unit );
		$label_key = $key;
		$base_unit = self::unit_split( $raw_unit )[0];
		$power_row = self::is_power_field( $field . ' ' . (string) ( $fact['label'] ?? '' ), $base_unit );
		$value     = self::customer_power( $value, $power_row, $german, $de );
		if ( '' !== $note ) {
			$note = self::customer_power( $note, $power_row, $german, $de );
		}
		if ( 'ac_power' === $key && 'VA' === $power_row ) {
			$label_key = 'ac_apparent_power';
		}
		if ( 'ac_output_kw_max' === $key && 'VA' === $power_row ) {
			$label_key = 'ac_apparent_power_max';
		}
		if ( '' !== $note ) {
			$value .= ' (' . $note . ')';
		}
		if ( 'temp' === $key && \is_array( $fact['qualifier'] ?? null ) ) {
			$qualifier = \trim( (string) ( $fact['qualifier'][ $de ? 'de' : 'en' ] ?? '' ) );
			if ( '' !== $qualifier ) {
				$value .= ' (' . $qualifier . ')';
			}
		}
		return array(
			'value'     => $value,
			'german'    => $german,
			'label_key' => $label_key,
			'unit'      => $base_unit,
		);
	}

	/**
	 * A value's German twin: the product's own value→value_de map first, then
	 * the registry-wide map (tv_woo_b2b_spec_value_de).
	 *
	 * @param WC_Product $product The product.
	 * @param string     $value The value.
	 */
	public static function spec_value_de( WC_Product $product, string $value ): string {
		if ( '' === $value ) {
			return $value;
		}
		static $maps = array();
		$id          = (int) $product->get_id();
		if ( ! isset( $maps[ $id ] ) ) {
			$maps[ $id ] = array();
			foreach ( self::facts( $product ) as $fact ) {
				$english = \trim( (string) ( $fact['value'] ?? '' ) );
				$german  = \trim( (string) ( $fact['value_de'] ?? '' ) );
				if ( '' !== $english && '' !== $german && \preg_match( '/\p{L}/u', $english ) ) {
					$maps[ $id ][ $english ] = $german;
				}
			}
		}
		$key = \trim( $value );
		if ( isset( $maps[ $id ][ $key ] ) ) {
			return $maps[ $id ][ $key ];
		}
		return $value;
	}

	/**
	 * The phase count as words in the page's language.
	 *
	 * @param string $value The value.
	 * @param bool   $de Whether the page is German.
	 */
	public static function phase_words( string $value, bool $de ): string {
		$map = array(
			'1'            => $de ? '1-phasig' : '1-phase',
			'3'            => $de ? '3-phasig' : '3-phase',
			'one'          => $de ? '1-phasig' : '1-phase',
			'three'        => $de ? '3-phasig' : '3-phase',
			'single'       => $de ? '1-phasig' : '1-phase',
			'three_phase'  => $de ? '3-phasig' : '3-phase',
			'three phase'  => $de ? 'Dreiphasig' : 'Three-phase',
			'single phase' => $de ? 'Einphasig' : 'Single-phase',
			'three-phase'  => $de ? 'Dreiphasig' : 'Three-phase',
			'single-phase' => $de ? 'Einphasig' : 'Single-phase',
		);
		$key = \strtolower( \trim( $value ) );
		return $map[ $key ] ?? $value;
	}

	/**
	 * The unit as printed: symbol units untouched, word units German on German
	 * pages, label-like units dropped (tv_b2b_material_unit_label).
	 *
	 * @param string  $unit The unit.
	 * @param ?string $locale The locale ('de' or 'en').
	 */
	public static function unit_label( string $unit, ?string $locale = null ): string {
		$unit = \trim( $unit );
		$bare = \trim( $unit, " \t\n\r\0\x0B\xC2\xA0" );
		if ( '' === $bare || \in_array( \strtolower( $bare ), array( '-', '--', "\u{2013}", "\u{2014}", 'n/a', 'na', 'none' ), true ) ) {
			return '';
		}
		$key = \strtolower( $bare );
		if ( \in_array( $key, array( 'count', 'counts', 'class', 'classes', 'nos', 'no.', 'qty' ), true ) ) {
			return '';
		}
		$german = null !== $locale ? \str_starts_with( \strtolower( $locale ), 'de' ) : self::is_de();
		if ( ! $german ) {
			return $unit;
		}
		// The HS3 registry's W, VA and A notes qualify the Ireland variant;
		// localize their words while retaining the source marker and quantity.
		if ( \preg_match( '/^(W|VA|A @230Vac) \(footnote (\*{1,2}): (\d+(?:\.\d+)? (?:W|VA|A)) for Ireland variant\)$/D', $bare, $note ) ) {
			return $note[1] . ' (Fußnote ' . $note[2] . ': ' . $note[3] . ' für die Irland-Variante)';
		}
		$words = array(
			'phase'     => '',
			'phases'    => '',
			'year'      => 'Jahr',
			'years'     => 'Jahre',
			'month'     => 'Monat',
			'months'    => 'Monate',
			'pack'      => 'Pack',
			'packs'     => 'Packs',
			'pc'        => 'Stück',
			'pcs'       => 'Stück',
			'piece'     => 'Stück',
			'pieces'    => 'Stück',
			'module'    => 'Modul',
			'modules'   => 'Module',
			'cycle'     => 'Zyklus',
			'cycles'    => 'Zyklen',
			'device'    => 'Gerät',
			'devices'   => 'Geräte',
			'inverter'  => 'Wechselrichter',
			'inverters' => 'Wechselrichter',
			'tower'     => 'Turm',
			'towers'    => 'Türme',
			'unit'      => 'Einheit',
			'units'     => 'Einheiten',
			'set'       => 'Satz',
			'sets'      => 'Sätze',
			'string'    => 'Strang',
			'strings'   => 'Stränge',
			'group'     => 'Gruppe',
			'groups'    => 'Gruppen',
			'cell'      => 'Zelle',
			'cells'     => 'Zellen',
			'ton'       => 'Tonne',
			'tons'      => 'Tonnen',
			'tonne'     => 'Tonne',
			'tonnes'    => 'Tonnen',
			'rack'      => 'Rack',
			'racks'     => 'Racks',
			'channel'   => 'Kanal',
			'channels'  => 'Kanäle',
			'port'      => 'Port',
			'ports'     => 'Ports',
			'phase(s)'  => '',
		);
		return \array_key_exists( $key, $words ) ? $words[ $key ] : $unit;
	}

	/**
	 * A unit split into its symbol and its qualifier note.
	 *
	 * @return array{0: string, 1: string}
	 * @param string $unit The unit.
	 */
	public static function unit_split( string $unit ): array {
		$unit = \trim( $unit );
		if ( '' === $unit ) {
			return array( '', '' );
		}
		if ( \preg_match( '/^([^([]+)\s*[(\[]([^)\]]+)[)\]]\s*$/', $unit, $m ) ) {
			return array( \trim( $m[1] ), \trim( $m[2] ) );
		}
		return array( $unit, '' );
	}

	/**
	 * The value with its unit joined as the live formatter joins them
	 * (tv_b2b_material_value_with_unit).
	 *
	 * @param string $value The value.
	 * @param string $unit The unit.
	 */
	public static function value_with_unit( string $value, string $unit ): string {
		$value = \trim( $value );
		$unit  = \trim( $unit );
		if ( '' === $value || '' === $unit ) {
			return $value;
		}
		$lead_pattern = '/^([<>≤≥~±+-]?\s*\d[\d.,]*(?:\s*(?:[-–~]|to|bis)\s*[+-]?\d[\d.,]*)?)(\s+(?:for|für)\s.+|\s*\([^()]*\))$/u';
		if ( \strpos( $value, ' / ' ) === false && \strpos( $value, '; ' ) === false && \preg_match( $lead_pattern, $value, $lead ) ) {
			return $lead[1] . ' ' . $unit . ' ' . \trim( $lead[2] );
		}
		$symbol     = \explode( ' ', $unit, 2 )[0];
		$kilo_class = (bool) \preg_match( '/^(?:W|Wp|VA)$/', $symbol )
			&& (bool) \preg_match( '/(?<![A-Za-z])[kM]' . \preg_quote( $symbol, '/' ) . '(?![A-Za-z])/u', $value );
		if ( $kilo_class
			|| \preg_match( '/(?<![A-Za-z])' . \preg_quote( $symbol, '/' ) . '(?![A-Za-z])/u', $value )
			|| ( \strlen( $symbol ) > 2 && \stripos( $value, $symbol ) !== false )
			|| ( '°C' === $symbol && \strpos( $value, '℃' ) !== false ) ) {
			$rest = \trim( \substr( $unit, \strlen( $symbol ) ) );
			return '' !== $rest ? $value . ' ' . $rest : $value;
		}
		$parts = \preg_split( '/;\s+/u', $value );
		if ( \is_array( $parts ) && \count( $parts ) > 1 ) {
			$figures = true;
			foreach ( $parts as $part ) {
				if ( ! \preg_match( '/\d$/u', \trim( $part ) ) && ! \preg_match( $lead_pattern, \trim( $part ) ) ) {
					$figures = false;
					break;
				}
			}
			if ( $figures ) {
				return \implode( '; ', \array_map( static fn( $part ): string => self::value_with_unit( $part, $unit ), $parts ) );
			}
		}
		if ( ! \preg_match( '/^(?:mm|cm|m|M)(?![A-Za-z])/u', $unit )
			&& \preg_match( '/^(\d+(?:[.,]\d+)?)\s*[×x*]\s*(\d+(?:[.,]\d+)?)$/u', $value, $times ) ) {
			return (float) \str_replace( ',', '.', $times[1] ) >= (float) \str_replace( ',', '.', $times[2] )
				? $times[1] . ' ' . $unit . ' × ' . $times[2]
				: $times[1] . ' × ' . $times[2] . ' ' . $unit;
		}
		$items = \preg_split( '/,\s+/u', $value );
		if ( \is_array( $items ) && \count( $items ) > 1 ) {
			foreach ( $items as $item ) {
				if ( ! \preg_match( '/^(?:\p{L}[^:,]*:\s*)?\d+(?:[.,]\d+)?(?:\/\d+(?:[.,]\d+)?)*$/u', \trim( $item ) ) ) {
					return $value . ' ' . $unit;
				}
			}
			return \implode( ', ', \array_map( static fn( $item ): string => \trim( $item ) . ' ' . $unit, $items ) );
		}
		return $value . ' ' . $unit;
	}

	/**
	 * A power row's unit family, false when the row is not power
	 * (tv_woo_b2b_is_power_field).
	 *
	 * @return string|false
	 * @param string $name The field or unit name.
	 * @param string $unit The unit.
	 */
	public static function is_power_field( string $name, string $unit ) {
		$unit = \trim( $unit );
		if ( '' !== $unit && \preg_match( '/^(?:W|kW|MW|Wp|kWp|VA|kVA|MVA|Watts?)$/i', $unit ) ) {
			$family = \strtoupper( (string) \preg_replace( '/^k/i', '', $unit ) );
			return 'WATTS' === $family ? 'W' : $family;
		}
		$name = \strtolower( \trim( $name ) );
		if ( ! \preg_match( '/power|leistung|watt|\bk?va\b|\bk?wp\b|\bk?w\b|_k?w(?:_|$)|_k?wp(?:_|$)|_k?va(?:_|$)/', $name ) ) {
			return false;
		}
		if ( \preg_match( '/\bk?va\b|_k?va(?:_|$)|apparent|schein/', $name ) ) {
			return 'VA';
		}
		if ( \preg_match( '/\bk?wp\b|_k?wp(?:_|$)/', $name ) ) {
			return 'Wp';
		}
		return 'W';
	}

	/**
	 * A power figure in its kilowatt class, as the customer-facing printer
	 * writes it (tv_woo_b2b_customer_power).
	 *
	 * @param string $value The value.
	 * @param mixed  $bare_unit The unit without its qualifier.
	 * @param bool   $localise Whether to localise the number.
	 * @param ?bool  $de Whether the page is German.
	 */
	public static function customer_power( string $value, $bare_unit = 'W', bool $localise = true, ?bool $de = null ): string {
		if ( '' === $value ) {
			return $value;
		}
		$de = $de ?? self::is_de();
		if ( \is_string( $bare_unit ) && '' !== $bare_unit && \preg_match( '/^\s*(\d{4,6})\s*$/', $value, $bare ) ) {
			$shown = self::power_class( (int) $bare[1], $bare_unit, $localise, $de );
			if ( null !== $shown ) {
				return $shown;
			}
		}
		return (string) \preg_replace_callback(
			'/(?<![A-Za-z0-9.])(\d{1,2}[.,]\d{3}|\d{4,6})\s*(kWp|kVA|kW|Wp|VA|Watts?|W)(?![A-Za-z0-9])/u',
			static function ( $m ) use ( $localise, $de ) {
				$raw = \str_replace( array( ',', '.' ), '', $m[1] );
				if ( '' === $raw || ! \ctype_digit( $raw ) ) {
					return $m[0];
				}
				$shown = self::power_class( (int) $raw, $m[2], $localise, $de );
				return null !== $shown ? $shown : $m[0];
			},
			$value
		);
	}

	/**
	 * One power figure in its kilowatt class name (tv_woo_b2b_customer_power_class).
	 *
	 * @param int    $watts The power in watts.
	 * @param string $unit The unit.
	 * @param bool   $localise Whether to localise the number.
	 * @param bool   $de Whether the page is German.
	 */
	private static function power_class( int $watts, string $unit, bool $localise, bool $de ): ?string {
		if ( $watts < 1000 ) {
			return null;
		}
		$kilo   = $watts / 1000.0;
		$symbol = \strtoupper( (string) \preg_replace( '/^k/i', '', $unit ) );
		$symbol = 'WATTS' === $symbol ? 'W' : $symbol;
		if ( ! \in_array( $symbol, array( 'W', 'VA', 'WP' ), true ) ) {
			return null;
		}
		$label = 'WP' === $symbol ? 'kWp' : ( 'VA' === $symbol ? 'kVA' : 'kW' );
		// The live cards keep the figure's own precision: 5750 W prints
		// "5.75 kW", 29999 W "29.999 kW" (measured on the live catalogue's
		// GW29.999K-ETA-G20 and OCEAN 2 HD-P1-5K75 cards 2026-10-12); the
		// separator is the page's, the trailing zeros are dropped.
		$printed = \rtrim( \rtrim( \number_format( $kilo, 3, '.', '' ), '0' ), '.' );
		if ( $de && $localise ) {
			$printed = \str_replace( '.', ',', $printed );
		}
		return $printed . ' ' . $label;
	}

	/**
	 * A spec row's label (tv_woo_b2b_key_label's map).
	 *
	 * @param string $key The vocabulary key.
	 * @param string $unit The unit.
	 */
	public static function key_label( string $key, string $unit = '' ): string {
		$base_unit = self::unit_split( $unit )[0];
		$labels    = array(
			'ac_power'                        => __( 'Rated AC power', 'linker-commerce' ),
			'ac_apparent_power'               => __( 'Nominal apparent power', 'linker-commerce' ),
			'ac_apparent_power_max'           => __( 'Max. apparent power', 'linker-commerce' ),
			'phase'                           => __( 'Phase', 'linker-commerce' ),
			'mppt'                            => __( 'MPPT trackers', 'linker-commerce' ),
			'efficiency'                      => __( 'Max. efficiency', 'linker-commerce' ),
			'batt_voltage'                    => __( 'Battery voltage', 'linker-commerce' ),
			'usable_kwh'                      => __( 'Usable energy', 'linker-commerce' ),
			'nominal_kwh'                     => __( 'Nominal energy', 'linker-commerce' ),
			'nom_voltage'                     => __( 'Nominal voltage', 'linker-commerce' ),
			'ac_nom_voltage'                  => __( 'Nominal AC voltage', 'linker-commerce' ),
			'system_range'                    => __( 'System energy range', 'linker-commerce' ),
			'ac_output_w_nominal'             => __( 'AC output w nominal', 'linker-commerce' ),
			'ac_output_kw_max'                => __( 'Maximum AC output power', 'linker-commerce' ),
			'anti_corrosion_class'            => __( 'Corrosion protection class', 'linker-commerce' ),
			'box_material'                    => __( 'Enclosure material', 'linker-commerce' ),
			'cooling_method'                  => __( 'Cooling method', 'linker-commerce' ),
			'datalogger'                      => __( 'Data logger', 'linker-commerce' ),
			'ev_chargers'                     => __( 'EV chargers', 'linker-commerce' ),
			'power_consumption'               => __( 'Power consumption', 'linker-commerce' ),
			'operating_temp_range'            => __( 'Operating temperature', 'linker-commerce' ),
			'operating_temperature_range'     => __( 'Operating temperature', 'linker-commerce' ),
			'measurement_accuracy'            => __( 'Measurement accuracy', 'linker-commerce' ),
			'measuring_cycle'                 => __( 'Measuring cycle', 'linker-commerce' ),
			'current_measurement'             => __( 'Current measurement', 'linker-commerce' ),
			'ac_pf'                           => __( 'AC power factor', 'linker-commerce' ),
			'rated_current_a'                 => __( 'Nominal current', 'linker-commerce' ),
			'rated_voltage'                   => __( 'Supply', 'linker-commerce' ),
			'dimensions_hwd'                  => __( 'Dimensions (H × W × D)', 'linker-commerce' ),
			'communication_address_range'     => __( 'Communication address range', 'linker-commerce' ),
			'max_pv_input_power_w'            => __( 'Maximum PV input power', 'linker-commerce' ),
			'max_input_current_per_mppt_a'    => __( 'Maximum input current per MPPT', 'linker-commerce' ),
			'chemistry'                       => __( 'Cell chemistry', 'linker-commerce' ),
			'charge_a'                        => __( 'Max. charge current', 'linker-commerce' ),
			'discharge_a'                     => __( 'Max. discharge current', 'linker-commerce' ),
			'cycles'                          => __( 'Cycle life', 'linker-commerce' ),
			'ratio'                           => __( 'Transformer ratio', 'linker-commerce' ),
			'accuracy'                        => __( 'Accuracy class', 'linker-commerce' ),
			'burden'                          => __( 'Rated burden', 'linker-commerce' ),
			'devices'                         => __( 'Devices supported', 'linker-commerce' ),
			'interface'                       => __( 'Communication', 'linker-commerce' ),
			'ip'                              => __( 'Ingress protection', 'linker-commerce' ),
			'ingress_protection'              => __( 'Ingress protection', 'linker-commerce' ),
			'temp'                            => __( 'Operating temperature', 'linker-commerce' ),
			'weight'                          => __( 'Weight', 'linker-commerce' ),
			'dimensions'                      => __( 'Dimensions', 'linker-commerce' ),
			'dod_pct'                         => 'DoD',
			'dod'                             => 'DoD',
			'ac_output_kw_nominal'            => __( 'AC output (nominal)', 'linker-commerce' ),
			'backup_power_kw'                 => __( 'Backup power', 'linker-commerce' ),
			'system_voltage_vdc'              => __( 'System voltage', 'linker-commerce' ),
			'modules_per_stack_max'           => __( 'Modules per stack', 'linker-commerce' ),
			'cycle_life'                      => __( 'Cycle life', 'linker-commerce' ),
			'role'                            => __( 'Role', 'linker-commerce' ),
			'altitude'                        => __( 'Altitude', 'linker-commerce' ),
			'altitude_m'                      => __( 'Altitude', 'linker-commerce' ),
			'ambient_humidity'                => __( 'Ambient humidity', 'linker-commerce' ),
			'applicable_standard'             => __( 'Applicable standards', 'linker-commerce' ),
			'certification'                   => __( 'Certification', 'linker-commerce' ),
			'cable'                           => __( 'Cable length', 'linker-commerce' ),
			'accessory_option'                => __( 'Accessory option', 'linker-commerce' ),
			'ac_surge_protection'             => __( 'AC surge protection', 'linker-commerce' ),
			'accuracy_class_reactive'         => __( 'Accuracy class, reactive', 'linker-commerce' ),
			'battery_type'                    => __( 'Battery type', 'linker-commerce' ),
			'backup_nominal_apparent_power'   => __( 'Backup apparent power', 'linker-commerce' ),
			'backup_nominal_output_frequency' => __( 'Backup output frequency', 'linker-commerce' ),
			'nominal_apparent_power_output_to_utility_grid' => __( 'Nominal apparent power to grid', 'linker-commerce' ),
		);
		if ( isset( $labels[ $key ] ) ) {
			return $labels[ $key ];
		}
		$pretty = \str_replace( '_', ' ', $key );
		return \mb_strtoupper( \mb_substr( $pretty, 0, 1 ) ) . \mb_substr( $pretty, 1 );
	}

	/**
	 * The product row a translation belongs to: the English source product of
	 * a German twin (the registry bindings and the German content overlays
	 * hang off the English row).
	 *
	 * @param int $product_id The product ID.
	 */
	public static function source_product_id( int $product_id ): int {
		if ( \function_exists( 'pll_get_post' ) && \function_exists( 'pll_get_post_language' ) ) {
			$language = pll_get_post_language( $product_id );
			if ( 'en' !== $language ) {
				$source = pll_get_post( $product_id, 'en' );
				if ( $source > 0 ) {
					return $source;
				}
			}
		}
		return $product_id;
	}

	/**
	 * The product's legacy ACF JSON in the page's language: the German overlay
	 * (`_linker_de_acf_json`, stored on the English source row) on a German
	 * page, the English JSON otherwise.
	 *
	 * @param int $product_id The product.
	 * @return array<string, mixed>
	 */
	public static function acf( int $product_id ): array {
		if ( self::is_de() ) {
			$decoded = self::decode( \get_post_meta( $product_id, '_linker_de_acf_json', true ) );
			if ( array() !== $decoded ) {
				return self::terms_in( $decoded );
			}
			$source  = self::source_product_id( $product_id );
			$decoded = self::decode( \get_post_meta( $source, '_linker_de_acf_json', true ) );
			return self::terms_in( $decoded );
		}
		return self::decode( \get_post_meta( $product_id, '_tv_legacy_acf_json', true ) );
	}

	/**
	 * The site's German words for the old data's item and catalogue terms
	 * (AGENTS.md §3: Produkt, nie Artikel or Katalog; ticket #264 M3). Longest
	 * phrases first, so "Artikelnummer" becomes "Produktnummer" and the legal
	 * citation "Artikel 10, 12 und 14" stays untouched (banned-de.json's
	 * documented exception).
	 *
	 * @var array<string,string>
	 */
	private const GERMAN_TERMS = array(
		'Batteriespeicher-Katalog'          => 'Batteriespeicher-Produktübersicht',
		'Katalog der Hybrid-Wechselrichter' => 'Produktübersicht der Hybrid-Wechselrichter',
		'Katalog Hybrid-Wechselrichter'     => 'Produktübersicht Hybrid-Wechselrichter',
		'Multi-Marken-PV-Katalog'           => 'Multi-Marken-PV-Sortiment',
		'de-linker PV-Katalog'              => 'de-linker PV-Sortiment',
		'de-linker-Katalog'                 => 'de-linker-Sortiment',
		'Katalogprodukte'                   => 'Sortimentsprodukte',
		'Katalognummer'                     => 'Produktnummer',
		'Katalog'                           => 'Produktübersicht',
		'Artikelnummer (Serie)'             => 'Produktnummer (Serie)',
		'Artikelnummer'                     => 'Produktnummer',
		'Artikelnr.'                        => 'Produktnr.',
		'Artikel 1023601'                   => 'Produkt 1023601',
		'Artikel 1023621'                   => 'Produkt 1023621',
		'Entspricht Artikel '               => 'Entspricht Produkt ',
		'ein eigener Artikel'               => 'ein eigenes Produkt',
		'ein separater Artikel'             => 'ein separates Produkt',
		'diesen Artikel'                    => 'dieses Produkt',
		'Dieser Artikel ist'                => 'Dieses Produkt ist',
		'Dieser Artikel umfasst'            => 'Dieses Produkt umfasst',
		'dieses Artikels'                   => 'dieses Produkts',
		'diesem Artikel'                    => 'diesem Produkt',
		'P3-S2-Artikeln'                    => 'P3-S2-Produkten',
		'dieser Artikelnummer'              => 'dieser Produktnummer',
		'Diese Artikelnummer'               => 'Diese Produktnummer',
	);

	/**
	 * A German product text with the site's words for the old data's item and
	 * catalogue terms. English pages get their text byte for byte.
	 *
	 * @param string    $text   Text.
	 * @param bool|null $german Whether the page is German; null reads the request.
	 */
	public static function apply_terms( string $text, ?bool $german = null ): string {
		return ( $german ?? self::is_de() ) ? \strtr( $text, self::GERMAN_TERMS ) : $text;
	}

	/**
	 * The reviewed terms through every string of a decoded ACF value.
	 *
	 * @param array<string, mixed> $value Decoded ACF value.
	 * @return array<string, mixed>
	 */
	private static function terms_in( array $value ): array {
		foreach ( $value as $key => $entry ) {
			if ( \is_array( $entry ) ) {
				$value[ $key ] = self::terms_in( $entry );
			} elseif ( \is_string( $entry ) ) {
				$value[ $key ] = self::apply_terms( $entry, true );
			}
		}
		return $value;
	}

	/**
	 * One JSON meta value as an array, array() when it holds none.
	 *
	 * @param mixed $value The raw meta value.
	 * @return array<string, mixed>
	 */
	private static function decode( $value ): array {
		$decoded = \is_string( $value ) ? \json_decode( $value, true ) : ( \is_array( $value ) ? $value : null );
		return \is_array( $decoded ) ? $decoded : array();
	}

	/**
	 * The registry's compatibility relationships of a product's material.
	 *
	 * @param int $product_id The product.
	 * @return list<array<string, mixed>>
	 */
	public static function relationships( int $product_id ): array {
		$material = self::material_for_product( $product_id );
		if ( ! \is_array( $material ) ) {
			return array();
		}
		$rels = $material['technical']['relationships'] ?? array();
		return \is_array( $rels ) ? \array_values( \array_filter( $rels, 'is_array' ) ) : array();
	}

	/**
	 * The contract cell a relationship was expanded from.
	 *
	 * @param array<string, mixed> $relationship The registry relationship.
	 */
	public static function relationship_cell_id( array $relationship ): string {
		$parts = \explode( ':', (string) ( $relationship['relationship_id'] ?? '' ) );
		return 4 === \count( $parts ) && 'compat' === $parts[0] ? $parts[1] : '';
	}

	/**
	 * Localized registry text: the German twin when it exists, the English
	 * authority text otherwise.
	 *
	 * @param array<string, mixed> $row The row.
	 * @param string               $key The vocabulary key.
	 * @param string               $locale The locale ('de' or 'en').
	 */
	public static function localized_text( array $row, string $key, string $locale ): string {
		$en = \trim( (string) ( $row[ $key ] ?? '' ) );
		if ( 'de' === $locale ) {
			$de = \trim( (string) ( $row[ $key . '_de' ] ?? '' ) );
			if ( '' !== $de ) {
				return $de;
			}
		}
		return $en;
	}

	/**
	 * Which cited documents list a one-way pair (null when the sides do not
	 * split cleanly).
	 *
	 * @return array{listing: string[], not_listing: string[]}|null
	 * @param array<string, mixed> $row The row.
	 */
	public static function one_way_documents( array $row ): ?array {
		$label = \trim( (string) ( $row['not_listed_by'] ?? '' ) );
		if ( ( $row['status'] ?? '' ) !== 'one_way' || '' === $label ) {
			return null;
		}
		$documents = self::contract()['documents'] ?? array();
		if ( ! \is_array( $documents ) ) {
			return null;
		}
		$brands = array();
		$sides  = array(
			'listing'     => array(),
			'not_listing' => array(),
		);
		foreach ( (array) ( $row['document_refs'] ?? array() ) as $ref ) {
			$ref = \trim( (string) $ref );
			if ( '' === $ref || ! isset( $documents[ $ref ] ) || ! \is_array( $documents[ $ref ] ) ) {
				return null;
			}
			$brands[ \strtolower( \trim( (string) ( $documents[ $ref ]['brand'] ?? '' ) ) ) ] = true;
			$short = \trim( (string) ( $documents[ $ref ]['short'] ?? '' ) );
			$sides[ '' !== $short && \stripos( $label, $short ) !== false ? 'not_listing' : 'listing' ][] = $ref;
		}
		if ( 1 !== \count( $brands ) || isset( $brands[''] ) || ! $sides['listing'] || ! $sides['not_listing'] ) {
			return null;
		}
		return $sides;
	}

	/**
	 * Customer-facing names of compatibility documents a relationship cites.
	 *
	 * @return list<string>
	 * @param array<int|string, mixed> $refs The document references.
	 * @param string                   $locale The locale ('de' or 'en').
	 */
	public static function document_names( array $refs, string $locale = 'en' ): array {
		$documents = self::contract()['documents'] ?? array();
		if ( ! \is_array( $documents ) ) {
			return array();
		}
		$locale = 'de' === $locale ? 'de' : 'en';
		$names  = array();
		foreach ( $refs as $ref ) {
			$ref      = \trim( (string) $ref );
			$document = $documents[ $ref ] ?? null;
			$title    = \is_array( $document ) ? self::localized_text( $document, 'title', $locale ) : '';
			if ( '' === $title ) {
				continue;
			}
			$brand          = \trim( (string) ( $document['brand'] ?? '' ) );
			$name           = '' !== $brand && \stripos( $title, $brand ) === false ? $brand . ' ' . $title : $title;
			$names[ $name ] = $name;
		}
		return \array_values( $names );
	}

	/**
	 * The logistics fact of a product: the registry's delivery block, else the
	 * product's own shipping meta (tv_b2b_shipping_product_logistics).
	 *
	 * @return array<string, mixed>
	 * @param int         $product_id The product ID.
	 * @param ?WC_Product $product The product.
	 */
	public static function logistics( int $product_id, ?WC_Product $product = null ): array {
		$material = self::material_for_product( $product_id );
		if ( \is_array( $material ) ) {
			$logistics = $material['delivery']['logistics'] ?? array();
			if ( \is_array( $logistics ) && ! empty( $logistics['mode'] ) && 'product_specific' !== $logistics['mode'] ) {
				return array(
					'product_id'  => $product_id,
					'mode'        => \sanitize_key( (string) $logistics['mode'] ),
					'adr_un3480'  => ! empty( $logistics['adr_un3480'] ),
					'weight_kg'   => \is_numeric( $logistics['weight_kg'] ?? null ) ? (float) $logistics['weight_kg'] : 0.0,
					'weight_kind' => \sanitize_text_field( (string) ( $logistics['weight_kind'] ?? '' ) ),
				);
			}
		}
		$product = $product ? $product : \wc_get_product( $product_id );
		$read    = static function ( string $key ) use ( $product, $product_id ) {
			if ( $product ) {
				return $product->get_meta( $key, true );
			}
			return \get_post_meta( $product_id, $key, true );
		};
		$weight  = $read( '_delinker_shipping_weight_kg' );
		if ( ! \is_numeric( $weight ) || (float) $weight <= 0 ) {
			$weight = $product ? $product->get_weight() : $read( '_weight' );
		}
		return array(
			'product_id'  => $product_id,
			'mode'        => \sanitize_key( (string) $read( '_delinker_shipping_mode' ) ),
			'adr_un3480'  => \wc_string_to_bool( (string) $read( '_delinker_shipping_adr' ) ),
			'weight_kg'   => \is_numeric( $weight ) ? (float) $weight : 0.0,
			'weight_kind' => \sanitize_text_field( (string) $read( '_delinker_shipping_weight_kind' ) ),
		);
	}

	/**
	 * The freight guidance of a product's logistics fact, as the customer
	 * outcome the live page prints (tv_b2b_shipping_product_guidance →
	 * customer_outcome): {kind, headline, detail}.
	 *
	 * @param array<string, mixed> $fact The logistics fact.
	 * @return array{kind: string, headline: string, detail: string}
	 */
	public static function freight_outcome( array $fact ): array {
		$fact['quantity'] = 1;
		$parcel_cost      = 14.9;
		$safe_kg          = 28.0;
		if ( '' === ( $fact['mode'] ?? '' ) || ! \is_numeric( $fact['weight_kg'] ?? null ) || (float) $fact['weight_kg'] <= 0 ) {
			$reason = 'logistics_incomplete';
		} elseif ( ! empty( $fact['adr_un3480'] ) ) {
			$reason = 'dangerous_goods';
		} elseif ( 'parcel' !== ( $fact['mode'] ?? '' ) ) {
			$reason = 'pallet_or_oversize';
		} elseif ( (float) $fact['weight_kg'] > $safe_kg ) {
			$reason = 'packed_weight_confirmation';
		} else {
			$reason = 'confirmed_parcel';
		}

		if ( 'confirmed_parcel' === $reason ) {
			return array(
				'kind'     => 'exact',
				'headline' => __( 'Delivery to Germany', 'linker-commerce' ),
				'detail'   => \sprintf(
					/* translators: %s: a money amount. */
					__( 'Parcel rate for one eligible item within Germany: %s when you submit. Freight for multiple items is confirmed separately.', 'linker-commerce' ),
					self::money( $parcel_cost )
				),
			);
		}
		if ( \in_array( $reason, array( 'cross_border', 'destination_unknown', 'empty_cart', 'logistics_incomplete', 'consolidation_confirmation' ), true ) ) {
			return array(
				'kind'     => 'proforma',
				'headline' => __( 'Delivery included in your Proforma', 'linker-commerce' ),
				'detail'   => '',
			);
		}

		$mode        = \sanitize_key( (string) ( $fact['mode'] ?? '' ) );
		$unit_weight = \is_numeric( $fact['weight_kg'] ?? null ) ? (float) $fact['weight_kg'] : 0.0;
		if ( $unit_weight <= 0 || ! \in_array( $mode, array( 'half_pallet', 'pallet', 'multi_pallet' ), true ) ) {
			return array(
				'kind'     => 'proforma',
				'headline' => __( 'Delivery included in your Proforma', 'linker-commerce' ),
				'detail'   => '',
			);
		}
		$total_weight = $unit_weight;
		if ( 'multi_pallet' === $mode || $total_weight > 1000 ) {
			$classification = 'project_freight';
		} elseif ( ! empty( $fact['adr_un3480'] ) ) {
			$classification = $total_weight <= 300 ? 'adr_up_to_300kg' : 'adr_300_to_1000kg';
		} elseif ( 'pallet' === $mode ) {
			$classification = $total_weight > 500 ? 'heavy_pallet' : 'pallet';
		} else {
			$classification = 'half_pallet';
		}

		$policy = self::policy( 'freight' );
		$bands  = \is_array( $policy ) ? $policy['value']['domestic_guidance'] ?? array() : array();
		$band   = \is_array( $bands[ $classification ] ?? null ) ? $bands[ $classification ] : null;
		if ( ! \is_array( $band ) || ! \is_numeric( $band['min'] ?? null ) || ! \is_numeric( $band['max'] ?? null ) ) {
			return array(
				'kind'     => 'proforma',
				'headline' => __( 'Delivery included in your Proforma', 'linker-commerce' ),
				'detail'   => '',
			);
		}
		$min = (float) $band['min'];
		$max = (float) $band['max'];
		if ( $min < 0 || $max < $min ) {
			return array(
				'kind'     => 'proforma',
				'headline' => __( 'Delivery included in your Proforma', 'linker-commerce' ),
				'detail'   => '',
			);
		}
		if ( 'project_freight' === $classification ) {
			return array(
				'kind'     => 'proforma',
				'headline' => __( 'Delivery included in your Proforma', 'linker-commerce' ),
				'detail'   => '',
			);
		}
		return array(
			'kind'     => 'estimate',
			'headline' => \sprintf(
				/* translators: 1: minimum, 2: maximum money amounts. */
				__( 'Germany delivery estimate: %1$s to %2$s', 'linker-commerce' ),
				self::money( $min ),
				self::money( $max )
			),
			'detail'   => __( 'The final delivery charge is included in your Proforma.', 'linker-commerce' ),
		);
	}

	/**
	 * A money amount written the way the page writes money
	 * (tv_b2b_shipping_money: wc_price()'s text, entities decoded).
	 *
	 * @param float $amount The money amount.
	 */
	public static function money( float $amount ): string {
		$markup = \wc_price( $amount );
		$text   = \wp_strip_all_tags( (string) $markup );
		return \trim( (string) \html_entity_decode( $text, \ENT_QUOTES | \ENT_HTML5, 'UTF-8' ) );
	}

	/**
	 * The gallery image ids in the live order: the featured image, the
	 * gallery rows, feature cards, scenarios (tv_product_v5_gallery_ids).
	 *
	 * @return list<int>
	 * @param WC_Product           $product The product.
	 * @param array<string, mixed> $acf The decoded ACF JSON.
	 */
	public static function gallery_ids( WC_Product $product, array $acf ): array {
		$ids         = array();
		$featured_id = (int) $product->get_image_id();
		if ( $featured_id && \wp_attachment_is_image( $featured_id ) ) {
			$ids[] = $featured_id;
		}
		$sources = array(
			array( 'product_gallery', 'gallery_image' ),
			array( 'feature_cards', 'feature_image' ),
			array( 'application_scenarios', 'scenario_image' ),
		);
		foreach ( $sources as $source ) {
			$rows = isset( $acf[ $source[0] ] ) && \is_array( $acf[ $source[0] ] ) ? $acf[ $source[0] ] : array();
			foreach ( $rows as $row ) {
				$image_id = isset( $row[ $source[1] ] ) ? (int) $row[ $source[1] ] : 0;
				if ( $image_id && \wp_attachment_is_image( $image_id ) && ! \in_array( $image_id, $ids, true ) ) {
					$ids[] = $image_id;
				}
			}
		}
		// WooCommerce's own gallery field is one comma-separated list
		// (`WC_Meta_Box_Product_Images::save`; the products carry
		// "6504,6505"). Casting that string to an array yields its one
		// element, which is what this read did until 2026-10-13: every
		// product showed one image fewer than its editor holds, and the
		// product page lost its second picture and its whole thumbnail strip
		// (linker_pdp_gallery_pair/thumbs render nothing below two ids). An
		// array is still accepted — the field has held serialized arrays, and
		// both shapes name ids.
		$gallery = \get_post_meta( (int) $product->get_id(), '_product_image_gallery', true );
		$editor  = \array_filter( \array_map( 'intval', \is_array( $gallery ) ? $gallery : \explode( ',', (string) $gallery ) ) );
		foreach ( $editor as $image_id ) {
			if ( \wp_attachment_is_image( $image_id ) && ! \in_array( $image_id, $ids, true ) ) {
				$ids[] = $image_id;
			}
		}
		return $ids;
	}

	/**
	 * A download row's kind (tv_woo_b2b_document_kind).
	 *
	 * The role is read first, the type second, so a German row
	 * (`download_type` "Datenblatt") and its English twin answer the same
	 * kind. A word the table does not know comes back lowercased as it is;
	 * readers close that on their own vocabulary (DocumentLibrary::type)
	 * where the list must stay finite.
	 *
	 * @param string $role The document role.
	 * @param string $type The document type.
	 */
	public static function document_kind( string $role, string $type = '' ): string {
		$kinds = array(
			'datasheet'            => 'datasheet',
			'datenblatt'           => 'datasheet',
			'manual'               => 'manual',
			'user_manual'          => 'manual',
			'handbuch'             => 'manual',
			'anleitung'            => 'manual',
			'warranty'             => 'warranty',
			'garantie'             => 'warranty',
			'certificate'          => 'certificate',
			'zertifikat'           => 'certificate',
			'compatibility'        => 'compatibility',
			'compatibility_list'   => 'compatibility',
			'kompatibilität'       => 'compatibility',
			'kompatibilitätsliste' => 'compatibility',
			'brochure'             => 'brochure',
			'broschüre'            => 'brochure',
			'document'             => 'document',
			'dokument'             => 'document',
		);
		$lower = static fn( $value ): string => \mb_strtolower( \trim( (string) $value ), 'UTF-8' );
		foreach ( array( $role, $type ) as $value ) {
			if ( isset( $kinds[ $lower( $value ) ] ) ) {
				return $kinds[ $lower( $value ) ];
			}
		}
		return '' !== $lower( $type ) ? $lower( $type ) : 'document';
	}

	/**
	 * A document title in the page's language (AGENTS.md §3: the site never
	 * says catalogue; ticket #264 M3). The stored titles are manufacturer
	 * document names and may carry the English word; on a German page the
	 * standalone word becomes "Produktübersicht", a catalogue number becomes
	 * "Produktnummer", and English pages keep the stored title byte for byte.
	 *
	 * @param string    $title  The stored document title.
	 * @param bool|null $german Whether the page is German; null reads the request.
	 */
	public static function document_title_display( string $title, ?bool $german = null ): string {
		if ( ! ( $german ?? self::is_de() ) ) {
			return $title;
		}
		return self::apply_terms( $title, true );
	}

	/**
	 * The key figures of a product's purchase panel: the product type's first
	 * spec keys in the type's own order.
	 *
	 * @param WC_Product $product The product.
	 * @param int        $limit   How many rows the panel holds.
	 * @return list<array{key: string, label: string, value: string}>
	 */
	public static function key_stats( WC_Product $product, int $limit = 4 ): array {
		$order = array(
			'inverter'  => array( 'ac_power', 'phase', 'mppt', 'efficiency', 'batt_voltage', 'ip', 'weight', 'dimensions' ),
			'system'    => array( 'ac_power', 'nominal_kwh', 'phase', 'chemistry', 'ip', 'temp', 'weight', 'dimensions' ),
			'battery'   => array( 'usable_kwh', 'nominal_kwh', 'nom_voltage', 'chemistry', 'charge_a', 'discharge_a', 'ip', 'weight' ),
			'meter'     => array( 'accuracy', 'ratio', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'ct'        => array( 'ratio', 'accuracy', 'burden', 'temp', 'weight', 'dimensions' ),
			'ems'       => array( 'devices', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'accessory' => array( 'ac_power', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'other'     => array( 'nom_voltage', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
		);
		$kind  = self::contract_type( (string) self::identity( $product )['kind'] );
		$specs = self::specs( $product );
		if ( isset( $specs['phase']['value'] ) ) {
			$specs['phase']['value'] = self::phase_voltage_unit( $product, (string) $specs['phase']['value'] );
		}
		$out = array();
		foreach ( $order[ $kind ] ?? $order['other'] as $key ) {
			if ( ! isset( $specs[ $key ] ) ) {
				continue;
			}
			$out[] = array(
				'key'   => (string) $key,
				'label' => (string) $specs[ $key ]['label'],
				'value' => self::de_number( (string) $specs[ $key ]['value'] ),
			);
			if ( count( $out ) >= $limit ) {
				break;
			}
		}
		return $out;
	}

	/**
	 * Carry a voltage unit only when this same product states the identical
	 * combined phase/voltage value as an explicitly measured AC voltage.
	 *
	 * @param WC_Product $product Product owning both facts.
	 * @param string     $display Formatted phase value selected for the panel.
	 */
	private static function phase_voltage_unit( WC_Product $product, string $display ): string {
		$facts   = self::facts( $product );
		$voltage = $facts['rated_ac_voltage'] ?? null;
		if ( ! \is_array( $voltage ) || 'V' !== ( $voltage['unit'] ?? null ) || ! \is_string( $voltage['value'] ?? null ) || 1 !== \preg_match( '/^\s*[123]\s*\+\s*N\s*\+\s*PE\s*,\s*\d{2,4}\s*\/\s*\d{2,4}\s*$/iD', $voltage['value'] ) ) {
			return $display;
		}
		if ( $display !== $voltage['value'] ) {
			return $display;
		}
		foreach ( array( 'phase', 'phases' ) as $field ) {
			$phase = $facts[ $field ] ?? null;
			if ( ! \is_array( $phase ) || '' !== trim( (string) ( $phase['unit'] ?? '' ) ) || ( $phase['value'] ?? null ) !== $voltage['value'] ) {
				continue;
			}
			if ( self::spec_text( $product, 'phase', $field, $phase, self::is_de() )['value'] === $display ) {
				return self::value_with_unit( $display, 'V' );
			}
		}
		return $display;
	}

	/**
	 * The catalogue card's fact rows: the registry's figures in the card's own
	 * order, per the material type the live catalogue renders it with. The
	 * order table is read from the live card DOM (89 cards measured
	 * 2026-10-12 across the shop's three pages and the inverter archive):
	 * power modules read rated AC power / phase / MPPT / max. efficiency,
	 * the single-phase ones add their nominal AC voltage, the ESA battery
	 * modules usable energy / cell chemistry / ingress protection / system
	 * energy range, the transfer switches communication / ingress protection /
	 * weight / dimensions, the EcoFlow hybrid families phase / MPPT /
	 * efficiency / AC output. A missing row is skipped, never swapped, so the
	 * card's height follows its own data.
	 *
	 * @param WC_Product $product The product.
	 * @param int        $limit   How many rows the card holds.
	 * @return list<array{key: string, label: string, value: string}>
	 */
	public static function card_facts( WC_Product $product, int $limit = 4 ): array {
		// The figures live on the English record (#9): a German product's card
		// states the same values as its English twin because it reads them
		// through the same swap the selection facts use (i18n's
		// facts_product_id listener); without a language layer the asked-for
		// product answers itself.
		if ( \function_exists( 'has_filter' ) && \has_filter( 'linker_commerce_facts_product_id' ) ) {
			/**
			 * Filters the product the selection facts answer for; documented
			 * where it is registered (Linker\I18n\Woo\Storefront).
			 *
			 * @since 0.1.0
			 *
			 * @param int $product_id The product ID asked for.
			 */
			$source = (int) \apply_filters( 'linker_commerce_facts_product_id', (int) $product->get_id() );
			if ( $source > 0 && $source !== (int) $product->get_id() ) {
				$swapped = \wc_get_product( $source );
				if ( $swapped instanceof WC_Product ) {
					$product = $swapped;
				}
			}
		}
		$order = array(
			// The live's own material types first.
			'fixed_system'    => array( 'ac_power', 'phase', 'mppt', 'efficiency', 'ac_nom_voltage', 'system_range' ),
			'transfer_switch' => array( 'interface', 'ip', 'weight', 'dimensions', 'cooling_method' ),
			'battery_module'  => array( 'usable_kwh', 'nom_voltage', 'chemistry', 'ip', 'nominal_kwh' ),
			'ev_charger'      => array( 'ac_power', 'phase', 'rated_current_a', 'rated_voltage', 'ip', 'weight', 'nom_voltage', 'temp' ),
			// Contract types (contract_type()) for the rest.
			'inverter'        => array( 'ac_power', 'phase', 'mppt', 'efficiency', 'ac_output_kw_max', 'nom_voltage' ),
			'system'          => array( 'ac_power', 'nominal_kwh', 'phase', 'ip', 'ingress_protection', 'altitude', 'altitude_m', 'interface', 'ac_pf', 'usable_kwh', 'nom_voltage', 'chemistry', 'dimensions' ),
			'battery'         => array( 'usable_kwh', 'nom_voltage', 'chemistry', 'ip', 'system_range', 'nominal_kwh' ),
			'meter'           => array( 'accuracy', 'interface', 'ip', 'accuracy_class_reactive', 'communication_address_range', 'ratio', 'weight', 'dimensions' ),
			'ct'              => array( 'ratio', 'accuracy', 'burden', 'temp', 'interface', 'ip', 'weight' ),
			'ems'             => array( 'current_measurement', 'measurement_accuracy', 'measuring_cycle', 'ev_chargers', 'ip', 'ingress_protection', 'temp', 'operating_temp_range', 'operating_temperature_range', 'datalogger', 'box_material', 'dimensions', 'dimensions_hwd', 'power_consumption', 'interface', 'weight' ),
			'accessory'       => array( 'ac_power', 'phase', 'rated_current_a', 'rated_voltage', 'ip', 'ingress_protection', 'weight', 'accessory_option', 'altitude', 'interface', 'nom_voltage', 'temp' ),
			'other'           => array( 'ac_power', 'nominal_kwh', 'phase', 'mppt', 'efficiency', 'ac_output_w_nominal', 'backup_power_kw', 'max_pv_input_power_w', 'max_input_current_per_mppt_a', 'ip', 'interface', 'weight', 'temp' ),
		);
		$type  = (string) self::identity( $product )['kind'];
		$keys  = $order[ $type ] ?? $order[ self::contract_type( $type ) ] ?? $order['other'];
		$specs = self::specs( $product );
		$out   = array();
		foreach ( $keys as $key ) {
			if ( ! isset( $specs[ $key ] ) ) {
				continue;
			}
			$out[] = array(
				'key'   => (string) $key,
				'label' => (string) $specs[ $key ]['label'],
				'value' => self::de_number( (string) $specs[ $key ]['value'] ),
			);
			if ( count( $out ) >= $limit ) {
				break;
			}
		}
		return $out;
	}

	/**
	 * A stat value in the page's language: German prints decimals with a comma
	 * (the live German pages' own values read 5,0 kWh / 12,0 A).
	 *
	 * @param string $value The value.
	 */
	public static function de_number( string $value ): string {
		if ( ! self::is_de() ) {
			return $value;
		}
		return (string) \preg_replace( '/(?<=\d)\.(?=\d)/', ',', $value );
	}

	/**
	 * A document kind's label as the document card prints it.
	 *
	 * @param string $kind The kind.
	 */
	public static function document_kind_label( string $kind ): string {
		$labels = array(
			'datasheet'     => __( 'Datasheet', 'linker-commerce' ),
			'manual'        => __( 'Manual', 'linker-commerce' ),
			'warranty'      => __( 'Warranty', 'linker-commerce' ),
			'certificate'   => __( 'Certificate', 'linker-commerce' ),
			'compatibility' => __( 'Compatibility list', 'linker-commerce' ),
			'brochure'      => __( 'Brochure', 'linker-commerce' ),
			'document'      => __( 'Document', 'linker-commerce' ),
		);
		return $labels[ $kind ] ?? ( '' !== $kind ? ucfirst( $kind ) : '' );
	}
}
