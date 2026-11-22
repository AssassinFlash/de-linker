<?php
/**
 * Display fields for the customer-facing Genie comparison.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Publication;

/** Assemble compared models and their current, documented storage pairings. */
final class ComparisonPresentation {
	/**
	 * Enrich only the interactive comparison. The model's ability response stays compact.
	 *
	 * @param array<int,array<string,mixed>> $columns Comparison columns.
	 * @param array<string,mixed>            $manifest Current publication.
	 * @param PublicationData                $publication Source and release reader.
	 * @param 'en'|'de'                      $lang Customer language.
	 * @return array{details:array<int,array<string,mixed>>,dependencies:list<int>}
	 */
	public static function read( array $columns, array $manifest, PublicationData $publication, string $lang ): array {
		$catalog    = new GetProduct( $publication );
		$details    = array();
		$related    = array();
		$candidates = array();
		$models     = array_column( $manifest['products'], 'model', 'product_id' );
		foreach ( $publication->pairs( $manifest ) as $pair ) {
			$candidates[ $pair['inverter_product_id'] ][ $pair['battery_product_id'] ] = true;
		}
		wc_load_cart();
		$draft = array();
		foreach ( WC()->cart->get_cart() as $line ) {
			if ( (int) $line['quantity'] > 0 ) {
				$draft[ Publication::canonical_id( (int) $line['product_id'] ) ] = true;
			}
		}

		foreach ( $columns as $column ) {
			$id       = (int) $column['product_id'];
			$product  = $catalog->customer_fields( $id, $lang, $manifest );
			$commerce = $product['commerce'];
			$file     = null;
			foreach ( $product['documents'] as $doc ) {
				if ( 'datasheet' !== $doc['type'] ) {
					continue;
				}
				if ( null === $file || strtolower( $doc['lang'] ) === $lang ) {
					$file = array(
						'title' => $doc['title'],
						'url'   => $doc['url'],
					);
				}
				if ( strtolower( $doc['lang'] ) === $lang ) {
					break;
				}
			}
			$storage = array();
			foreach ( array_keys( $candidates[ Publication::canonical_id( $id ) ] ?? array() ) as $battery ) {
				$release = $publication->pairing( $id, (int) $battery, $manifest );
				if ( null === $release || 'not_released' === $release['verdict'] ) {
					continue;
				}
				$parts = array_column( $release['accessories'], 'product_id' );
				if ( in_array( $battery, $parts, true ) ) {
					continue;
				}
				$model = ProductText::term_name( (int) $battery, 'pa_model' );
				if ( null === $model ) {
					continue;
				}
				$storage[] = array(
					'model'       => $model,
					'conditions'  => array_column( $release['conditions'], $lang ),
					'accessories' => array_values( array_filter( array_map( static fn( int $part ): string => (string) ( $models[ $part ] ?? '' ), $parts ) ) ),
					'verdict'     => $release['verdict'],
				);
				$related[] = (int) $battery;
				array_push( $related, ...$parts, ...array_column( $release['documents'], 'product_id' ) );
			}
			$details[ $id ] = array(
				'model'        => $product['model'],
				'brand'        => $product['brand'],
				'series'       => $product['series'],
				'sku'          => $column['sku'],
				'image'        => $column['image'],
				'in_stock'     => $commerce['in_stock'],
				'in_draft'     => isset( $draft[ Publication::canonical_id( $id ) ] ),
				'price_line'   => $commerce['price_line'] ?? '',
				'price_reason' => $commerce['price_reason'] ?? null,
				'datasheet'    => $file,
				'storage'      => $storage,
			);
		}
		return array(
			'details'      => $details,
			'dependencies' => array_values( array_unique( $related ) ),
		);
	}
}
