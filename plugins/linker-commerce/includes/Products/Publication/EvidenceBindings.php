<?php
/**
 * Existing Woo technical values and cited answers remain tied to their source bytes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\Faqs;

/** A generated evidence binding, not another manually maintained product source. */
final class EvidenceBindings {
	public const META_KEY     = '_linker_publication_figures';
	public const FAQ_META_KEY = '_linker_publication_faqs';

	/**
	 * Initialize never-bound entries after Woo persists current explicit source relations.
	 * Previously recorded entries, including stale evidence, are never renewed here.
	 *
	 * @param int $id Saved locale product ID.
	 */
	public static function capture_missing( int $id ): void {
		if ( ! Publication::is_published( $id ) ) {
			return;
		}
		$id = Publication::canonical_id( $id );
		self::capture( $id, true );
		self::capture_faqs( $id, true );
	}

	/**
	 * Bind new/edited figure facts; unchanged fields never adopt replaced bytes.
	 *
	 * @param int  $id Canonical Woo product.
	 * @param bool $adopt_existing Initial explicit-source adoption; never overwrite an existing entry.
	 */
	public static function capture( int $id, bool $adopt_existing = false ): void {
		$id  = Publication::canonical_id( $id );
		$raw = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$raw = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$raw = is_array( $raw ) ? $raw : array();
		self::capture_entries( $id, $raw, self::META_KEY, $adopt_existing );
	}

	/**
	 * Bind cited answers by content identity, so reordering never adopts new PDF bytes.
	 *
	 * @param int  $id Canonical Woo product.
	 * @param bool $adopt_existing Preserve existing entries while adopting missing explicit sources.
	 */
	public static function capture_faqs( int $id, bool $adopt_existing = false ): void {
		$id      = Publication::canonical_id( $id );
		$entries = array();
		foreach ( Faqs::of( $id ) as $entry ) {
			$entries[ Publication::revision( $entry ) ] = $entry;
		}
		self::capture_entries( $id, $entries, self::FAQ_META_KEY, $adopt_existing );
	}

