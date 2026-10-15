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
 *
 * The page is replaced as a whole (ticket #184): the account template is
 * swapped for the review card, so the workplace shell — sidebar, heading and
 * every endpoint hook — never renders for this account. An endpoint request
 * is sent back to the account page.
 */
final class PendingGate {

	/**
	 * Woo template this gate replaces.
	 */
	private const ACCOUNT_TEMPLATE = 'myaccount/my-account.php';

	/**
	 * The instance the account module registered; the template prints through
	 * it (the same adapter shape AccountTemplates uses), so the wired Approval
	 * and LoginGate are the ones that render.
	 *
	 * @var self|null
	 */
	private static ?self $adapter = null;

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
	 * Registers the gate as the request's own instance and adds its hook; runs
	 * from the account module's register().
	 */
	public function register(): void {
		self::$adapter = $this;
		add_action( 'template_redirect', array( $this, 'redirect' ) );
	}

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
	 * before any account template prints: an endpoint request is sent back to
	 * the account page, and the account page's own template is swapped for
	 * the review card, so the workplace never starts rendering.
	 */
	public function redirect(): void {
		if ( ! function_exists( 'is_account_page' ) || ! \is_account_page() || ! $this->holds() ) {
			return;
		}
		if ( function_exists( 'is_wc_endpoint_url' ) && \is_wc_endpoint_url() ) {
			\wp_safe_redirect( \wc_get_page_permalink( 'myaccount' ) );
			exit;
		}
		\add_filter( 'wc_get_template', array( $this, 'template' ), 40, 2 );
	}

	/**
	 * The account page's own template becomes the review card: the workplace
	 * shell (AccountTemplates, priority 20) never gets the request. Woo's
	 * other templates keep their path.
	 *
	 * @param string $path Located template.
	 * @param string $name Woo template name.
	 */
	public function template( string $path, string $name ): string {
		return self::ACCOUNT_TEMPLATE === $name
			? dirname( __DIR__, 2 ) . '/templates/myaccount/auth/pending.php'
			: $path;
	}

	/**
	 * Called by the account template Woo already loaded. No markup is produced
	 * outside that template.
	 */
	public static function output(): void {
		self::$adapter?->render();
	}

	/**
	 * The review page: LoginGate's one pending card.
	 */
	public function render(): void {
		if ( ! $this->holds() ) {
			return;
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- LoginGate escapes every value it prints.
		echo $this->login->pending_html();
	}
}
