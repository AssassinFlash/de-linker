<?php
/**
 * Reading the #10 MariaDB document index (position A).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

/**
 * Dense ranking over wp_{prefix}genie_chunks.embedding, with FULLTEXT as the
 * fallback when this host has no query encoder (docs/specs/10-knowledge-index.md,
 * bake-off revision: no RRF). Product IDs first narrow to those documents'
 * models; an empty scoped ranking falls back to the whole library.
 */
final class KnowledgeIndex {

	/**
	 * How many chunks a ranking reads (services/genie/src/linker_genie/retrieval.py CANDIDATES).
	 */
	public const CANDIDATES = 30;

	/**
	 * Default hits (spec search_documents k=8).
	 */
	public const DEFAULT_K = 8;

	/**
	 * Sets up the index reader.
	 *
	 * @param \wpdb                                $db    WordPress database.
	 * @param callable(string):(?list<float>)|null $embed Encodes a query, or null to skip vectors.
	 */
	public function __construct(
		private readonly \wpdb $db,
		private readonly mixed $embed = null
	) {}

	/**
	 * Table name `{$wpdb->prefix}genie_{$suffix}`.
	 *
	 * @param string $suffix meta|documents|document_models|products|chunks.
	 */
	public function table( string $suffix ): string {
		return $this->db->prefix . 'genie_' . $suffix;
	}

	/**
	 * Search: product-scoped dense, then scoped FULLTEXT, then the whole library.
	 *
	 * @param string    $query       Search text.
	 * @param 'en'|'de' $lang       Title language.
	 * @param int[]     $product_ids Optional product filter.
	 * @param int       $k           Hit cap.
	 * @return list<array{chunk_id: string, doc_url: string, title: string, page: int, section: string, text: string, score: float}>
	 */
	public function search( string $query, string $lang, array $product_ids = array(), int $k = self::DEFAULT_K ): array {
		$query = trim( $query );
		if ( '' === $query || $k < 1 ) {
			return array();
		}
		$vector = is_callable( $this->embed ) ? ( $this->embed )( $query ) : null;
		$scopes = array() !== $product_ids ? array( $product_ids, array() ) : array( array() );
		foreach ( $scopes as $scope ) {
			$rowids = is_array( $vector ) && array() !== $vector
				? $this->vector_ranking( $vector, $scope )
				: array();
			if ( array() === $rowids ) {
				$rowids = $this->keyword_ranking( $query, $scope );
			}
			if ( array() !== $rowids ) {
				return $this->hits( array_slice( $rowids, 0, $k ), $lang );
			}
		}

		return array();
	}

	/**
	 * Chunk rowids nearest to the query vector (cosine). Empty when the table
	 * has no VECTOR column or the scope is empty.
	 *
	 * @param float[] $vector Query vector.
	 * @param int[]   $product_ids Product filter; empty is the whole library.
	 * @return int[]
	 */
	public function vector_ranking( array $vector, array $product_ids ): array {
		$chunks  = $this->table( 'chunks' );
		$literal = $this->vector_literal( $vector );
		$sql     = "SELECT DISTINCT c.rowid FROM `{$chunks}` c"
			. $this->scope_join( $product_ids )
			. " WHERE c.embedding IS NOT NULL {$this->scope_where( $product_ids )}"
				. " ORDER BY VEC_DISTANCE_COSINE(c.embedding, {$literal}) ASC LIMIT %d";
			// Table names are prefix + a fixed suffix; the limit is an integer placeholder.
			$prepared = $this->db->prepare( $sql, self::CANDIDATES ); // @phpstan-ignore argument.type (table name is interpolated from a fixed suffix)

		return $this->rowids( is_string( $prepared ) ? $this->db->get_col( $prepared ) : array() );
	}

	/**
	 * Chunk rowids by FULLTEXT over header and text.
	 *
	 * @param string $query       Search text.
	 * @param int[]  $product_ids Product filter; empty is the whole library.
	 * @return int[]
	 */
	public function keyword_ranking( string $query, array $product_ids ): array {
		$against = $this->boolean_query( $query );
		if ( '' === $against ) {
			return array();
		}
		$chunks       = $this->table( 'chunks' );
		$sql          = "SELECT DISTINCT c.rowid FROM `{$chunks}` c"
			. $this->scope_join( $product_ids )
			. ' WHERE MATCH(c.header, c.text) AGAINST (%s IN BOOLEAN MODE)'
			. $this->scope_where( $product_ids )
				. ' ORDER BY MATCH(c.header, c.text) AGAINST (%s IN BOOLEAN MODE) DESC LIMIT %d';
			$prepared = $this->db->prepare( $sql, $against, $against, self::CANDIDATES ); // @phpstan-ignore argument.type (table name is interpolated from a fixed suffix)

		return $this->rowids( is_string( $prepared ) ? $this->db->get_col( $prepared ) : array() );
	}

