<?php
/**
 * An email to the customer about their account's approval.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration\Emails;

use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Prepared;
use WC_Email;
use WP_User;

/**
 * Base of the three customer emails about the approval state: sent to the
 * customer's address, in the customer's own language (WordPress's user locale,
 * recorded at registration), as HTML, from a template of this plugin (a theme
 * may override it in woocommerce/emails/). Each concrete email speaks when the
 * state changes to its own; the team's reason travels with the change.
 */
abstract class CustomerApprovalEmail extends WC_Email {
	/** Immutable native messages staged only for their actual producer.
	 *
	 * @var array<int,array{message:Message,reservation:array<string,mixed>}>
	 */
	private array $prepared = array();

	/**
	 * The state is known before user meta changes; preview has no account writes.
	 *
	 * @param int    $id Customer.
	 * @param string $previous Existing state.
	 * @param string $current Desired state.
	 * @param string $reason Complete staff reason, never truncated.
	 */
	public function preview_approval( int $id, string $previous, string $current, string $reason ): ?Message {
		return $current === $this->target_status() ? Prepared::capture( fn () => $this->trigger( $id, $previous, $current, $reason ) ) : null;
	}

	/**
	 * Stage only this exact native notification's pre-reservation.
	 *
	 * @param int                 $id Customer.
	 * @param Message             $message Immutable preview.
	 * @param array<string,mixed> $reservation Server-only capacity.
	 */
	public function stage( int $id, Message $message, array $reservation ): void {
		$this->prepared[ $id ] = array(
			'message'     => $message,
			'reservation' => $reservation,
		);
	}

	/**
	 * The language switch.
	 *
	 * @var LocaleSwitch
	 */
	protected LocaleSwitch $locale_switch;

	/**
	 * The reason the team gave for the change.
	 *
	 * @var string
	 */
	protected string $change_reason = '';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->customer_email = true;
		$this->template_base  = plugin_dir_path( $plugin_file ) . 'templates/';
		$this->locale_switch  = new LocaleSwitch();
		parent::__construct();
	}

	/**
	 * The state this email speaks for.
	 */
	abstract protected function target_status(): string;

	/**
	 * Sends the email about a changed approval state; runs on the change
	 * action's "_notification" form, which carries the four arguments of
	 * Approval::CHANGED_ACTION.
	 *
	 * @param int    $user_id  Customer.
	 * @param string $previous State before.
	 * @param string $current  State now.
	 * @param string $reason   The reason the team gave.
	 * @throws \RuntimeException A staged critical notice was not durably accepted.
	 */
	public function trigger( $user_id, $previous = '', $current = '', $reason = '' ): void {
		if ( (string) $current !== $this->target_status() ) {
			return;
		}
		$user = get_userdata( (int) $user_id );
		if ( ! $user instanceof WP_User ) {
			return;
		}
		$this->object        = $user;
		$this->recipient     = $user->user_email;
		$this->change_reason = (string) $reason;

		$this->locale_switch->to( get_user_locale( $user->ID ) );
		try {
			$prepared = $this->prepared[ $user->ID ] ?? null;
			unset( $this->prepared[ $user->ID ] );
			if ( null === $prepared ) {
				$this->send_notification();
			} else {
				$accepted = Capacity::within( $prepared['reservation'], fn () => Prepared::within( $prepared['message'], fn () => $this->send_notification() ) );
				if ( ! $accepted ) {
					throw new \RuntimeException( 'approval_notice_not_accepted' );
				}
			}
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * The language switch happens in trigger(); WooCommerce's switch to the
	 * site language stays off for these emails.
	 */
	public function setup_locale(): void {}

	/**
	 * See setup_locale().
	 */
	public function restore_locale(): void {}

	/**
	 * The subject in the customer's language. WooCommerce's settings cache
	 * keeps the first default a render filled in, so one request sending for
	 * customers of two languages would keep the first language for the rest;
	 * these emails re-read their stored settings per render (a subject staff
	 * saved still wins, an unsaved one is taken fresh in the render language).
	 */
	public function get_subject() {
		$this->init_settings();
		return parent::get_subject();
	}

	/**
	 * The heading in the customer's language; see get_subject().
	 */
	public function get_heading() {
		$this->init_settings();
		return parent::get_heading();
	}

	/**
	 * These emails are HTML only.
	 */
	public function get_email_type() {
		return 'html';
	}

	/**
	 * The only format offered in the email settings.
	 *
	 * @return array<string, string>
	 */
	public function get_email_type_options() {
		return array( 'html' => __( 'HTML', 'linker-commerce' ) );
	}

	/**
	 * The HTML body.
	 */
	public function get_content_html() {
		return wc_get_template_html(
			$this->template_html,
			array(
				'email_heading'      => $this->get_heading(),
				'additional_content' => $this->get_additional_content(),
				'sent_to_admin'      => false,
				'plain_text'         => false,
				'email'              => $this,
			) + $this->template_args(),
			'',
			$this->template_base
		);
	}

	/**
	 * Plain text is not offered; WooCommerce asks for it only for plain or multipart emails.
	 */
	public function get_content_plain() {
		return '';
	}

	/**
	 * No default closing paragraph.
	 */
	public function get_default_additional_content() {
		return '';
	}

	/**
	 * The customer and the reason for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array(
			'customer' => $this->object,
			'reason'   => $this->change_reason,
		);
	}
}
