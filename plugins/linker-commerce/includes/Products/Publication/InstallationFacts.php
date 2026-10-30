<?php
/**
 * Typed installation facts maintained in Woo product metadata.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/** Product metadata is the authority; this class only validates and projects it. */
final class InstallationFacts {

	public const META_KEY = '_linker_installation_facts';

	private const MAX_JSON_INTEGER = 9007199254740991;

	private const HANDLINGS = array(
		'manufacturer_included',
		'customer_supplied_required',
		'site_engineering_required',
	);

	private const DOMAINS = array(
		'ac',
		'pe',
		'battery_dc',
		'pv_dc',
		'communication',
	);

	/**
	 * Bind one stored row to the current product and associated document.
	 *
	 * @param  int                 $owner    Canonical Woo product.
	 * @param  array<string,mixed> $row      Stored row.
	 * @param  array<string,mixed> $manifest Current publication assembly.
	 * @return array<string,mixed> Projection; specification is an object so JSON keeps it as an object, including an empty one.
	 * @throws \RuntimeException When the typed row or evidence is invalid.
	 */
	public static function bind( int $owner, array $row, array $manifest ): array {
		$products      = array_column( $manifest['products'], null, 'product_id' );
		$documents     = array_column( $manifest['documents'], null, 'document_id' );
		$source        = $row['source'] ?? null;
		$document_id   = is_array( $source ) && is_string( $source['document_id'] ?? null ) ? $source['document_id'] : '';
		$document      = $documents[ $document_id ] ?? null;
		$quantity      = $row['quantity'] ?? null;
		$unit          = $row['unit'] ?? null;
		$handling      = $row['handling'] ?? null;
		$specification = array_key_exists( 'specification', $row ) ? $row['specification'] : array();
		$conditions    = array_key_exists( 'conditions', $row ) ? $row['conditions'] : array();
		$id            = $row['id'] ?? null;
		$basis         = $row['basis'] ?? null;

		if ( ! isset( $products[ $owner ] ) || ! is_string( $id ) || '' === trim( $id ) || ! self::localized( $row['label'] ?? null ) ) {
			throw new \RuntimeException( __( 'Installation facts need a current Woo product, item identity and English/German names.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		if ( ! in_array( $handling, self::HANDLINGS, true ) || ! is_string( $basis ) || '' === trim( $basis ) ) {
			throw new \RuntimeException( __( 'Each installation fact needs an explicit handling and basis.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		if ( ( ! is_int( $quantity ) && ! is_float( $quantity ) && null !== $quantity ) || ( is_float( $quantity ) && ! is_finite( $quantity ) ) || ! in_array( $unit, array( 'piece', 'pair', 'm' ), true ) || ( 'm' !== $unit && null !== $quantity && floor( (float) $quantity ) !== (float) $quantity ) ) {
			throw new \RuntimeException( __( 'Installation fact quantities need an explicit unit and a whole count for pieces or pairs.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		if ( null !== $quantity && ( (float) $quantity <= 0 || (float) $quantity > self::MAX_JSON_INTEGER ) ) {
			throw new \RuntimeException( __( 'Installation fact quantities must be positive and interoperable.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		$page       = is_array( $source ) ? ( $source['page'] ?? null ) : null;
		$quote      = is_array( $source ) ? ( $source['quote'] ?? null ) : null;
		$quote_text = is_string( $quote ) ? trim( $quote ) : '';
		if ( ! is_array( $document ) || ! in_array( $owner, $document['product_ids'], true ) || ! is_int( $page ) || $page < 1 || $page > self::MAX_JSON_INTEGER || ! self::valid_quote( $quote ) ) {
			throw new \RuntimeException( __( 'Installation evidence must be a current product document with its PDF page and exact quote.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		if ( ( $source['document_revision'] ?? null ) !== $document['document_revision'] || ( $source['blob_sha256'] ?? null ) !== $document['blob_sha256'] || ( $source['product_id'] ?? null ) !== $owner ) {
			throw new \RuntimeException( __( 'Installation facts are bound to exact current document bytes and version.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		if ( is_object( $specification ) ) {
			$specification = get_object_vars( $specification );
		}
		if ( ! is_array( $specification ) || ! self::specification( $specification ) ) {
			throw new \RuntimeException( __( 'Installation specifications must retain their typed terminal and requirement semantics.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}

		return array(
			'id'            => $id,
			'handling'      => $handling,
			'label'         => array(
				'en' => $row['label']['en'],
				'de' => $row['label']['de'],
			),
			'quantity'      => $quantity,
			'unit'          => $unit,
			'basis'         => $basis,
			'specification' => (object) $specification,
			'conditions'    => self::conditions( $conditions ),
			'source'        => array(
				'document_id'       => $document['document_id'],
				'document_revision' => $document['document_revision'],
				'blob_sha256'       => $document['blob_sha256'],
				'product_id'        => $owner,
				'page'              => $page,
				'url'               => 'https://de-linker.com' . (string) wp_parse_url( $document['url'], PHP_URL_PATH ),
				'quote'             => $quote_text,
			),
		);
	}

	/**
	 * One current projection. Invalid declarations withdraw the whole projection.
	 *
	 * @param  int                 $owner    Canonical product.
	 * @param  array<string,mixed> $manifest Same assembly used by the feed.
	 * @return array<string,mixed>|null
	 * @throws \RuntimeException When an invalid declaration must be withdrawn.
	 * @phpstan-impure Reads current Woo metadata, including after operator edits.
	 */
	public static function projection( int $owner, array $manifest ): ?array {
		$raw = get_post_meta( $owner, self::META_KEY, true );
		if ( '' === $raw || array() === $raw ) {
			return null;
		}
		try {
			if ( ! is_array( $raw ) || 1 !== ( $raw['schema_version'] ?? null ) || ! is_array( $raw['items'] ?? null ) ) {
				throw new \RuntimeException( __( 'Unsupported installation facts format.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
			}
			$items = array();
			foreach ( $raw['items'] as $row ) {
				if ( ! is_array( $row ) || ! is_string( $row['id'] ?? null ) || isset( $items[ $row['id'] ] ) ) {
					throw new \RuntimeException( __( 'Installation fact identities must be distinct.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
				}
				$item                 = self::bind( $owner, $row, $manifest );
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

	/**
	 * Whether both language labels are present.
	 *
	 * @param mixed $label Raw label.
	 */
	private static function localized( mixed $label ): bool {
		return is_array( $label ) && is_string( $label['en'] ?? null ) && is_string( $label['de'] ?? null ) && '' !== trim( $label['en'] ) && '' !== trim( $label['de'] );
	}

	/**
	 * Validate a bounded, typed specification envelope.
	 *
	 * @param  array<string,mixed> $value Raw specification.
	 */
	private static function specification( array $value ): bool {
		$allowed = array(
			'terminal_domain',
			'terminals',
			'recommended_conductor_mm2',
			'cable_od_mm',
			'minimum_voltage_v',
			'minimum_current_a',
			'rating_note',
		);
		if ( array_diff( array_keys( $value ), $allowed ) !== array() ) {
			return false;
		}
		$domain = $value['terminal_domain'] ?? null;
		if ( array_key_exists( 'terminal_domain', $value ) && ( ! is_string( $domain ) || ! in_array( $domain, self::DOMAINS, true ) ) ) {
			return false;
		}
		if ( array_key_exists( 'terminals', $value ) ) {
			$terminals = $value['terminals'];
			if ( ! is_array( $terminals ) || array_values( $terminals ) !== $terminals ) {
				return false;
			}
			if ( array_filter( $terminals, static fn ( mixed $terminal ): bool => ! is_string( $terminal ) || '' === trim( $terminal ) ) !== array() ) {
				return false;
			}
			$normalized = array_map( 'strval', $terminals );
			if ( count( $normalized ) !== count( array_unique( $normalized ) ) ) {
				return false;
			}
		}
		foreach ( array( 'recommended_conductor_mm2', 'cable_od_mm' ) as $interval ) {
			if ( array_key_exists( $interval, $value ) && ! self::interval( $value[ $interval ] ) ) {
				return false;
			}
		}
		foreach ( array( 'minimum_voltage_v', 'minimum_current_a' ) as $number ) {
			if ( array_key_exists( $number, $value ) && ! self::positive_number( $value[ $number ] ) ) {
				return false;
			}
		}
		return ! array_key_exists( 'rating_note', $value ) || is_string( $value['rating_note'] );
	}

	/**
	 * Validate a recommended range; it never becomes a named maximum.
	 *
	 * @param mixed $value Raw interval.
	 */
	private static function interval( mixed $value ): bool {
		return is_array( $value )
			&& 2 === count( $value )
			&& array_key_exists( 'low', $value )
			&& array_key_exists( 'high', $value )
			&& self::positive_number( $value['low'] )
			&& self::positive_number( $value['high'] )
			&& (float) $value['low'] <= (float) $value['high'];
	}

	/**
	 * Whether a value is a finite, positive JSON number.
	 *
	 * @param mixed $value Raw number.
	 */
	private static function positive_number( mixed $value ): bool {
		return ( is_int( $value ) || ( is_float( $value ) && is_finite( $value ) ) ) && (float) $value > 0;
	}

	/**
	 * Whether a source quote survives trimming and the feed's 2000-character bound.
	 *
	 * @param mixed $value Raw quote.
	 */
	private static function valid_quote( mixed $value ): bool {
		if ( ! is_string( $value ) ) {
			return false;
		}
		$quote = trim( $value );
		if ( '' === $quote ) {
			return false;
		}
		$length = function_exists( 'mb_strlen' ) ? mb_strlen( $quote, 'UTF-8' ) : strlen( $quote );
		return $length <= 2000;
	}

	/**
	 * Validate localized conditions without interpreting them.
	 *
	 * @param  mixed $value Raw conditions.
	 * @return list<array{en:string,de:string}>
	 * @throws \RuntimeException When a condition is not fully bilingual.
	 */
	private static function conditions( mixed $value ): array {
		if ( ! is_array( $value ) || array_values( $value ) !== $value ) {
			throw new \RuntimeException( __( 'Installation conditions need English and German text.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
		}
		$conditions = array();
		foreach ( $value as $condition ) {
			if ( ! self::localized( $condition ) ) {
				throw new \RuntimeException( __( 'Installation conditions need English and German text.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Native notices escape plain errors.
			}
			$conditions[] = array(
				'en' => $condition['en'],
				'de' => $condition['de'],
			);
		}
		return $conditions;
	}
}
