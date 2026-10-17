<?php
/**
 * The address confirmation a guest gets before a conversation is emailed.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

/**
 * A guest who asks for a conversation by email first gets this (ticket #235,
 * review round 1): fixed words and a one-time link, nothing of the
 * conversation, so an address typed by someone else receives no text that
 * person wrote. The conversation follows once the link is opened.
 */
final class ConfirmAddressEmail extends GenieEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_genie_confirm_address';

	/**
	 * The confirmation link.
	 *
	 * @var string
	 */
	private string $link = '';

	/**
	 * How many hours the link works.
	 *
	 * @var int
	 */
	private int $hours = 0;

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Genie conversation: address confirmation', 'linker-commerce' );
		$this->description   = __( 'Sent to the address a visitor without an account enters to get a Genie conversation by email. It holds only a link that confirms the address; the conversation follows after the click.', 'linker-commerce' );
		$this->template_html = 'emails/linker-genie-confirm-address.php';
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the link.
	 *
	 * @param string $to     The guest's address.
	 * @param string $locale WordPress locale.
	 * @param string $link   The one-time link.
	 * @param int    $hours  How many hours it works.
	 * @return bool Whether wp_mail() took it.
	 */
	public function notify( string $to, string $locale, string $link, int $hours ): bool {
		$this->object = false;
		$this->link   = $link;
		$this->hours  = $hours;
		return $this->send_to( $to, $locale );
	}

	/**
	 * The template's link and lifetime.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array(
			'link'  => $this->link,
			'hours' => $this->hours,
		);
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Conversation with Genie requested for this email address', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Confirm your email address', 'linker-commerce' );
	}
}
