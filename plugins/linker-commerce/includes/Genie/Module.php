<?php
/**
 * The email side of Genie: "email me this conversation" (#235) and "Let
 * Linker contact me" (#243).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

use Linker\Commerce\Settings\Options;

/**
 * Genie lives in linker-tools; the site's emails live here (every one a
 * WooCommerce email of this plugin, sent through the Outbox). linker-tools
 * decides whether an email may go and to whom, then asks on two filters;
 * this module answers them (ticket #235, docs/specs/13-genie.md goal 7):
 * SEND_FILTER with ConversationEmail, CONFIRM_FILTER with
 * ConfirmAddressEmail.
 *
 * "Let Linker contact me" (#243): linker-tools' contact card route fires
 * ACTION with the hand-off; this module makes it one of WooCommerce's
 * transactional email actions and registers the team mail that answers it
 * (ContactEmail, a Mail\TeamEmail), so it goes through Woo's mailer and the
 * Outbox like every other internal notification; and it answers
 * MAILBOX_FILTER with the team mailbox customers see.
 */
final class Module {

	/**
	 * The filters linker-tools asks on (Linker\Tools\Genie\ConversationMail).
	 */
	public const SEND_FILTER    = 'linker_tools_genie_send_conversation';
	public const CONFIRM_FILTER = 'linker_tools_genie_confirm_address';

	/**
	 * The action linker-tools fires with a contact request's hand-off
	 * (Linker\Tools\Genie\ContactRequest::ACTION). Here, not on the email
	 * class: WooCommerce reads the action list before it loads WC_Email.
	 */
	public const ACTION = 'linker_genie_contact_requested';

	/**
	 * The filter the contact card's route reads the team mailbox from
	 * (Linker\Tools\Genie\ContactRequest::MAILBOX_FILTER).
	 */
	public const MAILBOX_FILTER = 'linker_genie_team_mailbox';

	/**
	 * Sets up the module.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings (internal notification recipients, team mailbox).
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly Options $options
	) {}

	/**
	 * Adds the module's hooks.
	 */
	public function register(): void {
		add_filter( 'woocommerce_email_classes', array( $this, 'add_emails' ) );
		add_filter( 'woocommerce_email_actions', array( $this, 'email_actions' ) );
		add_filter( self::SEND_FILTER, array( $this, 'send' ), 10, 2 );
		add_filter( self::CONFIRM_FILTER, array( $this, 'confirm' ), 10, 2 );
		add_filter( self::MAILBOX_FILTER, array( $this, 'mailbox' ) );
	}

	/**
	 * WooCommerce sends emails only on the actions in this list.
	 *
	 * @param string[] $actions Actions.
	 * @return string[]
	 */
	public function email_actions( array $actions ): array {
		$actions[] = self::ACTION;
		return $actions;
	}

	/**
	 * The team mailbox customers see, for the contact card's refusals.
	 *
	 * @return string Options::team_mailbox().
	 */
	public function mailbox(): string {
		return $this->options->team_mailbox();
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
		$emails[ ContactEmail::class ]        = new ContactEmail( $this->plugin_file, $this->options );
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
