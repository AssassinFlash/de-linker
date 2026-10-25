<?php
/**
 * Ability linker/compare-products.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Comparison;

/**
 * A comparison table of two to four published products. Battery energy and
 * inverter output are different rows, never one mixed "power" row
 * (docs/specs/13-genie.md).
 *
 * The table itself is built by Products\Comparison, which the standalone
 * comparison page (/compare-products/) reads as well: this ability is the
 * table as Genie sees it, the page is the table as a visitor sees it, and
 * neither keeps a second derivation of it (docs/specs/19-tool-pages.md).
 */
final class CompareProducts {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/compare-products';

	/**
	 * The comparison assembly.
	 *
	 * @var Comparison
	 */
	private readonly Comparison $comparison;
	/**
	 * Current operation snapshot.
	 *
	 * @var array<string,mixed>
	 */
	private array $publication_snapshot = array();

	/**
	 * Sets up the ability.
	 *
	 * @param Comparison|null $comparison Assembly override (tests).
	 * @param PublicationData $publication Current authority reader.
	 */
	public function __construct( ?Comparison $comparison = null, private readonly PublicationData $publication = new PublicationData() ) {
		$this->comparison = $comparison ?? new Comparison( facts_reader: fn( int $id ) => $this->publication->facts( $id, $this->publication_snapshot ), publication: $this->publication );
	}

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
		$input                      = (array) $input;
		$lang                       = ProductText::lang( $input['lang'] ?? null );
		$ids                        = array_values( array_unique( array_map( 'intval', (array) ( $input['product_ids'] ?? array() ) ) ) );
		$this->publication_snapshot = $this->publication->manifest();
		if ( $this->publication->published( $ids, $this->publication_snapshot, $lang ) !== $ids ) {
			return array(
				'products' => array(),
				'rows'     => array(),
			);
		}
		$dependencies = $this->publication->dependencies( $ids, $this->publication_snapshot );
		$comparison   = $this->comparison->of( $ids, $lang );
		$products     = array();
		foreach ( $comparison['products'] as $column ) {
			$products[] = array(
				'product_id' => $column['product_id'],
				'title'      => $column['title'],
				'url'        => $column['url'],
				'facts'      => $column['facts'],
			);
		}

		if ( ! $this->publication->unchanged( $dependencies ) ) {
			return array(
				'products' => array(),
				'rows'     => array(),
			);
		}
		return array(
			'products' => $products,
			'rows'     => array_map(
				static fn( array $row ): array => array(
					'field'  => $row['field'],
					'label'  => $row['label'],
					'values' => (object) $row['values'],
				),
				$comparison['rows']
			),
		);
	}
}
