<?php
/**
 * Display a live document against the publication read used to release the turn.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Genie;

use Linker\Commerce\Products\Materials;

/** A shared manual identifies a model only when the cited evidence identifies that model. */
final class LiveDocuments {
	/** Resolve the explicit evidence owner, including the older product-scoped reference.
	 *
	 * @param array<string,mixed> $block Hydrated document.
	 */
	public static function owner( array $block ): ?int {
		if ( isset( $block['evidence_product_id'] ) ) {
			return (int) $block['evidence_product_id'];
		}
		return preg_match( '/^p(\d+)\.(?:document\.\d+|.+\.source(?:\.\d+)?)$/D', $block['ref'] ?? '', $match ) ? (int) $match[1] : null;
	}

	/**
	 * Keep the exact URL and pages only for the current file version and association.
	 *
	 * @param array<string,mixed> $block    Hydrated document.
	 * @param array<string,mixed> $manifest Checked Woo manifest.
	 * @param int[]               $shown    IDs referenced by this answer.
	 * @param string              $locale   Turn language.
	 * @return array<string,mixed> Browser document block.
	 */
	public static function present( array $block, array $manifest, array $shown, string $locale ): array {
		$owner        = self::owner( $block );
		$base         = explode( '#', (string) ( $block['url'] ?? '' ) )[0];
		$ref          = (string) ( $block['ref'] ?? '' );
		$url          = $block['url'] ?? null;
		$block['url'] = null;
		if ( '' === $base || ( null === $owner && preg_match( '/^(?:compat\.document\.|[a-f0-9]{12}-p\d+-)/', $ref ) ) ) {
			return $block;
		}
		foreach ( $manifest['documents'] as $document ) {
			if ( ( $block['document_id'] ?? null ) !== $document['document_id'] || ( $block['document_revision'] ?? null ) !== $document['document_revision'] ||
				! in_array( $base, array_merge( array( $document['url'] ), $document['aliases'] ?? array() ), true ) ) {
				continue;
			}
			$matches     = array();
			$cited       = null;
			$file_models = array();
			foreach ( $manifest['products'] as $product ) {
				if ( ! in_array( $product['product_id'], $document['product_ids'], true ) ) {
					continue;
				}
				$ids           = array_merge( array( $product['product_id'] ), $product['published_locale_ids'] );
				$file_models[] = (string) ( $product['model'] ?? '' );
				if ( in_array( $owner, $ids, true ) ) {
					$cited = $product;
				}
				if ( array_intersect( $ids, $shown ) ) {
					$matches[ $product['product_id'] ] = $product;
				}
			}
			if ( ( null !== $owner && null === $cited ) || ( $shown && ! $matches ) ) {
				return $block;
			}
			$target = $cited;
			if ( $shown ) {
				$target = 1 === count( $matches ) ? reset( $matches ) : ( $matches[ $cited['product_id'] ?? 0 ] ?? null );
			}
			$label = (string) ( $block['label'] ?? '' );
			$pages = array();
			if ( preg_match( '/\s*(?:·|,)\s*(?:p{1,2}\.|S\.|pages?|Seiten?)\s*(\d+(?:\s*,\s*\d+)*)$/iu', $label, $m ) ) {
				$pages = array_map( 'trim', explode( ',', $m[1] ) );
				$label = trim( substr( $label, 0, -strlen( $m[0] ) ) );
			} elseif ( preg_match( '/#page=(\d+)$/D', $url, $m ) ) {
				$pages = array( $m[1] );
			}
			$title = trim( (string) ( $document['title'] ?? '' ) );
			$local = 'de' === $locale && ! empty( $document['title_de'] ) ? trim( $document['title_de'] ) : $title;
			$file  = rawurldecode( basename( $base ) );
			if ( $target ) {
				$name = (string) ( $target['model'] ?? '' );
				if ( '' === $name ) {
					$name = '' !== $title ? $title : $label;
				}
				$kind    = Materials::document_kind_label( in_array( $document['type'] ?? '', array( 'datasheet', 'manual', 'warranty', 'certificate', 'compatibility', 'brochure' ), true ) ? $document['type'] : 'document' );
				$purpose = Materials::document_purpose( $base, $locale, $file_models );
				$kind    = '' === $purpose ? $kind : $purpose;
				$lang    = strtoupper( $document['lang'] ?? '' );
				$text    = $name . ' · ' . $kind . ( '' !== $lang ? ' (' . $lang . ')' : '' );
			} else {
				$text = '' !== $local ? $local : Materials::document_kind_label( 'document' ) . ' · ' . $file;
			}
			$page_word            = 'de' === $locale ? 'S.' : ( count( $pages ) > 1 ? 'pp.' : 'p.' );
			$block['label']       = $text . ( $pages ? ' · ' . $page_word . "\u{00a0}" . implode( ', ', $pages ) : '' );
			$block['sourceTitle'] = '' !== $title ? $title : $label;
			$block['url']         = $url;
			return $block;
		}
		return $block;
	}
}
