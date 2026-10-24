<?php
/**
 * Immutable current-document fixtures for presentation-only tests.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use Linker\Commerce\Storefront\ProductView;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Gating\CommerceState;

/** Source permissions and byte validation have separate real-WordPress fixtures. */
trait PublishedDocumentView {
	/** A current allowed view built from the test's existing document rows. */
	private function published_document_view(): ProductView {
		return new ProductView(
			new CommerceState(),
			static function ( int $id ): array {
				$rows = array();
				foreach ( Materials::acf( $id )['downloads'] ?? array() as $download ) {
					$url = wp_get_attachment_url( $download['download_file'] );
					if ( ! is_string( $url ) ) {
						continue;
					}
					$rows[] = array(
						'title'    => $download['download_title'] ?? '',
						'url'      => $url,
						'type'     => $download['download_type'] ?? '',
						'role'     => $download['download_role'] ?? '',
						'language' => $download['download_language'] ?? '',
					);
				}
				return $rows;
			}
		);
	}
}
