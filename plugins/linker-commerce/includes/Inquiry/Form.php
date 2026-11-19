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
	 * Registers the form and its escaped data tags.
	 */
	public function register(): void {
		add_shortcode( 'linker_inquiry_billing', fn (): string => BillingFields::render( $this->flash['fields']['billing'] ?? array() ) );
		add_shortcode( 'linker_inquiry_restriction', array( new \Linker\Commerce\Presentation\LoginGate(), 'restricted_notice' ) );
		add_shortcode( 'linker_inquiry_form', array( $this, 'render' ) );
		add_shortcode( 'linker_inquiry_text', array( $this, 'text' ) );
		add_shortcode( 'linker_inquiry_hidden', array( $this, 'hidden' ) );
		add_shortcode( 'linker_inquiry_project_notes', array( $this, 'project_notes' ) );
		add_shortcode( 'linker_inquiry_lines', array( $this, 'lines' ) );
		add_shortcode( 'linker_inquiry_draft_nonce', array( $this, 'draft_nonce' ) );
	}

	/**
	 * Active planning project notes, rendered separately from the customer message.
	 */
	public function project_notes(): string {
		$previous = (array) ( $this->flash['fields'] ?? array() );
		if ( isset( $previous['linker_planner_handoff_id'] ) || ( ( isset( $previous['linker_note_project'] ) || isset( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ) && '1' === $previous['linker_recovery_available'] ) ) {
			// Recover an uncertain send with the exact draft and note revisions originally posted.
			$html = '';
			if ( '1' === $previous[ \Linker\Commerce\Planning\Context::PRESENT_FIELD ] ) {
				$html .= '<input type="hidden" name="linker_project_notes_present" value="1" />';
				$html .= '<input type="hidden" name="linker_include_project_notes" value="' . esc_attr( $previous[ \Linker\Commerce\Planning\Context::INCLUDE_FIELD ] ) . '" />';
			}
			foreach ( $previous[ \Linker\Commerce\Planning\Context::REVISIONS_FIELD ] ?? array() as $id => $revision ) {
				$html .= '<input type="hidden" name="linker_project_note_revisions[' . esc_attr( $id ) . ']" value="' . esc_attr( $revision ) . '" />';
			}
			return $html;
		}
		$note = null;
		if ( isset( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ) {
			$note = \Linker\Commerce\Planning\Context::read_preliminary_project( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] );
			if ( $note instanceof \WP_Error ) {
				return '<p role="alert">' . esc_html( $note->get_error_message() ) . '</p>';
			}
		} elseif ( isset( $previous['linker_note_project'] ) ) {
			$note = \Linker\Commerce\Planning\Context::read_selected_note( $previous['linker_note_project'] );
			if ( $note instanceof \WP_Error ) {
				return '<p role="alert">' . esc_html( $note->get_error_message() ) . '</p>' . \Linker\Commerce\Planning\Context::inquiry_notes_section(
					$previous,
					null,
					array(
						'project_id'    => $previous['linker_note_project'],
						'note_revision' => $previous[ \Linker\Commerce\Planning\Context::REVISIONS_FIELD ][ 'project_' . $previous['linker_note_project'] ],
					)
				);
			}
		}
		return \Linker\Commerce\Planning\Context::inquiry_notes_section( $previous, null, $note );
	}

	/**
	 * LC's own fragment with no PHP layout.
	 */
	public function render(): string {
		\Linker\Commerce\Cache\DynamicHtml::forbid( 'inquiry form' );
		foreach ( array( 'fields', 'error', 'error_locale' ) as $key ) {
			$this->flash[ $key ] = WC()->session->get( 'linker_inquiry_' . $key );
			WC()->session->set( 'linker_inquiry_' . $key, null );
		}
		try {
			$template = do_shortcode( str_replace( '{{inquiry-fields}}', self::fields_template(), Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/form.html' ) ) );
			// Core intentionally refuses shortcode expansion in form actions and empty attributes.
			// Insert customer text last so a message can never execute shortcodes.
			return preg_replace_callback( '/\{\{([a-z-]+)\}\}/', fn ( array $token ): string => $this->value( array( 'key' => $token[1] ) ), $template ) ?? '';
		} finally {
			$this->flash = array();
		}
	}

	/** Shared native reply, consent and submit controls for checkout and planner Review. */
	private static function fields_template(): string {
		return Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/fields.html' );
	}

	/**
	 * Render the native POST form for the proposed draft, without consuming checkout flash data.
	 *
	 * @param array<string,mixed>|null $handoff Verified engine handoff, or the current native draft alone.
	 * @param string                   $language Requested planner language.
	 * @param array<string,mixed>|null $note Current owner-verified project note.
	 */
	public function planning( ?array $handoff, string $language, ?array $note = null ): string {
		$locale = new \Linker\Commerce\Mail\LocaleSwitch();
		$locale->to( OrderLocale::current( $language ) );
		try {
			$fields = do_shortcode( self::fields_template() );
			$fields = preg_replace_callback( '/\{\{([a-z-]+)\}\}/', fn ( array $token ): string => 'privacy' === $token[1] ? esc_url( \Linker\Commerce\Presentation\PageUrls::translated( 'privacy-policy', $language ) ) : $this->value( array( 'key' => $token[1] ) ), $fields ) ?? '';
			return '<form class="linker-inquiry-form" data-inquiry-context="' . $this->value( array( 'key' => 'retention-context' ) ) . '" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">' . $this->hidden_fields( $language, isset( $note['inputs'] ) ? $note['project_id'] . ':' . $note['revision'] : '' )
				. '<input type="hidden" name="linker_draft_hash" value="' . $this->value( array( 'key' => 'draft-hash' ) ) . '" />'
				. ( null === $handoff ? '' : self::planner_fields( $handoff['id'], '' ) )
				. \Linker\Commerce\Planning\Context::inquiry_notes_section( array(), $handoff, $note ) . $fields . '</form>';
		} finally {
			$locale->back();
		}
	}

	/**
	 * Scalar values are escaped for attributes as well as text nodes.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function value( $atts = array() ): string {
		$key = (string) ( $atts['key'] ?? '' );
		if ( 'draft-hash' === $key ) {
			return esc_attr( $this->flash['fields']['linker_draft_hash'] ?? WC()->cart->get_cart_hash() );
		}
		$customer = new WC_Customer( get_current_user_id() );
		$previous = (array) ( $this->flash['fields'] ?? array() );
		$name     = trim( $customer->get_billing_first_name() . ' ' . $customer->get_billing_last_name() );
		if ( '' === $name && is_user_logged_in() ) {
			$name = trim( (string) wp_get_current_user()->first_name . ' ' . (string) wp_get_current_user()->last_name );
		}
		if ( '' === $name && is_user_logged_in() ) {
			// Accounts without any stored name (staff-created, legacy imports) still
			// have an identity; the required reply-name input must never render
			// empty for them, or the browser's own validation silently blocks
			// the inquiry submit before it reaches the server.
			$name = trim( (string) wp_get_current_user()->display_name );
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
			'retention-context'  => hash_hmac( 'sha256', get_current_user_id() . '|' . wp_get_session_token(), wp_salt( 'nonce' ) ),
			'name'               => $name,
			'email'              => $email,
			'company'            => $customer->get_billing_company(),
			'message'            => isset( $previous['message'] ) && is_string( $previous['message'] ) ? $previous['message'] : '',
			'action'             => admin_url( 'admin-post.php' ),
			'draft-url'          => wc_get_cart_url(),
			'draft-action'       => wc_get_checkout_url(),
			'login-url'          => wc_get_page_permalink( 'myaccount' ),
			'privacy'            => \Linker\Commerce\Presentation\PageUrls::translated( 'privacy-policy' ),
			'open'               => is_user_logged_in() && '' !== $name && '' !== $email && array() === $previous ? '' : 'open',
			'summary-hide'       => is_user_logged_in() ? '' : 'hidden',
			'draft-empty'        => WC()->cart->is_empty() ? 'hidden' : '',
			'consent-attributes' => is_user_logged_in() ? 'checked' : ( '1' === ( $previous['consent'] ?? '' ) ? 'required checked' : 'required' ),
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
		return $this->hidden_fields( str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en' );
	}

	/** Fields carried from the reviewed transfer through native retries.
	 *
	 * @param string $handoff Planner handoff ID.
	 * @param string $fingerprint Post-apply draft fingerprint.
	 */
	private static function planner_fields( string $handoff, string $fingerprint ): string {
		return '<input type="hidden" name="linker_planner_handoff_id" value="' . esc_attr( $handoff ) . '" /><input type="hidden" name="linker_planner_draft_sha256" value="' . esc_attr( $fingerprint ) . '" />';
	}

	/** Native guard and draft binding for both POST surfaces.
	 *
	 * @param string $language Form language.
	 * @param string $project Reviewed preliminary project reference.
	 */
	private function hidden_fields( string $language, string $project = '' ): string {
		$previous = $this->flash['fields'] ?? array();
		$project  = $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ?? $project;
		$binding  = '' === $project ? '' : '<input type="hidden" name="' . esc_attr( \Linker\Commerce\Planning\Context::PROJECT_FIELD ) . '" value="' . esc_attr( $project ) . '" />';
		if ( isset( $previous['linker_planner_handoff_id'] ) ) {
			$binding .= self::planner_fields( $previous['linker_planner_handoff_id'], $previous['linker_planner_draft_sha256'] );
		}
		return $binding . '<input type="hidden" name="action" value="linker_inquiry" /><input type="hidden" name="lang" value="' . esc_attr( $language ) . '" />'
		. '<input type="hidden" name="linker_inquiry_retained" value="' . ( array() !== (array) ( $this->flash['fields'] ?? array() ) ? '1' : '0' ) . '" />'
		. wp_nonce_field( Handler::nonce_action( $project ), Handler::NONCE, true, false ) . ( new PublicGuard() )->fields()
		. \Linker\Commerce\Protection\FormFields::render( 'inquiry', (string) ( $this->flash['fields']['linker_request_id'] ?? '' ), '1' === ( $this->flash['fields']['linker_individual_review'] ?? '' ), '0' !== ( $this->flash['fields']['linker_recovery_available'] ?? '1' ) );
	}

	/**
	 * Woo's own draft update handler consumes these fields.
	 */
	public function draft_nonce(): string {
		return wp_nonce_field( 'woocommerce-cart', 'woocommerce-cart-nonce', true, false ) . \Linker\Commerce\Protection\FormFields::render( 'draft_write' );
	}

	/**
	 * Reviewed bilingual words, resolved by the plugin's gettext catalogues.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function text( $atts = array() ): string {
		$words = array(
			'title'              => __( 'Send an inquiry', 'linker-commerce' ),
			'intro'              => __( 'Tell us what you need. The products in your solution draft will be included.', 'linker-commerce' ),
			'message'            => __( 'Message (optional)', 'linker-commerce' ),
			'details'            => __( 'Your reply details', 'linker-commerce' ),
			'change'             => __( 'Change', 'linker-commerce' ),
			'name'               => __( 'Name', 'linker-commerce' ),
			'email'              => __( 'Reply email', 'linker-commerce' ),
			'company'            => __( 'Company (optional)', 'linker-commerce' ),
			'consent'            => __( 'I agree that my details may be used to respond to this message.', 'linker-commerce' ),
			'privacy'            => __( 'Privacy', 'linker-commerce' ),
			'send'               => __( 'Send inquiry', 'linker-commerce' ),
			'promise'            => __( 'We reply within one business day.', 'linker-commerce' ),
			'no-account'         => __( 'No account needed.', 'linker-commerce' ),
			'partner'            => __( 'Have an approved account? Log in for net prices and saved details.', 'linker-commerce' ),
			'draft'              => __( 'Solution draft', 'linker-commerce' ),
			'edit'               => __( 'Edit solution draft', 'linker-commerce' ),
			'quantity'           => __( 'Quantity', 'linker-commerce' ),
			'update'             => __( 'Update solution draft', 'linker-commerce' ),
			'update-before-send' => __( 'Check the quantities in your solution draft and try again.', 'linker-commerce' ),
			'retention-error'    => __( 'Your browser could not save your entries. Stay on this page to avoid losing them.', 'linker-commerce' ),
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
