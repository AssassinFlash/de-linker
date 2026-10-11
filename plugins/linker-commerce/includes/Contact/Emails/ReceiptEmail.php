<?php
/**
 * Receipt of a contact form message, to the visitor.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact\Emails;

use Linker\Commerce\Contact\Submission;

/**
 * Sent when the contact form is sent: the message arrived, in the language
 * the visitor wrote in (docs/specs/11-commerce.md, Mail; ticket #68). A reply
 * to it goes to the team mailbox.
 */
final class ReceiptEmail extends ContactEmail {


	/**
	 * Email id.
	 */
	public const ID = 'linker_contact_receipt';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id             = self::ID;
		$this->title          = __( 'Contact form receipt', 'linker-commerce' );
		$this->description    = __( 'Sent to the visitor when the contact form is sent.', 'linker-commerce' );
		$this->customer_email = true;
		$this->template_html  = 'emails/linker-contact-receipt.php';
		$this->placeholders   = array( '{name}' => '' );
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the receipt to the visitor who wrote the message.
	 *
	 * @param Submission $submission The visitor's message.
	 */
	public function notify( Submission $submission ): void {
		$this->recipient              = $submission->email;
		$this->placeholders['{name}'] = $submission->name;
		$this->notify_in( $submission, $submission->locale );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'We received your message', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'We received your message', 'linker-commerce' );
	}
}
