<?php
/**
 * The WordPress side of tools/migrate/285-l260-documents.py.
 *
 * Reads, or writes, product 2003's document sources (ticket #285 C2). The
 * payload is base64 JSON: {action: read|write, product: int, meta_key: string,
 * download_keys: string[], fields?: [{kind: documents|downloads, meta_key,
 * value}]}. Read prints base64 JSON of the site URL, the document list, every
 * downloads array, and the fields the migration must not change. Write stores
 * a document list, or replaces the downloads array inside an ACF JSON while
 * preserving its other keys, with the site's own encoding.
 *
 * @package Linker\Migrate
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets the request JSON sit in the single-quoted literal 285-l260-documents.py writes into this file.
	$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );

	$product_id    = (int) ( $request['product'] ?? 0 );
	$documents_key = (string) ( $request['meta_key'] ?? '_linker_documents' );
	$download_keys = array();
	foreach ( is_array( $request['download_keys'] ?? null ) ? $request['download_keys'] : array() as $key ) {
		$download_keys[] = (string) $key;
	}
	$product = function_exists( 'wc_get_product' ) ? wc_get_product( $product_id ) : false;

	$documents = static function () use ( $product_id, $documents_key ): array {
		$raw = (string) get_post_meta( $product_id, $documents_key, true );
		if ( '' === $raw ) {
			return array();
		}
		$decoded = json_decode( $raw, true );
		return is_array( $decoded ) ? $decoded : array();
	};

	$downloads = static function ( string $key ) use ( $product_id ): ?array {
		$raw = (string) get_post_meta( $product_id, $key, true );
		if ( '' === $raw ) {
			return null;
		}
		$decoded = json_decode( $raw, true );
		return is_array( $decoded ) && is_array( $decoded['downloads'] ?? null )
			? $decoded['downloads'] : null;
	};

	$fields = static function () use ( $product ): array {
		return array(
			'name'           => $product ? $product->get_name() : '',
			'sku'            => $product ? $product->get_sku() : '',
			'status'         => $product ? $product->get_status() : '',
			'price'          => $product ? $product->get_price() : '',
			'regular_price'  => $product ? $product->get_regular_price() : '',
			'sale_price'     => $product ? $product->get_sale_price() : '',
			'stock_status'   => $product ? $product->get_stock_status() : '',
			'stock_quantity' => $product ? $product->get_stock_quantity() : null,
		);
	};

	if ( 'write' === ( $request['action'] ?? '' ) ) {
		foreach ( is_array( $request['fields'] ?? null ) ? $request['fields'] : array() as $field ) {
			$key = (string) ( $field['meta_key'] ?? '' );
			if ( '' === $key ) {
				continue;
			}
			if ( 'documents' === ( $field['kind'] ?? '' ) ) {
				update_post_meta(
					$product_id,
					$key,
					wp_slash( (string) wp_json_encode( $field['value'] ?? array(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
				);
				continue;
			}
			$raw     = (string) get_post_meta( $product_id, $key, true );
			$decoded = '' === $raw ? array() : json_decode( $raw, true );
			if ( ! is_array( $decoded ) ) {
				$decoded = array();
			}
			$decoded['downloads'] = $field['value'] ?? array();
			update_post_meta(
				$product_id,
				$key,
				wp_slash( (string) wp_json_encode( $decoded, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
			);
		}
	}

	$downloads_out = array();
	foreach ( $download_keys as $key ) {
		$downloads_out[ $key ] = $downloads( $key );
	}

	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped, WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- The answer is base64 JSON for the migration script, not HTML.
	echo '@@285-l260-documents@@' . base64_encode(
		(string) wp_json_encode(
			array(
				'site'      => home_url( '/' ),
				'product'   => $product_id,
				'documents' => $documents(),
				'downloads' => $downloads_out,
				'fields'    => $fields(),
			)
		)
	), "\n";
} )( '285-l260-documents-payload' );
