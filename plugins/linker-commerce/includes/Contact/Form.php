<?php
/**
 * The contact form of the /contact/ page: the fields.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Settings\Options;

/**
 * The markup of the contact form (ticket #68, GAP-8): the card the old live
 * pages showed — heading, question, topic, reply details, consent and send
 * row — and the two cards beside it ("Prefer email?", "Still exploring?").
 *
 * The composition is the live card's (README of docs/acceptance/2026-10-14/
 * contact-form/; the captures `contact-en-1440-live.png`, `contact-de-1440-
 * live.png`, `contact-en-390-live.png` and `contact-de-390-live.png` of the
 * 2026-10-12/13 rounds): the same blocks in the same order, the same fields,
 * and the card's words. The consent and button copy follow the #68 review.
 * The #1143 updates to the lead, contact details and response promise are
 * recorded in docs/acceptance/2026-11-18/1143/copy-review.md.
 * Its colours are not carried
 * over — the site's tokens are (AGENTS.md §2, 2026-10-11: the site's palette
 * is the current one) — and neither is the retired runtime that rendered it:
 * this form posts to admin-post.php, keeps its meaning without JavaScript,
 * and carries the language of the page it was written on.
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
	 * Order key of a saved contact inquiry, so the confirmation can follow its receipt.
	 */
	public const ORDER_PARAM = 'contact_order';

	/**
	 * The id of the region the redirect returns to.
	 */
	public const ANCHOR = 'contact-form';


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
		\Linker\Commerce\Cache\DynamicHtml::forbid( 'contact form' );
		LanguageDraft::enqueue();
		$state = $this->state_message();
		if ( str_contains( $state, 'linker-form-success' ) ) {
			// A sent message keeps the card's side cards, the way the live
			// workspace kept them around the receipt. The receipt is the box
			// itself (its own panel), so the wrapper carries no card styling.
			return '<div class="linker-contact-card"><div class="linker-contact-form linker-contact-receipt">' . $state . '</div>' . $this->rail() . '</div>';
		}
		if ( ! \Linker\Commerce\Protection\Identity::ensure_browser_cookie() ) {
			return $this->notice( \Linker\Commerce\Protection\Business::verification_message( 'unavailable' ) );
		}
		return '<div class="linker-contact-card">' . $this->form( $state ) . $this->rail() . '</div>';
	}

	/**
	 * The enquiry card: the live card's blocks and fields.
	 *
	 * @param string $state The state message to show above the fields, '' on a fresh visit.
	 */
	private function form( string $state ): string {
		$previous = \Linker\Commerce\Protection\FormRecovery::consume( 'contact' );
		$field    = 'linker-form-input';
		$label    = 'lk-field linker-form-label';
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- read-only public navigation; canonical source and selection are revalidated.
		$query    = wp_unslash( $_GET );
		$raw      = $previous[ SelectionContext::FIELD ] ?? ( is_string( $query[ SelectionContext::FIELD ] ?? null ) ? $query[ SelectionContext::FIELD ] : '' );
		$context  = array() !== $previous ? SelectionContext::normalize( json_decode( $raw, true ) ) : SelectionContext::query( $query );
		$included = ! ( array() !== $previous && '' === $raw && '0' === ( $previous[ SelectionContext::INCLUDE_FIELD ] ?? '' ) );
		// A native failed POST may have removed the optional source. Its language
		// link still carries the current public URL context, not a private old JSON value.
		$draft_context = ! $included && array() === $context ? SelectionContext::query( $query ) : $context;

		$html  = '<form class="linker-contact-form"' . LanguageDraft::attributes( array() !== $previous, $draft_context ) . ' method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">';
		$html .= '<input type="hidden" name="action" value="' . esc_attr( self::ACTION ) . '" />';
		$html .= '<input type="hidden" name="lang" value="' . esc_attr( $this->locale() ) . '" />';
		$html .= '<input type="hidden" name="' . esc_attr( self::BACK_FIELD ) . '" value="' . esc_url( $this->current_url() ) . '" />';
		// Selection transport is submitted only by the inclusion checkbox.
		$html .= wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD, false, false );
		$html .= '<input type="hidden" name="_wp_http_referer" value="' . esc_url( $this->posted_referer() ) . '" />';
		$html .= \Linker\Commerce\Inquiry\PublicGuard::fields();

		if ( '' !== $state ) {
			$html .= $state;
		}

		$html .= '<div class="linker-contact-head">';
		$html .= '<span class="linker-contact-overline">' . esc_html__( 'CONTACT LINKER', 'linker-commerce' ) . '</span>';
		$html .= '<h2>' . esc_html__( 'What can we help with?', 'linker-commerce' ) . '</h2>';
		$html .= '<p>' . esc_html__( 'Tell us what you need.', 'linker-commerce' ) . '</p>';
		$html .= '</div>';

		$html .= LanguageDraft::notice();

		$html .= SelectionView::form( $context, $raw, $included );

		$html .= '<div class="linker-form-fields">';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-name"><span class="lk-field-heading">' . esc_html__( 'Name', 'linker-commerce' ) . '<span class="lk-required" aria-hidden="true"> *</span></span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-name" type="text" name="name" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="name" required /></label>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-email"><span class="lk-field-heading">' . esc_html__( 'Email address', 'linker-commerce' ) . '<span class="lk-required" aria-hidden="true"> *</span></span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-email" type="email" name="email" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="email" required /></label>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-company"><span class="lk-field-heading">' . esc_html__( 'Company', 'linker-commerce' ) . ' <small class="linker-form-optional">' . esc_html__( 'optional', 'linker-commerce' ) . '</small></span>'
			. '<input class="' . esc_attr( $field ) . '" id="linker-contact-company" type="text" name="company" maxlength="' . esc_attr( (string) Submission::MAX_TEXT ) . '" autocomplete="organization" /></label>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-intent"><span class="lk-field-heading">' . esc_html__( 'This is about', 'linker-commerce' ) . '</span>'
			. '<select class="' . esc_attr( $field ) . '" id="linker-contact-intent" name="' . esc_attr( Submission::INTENT_FIELD ) . '">' . $this->intent_options() . '</select></label>';
		$html .= '</div>';
		$html .= '<label class="' . esc_attr( $label ) . '" for="linker-contact-message"><span class="lk-field-heading">' . esc_html__( 'Your question', 'linker-commerce' ) . '<span class="lk-required" aria-hidden="true"> *</span></span>'
			. '<textarea class="' . esc_attr( $field ) . '" id="linker-contact-message" name="message" rows="4" maxlength="' . esc_attr( (string) Submission::MAX_MESSAGE ) . '" placeholder="' . esc_attr__( 'What would you like to know?', 'linker-commerce' ) . '" required></textarea></label>';

		$html   .= '<div class="linker-contact-end">';
		$privacy = get_privacy_policy_url();
		$html   .= '<label class="linker-form-consent flex items-start gap-3 text-xs text-neutral-600"><input class="mt-1" type="checkbox" name="consent" value="1" required />'
			. '<span>' . esc_html__( 'I agree that my details may be used to respond to this message.', 'linker-commerce' );
		if ( '' !== $privacy ) {
			$html .= ' <a class="underline" href="' . esc_url( $privacy ) . '">' . esc_html__( 'Privacy', 'linker-commerce' ) . '</a>';
		}
		$html .= '</span></label>';
		$html .= \Linker\Commerce\Protection\FormFields::render( 'contact', $previous['linker_request_id'] ?? '' );
		$html .= '<div class="linker-form-submit grid gap-2"><button type="submit" class="linker-form-primary">' . esc_html__( 'Send message', 'linker-commerce' ) . '<span aria-hidden="true">↗</span></button>'
			. '</div>';
		$html .= '</div>';

		$html .= '</form>';
		if ( array() !== $previous ) {
			// Insert escaped values after shortcode/template assembly; no user text is executable.
			$html = preg_replace_callback( '/(<input[^>]+name="(name|email|company)"[^>]*)(\s\/>)/', static fn ( array $m ): string => $m[1] . ' value="' . esc_attr( $previous[ $m[2] ] ?? '' ) . '"' . $m[3], $html ) ?? $html;
			$html = str_replace( 'required></textarea>', 'required>' . esc_textarea( $previous['message'] ?? '' ) . '</textarea>', $html );
			$html = str_replace( 'name="consent" value="1" required', 'name="consent" value="1"' . ( '1' === ( $previous['consent'] ?? '' ) ? ' checked' : '' ) . ' required', $html );
			$html = preg_replace( '/(<option[^>]+) selected/', '$1', $html ) ?? $html;
			if ( in_array( $previous['intent'] ?? '', self::INTENTS, true ) ) {
				$html = str_replace( '<option value="' . $previous['intent'] . '"', '<option value="' . $previous['intent'] . '" selected', $html );
			}
		}
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
			'support'     => __( 'Support after delivery', 'linker-commerce' ),
			'partnership' => __( 'Work with Linker', 'linker-commerce' ),
			default       => __( 'A question', 'linker-commerce' ),
		};
	}

	/**
	 * The two cards beside the form: the direct address and the way into
	 * Genie. Words from the live card; the address is the team mailbox
	 * customers see. The form's own letter goes to the internal notification
	 * address instead (owner ruling 2026-10-17, Options::notify_to()).
	 */
	private function rail(): string {
		$email = ( new Options() )->team_mailbox();
		$html  = '<aside class="linker-contact-rail">';
		$html .= '<div class="linker-contact-rail-card linker-contact-email">';
		$html .= '<span class="linker-contact-overline">' . esc_html__( 'Sales and technical support', 'linker-commerce' ) . '</span>';
		$html .= '<a class="linker-contact-address" href="mailto:' . esc_attr( $email ) . '">' . esc_html( $email ) . '</a>';
		$html .= '<p>' . esc_html__( 'The Linker team replies within one business day.', 'linker-commerce' ) . '</p>';
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
	 * The Genie page in the page's language, the language's home when the
	 * page does not exist. The live card linked the assistant the same way
	 * (its advisor page).
	 */
	private function genie_url(): string {
		return PageUrls::page( 'genie' );
	}

	/**
	 * The state message of the last submission, '' when the form opens fresh.
	 */
	private function state_message(): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- a state the redirect added, not an action.
		$state = isset( $_GET[ self::STATE_PARAM ] ) ? sanitize_key( (string) wp_unslash( $_GET[ self::STATE_PARAM ] ) ) : '';
		if ( in_array( $state, array( 'sent', 'sent_no_receipt', 'receipt_pending', 'saved_review' ), true ) ) {
			$order = $this->receipt_order( $state );
			return $order instanceof \WC_Order ? $this->receipt_notice( $order ) : '';
		}
		return match ( $state ) {
			'reception_full' => $this->notice( \Linker\Commerce\Protection\BusinessCapacity::message() ),
			'review_size' => $this->notice( __( 'This request is too large to save for review. Your entries and solution draft are still here. Please email sales@de-linker.com.', 'linker-commerce' ) ),
			'review_full' => $this->notice( __( 'Your request has not been saved because the review queue is full. Your entries are still here. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) ),
			'grouped' => $this->notice( __( 'This message matches a repeated spam submission. We have not saved a separate inquiry or sent an email. Your entries are still here. For an individual review, select the review option in this form or email sales@de-linker.com.', 'linker-commerce' ) ),
			'invalid'   => $this->notice( __( 'Please check your entries and send the form again.', 'linker-commerce' ) ),
			'throttled' => $this->notice( __( 'The message limit has been reached. Your entries are still here. You can try again later or email sales@de-linker.com.', 'linker-commerce' ) ),
			'verification_failed' => $this->notice( \Linker\Commerce\Protection\Business::verification_message( 'failed' ) ),
			'verification_unavailable' => $this->notice( \Linker\Commerce\Protection\Business::verification_message( 'unavailable' ) ),
			'pending' => $this->notice( __( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) ),
			default     => '',
		};
	}

	/**
	 * The contact inquiry named by the confirmation.
	 *
	 * @param string $state Requested receipt state.
	 */
	private function receipt_order( string $state ): ?\WC_Order {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- A previous individual-review receipt was bound only to Woo's session.
		if ( 'saved_review' === $state && ! isset( $_GET[ self::ORDER_PARAM ] ) ) {
			$number = (string) WC()->session->get( 'linker_review_saved', '' );
			$order  = ctype_digit( $number ) ? wc_get_order( (int) $number ) : false;
			if ( ! $order instanceof \WC_Order || $number !== (string) $order->get_order_number() || 'individual' !== $order->get_meta( \Linker\Commerce\Protection\Intake::LANE_META ) || 'contact' !== $order->get_meta( '_linker_inquiry_source' ) || $order->has_status( 'trash' ) || $order->get_meta( \Linker\Commerce\Inquiry\Assessment\Reviews::ERASED ) ) {
				return null;
			}
			$owner = (int) $order->get_customer_id();
			return 0 === $owner || get_current_user_id() === $owner ? $order : null;
		}
		if ( ! isset( $_GET[ self::ORDER_PARAM ] ) || ! function_exists( 'wc_get_order_id_by_order_key' ) || ! function_exists( 'wc_get_order' ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the redirect's own order key, rechecked against the contact source.
			return null;
		}
		$key = sanitize_text_field( (string) wp_unslash( $_GET[ self::ORDER_PARAM ] ) ); // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- the redirect's own order key, rechecked against the contact source.
		if ( 1 !== preg_match( '/\Awc_order_[A-Za-z0-9]+\z/', $key ) ) {
			return null;
		}
		$id    = wc_get_order_id_by_order_key( $key );
		$order = $id > 0 ? wc_get_order( $id ) : false;
		if ( ! $order instanceof \WC_Order || ! hash_equals( (string) $order->get_order_key(), $key ) || 'contact' !== (string) $order->get_meta( '_linker_inquiry_source' ) ) {
			return null;
		}
		return $order;
	}

	/**
	 * Confirm this saved inquiry using Woo's current order number and mail state.
	 *
	 * @param \WC_Order $order Contact inquiry identified by its key.
	 */
	private function receipt_notice( \WC_Order $order ): string {
		if ( 'individual' === $order->get_meta( \Linker\Commerce\Protection\Intake::LANE_META ) && $order->has_status( \Linker\Commerce\Inquiry\Statuses::RECEIVED ) && \Linker\Commerce\Mail\NotificationHold::held( $order ) ) {
			$text = \Linker\Commerce\Protection\IntakeAdmin::saved_message( $order );
		} else {
			/* translators: %s: inquiry number. */
			$number = sprintf( __( 'Inquiry #%s', 'linker-commerce' ), $order->get_order_number() );
			$text   = 'sent_no_receipt' === Handler::receipt_state( $order )
				? __( 'Thank you. Your message is with the Linker team. We have not sent a confirmation email. We reply within one business day.', 'linker-commerce' )
				: __( 'Thank you. Your message is with the Linker team.', 'linker-commerce' );
			$text   = $number . ' · ' . $text;
		}
		return '<section class="linker-form-success woocommerce-message" role="status">'
			. '<span class="linker-form-state-icon" aria-hidden="true">✓</span>'
			. '<p>' . esc_html( $text ) . '</p>'
			. '<a class="linker-form-primary" href="' . esc_url( $this->current_url() . '#' . self::ANCHOR ) . '">' . esc_html__( 'Send another message', 'linker-commerce' ) . '</a></section>';
	}

	/**
	 * An error above the contact fields.
	 *
	 * @param string $text The message.
	 */
	private function notice( string $text ): string {
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
	 * The current contact path for WordPress' referer field.
	 *
	 * Selection transport stays in the inclusion checkbox. Repeating it here
	 * would keep an excluded search in the native POST.
	 */
	private function posted_referer(): string {
		// Current request path only. It is stripped before display and is not an action.
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? (string) wp_unslash( $_SERVER['REQUEST_URI'] ) : ''; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized
		if ( '' === $uri ) {
			$path = wp_parse_url( $this->current_url(), PHP_URL_PATH );
			return is_string( $path ) && '' !== $path ? $path : '/';
		}
		$path  = wp_parse_url( $uri, PHP_URL_PATH );
		$path  = is_string( $path ) && '' !== $path ? $path : '/';
		$query = wp_parse_url( $uri, PHP_URL_QUERY );
		if ( ! is_string( $query ) || '' === $query ) {
			return $path;
		}
		parse_str( $query, $args );
		// These are the public selection transports read by SelectionContext::query.
		foreach ( array( '_wp_http_referer', SelectionContext::FIELD, 'source', 'search', 'filters', 'sort', 'platform', 'document' ) as $key ) {
			unset( $args[ $key ] );
		}
		$rebuilt = http_build_query( $args );
		return '' === $rebuilt ? $path : $path . '?' . $rebuilt;
	}

	/**
	 * The address the form was rendered on.
	 */
	private function current_url(): string {
		$page = get_queried_object();
		if ( $page instanceof \WP_Post ) {
			return (string) get_permalink( $page );
		}
		return PageUrls::page( 'contact' );
	}
}
