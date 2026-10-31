<?php
/**
 * WooCommerce is the sole authority for current product/document permission.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\PreparationJobs;
use Linker\Commerce\Products\Publication\EvidenceBindings;

/** A current read; no TTL, index or preparation acknowledgement grants access. */
final class Publication {
	/** Exact whitespace-normalized Unicode-boundary matching contract. */
	public const IDENTITY_PROTOCOL = 'native-model-identification-v1';

	/**
	 * Opaque identity of all native model permissions, including unavailable labels.
	 *
	 * @param array<string,array{status:'published',product_id:int}|array{status:'unavailable'}> $known Fresh native model map.
	 */
	public static function model_identity_revision( array $known ): string {
		return self::revision(
			array(
				'protocol' => self::IDENTITY_PROTOCOL,
				'models'   => $known,
			)
		);
	}

	/**
	 * Stable canonical JSON hash; generated times and readiness stay outside it.
	 *
	 * @param mixed $value Content to version.
	 */
	public static function revision( mixed $value ): string {
		return hash( 'sha256', (string) wp_json_encode( self::ordered( $value ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
	}

	/**
	 * Normalize object keys recursively.
	 *
	 * @param mixed $value Content to normalize.
	 * @return mixed
	 */
	private static function ordered( mixed $value ): mixed {
		if ( is_object( $value ) ) {
			$value = get_object_vars( $value );
		}
		if ( ! is_array( $value ) ) {
			return $value;
		}
		if ( ! array_is_list( $value ) ) {
			ksort( $value );
		}
		return array_map( array( self::class, 'ordered' ), $value );
	}

	/**
	 * Canonical identity uses the existing language layer.
	 *
	 * @param int $id Product ID.
	 */
	public static function canonical_id( int $id ): int {
		if ( ! function_exists( 'has_filter' ) || ! has_filter( 'linker_commerce_facts_product_id' ) ) {
			return $id;
		}
		/**
		 * Filter the canonical product identity through the language companion.
		 *
		 * @since 0.1.0
		 */
		return (int) apply_filters( 'linker_commerce_facts_product_id', $id );
	}

	/**
	 * Both locale and source must currently be published.
	 *
	 * @param int $id Locale product ID.
	 */
	public static function is_published( int $id ): bool {
		self::refresh_runtime();
		return self::published_in_current_read( $id );
	}

	/**
	 * One fresh native permission read for a batch, without document bytes.
	 *
	 * A candidate reader executes after refresh, so native category/visibility
	 * queries and options belong to the same fresh read as product permission.
	 *
	 * @param int[]|callable():int[] $ids Locale IDs or their native candidate reader.
	 * @return list<int>
	 */
	public static function published_ids( array|callable $ids ): array {
		self::refresh_runtime();
		$ids = is_callable( $ids ) ? $ids() : $ids;
		return array_values( array_filter( $ids, array( self::class, 'published_in_current_read' ) ) );
	}

	/**
	 * Read within one explicit freshly opened authority assembly.
	 *
	 * The outer manifest already refreshed runtime copies; repeating that flush
	 * per locale would discard every post/term read made by this same assembly.
	 *
	 * @param int $id Locale product ID.
	 */
	private static function published_in_current_read( int $id ): bool {
		$canonical = self::canonical_id( $id );
		return $id > 0 && 'product' === get_post_type( $id ) && 'publish' === get_post_status( $id ) && 'product' === get_post_type( $canonical ) && 'publish' === get_post_status( $canonical );
	}

	/**
	 * Drop only request-local object-cache copies before a new authority read.
	 *
	 * @throws \RuntimeException When a cache drop-in cannot refresh runtime copies.
	 */
	private static function refresh_runtime(): void {
		if ( ! wp_cache_supports( 'flush_runtime' ) || ! wp_cache_flush_runtime() ) {
			throw new \RuntimeException( 'Current publication requires request-local cache refresh support.' );
		}
	}

	/**
	 * Current model-label statuses, without document bytes or technical facts.
	 *
	 * This is an internal projection of the same native Woo source. Callers must
	 * return only labels already supplied by their client, never this whole map.
	 *
	 * @return array<string,array{status:'published',product_id:int}|array{status:'unavailable'}>
	 * @throws \RuntimeException When fresh native permissions cannot be read.
	 * @phpstan-impure
	 */
	public static function model_statuses(): array {
		self::refresh_runtime();
		return self::model_statuses_in_current_read();
	}

	/**
	 * The enclosing manifest/identity operation already owns one fresh read.
	 *
	 * @throws \RuntimeException When native model terms cannot be read.
	 * @return array<string,array{status:'published',product_id:int}|array{status:'unavailable'}>
	 */
	private static function model_statuses_in_current_read(): array {
		$ids = get_posts(
			array(
				'post_type'                   => 'product',
				'post_status'                 => array( 'publish', 'draft', 'pending', 'private', 'future', 'trash' ),
				'fields'                      => 'ids',
				'posts_per_page'              => -1,
				'suppress_filters'            => true,
				'lang'                        => '',
				'linker_publication_internal' => true,
				'cache_results'               => false,
			)
		);
		$ids = array_map( 'intval', $ids );
		if ( array() === $ids ) {
			return array();
		}
		// This fresh authority read batches native posts/meta and model relationships.
		_prime_post_caches( $ids, false, true );
		$terms = wp_get_object_terms(
			$ids,
			'pa_model',
			array(
				'fields' => 'all_with_object_id',
				'lang'   => '',
			)
		);
		if ( is_wp_error( $terms ) ) {
			if ( 'invalid_taxonomy' !== $terms->get_error_code() || taxonomy_exists( 'pa_model' ) ) {
				throw new \RuntimeException( 'Current model identity terms could not be read.' );
			}
			// Woo products may exist before the optional model attribute is registered.
			$terms = array();
		}
		$models_by_id = array();
		foreach ( $terms as $term ) {
			// all_with_object_id adds the native relationship to the term's fields.
			$relationship                                       = get_object_vars( $term );
			$models_by_id[ (int) $relationship['object_id'] ][] = $term->name;
		}
		$known = array();
		foreach ( $ids as $id ) {
			$published = self::published_in_current_read( $id ) && ! EngineeringReference::is_reference( $id );
			foreach ( $models_by_id[ $id ] ?? array() as $model ) {
				$key = strtolower( trim( $model ) );
				if ( ! isset( $known[ $key ] ) || $published ) {
					$known[ $key ] = $published
						? array(
							'status'     => 'published',
							'product_id' => self::canonical_id( $id ),
						)
						: array( 'status' => 'unavailable' );
				}
			}
		}
		return $known;
	}

	/**
	 * Current public manifest, including an empty set.
	 *
	 * @return array<string,mixed>
	 */
	public static function manifest(): array {
		self::refresh_runtime();
		DocumentFiles::begin_read();
		try {
			return self::assemble();
		} finally {
			DocumentFiles::end_read();
		}
	}

	/**
	 * Fresh library rows, with byte identity only for potential FAQ sources.
	 *
	 * This projection has no manifest/product/document revisions or readiness.
	 * Uncited rows expose listing metadata, never a claimed content hash; the
	 * original download gate independently resolves and authorizes actual bytes.
	 *
	 * @return array<string,mixed>
	 */
	public static function library_read(): array {
		self::refresh_runtime();
		DocumentFiles::begin_read();
		try {
			return self::assemble( true );
		} finally {
			DocumentFiles::end_read();
		}
	}

	/**
	 * Current product documents, retaining the shared register's first-row rules.
	 *
	 * Other products still determine shared metadata and declared aliases, but
	 * their unrelated files and FAQ citations do not need to be inspected.
	 *
	 * @param int    $id Locale product ID.
	 * @param string $legacy_url Legacy selection URL needing declared-alias byte identity.
	 * @return array<string,mixed>
	 */
	public static function product_library_read( int $id, string $legacy_url = '' ): array {
		self::refresh_runtime();
		DocumentFiles::begin_read();
		try {
			if ( ! self::published_in_current_read( $id ) ) {
				return array(
					'products'  => array(),
					'documents' => array(),
				);
			}
			return self::assemble( true, self::canonical_id( $id ), $legacy_url );
		} finally {
			DocumentFiles::end_read();
		}
	}

	/**
	 * Authorize one original PDF without hashing unrelated technical documents.
	 *
	 * @param array<string,string> $file The caller's resolved hosted PDF.
	 */
	public static function allows_document( array $file ): bool {
		self::refresh_runtime();
		DocumentFiles::begin_read();
		try {
			return self::document_in_current_read( $file );
		} finally {
			DocumentFiles::end_read();
		}
	}

	/**
	 * Preserve manifest association order and alias permission for this PDF.
	 *
	 * @param array<string,string> $file The caller's resolved hosted PDF.
	 */
	private static function document_in_current_read( array $file ): bool {
		$target     = DocumentFiles::id( $file['url'] );
		$rows       = array();
		$candidates = array();
		$sources    = array();
		foreach ( self::candidate_ids() as $locale_id ) {
			if ( ! self::published_in_current_read( $locale_id ) ) {
				continue;
			}
			$id = self::canonical_id( $locale_id );
			if ( isset( $sources[ $id ] ) ) {
				continue;
			}
			$sources[ $id ] = true;
			foreach ( self::document_rows( $id ) as $row ) {
				if ( false === ( $row['active'] ?? true ) || '0' === (string) ( $row['active'] ?? '1' ) ) {
					continue;
				}
				$identity = DocumentFiles::id( (string) ( $row['url'] ?? '' ) );
				$rows[]   = array( $identity, $row );
				if ( $identity === $target ) {
					$candidates[ $identity ] = true;
				}
				foreach ( (array) ( $row['aliases'] ?? array() ) as $url ) {
					if ( is_string( $url ) && DocumentFiles::id( $url ) === $target ) {
						$candidates[ $identity ] = true;
					}
				}
			}
		}
		$seen        = array();
		$permissions = array();
		foreach ( $rows as [ $identity, $row ] ) {
			if ( ! isset( $candidates[ $identity ] ) || isset( $seen[ $identity ] ) ) {
				continue;
			}
			$primary = DocumentFiles::resolve( (string) ( $row['url'] ?? '' ) );
			if ( null === $primary || ! self::attachment_allows( $primary['url'], $permissions ) ) {
				continue;
			}
			$seen[ $identity ] = true;
			if ( $primary['url'] === $file['url'] && $primary['blob_sha256'] === $file['blob_sha256'] ) {
				return true;
			}
			foreach ( (array) ( $row['aliases'] ?? array() ) as $url ) {
				if ( ! is_string( $url ) || DocumentFiles::id( $url ) !== $target ) {
					continue;
				}
				$alias = DocumentFiles::resolve( $url );
				if ( null !== $alias && $alias['url'] === $file['url'] && $alias['blob_sha256'] === $primary['blob_sha256'] && $alias['blob_sha256'] === $file['blob_sha256'] && self::attachment_allows( $alias['url'], $permissions ) ) {
					return true;
				}
			}
		}
		return false;
	}

	/**
	 * Native candidate order shared by the full manifest and original PDF gate.
	 *
	 * @return list<int>
	 */
	private static function candidate_ids(): array {
		return array_values(
			array_map(
				'intval',
				get_posts(
					array(
						'post_type'                   => 'product',
						'post_status'                 => 'publish',
						'fields'                      => 'ids',
						'posts_per_page'              => -1,
						'orderby'                     => 'ID',
						'order'                       => 'ASC',
						'suppress_filters'            => true,
						'lang'                        => '',
						'linker_publication_internal' => true,
						'cache_results'               => false,
					)
				)
			)
		);
	}

	/**
	 * Assemble this authority read, hashing each real file at most once.
	 *
	 * @param bool     $library Only library metadata and current cited FAQ bytes.
	 * @param int|null $product_id Restrict document IO to this current source.
	 * @param string   $legacy_url Inspect aliases needed to select a legacy document URL.
	 * @return array<string,mixed>
	 */
	private static function assemble( bool $library = false, ?int $product_id = null, string $legacy_url = '' ): array {
		$ids = self::candidate_ids();
		// WordPress batches the same native posts, metadata and terms after this read's runtime refresh.
		_prime_post_caches( $ids, true, true );
		$citation_ids           = $library ? self::faq_document_ids( null === $product_id ? $ids : array( $product_id ) ) : array();
		$document_ids           = null === $product_id ? null : self::product_document_ids( $product_id );
		$products               = array();
		$documents              = array();
		$attachment_permissions = array();
		if ( $library && '' !== $legacy_url ) {
			$citation_ids[ DocumentFiles::id( $legacy_url ) ] = true;
		}
		foreach ( $ids as $locale_id ) {
			$locale_id = (int) $locale_id;
			if ( ! self::published_in_current_read( $locale_id ) ) {
				continue;
			}
			$id = self::canonical_id( $locale_id );
			if ( ! isset( $products[ $id ] ) ) {
				$record = $library ? array(
					'product_id'           => $id,
					'locale_product_ids'   => array(),
					'published_locale_ids' => array(),
					'documents'            => array(),
				) : self::product_record( $id );
				if ( null === $record ) {
					continue;
				}
				$products[ $id ] = $record;
				foreach ( self::document_rows( $id ) as $row ) {
					if ( false === ( $row['active'] ?? true ) || '0' === (string) ( $row['active'] ?? '1' ) ) {
						continue;
					}
					if ( null !== $document_ids && ! isset( $document_ids[ DocumentFiles::id( (string) ( $row['url'] ?? '' ) ) ] ) ) {
						continue;
					}
					$needs_bytes = ! $library || self::row_is_cited( $row, $citation_ids );
					$file        = $needs_bytes ? DocumentFiles::resolve( (string) ( $row['url'] ?? '' ) ) : DocumentFiles::locate( (string) ( $row['url'] ?? '' ) );
					if ( null === $file || ! self::attachment_allows( $file['url'], $attachment_permissions ) ) {
						continue;
					}
					$document_id = DocumentFiles::id( $file['url'] );
					if ( ! isset( $documents[ $document_id ] ) ) {
						$aliases = array( $file['url'] );
						foreach ( isset( $file['blob_sha256'] ) ? (array) ( $row['aliases'] ?? array() ) : array() as $alias ) {
							$resolved = is_string( $alias ) ? DocumentFiles::resolve( $alias ) : null;
							if ( null !== $resolved && ( $file['blob_sha256'] ?? null ) === $resolved['blob_sha256'] && self::attachment_allows( $resolved['url'], $attachment_permissions ) ) {
								$aliases[] = $resolved['url'];
							}
						}
						$documents[ $document_id ] = array(
							'document_id'      => $document_id,
							'blob_sha256'      => $file['blob_sha256'] ?? null,
							'url'              => $file['url'],
							'aliases'          => array_values( array_unique( $aliases ) ),
							'product_ids'      => array(),
							'title'            => (string) ( $row['title'] ?? '' ),
							'type'             => (string) ( $row['type'] ?? 'document' ),
							'lang'             => (string) ( $row['lang'] ?? '' ),
							'role'             => (string) ( $row['role'] ?? '' ),
							'citation_aliases' => array_values( array_filter( (array) ( $row['citation_aliases'] ?? array() ), 'is_string' ) ),
						);
					}
					$documents[ $document_id ]['product_ids'][] = $id;
					$products[ $id ]['documents'][]             = $document_id;
				}
			}
			$lang = function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $locale_id, 'slug' ) : 'en';
			$products[ $id ]['locale_product_ids'][ is_string( $lang ) ? $lang : 'en' ] = $locale_id;
			$products[ $id ]['published_locale_ids'][]                                  = $locale_id;
		}
		ksort( $documents );
		foreach ( $documents as &$document ) {
			$document['product_ids'] = array_values( array_unique( $document['product_ids'] ) );
			sort( $document['product_ids'] );
			sort( $document['aliases'] );
		}
		unset( $document );
		ksort( $products );
		foreach ( $products as &$product ) {
			$product['documents'] = array_values( array_unique( $product['documents'] ) );
			sort( $product['documents'] );
			sort( $product['published_locale_ids'] );
		}
		unset( $product );
		if ( $library ) {
			return array(
				'products'  => array_values( $products ),
				'documents' => array_values( $documents ),
			);
		}
		foreach ( $documents as &$document ) {
			$content = $document;
			unset( $content['product_ids'] );
			$document['document_revision'] = self::revision( $content );
		}
		unset( $document );
		foreach ( $products as &$product ) {
			$versions = array();
			foreach ( $product['documents'] as $document_id ) {
				$versions[ $document_id ] = $documents[ $document_id ]['document_revision'];
			}
			$product['product_revision'] = self::revision( array( $product, $versions ) );
			unset( $product['_facts'] );
		}
		unset( $product );
		$manifest                    = array(
			'schema_version'         => 1,
			'compatibility_revision' => self::revision( Publication\CompatibilityClaims::projection( array_values( $products ), array_values( $documents ) ) ),
			'products'               => array_values( $products ),
			'documents'              => array_values( $documents ),
		);
		$manifest['source_revision'] = self::revision( $manifest );
		// Knowledge has an additional identity dependency. Draft-only identity
		// changes must not alter the published source or engineering generation.
		$manifest['model_identity_revision'] = self::model_identity_revision( self::model_statuses_in_current_read() );
		foreach ( $manifest['products'] as &$product ) {
			$product['ready'] = PreparationJobs::readiness( $product['product_id'], $product['product_revision'], $manifest['model_identity_revision'] );
		}
		unset( $product );
		return $manifest;
	}

	/**
	 * Select maintained primary identities; aliases remain owned by the first row.
	 *
	 * @param int $id Current canonical source.
	 * @return array<string,true>
	 */
	private static function product_document_ids( int $id ): array {
		$documents = array();
		foreach ( self::document_rows( $id ) as $row ) {
			if ( false !== ( $row['active'] ?? true ) && '0' !== (string) ( $row['active'] ?? '1' ) ) {
				$documents[ DocumentFiles::id( (string) ( $row['url'] ?? '' ) ) ] = true;
			}
		}
		return $documents;
	}

	/**
	 * A primary or declared alias may be an FAQ source anywhere in this read.
	 *
	 * @param array<string,mixed> $row Current maintained association.
	 * @param array<string,true>  $citation_ids Potential citation paths.
	 */
	private static function row_is_cited( array $row, array $citation_ids ): bool {
		foreach ( array_merge( array( $row['url'] ?? '' ), (array) ( $row['aliases'] ?? array() ) ) as $url ) {
			if ( is_string( $url ) && isset( $citation_ids[ DocumentFiles::id( $url ) ] ) ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * Conservative byte-read scope; stored FAQ bindings still decide release.
	 *
	 * The source candidates in this read are considered before the first shared
	 * document row. A selected product's citation may depend on an earlier row.
	 * Path identity can over-select a file, but cannot authorize an answer.
	 *
	 * @param int[] $ids Native locale candidates.
	 * @return array<string,true>
	 */
	private static function faq_document_ids( array $ids ): array {
		$sources   = array();
		$documents = array();
		foreach ( $ids as $id ) {
			if ( ! self::published_in_current_read( $id ) ) {
				continue;
			}
			$source = self::canonical_id( $id );
			if ( isset( $sources[ $source ] ) ) {
				continue;
			}
			$sources[ $source ] = true;
			foreach ( Faqs::of( $source ) as $entry ) {
				$documents[ DocumentFiles::id( $entry['citation']['url'] ) ] = true;
			}
		}
		return $documents;
	}

	/**
	 * Product facts are versioned without exposing private Woo metadata.
	 *
	 * @param int $id Canonical published product ID.
	 * @return array<string,mixed>|null
	 */
	private static function product_record( int $id ): ?array {
		$post = get_post( $id );
		if ( null === $post ) {
			return null;
		}
		$meta = get_post_meta( $id );
		// Migration receipts are operational recovery, not product facts. Only
		// products with actual maintained claims acquire this fact identity.
		unset( $meta[ Publication\CompatibilityMigration::META_KEY ] );
		$claims = get_post_meta( $id, Publication\CompatibilityClaims::META_KEY, true );
		if ( '' === $claims || array() === $claims ) {
			unset( $meta[ Publication\CompatibilityClaims::META_KEY ] );
		} elseif ( Publication\CompatibilityClaims::shape( $claims ) ) {
			if ( array() === $claims['pairs'] && array() === $claims['requirements'] ) {
				unset( $meta[ Publication\CompatibilityClaims::META_KEY ] );
			} else {
				$meta[ Publication\CompatibilityClaims::META_KEY ] = array( self::ordered( $claims ) );
			}
		}
		// Translation queue status and retry diagnostics are operational metadata.
		foreach ( array_keys( $meta ) as $key ) {
			if ( ( str_starts_with( (string) $key, '_linker_publication_' ) && ! in_array( $key, array( EvidenceBindings::META_KEY, EvidenceBindings::FAQ_META_KEY ), true ) ) || in_array( $key, array( '_edit_lock', '_edit_last', '_linker_i18n_status', '_linker_i18n_note' ), true ) ) {
				unset( $meta[ $key ] );
			}
		}
		$terms = array();
		foreach ( get_object_taxonomies( 'product' ) as $taxonomy ) {
			// This authority assembly already primed native relationships after its
			// fresh runtime read. Reuse those terms without another term query.
			$cached = get_object_term_cache( $id, $taxonomy );
			if ( is_array( $cached ) ) {
				$names = array_column( $cached, 'name' );
			} elseif ( is_wp_error( $cached ) ) {
				$names = $cached;
			} else {
				$names = wp_get_object_terms( $id, $taxonomy, array( 'fields' => 'names' ) );
			}
			if ( ! is_wp_error( $names ) ) {
				sort( $names );
				$terms[ $taxonomy ] = $names;
			}
		}
		return array(
			'product_id'           => $id,
			'title'                => $post->post_title,
			'model'                => implode( ', ', $terms['pa_model'] ?? array() ),
			'brand'                => implode( ', ', $terms['pa_brand'] ?? array() ),
			'engineering_role'     => EngineeringReference::role( $id ),
			'engineering_id'       => is_string( get_post_meta( $id, EngineeringReference::ID_META_KEY, true ) ) ? get_post_meta( $id, EngineeringReference::ID_META_KEY, true ) : '',
			'locale_product_ids'   => array(),
			'published_locale_ids' => array(),
			'documents'            => array(),
			'_facts'               => array(
				'post'  => array( $post->post_title, $post->post_content, $post->post_excerpt, $post->post_name ),
				'meta'  => $meta,
				'terms' => $terms,
			),
		);
	}

	/**
	 * Canonical Woo-maintained associations.
	 *
	 * @param int $id Product ID.
	 * @return list<array<string,mixed>>
	 */
	public static function document_rows( int $id ): array {
		// Resolve this relation read once; the next call still asks the language authority again.
		$id   = self::canonical_id( $id );
		$rows = get_post_meta( $id, EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $rows ) ) {
			$rows = json_decode( $rows, true );
		}
		$rows = is_array( $rows ) ? array_values( array_filter( $rows, 'is_array' ) ) : array();
		if ( '1' === get_post_meta( $id, '_linker_documents_managed', true ) ) {
			return $rows;
		}
		$urls      = array_column( $rows, 'url' );
		$figures   = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$figures   = is_string( $figures ) ? json_decode( $figures, true ) : $figures;
		$citations = array();
		foreach ( is_array( $figures ) ? $figures : array() as $figure ) {
			if ( is_array( $figure ) && is_string( $figure['citation']['url'] ?? null ) ) {
				$citations[] = $figure['citation']['url'];
			}
		}
		foreach ( array( '_delinker_datasheet_url', '_delinker_manual_url' ) as $key ) {
			$legacy = get_post_meta( $id, $key, true );
			if ( is_string( $legacy ) && '' !== $legacy ) {
				$citations[] = $legacy;
			}
		}
		foreach ( array( '_tv_legacy_acf_json', '_linker_de_acf_json' ) as $key ) {
			$raw = get_post_meta( $id, $key, true );
			$acf = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
			foreach ( is_array( $acf ) && is_array( $acf['downloads'] ?? null ) ? $acf['downloads'] : array() as $download ) {
				if ( ! is_array( $download ) ) {
					continue;
				}
				$url = wp_get_attachment_url( (int) ( $download['download_file'] ?? 0 ) );
				if ( is_string( $url ) && ! in_array( $url, $urls, true ) ) {
					$rows[] = array(
						'url'   => $url,
						'title' => (string) ( $download['download_title'] ?? '' ),
						'type'  => (string) ( $download['download_type'] ?? 'document' ),
						'lang'  => (string) ( $download['download_language'] ?? '' ),
						'role'  => (string) ( $download['download_role'] ?? '' ),
					);
					$urls[] = $url;
				}
			}
		}
		foreach ( array_unique( $citations ) as $url ) {
			if ( ! in_array( $url, $urls, true ) ) {
				$rows[] = array(
					'url'   => $url,
					'title' => '',
					'type'  => 'document',
					'lang'  => '',
				);
			}
		}
		return $rows;
	}

	/**
	 * A media-level withdrawal applies to every relation of that attachment.
	 *
	 * @param string             $url Hosted document URL.
	 * @param array<string,bool> $permissions Decisions for this assembly only.
	 */
	private static function attachment_allows( string $url, array &$permissions ): bool {
		if ( ! array_key_exists( $url, $permissions ) ) {
			$id                  = attachment_url_to_postid( $url );
			$permissions[ $url ] = 0 === $id || ! in_array( get_post_meta( $id, '_linker_document_public', true ), array( '0', 0, false ), true );
		}
		return $permissions[ $url ];
	}

	/**
	 * Current cited FAQ answers; raw editorial metadata remains available to its editor.
	 *
	 * @param int                      $id Product ID.
	 * @param array<string,mixed>|null $manifest Current assembly, otherwise a fresh read.
	 * @return list<array{question:string,answer:string,question_de:string,answer_de:string,citation:array{url:string,page:int,title?:string}}>
	 * @phpstan-impure
	 */
	public static function faqs_for( int $id, ?array $manifest = null ): array {
		if ( ! self::is_published( $id ) ) {
			return array();
		}
		$id      = self::canonical_id( $id );
		$entries = Faqs::of( $id );
		if ( array() === $entries ) {
			return array();
		}
		// FAQ release needs current cited bytes, not product revision or readiness.
		$manifest ??= self::product_library_read( $id );
		if ( ! in_array( $id, array_column( $manifest['products'], 'product_id' ), true ) ) {
			return array();
		}
		$answers = array();
		foreach ( $entries as $entry ) {
			foreach ( $manifest['documents'] as $document ) {
				if ( in_array( $id, $document['product_ids'], true ) && in_array( strtok( $entry['citation']['url'], '#' ), $document['aliases'], true ) && EvidenceBindings::matches_faq( $id, $entry, $document ) ) {
					$answers[] = $entry;
					break;
				}
			}
		}
		return $answers;
	}

	/**
	 * Current public product, never draft facts.
	 *
	 * @param int $id Product ID.
	 * @return array<string,mixed>|null
	 */
	public static function product( int $id ): ?array {
		if ( ! self::is_published( $id ) ) {
			return null;
		}
		$canonical = self::canonical_id( $id );
		foreach ( self::manifest()['products'] as $product ) {
			if ( $canonical === $product['product_id'] ) {
				return $product;
			}
		}
		return null;
	}

	/**
	 * Current cited figures for a product, without private or removed evidence.
	 *
	 * @param int                      $id Product ID.
	 * @param array<string,mixed>|null $manifest Optional current caller snapshot.
	 * @return array<string,array<string,mixed>>
	 */
	public static function figures_for( int $id, ?array $manifest = null ): array {
		if ( ! self::is_published( $id ) ) {
			return array();
		}
		$id         = self::canonical_id( $id );
		$manifest ??= self::manifest();
		$allowed    = array();
		$names      = array();
		foreach ( $manifest['documents'] as $document ) {
			if ( ! in_array( $id, $document['product_ids'], true ) ) {
				continue;
			}
			foreach ( $document['aliases'] as $url ) {
				$path             = rawurldecode( (string) wp_parse_url( $url, PHP_URL_PATH ) );
				$allowed[ $path ] = $document;
				$names[ strtolower( basename( $path ) ) ][ $document['document_id'] ] = $document;
			}
			foreach ( $document['citation_aliases'] ?? array() as $name ) {
				$names[ strtolower( $name ) ][ $document['document_id'] ] = $document;
			}
		}
		$raw    = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$raw    = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$result = array();
		foreach ( is_array( $raw ) ? $raw : array() as $key => $entry ) {
			if ( ! is_array( $entry ) || ! is_array( $entry['citation'] ?? null ) ) {
				continue;
			}
			$document = null;
			$url      = $entry['citation']['url'] ?? null;
			if ( is_string( $url ) ) {
				$host  = wp_parse_url( $url, PHP_URL_HOST );
				$hosts = array( wp_parse_url( home_url(), PHP_URL_HOST ), 'de-linker.com', 'www.de-linker.com' );
				if ( is_string( $host ) && in_array( strtolower( $host ), $hosts, true ) ) {
					$document = $allowed[ rawurldecode( (string) wp_parse_url( $url, PHP_URL_PATH ) ) ] ?? null;
				}
			} elseif ( is_string( $entry['citation']['doc'] ?? null ) ) {
				$matches = $names[ strtolower( $entry['citation']['doc'] ) ] ?? array();
				if ( 1 === count( $matches ) ) {
					$document = reset( $matches );
				}
			}
			if ( is_array( $document ) && EvidenceBindings::matches( $id, (string) $key, $entry, $document ) ) {
				$entry['citation']['url'] = $document['url'];
				$result[ (string) $key ]  = $entry;
			}
		}

		return $result;
	}

	/**
	 * Validate the complete caller-supplied scope against a fresh authority read.
	 *
	 * @param array<string,mixed> $dependencies Product/document revisions.
	 * @return array<string,mixed>
	 */
	public static function validate( array $dependencies ): array {
		return self::validate_manifest( $dependencies, self::manifest() );
	}

	/**
	 * Validate dependency semantics against an explicitly supplied source snapshot.
	 *
	 * Current operations call validate(); this pure seam supports contract fixtures.
	 *
	 * @param array<string,mixed> $dependencies Product/document revisions.
	 * @param array<string,mixed> $manifest Trusted current source snapshot.
	 * @return array<string,mixed>
	 */
	public static function validate_manifest( array $dependencies, array $manifest ): array {
		$products  = array_column( $manifest['products'], null, 'product_id' );
		$documents = array_column( $manifest['documents'], null, 'document_id' );
		$invalid   = array();
		foreach ( array( 'products', 'documents' ) as $kind ) {
			if ( ! isset( $dependencies[ $kind ] ) || ! is_array( $dependencies[ $kind ] ) || ! array_is_list( $dependencies[ $kind ] ) ) {
				$invalid[] = array(
					'kind'   => $kind,
					'id'     => '',
					'reason' => 'invalid_dependencies',
				);
				continue;
			}
			foreach ( $dependencies[ $kind ] as $dependency ) {
				if ( ! is_array( $dependency ) ) {
					$invalid[] = array(
						'kind'   => $kind,
						'id'     => '',
						'reason' => 'invalid_dependency',
					);
					continue;
				}
				$key      = 'products' === $kind ? 'product_id' : 'document_id';
				$revision = 'products' === $kind ? 'product_revision' : 'document_revision';
				$id       = $dependency[ $key ] ?? '';
				if ( ( 'products' === $kind && ( ! is_int( $id ) || $id < 1 ) ) || ( 'documents' === $kind && ( ! is_string( $id ) || '' === $id || ! is_int( $dependency['product_id'] ?? null ) ) ) ) {
					$invalid[] = array(
						'kind'   => $kind,
						'id'     => '',
						'reason' => 'invalid_dependency',
					);
					continue;
				}
				$current = 'products' === $kind ? ( $products[ $id ] ?? null ) : ( $documents[ $id ] ?? null );
				$reason  = null === $current ? 'unavailable' : ( ! is_string( $dependency[ $revision ] ?? null ) || ! hash_equals( $current[ $revision ], $dependency[ $revision ] ) ? 'revision_mismatch' : '' );
				if ( 'documents' === $kind && null !== $current && ! in_array( $dependency['product_id'] ?? null, $current['product_ids'], true ) ) {
					$reason = 'association_unavailable';
				}
				if ( '' !== $reason ) {
					$invalid[] = array(
						'kind'   => $kind,
						'id'     => $id,
						'reason' => $reason,
					);
				}
			}
		}
		if ( isset( $dependencies['compatibility_revision'] ) && $dependencies['compatibility_revision'] !== $manifest['compatibility_revision'] ) {
			$invalid[] = array(
				'kind'   => 'compatibility',
				'id'     => '',
				'reason' => 'revision_mismatch',
			);
		}
		if ( array_key_exists( 'model_identity_revision', $dependencies ) && ( ! is_string( $dependencies['model_identity_revision'] ) || 1 !== preg_match( '/^[a-f0-9]{64}$/D', $dependencies['model_identity_revision'] ) || ( $manifest['model_identity_revision'] ?? null ) !== $dependencies['model_identity_revision'] ) ) {
			$invalid[] = array(
				'kind'   => 'model_identity',
				'id'     => '',
				'reason' => 'revision_mismatch',
			);
		}
		return array(
			'valid'           => array() === $invalid,
			'source_revision' => $manifest['source_revision'],
			'invalid'         => $invalid,
		);
	}
}
