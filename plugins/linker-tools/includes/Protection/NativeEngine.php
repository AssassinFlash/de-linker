<?php
/**
 * Account-owned saved-design recomputation uses the same sizing ledger.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Fingerprint;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use WP_Error;
use WP_REST_Response;

/** Native ability authentication is already checked before this trusted seam. */
final class NativeEngine {
	/**
	 * Read the actual running snapshot through the shared private service seam.
	 *
	 * @param EngineVersion $version Trusted live-version reader.
	 */
	public function __construct( private readonly EngineVersion $version = new EngineVersion() ) {}

	/** Register a server-only filter; the public proxy cannot choose this seam. */
	public function register(): void {
		add_filter( 'linker_tools_engine_request', array( $this, 'request' ), 10, 3 );
	}

	/**
	 * Return the existing ability's native HTTP tuple, with no second source of design data.
	 *
	 * @phpstan-impure
	 *
	 * @param mixed  $previous Earlier safe refusal.
	 * @param string $url Server-selected engine URL.
	 * @param string $body Server-validated stored design input.
	 * @return array{0:int,1:string}|WP_Error Native result.
	 */
	public function request( mixed $previous, string $url, string $body ): array|WP_Error {
		if ( ( ! is_user_logged_in() && ! str_ends_with( $url, '/selection/validate' ) ) || ! class_exists( Configuration::class ) ) {
			return self::failure();
		}
		$mode = Configuration::current()->mode;
		if ( ! in_array( $mode, array( 'off', 'observe', 'enforce' ), true ) ) {
			return self::failure();
		}
		if ( is_user_logged_in() ) {
			$account  = Identity::account( get_current_user_id() );
			$identity = new Identity( hash( 'sha256', 'ability|' . $account ), $account );
		} else {
			$identity = Identity::current();
			if ( is_wp_error( $identity ) ) {
				return $identity;
			}
			$account = $identity->browser;
		}
		$input   = json_decode( $body, true );
		$version = $this->version->current();
		if ( is_wp_error( $version ) ) {
			return $version;
		}
		if ( ! is_array( $input ) || ( 'enforce' === $mode && ( strlen( $body ) > 6 * 1024 * 1024 || '' === $version ) ) || ! in_array( $url, array( rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/design/residential', rtrim( (string) get_option( 'linker_engine_url', '' ), '/' ) . '/selection/validate' ), true ) ) {
			return self::failure();
		}
		$fingerprint = 'enforce' === $mode ? Fingerprint::make(
			$identity,
			'design',
			array(
				'input'   => $input,
				'version' => $version,
				'day'     => intdiv( time(), DAY_IN_SECONDS ),
			)
		) : '';
		if ( is_wp_error( $fingerprint ) ) {
			return $fingerprint;
		}
		$id              = substr( $fingerprint, 0, 8 ) . '-' . substr( $fingerprint, 8, 4 ) . '-4' . substr( $fingerprint, 13, 3 ) . '-a' . substr( $fingerprint, 17, 3 ) . '-' . substr( $fingerprint, 20, 12 );
		$ledger          = new Ledger();
		$plan            = ResourcePolicy::plan( 'design', $identity );
		$enforce         = 'enforce' === $mode && ! str_ends_with( $url, '/selection/validate' );
		$canonical_reply = 0;
		if ( $enforce ) {
			$permit = $ledger->reserve( $id, $fingerprint, $plan['limits'], 90, $plan['carry'], 'design', $identity->binding(), $identity->owners() );
			if ( is_wp_error( $permit ) ) {
				return self::failure( 'linker_admission_quota' === $permit->get_error_code() ? 429 : 503 );
			}
			if ( 'completed' === $permit['status'] ) {
				$old = EnginePublication::reply( ( new Replies() )->read( (int) $permit['outcome'], $identity->binding() ) );
				if ( is_wp_error( $old ) || $old->get_status() < 400 ) {
					return is_wp_error( $old ) ? $old : array( $old->get_status(), (string) $old->get_data() );
				}
				$canonical_reply = (int) $permit['outcome'];
				$id              = wp_generate_uuid4();
				$permit          = $ledger->reserve( $id, $fingerprint, $plan['limits'], 90, $plan['carry'], 'design', $identity->binding(), $identity->owners() );
				if ( is_wp_error( $permit ) ) {
					return self::failure( 'linker_admission_quota' === $permit->get_error_code() ? 429 : 503 );
				}
			}
			if ( is_wp_error( $ledger->dispatch( $id, $fingerprint ) ) ) {
				return self::failure( 409 );
			}
		}
		$replies  = new Replies();
		$reply_id = $enforce ? $replies->open( $identity->binding() ) : 0;
		$response = wp_remote_post(
			$url,
			array(
				'timeout' => 60,
				'headers' => array(
					'Content-Type'              => 'application/json',
					'X-Linker-Service-Token'    => defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ? (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ) : '',
					'X-Linker-Resource-Subject' => $account,
					'X-Linker-Engine-Version'   => $version,
				),
				'body'    => $body,
			)
		);
		$status   = is_wp_error( $response ) ? 503 : (int) wp_remote_retrieve_response_code( $response );
		$payload  = is_wp_error( $response ) ? '{"error":"engine_unavailable"}' : (string) wp_remote_retrieve_body( $response );
		if ( $status < 400 && wp_remote_retrieve_header( $response, 'x-linker-engine-version' ) !== $version ) {
			$status  = 503;
			$payload = '{"error":"engine_version_changed"}';
		}
		if ( $status < 400 ) {
			$decoded = json_decode( $payload, true );
			$valid   = EnginePublication::validate( is_array( $decoded ) && is_array( $decoded['publication'] ?? null ) ? $decoded['publication'] : array() );
			if ( is_wp_error( $valid ) ) {
				$status  = (int) ( $valid->get_error_data()['status'] ?? 503 );
				$payload = (string) wp_json_encode( array( 'detail' => array( 'error' => 409 === $status ? 'publication_changed' : 'publication_unavailable' ) ) );
			}
		}
		if ( $enforce ) {
			if ( $canonical_reply > 0 && $status < 400 ) {
				$replies->finish( $canonical_reply, new WP_REST_Response( $payload, $status ) );
			}
			$outcome   = $replies->finish( $reply_id, new WP_REST_Response( $payload, $status ) );
			$completed = $ledger->complete( $id, $fingerprint, $outcome );
			if ( is_wp_error( $completed ) && $outcome > 0 ) {
				wp_delete_post( $outcome, true );
			}
		}
		return array( $status, $payload );
	}

	/**
	 * Safe diagnostic for the ability's existing visible failure path.
	 *
	 * @param int $status Failure status.
	 */
	private static function failure( int $status = 503 ): WP_Error {
		return new WP_Error( 'linker_engine_admission', 'Sizing could not be admitted.', array( 'status' => $status ) );
	}
}
