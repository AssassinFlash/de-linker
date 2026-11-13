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
			$entries[ Publication::figure_revision( $entry ) ] = $entry;
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
			if ( $adopt_existing ? ! array_key_exists( $key, $previous ) : ! is_array( $old ) || ( $old['figure_revision'] ?? '' ) !== Publication::figure_revision( $entry ) ) {
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
			$fingerprint = Publication::figure_revision( $entry );
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
	 * Renew bindings whose entry changed while their source document did not.
	 *
	 * An entry's revision moves when its own text changes (a citation rewritten
	 * from a document label to its URL, a missing unit added, an FAQ answer
	 * edited); the bytes it cites can stay the same. Such a binding is a
	 * bookkeeping miss, not stale evidence, and `capture()`/`capture_faqs()`
	 * with `$adopt_existing` or direct metadata edits never repair it:
	 * `adopt_existing` keeps every recorded entry and the ordinary path only
	 * binds entries whose revision moved *with* new bytes. This repairs exactly
	 * the miss and nothing else: both the document identity and its blob must
	 * equal the recorded binding, so no value ever adopts a replaced file.
	 *
	 * @param int  $id      Canonical Woo product.
	 * @param bool $dry_run Count the renewable bindings without writing.
	 * @return int Bindings renewed (or renewable, on a dry run).
	 */
	public static function repair_unchanged( int $id, bool $dry_run = false ): int {
		$id = Publication::canonical_id( $id );
		if ( ! Publication::is_published( $id ) ) {
			return 0;
		}
		$previous_figures = get_post_meta( $id, self::META_KEY, true );
		$previous_figures = is_array( $previous_figures ) ? $previous_figures : array();
		$raw_figures      = get_post_meta( $id, SelectionFacts::FIGURES_META_KEY, true );
		$raw_figures      = is_string( $raw_figures ) ? json_decode( $raw_figures, true ) : $raw_figures;
		$stale_figures    = array();
		if ( array() !== $previous_figures && is_array( $raw_figures ) ) {
			foreach ( $raw_figures as $key => $entry ) {
				$old = $previous_figures[ $key ] ?? null;
				if ( ! is_array( $entry ) || ! is_array( $entry['citation'] ?? null ) || ! is_array( $old ) ) {
					continue;
				}
				if ( ( $old['figure_revision'] ?? '' ) !== Publication::figure_revision( $entry ) ) {
					$stale_figures[ $key ] = $entry;
				}
			}
		}

		$previous_faqs = get_post_meta( $id, self::FAQ_META_KEY, true );
		$previous_faqs = is_array( $previous_faqs ) ? $previous_faqs : array();
		$faq_entries   = array();
		$stale_faqs    = array();
		if ( array() !== $previous_faqs ) {
			foreach ( Faqs::of( $id ) as $entry ) {
				$revision                 = Publication::figure_revision( $entry );
				$faq_entries[ $revision ] = $entry;
				if ( ! array_key_exists( $revision, $previous_faqs ) ) {
					$stale_faqs[ $revision ] = $entry;
				}
			}
		}

		if ( array() === $stale_figures && array() === $stale_faqs ) {
			return 0;
		}

		// Only a product with a stale entry pays for reading its documents.
		$allowed         = self::documents_by_citation_path( $id );
		$renewed_figures = 0;
		if ( array() !== $stale_figures ) {
			$next_figures = $previous_figures;
			foreach ( $stale_figures as $key => $entry ) {
				$old      = $previous_figures[ $key ];
				$document = self::cited_document( $entry, $allowed );
				if (
					null === $document
					|| ( $old['document_id'] ?? '' ) !== $document['document_id']
					|| ( $old['blob_sha256'] ?? '' ) !== $document['blob_sha256']
				) {
					continue;
				}
				$next_figures[ $key ] = array_merge(
					$old,
					array( 'figure_revision' => Publication::figure_revision( $entry ) )
				);
				++$renewed_figures;
			}
			if ( $renewed_figures > 0 && ! $dry_run ) {
				update_post_meta( $id, self::META_KEY, $next_figures );
			}
		}

		$renewed_faqs = 0;
		if ( array() !== $stale_faqs ) {
			$next_faqs     = $previous_faqs;
			$orphaned_faqs = array_diff_key( $previous_faqs, $faq_entries );
			foreach ( $stale_faqs as $revision => $entry ) {
				$document = self::cited_document( $entry, $allowed );
				if ( null === $document ) {
					continue;
				}
				foreach ( $orphaned_faqs as $old_key => $old ) {
					if (
						! is_array( $old )
						|| ( $old['document_id'] ?? '' ) !== $document['document_id']
						|| ( $old['blob_sha256'] ?? '' ) !== $document['blob_sha256']
					) {
						continue;
					}
					unset( $orphaned_faqs[ $old_key ], $next_faqs[ $old_key ] );
					$next_faqs[ $revision ] = array_merge(
						$old,
						array( 'figure_revision' => $revision )
					);
					++$renewed_faqs;
					break;
				}
			}
			if ( $renewed_faqs > 0 && ! $dry_run ) {
				update_post_meta( $id, self::FAQ_META_KEY, $next_faqs );
			}
		}

		return $renewed_figures + $renewed_faqs;
	}

	/**
	 * The current documents of one product, by the path their aliases cite, and
	 * by file name for entries whose citation names the document instead.
	 *
	 * @param int $id Canonical Woo product.
	 * @return array{paths:array<string,array<string,mixed>>,names:array<string,array<string,array<string,mixed>>>}
	 */
	private static function documents_by_citation_path( int $id ): array {
		$paths = array();
		$names = array();
		DocumentFiles::begin_read();
		try {
			foreach ( Publication::document_rows( $id ) as $row ) {
				$file = DocumentFiles::resolve( (string) ( $row['url'] ?? '' ) );
				if ( null === $file ) {
					continue;
				}
				$identity = DocumentFiles::id( $file['url'] );
				$document = array(
					'document_id' => $identity,
					'blob_sha256' => $file['blob_sha256'],
				);
				foreach ( array_merge( array( $file['url'] ), (array) ( $row['aliases'] ?? array() ) ) as $url ) {
					$alias = is_string( $url ) ? DocumentFiles::resolve( $url ) : null;
					if ( null !== $alias && $alias['blob_sha256'] === $file['blob_sha256'] ) {
						$path           = rawurldecode( (string) wp_parse_url( $alias['url'], PHP_URL_PATH ) );
						$paths[ $path ] = $document;
						$names[ strtolower( basename( $path ) ) ][ $identity ] = $document;
					}
				}
				foreach ( (array) ( $row['citation_aliases'] ?? array() ) as $name ) {
					if ( is_string( $name ) ) {
						$names[ strtolower( $name ) ][ $identity ] = $document;
					}
				}
			}
		} finally {
			DocumentFiles::end_read();
		}

		return array(
			'paths' => $paths,
			'names' => $names,
		);
	}

	/**
	 * The one current document an entry cites, resolved the way the feed does it:
	 * by path for a URL, by file name only when exactly one document answers.
	 *
	 * @param array<string,mixed>                                                                                  $entry   Current Woo figure.
	 * @param array{paths:array<string,array<string,mixed>>,names:array<string,array<string,array<string,mixed>>>} $allowed Current documents of the product.
	 * @return array<string,mixed>|null
	 */
	private static function cited_document( array $entry, array $allowed ): ?array {
		$url = $entry['citation']['url'] ?? null;
		if ( is_string( $url ) ) {
			return $allowed['paths'][ self::citation_path( $entry ) ] ?? null;
		}
		$doc = $entry['citation']['doc'] ?? null;
		if ( ! is_string( $doc ) ) {
			return null;
		}
		$matches = $allowed['names'][ strtolower( $doc ) ] ?? array();

		return 1 === count( $matches ) ? reset( $matches ) : null;
	}

	/**
	 * The citation path of an entry, normalized as `figure_revision()` does it.
	 *
	 * @param array<string,mixed> $entry Current Woo figure.
	 */
	private static function citation_path( array $entry ): string {
		$url = $entry['citation']['url'] ?? null;

		return is_string( $url ) ? rawurldecode( (string) wp_parse_url( $url, PHP_URL_PATH ) ) : '';
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
		return self::binding_matches( $id, self::FAQ_META_KEY, Publication::figure_revision( $entry ), $entry, $document );
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
		return is_array( $binding ) && ( $binding['figure_revision'] ?? '' ) === Publication::figure_revision( $entry ) && ( $binding['document_id'] ?? '' ) === $document['document_id'] && ( $binding['blob_sha256'] ?? '' ) === $document['blob_sha256'];
	}
}
