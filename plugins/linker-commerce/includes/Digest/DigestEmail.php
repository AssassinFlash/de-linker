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
			body, #outer_wrapper, #wrapper, #inner_wrapper, #template_container, #template_body, #body_content { background-color: #f4f4f5; }
			#template_header_image { padding: 28px 32px 0; }
			.email-logo-text, .email-logo-text a { color: #71717a; font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; }
			#template_header, #header_wrapper { background-color: #f4f4f5; }
			#header_wrapper { padding: 8px 32px 0; }
			#header_wrapper h1 { color: #18181b; font-size: 28px; font-weight: 650; letter-spacing: -0.4px; }
			#body_content_inner_cell { background-color: #f4f4f5; padding: 8px 32px 8px; }
			#credit { border-top: 0; color: #a1a1aa; padding: 8px 32px 28px; }
			.linker-digest-date { margin: 0 0 16px; color: #71717a; font-size: 13px; }
			.linker-digest-card { width: 100%; background-color: #ffffff; border: 1px solid #e6e6ea; border-radius: 12px; margin: 0 0 12px; }
			.linker-digest-num { width: 56px; padding: 16px 0 4px 16px; font-size: 26px; line-height: 1; font-weight: 700; color: #18181b; vertical-align: top; }
			.linker-digest-title { padding: 18px 16px 4px 0; font-size: 15px; line-height: 1.35; font-weight: 650; color: #18181b; vertical-align: top; }
			.linker-digest-body { padding: 0 16px 8px; }
			.linker-digest-rows { width: 100%; }
			.linker-digest-main { padding: 12px 0; border-top: 1px solid #f0f0f2; font-size: 14px; line-height: 1.45; color: #18181b; }
			.linker-digest-detail { color: #71717a; font-size: 12px; }
			.linker-digest-link { color: #6d28d9; font-size: 13px; font-weight: 600; text-decoration: none; }
			.linker-digest-quiet { width: 100%; background-color: #ffffff; border: 1px solid #e6e6ea; border-radius: 12px; margin: 4px 0 0; }
			.linker-digest-empty { padding: 12px 16px; border-top: 1px solid #f0f0f2; color: #71717a; font-size: 13px; line-height: 1.4; }
			.linker-digest-quiet tr:first-child .linker-digest-empty { border-top: 0; }
			.linker-digest-empty strong { color: #3f3f46; font-weight: 600; }
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
