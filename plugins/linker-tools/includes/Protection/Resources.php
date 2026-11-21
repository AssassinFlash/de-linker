<?php
/**
 * Admit resource work after native REST validation/permissions, before callback.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Fingerprint;
use Linker\Tools\Genie\Attachments;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** The callback stack is trusted server state, never a browser field. */
final class Resources {
	/**
	 * Successor entries one request may advance through, past attempts that
	 * stored nothing. A retry chain grows by one entry per failed Try again;
	 * this bound keeps a single request's work finite, as the journal's own
	 * attempt chain does.
	 */
	private const MAX_UNRECORDED_CHAIN = 8;

	/**
	 * The currently dispatched native operation.
	 *
	 * @var array<string,mixed>|null
	 */
	private static ?array $context = null;

	/**
	 * Native reply lifecycle dependency.
	 *
	 * @param Replies          $replies Private receipts.
	 * @param Attachments|null $attachments Heavy validation seam.
	 * @param EngineVersion    $version Running data snapshot readback.
	 */
	public function __construct( private readonly Replies $replies = new Replies(), private readonly ?Attachments $attachments = null, private readonly EngineVersion $version = new EngineVersion() ) {}

	/** Wire native boundaries; do not replace endpoint callbacks or permissions. */
	public function register(): void {
		add_filter( 'rest_dispatch_request', array( $this, 'dispatch' ), 10, 4 );
		add_filter( 'linker_commerce_public_business_context', array( $this, 'context' ) );
		add_action( 'init', array( $this->replies, 'register' ) );
		add_action( 'linker_tools_reply_cleanup', array( $this->replies, 'expire' ) );
		add_action( 'wp_print_footer_scripts', array( $this, 'assets' ), 0 );
		if ( ! wp_next_scheduled( 'linker_tools_reply_cleanup' ) ) {
			wp_schedule_event( time() + HOUR_IN_SECONDS, 'hourly', 'linker_tools_reply_cleanup' );
		}
	}

	/** Only the successfully dispatched enforce callback can skip legacy limits. */
	public static function verified(): bool {
		return null !== self::$context && ! empty( self::$context['enforced'] );
	}

	/** Completion identity for this verified Genie callback; never authorization. */
	public static function genie_operation(): string {
		return self::verified() && 'genie' === ( self::$context['action'] ?? '' ) ? (string) ( self::$context['id'] ?? '' ) : '';
	}

	/** Internal body fingerprint from the same trusted permit, never a client field. */
	public static function genie_fingerprint(): string {
		return '' !== self::genie_operation() ? (string) ( self::$context['fingerprint'] ?? '' ) : '';
	}

	/**
	 * A saved completion is usable only while its native result still exists.
	 * Privacy erasure, expiry and unresolved dispatches cannot become success.
	 * Ownership is checked by the existing conversation route, not by this ID.
	 *
	 * @param string $id Trusted completion ID stored with the answer.
	 * @param string $fingerprint Internal native input fingerprint.
	 */
	public static function completed_genie_operation( string $id, string $fingerprint ): bool {
		if ( ! class_exists( Ledger::class ) || '' === $id || '' === $fingerprint ) {
			return false;
		}
		$receipt = ( new Ledger() )->lookup( $id, $fingerprint );
		if ( is_wp_error( $receipt ) || 'genie' !== $receipt['purpose'] || 'completed' !== $receipt['status'] || $receipt['outcome'] < 1 ) {
			return false;
		}
		$reply = ( new Replies() )->read( $receipt['outcome'], $receipt['binding'] );
		return ! is_wp_error( $reply ) && $reply->get_status() < 400;
	}

	/** Expected snapshot for the trusted currently running native engine callback. */
	public static function engine_version(): string {
		return (string) ( self::$context['engine_version'] ?? '' );
	}

	/**
	 * Native Commerce can associate its saved order with this trusted UUID/HMAC.
	 *
	 * @param mixed $previous Another trusted adapter's scope.
	 * @return mixed Server-only context, removed even if the callback throws.
	 */
	public function context( mixed $previous ): mixed {
		return self::verified() ? self::$context : $previous;
	}

