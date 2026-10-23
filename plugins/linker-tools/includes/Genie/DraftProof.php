<?php
/**
 * Server-signed product-list actions from a freshly checked Genie answer.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Genie;

use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Protection\Identity;
use WP_Error;

/** Tokens grant only the exact normalized list and current dependency set. */
class DraftProof {
	/**
	 * Optional current-source, identity and clock seams for fixtures.
	 *
	 * @param callable():array<string,mixed>|null $manifest Woo manifest reader.
	 * @param callable():(string|WP_Error)|null   $binding Existing private identity.
	 * @param callable():int|null                 $clock Current time.
	 */
	public function __construct( private $manifest = null, private $binding = null, private $clock = null ) {}

	/**
	 * Sign live artifacts only; the unsigned stream remains the stored history.
	 *
	 * @param string              $stream Server-normalized SSE.
	 * @param array<string,mixed> $dependencies Complete turn dependencies.
	 */
	public function stream( string $stream, array $dependencies ): string|WP_Error {
		$products = $dependencies['products'] ?? array();
		if ( ! is_array( $products ) || array() === $products ) {
			return $stream;
		}
		try {
			$manifest = is_callable( $this->manifest ) ? ( $this->manifest )() : Publication::manifest();
		} catch ( \RuntimeException $error ) {
			return self::unavailable();
		}
		$owner = $this->owner();
		if ( $owner instanceof WP_Error || true !== Publication::validate_manifest( $dependencies, $manifest )['valid'] ) {
			return $stream;
		}
		$events = explode( "\n\n", $stream );
		foreach ( $events as &$event ) {
			if ( 1 !== preg_match( '/^event: block$/m', $event ) || 1 !== preg_match( '/^data: (.+)$/m', $event, $data ) ) {
				continue;
			}
			$block = json_decode( $data[1], true );
			if ( ! is_array( $block ) ) {
				continue;
			}
			if ( 'cards' === ( $block['type'] ?? '' ) ) {
				$block['draft_proofs'] = array();
				foreach ( (array) ( $block['product_ids'] ?? array() ) as $id ) {
					if ( is_int( $id ) ) {
						$token = $this->mint(
							array(
								array(
									'product_id' => $id,
									'quantity'   => 1,
								),
							),
							$dependencies,
							$manifest,
							$owner
						);
						if ( '' !== $token ) {
							$block['draft_proofs'][ (string) $id ] = $token;
						}
					}
				}
			} elseif ( 'parts' === ( $block['type'] ?? '' ) && is_array( $block['add']['items'] ?? null ) ) {
				$block['add']['proof'] = $this->mint( $block['add']['items'], $dependencies, $manifest, $owner );
			} else {
				continue;
			}
			$event = str_replace( $data[0], 'data: ' . (string) wp_json_encode( $block ), $event );
		}
		unset( $event );
		return implode( "\n\n", $events );
	}