	/**
	 * Hits for ranked rowids, in that order.
	 *
	 * @param int[]     $rowids Ranked chunk rowids.
	 * @param 'en'|'de' $lang   Title language.
	 * @return list<array{chunk_id: string, doc_url: string, title: string, page: int, section: string, text: string, score: float}>
	 */
	public function hits( array $rowids, string $lang ): array {
		if ( array() === $rowids ) {
			return array();
		}
		$chunks       = $this->table( 'chunks' );
		$documents    = $this->table( 'documents' );
		$in           = implode( ',', array_map( 'intval', $rowids ) );
		$title_col    = 'de' === $lang ? 'd.title_de' : 'd.title_en';
		$sql          = "SELECT c.rowid, c.id, d.url, {$title_col} AS title, d.title_en, c.page, c.section, c.text"
			. " FROM `{$chunks}` c JOIN `{$documents}` d ON d.sha256 = c.doc_sha256"
			. " WHERE c.rowid IN ({$in})";
			$rows     = $this->db->get_results( $sql, ARRAY_A );
			$by_rowid = array();
		foreach ( $rows as $row ) {
			$by_rowid[ (int) $row['rowid'] ] = $row;
		}
		$hits = array();
		foreach ( $rowids as $position => $rowid ) {
			$row = $by_rowid[ $rowid ] ?? null;
			if ( ! is_array( $row ) ) {
				continue;
			}
			$title = (string) $row['title'];
			if ( '' === $title ) {
				$title = (string) $row['title_en'];
			}
			$hits[] = array(
				'chunk_id' => (string) $row['id'],
				'doc_url'  => (string) $row['url'],
				'title'    => $title,
				'page'     => (int) $row['page'],
				'section'  => (string) $row['section'],
				'text'     => (string) $row['text'],
				'score'    => (float) ( - $position ),
			);
		}

		return $hits;
	}

	/**
	 * JOIN + WHERE fragment that keeps chunks whose document is tagged with one
	 * of the products' models. Empty $product_ids adds nothing. A product list
	 * that matches no document still filters to nothing (the caller then retries
	 * with an empty list = the whole library).
	 *
	 * @param int[] $product_ids Product filter.
	 */
	private function scope_join( array $product_ids ): string {
		if ( array() === $product_ids ) {
			return '';
		}
		$models   = $this->table( 'document_models' );
		$products = $this->table( 'products' );

		return " INNER JOIN `{$models}` dm ON dm.doc_sha256 = c.doc_sha256 INNER JOIN `{$products}` p ON p.model = dm.model";
	}

	/**
	 * AND p.product_id IN (...) when a product filter is on.
	 *
	 * @param int[] $product_ids Product filter.
	 */
	private function scope_where( array $product_ids ): string {
		if ( array() === $product_ids ) {
			return '';
		}
		$in = implode( ',', array_map( 'intval', $product_ids ) );

		return " AND p.product_id IN ({$in})";
	}

	/**
	 * `VEC_FromText('[…]')` of a float vector. Values are formatted so the
	 * literal cannot break out of the function call.
	 *
	 * @param float[] $vector Query vector.
	 */
	private function vector_literal( array $vector ): string {
		$parts = array();
		foreach ( $vector as $value ) {
			$parts[] = sprintf( '%.7g', $value );
		}

		return "VEC_FromText('[" . implode( ',', $parts ) . "]')";
	}

	/**
	 * BOOLEAN MODE query: each term as a quoted phrase, the way FTS5 quoting
	 * keeps a model code together (retrieval.py fts_query).
	 *
	 * @param string $query Search text.
	 */
	public function boolean_query( string $query ): string {
		if ( false === preg_match_all( '/[A-Za-z0-9](?:[A-Za-z0-9.\/-]*[A-Za-z0-9])?/', $query, $matches ) || array() === $matches[0] ) {
			return '';
		}
		$terms = array();
		foreach ( $matches[0] as $term ) {
			$term = strtolower( $term );
			if ( ! in_array( $term, $terms, true ) ) {
				$terms[] = $term;
			}
		}
		$quoted = array();
		foreach ( $terms as $term ) {
			$quoted[] = '"' . str_replace( '"', '', $term ) . '"';
		}

		return implode( ' ', $quoted );
	}

	/**
	 * Rowids as positive ints, dropping empties.
	 *
	 * @param mixed $rows get_col() result.
	 * @return int[]
	 */
	private function rowids( mixed $rows ): array {
		$out = array();
		foreach ( is_array( $rows ) ? $rows : array() as $row ) {
			$id = (int) $row;
			if ( $id > 0 ) {
				$out[] = $id;
			}
		}

		return $out;
	}
}
