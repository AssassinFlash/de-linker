<?php
/**
 * Ability linker/read-solution.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Account\SavedSolutions;
use WP_Error;

/**
 * The customer's own saved result, read as history. Neither product metadata
 * nor the current sizing engine can fill in or rewrite a historical snapshot.
 */
final class ReadSolution {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/read-solution';

	/** Languages accepted by the existing ability contract. */
	private const LANGUAGES = array( 'en', 'de' );

	/**
	 * Sets up the historical reader.
	 *
	 * @param SavedSolutions $solutions Customer-owned snapshots.
	 */
	public function __construct( private readonly SavedSolutions $solutions ) {}

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$range = array(
			'type'                 => 'object',
			'properties'           => array(
				'low'  => array( 'type' => 'number' ),
				'high' => array( 'type' => 'number' ),
			),
			'required'             => array( 'low', 'high' ),
			'additionalProperties' => false,
		);
		$item  = array(
			'type'                 => 'object',
			'properties'           => array(
				'product_id' => array( 'type' => 'integer' ),
				'quantity'   => array( 'type' => 'integer' ),
				'model'      => array( 'type' => 'string' ),
			),
			'required'             => array( 'product_id', 'quantity', 'model' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'Read a saved solution', 'linker-commerce' ),
			'description'         => __( 'Returns this account\'s own saved historical snapshot and its selection basis. This does not recalculate a design or provide current product facts.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'solution_id' => array(
						'type'    => 'integer',
						'minimum' => 1,
					),
					'lang'        => array(
						'type' => 'string',
						'enum' => self::LANGUAGES,
					),
				),
				'required'             => array( 'solution_id' ),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'historical' => array( 'type' => 'boolean' ),
					'id'         => array( 'type' => 'integer' ),
					'title'      => array( 'type' => 'string' ),
					'created'    => array( 'type' => 'string' ),
					'status'     => array(
						'type' => 'string',
						'enum' => array( 'solution', 'no_candidate' ),
					),
					'yield'      => array(
						'type'                 => 'object',
						'properties'           => array(
							'kwh_year_low'  => array( 'type' => 'number' ),
							'kwh_year_high' => array( 'type' => 'number' ),
							'kwh_year_mean' => array( 'type' => 'number' ),
						),
						'required'             => array( 'kwh_year_low', 'kwh_year_high', 'kwh_year_mean' ),
						'additionalProperties' => false,
					),
					'storage'    => array(
						'type'                 => 'object',
						'properties'           => array(
							'usable_kwh'  => array( 'type' => array( 'number', 'null' ) ),
							'recommended' => array( 'type' => 'boolean' ),
						),
						'required'             => array( 'usable_kwh', 'recommended' ),
						'additionalProperties' => false,
					),
					'metrics'    => array(
						'type'       => array( 'object', 'null' ),
						'properties' => array(
							'autarky_low'           => array( 'type' => 'number' ),
							'autarky_high'          => array( 'type' => 'number' ),
							'self_consumption_low'  => array( 'type' => 'number' ),
							'self_consumption_high' => array( 'type' => 'number' ),
						),
					),
					'selected'   => array(
						'type'       => array( 'object', 'null' ),
						'properties' => array(
							'inverter'         => array( 'type' => 'string' ),
							'battery'          => array( 'type' => array( 'string', 'null' ) ),
							'battery_quantity' => array( 'type' => array( 'integer', 'null' ) ),
						),
					),
					'basis'      => array(
						'type'  => 'array',
						'items' => array( 'type' => 'string' ),
					),
					'warnings'   => array(
						'type'  => 'array',
						'items' => array( 'type' => 'string' ),
					),
					'items'      => array(
						'type'  => 'array',
						'items' => $item,
					),
				),
				'required'             => array( 'historical', 'id', 'title', 'created', 'status', 'yield', 'storage', 'metrics', 'selected', 'basis', 'warnings', 'items' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Only a logged-in customer may read a saved solution; a guest answers 401.
	 */
	public function can_execute(): bool {
		return is_user_logged_in();
	}

	/**
	 * This account's own saved solution, read from the stored design.
	 *
	 * @param array<string, mixed>|object $input solution_id, and lang when the turn is German.
	 * @return array<string, mixed>|WP_Error
	 */
	public function execute( $input = array() ) {
		$input = (array) $input;
		$id    = (int) ( $input['solution_id'] ?? 0 );
		if ( $id < 1 ) {
			return new WP_Error( 'linker_solution_id', __( 'A solution ID is required.', 'linker-commerce' ), array( 'status' => 400 ) );
		}
		if ( ! is_user_logged_in() ) {
			return new WP_Error( 'linker_solution_login', __( 'Sign in to read your saved solution.', 'linker-commerce' ), array( 'status' => 401 ) );
		}
		$owner = $this->solutions->owner( $id );
		if ( $owner < 1 ) {
			return new WP_Error( 'linker_solution_missing', __( 'The saved solution was not found.', 'linker-commerce' ), array( 'status' => 404 ) );
		}
		if ( get_current_user_id() !== $owner ) {
			return new WP_Error( 'linker_solution_owner', __( 'This saved solution belongs to another account.', 'linker-commerce' ), array( 'status' => 403 ) );
		}
		$result = $this->solutions->snapshot( $id );
		if ( null === $result ) {
			return new WP_Error( 'linker_solution_snapshot_missing', __( 'This saved solution has no recorded design details. Its saved documents are still available in your account.', 'linker-commerce' ), array( 'status' => 422 ) );
		}
		if ( ! is_array( $result['yield'] ?? null ) || ! is_array( $result['storage'] ?? null ) ) {
			return new WP_Error( 'linker_solution_unsupported', __( 'These saved design details are not available in Genie. Your saved solution and documents remain in your account.', 'linker-commerce' ), array( 'status' => 422 ) );
		}
		return $this->output( $id, $result );
	}

	/**
	 * The engine's result reduced to what Genie reads: figures, basis, items.
	 * Only these fields are copied, so no price or amount can ride along.
	 *
	 * @param int                  $id     Solution id.
	 * @param array<string, mixed> $result Engine's ResidentialResult.
	 * @return array<string, mixed>
	 */
	private function output( int $id, array $result ): array {
		$yield    = is_array( $result['yield'] ?? null ) ? $result['yield'] : array();
		$range    = is_array( $yield['kwh_year_range'] ?? null ) ? $yield['kwh_year_range'] : array();
		$storage  = is_array( $result['storage'] ?? null ) ? $result['storage'] : array();
		$metrics  = is_array( $result['metrics'] ?? null ) ? $result['metrics'] : null;
		$selected = is_array( $result['selected'] ?? null ) ? $result['selected'] : null;
		$items    = array();
		foreach ( $this->solutions->items( $id ) as $item ) {
			$items[] = array(
				'product_id' => $item['product_id'],
				'quantity'   => $item['quantity'],
				'model'      => $this->item_model( $selected, $item['product_id'] ),
			);
		}
		$battery = is_array( $selected['battery'] ?? null ) ? $selected['battery'] : null;

		return array(
			'historical' => true,
			'id'         => $id,
			// The stored title, not get_the_title(): a private post's title is
			// prefixed "Private:" for display, and that prefix is not the
			// customer's name for their solution.
			'title'      => (string) get_post_field( 'post_title', $id ),
			'created'    => (string) get_post_time( 'Y-m-d', false, $id ),
			'status'     => 'solution' === ( $result['status'] ?? '' ) ? 'solution' : 'no_candidate',
			'yield'      => array(
				'kwh_year_low'  => (float) ( $range['low'] ?? 0 ),
				'kwh_year_high' => (float) ( $range['high'] ?? 0 ),
				'kwh_year_mean' => (float) ( $yield['kwh_year_mean'] ?? 0 ),
			),
			'storage'    => array(
				'usable_kwh'  => $metrics && is_numeric( $metrics['usable_kwh'] ?? null ) ? (float) $metrics['usable_kwh'] : null,
				'recommended' => (bool) ( $storage['recommended'] ?? false ),
			),
			'metrics'    => $metrics ? array(
				'autarky_low'           => (float) ( $this->range_value( $metrics, 'autarky_range', 'low' ) ),
				'autarky_high'          => (float) ( $this->range_value( $metrics, 'autarky_range', 'high' ) ),
				'self_consumption_low'  => (float) ( $this->range_value( $metrics, 'self_consumption_range', 'low' ) ),
				'self_consumption_high' => (float) ( $this->range_value( $metrics, 'self_consumption_range', 'high' ) ),
			) : null,
			'selected'   => $selected ? array(
				'inverter'         => $this->product_name( $selected['inverter'] ?? null ),
				'battery'          => $battery ? $this->product_name( $battery['product'] ?? null ) : null,
				'battery_quantity' => $battery ? (int) ( $battery['quantity'] ?? 0 ) : null,
			) : null,
			'basis'      => $this->basis( $selected, $storage ),
			'warnings'   => $this->texts( $result['warnings'] ?? null ),
			'items'      => $items,
		);
	}

	/**
	 * The selection basis the design report shows: the inverter's rules, the
	 * storage sizing's rules, and the battery's release conditions.
	 *
	 * @param array<string, mixed>|null $selected The engine's selection, null for no candidate.
	 * @param array<string, mixed>      $storage  The engine's storage result.
	 * @return list<string>
	 */
	private function basis( ?array $selected, array $storage ): array {
		$lines          = array();
		$inverter_rules = is_array( $selected['inverter_rules'] ?? null ) ? $selected['inverter_rules'] : array();
		$storage_rules  = is_array( $storage['basis'] ?? null ) ? $storage['basis'] : array();
		foreach ( array( $inverter_rules, $storage_rules ) as $rules ) {
			foreach ( $rules as $rule ) {
				if ( is_array( $rule ) && is_string( $rule['text'] ?? null ) && '' !== $rule['text'] ) {
					$lines[] = $rule['text'];
				}
			}
		}
		$battery = is_array( $selected['battery'] ?? null ) ? $selected['battery'] : array();
		$release = is_array( $battery['release'] ?? null ) ? $battery['release'] : array();
		return array_merge( $lines, $this->texts( $release['conditions'] ?? null ) );
	}

	/**
	 * The model of a saved item, from the engine's Stückliste lines; '' when the
	 * engine no longer selects that product.
	 *
	 * @param array<string, mixed>|null $selected The engine's selection.
	 * @param int                       $product_id Saved product.
	 */
	private function item_model( ?array $selected, int $product_id ): string {
		foreach ( is_array( $selected['lines'] ?? null ) ? $selected['lines'] : array() as $line ) {
			if ( is_array( $line ) && is_array( $line['product'] ?? null ) && (int) ( $line['product']['id'] ?? 0 ) === $product_id ) {
				return $this->product_name( $line['product'] );
			}
		}
		return '';
	}

	/**
	 * A product reference as the report writes it: "Brand Model".
	 *
	 * @param mixed $product A ProductRef.
	 */
	private function product_name( mixed $product ): string {
		$product = is_array( $product ) ? $product : array();
		return trim( (string) ( $product['brand'] ?? '' ) . ' ' . (string) ( $product['model'] ?? '' ) );
	}

	/**
	 * One low/high value of a range in the engine's result.
	 *
	 * @param array<string, mixed> $metrics The engine's metrics.
	 * @param string               $range   The range's key.
	 * @param string               $end     `low` or `high`.
	 */
	private function range_value( array $metrics, string $range, string $end ): float {
		$found = is_array( $metrics[ $range ] ?? null ) ? $metrics[ $range ] : array();
		return is_numeric( $found[ $end ] ?? null ) ? (float) $found[ $end ] : 0.0;
	}

	/**
	 * The strings of a list, ignoring everything that is not one.
	 *
	 * @param mixed $value A list from the engine's result.
	 * @return list<string>
	 */
	private function texts( mixed $value ): array {
		$texts = array();
		foreach ( is_array( $value ) ? $value : array() as $item ) {
			if ( is_string( $item ) && '' !== $item ) {
				$texts[] = $item;
			}
		}
		return $texts;
	}
}
