<?php
/**
 * The contact form of the /contact/ page: the fields.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

/**
 * The markup of the minimal contact form (ticket #68, GAP-8): the fields the
 * mail pipeline needs and nothing else. The form posts to admin-post.php,
 * keeps its meaning without JavaScript (plain POST, then a redirect back to
 * the page's state), and carries the language of the page it was written on —
 * the same hidden `lang` field the Proforma request form posts.
 *
 * The composition is data assembly: semantic markup and utility classes, no
 * styles and no scripts of its own (AGENTS.md §5 — the styles of the page
 * come from the WindPress pipeline, which scans the rendered shortcode).
 */
final class Form {


	/**
	 * The shortcode that mounts the form (the contact page's content).
	 */
	public const SHORTCODE = 'linker_contact_form';

	/**
	 * Who may post the form.
	 */
	public const NONCE_ACTION = 'linker_contact_form';

	/**
	 * The nonce field of the form.
	 */
	public const NONCE_FIELD = 'linker_contact_nonce';

	/**
	 * The admin-post action the form submits to.
	 */
	public const ACTION = 'linker_contact';

	/**
	 * The query parameter that carries the state back to the page.
	 */
	public const STATE_PARAM = 'contact';

	/**
	 * The id of the region the redirect returns to.
	 */
	public const ANCHOR = 'contact-form';

	/**
	 * The field the honeypot rides in: a person never sees or fills it.
	 */
	public const TRAP_FIELD = 'website';

	/**
	 * The field that carries where the visitor came from, so the answer goes
	 * back to the page they wrote on.
	 */
	public const BACK_FIELD = 'linker_contact_back';

	/**
	 * Adds the shortcode.
	 */
	public function register(): void {
		add_shortcode( self::SHORTCODE, array( $this, 'render' ) );
	}

	/**
	 * The form, with the state of the last submission above the fields.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes (unused).
	 */
	public function render( $atts = array() ): string {
		unset( $atts );
		$field = 'block w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-normal text-[#15372f] focus:border-[#0c7f73] focus:outline-none';
		$label = 'grid gap-1 text-sm font-semibold text-[#15372f]';

		$html  = '<form class="linker-contact-form grid gap-5" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
		$html .= '<input type="hidden" name="action" value="' . esc_attr( self::ACTION ) . '" />';
		$html .= '<input type="hidden" name="lang" value="' . esc_attr( $this->locale() ) . '" />';
		$html .= '<input type="hidden" name="' . esc_attr( self::BACK_FIELD ) . '" value="' . esc_url( $this->current_url() ) . '" />';
		$html .= wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD, true, false );

		$state = $this->state_message();
		if ( '' !== $state ) {
			$html .= $state;
		}

		$html .= '<label class="' . esc_attr( $label ) . '"><span>' . esc_html__( 'Your question', 'linker-commerce' ) . '</span>'
		. '<textarea class="' . esc_attr( $field ) . '" name="message" rows="6" maxlength="' . esc_attr( (string) Submission::MAX_MESSAGE ) . '" required></textarea></label>';
		$html .= '<div class="grid gap-5 sm:grid-cols-2">';
		$html .= '<label class="' . esc_attr( $label ) . '"><span>' . esc_html__( 'Name', 'linker-commerce' ) . '</span>'
		. '<input class="' . esc_attr( $field ) . '" type="text" name="name" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="name" required /></label>';
		$html .= '<label class="' . esc_attr( $label ) . '"><span>' . esc_html__( 'Company', 'linker-commerce' ) . ' <small class="font-normal text-neutral-500">' . esc_html__( 'optional', 'linker-commerce' ) . '</small></span>'
		. '<input class="' . esc_attr( $field ) . '" type="text" name="company" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="organization" /></label>';
		$html .= '</div>';
		$html .= '<label class="' . esc_attr( $label ) . '"><span>' . esc_html__( 'Reply email', 'linker-commerce' ) . '</span>'
		. '<input class="' . esc_attr( $field ) . '" type="email" name="email" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="email" required /></label>';

		$privacy = get_privacy_policy_url();
		$html   .= '<label class="flex items-start gap-3 text-xs text-neutral-600"><input class="mt-1" type="checkbox" name="consent" value="1" required />'
		. '<span>' . esc_html__( 'I agree that my details may be used to respond to this message.', 'linker-commerce' );
		if ( '' !== $privacy ) {
			$html .= ' <a class="underline" href="' . esc_url( $privacy ) . '">' . esc_html__( 'Privacy', 'linker-commerce' ) . '</a>';
		}
		$html .= '</span></label>';

		$html .= '<div hidden aria-hidden="true"><label>' . esc_html__( 'Website', 'linker-commerce' ) . '<input type="text" name="' . esc_attr( self::TRAP_FIELD ) . '" tabindex="-1" autocomplete="off" /></label></div>';

		$html .= '<div class="grid gap-2"><button type="submit" class="min-h-11 justify-self-start rounded-lg bg-[#0c7f73] px-5 py-2 text-sm font-semibold text-white">' . esc_html__( 'Send message', 'linker-commerce' ) . '</button>'
		. '<p class="text-xs text-neutral-500">' . esc_html__( 'Your message goes to the Linker team. We reply to the address you give here.', 'linker-commerce' ) . '</p></div>';
		$html .= '</form>';
		return $html;
	}

	/**
	 * The state message of the last submission, '' when the form opens fresh.
	 */
	private function state_message(): string {
     // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- a state the redirect added, not an action.
		$state = isset( $_GET[ self::STATE_PARAM ] ) ? sanitize_key( (string) wp_unslash( $_GET[ self::STATE_PARAM ] ) ) : '';
		return match ( $state ) {
			'sent'      => $this->notice( 'sent', __( 'Thank you. Your message is with the Linker team.', 'linker-commerce' ) ),
			'invalid'   => $this->notice( 'invalid', __( 'Please check your entries and send the form again.', 'linker-commerce' ) ),
			'throttled' => $this->notice( 'invalid', __( 'We received several messages from this connection. Please try again later or write to sales@de-linker.com.', 'linker-commerce' ) ),
			default     => '',
		};
	}

	/**
	 * One state message.
	 *
	 * @param string $kind `sent` or `invalid`.
	 * @param string $text The message.
	 */
	private function notice( string $kind, string $text ): string {
		$classes = 'sent' === $kind
		? 'rounded-lg border border-[#0c7f73]/30 bg-[#0c7f73]/5 px-4 py-3 text-sm text-[#15372f]'
		: 'rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900';
		return '<p class="' . esc_attr( $classes ) . '" role="status">' . esc_html( $text ) . '</p>';
	}

	/**
	 * The language of the page: `en` or `de`.
	 */
	private function locale(): string {
		$lang = function_exists( 'determine_locale' ) ? determine_locale() : 'en_US';
		return str_starts_with( strtolower( $lang ), 'de' ) ? 'de' : 'en';
	}

	/**
	 * The address the form was rendered on.
	 */
	private function current_url(): string {
		$page = get_queried_object();
		if ( $page instanceof \WP_Post ) {
			return (string) get_permalink( $page );
		}
		return home_url( '/contact/' );
	}
}
