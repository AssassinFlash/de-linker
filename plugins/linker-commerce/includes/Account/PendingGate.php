<?php
/**
 * The pending account's status within its usable workspace.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Registration\Approval;

/** Approval controls prices; this adapter only supplies the account status. */
final class PendingGate {

	/**
	 * Sets up the status notice.
	 *
	 * @param Approval  $approval The account approval rule.
	 * @param LoginGate $login    The pending status markup.
	 */
	public function __construct(
		private readonly Approval $approval = new Approval(),
		private readonly LoginGate $login = new LoginGate()
	) {}

	/** Adds the status before Woo's endpoint dispatcher (native priority 10). */
	public function register(): void {
		add_action( 'woocommerce_account_content', array( $this, 'render' ), 5 );
	}

	/** A pending account reads its status alongside the normal endpoint content. */
	public function render(): void {
		$user_id = get_current_user_id();
		if ( $user_id <= 0 || Approval::PENDING !== $this->approval->status( $user_id ) ) {
			return;
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- LoginGate escapes every value supplied to the LC fragment.
		echo $this->login->pending_html();
	}
}
