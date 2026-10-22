<?php
/**
 * The email side of Genie: "email me this conversation" (#235) and "Let
 * Linker contact me" (#243).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Inquiry\Checkout;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Settings\Options;
use WP_Error;

/**
 * Genie lives in linker-tools; the site's emails live here (every one a
 * WooCommerce email of this plugin, sent through the Outbox). linker-tools
 * decides whether an email may go and to whom, then asks on two filters;
 * this module answers them (ticket #235, docs/specs/13-genie.md goal 7):
 * SEND_FILTER with ConversationEmail, CONFIRM_FILTER with
 * ConfirmAddressEmail.
 *
 * "Let Linker contact me" (#243) is a contact message that arrives through
 * Genie: linker-tools' contact card route asks on CONTACT_FILTER with the
 * hand-off, and this module sends it through #246's one door for messages,
 * Inquiry\Sender::message() — one record (a Woo order of the contact source),
 * #246's team mail and the customer's receipt under the site's receipt cap.
 * The hand-off rides on the record (HANDOFF_META), and #246's team mail shows
 * it (templates/emails/linker-genie-handoff.php). It also answers
 * MAILBOX_FILTER with the team mailbox customers see.
 */
final class Module {

	/**
	 * The filters linker-tools asks on (Linker\Tools\Genie\ConversationMail).
	 */
	public const SEND_FILTER    = 'linker_tools_genie_send_conversation';
	public const CONFIRM_FILTER = 'linker_tools_genie_confirm_address';

	/**
	 * The filter linker-tools asks with a contact request's hand-off
	 * (Linker\Tools\Genie\ContactRequest::CONTACT_FILTER).
	 */
	public const CONTACT_FILTER = 'linker_tools_genie_contact_team';

	/**
	 * The filter linker-tools asks with the inquiry confirmation card's details
	 * (Linker\Tools\Genie\InquiryRequest::SEND_FILTER, #250). The answer is the
	 * record and whether the receipt went, or a WP_Error when Woo refused it.
	 */
	public const INQUIRY_FILTER = 'linker_tools_genie_inquiry_send';

	/**
	 * The filter that names the request page in the card's language
	 * (Linker\Tools\Genie\InquiryRequest::PAGE_FILTER): Checkout::request_url().
	 */
	public const INQUIRY_PAGE_FILTER = 'linker_genie_inquiry_page';

