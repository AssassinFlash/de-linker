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
			body, #outer_wrapper, #wrapper, #inner_wrapper, #template_container, #template_body, #body_content, #template_header, #header_wrapper, #body_content_inner_cell { background-color: #f5f5f7; }
			body, #wrapper, #header_wrapper h1, .email-logo-text, .linker-digest-title, .linker-digest-main { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif; }
			#template_header_image { padding: 36px 28px 0; }
			.email-logo-text, .email-logo-text a { color: #6e6e73; font-size: 15px; font-weight: 600; letter-spacing: -0.01em; text-transform: none; }
			#header_wrapper { padding: 4px 28px 0; }
			#header_wrapper h1 { color: #1d1d1f; font-size: 32px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.1; }
			#body_content_inner_cell { padding: 4px 28px 12px; }
			#credit { border-top: 0; color: #86868b; padding: 8px 28px 36px; }
			.linker-digest-date { margin: 6px 0 22px; color: #86868b; font-size: 17px; line-height: 1.3; }
			.linker-digest-card { width: 100%; background-color: #ffffff; border: 0; border-radius: 18px; margin: 0 0 16px; }
			.linker-digest-num { width: 52px; padding: 22px 0 6px 20px; font-size: 22px; line-height: 1.1; font-weight: 600; color: #1d1d1f; vertical-align: middle; }
			.linker-digest-title { padding: 22px 20px 6px 0; font-size: 17px; line-height: 1.25; font-weight: 600; color: #1d1d1f; vertical-align: middle; }
			.linker-digest-body { padding: 0 8px 8px 20px; }
			.linker-digest-rows { width: 100%; }
			.linker-digest-main { padding: 16px 0; border-top: 1px solid #d2d2d7; font-size: 15px; line-height: 1.35; font-weight: 400; color: #1d1d1f; }
			.linker-digest-detail { color: #86868b; font-size: 13px; line-height: 1.35; }
			.linker-digest-act { width: 100%; margin-top: 8px; }
			.linker-digest-link { color: #0066cc; font-size: 15px; font-weight: 400; text-decoration: none; }
			.linker-digest-quiet { width: 100%; background-color: transparent; border: 0; margin: 18px 0 0; }
			.linker-digest-empty { padding: 8px 4px; border-top: 0; color: #86868b; font-size: 13px; line-height: 1.35; }
			.linker-digest-empty strong { color: #6e6e73; font-weight: 600; }
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
