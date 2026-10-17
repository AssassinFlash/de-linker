<?php
/**
 * The email side of Genie's "email me this conversation".
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

/**
 * Genie lives in linker-tools; the site's emails live here (every one a
 * WooCommerce email of this plugin, sent through the Outbox). linker-tools
 * decides whether an email may go and to whom, then asks on two filters;
 * this module answers them (ticket #235, docs/specs/13-genie.md goal 7):
 * SEND_FILTER with ConversationEmail, CONFIRM_FILTER with
 * ConfirmAddressEmail.
 */
final class Module {

	/**
	 * The filters linker-tools asks on (Linker\Tools\Genie\ConversationMail).
	 */
	public const SEND_FILTER    = 'linker_tools_genie_send_conversation';
	public const CONFIRM_FILTER = 'linker_tools_genie_confirm_address';

	/**
	 * Sets up the module.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'woocommerce_email_classes', array( $this, 'add_emails' ) );
		add_filter( self::SEND_FILTER, array( $this, 'send' ), 10, 2 );
		add_filter( self::CONFIRM_FILTER, array( $this, 'confirm' ), 10, 2 );
	}

	/**
	 * Adds the emails to WooCommerce's list, so they have their settings screens.
	 *
	 * @param array<string, mixed> $emails Email objects by class.
	 * @return array<string, mixed>
	 */
	public function add_emails( array $emails ): array {
		$emails[ ConversationEmail::class ]   = new ConversationEmail( $this->plugin_file );
		$emails[ ConfirmAddressEmail::class ] = new ConfirmAddressEmail( $this->plugin_file );
		return $emails;
	}

	/**
	 * Sends one conversation; the SEND_FILTER answer.
	 *
	 * WooCommerce's mailer is loaded first: it hangs the header and footer
	 * of every site email on their actions. Each send is a new email object
	 * (GenieEmail).
	 *
	 * @param mixed $sent  An earlier answer: true when another listener sent it.
	 * @param mixed $email to, locale, messages.
	 */
	public function send( mixed $sent, mixed $email ): bool {
		if ( true === $sent ) {
			return true;
		}
		$conversation = Conversation::from_array( is_array( $email ) ? $email : array() );
		if ( null === $conversation ) {
			return false;
		}
		WC()->mailer();
		return ( new ConversationEmail( $this->plugin_file ) )->notify( $conversation );
	}

	/**
	 * Sends an address confirmation; the CONFIRM_FILTER answer.
	 *
	 * @param mixed $sent  An earlier answer: true when another listener sent it.
	 * @param mixed $email to, locale, link, hours.
	 */
	public function confirm( mixed $sent, mixed $email ): bool {
		if ( true === $sent ) {
			return true;
		}
		$email = is_array( $email ) ? $email : array();
		$to    = isset( $email['to'] ) && is_string( $email['to'] ) ? $email['to'] : '';
		$link  = isset( $email['link'] ) && is_string( $email['link'] ) ? $email['link'] : '';
		if ( ! is_email( $to ) || ! str_starts_with( $link, admin_url( 'admin-post.php' ) ) ) {
			return false;
		}
		$locale = isset( $email['locale'] ) && is_string( $email['locale'] ) && str_starts_with( strtolower( $email['locale'] ), 'de' ) ? 'de_DE_formal' : 'en_US';
		WC()->mailer();
		return ( new ConfirmAddressEmail( $this->plugin_file ) )->notify( $to, $locale, $link, max( 1, (int) ( $email['hours'] ?? 0 ) ) );
	}
}
