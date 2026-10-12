<?php
/**
 * The account page of an account still under review.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Presentation\LoginGate;
use Linker\Commerce\Registration\Approval;

/**
 * A pending account may sign in, and then sees only the review page. The
 * inquiries, prices and the rest of the account stay closed until the team
 * approves. The markup is LoginGate's pending gate, the one place that copy
 * is written. A rejected account never reaches this page: Approval keeps it
 * out at sign-in. A restricted account keeps the workplace and reads its own
 * gate on the Proforma request.
 */
final class PendingGate {

	/**
	 * Sets up the gate.
	 *
	 * @param Approval  $approval The account approval rule.
	 * @param LoginGate $login    The pending-review markup.
	 */
	public function __construct(
		private readonly Approval $approval = new Approval(),
		private readonly LoginGate $login = new LoginGate()
	) {}

	/**
	 * Whether the signed-in account is still under review. Guests and staff
	 * are not: the account page's own login form and staff roles stay as they
	 * are.
	 */
	public function holds(): bool {
		$user_id = \get_current_user_id();
		return $user_id > 0 && Approval::PENDING === $this->approval->status( $user_id );
	}

	/**
	 * Holds a pending account on the review page. Runs on template_redirect,
	 * before any account template prints. An endpoint request is sent back to
	 * the account page. On the account page itself the workplace hooks are
	 * cleared — an older account view prints the inquiries from the dashboard
	 * hook, which fires before the account content — and the review page is
	 * printed in their place.
	 */
	public function redirect(): void {
		if ( ! function_exists( 'is_account_page' ) || ! \is_account_page() || ! $this->holds() ) {
			return;
		}
		if ( function_exists( 'is_wc_endpoint_url' ) && \is_wc_endpoint_url() ) {
			\wp_safe_redirect( \wc_get_page_permalink( 'myaccount' ) );
			return;
		}
		$this->close_workplace();
		\add_action( 'woocommerce_account_content', array( $this, 'render' ), 1 );
	}

	/**
	 * The review page. The workplace hooks were already cleared, so this is
	 * the only account content a pending account reads.
	 */
	public function render(): void {
		if ( ! $this->holds() ) {
			return;
		}
		$products = function_exists( 'wc_get_page_id' ) ? (string) \get_permalink( (int) \wc_get_page_id( 'shop' ) ) : '';
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- LoginGate escapes every value it prints.
		echo $this->login->pending_html( $products );
	}

	/**
	 * Stops the account workplace printing for a pending account. An approved
	 * account never enters here, so its workplace stays.
	 */
	public function close_workplace(): void {
		if ( ! $this->holds() ) {
			return;
		}
		\remove_all_actions( 'woocommerce_account_content' );
		\remove_all_actions( 'woocommerce_account_dashboard' );
	}
}
