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

namespace Linker\Commerce\Catalog;

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
	 * Product ID to material ID, built once per request.
	 *
	 * @var array<int, string>|null
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
	 * The material that speaks for a product, as the live lookup resolves it:
	 * the registry material bound to the product id.
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
					if ( $bound > 0 && ! isset( self::$product_index[ $bound ] ) ) {
						self::$product_index[ $bound ] = (string) $id;
					}
				}
			}
		}
		$material_id = self::$product_index[ $product_id ] ?? '';
		if ( '' === $material_id ) {
			// A German twin carries no registry binding of its own: the
			// English source row is the bound one.
			$source      = self::source_product_id( $product_id );
			$material_id = $source === $product_id ? '' : ( self::$product_index[ $source ] ?? '' );
		}
		if ( '' === $material_id ) {
			return null;
		}
		$material = self::registry()['materials'][ $material_id ] ?? null;
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
		$id          = (int) $product->get_id();
		$material    = self::material_for_product( $id );
		$identity    = \is_array( $material ) && \is_array( $material['identity'] ?? null ) ? $material['identity'] : array();
		$brand       = (string) ( $identity['manufacturer'] ?? '' );
		$model       = (string) ( $identity['model'] ?? '' );
		$kind        = (string) ( $identity['kind'] ?? 'other' );
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
	 * when no material is bound.
	 *
	 * @param WC_Product $product The product.
	 * @return array<string, array<string, mixed>>
	 */
	public static function facts( WC_Product $product ): array {
		$material = self::material_for_product( (int) $product->get_id() );
		if ( \is_array( $material ) ) {
			$specs = $material['technical']['specifications'] ?? array();
			return \is_array( $specs ) ? $specs : array();
		}
		$id  = (int) $product->get_id();
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
			'chemistry'                        => 'chemistry',
			'max_charge_current_a'             => 'charge_a',
			'max_discharge_current_a'          => 'discharge_a',
			'cycle_life'                       => 'cycles',
			'ratio'                            => 'ratio',
			'accuracy_class'                   => 'accuracy',
			'rated_burden_va'                  => 'burden',
			'bms_comms'                        => 'interface',
			'communication'                    => 'interface',
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
			'nominal_voltage_v'                => 'nominal_voltage_v',
			'system_nominal_voltage_v'         => 'system_nominal_voltage_v',
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
			'1'           => $de ? '1-phasig' : '1-phase',
			'3'           => $de ? '3-phasig' : '3-phase',
			'one'         => $de ? '1-phasig' : '1-phase',
			'three'       => $de ? '3-phasig' : '3-phase',
			'single'      => $de ? '1-phasig' : '1-phase',
			'three_phase' => $de ? '3-phasig' : '3-phase',
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
		if ( ! $localise ) {
			return \rtrim( \rtrim( \number_format( $kilo, 2, '.', '' ), '0' ), '.' ) . ' ' . $label;
		}
		$printed = \floor( $kilo ) === $kilo
			? (string) (int) $kilo
			: \number_format( $kilo, \ceil( $kilo * 10 ) / 10 === \round( $kilo, 1 ) ? 1 : 2, $de ? ',' : '.', '' );
		if ( \str_contains( $printed, '.' ) ) {
			$printed = \rtrim( \rtrim( $printed, '0' ), '.' );
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
			'nominal_voltage_v'               => __( 'Nominal voltage', 'linker-commerce' ),
			'system_nominal_voltage_v'        => __( 'System nominal voltage', 'linker-commerce' ),
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
				return $decoded;
			}
			$source  = self::source_product_id( $product_id );
			$decoded = self::decode( \get_post_meta( $source, '_linker_de_acf_json', true ) );
			return $decoded;
		}
		return self::decode( \get_post_meta( $product_id, '_tv_legacy_acf_json', true ) );
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
	 * The availability text the live page prints
	 * (tv_woo_b2b_availability_text over the stock mirror).
	 *
	 * @param WC_Product $product The product.
	 * @param bool       $sellable Whether the product is sellable.
	 */
	public static function availability_text( WC_Product $product, bool $sellable ): string {
		$de = self::is_de();
		if ( ! $sellable ) {
			return $de ? 'Derzeit nicht bestellbar' : 'Currently not orderable';
		}
		$id       = (int) $product->get_id();
		$stamped  = '' !== (string) \get_post_meta( $id, '_tv_b2b_stock_mirrored_at', true );
		$days_min = \get_post_meta( $id, '_tv_b2b_lead_time_days_min', true );
		$days_max = \get_post_meta( $id, '_tv_b2b_lead_time_days_max', true );
		if ( $stamped ) {
			$status = $product->get_stock_status();
			if ( 'instock' === $status ) {
				$state = 'available';
			} elseif ( 'outofstock' === $status ) {
				$state = 'unavailable';
			} elseif ( 'onbackorder' === $status && \is_numeric( $days_min ) && \is_numeric( $days_max ) ) {
				$state = 'lead_time';
			} else {
				$state = 'on_request';
			}
			if ( ( 'available' === $state || 'lead_time' === $state ) ) {
				$expires = (string) \get_post_meta( $id, '_tv_b2b_supply_expires_at', true );
				$stamp   = '' !== $expires ? \strtotime( $expires ) : false;
				if ( false !== $stamp && $stamp <= \time() ) {
					$state = 'on_request';
				}
			}
		} else {
			$state = 'on_request';
		}
		if ( 'available' === $state ) {
			return $de ? 'Auf Lager' : 'In stock';
		}
		if ( 'lead_time' === $state ) {
			$min  = (int) $days_min;
			$max  = (int) $days_max;
			$days = $min === $max ? (string) $min : $min . '–' . $max;
			return $de
				? 'Bestellbar · Lieferzeit ' . $days . ' Kalendertage'
				: 'Orderable · lead time ' . $days . ' calendar days';
		}
		return $de ? 'Derzeit nicht bestellbar' : 'Currently not orderable';
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
		$editor = \array_filter( \array_map( 'intval', (array) \get_post_meta( (int) $product->get_id(), '_product_image_gallery', true ) ) );
		foreach ( $editor as $image_id ) {
			if ( \wp_attachment_is_image( $image_id ) && ! \in_array( $image_id, $ids, true ) ) {
				$ids[] = $image_id;
			}
		}
		return $ids;
	}

	/**
	 * The documents of a product: the ACF download rows and the registry's
	 * documents, deduplicated and ranked
	 * (tv_woo_b2b_product_documents).
	 *
	 * @return list<array{kind: string, title: string, language: string, url: string}>
	 * @param WC_Product $product The product.
	 */
	public static function documents( WC_Product $product ): array {
		$out    = array();
		$seen   = array();
		$titles = array();
		$seq    = 0;
		$push   = static function ( $kind, $title, $language, $url, $registry = false ) use ( &$out, &$seen, &$titles, &$seq ) {
			$url = \trim( (string) $url );
			if ( '' === $url || ! self::is_hosted_url( $url ) ) {
				return;
			}
			$key      = \preg_replace( '#/+$#', '', $url );
			$path     = (string) \wp_parse_url( $url, \PHP_URL_PATH );
			$file_key = '' !== $path ? \strtolower( \basename( $path ) ) : '';
			$title    = \trim( (string) $title );
			$language = \strtoupper( \trim( (string) $language ) );
			if ( 'MUL' === $language ) {
				$language = __( 'Multilingual', 'linker-commerce' );
			}
			if ( '' === $language || '' !== self::document_language_tag( $title ) ) {
				$language = self::document_language( $title, $url );
			}
			$title_key = \strtolower( $title ) . '|' . $language;
			if ( isset( $seen[ $key ] ) || ( '' !== $file_key && isset( $seen[ $file_key ] ) ) ) {
				$titles[ $title_key ] = true;
				return;
			}
			if ( $registry && isset( $titles[ $title_key ] ) ) {
				return;
			}
			$seen[ $key ] = true;
			if ( '' !== $file_key ) {
				$seen[ $file_key ] = true;
			}
			$titles[ $title_key ] = true;
			$out[]                = array(
				'kind'      => $kind,
				'title'     => '' !== $title ? $title : \ucfirst( (string) $kind ),
				'language'  => $language,
				'url'       => $url,
				'_sequence' => $seq++,
			);
		};

		$product_id = (int) $product->get_id();
		$own_urls   = array();
		$acf        = self::acf( $product_id );
		$downloads  = isset( $acf['downloads'] ) && \is_array( $acf['downloads'] ) ? $acf['downloads'] : array();
		foreach ( $downloads as $download ) {
			if ( ! \is_array( $download ) ) {
				continue;
			}
			$file_id = (int) ( $download['download_file'] ?? 0 );
			$url     = $file_id ? \trim( (string) \wp_get_attachment_url( $file_id ) ) : '';
			if ( '' === $url ) {
				$url = (string) ( $download['download_url'] ?? '' );
			}
			$push(
				self::document_kind( (string) ( $download['download_role'] ?? '' ), (string) ( $download['download_type'] ?? '' ) ),
				(string) ( $download['download_title'] ?? 'Document' ),
				(string) ( $download['download_language'] ?? 'EN' ),
				$url
			);
		}

		$material      = self::material_for_product( $product_id );
		$registry_docs = \is_array( $material ) && \is_array( $material['technical']['documents'] ?? null )
			? $material['technical']['documents'] : array();
		foreach ( $registry_docs as $document ) {
			if ( ! \is_array( $document ) ) {
				continue;
			}
			if ( self::registry_document_is_foreign( $document, $product_id, $own_urls ) ) {
				continue;
			}
			$push(
				self::document_kind( '', (string) ( $document['kind'] ?? '' ) ),
				(string) ( $document['title'] ?? 'Document' ),
				(string) ( $document['language'] ?? 'EN' ),
				(string) ( $document['url'] ?? '' ),
				true
			);
		}

		$rank = array(
			'datasheet' => 0,
			'manual'    => 1,
			'warranty'  => 2,
		);
		\usort(
			$out,
			static function ( $left, $right ) use ( $rank ) {
				$left_rank  = $rank[ $left['kind'] ] ?? 3;
				$right_rank = $rank[ $right['kind'] ] ?? 3;
				if ( $left_rank !== $right_rank ) {
					return $left_rank < $right_rank ? -1 : 1;
				}
				return $left['_sequence'] <=> $right['_sequence'];
			}
		);
		foreach ( $out as &$document ) {
			unset( $document['_sequence'] );
		}
		return $out;
	}

	/**
	 * Whether a URL is one of our hosted document URLs.
	 *
	 * @param string $url The URL.
	 */
	public static function is_hosted_url( string $url ): bool {
		$url = \trim( $url );
		if ( '' === $url ) {
			return false;
		}
		$scheme = \strtolower( (string) ( \wp_parse_url( $url, \PHP_URL_SCHEME ) ? \wp_parse_url( $url, \PHP_URL_SCHEME ) : '' ) );
		if ( 'https' !== $scheme && 'http' !== $scheme ) {
			return false;
		}
		$host = \strtolower( (string) ( \wp_parse_url( $url, \PHP_URL_HOST ) ? \wp_parse_url( $url, \PHP_URL_HOST ) : '' ) );
		$home = \strtolower( (string) ( \wp_parse_url( (string) \home_url(), \PHP_URL_HOST ) ? \wp_parse_url( (string) \home_url(), \PHP_URL_HOST ) : '' ) );
		return $host === $home || \str_ends_with( $host, '.' . $home ) || 'de-linker.com' === $host || \str_ends_with( $host, '.de-linker.com' );
	}

	/**
	 * A download row's kind (tv_woo_b2b_document_kind).
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
	 * The language tag a document title carries, '' when it carries none.
	 *
	 * @param string $title The title.
	 */
	public static function document_language_tag( string $title ): string {
		if ( ! \preg_match( '/[\[(]\s*(DE|EN|ES|IT|PT|multilingual|mehrsprachig)\s*[\])]/i', $title, $m ) ) {
			return '';
		}
		return \strlen( $m[1] ) > 2 ? __( 'Multilingual', 'linker-commerce' ) : \strtoupper( $m[1] );
	}

	/**
	 * A document's language, read from its title or its file name.
	 *
	 * @param string $title The title.
	 * @param string $url The URL.
	 */
	public static function document_language( string $title, string $url ): string {
		$tag = self::document_language_tag( $title );
		if ( '' !== $tag ) {
			return $tag;
		}
		$file = \strtolower( (string) \wp_parse_url( $url, \PHP_URL_PATH ) );
		$file = (string) \substr( $file, (int) \strrpos( $file, '/' ) );
		if ( \preg_match( '/[-_.](de|en|es|it|pt)(?=[-_.]|$)/', (string) \preg_replace( '/\.[a-z0-9]+$/', '', $file ), $m ) ) {
			return \strtoupper( $m[1] );
		}
		if ( \preg_match( '/\b(datenblatt|handbuch|anleitung|bedienungsanleitung|garantie|deutsch|german)\b/iu', $title ) ) {
			return 'DE';
		}
		return 'EN';
	}

	/**
	 * Whether a registry document belongs to another product
	 * (tv_woo_b2b_registry_document_is_foreign).
	 *
	 * @param array<string, mixed> $document The document row.
	 * @param int                  $product_id The product ID.
	 * @param array<string, bool>  $own_urls The product's own document URLs.
	 */
	private static function registry_document_is_foreign( array $document, int $product_id, array $own_urls ): bool {
		$refs = isset( $document['evidence_refs'] ) && \is_array( $document['evidence_refs'] ) ? $document['evidence_refs'] : array();
		if ( ! $refs ) {
			return false;
		}
		foreach ( $refs as $ref ) {
			if ( ! \is_string( $ref ) || ! \preg_match( '/^woo:(\d+):/', $ref, $match ) ) {
				return false;
			}
			if ( (int) $match[1] === $product_id ) {
				return false;
			}
		}
		$url = \preg_replace( '#/+$#', '', \trim( (string) ( $document['url'] ?? '' ) ) );
		return '' === $url || ! isset( $own_urls[ $url ] );
	}

	/**
	 * The key figures of a product's purchase panel: the product type's first
	 * spec keys, in the type's own order, each with the symbol it shows. The
	 * order and the symbol are type vocabulary, not page design.
	 *
	 * @param WC_Product $product The product.
	 * @param int        $limit   How many rows the panel holds.
	 * @return list<array{key: string, label: string, value: string, icon: string}>
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
		$icons = array(
			'phase'       => 'grid',
			'mppt'        => 'grid',
			'usable_kwh'  => 'energy',
			'nominal_kwh' => 'energy',
			'efficiency'  => 'gauge',
		);
		$kind  = self::contract_type( (string) self::identity( $product )['kind'] );
		$specs = self::specs( $product );
		$out   = array();
		foreach ( $order[ $kind ] ?? $order['other'] as $key ) {
			if ( ! isset( $specs[ $key ] ) ) {
				continue;
			}
			$out[] = array(
				'key'   => (string) $key,
				'label' => (string) $specs[ $key ]['label'],
				'value' => self::de_number( (string) $specs[ $key ]['value'] ),
				'icon'  => (string) ( $icons[ $key ] ?? 'power' ),
			);
			if ( count( $out ) >= $limit ) {
				break;
			}
		}
		return $out;
	}

	/**
	 * The catalogue card's fact rows: the registry's figures in the card's own
	 * order (measured on the live catalogue 2026-10-11: inverters read AC
	 * power / phase / MPPT / efficiency, battery modules usable energy /
	 * chemistry / ingress protection / system energy range, cabinets usable
	 * energy / nominal voltage / chemistry / ingress protection, the
	 * meter-and-accessory families communication / ingress protection /
	 * weight / dimensions). Availability skips a missing row, so the count
	 * follows the data.
	 *
	 * @param WC_Product $product The product.
	 * @param int        $limit   How many rows the card holds.
	 * @return list<array{key: string, label: string, value: string}>
	 */
	public static function card_facts( WC_Product $product, int $limit = 4 ): array {
		$order = array(
			'inverter'  => array( 'ac_power', 'phase', 'mppt', 'efficiency', 'nom_voltage' ),
			'battery'   => array( 'usable_kwh', 'chemistry', 'ip', 'system_range', 'nominal_kwh' ),
			'system'    => array( 'usable_kwh', 'nom_voltage', 'chemistry', 'ip' ),
			'meter'     => array( 'interface', 'ip', 'weight', 'dimensions' ),
			'ct'        => array( 'interface', 'ip', 'weight', 'dimensions' ),
			'ems'       => array( 'interface', 'ip', 'weight', 'dimensions' ),
			'accessory' => array( 'interface', 'ip', 'weight', 'dimensions' ),
			'other'     => array( 'interface', 'ip', 'weight', 'dimensions' ),
		);
		$kind  = self::contract_type( (string) self::identity( $product )['kind'] );
		$specs = self::specs( $product );
		$out   = array();
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
			'document'      => __( 'Document', 'linker-commerce' ),
		);
		return $labels[ $kind ] ?? ( '' !== $kind ? ucfirst( $kind ) : '' );
	}
}
