<?php
/**
 * Display fields for the customer-facing Genie comparison.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Compatibility;
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
		$details    = array();
		$related    = array();
		$candidates = array();
		foreach ( Compatibility::pairs( $manifest ) as $pair ) {
			$candidates[ $pair['inverter_product_id'] ][ $pair['battery_product_id'] ] = true;
		}
		foreach ( $columns as $column ) {
			$id       = (int) $column['product_id'];
			$commerce = ProductCommerce::of( $id, null, $lang );
			$file     = null;
			foreach ( $publication->documents( $id, $manifest ) as $doc ) {
				if ( 'datasheet' !== $doc['type'] ) {
					continue;
				}
				if ( null === $file || $lang === strtolower( $doc['lang'] ) ) {
					$file = array(
						'title' => $doc['title'],
						'url'   => $doc['url'],
					);
				}
				if ( $lang === strtolower( $doc['lang'] ) ) {
					break;
				}
			}
			$storage = array();
			foreach ( array_keys( $candidates[ Publication::canonical_id( $id ) ] ?? array() ) as $battery ) {
				$release = $publication->pairing( $id, (int) $battery, $manifest );
				if ( null === $release || 'not_released' === $release['verdict'] ) {
					continue;
				}
				$model = ProductText::term_name( (int) $battery, 'pa_model' );
				if ( null === $model ) {
					continue;
				}
				$storage[] = array(
					'model'       => $model,
					'conditions'  => array_column( $release['conditions'], $lang ),
					'accessories' => array_column( $release['accessories'], 'model' ),
					'verdict'     => $release['verdict'],
				);
				$related[] = (int) $battery;
				array_push( $related, ...array_column( $release['accessories'], 'product_id' ), ...array_column( $release['documents'], 'product_id' ) );
			}
			$details[ $id ] = array(
				'model'        => ProductText::term_name( $id, 'pa_model' ),
				'brand'        => ProductText::term_name( $id, 'pa_brand' ),
				'series'       => ProductText::term_name( $id, 'pa_series' ),
				'sku'          => $column['sku'],
				'image'        => $column['image'],
				'in_stock'     => $commerce['in_stock'],
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
