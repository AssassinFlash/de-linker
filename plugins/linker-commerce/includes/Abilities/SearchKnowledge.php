<?php
/**
 * Ability linker/search-knowledge.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Document search over the #10 MariaDB index (position A): dense ranking when
 * a query encoder is available, FULLTEXT otherwise. The model may only cite
 * the returned chunk IDs (docs/specs/13-genie.md, docs/specs/10-knowledge-index.md).
 */
final class SearchKnowledge {

	/**
	 * Ability name.
	 */
	public const NAME = 'linker/search-knowledge';

	/**
	 * Sets up the ability.
	 *
	 * @param KnowledgeIndex|null $index Index reader; omitted, built from $wpdb on execute.
	 */
	public function __construct( private readonly ?KnowledgeIndex $index = null ) {}

	/**
	 * Arguments for wp_register_ability(), apart from the category.
	 *
	 * @return array<string, mixed>
	 */
	public function args(): array {
		$hit = array(
			'type'                 => 'object',
			'properties'           => array(
				'chunk_id' => array(
					'type'        => 'string',
					'description' => __( 'Chunk ID the answer may cite.', 'linker-commerce' ),
				),
				'doc_url'  => array(
					'type'        => 'string',
					'description' => __( 'Hosted document URL.', 'linker-commerce' ),
				),
				'title'    => array(
					'type'        => 'string',
					'description' => __( 'Document title in the requested language.', 'linker-commerce' ),
				),
				'page'     => array(
					'type'        => 'integer',
					'description' => __( '1-based page of the chunk.', 'linker-commerce' ),
				),
				'section'  => array( 'type' => 'string' ),
				'text'     => array( 'type' => 'string' ),
				'score'    => array( 'type' => 'number' ),
			),
			'required'             => array( 'chunk_id', 'doc_url', 'title', 'page', 'section', 'text', 'score' ),
			'additionalProperties' => false,
		);

		return array(
			'label'               => __( 'Search hosted documents', 'linker-commerce' ),
			'description'         => __( 'Returns chunks from the hosted PDF index. Cite only the returned chunk IDs.', 'linker-commerce' ),
			'input_schema'        => array(
				'type'                 => 'object',
				'properties'           => array(
					'query'       => array(
						'type'      => 'string',
						'minLength' => 1,
					),
					'lang'        => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
					'product_ids' => array(
						'type'  => 'array',
						'items' => array(
							'type'    => 'integer',
							'minimum' => 1,
						),
					),
				),
				'required'             => array( 'query', 'lang' ),
				'additionalProperties' => false,
			),
			'output_schema'       => array(
				'type'                 => 'object',
				'properties'           => array(
					'hits' => array(
						'type'  => 'array',
						'items' => $hit,
					),
				),
				'required'             => array( 'hits' ),
				'additionalProperties' => false,
			),
			'execute_callback'    => array( $this, 'execute' ),
			'permission_callback' => array( $this, 'can_execute' ),
			'meta'                => RestMeta::readonly(),
		);
	}

	/**
	 * Anyone may search hosted documents.
	 */
	public function can_execute(): bool {
		return true;
	}

	/**
	 * Chunks for the query, product-scoped then whole library.
	 *
	 * @param array<string, mixed>|object $input query, lang, optional product_ids.
	 * @return array{hits: list<array<string, mixed>>}
	 */
	public function execute( $input = array() ): array {
		$input = (array) $input;
		$query = is_string( $input['query'] ?? null ) ? trim( $input['query'] ) : '';
		$lang  = ProductText::lang( $input['lang'] ?? null );
		$ids   = array_values( array_unique( array_filter( array_map( 'intval', (array) ( $input['product_ids'] ?? array() ) ) ) ) );

		return array( 'hits' => $this->index()->search( $query, $lang, $ids ) );
	}

	/**
	 * The index reader, built against $wpdb on first use.
	 */
	private function index(): KnowledgeIndex {
		if ( $this->index instanceof KnowledgeIndex ) {
			return $this->index;
		}
		global $wpdb;
		$embedder = new QueryEmbedding();

		return new KnowledgeIndex( $wpdb, array( $embedder, 'vector' ) );
	}
}