	/**
	 * Capture only explicit current relations; preserve unchanged historical evidence.
	 *
	 * @param int                     $id Product ID.
	 * @param array<int|string,mixed> $raw Current Woo entries.
	 * @param string                  $meta_key Generated binding field.
	 * @param bool                    $adopt_existing Adopt missing existing bindings only.
	 */
	private static function capture_entries( int $id, array $raw, string $meta_key, bool $adopt_existing ): void {
		$previous = get_post_meta( $id, $meta_key, true );
		if ( $adopt_existing && ! is_array( $previous ) && metadata_exists( 'post', $id, $meta_key ) ) {
			return;
		}
		$previous = is_array( $previous ) ? $previous : array();
		$paths    = array();
		$names    = array();
		$needed   = false;
		foreach ( $raw as $key => $entry ) {
			if ( ! is_array( $entry ) || ! is_array( $entry['citation'] ?? null ) ) {
				continue;
			}
			$old = $previous[ $key ] ?? null;
			if ( $adopt_existing ? ! array_key_exists( $key, $previous ) : ! is_array( $old ) || ( $old['figure_revision'] ?? '' ) !== Publication::revision( $entry ) ) {
				$needed = true;
				break;
			}
		}
		if ( $needed ) {
			DocumentFiles::begin_read();
			try {
				foreach ( Publication::document_rows( $id ) as $row ) {
					$file = DocumentFiles::resolve( (string) ( $row['url'] ?? '' ) );
					if ( null === $file ) {
						continue;
					}
					$identity = DocumentFiles::id( $file['url'] );
					$binding  = array(
						'document_id' => $identity,
						'blob_sha256' => $file['blob_sha256'],
					);
					foreach ( array_merge( array( $file['url'] ), (array) ( $row['aliases'] ?? array() ) ) as $url ) {
						$alias = is_string( $url ) ? DocumentFiles::resolve( $url ) : null;
						if ( null !== $alias && $alias['blob_sha256'] === $file['blob_sha256'] ) {
							$path           = rawurldecode( (string) wp_parse_url( $alias['url'], PHP_URL_PATH ) );
							$paths[ $path ] = $binding;
							$names[ strtolower( basename( $path ) ) ][ $identity ] = $binding;
						}
					}
					foreach ( (array) ( $row['citation_aliases'] ?? array() ) as $name ) {
						if ( is_string( $name ) ) {
							$names[ strtolower( $name ) ][ $identity ] = $binding;
						}
					}
				}
			} finally {
				DocumentFiles::end_read();
			}
		}
		$next = array();
		foreach ( $raw as $key => $entry ) {
			if ( ! is_array( $entry ) || ! is_array( $entry['citation'] ?? null ) ) {
				continue;
			}
			$fingerprint = Publication::revision( $entry );
			$old         = $previous[ $key ] ?? null;
			if ( ( $adopt_existing && array_key_exists( $key, $previous ) ) || ( is_array( $old ) && ( $old['figure_revision'] ?? '' ) === $fingerprint ) ) {
				$next[ $key ] = $previous[ $key ];
				continue;
			}
			$binding = null;
			if ( is_string( $entry['citation']['url'] ?? null ) ) {
				$url  = $entry['citation']['url'];
				$file = DocumentFiles::resolve( $url );
				if ( null !== $file ) {
					$binding = $paths[ rawurldecode( (string) wp_parse_url( $file['url'], PHP_URL_PATH ) ) ] ?? null;
				}
			} elseif ( is_string( $entry['citation']['doc'] ?? null ) ) {
				$matches = $names[ strtolower( $entry['citation']['doc'] ) ] ?? array();
				if ( 1 === count( $matches ) ) {
					$binding = reset( $matches );
				}
			}
			if ( is_array( $binding ) ) {
				$next[ $key ] = array_merge( $binding, array( 'figure_revision' => $fingerprint ) );
			}
		}
		update_post_meta( $id, $meta_key, $next );
	}

	/**
	 * Neither a URL nor a ready acknowledgement proves old values in new bytes.
	 *
	 * @param int                 $id Product ID.
	 * @param string              $key Figure key.
	 * @param array<string,mixed> $entry Current Woo figure.
	 * @param array<string,mixed> $document Current allowed document.
	 */
	public static function matches( int $id, string $key, array $entry, array $document ): bool {
		return self::binding_matches( $id, self::META_KEY, $key, $entry, $document );
	}

	/**
	 * A cited answer is current only for the bytes to which it was bound.
	 *
	 * @param int                 $id Product ID.
	 * @param array<string,mixed> $entry Current normalized FAQ.
	 * @param array<string,mixed> $document Current allowed document.
	 */
	public static function matches_faq( int $id, array $entry, array $document ): bool {
		return self::binding_matches( $id, self::FAQ_META_KEY, Publication::revision( $entry ), $entry, $document );
	}

	/**
	 * Compare a generated entry binding with currently allowed file bytes.
	 *
	 * @param int                 $id Product ID.
	 * @param string              $meta_key Binding field.
	 * @param string              $key Entry identity.
	 * @param array<string,mixed> $entry Current Woo entry.
	 * @param array<string,mixed> $document Allowed document.
	 */
	private static function binding_matches( int $id, string $meta_key, string $key, array $entry, array $document ): bool {
		$bindings = get_post_meta( $id, $meta_key, true );
		$binding  = is_array( $bindings ) ? ( $bindings[ $key ] ?? null ) : null;
		return is_array( $binding ) && ( $binding['figure_revision'] ?? '' ) === Publication::revision( $entry ) && ( $binding['document_id'] ?? '' ) === $document['document_id'] && ( $binding['blob_sha256'] ?? '' ) === $document['blob_sha256'];
	}
}
