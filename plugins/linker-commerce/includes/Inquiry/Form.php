<?php
/**
 * Data tags for the LiveCanvas inquiry form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\Tokens;
use WC_Customer;

/**
 * Page composition belongs to content/livecanvas/inquiry, styles to WindPress.
 */
final class Form {


	/**
	 * One render's consumed flash values.
	 *
	 * @var array<string, mixed>
	 */
	private array $flash = array();

	/**
	 * The conversation's note, resolved once per render (#244).
	 *
	 * @var string|null
	 */
	private ?string $note = null;

	/**
	 * Registers the form and its escaped data tags.
	 */
	public function register(): void {
		add_shortcode( 'linker_inquiry_billing', array( BillingFields::class, 'render' ) );
		add_shortcode( 'linker_inquiry_restriction', array( new \Linker\Commerce\Presentation\LoginGate(), 'restricted_notice' ) );
		add_shortcode( 'linker_inquiry_form', array( $this, 'render' ) );
		add_shortcode( 'linker_inquiry_text', array( $this, 'text' ) );
		add_shortcode( 'linker_inquiry_hidden', array( $this, 'hidden' ) );
		add_shortcode( 'linker_inquiry_lines', array( $this, 'lines' ) );
		add_shortcode( 'linker_inquiry_draft_nonce', array( $this, 'draft_nonce' ) );
	}

