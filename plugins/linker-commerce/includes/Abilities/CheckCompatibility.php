<?php
/**
 * Ability linker/check-compatibility.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;

/**
 * Pairing against data/compatibility.json (docs/specs/8-engineering-data.md).
 * A combination the contract does not mention is unknown, never inferred.
 */
final class CheckCompatibility {
	/**
	 * Current operation snapshot, refreshed for every selection.
	 *
	 * @var array<string,mixed>
	 */
	private array $publication_snapshot = array();
	/**
	 * Use the shared current authority.
	 *
	 * @param PublicationData $publication Current authority reader.
	 */
	public function __construct( private readonly PublicationData $publication = new PublicationData() ) {}


	/**
	 * Ability name.
	 */
	public const NAME = 'linker/check-compatibility';

	/**
	 * Device classes treated as inverters when product_ids is a mixed pair.
	 */
	private const INVERTER_CLASSES = array( 'inverters', 'all-in-one-systems' );

	/**
	 * Device classes treated as batteries when product_ids is a mixed pair.
	 */
	private const BATTERY_CLASSES = array( 'home-storage', 'battery-systems' );

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$document = array(
			'type'                 => 'object',
			'properties'           => array(
				'url'  => array( 'type' => 'string' ),
				'page' => array( 'type' => 'integer' ),
			),
			'required'             => array( 'url' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'Check inverter and battery compatibility', 'linker-commerce' ),
			'description'         => __( 'Returns the documented release of an inverter with a battery: released, released with an accessory, not released, or unknown when no file covers the pair.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'inverter_id' => array(
						'type'        => 'integer',
						'minimum'     => 1,
						'description' => __( 'Inverter product ID.', 'linker-commerce' ),
					),
					'battery_id'  => array(
						'type'        => 'integer',
						'minimum'     => 1,
						'description' => __( 'Battery product ID.', 'linker-commerce' ),
					),
					'product_ids' => array(
						'type'        => 'array',
						'minItems'    => 2,
						'maxItems'    => 2,
						'items'       => array(
							'type'    => 'integer',
							'minimum' => 1,
						),
						'description' => __( 'Two product IDs: one inverter and one battery, in either order.', 'linker-commerce' ),
					),
				),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'verdict'    => array(
						'type' => 'string',
						'enum' => array( 'released', 'released_with_accessory', 'not_released', 'unknown' ),
					),
					'conditions' => array(
						'type'  => 'array',
						'items' => array(
							'type'                 => 'object',
							'properties'           => array(
								'en' => array( 'type' => 'string' ),
								'de' => array( 'type' => 'string' ),
							),
							'required'             => array( 'en', 'de' ),
							'additionalProperties' => false,
						),
					),
					'documents'  => array(
						'type'  => 'array',
						'items' => $document,
					),
				),
				'required'             => array( 'verdict', 'conditions', 'documents' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may read a documented pairing.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * The verdict for one inverter and one battery.
	 *
	 * @param array<string, mixed>|object $input inverter_id+battery_id or product_ids.
	 * @return array{verdict: string, conditions: list<array{en: string, de: string}>, documents: list<array{url: string, page?: int}>}
	 */
	public function execute( $input = array() ): array {
		$this->publication_snapshot = $this->publication->manifest();
		$pair                       = $this->pair( (array) $input );
		if ( null === $pair ) {
			return $this->unknown();
		}
		$dependencies = $this->publication->dependencies( array_column( $this->publication_snapshot['products'], 'product_id' ), $this->publication_snapshot );
		$answer       = $this->publication->pairing( $pair[0], $pair[1], $this->publication_snapshot );
		if ( null === $answer ) {
			return $this->unknown();
		}

		if ( ! $this->publication->unchanged( $dependencies ) ) {
			return $this->unknown();
		}
		return array(
			'verdict'    => $answer['verdict'],
			'conditions' => $answer['conditions'],
			'documents'  => $answer['documents'],
		);
	}

	/**
	 * Inverter and battery IDs from either input shape.
	 *
	 * @param array<string, mixed> $input Input.
	 * @return array{0: int, 1: int}|null
	 */
	private function pair( array $input ): ?array {
		if ( isset( $input['inverter_id'], $input['battery_id'] ) ) {
			$inverter = (int) $input['inverter_id'];
			$battery  = (int) $input['battery_id'];
			return $inverter > 0 && $battery > 0 ? array( $inverter, $battery ) : null;
		}
		$ids = array_values( array_map( 'intval', (array) ( $input['product_ids'] ?? array() ) ) );
		if ( 2 !== count( $ids ) || $ids[0] < 1 || $ids[1] < 1 ) {
			return null;
		}
		if ( count( $this->publication->published( $ids, $this->publication_snapshot ) ) !== 2 ) {
			return null;
		}
		$first  = $this->publication->facts( $ids[0], $this->publication_snapshot )->device_class;
		$second = $this->publication->facts( $ids[1], $this->publication_snapshot )->device_class;
		if ( $this->is_inverter( $first ) && $this->is_battery( $second ) ) {
			return array( $ids[0], $ids[1] );
		}
		if ( $this->is_battery( $first ) && $this->is_inverter( $second ) ) {
			return array( $ids[1], $ids[0] );
		}

		return null;
	}

	/**
	 * Whether a device class is an inverter side of a pairing.
	 *
	 * @param value-of<SelectionFacts::DEVICE_CLASSES>|'unknown' $device_class Device class.
	 */
	private function is_inverter( string $device_class ): bool {
		return in_array( $device_class, self::INVERTER_CLASSES, true );
	}

	/**
	 * Whether a device class is a battery side of a pairing.
	 *
	 * @param value-of<SelectionFacts::DEVICE_CLASSES>|'unknown' $device_class Device class.
	 */
	private function is_battery( string $device_class ): bool {
		return in_array( $device_class, self::BATTERY_CLASSES, true );
	}

	/**
	 * No documented release.
	 *
	 * @return array{verdict: 'unknown', conditions: array{}, documents: array{}}
	 */
	private function unknown(): array {
		return array(
			'verdict'    => SelectionFactSet::UNKNOWN,
			'conditions' => array(),
			'documents'  => array(),
		);
	}
}