	/** Load the shared first-party client when a real tool app is present. */
	public function assets(): void {
		if ( ! is_admin() ) {
			wp_enqueue_script( 'linker-tools-inquiry-handoff' );
			if ( ! is_user_logged_in() ) {
				/**
				 * Load the native form widget client for anonymous Genie transfer cards.
				 *
				 * @since 0.1.0
				 */
				do_action( 'linker_commerce_public_protection_assets' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce owns this public integration seam.
			}
		}
	}

	/**
	 * This WordPress hook runs after the native permission callback and schema.
	 *
	 * @phpstan-impure
	 *
	 * @param mixed               $result Earlier dispatch override.
	 * @param WP_REST_Request     $request Validated native request.
	 * @param string              $route Matched native route pattern (use request for actual ID).
	 * @param array<string,mixed> $handler Native endpoint definition.
	 * @return mixed Native response or explicit admission failure.
	 */
	public function dispatch( mixed $result, WP_REST_Request $request, string $route, array $handler ): mixed {
		$action = ResourcePolicy::action( $request->get_route(), $request->get_method(), (int) $request->get_param( 'id' ) > 0 );
		if ( null !== $result || '' === $action ) {
			return $result;
		}
		if ( ! class_exists( Ledger::class ) ) {
			return self::error( 'configuration', 503 );
		}
		// Encoded 20 MiB files need <28 MiB JSON. Two MiB of metadata is
		// ample for the bounded native history (schema.MAX_REQUEST_BYTES).
		$ceiling = 'genie' === $action ? 30 * 1024 * 1024 : 6 * 1024 * 1024;
		if ( strlen( (string) $request->get_body() ) > $ceiling ) {
			return self::error( 'body', 413 );
		}
		$engineering        = in_array( $action, array( 'design', 'roof', 'report_pdf' ), true );
		$publication_action = $engineering || in_array( $action, array( 'solution_save', 'draft_write' ), true );
		$payload            = $engineering ? array( 'input' => (array) $request->get_json_params() ) : $request->get_params();
		if ( ! $engineering ) {
			foreach ( array( 'website', 'started', 'started_nonce', '_wpnonce' ) as $field ) {
				unset( $payload[ $field ] );
			}
		}
		$payload['_route']  = strtolower( $request->get_route() );
		$payload['_method'] = $request->get_method();
		$identity           = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$raw_files = $request->get_param( 'attachments' );
		if ( 'genie' === $action && null !== $raw_files && ( ! is_array( $raw_files ) || count( $raw_files ) > Attachments::MAX_FILES ) ) {
			return self::error( 'files', 400 );
		}
		$plan      = ResourcePolicy::plan( $action, $identity );
		$operation = (string) $request->get_header( 'X-Linker-Operation' );
		$version   = '';
		if ( in_array( $action, array( 'design', 'roof', 'report_pdf' ), true ) ) {
			$version = $this->version->current( $request );
			if ( is_wp_error( $version ) ) {
				return $version;
			}
			// The live loaded snapshot, rather than a deployment stamp, scopes reuse.
			// Identical input/version/subject/day cannot spend another unit.
			$semantic = Fingerprint::make( $identity, $action, $payload );
			if ( is_wp_error( $semantic ) ) {
				return self::error( 'input', 400 );
			}
			$hash      = hash_hmac( 'sha256', (string) wp_json_encode( array( $identity->binding(), $version, $semantic, intdiv( time(), DAY_IN_SECONDS ) ) ), wp_salt( 'nonce' ) );
			$operation = substr( $hash, 0, 8 ) . '-' . substr( $hash, 8, 4 ) . '-4' . substr( $hash, 13, 3 ) . '-a' . substr( $hash, 17, 3 ) . '-' . substr( $hash, 20, 12 );
		}
		$ledger      = new Ledger();
		$fingerprint = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fingerprint ) ) {
			return self::error( 'input', 400 );
		}
		$permit = $this->reserve( $ledger, $identity, $action, $operation, $fingerprint, $plan );

		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		$canonical_reply = 0;
		// A turn the proxy refused before it stored an answer keeps that fact on
		// its saved reply (Proxy::unrecorded). Try again is a new attempt at the
		// same question, never a replay of that refusal, so each such predecessor
		// advances this operation to a successor journal entry. Bounded: every
		// step is a distinct id, and a step that is not reused is dispatched.
		for ( $step = 0, $unrecorded = self::unrecorded_reply( $permit, $this->replies, $action, $identity->binding() ); $step < self::MAX_UNRECORDED_CHAIN && false !== $unrecorded; ++$step ) {
			$permit = $this->reserve( $ledger, $identity, $action, self::successor( (string) $permit['id'] ), $fingerprint, $plan );
			if ( is_wp_error( $permit ) ) {
				return $permit;
			}
			$unrecorded = self::unrecorded_reply( $permit, $this->replies, $action, $identity->binding() );
		}
		if ( ! empty( $permit['reused'] ) ) {
			$old   = $this->replies->read( (int) $permit['receipt']['outcome'], $identity->binding() );
			$again = ! in_array( $action, array( 'design', 'roof', 'report_pdf' ), true ) || is_wp_error( $old ) || $old->get_status() < 400;
			if ( ! $again ) {
				// A definite failed pure calculation can be attempted explicitly again.
				// Unknown/dispatched operations and business writes never enter here.
				$canonical_reply = (int) $permit['receipt']['outcome'];
				$retry           = hash( 'sha256', $operation . '|' . $request->get_header( 'X-Linker-Operation' ) );
				$operation       = substr( $retry, 0, 8 ) . '-' . substr( $retry, 8, 4 ) . '-4' . substr( $retry, 13, 3 ) . '-a' . substr( $retry, 17, 3 ) . '-' . substr( $retry, 20, 12 );
				$permit          = $this->reserve( $ledger, $identity, $action, $operation, $fingerprint, $plan );
				if ( is_wp_error( $permit ) ) {
					return $permit;
				}
				if ( ! empty( $permit['reused'] ) ) {
					$retry_reply = $this->replies->read( (int) $permit['receipt']['outcome'], $identity->binding() );
					return EnginePublication::reply( $retry_reply );
				}
			} else {
				return $publication_action ? EnginePublication::reply( $old ) : $old;
			}
		}

