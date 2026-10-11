<?php
/**
 * Approval email: the account is rejected.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Registration\Approval;

/**
 * Sent when the team rejects an account: sign-in stays closed, and the team's
 * reason says why.
 */
final class RejectedEmail extends CustomerApprovalEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_approval_rejected';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Account rejected', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when the team rejects the account, with the reason.', 'linker-commerce' );
		$this->template_html = 'emails/linker-approval-rejected.php';
		add_action( Approval::CHANGED_ACTION . '_notification', array( $this, 'trigger' ), 10, 4 );
		parent::__construct( $plugin_file );
	}

	/**
	 * The state this email speaks for.
	 */
	protected function target_status(): string {
		return Approval::REJECTED;
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Your partner account was not approved', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Account not approved', 'linker-commerce' );
	}
}
