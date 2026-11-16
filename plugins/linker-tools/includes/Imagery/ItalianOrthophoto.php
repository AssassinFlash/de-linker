<?php
/**
 * Public HTTPS tile relay for Italy's open national 50 cm aerial orthophoto.
 *
 * The Italian Ministry of the Environment (Geoportale Nazionale / PCN) serves
 * `ortofoto_colore_12` over ArcGIS MapServer export, whose HTTPS endpoint
 * redirects with HTTP 301 to plaintext HTTP without CORS headers. Browser maps
 * on an HTTPS origin refuse Mixed Content downgrades, so this bounded read-only
 * route validates an EPSG:3857 tile bounding box within Italy and relays the
 * verified JPEG over same-origin HTTPS.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Imagery;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Fixed-upstream, numeric-bbox-only read relay for PCN orthophoto tiles. */
final class ItalianOrthophoto {

	public const NAMESPACE = 'linker/v1';
	public const ROUTE     = '/imagery/it';
	public const UPSTREAM  = 'http://www.pcn.minambiente.it/arcgis/rest/services/immagini/ortofoto_colore_12/MapServer/export';
	public const MAX_BYTES = 1048576;
	public const TILE_PX   = 256;

	/** A 256x256 photographic tile is never this small; a blank one is 1.6 KB. */
	private const BLANK_BYTES = 2500;

	/** Exact EPSG:3857 envelope covering Italy (including Sicily, Sardinia and Lampedusa). */
	private const MIN_X    = 500000.0;
	private const MAX_X    = 2300000.0;
	private const MIN_Y    = 4100000.0;
	private const MAX_Y    = 6100000.0;
	private const MAX_SPAN = 200000.0;

	/**
	 * Optional HTTP test seam.
	 *
	 * @param (callable(string,array<string,mixed>):(array<string,mixed>|WP_Error))|null $fetch Native HTTP getter.
	 */
	public function __construct( private mixed $fetch = null ) {}

	/** Register the public read-only tile endpoint and binary output hook. */
	public function register(): void {
		add_action( 'rest_api_init', array( $this, 'register_routes' ) );
		add_filter( 'rest_pre_serve_request', array( $this, 'serve' ), 20, 4 );
	}

