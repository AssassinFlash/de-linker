<?php
/**
 * A Genie conversation, to the visitor who asked for it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

/**
 * Sent when a visitor asks Genie to email them a conversation (ticket #235,
 * docs/specs/13-genie.md goal 7, acceptance A12): every message and the
 * products the answers showed, in the language of the page it was asked
 * from, to the visitor's address alone (the account's, or a guest's address
 * once its confirmation link was opened). A reply goes to the team, like
 * every customer email of the site.
 */
final class ConversationEmail extends GenieEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_genie_conversation';

	/**
	 * Sets up the email.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( string $plugin_file ) {
		$this->id            = self::ID;
		$this->title         = __( 'Genie conversation', 'linker-commerce' );
		$this->description   = __( 'Sent when someone asks for a copy of a Genie conversation by email.', 'linker-commerce' );
		$this->template_html = 'emails/linker-genie-conversation.php';
		parent::__construct( $plugin_file );
	}

	/**
	 * Sends the conversation to the visitor, in its language.
	 *
	 * @param Conversation $conversation The conversation.
	 * @return bool Whether wp_mail() took it.
	 */
	public function notify( Conversation $conversation ): bool {
		$this->object = $conversation;
		return $this->send_to( $conversation->to, $conversation->locale );
	}

	/** Native validated full transcript.
	 *
	 * @param Conversation $conversation Native validated full transcript.
	 */
	public function capture( Conversation $conversation ): ?\Linker\Commerce\Mail\Message {
		return \Linker\Commerce\Mail\Capture::run(
			$this,
			function () use ( $conversation ): void {
				$this->notify( $conversation );
			}
		);
	}

	/**
	 * The template's conversation.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array( 'conversation' => $this->object );
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Your conversation with Genie', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Your conversation with Genie', 'linker-commerce' );
	}
}