	/**
	 * LC's own fragment with no PHP layout.
	 */
	public function render(): string {
		foreach ( array( 'fields', 'error', 'error_locale' ) as $key ) {
			$this->flash[ $key ] = WC()->session->get( 'linker_inquiry_' . $key );
			WC()->session->set( 'linker_inquiry_' . $key, null );
		}
		try {
			$template = do_shortcode( Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/form.html' ) );
			// Core intentionally refuses shortcode expansion in form actions and empty attributes.
			// Insert customer text last so a message can never execute shortcodes.
			return preg_replace_callback( '/\{\{([a-z-]+)\}\}/', fn ( array $token ): string => $this->value( array( 'key' => $token[1] ) ), $template ) ?? '';
		} finally {
			$this->flash = array();
		}
	}

	/**
	 * Scalar values are escaped for attributes as well as text nodes.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function value( $atts = array() ): string {
		$key      = (string) ( $atts['key'] ?? '' );
		$customer = new WC_Customer( get_current_user_id() );
		$previous = (array) ( $this->flash['fields'] ?? array() );
		$name     = trim( $customer->get_billing_first_name() . ' ' . $customer->get_billing_last_name() );
		if ( '' === $name && is_user_logged_in() ) {
			$name = trim( (string) wp_get_current_user()->first_name . ' ' . (string) wp_get_current_user()->last_name );
		}
		$email = $customer->get_billing_email();
		if ( '' === $email && is_user_logged_in() ) {
			$email = wp_get_current_user()->user_email;
		}
		$error = (string) ( $this->flash['error'] ?? '' );
		if ( '' !== $error && ( $this->flash['error_locale'] ?? '' ) !== get_locale() ) {
			$error = __( 'Please check your entries and send the form again.', 'linker-commerce' );
		}
		$values = array(
			'name'               => $name,
			'email'              => $email,
			'company'            => $customer->get_billing_company(),
			// A customer who talked with Genie starts from the note of that
			// conversation (#244): the team sees the whole summary with the
			// inquiry, and nothing already said is typed again.
			'message'            => $this->summary_note(),
			'action'             => admin_url( 'admin-post.php' ),
			'draft-url'          => wc_get_cart_url(),
			'draft-action'       => wc_get_checkout_url(),
			'login-url'          => wc_get_page_permalink( 'myaccount' ),
			'privacy'            => \Linker\Commerce\Presentation\PageUrls::translated( 'privacy-policy' ),
			'open'               => is_user_logged_in() && '' !== $name && '' !== $email && array() === $previous ? '' : 'open',
			'summary-hide'       => is_user_logged_in() ? '' : 'hidden',
			'draft-empty'        => WC()->cart->is_empty() ? 'hidden' : '',
			'consent-attributes' => is_user_logged_in() ? 'checked' : 'required',
			'guest-hide'         => is_user_logged_in() ? 'hidden' : '',
			'error'              => $error,
		);
		if ( in_array( $key, array( 'name', 'email', 'company', 'message' ), true ) && isset( $previous[ $key ] ) && is_string( $previous[ $key ] ) ) {
			return esc_attr( $previous[ $key ] );
		}
		return esc_attr( (string) ( $values[ $key ] ?? '' ) );
	}

	/**
	 * Nonce, language, anti-bot time, and transport fields.
	 */
	public function hidden(): string {
		return '<input type="hidden" name="action" value="linker_inquiry" /><input type="hidden" name="lang" value="' . esc_attr( str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en' ) . '" />'
		. wp_nonce_field( Handler::ACTION, Handler::NONCE, true, false ) . ( new PublicGuard() )->fields()
		. '<input type="hidden" name="linker_draft_hash" value="' . esc_attr( WC()->cart->get_cart_hash() ) . '" />'
		. \Linker\Commerce\Protection\FormFields::render( 'inquiry', (string) ( $this->flash['fields']['linker_request_id'] ?? '' ), '1' === ( $this->flash['fields']['linker_individual_review'] ?? '' ) );
	}

	/**
	 * Woo's own draft update handler consumes these fields.
	 */
	public function draft_nonce(): string {
		return wp_nonce_field( 'woocommerce-cart', 'woocommerce-cart-nonce', true, false ) . \Linker\Commerce\Protection\FormFields::render( 'draft_write' );
	}

	/**
	 * The latest message of the visitor's Genie conversation, or ''.
	 *
	 * Linker\Tools\Genie\InquirySummary answers the filter once per thread
	 * state and caches it, so the form's render and the inquiry's submit share
	 * one summary (#244). Without linker-tools or a conversation the filter
	 * stays unanswered and the form starts empty.
	 */
	private function summary_note(): string {
		if ( null !== $this->note ) {
			return $this->note;
		}
		$summary    = apply_filters( 'linker_genie_inquiry_summary', null, 0 ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- linker-tools' filter (Linker\Tools\Genie\InquirySummary::FILTER): the plugin answers with the conversation's summary.
		$this->note = is_array( $summary ) && isset( $summary['note'] ) && is_string( $summary['note'] ) ? $summary['note'] : '';
		return $this->note;
	}

	/**
	 * Reviewed bilingual words, resolved by the plugin's gettext catalogues.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function text( $atts = array() ): string {
		$words = array(
			'title'      => __( 'Send an inquiry', 'linker-commerce' ),
			'intro'      => __( 'Tell us what you need. The products in your solution draft will be included.', 'linker-commerce' ),
			'message'    => __( 'Message (optional)', 'linker-commerce' ),
			'details'    => __( 'Your reply details', 'linker-commerce' ),
			'change'     => __( 'Change', 'linker-commerce' ),
			'name'       => __( 'Name', 'linker-commerce' ),
			'email'      => __( 'Reply email', 'linker-commerce' ),
			'company'    => __( 'Company (optional)', 'linker-commerce' ),
			'consent'    => __( 'I agree that my details may be used to respond to this message.', 'linker-commerce' ),
			'privacy'    => __( 'Privacy', 'linker-commerce' ),
			'send'       => __( 'Send inquiry', 'linker-commerce' ),
			'promise'    => __( 'We reply within one business day.', 'linker-commerce' ),
			'no-account' => __( 'No account needed.', 'linker-commerce' ),
			'partner'    => __( 'Have an approved account? Log in for net prices and saved details.', 'linker-commerce' ),
			'draft'      => __( 'Solution draft', 'linker-commerce' ),
			'edit'       => __( 'Edit solution draft', 'linker-commerce' ),
			'quantity'   => __( 'Quantity', 'linker-commerce' ),
			'update'     => __( 'Update solution draft', 'linker-commerce' ),
		);
		return esc_html( $words[ $atts['key'] ?? '' ] ?? '' );
	}

	/**
	 * Current Woo lines, rendered through LC's row fragment.
	 */
	public function lines(): string {
		$html = '';
		foreach ( WC()->cart->get_cart() as $key => $line ) {
			$product = $line['data'];
			if ( ! $product instanceof \WC_Product ) {
				continue;
			}
			$html .= strtr(
				Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/line.html' ),
				array(
					'{{name}}'               => esc_html( $product->get_name() ),
					'{{image}}'              => wp_kses_post(
						$product->get_image(
							'woocommerce_thumbnail',
							array(
								'alt'     => '',
								'loading' => 'lazy',
							)
						)
					),
					'{{quantity}}'           => esc_html( (string) $line['quantity'] ),
					'{{quantity-label}}'     => esc_html__( 'Quantity', 'linker-commerce' ),
					'{{key}}'                => esc_attr( $key ),
					'{{label}}'              => esc_attr( sprintf( /* translators: %s: product name. */ __( 'Quantity for %s', 'linker-commerce' ), $product->get_name() ) ),
					'{{price}}'              => wp_kses_post( $product->get_price_html() ),
					'{{remove-url}}'         => esc_url( wc_get_cart_remove_url( $key ) ),
					'{{remove}}'             => esc_html__( 'Remove', 'linker-commerce' ),
					'{{remove-description}}' => esc_attr( sprintf( /* translators: %s: product name. */ __( 'Remove %s from the solution draft', 'linker-commerce' ), $product->get_name() ) ),
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.HookCommentWrongStyle, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Woo's native cart link filter resolves the language twin.
					'{{url}}'                => esc_url( (string) apply_filters( 'woocommerce_cart_item_permalink', $product->get_permalink(), $line, $key ) ),
				)
			);
		}
		return '' === $html ? str_replace( '{{message}}', esc_html__( 'You can send a message without products.', 'linker-commerce' ), Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/empty.html' ) ) : $html;
	}
}
