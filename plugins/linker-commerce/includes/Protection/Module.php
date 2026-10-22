<?php
/**
 * Shared admission hooks; native doors connect through explicit consumer modules.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

use WP_Error;
use WP_REST_Request;

/** Source configuration stays private; the proof controller exposes no quota edits. */
final class Module {
	public const MAINTENANCE = 'linker_public_protection_maintenance';
	// Initial small verification-body ceiling, docs/specs/519-public-admission.md.
	private const MAX_BYTES = 16384;

	/**
	 * Main plugin file locates the one shared build.
	 *
	 * @param string $file Plugin file.
	 */
	public function __construct( private readonly string $file ) {}

	/** Register actual routes, native privacy and explicit integration seams. */
	public function register(): void {
		$configuration = Configuration::current();
		$controller    = new Controller( $configuration );
		$assets        = new Assets( $this->file, $configuration );
		$health        = new HealthPage( $configuration, $assets );
		add_action( 'rest_api_init', array( $controller, 'register' ) );
		add_filter( 'rest_pre_dispatch', array( $this, 'body_limit' ), 10, 3 );
		add_action( 'linker_commerce_public_protection_assets', array( $assets, 'enqueue' ) );
		add_filter( 'linker_commerce_public_admission', array( $this, 'admit' ), 10, 2 );
		add_action( 'admin_menu', array( $health, 'menu' ) );
		add_action( 'admin_enqueue_scripts', array( $health, 'assets' ) );
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::MAINTENANCE, array( $this, 'maintain' ) );
		( new Privacy() )->register();
		( new BusinessPolicy() )->register();
		add_filter( 'linker_commerce_public_protection_consumers', array( $this, 'consumers' ) );
		add_filter( 'linker_commerce_receipt_budget_reason', array( $this, 'receipt_budget' ), 10, 4 );
		( new BusinessRecord() )->register();
		( new IntakeAdmin() )->register();
		add_filter( 'linker_commerce_pending_review_summary', array( Intake::class, 'pending_summary' ), 10, 0 );
		add_action( 'woocommerce_privacy_before_remove_order_personal_data', array( IntakeStore::class, 'forget' ) );
		( new Accounts() )->register();
		( new Draft() )->register();
		( new Login() )->register();
		( new Comments() )->register();
		if ( Business::enabled() ) {
			add_action( 'wp_enqueue_scripts', array( $assets, 'enqueue' ) );
		}
	}

	/**
	 * Report actual native hooks; configured mode still determines enforcement.
	 *
	 * @param array<string,string> $existing Other connected modules.
	 * @return array<string,string>
	 */
	public function consumers( array $existing ): array {
		return array_merge(
			$existing,
			array(
				'contact'        => 'Contact\\Handler::process (admin-post)',
				'inquiry'        => 'Inquiry\\Handler::process (admin-post, guest/account)',
				'registration'   => 'Accounts (Woo process_registration_errors; WordPress registration_errors)',
				'password_reset' => 'Accounts (native lostpassword_post, before key/mail)',
				'login'          => 'Login (wp_authenticate_user after failed use)',
				'draft_write'    => 'Draft (Woo forms, session reorder, wc-ajax, Store API)',
				'comment'        => 'Comments (native form, WordPress REST; pingback write closed in enforce)',
			)
		);
	}

	/**
	 * Trusted optional-receipt seam shared with Tools; never a public endpoint.
	 *
	 * @param mixed      $reason Earlier trusted decision, null when unanswered.
	 * @param string     $email Validated destination.
	 * @param int|string $reference Stable native source id or logical UUID.
	 * @param string     $kind Native source kind.
	 */
	public function receipt_budget( mixed $reason, string $email, int|string $reference, string $kind ): string {
		return is_string( $reason ) ? $reason : ReceiptBudget::reason( $email, $reference, $kind );
	}

	/** Native hourly cleanup complements recovery on each actual admission. */
	public function schedule(): void {
		if ( ! wp_next_scheduled( self::MAINTENANCE ) ) {
			wp_schedule_event( time() + HOUR_IN_SECONDS, 'hourly', self::MAINTENANCE );
		}
	}

	/** A failure stays observable as the journal failure; no reset or silent purge. */
	public function maintain(): void {
		if ( false !== get_option( Ledger::OPTION ) ) {
			( new Ledger() )->summary();
		}
	}

	/**
	 * Reject oversized verification JSON before WordPress validates/parses its args.
	 * This does not claim to replace a host-level ingress limit.
	 *
	 * @param mixed           $result Earlier REST pre-dispatch result.
	 * @param mixed           $server Native server, unused.
	 * @param WP_REST_Request $request Request.
	 * @return mixed Earlier result or bounded-body refusal.
	 */
	public function body_limit( mixed $result, mixed $server, WP_REST_Request $request ): mixed {
		if ( null !== $result || ! in_array( strtolower( $request->get_route() ), array( '/linker/v1/protection/prepare', '/linker/v1/protection/verify' ), true ) ) {
			return $result;
		}
		$length = $request->get_header( 'content-length' ) ?? '';
		return ( ctype_digit( $length ) && (int) $length > self::MAX_BYTES ) || self::oversized( $request->get_body() ) ? new WP_Error( 'linker_verification_size', __( 'This verification request is too large. Please try again.', 'linker-commerce' ), array( 'status' => 413 ) ) : $result;
	}

	/**
	 * WordPress body-params-only requests have null raw bodies despite vendor stubs.
	 *
	 * @param string|null $body Actual native raw body.
	 */
	private static function oversized( ?string $body ): bool {
		return null !== $body && strlen( $body ) > self::MAX_BYTES;
	}

	/**
	 * A trusted PHP seam: limits and canonical data never come from browser JSON.
	 *
	 * @param mixed               $previous Existing result.
	 * @param array<string,mixed> $input Native consumer request.
	 * @return array<string,mixed>|WP_Error Server permit.
	 */
	public function admit( mixed $previous, array $input ): array|WP_Error {
		if ( is_array( $previous ) || is_wp_error( $previous ) ) {
			return $previous;
		}
		foreach ( array( 'action', 'proof', 'id' ) as $field ) {
			if ( ! is_string( $input[ $field ] ?? null ) ) {
				return new WP_Error( 'linker_admission_input', 'Invalid native admission input.' );
			}
		}
		if ( ! is_array( $input['payload'] ?? null ) || ! is_array( $input['limits'] ?? null ) || ! is_int( $input['lease'] ?? null ) || ( isset( $input['single'] ) && ! is_bool( $input['single'] ) ) || ( isset( $input['carry'] ) && ! is_array( $input['carry'] ) ) ) {
			return new WP_Error( 'linker_admission_input', 'Invalid native admission input.' );
		}
		foreach ( $input['limits'] as $limit ) {
			if ( ! $limit instanceof Allowance ) {
				return new WP_Error( 'linker_admission_input', 'Invalid native admission limit.' );
			}
		}
		$carry = array();
		foreach ( $input['carry'] ?? array() as $link ) {
			if ( ! is_array( $link ) || ! ( $link['source'] ?? null ) instanceof Allowance || ! ( $link['target'] ?? null ) instanceof Allowance ) {
				return new WP_Error( 'linker_admission_input', 'Invalid native admission carry.' );
			}
			$carry[] = array(
				'source' => $link['source'],
				'target' => $link['target'],
			);
		}
		return ( new Admission( Configuration::current() ) )->reserve( $input['action'], $input['proof'], $input['id'], $input['payload'], $input['limits'], $input['lease'], $input['single'] ?? false, $carry );
	}
}
