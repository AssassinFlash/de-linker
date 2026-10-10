<?php
/**
 * Ability linker/compare-products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Catalog\SelectionFacts;
use Linker\Commerce\Catalog\SelectionFactSet;

/**
 * A comparison table of two to four published products. Battery energy and
 * inverter output are different rows, never one mixed "power" row
 * (docs/specs/13-genie.md).
 */
final class CompareProducts {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/compare-products';

	/**
	 * Inverter-side dimensions, in display order.
	 */
	private const INVERTER_FIELDS = array( 'application', 'phase', 'ac_power_kw', 'pv_input_kw' );

	/**
	 * Battery-side dimensions, in display order.
	 */
	private const BATTERY_FIELDS = array( 'usable_kwh', 'nominal_kwh', 'kwh_range' );

	/**
	 * Device classes that show the inverter-side rows.
	 */
	private const INVERTER_CLASSES = array( 'inverters', 'all-in-one-systems' );

	/**
	 * Device classes that show the battery-side rows.
	 */
	private const BATTERY_CLASSES = array( 'home-storage', 'battery-systems', 'all-in-one-systems' );

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		return array(
			'label'               => __( 'Compare products', 'linker-commerce' ),
			'description'         => __( 'A table of two to four published products. Battery energy and inverter output are separate rows.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'product_ids' => array(
						'type'     => 'array',
						'minItems' => 2,
						'maxItems' => 4,
						'items'    => array(
							'type'    => 'integer',
							'minimum' => 1,
						),
					),
					'lang'        => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
				),
				'required'             => array( 'product_ids' ),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'products' => array(
						'type'  => 'array',
						'items' => array(
							'type'                 => 'object',
							'properties'           => array(
								'product_id' => array( 'type' => 'integer' ),
								'title'      => array( 'type' => 'string' ),
								'url'        => array( 'type' => 'string' ),
								'facts'      => array( 'type' => 'object' ),
							),
							'required'             => array( 'product_id', 'title', 'url', 'facts' ),
							'additionalProperties' => false,
						),
					),
					'rows'     => array(
						'type'  => 'array',
						'items' => array(
							'type'                 => 'object',
							'properties'           => array(
								'field'  => array( 'type' => 'string' ),
								'label'  => array( 'type' => 'string' ),
								'values' => array(
									'type'                 => 'object',
									'additionalProperties' => true,
								),
							),
							'required'             => array( 'field', 'label', 'values' ),
							'additionalProperties' => false,
						),
					),
				),
				'required'             => array( 'products', 'rows' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may compare published products.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * The table: one column per published id, rows chosen from the classes present.
	 *
	 * @param array<string, mixed>|object $input product_ids and optional lang.
	 * @return array{products: list<array<string, mixed>>, rows: list<array<string, mixed>>}
	 */
	public function execute( $input = array() ): array {
		$input    = (array) $input;
		$lang     = CatalogText::lang( $input['lang'] ?? null );
		$ids      = array_values( array_unique( array_map( 'intval', (array) ( $input['product_ids'] ?? array() ) ) ) );
		$ids      = array_values(
			array_filter(
				$ids,
				static fn( int $id ): bool => $id > 0 && 'product' === get_post_type( $id ) && 'publish' === get_post_status( $id )
			)
		);
		$products = array();
		$classes  = array();
		foreach ( $ids as $id ) {
			$facts      = SelectionFacts::for_product( $id );
			$classes[]  = $facts->device_class;
			$products[] = array(
				'product_id' => $id,
				'title'      => CatalogText::title( $id, $lang ),
				'url'        => CatalogText::url( $id, $lang ),
				'facts'      => $facts->to_array(),
			);
		}
		$fields = $this->fields( $classes );

		return array(
			'products' => $products,
			'rows'     => array_values(
				array_map(
					fn( string $field ): array => $this->row( $field, $products, $lang ),
					$fields
				)
			),
		);
	}

	/**
	 * Dimension keys for the classes on the table: inverter rows, then battery
	 * rows, never a shared "power" row.
	 *
	 * @param string[] $classes Device classes of the columns.
	 * @return string[]
	 */
	private function fields( array $classes ): array {
		$fields = array();
		if ( array() !== array_intersect( $classes, self::INVERTER_CLASSES ) ) {
			$fields = array_merge( $fields, self::INVERTER_FIELDS );
		}
		if ( array() !== array_intersect( $classes, self::BATTERY_CLASSES ) ) {
			$fields = array_merge( $fields, self::BATTERY_FIELDS );
		}
		if ( array() === $fields ) {
			$fields = array( 'device_class', 'application' );
		}

		return $fields;
	}

	/**
	 * One dimension row: field, label, values keyed by product ID.
	 *
	 * @param string                     $field    Fact key.
	 * @param list<array<string, mixed>> $products Columns.
	 * @param 'en'|'de'                  $lang     Language of the labels.
	 * @return array{field: string, label: string, values: object}
	 */
	private function row( string $field, array $products, string $lang ): array {
		$values = array();
		foreach ( $products as $product ) {
			$facts                            = $product['facts'];
			$values[ $product['product_id'] ] = $facts[ $field ] ?? SelectionFactSet::UNKNOWN;
		}

		return array(
			'field'  => $field,
			'label'  => $this->label( $field, $lang ),
			'values' => (object) $values,
		);
	}

	/**
	 * Row label. English and German are both stored because the table is built
	 * once per request language.
	 *
	 * @param string    $field Fact key.
	 * @param 'en'|'de' $lang  Language.
	 */
	private function label( string $field, string $lang ): string {
		$labels = array(
			'en' => array(
				'device_class' => 'Product category',
				'application'  => 'Application',
				'phase'        => 'Phases',
				'ac_power_kw'  => 'Rated AC power (kW)',
				'pv_input_kw'  => 'Maximum PV input (kW)',
				'usable_kwh'   => 'Usable energy (kWh)',
				'nominal_kwh'  => 'Nominal energy (kWh)',
				'kwh_range'    => 'Energy range (kWh)',
			),
			'de' => array(
				'device_class' => 'Produktkategorie',
				'application'  => 'Anwendung',
				'phase'        => 'Phasen',
				'ac_power_kw'  => 'Bemessungsleistung AC (kW)',
				'pv_input_kw'  => 'Maximale PV-Eingangsleistung (kW)',
				'usable_kwh'   => 'Nutzbare Energie (kWh)',
				'nominal_kwh'  => 'Nennenergie (kWh)',
				'kwh_range'    => 'Energiebereich (kWh)',
			),
		);

		return $labels[ $lang ][ $field ] ?? $field;
	}
}