	/** Declare GET /wp-json/linker/v1/imagery/it?bbox={bbox-epsg-3857}. */
	public function register_routes(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'tile' ),
				'permission_callback' => '__return_true',
			)
		);
	}

	/**
	 * Validate the requested EPSG:3857 bounding box and fetch one 256x256 JPEG.
	 *
	 * @param WP_REST_Request $request Incoming tile GET request.
	 * @return WP_REST_Response|WP_Error Verified JPEG response or bounded error.
	 */
	public function tile( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$bbox = $request->get_param( 'bbox' );
		$norm = is_string( $bbox ) ? self::normalise_bbox( $bbox ) : null;
		if ( null === $norm ) {
			return new WP_Error( 'linker_invalid_bbox', 'Invalid EPSG:3857 bounding box.', array( 'status' => 400 ) );
		}
		$url  = self::UPSTREAM . '?bbox=' . rawurlencode( $norm ) . '&bboxSR=3857&imageSR=3857&size=' . self::TILE_PX . ',' . self::TILE_PX . '&format=jpeg&f=image';
		$args = array(
			'timeout'             => 15.0,
			'redirection'         => 0,
			'sslverify'           => false,
			'limit_response_size' => self::MAX_BYTES + 1,
			'headers'             => array(
				'Accept' => 'image/jpeg',
			),
		);
		$raw  = is_callable( $this->fetch ) ? ( $this->fetch )( $url, $args ) : wp_remote_get( $url, $args );
		if ( is_wp_error( $raw ) ) {
			return new WP_Error( 'linker_imagery_unavailable', 'Upstream orthophoto service unavailable.', array( 'status' => 502 ) );
		}
		$status     = (int) wp_remote_retrieve_response_code( $raw );
		$raw_header = wp_remote_retrieve_header( $raw, 'content-type' );
		$type       = is_string( $raw_header ) ? $raw_header : '';
		$body       = (string) wp_remote_retrieve_body( $raw );
		if (
			200 !== $status ||
			! str_starts_with( strtolower( trim( $type ) ), 'image/jpeg' ) ||
			strlen( $body ) < 4 ||
			strlen( $body ) > self::MAX_BYTES ||
			! str_starts_with( $body, "\xff\xd8\xff" ) ||
			strlen( $body ) < self::BLANK_BYTES ||
			! self::is_full_tile( $body )
		) {
			return new WP_Error( 'linker_imagery_invalid_reply', 'Upstream orthophoto reply was not a valid JPEG tile.', array( 'status' => 502 ) );
		}
		$response = new WP_REST_Response( $body, 200 );
		$response->header( 'Content-Type', 'image/jpeg' );
		$response->header( 'Cache-Control', 'public, max-age=604800, immutable' );
		$response->header( 'X-Content-Type-Options', 'nosniff' );
		return $response;
	}

	/**
	 * Output raw JPEG bytes instead of JSON-encoding the response string.
	 *
	 * @param mixed           $served   Prior serve flag.
	 * @param mixed           $response Prepared REST response.
	 * @param WP_REST_Request $request  Current REST request.
	 * @param mixed           $server   REST server.
	 * @return bool True when raw JPEG bytes were emitted.
	 */
	public function serve( mixed $served, mixed $response, WP_REST_Request $request, mixed $server ): bool {
		unset( $server );
		if ( $served || '/' . self::NAMESPACE . self::ROUTE !== strtolower( $request->get_route() ) ) {
			return (bool) $served;
		}
		if ( $response instanceof WP_REST_Response && 'image/jpeg' === ( $response->get_headers()['Content-Type'] ?? '' ) && is_string( $response->get_data() ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- verified binary JPEG tile with nosniff header.
			echo $response->get_data();
			return true;
		}
		return (bool) $served;
	}

	/**
	 * Whether a JPEG is a complete 256x256 tile rather than a blank rectangle.
	 *
	 * The Italian service answers a valid but empty 256x256 JPEG (measured
	 * 2026-11-16: 1,651 bytes, pure white) at some zoom levels instead of
	 * failing. Relaying that would put a white square on the map — and it is
	 * cached for a week, so the gap would persist long after the upstream
	 * recovered. A blank tile is treated as no imagery, which is what the
	 * screen already knows how to explain.
	 *
	 * @param string $body Verified JPEG bytes.
	 * @return bool True when the frame is a full-size photograph.
	 */
	private static function is_full_tile( string $body ): bool {
		$size = self::frame_size( $body );
		return null !== $size && self::TILE_PX === $size[0] && self::TILE_PX === $size[1];
	}

	/**
	 * The pixel size declared by a JPEG's start-of-frame segment.
	 *
	 * @param string $body JPEG bytes.
	 * @return array{0:int,1:int}|null Width and height, or null when unreadable.
	 */
	private static function frame_size( string $body ): ?array {
		$length = strlen( $body );
		$offset = 2;
		while ( $offset + 9 < $length ) {
			if ( "\xff" !== $body[ $offset ] ) {
				++$offset;
				continue;
			}
			$marker = \ord( $body[ $offset + 1 ] );
			if ( 0xD8 === $marker || 0xD9 === $marker || 0x01 === $marker || ( $marker >= 0xD0 && $marker <= 0xD7 ) ) {
				$offset += 2;
				continue;
			}
			$segment = ( \ord( $body[ $offset + 2 ] ) << 8 ) | \ord( $body[ $offset + 3 ] );
			if ( $marker >= 0xC0 && $marker <= 0xC3 ) {
				if ( $offset + 9 >= $length ) {
					return null;
				}
				$height = ( \ord( $body[ $offset + 5 ] ) << 8 ) | \ord( $body[ $offset + 6 ] );
				$width  = ( \ord( $body[ $offset + 7 ] ) << 8 ) | \ord( $body[ $offset + 8 ] );
				return array( $width, $height );
			}
			if ( $segment < 2 ) {
				return null;
			}
			$offset += 2 + $segment;
		}
		return null;
	}

	/**
	 * Parse and bound-check four comma-separated EPSG:3857 coordinates.
	 *
	 * @param string $raw Raw bbox query parameter.
	 * @return string|null Canonical bbox string or null when outside Italy/bounds.
	 */
	public static function normalise_bbox( string $raw ): ?string {
		$parts = explode( ',', trim( $raw ) );
		if ( 4 !== count( $parts ) ) {
			return null;
		}
		$coords = array();
		foreach ( $parts as $part ) {
			$trimmed = trim( $part );
			if ( 1 !== preg_match( '/\A-?\d{1,8}(?:\.\d{1,10})?\z/', $trimmed ) ) {
				return null;
			}
			$value = (float) $trimmed;
			if ( ! is_finite( $value ) ) {
				return null;
			}
			$coords[] = $value;
		}
		list( $min_x, $min_y, $max_x, $max_y ) = $coords;
		if (
			$min_x >= $max_x ||
			$min_y >= $max_y ||
			( $max_x - $min_x ) > self::MAX_SPAN ||
			( $max_y - $min_y ) > self::MAX_SPAN ||
			$min_x < self::MIN_X ||
			$max_x > self::MAX_X ||
			$min_y < self::MIN_Y ||
			$max_y > self::MAX_Y
		) {
			return null;
		}
		return sprintf( '%.3f,%.3f,%.3f,%.3f', $min_x, $min_y, $max_x, $max_y );
	}
}
