<?php
/**
 * Approval email: the account is restricted.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Registration\Approval;

/**
 * Sent when the team restricts an account: the products and the open inquiry
 * stay open, net prices and the Proforma request are paused, and the team's
 * reason says why.
 */
final class RestrictedEmail extends CustomerApprovalEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_approval_restricted';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Account restricted', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when the team restricts the account, with the reason.', 'linker-commerce' );
		$this->template_html = 'emails/linker-approval-restricted.php';
		add_action( Approval::CHANGED_ACTION . '_notification', array( $this, 'trigger' ), 10, 4 );
		parent::__construct( $plugin_file );
	}

	/**
	 * The state this email speaks for.
	 */
	protected function target_status(): string {
		return Approval::RESTRICTED;
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Your partner account access is limited', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Access limited', 'linker-commerce' );
	}
}
