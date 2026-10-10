<?php
/**
 * Ability linker/get-product.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Catalog\EngineeringData;
use Linker\Commerce\Catalog\SelectionFacts;
use WC_Product;

/**
 * One published product: selection facts, cited figures, attributes, documents
 * and commerce state. FAQ answers are generated in #15 and live on product meta
 * `_linker_faq` when present.
 */
final class GetProduct {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/get-product';

	/**
	 * Product meta of the FAQ list written by #15.
	 */
	public const FAQ_META = '_linker_faq';

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		return array(
			'label'               => __( 'Get a product', 'linker-commerce' ),
			'description'         => __( 'Returns one published product: facts, figures, attributes, documents and FAQ.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'product_id' => array(
						'type'        => 'integer',
						'minimum'     => 1,
						'description' => __( 'Product ID.', 'linker-commerce' ),
					),
					'lang'       => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
				),
				'required'             => array( 'product_id' ),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'product_id' => array( 'type' => 'integer' ),
					'title'      => array( 'type' => 'string' ),
					'url'        => array( 'type' => 'string' ),
					'sku'        => array( 'type' => 'string' ),
					'model'      => array( 'type' => array( 'string', 'null' ) ),
					'brand'      => array( 'type' => array( 'string', 'null' ) ),
					'series'     => array( 'type' => array( 'string', 'null' ) ),
					'facts'      => array(
						'description' => __( 'Selection facts of the product.', 'linker-commerce' ),
						'type'        => 'object',
					),
					'figures'    => array(
						'description' => __( 'Cited figure entries as stored.', 'linker-commerce' ),
						'type'        => 'object',
					),
					'attributes' => array(
						'type'                 => 'object',
						'additionalProperties' => array(
							'type'  => 'array',
							'items' => array( 'type' => 'string' ),
						),
					),
					'documents'  => array(
						'type'  => 'array',
						'items' => array( 'type' => 'object' ),
					),
					'faq'        => array(
						'type'  => 'array',
						'items' => array(
							'type'                 => 'object',
							'properties'           => array(
								'question' => array( 'type' => 'string' ),
								'answer'   => array( 'type' => 'string' ),
							),
							'required'             => array( 'question', 'answer' ),
							'additionalProperties' => false,
						),
					),
					'commerce'   => ProductCommerce::schema(),
				),
				'required'             => array( 'product_id', 'title', 'url', 'sku', 'model', 'brand', 'series', 'facts', 'figures', 'attributes', 'documents', 'faq', 'commerce' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may read a published product.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * One published product, or an empty record when it is not published.
	 *
	 * @param array<string, mixed>|object $input product_id and optional lang.
	 * @return array<string, mixed>
	 */
	public function execute( $input = array() ): array {
		$input = (array) $input;
		$id    = (int) ( $input['product_id'] ?? 0 );
		$lang  = CatalogText::lang( $input['lang'] ?? null );
		if ( $id < 1 || 'product' !== get_post_type( $id ) || 'publish' !== get_post_status( $id ) ) {
			return $this->empty( $id, $lang );
		}
		$product = wc_get_product( $id );
		$facts   = SelectionFacts::for_product( $id );

		return array(
			'product_id' => $id,
			'title'      => CatalogText::title( $id, $lang ),
			'url'        => CatalogText::url( $id ),
			'sku'        => $product instanceof WC_Product ? (string) $product->get_sku() : '',
			'model'      => CatalogText::term_name( $id, 'pa_model' ),
			'brand'      => CatalogText::term_name( $id, 'pa_brand' ),
			'series'     => CatalogText::term_name( $id, 'pa_series' ),
			'facts'      => $facts->to_array(),
			'figures'    => (object) $this->figures( $id ),
			'attributes' => (object) $this->attributes( $id ),
			'documents'  => $this->documents( $id ),
			'faq'        => $this->faq( $id, $lang ),
			'commerce'   => ProductCommerce::of( $id, $product instanceof WC_Product ? $product : null ),
		);
	}

	/**
	 * Cited figures as stored (the same rule as the engineering feed).
	 *
	 * @param int $product_id Product ID.
	 * @return array<string, mixed>
	 */
	private function figures( int $product_id ): array {
		$figures = get_post_meta( $product_id, SelectionFacts::FIGURES_META_KEY, true );
		if ( is_string( $figures ) ) {
			$figures = json_decode( $figures, true );
		}

		return is_array( $figures ) ? $figures : array();
	}

	/**
	 * Visible product attributes as slug lists, keyed by taxonomy.
	 *
	 * @param int $product_id Product ID.
	 * @return array<string, list<string>>
	 */
	private function attributes( int $product_id ): array {
		$out = array();
		foreach ( array( 'pa_application', 'pa_phase', 'pa_brand', 'pa_model', 'pa_series' ) as $taxonomy ) {
			$slugs = CatalogText::term_slugs( $product_id, $taxonomy );
			if ( array() !== $slugs ) {
				$out[ $taxonomy ] = $slugs;
			}
		}

		return $out;
	}

	/**
	 * Hosted documents of the product.
	 *
	 * @param int $product_id Product ID.
	 * @return list<array<string, mixed>>
	 */
	private function documents( int $product_id ): array {
		$documents = get_post_meta( $product_id, EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $documents ) ) {
			$documents = json_decode( $documents, true );
		}
		if ( is_array( $documents ) && array() !== $documents ) {
			return array_values( $documents );
		}
		$fallback = array();
		foreach ( array(
			'_delinker_datasheet_url' => 'datasheet',
			'_delinker_manual_url'    => 'manual',
		) as $key => $type ) {
			$url = get_post_meta( $product_id, $key, true );
			if ( is_string( $url ) && '' !== $url ) {
				$fallback[] = array(
					'url'  => $url,
					'type' => $type,
				);
			}
		}

		return $fallback;
	}

	/**
	 * FAQ entries in the requested language.
	 *
	 * @param int       $product_id Product ID.
	 * @param 'en'|'de' $lang    Language.
	 * @return list<array{question: string, answer: string}>
	 */
	private function faq( int $product_id, string $lang ): array {
		$stored = get_post_meta( $product_id, self::FAQ_META, true );
		if ( is_string( $stored ) ) {
			$stored = json_decode( $stored, true );
		}
		if ( ! is_array( $stored ) ) {
			return array();
		}
		$out = array();
		foreach ( $stored as $entry ) {
			if ( ! is_array( $entry ) ) {
				continue;
			}
			$question = $entry[ 'question_' . $lang ] ?? $entry['question'] ?? $entry['question_en'] ?? null;
			$answer   = $entry[ 'answer_' . $lang ] ?? $entry['answer'] ?? $entry['answer_en'] ?? null;
			if ( is_string( $question ) && is_string( $answer ) && '' !== $question && '' !== $answer ) {
				$out[] = array(
					'question' => $question,
					'answer'   => $answer,
				);
			}
		}

		return $out;
	}

	/**
	 * An empty record for a missing product: the schema still holds.
	 *
	 * @param int       $id   Requested ID.
	 * @param 'en'|'de' $lang Language.
	 * @return array<string, mixed>
	 */
	private function empty( int $id, string $lang ): array {
		unset( $lang );

		return array(
			'product_id' => $id,
			'title'      => '',
			'url'        => '',
			'sku'        => '',
			'model'      => null,
			'brand'      => null,
			'series'     => null,
			'facts'      => (object) array(),
			'figures'    => (object) array(),
			'attributes' => (object) array(),
			'documents'  => array(),
			'faq'        => array(),
			'commerce'   => ProductCommerce::hidden(),
		);
	}
}
