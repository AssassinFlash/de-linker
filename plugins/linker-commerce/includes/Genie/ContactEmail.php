<?php
/**
 * A customer asks Genie for the team's contact: the mail to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Settings\Options;
use WP_User;

/**
 * Sent to the internal notification address, with the settings' blind copies
 * (Mail\TeamEmail), when a customer asks Genie for the team's contact (#243,
 * docs/specs/13-genie.md goal 6, A6): why Genie offered it, who asks and where
 * to reply, the page, the customer's last messages, the solution draft, and
 * the link to the whole conversation. A reply goes to the customer.
 *
 * The hand-off is linker-tools' (Linker\Tools\Genie\ContactRequest::handoff()),
 * passed as the argument of Module::ACTION.
 */
final class ContactEmail extends TeamEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_genie_contact';

	/**
	 * The hand-off of the request, once trigger() ran.
	 *
	 * @var array<string, mixed>
	 */
	private array $handoff = array();

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, Options $options ) {
		$this->id            = self::ID;
		$this->title         = __( 'Genie contact request', 'linker-commerce' );
		$this->description   = __( 'Sent to the internal notification address, with blind copies, when a customer sends a contact request from Genie.', 'linker-commerce' );
		$this->template_html = 'emails/linker-genie-contact.php';
		$this->placeholders  = array( '{customer}' => '' );
		add_action( Module::ACTION . '_notification', array( $this, 'trigger' ) );
		parent::__construct( $plugin_file, $options );
	}

	/**
	 * Sends the mail about one hand-off.
	 *
	 * @param mixed $handoff The hand-off (ContactRequest::handoff() in linker-tools).
	 */
	public function trigger( $handoff ): void {
		if ( ! is_array( $handoff ) || ! is_array( $handoff['customer'] ?? null ) || ! is_email( (string) ( $handoff['customer']['email'] ?? '' ) ) ) {
			return;
		}
		$this->handoff                    = $handoff;
		$customer                         = $handoff['customer'];
		$name                             = trim( (string) ( $customer['name'] ?? '' ) );
		$this->placeholders['{customer}'] = '' !== $name ? $name : (string) $customer['email'];
		$user                             = (int) ( $customer['user_id'] ?? 0 ) > 0 ? get_userdata( (int) $customer['user_id'] ) : false;
		$this->notify( $user instanceof WP_User ? $user : null );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		/* translators: {customer}: the customer's name, or their email address when no name is known. */
		return __( 'Contact request from {customer} via Genie', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'New contact request via Genie', 'linker-commerce' );
	}

	/**
	 * The reply goes to the address the customer gave or their account's.
	 */
	protected function reply_to(): string {
		$customer = is_array( $this->handoff['customer'] ?? null ) ? $this->handoff['customer'] : array();
		$email    = (string) ( $customer['email'] ?? '' );
		if ( ! is_email( $email ) ) {
			return '';
		}
		$name = trim( (string) ( $customer['name'] ?? '' ) );
		return '' !== $name ? $name . ' <' . $email . '>' : $email;
	}

	/**
	 * The hand-off for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array( 'handoff' => $this->handoff );
	}
}