	/**
	 * The record's meta that keeps the hand-off for the team mail and the
	 * inquiry screen.
	 */
	public const HANDOFF_META = '_linker_genie_handoff';

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
		add_filter( self::SEND_FILTER, array( $this, 'send' ), 10, 2 );
		add_filter( self::CONFIRM_FILTER, array( $this, 'confirm' ), 10, 2 );
		add_filter( self::MAILBOX_FILTER, array( $this, 'mailbox' ) );
		add_filter( self::CONTACT_FILTER, array( $this, 'contact' ), 10, 2 );
		add_filter( self::INQUIRY_FILTER, array( $this, 'inquiry' ), 10, 2 );
		add_filter( self::INQUIRY_PAGE_FILTER, array( $this, 'inquiry_page' ), 10, 2 );
	}

	/**
	 * Sends a contact request through #246's door; the CONTACT_FILTER answer.
	 *
	 * The customer's last message is the record's message; the rest of the
	 * hand-off (why, the page, the conversation, the solution draft) rides on
	 * the record for the team mail. A guest gives an email address only, so
	 * the name may be empty (Submission::from_handoff()); the card asked for
	 * the consent a guest gives, and an account's customer gave it at sign-up.
	 *
	 * @param mixed $sent    An earlier answer: an array when another listener sent it.
	 * @param mixed $handoff The hand-off (Linker\Tools\Genie\ContactRequest::handoff()).
	 * @return array{order: int, receipt: bool}|null The record and whether the receipt went; null when the hand-off is not one.
	 */
	public function contact( mixed $sent, mixed $handoff ): array|WP_Error|null {
		if ( is_array( $sent ) && isset( $sent['order'] ) ) {
			return array(
				'order'   => (int) $sent['order'],
				'receipt' => ! empty( $sent['receipt'] ),
			);
		}
		if ( ! is_array( $handoff ) || ! is_array( $handoff['customer'] ?? null ) ) {
			return null;
		}
		$summary = is_array( $handoff['summary'] ?? null ) ? $handoff['summary'] : array();
		$details = Submission::from_handoff(
			array(
				'name'    => (string) ( $handoff['customer']['name'] ?? '' ),
				'email'   => (string) ( $handoff['customer']['email'] ?? '' ),
				'message' => (string) ( $summary[0] ?? $handoff['reason_label'] ?? '' ),
				'consent' => '1',
				'lang'    => (string) ( $handoff['locale'] ?? 'en' ),
			)
		);
		if ( $details instanceof WP_Error ) {
			return null;
		}
		$order = ( new Sender() )->message( $details, array( self::HANDOFF_META => $handoff ) );
		if ( $order instanceof WP_Error ) {
			return $order;
		}
		return array(
			'order'   => $order->get_id(),
			'receipt' => '' === (string) $order->get_meta( ReceiptLimit::SKIPPED_META ),
		);
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
	 * Sends the inquiry the Genie confirmation card showed (#250); the
	 * INQUIRY_FILTER answer.
	 *
	 * The card's own details go through the request page's validation
	 * (Submission::from_post with the guest form's required fields) and then
	 * through the one writer, Inquiry\Sender::request(): the same Woo record,
	 * Proforma gateway, statuses, team mail and receipt the request page makes.
	 * The summary is the card's choice: the exact #244 summary it showed, or
	 * false when the customer turned it off.
	 *
	 * @param mixed $sent    An earlier answer: an array when another listener sent it.
	 * @param mixed $details The card's details (InquiryRequest::send()).
	 * @return array{order: int, receipt: bool}|WP_Error|null
	 */
	public function inquiry( mixed $sent, mixed $details ): array|WP_Error|null {
		if ( is_array( $sent ) && isset( $sent['order'] ) ) {
			return array(
				'order'   => (int) $sent['order'],
				'receipt' => ! empty( $sent['receipt'] ),
			);
		}
		if ( ! is_array( $details ) || ! is_array( $details['customer'] ?? null ) ) {
			return null;
		}
		$context = array(
			'conversation' => $details['conversation'] ?? 0,
			'page'         => $details['page'] ?? array(),
		);
		$summary = $details['summary'] ?? false;
		$details = Submission::from_post(
			array(
				'name'    => (string) ( $details['customer']['name'] ?? '' ),
				'email'   => (string) ( $details['customer']['email'] ?? '' ),
				'company' => (string) ( $details['customer']['company'] ?? '' ),
				'message' => (string) ( $details['message'] ?? '' ),
				// A guest ticked the card's consent; an account's customer
				// gave it at sign-up (the request page sends the same).
				'consent' => '1',
				'lang'    => (string) ( $details['locale'] ?? 'en' ),
			),
			false
		);
		if ( $details instanceof WP_Error ) {
			return $details;
		}
		$order = ( new Sender() )->request( $details, array(), is_array( $summary ) ? $summary : false, $context );
		if ( $order instanceof WP_Error ) {
			return $order;
		}
		return array(
			'order'   => $order->get_id(),
			'receipt' => '' === (string) $order->get_meta( ReceiptLimit::SKIPPED_META ),
		);
	}

	/**
	 * The request page in the card's language; the INQUIRY_PAGE_FILTER answer.
	 *
	 * @param mixed $url    An earlier answer.
	 * @param mixed $locale The card's language (en/de).
	 */
	public function inquiry_page( mixed $url, mixed $locale = 'en' ): string {
		if ( is_string( $url ) && '' !== $url ) {
			return $url;
		}
		return Checkout::request_url( 'de' === $locale ? 'de' : 'en' );
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
		$producer = new ConversationEmail( $this->plugin_file );
		if ( is_array( $email ) && is_callable( $email['accepted'] ?? null ) && is_callable( $email['defer'] ?? null ) ) {
			$message = \Linker\Commerce\Mail\Prepared::capture( fn () => $producer->notify( $conversation ) );
			if ( ! $message instanceof \Linker\Commerce\Mail\Message ) {
				return false; }
			$job = ( new \Linker\Commerce\Mail\JobStore() )->create(
				$message,
				0,
				static function ( int $id ) use ( $email ): void {
					$email['accepted']( $id );
					// The same existing Action Scheduler row survives a crash after
					// commit but before the immediate outside-lock attempt.
					$action = as_schedule_single_action( time() + 1, \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP, true );
					if ( $action < 1 && ! as_has_scheduled_action( \Linker\Commerce\Mail\Outbox::HOOK, array( $id ), \Linker\Commerce\Mail\Outbox::GROUP ) ) {
						throw new \RuntimeException( 'conversation_confirmation_schedule_failed' );
					}
				}
			);
			if ( $job < 1 ) {
				\Linker\Commerce\Mail\CapacityHealth::failed();
				return false; }
			$email['defer'](
				static function () use ( $job ): void {
					/** This action is documented in Mail\Module::register(). */
					do_action( \Linker\Commerce\Mail\Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing original-job consumer after source lock release.
				}
			);
			return true;
		}
		return $producer->notify( $conversation );
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
