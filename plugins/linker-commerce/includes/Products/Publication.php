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
use Linker\Commerce\Products\Publication\FigureBindings;

/** A current read; no TTL, index or preparation acknowledgement grants access. */
final class Publication {
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
	 * Assemble this authority read, hashing each real file at most once.
	 *
	 * @return array<string,mixed>
	 */
	private static function assemble(): array {
		$ids       = get_posts(
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
		);
		$products  = array();
		$documents = array();
		foreach ( $ids as $locale_id ) {
			$locale_id = (int) $locale_id;
			if ( ! self::is_published( $locale_id ) ) {
				continue;
			}
			$id = self::canonical_id( $locale_id );
			if ( ! isset( $products[ $id ] ) ) {
				$record = self::product_record( $id );
				if ( null === $record ) {
					continue;
				}
				$products[ $id ] = $record;
				foreach ( self::document_rows( $id ) as $row ) {
					if ( false === ( $row['active'] ?? true ) || '0' === (string) ( $row['active'] ?? '1' ) ) {
						continue;
					}
					$file = DocumentFiles::resolve( (string) ( $row['url'] ?? '' ) );
					if ( null === $file || ! self::attachment_allows( $file['url'] ) ) {
						continue;
					}
					$document_id = DocumentFiles::id( $file['url'] );
					if ( ! isset( $documents[ $document_id ] ) ) {
						$aliases = array( $file['url'] );
						foreach ( (array) ( $row['aliases'] ?? array() ) as $alias ) {
							$resolved = is_string( $alias ) ? DocumentFiles::resolve( $alias ) : null;
							if ( null !== $resolved && $resolved['blob_sha256'] === $file['blob_sha256'] && self::attachment_allows( $resolved['url'] ) ) {
								$aliases[] = $resolved['url'];
							}
						}
						$documents[ $document_id ] = array(
							'document_id'      => $document_id,
							'blob_sha256'      => $file['blob_sha256'],
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
			$content = $document;
			unset( $content['product_ids'] );
			$document['document_revision'] = self::revision( $content );
		}
		unset( $document );
		ksort( $products );
		foreach ( $products as &$product ) {
			$product['documents'] = array_values( array_unique( $product['documents'] ) );
			sort( $product['documents'] );
			sort( $product['published_locale_ids'] );
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
			'compatibility_revision' => self::revision( array( EngineeringData::json( EngineeringData::COMPATIBILITY_FILE ), EngineeringData::json( EngineeringData::OVERLAY_FILE ) ) ),
			'products'               => array_values( $products ),
			'documents'              => array_values( $documents ),
		);
		$manifest['source_revision'] = self::revision( $manifest );
		foreach ( $manifest['products'] as &$product ) {
			$product['ready'] = PreparationJobs::readiness( $product['product_id'], $product['product_revision'] );
		}
		unset( $product );
		return $manifest;
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
		foreach ( array_keys( $meta ) as $key ) {
			if ( ( str_starts_with( (string) $key, '_linker_publication_' ) && FigureBindings::META_KEY !== $key ) || in_array( $key, array( '_edit_lock', '_edit_last' ), true ) ) {
				unset( $meta[ $key ] );
			}
		}
		$terms = array();
		foreach ( get_object_taxonomies( 'product' ) as $taxonomy ) {
			$names = wp_get_object_terms( $id, $taxonomy, array( 'fields' => 'names' ) );
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
		$rows = get_post_meta( self::canonical_id( $id ), EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $rows ) ) {
			$rows = json_decode( $rows, true );
		}
		$rows      = is_array( $rows ) ? array_values( array_filter( $rows, 'is_array' ) ) : array();
		$urls      = array_column( $rows, 'url' );
		$figures   = get_post_meta( self::canonical_id( $id ), SelectionFacts::FIGURES_META_KEY, true );
		$figures   = is_string( $figures ) ? json_decode( $figures, true ) : $figures;
		$citations = array();
		foreach ( is_array( $figures ) ? $figures : array() as $figure ) {
			if ( is_array( $figure ) && is_string( $figure['citation']['url'] ?? null ) ) {
				$citations[] = $figure['citation']['url'];
			}
		}
		foreach ( array( '_delinker_datasheet_url', '_delinker_manual_url' ) as $key ) {
			$legacy = get_post_meta( self::canonical_id( $id ), $key, true );
			if ( is_string( $legacy ) && '' !== $legacy ) {
				$citations[] = $legacy;
			}
		}
		foreach ( array( '_tv_legacy_acf_json', '_linker_de_acf_json' ) as $key ) {
			$raw = get_post_meta( self::canonical_id( $id ), $key, true );
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
	 * @param string $url Hosted document URL.
	 */
	private static function attachment_allows( string $url ): bool {
		$id = attachment_url_to_postid( $url );
		return 0 === $id || ! in_array( get_post_meta( $id, '_linker_document_public', true ), array( '0', 0, false ), true );
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
			if ( is_array( $document ) && FigureBindings::matches( $id, (string) $key, $entry, $document ) ) {
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
		return array(
			'valid'           => array() === $invalid,
			'source_revision' => $manifest['source_revision'],
			'invalid'         => $invalid,
		);
	}
}