		if ( '' !== (string) $request->get_param( 'website' ) ) {
			$ledger->cancel( $permit['id'], $fingerprint );
			return self::error( 'form', 400 );
		}
		if ( 'genie' === $action ) {
			// A verified reservation exists before decoding; invalid bytes can
			// return it before dispatch. No parsing/model/conversation write yet.
			$checked = ( $this->attachments ?? new Attachments( static fn ( string $who, int $units ): bool => '' !== $who || $units > 0 ) )->check( $raw_files );
			if ( is_wp_error( $checked ) ) {
				$ledger->cancel( $permit['id'], $fingerprint );
				return $checked;
			}
		}
		$sent = $ledger->dispatch( $permit['id'], $fingerprint );
		if ( is_wp_error( $sent ) ) {
			return $sent;
		}
		$reply_id      = $this->replies->open( $identity->binding(), (string) $request->get_param( 'email' ) );
		$previous      = self::$context;
		self::$context = array_merge(
			$permit,
			array(
				'action'         => $action,
				'binding'        => $identity->binding(),
				'engine_version' => $version,
			)
		);
		try {
			$callback = $handler['callback'];
			if ( ! is_callable( $callback ) ) {
				return self::error( 'handler', 503 );
			}
			$reply    = call_user_func( $callback, $request );
			$response = is_wp_error( $reply ) ? rest_convert_error_to_response( $reply ) : rest_ensure_response( $reply );
			if ( $publication_action && $response->get_status() < 400 ) {
				$checked = EnginePublication::reply( $response );
				if ( is_wp_error( $checked ) ) {
					$response = rest_convert_error_to_response( $checked );
				}
			}
			$response->header( 'Cache-Control', 'private, no-store' );
			if ( $engineering && $response->get_status() >= 400 ) {
				// A native completed pure failure is safe to retry explicitly. A
				// reverse proxy's ambiguous 5xx never carries this trusted marker.
				$response->header( 'X-Linker-Resource-Outcome', 'failed' );
			}
			if ( 'genie' === $action && $response->get_status() >= 400 && self::states_unrecorded( $reply, $response ) ) {
				// The proxy itself refused before storing any answer, so this turn
				// is not a result a later Try again may receive again.
				$response->header( 'X-Linker-Resource-Outcome', 'failed' );
			}
			if ( $canonical_reply > 0 && $response->get_status() < 400 ) {
				$this->replies->finish( $canonical_reply, $response );
			}
			$outcome   = $reply_id > 0 ? $this->replies->finish( $reply_id, $response ) : 0;
			$completed = $ledger->complete( $permit['id'], $fingerprint, $outcome );
			if ( is_wp_error( $completed ) && $outcome > 0 ) {
				wp_delete_post( $outcome, true );
			}
			return $response;
		} finally {
			self::$context = $previous;
		}
	}

	/**
	 * Whether this permit's saved reply says the turn stored no answer.
	 *
	 * @param array<string,mixed> $permit Server permit.
	 * @param Replies             $replies Native reply store.
	 * @param string              $action Server action.
	 * @param string              $binding Current identity.
	 * @return WP_REST_Response|false The refused reply, or false when this is not one.
	 */
	private static function unrecorded_reply( array $permit, Replies $replies, string $action, string $binding ): WP_REST_Response|false {
		if ( 'genie' !== $action || empty( $permit['reused'] ) ) {
			return false;
		}
		$old = $replies->read( (int) $permit['receipt']['outcome'], $binding );
		return ! is_wp_error( $old ) && 'failed' === ( $old->get_headers()['X-Linker-Resource-Outcome'] ?? '' ) ? $old : false;
	}

	/** Key for an explicit retry of a turn that stored no answer.
	 *
	 * @param string $id Current operation.
	 */
	private static function successor( string $id ): string {
		$seed = hash( 'sha256', 'linker-genie-unrecorded|' . $id );
		return substr( $seed, 0, 8 ) . '-' . substr( $seed, 8, 4 ) . '-4' . substr( $seed, 13, 3 ) . '-a' . substr( $seed, 17, 3 ) . '-' . substr( $seed, 20, 12 );
	}

	/**
	 * Associate a tool operation with its native owner and replay only a completed reply.
	 *
	 * @param Ledger              $ledger Private journal.
	 * @param Identity            $identity Native session.
	 * @param string              $action Server-selected operation.
	 * @param string              $id Operation identifier.
	 * @param string              $fingerprint Canonical request.
	 * @param array<string,mixed> $plan Resource dimensions.
	 * @return array<string,mixed>|WP_Error
	 */
	private function reserve( Ledger $ledger, Identity $identity, string $action, string $id, string $fingerprint, array $plan ): array|WP_Error {
		$receipt = $ledger->reserve( $id, $fingerprint, $plan['limits'], 90, $plan['carry'], $action, $identity->binding(), $identity->owners() );
		if ( is_wp_error( $receipt ) ) {
			$status = match ( $receipt->get_error_code() ) {
				'linker_admission_quota' => 429,
				'linker_admission_payload_changed', 'linker_admission_input' => 409,
				default => 503,
			};
			$receipt->add_data( array_merge( (array) $receipt->get_error_data(), array( 'status' => $status ) ) );
			return $receipt;
		}
		if ( ! in_array( $receipt['status'], array( 'completed', 'reserved' ), true ) ) {
			return self::error( 'pending', 409 );
		}
		return array(
			'enforced'    => true,
			'reused'      => 'completed' === $receipt['status'],
			'receipt'     => $receipt,
			'id'          => $id,
			'fingerprint' => $fingerprint,
		);
	}

	/**
	 * Whether this callback refused before storing anything (Proxy::unrecorded).
	 *
	 * Only the callback's own error can say so; a response body the browser
	 * could have written never decides it.
	 *
	 * @param mixed            $reply Raw callback return.
	 * @param WP_REST_Response $response The same answer as a response.
	 */
	private static function states_unrecorded( mixed $reply, WP_REST_Response $response ): bool {
		if ( is_wp_error( $reply ) ) {
			$data = $reply->get_error_data();
			if ( is_array( $data ) && ! empty( $data['unrecorded'] ) ) {
				return true;
			}
		}
		// rest_convert_error_to_response() keeps the callback's data here.
		$body = $response->get_data();
		return is_array( $body ) && is_array( $body['data'] ?? null ) && ! empty( $body['data']['unrecorded'] );
	}

	/**
	 * Input is retained by the tool app on every refusal.
	 *
	 * @param string $reason Safe code.
	 * @param int    $status Native status.
	 */
	private static function error( string $reason, int $status ): WP_Error {
		return new WP_Error( 'linker_resource_' . $reason, __( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ), array( 'status' => $status ) );
	}
}
