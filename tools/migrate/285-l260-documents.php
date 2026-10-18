<?php
/**
 * The WordPress side of tools/migrate/285-l260-documents.py.
 *
 * Reads, or writes, the document list of product 2003 (ticket #285 C2). The
 * payload is base64 JSON: {action: read|write, product: int, meta_key: string,
 * documents?: array}. Read prints base64 JSON of the site URL, the current
 * document list and the fields the migration must not change. Write stores
 * the new list with the site's own encoding.
 *
 * @package Linker\Migrate
 */

// No declare(strict_types=1): `wp eval-file -` rejects it with a fatal error.
$request = json_decode( (string) base64_decode( '285-l260-documents-payload' ), true );

$product_id = (int) ( $request['product'] ?? 0 );
$meta_key   = (string) ( $request['meta_key'] ?? '_linker_documents' );
$product    = function_exists( 'wc_get_product' ) ? wc_get_product( $product_id ) : false;

$documents = static function () use ( $product_id, $meta_key ): array {
	$raw = (string) get_post_meta( $product_id, $meta_key, true );
	if ( '' === $raw ) {
		return array();
	}
	$decoded = json_decode( $raw, true );
	return is_array( $decoded ) ? $decoded : array();
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
	update_post_meta(
		$product_id,
		$meta_key,
		wp_slash( (string) wp_json_encode( $request['documents'] ?? array(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
	);
}

echo '@@285-l260-documents@@' . base64_encode(
	(string) wp_json_encode(
		array(
			'site'      => home_url( '/' ),
			'product'   => $product_id,
			'documents' => $documents(),
			'fields'    => $fields(),
		)
	)
), "\n";
