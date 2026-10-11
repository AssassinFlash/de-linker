<?php
/**
 * The daily digest, to the team.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Digest;

use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\TeamEmail;
use Linker\Commerce\Settings\Options;

/**
 * One email a day to the team mailbox, with the blind copies, in the site's
 * language, as HTML (docs/specs/74-daily-digest.md). It goes out through
 * wp_mail() like every email of the site, so the Outbox queues and retries it
 * like every email of the site; it is sent whether the blocks have items or
 * not — a missing digest is a broken pipe, not a quiet day.
 */
final class DigestEmail extends TeamEmail {

	/**
	 * Email id.
	 */
	public const ID = 'linker_digest';

	/**
	 * The blocks of the digest being rendered.
	 *
	 * @var Block[]
	 */
	private array $blocks = array();

	/**
	 * Sets up the email.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings.
	 */
	public function __construct( string $plugin_file, Options $options ) {
		$this->id            = self::ID;
		$this->title         = __( 'Daily digest', 'linker-commerce' );
		$this->description   = __( 'Sent to the team mailbox, with blind copies, every morning at 9:00 (Berlin time).', 'linker-commerce' );
		$this->template_html = 'emails/linker-digest.php';
		$this->placeholders  = array( '{date}' => '' );
		parent::__construct( $plugin_file, $options );
	}

	/**
	 * Renders and sends today's digest.
	 *
	 * @param Block[] $blocks The blocks, in order.
	 */
	public function send_report( array $blocks ): void {
		$this->blocks = $blocks;
		// WC_Email's "no object" value: there is no customer to reply to.
		$this->object                 = false;
		$this->recipient              = $this->options->team_to();
		$this->placeholders['{date}'] = Format::today();
		$this->locale_switch->to( LocaleSwitch::site_default() );
		try {
			$this->send_notification();
		} finally {
			$this->locale_switch->back();
		}
	}

	/**
	 * Default subject.
	 */
	public function get_default_subject() {
		return __( 'Daily digest, {date}', 'linker-commerce' );
	}

	/**
	 * Default heading.
	 */
	public function get_default_heading() {
		return __( 'Daily digest', 'linker-commerce' );
	}

	/**
	 * The blocks for the template.
	 *
	 * @return array<string, mixed>
	 */
	protected function template_args(): array {
		return array( 'blocks' => $this->blocks );
	}
}
