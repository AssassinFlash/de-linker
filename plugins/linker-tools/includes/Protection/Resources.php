<?php
/**
 * Admit resource work after native REST validation/permissions, before callback.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Admission;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Identity;
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
	 * @param NativeEngine     $engine Trusted ability requests.
	 * @param Attachments|null $attachments Heavy validation seam.
	 */
	public function __construct( private readonly Replies $replies = new Replies(), private readonly NativeEngine $engine = new NativeEngine(), private readonly ?Attachments $attachments = null ) {}

	/** Wire native boundaries; do not replace endpoint callbacks or permissions. */
	public function register(): void {
		$this->engine->register();
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
			/**
			 * Shared first-party code; the global dock loads Cloudflare on interaction.
			 *
			 * @since 0.1.0
			 */
			do_action( 'linker_commerce_public_protection_assets' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce owns this public integration seam.
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
		if ( ! class_exists( Configuration::class ) ) {
			$mode = defined( 'LINKER_PUBLIC_PROTECTION_MODE' ) ? constant( 'LINKER_PUBLIC_PROTECTION_MODE' ) : ( is_string( getenv( 'LINKER_PUBLIC_PROTECTION_MODE' ) ) ? getenv( 'LINKER_PUBLIC_PROTECTION_MODE' ) : 'off' );
			return 'off' === $mode ? $result : self::error( 'configuration', 503 );
		}
		$configuration = Configuration::current();
		if ( 'off' === $configuration->mode ) {
			return $result;
		}
		// Encoded 20 MiB files need <28 MiB JSON. Two MiB of metadata is
		// ample for the bounded native history (schema.MAX_REQUEST_BYTES).
		$ceiling = 'genie' === $action ? 30 * 1024 * 1024 : 6 * 1024 * 1024;
		if ( strlen( $request->get_body() ) > $ceiling ) {
			return self::error( 'body', 413 );
		}
		$payload = $request->get_params();
		foreach ( array( 'website', 'started', 'started_nonce', '_wpnonce' ) as $field ) {
			unset( $payload[ $field ] );
		}
		$payload['_route']  = $request->get_route();
		$payload['_method'] = $request->get_method();
		$identity           = Identity::current();
		if ( is_wp_error( $identity ) ) {
			return $identity;
		}
		// Native ownership is retained; reject an explicitly foreign conversation
		// before reserving any quota or exposing a previous receipt.
		$id = (int) $request->get_param( 'id' );
		if ( in_array( $action, array( 'conversation_write', 'conversation_mail' ), true ) && $id > 0 && ! ( new Conversations() )->may_use( $id ) ) {
			return self::error( 'conversation', 404 );
		}
		$raw_files = $request->get_param( 'attachments' );
		if ( 'genie' === $action && null !== $raw_files && ( ! is_array( $raw_files ) || count( $raw_files ) > Attachments::MAX_FILES ) ) {
			return self::error( 'files', 400 );
		}
		$plan = ResourcePolicy::plan( $action, $identity, is_array( $raw_files ) ? count( $raw_files ) : 0 );
		if ( 'enforce' === $configuration->mode && array() === $plan['limits'] ) {
			// The shared Commerce business policy is a required dependency.
			return self::error( 'configuration', 503 );
		}
		$operation = (string) $request->get_header( 'X-Linker-Operation' );
		if ( in_array( $action, array( 'design', 'roof', 'report_pdf' ), true ) ) {
			$version = defined( 'LINKER_ENGINE_RESOURCE_VERSION' ) ? (string) constant( 'LINKER_ENGINE_RESOURCE_VERSION' ) : '';
			if ( 'enforce' === $configuration->mode && '' === $version ) {
				return self::error( 'configuration', 503 );
			}
			// The immutable engine/feed release is deployed with the service.
			// Identical input/version/subject/day cannot spend another unit.
			$hash      = hash_hmac( 'sha256', (string) wp_json_encode( array( $identity->binding(), $version, Fingerprint::make( $identity, $action, $payload ), intdiv( time(), DAY_IN_SECONDS ) ) ), wp_salt( 'nonce' ) );
			$operation = substr( $hash, 0, 8 ) . '-' . substr( $hash, 8, 4 ) . '-4' . substr( $hash, 13, 3 ) . '-a' . substr( $hash, 17, 3 ) . '-' . substr( $hash, 20, 12 );
		}
		$admission = new Admission( $configuration );
		$business  = in_array( $action, array( 'genie_contact', 'genie_inquiry', 'conversation_mail' ), true );
		$permit    = $admission->reserve( $action, (string) $request->get_header( 'X-Linker-Proof' ), $operation, $payload, $plan['limits'], 90, $business, $plan['carry'], $business && is_email( (string) $request->get_param( 'email' ) ) ? array( Allowance::owner_for( Identity::recipient( (string) $request->get_param( 'email' ) ) ) ) : array() );
		if ( is_wp_error( $permit ) ) {
			return $permit;
		}
		$canonical_reply = 0;
		if ( ! empty( $permit['reused'] ) ) {
			$old = $this->replies->read( (int) $permit['receipt']['outcome'], $identity->binding() );
			if ( ! in_array( $action, array( 'design', 'roof', 'report_pdf' ), true ) || is_wp_error( $old ) || $old->get_status() < 400 ) {
				return $old;
			}
			// A definite failed pure calculation can be attempted explicitly again.
			// Unknown/dispatched operations and business writes never enter here.
			$canonical_reply = (int) $permit['receipt']['outcome'];
			$retry           = hash( 'sha256', $operation . '|' . $request->get_header( 'X-Linker-Operation' ) );
			$operation       = substr( $retry, 0, 8 ) . '-' . substr( $retry, 8, 4 ) . '-4' . substr( $retry, 13, 3 ) . '-a' . substr( $retry, 17, 3 ) . '-' . substr( $retry, 20, 12 );
			$permit          = $admission->reserve( $action, (string) $request->get_header( 'X-Linker-Proof' ), $operation, $payload, $plan['limits'], 90, false, $plan['carry'] );
			if ( is_wp_error( $permit ) ) {
				return $permit;
			}
			if ( ! empty( $permit['reused'] ) ) {
				return $this->replies->read( (int) $permit['receipt']['outcome'], $identity->binding() );
			}
		}

		$valid = $admission->validate( $permit );
		if ( is_wp_error( $valid ) ) {
			$admission->cancel( $permit );
			return $valid;
		}
		if ( 'enforce' === $configuration->mode && '' !== (string) $request->get_param( 'website' ) ) {
			$admission->cancel( $permit );
			return self::error( 'form', 400 );
		}
		if ( 'genie' === $action && 'enforce' === $configuration->mode ) {
			// A verified reservation exists before decoding; invalid bytes can
			// return it before dispatch. No parsing/model/conversation write yet.
			$checked = ( $this->attachments ?? new Attachments( static fn ( string $who, int $units ): bool => '' !== $who || $units > 0 ) )->check( $raw_files );
			if ( is_wp_error( $checked ) ) {
				$admission->cancel( $permit );
				return $checked;
			}
		}
		$sent = $admission->dispatch( $permit );
		if ( is_wp_error( $sent ) ) {
			return $sent;
		}
		$reply_id      = ! empty( $permit['enforced'] ) ? $this->replies->open( $identity->binding(), (string) $request->get_param( 'email' ) ) : 0;
		$previous      = self::$context;
		self::$context = array_merge(
			$permit,
			array(
				'action'  => $action,
				'binding' => $identity->binding(),
			)
		);
		try {
			$callback = $handler['callback'];
			if ( ! is_callable( $callback ) ) {
				return self::error( 'handler', 503 );
			}
			$reply    = call_user_func( $callback, $request );
			$response = is_wp_error( $reply ) ? rest_convert_error_to_response( $reply ) : rest_ensure_response( $reply );
			$response->header( 'Cache-Control', 'private, no-store' );
			if ( $canonical_reply > 0 && $response->get_status() < 400 ) {
				$this->replies->finish( $canonical_reply, $response );
			}
			$outcome   = $reply_id > 0 ? $this->replies->finish( $reply_id, $response ) : 0;
			$completed = $admission->complete( $permit, $outcome );
			if ( is_wp_error( $completed ) && $outcome > 0 ) {
				wp_delete_post( $outcome, true );
			}
			return $response;
		} finally {
			self::$context = $previous;
		}
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
