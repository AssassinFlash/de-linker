<?php
/**
 * A message from the contact form, to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact\Emails;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Settings\Options;

/**
 * Sent to the internal notification address when the contact form is sent,
 * with a blind copy to each address of the settings (WooCommerce → Settings →
 * Inquiries; the same rule every internal notification follows,
 * Options::notify_to()). Written in the site's language; a reply goes to the
 * visitor.
 */
final class TeamMessageEmail extends ContactEmail {


	/**
	 * Email id.
	 */
	public const ID = 'linker_contact_message';

	/**
	 * The message the letter is about, once notify() ran.
	 *
	 * @var Submission|null
	 */
	private ?Submission $submission = null;

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, private readonly Options $options ) {
		$this->id            = self::ID;
		$this->title         = __( 'Contact form message', 'linker-commerce' );
		$this->description   = __( 'Sent to the internal notification address, with blind copies, when the contact form is sent.', 'linker-commerce' );
		$this->template_html = 'emails/linker-contact-team.php';
		$this->placeholders  = array( '{name}' => '' );
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the letter to the internal notification address.
	 *
	 * @param Submission $submission The visitor's message.
	 */
	public function notify( Submission $submission ): void {
		$this->submission             = $submission;
		$this->recipient              = $this->options->notify_to();
		$this->placeholders['{name}'] = $submission->name;
		$this->notify_in( $submission, LocaleSwitch::site_default() );
	}

	/**
	 * Internal notifications identify the sender as Linker (#286).
	 *
	 * @param string $from_name Sender name passed by WordPress.
	 */
	public function get_from_name( $from_name = '' ) {
		return $this->options->notify_sender()->name;
	}

	/**
	 * WC_Email applies this address while sending; Outbox preserves it for retries.
	 *
	 * @param string $from_email Sender address passed by WordPress.
	 */
	public function get_from_address( $from_email = '' ) {
		return $this->options->notify_sender()->email;
	}

	/**
	 * The reply address (the visitor) and the blind copies of the settings.
	 */
	public function get_headers() {
		$header  = 'Content-Type: ' . $this->get_content_type() . "\r\n";
		$header .= Message::INTERNAL_HEADER . "\r\n";
		if ( $this->submission instanceof Submission ) {
			$header .= 'Reply-to: ' . $this->submission->name . ' <' . $this->submission->email . ">\r\n";
		}
		$bcc = $this->options->notify_bcc();
		if ( array() !== $bcc ) {
			$header .= 'Bcc: ' . implode( ', ', $bcc ) . "\r\n";
		}
		/**
	* This filter is documented in woocommerce/includes/emails/class-wc-email.php
*/
		return apply_filters( 'woocommerce_email_headers', $header, $this->id, $this->object, $this ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- WooCommerce's own filter, applied as WC_Email::get_headers() applies it.
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {name}: the visitor's name. */
		return __( 'New message from {name}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'New message from the contact form', 'linker-commerce' );
	}
}
