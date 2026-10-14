<?php
/**
 * The contact form of the /contact/ page: the fields.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Settings\Options;

/**
 * The markup of the contact form (ticket #68, GAP-8): the card the old live
 * pages showed — heading, question, topic, reply details, consent and send
 * row — and the two cards beside it ("Prefer email?", "Still exploring?").
 *
 * The composition is the live card's (README of docs/acceptance/2026-10-14/
 * contact-form/; the captures `contact-en-1440-live.png`, `contact-de-1440-
 * live.png`, `contact-en-390-live.png` and `contact-de-390-live.png` of the
 * 2026-10-12/13 rounds): the same blocks in the same order, the same words
 * (the contact page is frozen copy), the same fields. Its colours are not
 * carried over — the site's tokens are (AGENTS.md §2, 2026-10-11: the site's
 * palette is the current one) — and neither is the retired runtime that
 * rendered it: this form posts to admin-post.php, keeps its meaning without
 * JavaScript, and carries the language of the page it was written on.
 *
 * The composition is data assembly: semantic markup and class names, no
 * styles and no scripts of its own (AGENTS.md §5 — the styles of the page
 * come from the WindPress pipeline, which scans the rendered shortcode). The
 * shapes and the spacing live in content/windpress/contact-card.css.
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
	 * The topics the "This is about" select offers, in the live card's order.
	 *
	 * The live runtime read the same seven values out of the address (its
	 * `intents`); the site's own contact links still carry them — the header
	 * entry on a product page (`intent=product`) and the invitation band
	 * (`intent=project`, `intent=product`) — so the select is what makes those
	 * links arrive somewhere. The value is submitted and reaches the team
	 * letter (Submission::INTENT_FIELD).
	 */
	public const INTENTS = array( 'general', 'product', 'offer', 'document', 'project', 'support', 'partnership' );

	/**
	 * Adds the shortcode.
	 */
	public function register(): void {
		add_shortcode( self::SHORTCODE, array( $this, 'render' ) );
	}

	/**
	 * The card, with the state of the last submission above the fields.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes (unused).
	 */
	public function render( $atts = array() ): string {
		unset( $atts );
		$state = $this->state_message();
		if ( str_contains( $state, 'linker-form-success' ) ) {
			// A sent message keeps the card's side cards, the way the live
			// workspace kept them around the receipt. The receipt is the box
			// itself (its own panel), so the wrapper carries no card styling.
			return '<div class="linker-contact-card"><div class="linker-contact-form linker-contact-receipt">' . $state . '</div>' . $this->rail() . '</div>';
		}
		return '<div class="linker-contact-card">' . $this->form( $state ) . $this->rail() . '</div>';
	}

	/**
	 * The enquiry card: the live card's blocks and fields.
	 *
	 * @param string $state The state message to show above the fields, '' on a fresh visit.
	 */
	private function form( string $state ): string {
		$field = 'linker-form-input';
		$label = 'linker-form-label';

		$html  = '<form class="linker-contact-form" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
		$html .= '<input type="hidden" name="action" value="' . esc_attr( self::ACTION ) . '" />';
		$html .= '<input type="hidden" name="lang" value="' . esc_attr( $this->locale() ) . '" />';
		$html .= '<input type="hidden" name="' . esc_attr( self::BACK_FIELD ) . '" value="' . esc_url( $this->current_url() ) . '" />';
		$html .= wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD, true, false );

		if ( '' !== $state ) {
			$html .= $state;
		}

		$html .= '<div class="linker-contact-head">';
		$html .= '<span class="linker-contact-overline">' . esc_html__( 'CONTACT LINKER', 'linker-commerce' ) . '</span>';
		$html .= '<h2>' . esc_html__( 'What can we help with?', 'linker-commerce' ) . '</h2>';
		$html .= '<p>' . esc_html__( 'Tell us what you need. We’ll use the email below for your reply.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';

		$html .= '<div class="linker-contact-question">';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-message"><span>' . esc_html__( 'Your question', 'linker-commerce' ) . '</span>'
			. '<textarea class="' . esc_attr( $field ) . '" id="linker-contact-message" name="message" rows="4" maxlength="' . esc_attr( (string) Submission::MAX_MESSAGE ) . '" placeholder="' . esc_attr__( 'What would you like to know?', 'linker-commerce' ) . '" required></textarea></label>';
		$html .= '</div>';

		$html .= '<div class="linker-contact-topic">';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-intent"><span>' . esc_html__( 'This is about', 'linker-commerce' ) . '</span>'
			. '<select class="' . esc_attr( $field ) . '" id="linker-contact-intent" name="' . esc_attr( Submission::INTENT_FIELD ) . '">' . $this->intent_options() . '</select></label>';
		$html .= '</div>';

		$html .= '<div class="linker-contact-reply">';
		$html .= '<h3>' . esc_html__( 'Where can we reply?', 'linker-commerce' ) . '</h3>';
		$html .= '<div class="linker-form-fields">';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-name"><span>' . esc_html__( 'Name', 'linker-commerce' ) . '</span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-name" type="text" name="name" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="name" required /></label>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-email"><span>' . esc_html__( 'Reply email', 'linker-commerce' ) . '</span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-email" type="email" name="email" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="email" required /></label>';
		$html .= '</div>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-company"><span>' . esc_html__( 'Company', 'linker-commerce' ) . ' <small class="linker-form-optional">' . esc_html__( 'optional', 'linker-commerce' ) . '</small></span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-company" type="text" name="company" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="organization" /></label>';
		$html .= '<p class="linker-form-note">' . esc_html__( 'No account or Project is needed to ask a question.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';

		$html   .= '<div class="linker-contact-end">';
		$privacy = get_privacy_policy_url();
		$html   .= '<label class="linker-form-consent flex items-start gap-3 text-xs text-neutral-600"><input class="mt-1" type="checkbox" name="consent" value="1" required />'
			. '<span>' . esc_html__( 'I agree that my details may be used to respond to this enquiry.', 'linker-commerce' );
		if ( '' !== $privacy ) {
			$html .= ' <a class="underline" href="' . esc_url( $privacy ) . '">' . esc_html__( 'Privacy', 'linker-commerce' ) . '</a>';
		}
		$html .= '</span></label>';
		$html .= '<div hidden aria-hidden="true"><label>' . esc_html__( 'Website', 'linker-commerce' ) . '<input type="text" name="' . esc_attr( self::TRAP_FIELD ) . '" tabindex="-1" autocomplete="off" /></label></div>';
		$html .= '<div class="linker-form-submit grid gap-2"><button type="submit" class="linker-form-primary">' . esc_html__( 'Send enquiry', 'linker-commerce' ) . '<span aria-hidden="true">↗</span></button>'
			. '<p class="linker-form-note">' . esc_html__( 'Your question goes to the Linker team. Keep the receipt to check its progress.', 'linker-commerce' ) . '</p></div>';
		$html .= '</div>';

		$html .= '</form>';
		return $html;
	}

	/**
	 * The options of the "This is about" select, the topic that came in
	 * through the address selected.
	 */
	private function intent_options(): string {
		$current = $this->posted_intent();
		$html    = '';
		foreach ( self::INTENTS as $intent ) {
			$html .= '<option value="' . esc_attr( $intent ) . '"' . ( $intent === $current ? ' selected' : '' ) . '>' . esc_html( self::intent_label( $intent ) ) . '</option>';
		}
		return $html;
	}

	/**
	 * The topic the visitor arrived with: the site's own contact links carry
	 * `intent` (Presentation\Shortcodes), the live card selected it, and a
	 * request without it asks the general question.
	 */
	private function posted_intent(): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- a read-only preselect, not an action; the value is checked against INTENTS.
		$intent = isset( $_GET[ Submission::INTENT_FIELD ] ) ? sanitize_key( (string) wp_unslash( $_GET[ Submission::INTENT_FIELD ] ) ) : '';
		return in_array( $intent, self::INTENTS, true ) ? $intent : self::INTENTS[0];
	}

	/**
	 * The words of one topic, the live card's (its `labels`).
	 *
	 * @param string $intent One of INTENTS.
	 */
	public static function intent_label( string $intent ): string {
		return match ( $intent ) {
			'product'     => __( 'Product guidance', 'linker-commerce' ),
			'offer'       => __( 'Price & availability', 'linker-commerce' ),
			'document'    => __( 'Product documents', 'linker-commerce' ),
			'project'     => __( 'Discuss a project', 'linker-commerce' ),
			'support'     => __( 'Support for an order', 'linker-commerce' ),
			'partnership' => __( 'Work with Linker', 'linker-commerce' ),
			default       => __( 'A question', 'linker-commerce' ),
		};
	}

	/**
	 * The two cards beside the form: the direct address and the way into
	 * Genie. Words from the live card; the address is the team mailbox this
	 * form writes to, so both ways reach the same place.
	 */
	private function rail(): string {
		$email = ( new Options() )->team_to();
		$html  = '<aside class="linker-contact-rail">';
		$html .= '<div class="linker-contact-rail-card linker-contact-email">';
		$html .= '<span class="linker-contact-overline">' . esc_html__( 'Prefer email?', 'linker-commerce' ) . '</span>';
		$html .= '<a class="linker-contact-address" href="mailto:' . esc_attr( $email ) . '">' . esc_html( $email ) . '</a>';
		$html .= '<p>' . esc_html__( 'Send your question directly to our team. Opening your email app does not send a message.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';
		$html .= '<div class="linker-contact-rail-card linker-contact-explore">';
		$html .= '<span class="linker-contact-overline">' . esc_html__( 'Still exploring?', 'linker-commerce' ) . '</span>';
		$html .= '<h3>' . esc_html__( 'Take your time.', 'linker-commerce' ) . '</h3>';
		$html .= '<p>' . esc_html__( 'Use Genie to explore the options, then return to your question.', 'linker-commerce' ) . '</p>';
		$html .= '<a href="' . esc_url( $this->genie_url() ) . '">' . esc_html__( 'Explore with Genie', 'linker-commerce' ) . '<span aria-hidden="true">↗</span></a>';
		$html .= '</div>';
		$html .= '</aside>';
		return $html;
	}

	/**
	 * The Genie page in the page's language.
	 *
	 * The live card linked the assistant the same way (its advisor page);
	 * the resolution is the one the Genie entries use — the language layer
	 * (`pll_current_language`) decides, German gets the twin
	 * (`pll_get_post`), everything else stays on /genie/
	 * (linker-tools\includes\Genie\Entries::workspace_url()).
	 */
	private function genie_url(): string {
		if ( ! function_exists( 'pll_current_language' ) || 'de' !== pll_current_language() ) {
			return home_url( '/genie/' );
		}
		$page = get_page_by_path( 'genie' );
		if ( ! $page instanceof \WP_Post || ! function_exists( 'pll_get_post' ) ) {
			return home_url( '/de/genie/' );
		}
		$twin = (int) pll_get_post( (int) $page->ID, 'de' );
		$link = $twin > 0 ? get_permalink( $twin ) : false;
		return is_string( $link ) && '' !== $link ? $link : home_url( '/de/genie/' );
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
		if ( 'sent' === $kind ) {
			return '<section class="linker-form-success woocommerce-message" role="status">'
				. '<span class="linker-form-state-icon" aria-hidden="true">✓</span>'
				. '<p>' . esc_html( $text ) . '</p>'
				. '<a class="linker-form-primary" href="' . esc_url( $this->current_url() . '#' . self::ANCHOR ) . '">' . esc_html__( 'Send another message', 'linker-commerce' ) . '</a></section>';
		}
		return '<div class="linker-form-error woocommerce-error" role="alert"><span class="linker-form-state-icon" aria-hidden="true">!</span><p>' . esc_html( $text ) . '</p></div>';
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
