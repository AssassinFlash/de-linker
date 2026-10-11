<?php
/**
 * Approval email: the account is approved.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Registration\Approval;

/**
 * Sent when the team approves an account: net prices open, and the solution
 * draft and the Proforma request are usable.
 */
final class ApprovedEmail extends CustomerApprovalEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_approval_approved';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Account approved', 'linker-commerce' );
		$this->description   = __( 'Sent to the customer when the team approves the account.', 'linker-commerce' );
		$this->template_html = 'emails/linker-approval-approved.php';
		add_action( Approval::CHANGED_ACTION . '_notification', array( $this, 'trigger' ), 10, 4 );
		parent::__construct( $plugin_file );
	}

	/**
	 * The state this email speaks for.
	 */
	protected function target_status(): string {
		return Approval::APPROVED;
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Your partner account is approved', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Partner account approved', 'linker-commerce' );
	}
}
