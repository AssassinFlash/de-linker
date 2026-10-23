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

/** A current read; no TTL, index or preparation acknowledgement grants access. */
final class Publication {
	/** Stable canonical JSON hash; generated times and readiness stay outside it. */
	public static function revision( mixed $value ): string {
		return hash( 'sha256', (string) wp_json_encode( self::ordered( $value ), JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ) );
	}

	/** @return mixed */
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

	/** Canonical identity uses the existing language layer. */
	public static function canonical_id( int $id ): int {
		return (int) apply_filters( 'linker_commerce_facts_product_id', $id );
	}

	/** Both locale and source must currently be published. */
	public static function is_published( int $id ): bool {
		$canonical = self::canonical_id( $id );
		return $id > 0 && 'product' === get_post_type( $id ) && 'publish' === get_post_status( $id ) && 'product' === get_post_type( $canonical ) && 'publish' === get_post_status( $canonical );
	}

	/** @return array<string,mixed> Current public manifest, including an empty set. */
	public static function manifest(): array {
		$ids = get_posts( array( 'post_type' => 'product', 'post_status' => 'publish', 'fields' => 'ids', 'posts_per_page' => -1, 'orderby' => 'ID', 'order' => 'ASC', 'suppress_filters' => true ) );
		$products = array();
		$documents = array();
		foreach ( $ids as $locale_id ) {
			$locale_id = (int) $locale_id;
			if ( ! self::is_published( $locale_id ) ) {
				continue;
			}
			$id = self::canonical_id( $locale_id );
			if ( ! isset( $products[ $id ] ) ) {
				$post = get_post( $id );
				$meta = get_post_meta( $id );
				foreach ( array_keys( $meta ) as $key ) {
					if ( str_starts_with( $key, '_linker_publication_' ) || in_array( $key, array( '_edit_lock', '_edit_last' ), true ) ) {
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
				$products[ $id ] = array( 'product_id' => $id, 'title' => $post->post_title, 'model' => implode( ', ', $terms['pa_model'] ?? array() ), 'brand' => implode( ', ', $terms['pa_brand'] ?? array() ), 'locale_product_ids' => array(), 'published_locale_ids' => array(), 'documents' => array(), '_facts' => array( 'post' => array( $post->post_title, $post->post_content, $post->post_excerpt, $post->post_name ), 'meta' => $meta, 'terms' => $terms ) );
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
						$documents[ $document_id ] = array( 'document_id' => $document_id, 'blob_sha256' => $file['blob_sha256'], 'url' => $file['url'], 'aliases' => array_values( array_unique( $aliases ) ), 'product_ids' => array(), 'title' => (string) ( $row['title'] ?? '' ), 'type' => (string) ( $row['type'] ?? 'document' ), 'lang' => (string) ( $row['lang'] ?? '' ) );
					}
					$documents[ $document_id ]['product_ids'][] = $id;
					$products[ $id ]['documents'][] = $document_id;
				}
			}
			$lang = function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $locale_id, 'slug' ) : 'en';
			$products[ $id ]['locale_product_ids'][ is_string( $lang ) && '' !== $lang ? $lang : 'en' ] = $locale_id;
			$products[ $id ]['published_locale_ids'][] = $locale_id;
		}
		ksort( $documents );
		foreach ( $documents as &$document ) {
			$document['product_ids'] = array_values( array_unique( $document['product_ids'] ) );
			sort( $document['product_ids'] );
			sort( $document['aliases'] );
			$document['document_revision'] = self::revision( $document );
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
		$manifest = array( 'schema_version' => 1, 'compatibility_revision' => self::revision( array( EngineeringData::json( EngineeringData::COMPATIBILITY_FILE ), EngineeringData::json( EngineeringData::OVERLAY_FILE ) ) ), 'products' => array_values( $products ), 'documents' => array_values( $documents ) );
		$manifest['source_revision'] = self::revision( $manifest );
		foreach ( $manifest['products'] as &$product ) {
			$product['ready'] = PreparationJobs::readiness( $product['product_id'], $product['product_revision'] );
		}
		unset( $product );
		return $manifest;
	}

	/** @return list<array<string,mixed>> Canonical Woo-maintained associations. */
	public static function document_rows( int $id ): array {
		$rows = get_post_meta( self::canonical_id( $id ), EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $rows ) ) {
			$rows = json_decode( $rows, true );
		}
		return is_array( $rows ) ? array_values( array_filter( $rows, 'is_array' ) ) : array();
	}

	/** A media-level withdrawal applies to every relation of that attachment. */
	private static function attachment_allows( string $url ): bool {
		$id = attachment_url_to_postid( $url );
		return 0 === $id || ! in_array( get_post_meta( $id, '_linker_document_public', true ), array( '0', 0, false ), true );
	}

	/** @return array<string,mixed>|null Current public product, never draft facts. */
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

	/** @param array<string,mixed> $dependencies @return array<string,mixed> */
	public static function validate( array $dependencies ): array {
		$manifest = self::manifest();
		$products = array_column( $manifest['products'], null, 'product_id' );
		$documents = array_column( $manifest['documents'], null, 'document_id' );
		$invalid = array();
		foreach ( array( 'products', 'documents' ) as $kind ) {
			if ( ! isset( $dependencies[ $kind ] ) || ! is_array( $dependencies[ $kind ] ) || ! array_is_list( $dependencies[ $kind ] ) ) {
				$invalid[] = array( 'kind' => $kind, 'id' => '', 'reason' => 'invalid_dependencies' );
				continue;
			}
			foreach ( $dependencies[ $kind ] as $dependency ) {
				if ( ! is_array( $dependency ) ) {
					$invalid[] = array( 'kind' => $kind, 'id' => '', 'reason' => 'invalid_dependency' );
					continue;
				}
				$key = 'products' === $kind ? 'product_id' : 'document_id';
				$revision = 'products' === $kind ? 'product_revision' : 'document_revision';
				$id = $dependency[ $key ] ?? '';
				$current = 'products' === $kind ? ( $products[ $id ] ?? null ) : ( $documents[ $id ] ?? null );
				$reason = null === $current ? 'unavailable' : ( ! is_string( $dependency[ $revision ] ?? null ) || ! hash_equals( $current[ $revision ], $dependency[ $revision ] ) ? 'revision_mismatch' : '' );
				if ( 'documents' === $kind && null !== $current && ! in_array( $dependency['product_id'] ?? null, $current['product_ids'], true ) ) {
					$reason = 'association_unavailable';
				}
				if ( '' !== $reason ) {
					$invalid[] = array( 'kind' => $kind, 'id' => $id, 'reason' => $reason );
				}
			}
		}
		if ( isset( $dependencies['compatibility_revision'] ) && $dependencies['compatibility_revision'] !== $manifest['compatibility_revision'] ) {
			$invalid[] = array( 'kind' => 'compatibility', 'id' => '', 'reason' => 'revision_mismatch' );
		}
		return array( 'valid' => array() === $invalid, 'source_revision' => $manifest['source_revision'], 'invalid' => $invalid );
	}
}
