<?php
/**
 * The selection facts of one product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

/**
 * What the Solution Configurator, Genie's search-products and the product
 * category filters know about a product when they select it. Each of the seven
 * facts is always present; `unknown` is a value of its own, which a filter
 * neither matches nor counts as a conflict (docs/specs/7-selection-facts.md).
 */
final class SelectionFactSet {

	/**
	 * The value of a fact the product data does not establish.
	 */
	public const UNKNOWN = 'unknown';

	/**
	 * Sets the facts. SelectionFacts::for_product() is the one place that builds them.
	 *
	 * @param value-of<SelectionFacts::DEVICE_CLASSES>|'unknown' $device_class    Product category slug or unknown.
	 * @param 'home'|'commercial'|'unknown'                      $application     Attribute pa_application.
	 * @param 1|3|'unknown'                                      $phase           Number of grid phases.
	 * @param float|'unknown'                                    $ac_power_kw     Rated AC (active) power in kW.
	 * @param float|'unknown'                                    $pv_input_kw     Maximum PV input power in kW.
	 * @param float|'unknown'                                    $usable_kwh      Usable energy in kWh.
	 * @param float|'unknown'                                    $nominal_kwh     Nominal energy in kWh.
	 * @param array{min: float, max: float}|null                 $kwh_range       Energy range the figures state; never folded into a scalar.
	 * @param float|null                                         $ac_apparent_kva Rated AC power the figures state in kVA instead of kW.
	 */
	public function __construct(
		public readonly string $device_class,
		public readonly string $application,
		public readonly int|string $phase,
		public readonly float|string $ac_power_kw,
		public readonly float|string $pv_input_kw,
		public readonly float|string $usable_kwh,
		public readonly float|string $nominal_kwh,
		public readonly ?array $kwh_range = null,
		public readonly ?float $ac_apparent_kva = null
	) {}

	/**
	 * The facts as the REST route returns them: the seven facts, then
	 * `kwh_range` and `ac_apparent_kva` only when the figures state them.
	 *
	 * @return array{device_class: value-of<SelectionFacts::DEVICE_CLASSES>|'unknown', application: 'home'|'commercial'|'unknown', phase: 1|3|'unknown', ac_power_kw: float|'unknown', pv_input_kw: float|'unknown', usable_kwh: float|'unknown', nominal_kwh: float|'unknown', kwh_range?: array{min: float, max: float}, ac_apparent_kva?: float}
	 */
	public function to_array(): array {
		$facts = array(
			'device_class' => $this->device_class,
			'application'  => $this->application,
			'phase'        => $this->phase,
			'ac_power_kw'  => $this->ac_power_kw,
			'pv_input_kw'  => $this->pv_input_kw,
			'usable_kwh'   => $this->usable_kwh,
			'nominal_kwh'  => $this->nominal_kwh,
		);
		if ( null !== $this->kwh_range ) {
			$facts['kwh_range'] = $this->kwh_range;
		}
		if ( null !== $this->ac_apparent_kva ) {
			$facts['ac_apparent_kva'] = $this->ac_apparent_kva;
		}

		return $facts;
	}

	/**
	 * JSON Schema of to_array(), as the REST route documents it.
	 *
	 * @return array<string, mixed>
	 */
	public static function schema(): array {
		return array(
			'type'                 => 'object',
			'properties'           => array(
				'device_class'    => array(
					'description' => __( 'Product category the product is selected in.', 'linker-commerce' ),
					'type'        => 'string',
					'enum'        => array( ...SelectionFacts::DEVICE_CLASSES, self::UNKNOWN ),
				),
				'application'     => array(
					'description' => __( 'Application (attribute pa_application).', 'linker-commerce' ),
					'type'        => 'string',
					'enum'        => array( ...SelectionFacts::APPLICATIONS, self::UNKNOWN ),
				),
				'phase'           => array(
					'description' => __( 'Number of grid phases.', 'linker-commerce' ),
					'anyOf'       => array(
						array(
							'type' => 'integer',
							'enum' => array( 1, 3 ),
						),
						self::unknown_schema(),
					),
				),
				'ac_power_kw'     => self::number_schema( __( 'Rated AC power in kW.', 'linker-commerce' ) ),
				'pv_input_kw'     => self::number_schema( __( 'Maximum PV input power in kW.', 'linker-commerce' ) ),
				'usable_kwh'      => self::number_schema( __( 'Usable energy in kWh.', 'linker-commerce' ) ),
				'nominal_kwh'     => self::number_schema( __( 'Nominal energy in kWh.', 'linker-commerce' ) ),
				'kwh_range'       => array(
					'description'          => __( 'Energy range in kWh the product data states; present only then.', 'linker-commerce' ),
					'type'                 => 'object',
					'properties'           => array(
						'min' => array( 'type' => 'number' ),
						'max' => array( 'type' => 'number' ),
					),
					'required'             => array( 'min', 'max' ),
					'additionalProperties' => false,
				),
				'ac_apparent_kva' => array(
					'description' => __( 'Rated AC power the product data states in kVA; present only then.', 'linker-commerce' ),
					'type'        => 'number',
				),
			),
			'required'             => array( 'device_class', 'application', 'phase', 'ac_power_kw', 'pv_input_kw', 'usable_kwh', 'nominal_kwh' ),
			'additionalProperties' => false,
		);
	}

	/**
	 * Schema of a fact that is a number or unknown.
	 *
	 * @param string $description What the number is, with its unit.
	 * @return array<string, mixed>
	 */
	private static function number_schema( string $description ): array {
		return array(
			'description' => $description,
			'anyOf'       => array(
				array( 'type' => 'number' ),
				self::unknown_schema(),
			),
		);
	}

	/**
	 * Schema of the value unknown.
	 *
	 * @return array<string, mixed>
	 */
	private static function unknown_schema(): array {
		return array(
			'type' => 'string',
			'enum' => array( self::UNKNOWN ),
		);
	}
}
