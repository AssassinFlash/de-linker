<?php
/**
 * The selection facts of one product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Catalog;

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
	 * @param string                             $device_class    Product category slug (SelectionFacts::DEVICE_CLASSES) or unknown.
	 * @param 'home'|'commercial'|'unknown'      $application     Attribute pa_application.
	 * @param 1|3|'unknown'                      $phase           Number of grid phases.
	 * @param float|'unknown'                    $ac_power_kw     Rated AC (active) power in kW.
	 * @param float|'unknown'                    $pv_input_kw     Maximum PV input power in kW.
	 * @param float|'unknown'                    $usable_kwh      Usable energy in kWh.
	 * @param float|'unknown'                    $nominal_kwh     Nominal energy in kWh.
	 * @param array{min: float, max: float}|null $kwh_range       Energy range the figures state; never folded into a scalar.
	 * @param float|null                         $ac_apparent_kva Rated AC power the figures state in kVA instead of kW.
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
	 * The facts as the REST API and the abilities return them: the seven facts,
	 * then `kwh_range` and `ac_apparent_kva` only when the figures state them.
	 *
	 * @return array{device_class: string, application: 'home'|'commercial'|'unknown', phase: 1|3|'unknown', ac_power_kw: float|'unknown', pv_input_kw: float|'unknown', usable_kwh: float|'unknown', nominal_kwh: float|'unknown', kwh_range?: array{min: float, max: float}, ac_apparent_kva?: float}
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
}
