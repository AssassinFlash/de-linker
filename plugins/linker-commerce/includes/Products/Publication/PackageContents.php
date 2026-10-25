<?php
/**
 * Cited contents supplied with one native Woo sales unit.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/**
 * Product metadata is the authority; this class only binds and projects it.
 */
final class PackageContents {


	public const META_KEY = '_linker_package_contents';

	/**
	 * Validate one item against the product's current associated document bytes.
	 *
	 * @param  int                 $owner    Canonical Woo product.
	 * @param  array<string,mixed> $row      Stored or explicitly confirmed entry.
	 * @param  array<string,mixed> $manifest Current publication assembly.
	 * @param  bool                $bind     Confirm the current document version.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When identity, quantity or evidence is invalid.
	 */
	public static function bind( int $owner, array $row, array $manifest, bool $bind ): array {
		$products = array_column( $manifest['products'], null, 'product_id' );
		$docs     = array_column( $manifest['documents'], null, 'document_id' );
		$source   = $row['source'] ?? null;
		$doc      = is_array( $source ) && is_string( $source['document_id'] ?? null ) ? ( $docs[ $source['document_id'] ] ?? null ) : null;
		$quantity = $row['quantity'] ?? null;
		$unit     = $row['unit'] ?? null;
		if ( ! isset( $products[ $owner ] ) || ! is_string( $row['id'] ?? null ) || '' === trim( $row['id'] ) || ! is_array( $row['label'] ?? null ) || ! is_string( $row['label']['en'] ?? null ) || ! is_string( $row['label']['de'] ?? null ) || '' === trim( $row['label']['en'] ) || '' === trim( $row['label']['de'] ) ) {
			throw new \RuntimeException( __( 'A current Woo product, item identity and English/German names are required.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		// The integer ceiling is the shared browser transport bound, not a physical limit.
		if ( ( ! is_int( $quantity ) && ! is_float( $quantity ) ) || ! is_finite( (float) $quantity ) || $quantity <= 0 || $quantity > 9007199254740991 || ! in_array( $unit, array( 'piece', 'pair', 'm' ), true ) || ( 'm' !== $unit && floor( (float) $quantity ) !== (float) $quantity ) || ! in_array( $row['role'] ?? 'other', array( 'other', 'meter', 'backup', 'parallel_controller' ), true ) ) {
			throw new \RuntimeException( __( 'Package quantities need a positive value, an explicit unit and a whole count for pieces or pairs.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		if ( ! is_array( $doc ) || ! in_array( $owner, $doc['product_ids'], true ) || ! is_int( $source['page'] ?? null ) || $source['page'] < 1 || $source['page'] > 9007199254740991 ) {
			throw new \RuntimeException( __( 'Package evidence must be a current document of this product with its PDF page.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		if ( ! $bind && ( ( $source['document_revision'] ?? null ) !== $doc['document_revision'] || ( $source['blob_sha256'] ?? null ) !== $doc['blob_sha256'] || ( $source['product_id'] ?? null ) !== $owner ) ) {
			throw new \RuntimeException( __( 'Package contents require confirmation against these document bytes and version.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		return array(
			'id'       => $row['id'],
			'label'    => array(
				'en' => $row['label']['en'],
				'de' => $row['label']['de'],
			),
			'quantity' => $quantity,
			'unit'     => $unit,
			'role'     => $row['role'] ?? 'other',
			'source'   => array(
				'document_id'       => $doc['document_id'],
				'document_revision' => $doc['document_revision'],
				'blob_sha256'       => $doc['blob_sha256'],
				'product_id'        => $owner,
				'page'              => $source['page'],
				'url'               => 'https://de-linker.com' . (string) wp_parse_url( $doc['url'], PHP_URL_PATH ),
			),
		);
	}

	/**
	 * One current product projection. Invalid contents never become partial facts.
	 *
	 * @param  int                 $owner    Canonical product.
	 * @param  array<string,mixed> $manifest Same assembly used by the feed.
	 * @return array<string,mixed>|null Null retains the existing no-data contract.
	 * @throws \RuntimeException Handled internally to withdraw the entire invalid contents projection.
	 */
	public static function projection( int $owner, array $manifest ): ?array {
		$raw = get_post_meta( $owner, self::META_KEY, true );
		if ( '' === $raw || array() === $raw ) {
			return null;
		}
		try {
			if ( ! is_array( $raw ) || 1 !== ( $raw['schema_version'] ?? null ) || ! is_array( $raw['items'] ?? null ) ) {
				throw new \RuntimeException( __( 'Unsupported package contents format.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
			}
			$items = array();
			foreach ( $raw['items'] as $row ) {
				if ( ! is_array( $row ) || ! is_string( $row['id'] ?? null ) || isset( $items[ $row['id'] ] ) ) {
					throw new \RuntimeException( __( 'Package item identities must be distinct.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
				}
				$item                 = self::bind( $owner, $row, $manifest, false );
				$items[ $item['id'] ] = $item;
			}
			return array(
				'status' => 'documented',
				'items'  => array_values( $items ),
			);
		} catch ( \RuntimeException $error ) {
			return array(
				'status' => 'unresolved',
				'items'  => array(),
			);
		}
	}
}
