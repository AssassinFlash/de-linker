<?php
/**
 * Native customer forms and private intake administration.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Register native submit, account and privacy hooks. */
final class Module {
	public const MAINTENANCE = 'linker_public_protection_maintenance';
	/**
	 * Main plugin file locates the one shared build.
	 *
	 * @param string $file Plugin file.
	 */
	public function __construct( private readonly string $file ) {}

	/** Register actual routes, native privacy and explicit integration seams. */
	public function register(): void {
		$configuration = Configuration::current();
		$assets        = new Assets( $this->file, $configuration );
		$health        = new HealthPage( $configuration );
		add_action( 'linker_commerce_public_protection_assets', array( $assets, 'enqueue' ) );
		add_action( 'admin_menu', array( $health, 'menu' ) );
		add_action( 'init', array( $this, 'schedule' ) );
		add_action( self::MAINTENANCE, array( $this, 'maintain' ) );
		( new Privacy() )->register();
		add_filter( 'linker_commerce_receipt_budget_reason', array( $this, 'receipt_budget' ), 10, 4 );
		( new BusinessRecord() )->register();
		( new BusinessCapacity() )->register();
		( new \Linker\Commerce\Registration\VatNotice() )->register();
		( new IntakeAdmin() )->register();
		add_filter( 'linker_commerce_pending_review_summary', array( IntakeStore::class, 'pending_summary' ), 10, 0 );
		// Acquire the release boundary before other native erasure listeners write.
		add_action( 'woocommerce_privacy_before_remove_order_personal_data', array( IntakeStore::class, 'forget' ), 0 );
		add_action( 'woocommerce_customer_reset_password', array( \Linker\Commerce\Inquiry\ReceiptLimit::class, 'confirmed_mailbox' ) );
		add_action( 'profile_update', array( \Linker\Commerce\Inquiry\ReceiptLimit::class, 'account_updated' ), 10, 2 );
		( new Accounts() )->register();
		add_filter( 'xmlrpc_methods', array( $this, 'xmlrpc_methods' ) );
	}

	/**
	 * The site has no inbound pingback service.
	 *
	 * @param array<string,mixed> $methods Native XML-RPC methods.
	 * @return array<string,mixed>
	 */
	public function xmlrpc_methods( array $methods ): array {
		unset( $methods['pingback.ping'] );
		return $methods;
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
		\Linker\Commerce\Inquiry\Assessment\SendAuthorization::recover_intake();
	}
}
