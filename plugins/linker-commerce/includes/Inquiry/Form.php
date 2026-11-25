<?php
/**
 * Data tags for the LiveCanvas inquiry form.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Presentation\Tokens;
use Linker\Commerce\Planning\InquiryTransfer;
use Linker\Commerce\Planning\DraftRecovery;
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
		add_action( 'template_redirect', array( $this, 'prepare_form_owner' ) );
		add_shortcode( 'linker_inquiry_text', array( $this, 'text' ) );
		add_shortcode( 'linker_inquiry_verification', fn (): string => \Linker\Commerce\Protection\FormFields::render( 'inquiry', (string) ( $this->flash['fields']['linker_request_id'] ?? '' ) ) );
		add_shortcode( 'linker_inquiry_hidden', array( $this, 'hidden' ) );
		add_shortcode( 'linker_inquiry_project_notes', array( $this, 'project_notes' ) );
		add_shortcode( 'linker_inquiry_lines', array( $this, 'lines' ) );
		add_shortcode( 'linker_inquiry_draft_nonce', array( $this, 'draft_nonce' ) );
	}

	/** Bind the native checkout form to its owner before rendering the theme. */
	public function prepare_form_owner(): void {
		if ( is_checkout() && ! is_wc_endpoint_url() ) {
			\Linker\Commerce\Cache\DynamicHtml::forbid( 'inquiry form' );
			\Linker\Commerce\Protection\Identity::ensure_browser_cookie();
		}
	}

	/**
	 * Active planning project notes, rendered separately from the customer message.
	 */
	public function project_notes(): string {
		$previous = (array) ( $this->flash['fields'] ?? array() );
		if ( ! empty( $this->flash['unavailable'] ) || ! empty( $previous['linker_without_project'] ) ) {
			return '<label class="linker-form-consent"><input type="checkbox" required name="linker_without_project"' . checked( ! empty( $previous['linker_without_project'] ), true, false ) . ' value="' . esc_attr( wp_create_nonce( 'linker_without_project:' . $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ) . '" /> ' . esc_html__( 'Send my inquiry without this project', 'linker-commerce' ) . '</label>' . self::retained_notes( $previous );
		}
		if ( isset( $previous['linker_planner_handoff_id'] ) || ( ( isset( $previous['linker_note_project'] ) || isset( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ) && '1' === $previous['linker_recovery_available'] ) ) {
			return self::retained_notes( $previous );
		}
		$note = null;
		if ( isset( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ) {
			$note = \Linker\Commerce\Planning\Context::read_preliminary_project( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] );
			if ( $note instanceof \WP_Error ) {
				return '<p role="alert">' . esc_html( $note->get_error_message() ) . '</p>' . self::retained_notes( $previous );
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

	/** Preserve the reviewed inclusion choice and revisions while they cannot be reread.
	 *
	 * @param array<string,mixed> $previous Native form fields.
	 */
	private static function retained_notes( array $previous ): string {
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

	/** Show this POST's correctable error on the current checkout response.
	 *
	 * @param array<string,mixed> $fields Retained native input; no proof or nonce.
	 * @param \WP_Error           $error  Native outcome.
	 * @param string              $locale Submitted language.
	 * @param string|null         $handle Existing attempt handle, or empty for a fresh authorized attempt.
	 */
	public function retry( array $fields, \WP_Error $error, string $locale, ?string $handle = null ): void {
		if ( null !== $handle && ! wp_is_uuid( (string) ( $fields['linker_request_id'] ?? '' ), 4 ) ) {
			$fields['linker_request_id'] = wp_generate_uuid4();
		}
		$this->flash = array(
			'fields'       => $fields,
			'error'        => $error->get_error_message(),
			'error_locale' => $locale,
			'unavailable'  => 'planning_preliminary_unavailable' === $error->get_error_code(),
		);
		if ( null !== $handle ) {
			$this->flash['retry'] = CheckoutRetry::remember( $this->flash, $handle );
		}
	}

	/**
	 * LC's own fragment with no PHP layout.
	 */
	public function render(): string {
		\Linker\Commerce\Cache\DynamicHtml::forbid( 'inquiry form' );
		if ( ! \Linker\Commerce\Protection\Identity::ensure_browser_cookie() ) {
			return '<p role="alert">' . esc_html( \Linker\Commerce\Protection\Business::verification_message( 'unavailable' ) ) . '</p>';
		}
		$missing = DraftRecovery::review();
		if ( $missing instanceof \WP_Error ) {
			return '<p class="woocommerce-info" role="alert">' . esc_html( $missing->get_error_message() ) . '</p>';
		}
		// This opaque handle reads only server-validated fields from the current Woo session.
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only recovery in the native session.
		if ( array() === $this->flash && isset( $_GET[ CheckoutRetry::HANDLE ] ) ) {
			// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- CheckoutRetry verifies this opaque UUID.
			$handle = is_string( $_GET[ CheckoutRetry::HANDLE ] ) ? wp_unslash( $_GET[ CheckoutRetry::HANDLE ] ) : '';
			$flash  = CheckoutRetry::read( $handle );
			if ( null === $flash ) {
				return '<p role="alert">' . esc_html__( 'The request status could not be confirmed. Please check before sending it again.', 'linker-commerce' ) . '</p>';
			}
			$this->flash = $flash + array( 'retry' => $handle );
		}
		if ( array() === $this->flash ) {
			foreach ( array( 'fields', 'error', 'error_locale' ) as $key ) {
				$this->flash[ $key ] = WC()->session->get( 'linker_inquiry_' . $key );
				WC()->session->set( 'linker_inquiry_' . $key, null );
			}
		}
		try {
			$template = str_replace( '{{inquiry-fields}}', self::fields_template(), Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/form.html' ) );
			$template = do_shortcode( $template );
			// Core intentionally refuses shortcode expansion in form actions and empty attributes.
			// Insert customer text last so a message can never execute shortcodes.
			return preg_replace_callback( '/\{\{([a-z-]+)\}\}/', fn ( array $token ): string => 'draft-recovery' === $token[1] ? $this->draft_recovery( $missing ) : $this->value( array( 'key' => $token[1] ) ), $template ) ?? '';
		} finally {
			$this->flash = array();
		}
	}

	/** The original inquiry carries the buyer’s choice together with their reply details.
	 *
	 * @param string[] $missing Keys in the native draft.
	 */
	private function draft_recovery( array $missing ): string {
		if ( array() === $missing ) {
			return '';
		}
		$cart  = WC()->cart->get_cart();
		$names = array_map( static fn ( string $key ): string => $cart[ $key ]['data']->get_name(), $missing );
		$nonce = wp_create_nonce( DraftRecovery::nonce_action( $missing ) );
		return '<fieldset class="woocommerce-info"><legend>' . esc_html__( 'A planning report is unavailable for these products:', 'linker-commerce' ) . ' ' . esc_html( implode( ', ', array_unique( $names ) ) ) . '</legend><p>' . esc_html__( 'You can keep all products and quantities in your inquiry.', 'linker-commerce' ) . '</p>'
			. '<label class="linker-form-consent"><input type="checkbox" required name="' . esc_attr( DraftRecovery::FIELD ) . '" value="' . esc_attr( $nonce ) . '"' . checked( $this->flash['fields'][ DraftRecovery::FIELD ] ?? '', $nonce, false ) . ' /><span>' . esc_html__( 'Remove unavailable report links', 'linker-commerce' ) . '</span></label></fieldset>';
	}

	/** One set of native reply, consent and submit fields. */
	private static function fields_template(): string {
		return Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/inquiry/fields.html' );
	}

	/** Render the review form with a nonce for the immutable project revision.
	 *
	 * @param string                   $language Requested planner language.
	 * @param array<string,mixed>      $project Owner-verified project revision.
	 * @param InquiryTransfer|null     $transfer Reviewed draft intent.
	 * @param array<string,mixed>|null $handoff Frozen projected report.
	 * @param array<string,mixed>|null $retry Native retry from this Woo session.
	 */
	public function planning( string $language, array $project, ?InquiryTransfer $transfer = null, ?array $handoff = null, ?array $retry = null ): string {
		$this->flash = $retry ?? array();
		$locale      = new \Linker\Commerce\Mail\LocaleSwitch();
		$locale->to( OrderLocale::current( $language ) );
		try {
			$fields   = preg_replace_callback(
				'/\{\{([a-z-]+)\}\}/',
				fn ( array $token ): string => $this->value(
					array(
						'key'      => $token[1],
						'language' => $language,
					)
				),
				do_shortcode( self::fields_template() )
			) ?? '';
			$replay   = \Linker\Commerce\Protection\Ledger::RECEIPT_SECONDS;
			$previous = $this->flash['fields'] ?? array();
			$error    = $this->value( array( 'key' => 'error' ) );
			$notes    = '1' === ( $previous['linker_inquiry_receipt_only'] ?? '' )
				? self::retained_notes( $previous )
				: \Linker\Commerce\Planning\Context::inquiry_notes_section( $previous, $handoff, $project, show_project: false );
			return do_shortcode( '[linker_inquiry_restriction]' )
				. '<form class="linker-inquiry-form" data-linker-inquiry-replay-seconds="' . esc_attr( (string) $replay ) . '" data-inquiry-context="' . $this->value( array( 'key' => 'retention-context' ) ) . '" method="post" action="' . esc_url( admin_url( 'admin-post.php' ) ) . '">'
				. $this->hidden_fields( $previous['linker_inquiry_original_language'] ?? $language, $project['project_id'] . ':' . $project['revision'], $transfer )
				. ( '' === $error ? '' : '<p class="linker-inquiry-error" role="alert">' . $error . '</p>' )
				. $notes . $fields . '</form>';
		} finally {
			$this->flash = array();
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
			'retention-context'  => CheckoutRetry::context(),
			'name'               => $name,
			'email'              => $email,
			'company'            => $customer->get_billing_company(),
			'message'            => isset( $previous['message'] ) && is_string( $previous['message'] ) ? $previous['message'] : '',
			'action'             => isset( $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ) ? Checkout::request_url( OrderLocale::current( $this->submission_language() ) ) : admin_url( 'admin-post.php' ),
			'draft-url'          => wc_get_cart_url(),
			'draft-action'       => wc_get_checkout_url(),
			'login-url'          => wc_get_page_permalink( 'myaccount' ),
			'privacy'            => \Linker\Commerce\Presentation\PageUrls::translated( 'privacy-policy', $atts['language'] ?? null ),
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
		return $this->hidden_fields( $this->submission_language() );
	}

	/** Recover the previous locale used in the native journal's input fingerprint. */
	private function submission_language(): string {
		return $this->flash['fields']['linker_inquiry_original_language'] ?? ( str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en' );
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
	 * @param string               $language Form language.
	 * @param string               $project Reviewed project reference.
	 * @param InquiryTransfer|null $transfer Reviewed report and draft.
	 */
	private function hidden_fields( string $language, string $project = '', ?InquiryTransfer $transfer = null ): string {
		$previous = $this->flash['fields'] ?? array();
		$project  = $previous[ \Linker\Commerce\Planning\Context::PROJECT_FIELD ] ?? $project;
		$binding  = '' === $project ? '' : '<input type="hidden" name="' . esc_attr( \Linker\Commerce\Planning\Context::PROJECT_FIELD ) . '" value="' . esc_attr( $project ) . '" />';
		if ( null !== $transfer ) {
			$binding .= '<input type="hidden" name="' . esc_attr( InquiryTransfer::FIELD ) . '" value="' . esc_attr( $transfer->value() ) . '" />';
		}
		if ( isset( $previous['linker_planner_handoff_id'] ) ) {
			$binding .= self::planner_fields( $previous['linker_planner_handoff_id'], $previous['linker_planner_draft_sha256'] );
		}
		if ( isset( $this->flash['retry'] ) ) {
			$binding .= '<input type="hidden" name="' . CheckoutRetry::HANDLE . '" value="' . esc_attr( $this->flash['retry'] ) . '" data-linker-retry-pending="' . ( '1' === $previous['linker_recovery_available'] ? 'true' : 'false' ) . '" />';
		}
		if ( '1' === ( $previous['linker_inquiry_receipt_only'] ?? '' ) ) {
			$binding .= '<input type="hidden" name="linker_inquiry_receipt_only" value="1" />';
		}
		return $binding . '<input type="hidden" name="action" value="linker_inquiry" /><input type="hidden" name="lang" value="' . esc_attr( $language ) . '" />'
		. '<input type="hidden" name="linker_inquiry_retained" value="' . ( array() !== (array) ( $this->flash['fields'] ?? array() ) ? '1' : '0' ) . '" />'
		. '<input type="hidden" name="linker_draft_hash" value="' . $this->value( array( 'key' => 'draft-hash' ) ) . '" />'
		. wp_nonce_field( Handler::nonce_action( $project, $transfer ), Handler::NONCE, true, false ) . PublicGuard::fields();
	}

	/**
	 * Woo's own draft update handler consumes these fields.
	 */
	public function draft_nonce(): string {
		return wp_nonce_field( 'woocommerce-cart', 'woocommerce-cart-nonce', true, false );
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
			'message'            => __( 'Project message', 'linker-commerce' ),
			'details'            => __( 'Your reply details', 'linker-commerce' ),
			'change'             => __( 'Change', 'linker-commerce' ),
			'name'               => __( 'Name', 'linker-commerce' ),
			'email'              => __( 'Work email', 'linker-commerce' ),
			'company'            => __( 'Company', 'linker-commerce' ),
			'consent'            => __( 'I agree that my details may be used to respond to this message.', 'linker-commerce' ),
			'privacy'            => __( 'Privacy', 'linker-commerce' ),
			'send'               => '1' === ( $this->flash['fields']['linker_inquiry_receipt_only'] ?? '' )
				? __( 'Try again', 'linker-commerce' )
				: __( 'Send inquiry', 'linker-commerce' ),
			'promise'            => __( 'We reply within one business day.', 'linker-commerce' ),
			'no-account'         => __( 'No account needed.', 'linker-commerce' ),
			'partner-summary'    => __( 'Already a Linker partner? Sign in', 'linker-commerce' ),
			'sign-in'            => __( 'Sign in', 'linker-commerce' ),
			'optional'           => __( 'optional', 'linker-commerce' ),
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
			$source_id = \Linker\Commerce\Products\Publication::canonical_id( $product->get_id() );
			$source    = $source_id === $product->get_id() ? $product : wc_get_product( $source_id );
			$in_stock  = $source instanceof \WC_Product && $source->is_in_stock();
			$html     .= strtr(
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
					'{{sku}}'                => $source instanceof \WC_Product ? esc_attr( (string) $source->get_sku() ) : '',
					'{{stock-state}}'        => $in_stock ? 'in-stock' : 'unavailable',
					'{{availability}}'       => $in_stock ? esc_html__( 'In stock', 'linker-commerce' ) : esc_html__( 'Currently unavailable', 'linker-commerce' ),
					'{{decrease}}'           => esc_attr( sprintf( /* translators: %s: product name. */ __( 'Decrease quantity for %s', 'linker-commerce' ), $product->get_name() ) ),
					'{{increase}}'           => esc_attr( sprintf( /* translators: %s: product name. */ __( 'Increase quantity for %s', 'linker-commerce' ), $product->get_name() ) ),
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