	/**
	 * Verify HMAC, browser/account binding, lifetime and all current dependencies.
	 *
	 * @phpstan-impure Every call observes current identity and source, even within one request.
	 *
	 * @param string $token Signed artifact proof, never editable lines.
	 * @return array<string,mixed>|WP_Error Exact trusted list snapshot.
	 */
	public function verify( string $token ): array|WP_Error {
		$parts = explode( '.', $token );
		if ( 2 !== count( $parts ) || 1 !== preg_match( '/\A[0-9a-f]{64}\z/', $parts[1] ) || ! hash_equals( hash_hmac( 'sha256', 'genie-draft|' . $parts[0], wp_salt( 'nonce' ) ), $parts[1] ) ) {
			return self::changed();
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Authenticated JSON, never executable data.
		$decoded = base64_decode( strtr( $parts[0], '-_', '+/' ), true );
		$data    = false === $decoded ? null : json_decode( $decoded, true );
		$owner   = $this->owner();
		$now     = $this->now();
		if ( $owner instanceof WP_Error || ! is_array( $data ) || 1 !== ( $data['version'] ?? null ) || ! is_string( $data['binding'] ?? null ) || ! hash_equals( $owner, $data['binding'] ) || ! is_int( $data['issued'] ?? null ) || ! is_int( $data['expires'] ?? null ) || $data['issued'] > $now || $data['expires'] <= $now || DAY_IN_SECONDS !== $data['expires'] - $data['issued'] || ! is_array( $data['result'] ?? null ) || array() === DesignProof::items( $data['result'] ) ) {
			return self::changed();
		}
		$result = $data['result'];
		try {
			$manifest = is_callable( $this->manifest ) ? ( $this->manifest )() : Publication::manifest();
		} catch ( \RuntimeException $error ) {
			return self::unavailable();
		}
		if ( true !== Publication::validate_manifest( (array) ( $result['publication'] ?? array() ), $manifest )['valid'] ) {
			return self::changed();
		}
		return $result;
	}

	/**
	 * Sign exactly the normalized server artifact; unknown rows are refused.
	 *
	 * @param array<array-key,mixed> $items Service-normalized list.
	 * @param array<string,mixed>    $dependencies Complete turn dependencies.
	 * @param array<string,mixed>    $manifest Current Woo source.
	 * @param string                 $owner Private identity binding.
	 */
	private function mint( array $items, array $dependencies, array $manifest, string $owner ): string {
		$lines = array();
		foreach ( $items as $item ) {
			if ( ! is_array( $item ) || ! is_int( $item['product_id'] ?? null ) || ! is_int( $item['quantity'] ?? null ) || $item['quantity'] < 1 ) {
				return '';
			}
			$id      = $item['product_id'];
			$product = null;
			foreach ( $manifest['products'] as $candidate ) {
				if ( $id === $candidate['product_id'] || in_array( $id, $candidate['published_locale_ids'], true ) ) {
					$product = $candidate;
					break;
				}
			}
			$scope     = is_array( $dependencies['products'] ?? null ) ? $dependencies['products'] : array();
			$permitted = null !== $product && in_array(
				array(
					'product_id'       => $product['product_id'],
					'product_revision' => $product['product_revision'],
				),
				$scope,
				true
			);
			if ( ! $permitted ) {
				return '';
			}
			$lines[] = array(
				'product'  => array(
					'id'    => $id,
					'brand' => (string) ( $product['brand'] ?? '' ),
					'model' => (string) ( $product['model'] ?? $product['title'] ?? '' ),
				),
				'quantity' => $item['quantity'],
			);
		}
		if ( array() === $lines ) {
			return '';
		}
		$result                          = array(
			'kind'        => 'genie',
			'selected'    => array( 'lines' => $lines ),
			'publication' => $dependencies,
		);
		$result['selection_fingerprint'] = Publication::revision( $result );
		$now                             = $this->now();
		$data                            = array(
			'version' => 1,
			'issued'  => $now,
			'expires' => $now + DAY_IN_SECONDS,
			'binding' => $owner,
			'result'  => $result,
		);
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- URL-safe authenticated JSON, never executable data.
		$body = rtrim( strtr( base64_encode( (string) wp_json_encode( $data ) ), '+/', '-_' ), '=' );
		return $body . '.' . hash_hmac( 'sha256', 'genie-draft|' . $body, wp_salt( 'nonce' ) );
	}

	/** Current private identity; native admission owns its cookie. */
	private function owner(): string|WP_Error {
		if ( is_callable( $this->binding ) ) {
			return ( $this->binding )();
		}
		$identity = Identity::current();
		return $identity instanceof WP_Error ? $identity : $identity->binding();
	}

	/** Existing receipt lifetime and identity are evaluated with one clock. */
	private function now(): int {
		return is_callable( $this->clock ) ? ( $this->clock )() : time();
	}

	/** Current authority could not be read; it does not prove withdrawal. */
	private static function unavailable(): WP_Error {
		return new WP_Error( 'linker_publication_unavailable', __( 'The current product data could not be checked. Your entries are still here.', 'linker-tools' ), array( 'status' => 503 ) );
	}

	/** Reuse the configured action's stale state without exposing draft facts. */
	public static function changed(): WP_Error {
		return new WP_Error( 'linker_solution_changed', __( 'Genie needs to check this product list again before it can be saved or added.', 'linker-tools' ), array( 'status' => 409 ) );
	}
}
