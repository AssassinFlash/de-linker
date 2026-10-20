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
 * One email a day to the internal notification address, with the blind
 * copies (Options::notify_to() and notify_bcc()), in the site's
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
		$this->description   = __( 'Sent to the internal notification address, with blind copies, every morning at 9:00 (Berlin time).', 'linker-commerce' );
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
		$this->recipient              = $this->options->notify_to();
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
	 * Adds the digest presentation to this email only. WooCommerce inlines it
	 * when the message is sent (docs/specs/74-daily-digest.md).
	 *
	 * @param string $css   The email stylesheet so far.
	 * @param mixed  $email The email being rendered.
	 */
	public static function append_styles( string $css, $email ): string {
		if ( ! is_object( $email ) || ! isset( $email->id ) || self::ID !== $email->id ) {
			return $css;
		}
		return $css . self::presentation_css();
	}

	/**
	 * Presentation for the digest body. Class selectors, so the template stays
	 * free of style attributes.
	 */
	public static function presentation_css(): string {
		return '
			.linker-digest-date { margin: 0 0 16px; color: #787c82; font-size: 13px; }
			.linker-digest-counts { width: 100%; border-collapse: separate; border-spacing: 8px 0; margin: 0 0 8px; }
			.linker-digest-count { width: 33%; background: #f6f2ff; padding: 12px; vertical-align: top; }
			.linker-digest-num { font-size: 28px; line-height: 1; font-weight: 700; color: #8526ff; }
			.linker-digest-name { margin-top: 6px; font-size: 12px; line-height: 1.35; color: #1e1e1e; }
			.linker-digest-rows { width: 100%; border-collapse: collapse; }
			.linker-digest-main { padding: 12px 0; border-bottom: 1px solid #ececee; font-size: 14px; color: #1e1e1e; }
			.linker-digest-detail { color: #4b4b4b; font-size: 13px; }
			.linker-digest-link { display: inline-block; margin-top: 8px; padding: 6px 10px; background: #8526ff; color: #ffffff; font-size: 13px; font-weight: 700; text-decoration: none; }
			.linker-digest-empty { margin: 6px 0; color: #787c82; font-size: 13px; line-height: 1.4; }
			.linker-digest-empty strong { color: #4b4b4b; font-weight: 600; }
		';
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
