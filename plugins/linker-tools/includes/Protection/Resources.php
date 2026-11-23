<?php
/**
 * Admit resource work after native REST validation/permissions, before callback.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Protection\Fingerprint;
use Linker\Tools\Genie\Attachments;
use Linker\Tools\Genie\Conversations;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** The callback stack is trusted server state, never a browser field. */
final class Resources {
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
	 */
	public function __construct( private readonly Replies $replies = new Replies(), private readonly ?Attachments $attachments = null ) {}

	/** Wire native boundaries; do not replace endpoint callbacks or permissions. */
	public function register(): void {
		add_filter( 'rest_dispatch_request', array( $this, 'dispatch' ), 10, 4 );
		add_filter( 'linker_commerce_public_business_context', array( $this, 'context' ) );
		add_action( 'init', array( $this->replies, 'register' ) );
		add_action( 'linker_tools_expire_genie_turn', array( \Linker\Tools\Genie\PendingTurns::class, 'expire' ), 10, 2 );
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
		if ( ! wp_is_uuid( $id, 4 ) || '' === $fingerprint ) {
			return false;
		}
		$replies = new Replies();
		$outcome = $replies->operation( $id );
		if ( $outcome > 0 ) {
			if ( ! hash_equals( (string) get_post_meta( $outcome, '_linker_input', true ), $fingerprint ) ) {
				return false;
			}
			$binding = (string) get_post_meta( $outcome, '_linker_binding', true );
		} else {
			$previous = $replies->previous( $id );
			if ( ! $previous || 'genie' !== $previous['purpose'] || 'completed' !== $previous['status'] || ! hash_equals( $previous['fingerprint'], $fingerprint ) ) {
				return false;
			}
			$outcome = (int) $previous['outcome'];
			$binding = (string) $previous['binding'];
		}
		$reply = $replies->read( $outcome, $binding );
		return ! is_wp_error( $reply ) && 200 === $reply->get_status();
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
		$operation = strtolower( (string) ( $request->get_header( 'X-Linker-Operation' ) ?? $request->get_header( 'X-Linker-Operation-Id' ) ) );
		if ( ! wp_is_uuid( $operation, 4 ) || '' !== (string) $request->get_param( 'website' ) ) {
			return self::error( 'input', 400 );
		}
		$ceiling = 'genie' === $action ? 30 * MB_IN_BYTES : 6 * MB_IN_BYTES;
		if ( strlen( $request->get_body() ) > $ceiling ) {
			return self::error( 'body', 413 );
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		$files = $request->get_param( 'attachments' );
		if ( 'genie' === $action && null !== $files ) {
			if ( ! is_array( $files ) || count( $files ) > Attachments::MAX_FILES ) {
				return self::error( 'files', 400 );
			}
		}
		if ( 'genie' === $action && is_array( $request->get_param( 'messages' ) ) ) {
			// Restored display blocks are not customer input to the model or its operation fingerprint.
			$request->set_param(
				'messages',
				array_map(
					static fn( $message ) => is_array( $message ) ? array_intersect_key(
						$message,
						array(
							'role'    => true,
							'content' => true,
						)
					) : $message,
					$request->get_param( 'messages' )
				)
			);
		}
		$payload = $request->get_params();
		foreach ( array( 'website', 'started', 'started_nonce', '_wpnonce' ) as $field ) {
			unset( $payload[ $field ] );
		}
		$payload['_route']  = strtolower( $request->get_route() );
		$payload['_method'] = $request->get_method();
		$fingerprint        = Fingerprint::make( $identity, $action, $payload );
		if ( is_wp_error( $fingerprint ) ) {
			return self::error( 'input', 400 );
		}
		$binding = $identity->binding();
		$reply   = self::error( 'pending', 409 );
		Lock::run(
			'genie-operation-' . $operation,
			function () use ( &$reply, $operation, $binding, $fingerprint, $action, $request, $handler ): void {
				$reply = $this->run( $operation, $binding, $fingerprint, $action, $request, $handler['callback'] );
			}
		);
		return $reply;
	}

	/**
	 * Execute one request under its own lock. A placeholder left by interrupted
	 * work cannot dispatch a second time. Only an explicitly unrecorded turn can retry.
	 *
	 * @param string          $operation Native UUID.
	 * @param string          $binding Current owner.
	 * @param string          $fingerprint Authenticated request content.
	 * @param string          $action Server-selected operation.
	 * @param WP_REST_Request $request Native request.
	 * @param mixed           $callback Native handler.
	 */
	private function run( string $operation, string $binding, string $fingerprint, string $action, WP_REST_Request $request, mixed $callback ): WP_REST_Response|WP_Error {
		$id = $this->replies->operation( $operation );
		if ( $id > 0 ) {
			if ( ! hash_equals( (string) get_post_meta( $id, '_linker_input', true ), $fingerprint ) ) {
				return self::changed();
			}
			$stored = $this->replies->read( $id, $binding );
			if ( ! self::retryable( $action, $stored ) ) {
				if ( 'conversation_create' === $action && $stored instanceof WP_REST_Response && $stored->get_status() < 400 ) {
					$from          = (int) get_post_meta( $id, '_linker_previous_conversation', true );
					$conversations = new Conversations();
					if ( $from > 0 && $conversations->selected_id() === $from ) {
						if ( is_user_logged_in() ) {
							$conversations->activate( (int) $stored->get_data()['conversation_id'] );
						} else {
							$conversations->start_guest_conversation();
						}
					}
				}
				return 'solution_save' === $action ? EnginePublication::reply( $stored ) : $stored;
			}
			$reset = wp_update_post(
				array(
					'ID'           => $id,
					'post_content' => '',
				),
				true
			);
			if ( is_wp_error( $reset ) ) {
				return self::error( 'storage', 503 );
			}
		} else {
			$legacy_id = $operation;
			$entry     = $this->replies->previous( $legacy_id );
			while ( null !== $entry ) {
				if ( $entry['purpose'] !== $action || ! hash_equals( $entry['binding'], $binding ) || ! hash_equals( $entry['fingerprint'], $fingerprint ) ) {
					return self::changed();
				}
				if ( 'completed' !== $entry['status'] ) {
					return self::error( 'pending', 409 );
				}
				$stored = $this->replies->read( (int) $entry['outcome'], $binding );
				if ( ! self::retryable( $action, $stored ) ) {
					return 'solution_save' === $action ? EnginePublication::reply( $stored ) : $stored;
				}
				// Earlier explicitly retried turns used a new UUID for each failed attempt.
				$hash      = hash( 'sha256', 'linker-genie-unrecorded|' . $legacy_id );
				$legacy_id = substr( $hash, 0, 8 ) . '-' . substr( $hash, 8, 4 ) . '-4' . substr( $hash, 13, 3 ) . '-a' . substr( $hash, 17, 3 ) . '-' . substr( $hash, 20, 12 );
				$entry     = $this->replies->previous( $legacy_id );
			}
			$from = 'conversation_create' === $action ? ( new Conversations() )->selected_id() : 0;
			if ( 'conversation_create' === $action && ! is_user_logged_in() && 0 === $from && is_callable( $callback ) ) {
				// A blank guest editor with no selected conversation has no mutation to replay.
				$result = $callback( $request );
				return is_wp_error( $result ) ? $result : rest_ensure_response( $result );
			}
			$files = $request->get_param( 'attachments' );
			if ( 'genie' === $action && null !== $files ) {
				$checked = ( $this->attachments ?? new Attachments( static fn (): bool => true ) )->check( $files );
				if ( is_wp_error( $checked ) ) {
					return $checked;
				}
			}
			$id = $this->replies->open( $binding, (string) $request->get_param( 'email' ), $operation, $fingerprint, $from );
			if ( $id < 1 ) {
				return self::error( 'storage', 503 );
			}
		}
		if ( ! is_callable( $callback ) ) {
			return self::error( 'handler', 503 );
		}
		$previous      = self::$context;
		self::$context = array(
			'id'          => $operation,
			'fingerprint' => $fingerprint,
			'binding'     => $binding,
			'action'      => $action,
			'enforced'    => true,
		);
		try {
			$raw      = $callback( $request );
			$response = is_wp_error( $raw ) ? rest_convert_error_to_response( $raw ) : rest_ensure_response( $raw );
			if ( 'solution_save' === $action && $response->get_status() < 400 ) {
				$checked = EnginePublication::reply( $response );
				if ( is_wp_error( $checked ) ) {
					$response = rest_convert_error_to_response( $checked );
				}
			}
			$response->header( 'Cache-Control', 'private, no-store' );
			if ( 'genie' === $action && $response->get_status() >= 400 && self::states_unrecorded( $raw, $response ) ) {
				$response->header( 'X-Linker-Resource-Outcome', 'failed' );
			}
			if ( 'failed' === ( $response->get_headers()['X-Linker-Resource-Outcome'] ?? '' ) || ( 'solution_save' === $action && is_wp_error( $raw ) && 'linker_solution_changed' === $raw->get_error_code() ) ) {
				wp_delete_post( $id, true );
			} elseif ( $id !== $this->replies->finish( $id, $response ) ) {
				return new WP_Error( 'linker_resource_result', __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-tools' ), array( 'status' => 409 ) );
			}
			return $response;
		} finally {
			self::$context = $previous;
		}
	}

	/** Only a turn explicitly refused before recording may be dispatched again.
	 *
	 * @param string                    $action Native operation.
	 * @param WP_REST_Response|WP_Error $reply Stored native result.
	 */
	private static function retryable( string $action, WP_REST_Response|WP_Error $reply ): bool {
		return 'genie' === $action && ! is_wp_error( $reply ) && 'failed' === ( $reply->get_headers()['X-Linker-Resource-Outcome'] ?? '' );
	}

	/** A reused operation key names one owner and one payload. */
	private static function changed(): WP_Error {
		return new WP_Error( 'linker_admission_payload_changed', __( 'Your request could not be completed. Your input is still here. Please try again.', 'linker-tools' ), array( 'status' => 409 ) );
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
