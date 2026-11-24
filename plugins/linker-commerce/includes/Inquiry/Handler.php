<?php
/**
 * Browser adapter of the shared inquiry sender.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\DraftPreview;
use Linker\Commerce\Planning\InquiryTransfer;
use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Protection\Configuration;
use WC_Order;
use WP_Error;
use Linker\Commerce\Protection\Business;

/**
 * Transport, public-request checks, and a redirect; Sender owns the write.
 */
final class Handler {


	public const ACTION = 'linker_inquiry';
	public const NONCE  = 'linker_inquiry_nonce';

	/** Only the current checkout POST's form; never shared between browser requests.
	 *
	 * @param Form $form Native form registered for this request.
	 */
	public function __construct( private readonly Form $form = new Form() ) {}

	/** Bind preliminary forms to the reviewed revision. Older handlers reject this nonce.
	 *
	 * @param string               $project Project reference, empty for ordinary and legacy forms.
	 * @param InquiryTransfer|null $transfer Exact report draft shown with this form.
	 */
	public static function nonce_action( string $project, ?InquiryTransfer $transfer = null ): string {
		if ( '' === $project ) {
			return self::ACTION;
		}
		return self::ACTION . ':' . $project . ( null === $transfer ? '' : ':' . $transfer->value() );
	}

	/** The explicit omission was authenticated in this process() call, not inferred from POST or errors.
	 *
	 * @var bool
	 */
	private bool $without_project = false;

	/** The original project binding passed its native nonce check.
	 *
	 * @var bool
	 */
	private bool $preliminary_verified = false;

	/**
	 * Both guests and account holders use this adapter.
	 */
	public function register(): void {
		add_action( 'admin_post_nopriv_' . self::ACTION, array( $this, 'handle' ) );
		add_action( 'admin_post_' . self::ACTION, array( $this, 'handle' ) );
		add_action( 'template_redirect', array( $this, 'checkout_post' ), 1 );
		// Core reads POST into public query vars: name would select a post, company a Woo account endpoint.
		// phpcs:ignore WordPress.Security.NonceVerification.Missing, WordPress.Security.ValidatedSanitizedInput -- Only compare the literal action. checkout_post() verifies before writing.
		if ( self::ACTION === ( $_POST['action'] ?? '' ) && isset( $_POST[ Context::PROJECT_FIELD ] ) ) {
			add_filter(
				'request',
				static function ( array $vars ): array {
					$language = is_string( $_POST['lang'] ?? null ) ? sanitize_key( wp_unslash( $_POST['lang'] ) ) : null; // phpcs:ignore WordPress.Security.NonceVerification.Missing -- Select the configured page, never a posted URL.
					$path     = wp_parse_url( Checkout::request_url( OrderLocale::current( $language ) ), PHP_URL_PATH );
					$request  = wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Compared to the configured path only.
					if ( is_string( $path ) && is_string( $request ) && untrailingslashit( $path ) === untrailingslashit( $request ) ) {
						unset( $vars['name'], $vars['company'] );
					}
					return $vars;
				}
			);
		}
	}

	/**
	 * Verifies before creating any inquiry or email.
	 *
	 * @phpstan-impure
	 *
	 * @param  array<string, mixed> $post Unslashed fields.
	 * @return WC_Order|WP_Error The received inquiry or validation failure.
	 */
	public function process( array $post ): WC_Order|WP_Error {
		$this->without_project      = false;
		$this->preliminary_verified = false;
		$language                   = isset( $post['lang'] ) && is_string( $post['lang'] ) ? sanitize_key( $post['lang'] ) : null;
		$locale                     = new LocaleSwitch();
		$locale->to( OrderLocale::current( $language ) );
		try {
			$nonce       = $post[ self::NONCE ] ?? '';
			$project     = $post[ Context::PROJECT_FIELD ] ?? '';
			$transfer    = InquiryTransfer::read( $post[ InquiryTransfer::FIELD ] ?? null );
			$nonce_valid = is_string( $project ) && is_string( $nonce ) && wp_verify_nonce( $nonce, self::nonce_action( $project, $transfer ) );
			if ( array_key_exists( InquiryTransfer::FIELD, $post ) && ( null === $transfer || '' === $project ) ) {
				$nonce_valid = false;
			}
			$handle   = is_string( $post[ CheckoutRetry::HANDLE ] ?? null ) ? $post[ CheckoutRetry::HANDLE ] : '';
			$retained = CheckoutRetry::read( $handle )['fields'] ?? null;
			// A live handle can only continue its own submission. With no retained entry,
			// the nonce and original UUID still allow the native ledger to return a prior receipt.
			$retry_matches              = ! is_array( $retained ) || ( ( $retained[ Context::PROJECT_FIELD ] ?? '' ) === $project && ( $retained['linker_request_id'] ?? '' ) === ( $post['linker_request_id'] ?? '' ) );
			$this->preliminary_verified = $nonce_valid && $retry_matches && '' !== $project;
			if ( ! $nonce_valid || ! $retry_matches || ! PublicGuard::allows( $post ) ) {
				return new WP_Error( 'linker_inquiry_invalid', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
			}
			if ( '' !== $project && isset( $post['linker_without_project'] ) ) {
				if ( null !== $transfer || ! is_string( $post['linker_without_project'] ) || ! wp_verify_nonce( $post['linker_without_project'], 'linker_without_project:' . $project ) ) {
					return new WP_Error( 'linker_inquiry_invalid', __( 'Please check your entries and send the form again.', 'linker-commerce' ) );
				}
				// The customer opted out of this preliminary project, not the rest of the reviewed cart.
				unset( $post[ Context::PROJECT_FIELD ] );
				if ( is_array( $post[ Context::REVISIONS_FIELD ] ?? null ) ) {
					unset( $post[ Context::REVISIONS_FIELD ][ 'project_' . explode( ':', $project, 2 )[0] ] );
				}
				$this->without_project = true;
				$project               = '';
			}
			$details = Submission::from_post( $post, false );
			if ( $details instanceof WP_Error ) {
				return $details;
			}
			$draft   = isset( $post['linker_draft_hash'] ) && is_string( $post['linker_draft_hash'] ) ? $post['linker_draft_hash'] : '';
			$payload = array(
				'details' => get_object_vars( $details ),
				'billing' => BillingFields::values( $post ),
				'draft'   => $draft,
			);
			if ( isset( $post[ \Linker\Commerce\Planning\Context::PRESENT_FIELD ] ) || isset( $post[ \Linker\Commerce\Planning\Context::REVISIONS_FIELD ] ) ) {
				$payload['project_notes'] = \Linker\Commerce\Planning\Context::submission_fingerprint( $post );
			}
			if ( '' !== $project ) {
				$payload['preliminary_project'] = $project;
			}
			$sender  = new Sender();
			$current = hash_equals( WC()->cart->get_cart_hash(), $draft );
			if ( isset( $post['linker_planner_handoff_id'] ) || isset( $post['linker_planner_draft_sha256'] ) ) {
				$id                 = $post['linker_planner_handoff_id'] ?? '';
				$fingerprint        = $post['linker_planner_draft_sha256'] ?? '';
				$contexts           = Context::active() + Context::report_only_contexts();
				$payload['planner'] = array(
					'handoff' => is_string( $id ) ? $id : '',
					'draft'   => is_string( $fingerprint ) ? $fingerprint : '',
				);
				$current            = is_string( $id ) && isset( $contexts[ $id ] )
					&& is_string( $fingerprint ) && hash_equals( DraftPreview::fingerprint(), $fingerprint )
					&& hash_equals( WC()->cart->get_cart_hash(), $draft );
			}
			if ( null !== $transfer ) {
				$payload['report_transfer'] = $transfer->value();
				$current                    = $current && $transfer->current();
				$result                     = $this->send_report( $sender, $details, $post, $payload, $transfer, $project, $current );
				return $result;
			}
			// Conversation summaries belong to the separately reviewed Genie confirmation.
			return \Linker\Commerce\Planning\Context::with_submission(
				$post,
				static fn (): WC_Order|WP_Error => Business::run( 'inquiry', $post, $payload, static fn () => $sender->request( $details, $post, false ), $current, static fn () => $sender->preflight( $details ) )
			);
		} finally {
			$locale->back();
		}
	}

	/**
	 * Recover the original Woo order first. Only a newly admitted request
	 * can apply the reviewed transfer and write the inquiry.
	 *
	 * @param Sender              $sender Native inquiry writer.
	 * @param Submission          $details Validated contact details.
	 * @param array<string,mixed> $post Unslashed form fields.
	 * @param array<string,mixed> $payload Semantic idempotence input.
	 * @param InquiryTransfer     $transfer Reviewed report and draft.
	 * @param string              $project Nonce-bound project revision.
	 * @param bool                $current Current native draft still equals the review.
	 */
	private function send_report( Sender $sender, Submission $details, array $post, array $payload, InquiryTransfer $transfer, string $project, bool $current ): WC_Order|WP_Error {
		$frozen  = null;
		$prepare = static function () use ( $transfer, $project, &$frozen ): ?WP_Error {
			$owned = Context::read_preliminary_project( $project );
			if ( is_wp_error( $owned ) ) {
				return $owned;
			}
			$handoff = $transfer->owned( $owned['project_id'], $owned['revision'] );
			if ( is_wp_error( $handoff ) ) {
				return $handoff;
			}
			$frozen = $handoff;
			return null;
		};
		$work    = static function () use ( $sender, $details, $post, $transfer, $prepare, &$frozen ): WC_Order|WP_Error {
			$error = null === $frozen ? $prepare() : null;
			if ( $error instanceof WP_Error ) {
				return $error;
			}
			if ( ! is_array( $frozen ) ) {
				return Context::admission_unavailable();
			}
			$result = Context::with_submission(
				$post,
				static fn (): WC_Order|WP_Error => $sender->request(
					$details,
					$post,
					false,
					review: array(
						'intent'  => $transfer,
						'handoff' => $frozen,
					)
				)
			);
			return $result instanceof WP_Error && in_array( $result->get_error_code(), array( 'planning_draft_changed', 'planning_transfer_changed', 'out-of-stock' ), true ) ? self::draft_changed() : $result;
		};
		return Business::run( 'inquiry', $post, $payload, $work, $current, $prepare );
	}

	/** A confirmed draft change is safe to show for a fresh review. */
	private static function draft_changed(): WP_Error {
		return new WP_Error( 'linker_draft_changed', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ) );
	}

	/**
	 * Native form transport, retaining entries on a validation failure.
	 */
	public function handle(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- Only forwards; process() verifies on the destination.
		$post = wp_unslash( $_POST );
		if ( isset( $post[ Context::PROJECT_FIELD ] ) ) {
			$language = is_string( $post['lang'] ?? null ) ? $post['lang'] : null;
			// Keep the POST body in this tab. No write, proof consumption or Woo flash before the redirect.
			wp_safe_redirect( Checkout::request_url( OrderLocale::current( $language ) ), 307 );
			exit;
		}
		$this->submit( $post, false );
	}

	/** Process a forwarded preliminary form before the native inquiry page renders. */
	public function checkout_post(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- process() verifies the revision-bound nonce before any inquiry.
		$post = wp_unslash( $_POST );
		if ( self::ACTION === ( $post['action'] ?? '' ) && isset( $post[ Context::PROJECT_FIELD ] ) && is_checkout() && ! is_wc_endpoint_url() ) {
			\Linker\Commerce\Cache\DynamicHtml::forbid( 'preliminary inquiry' );
			$this->submit( $post, true );
		}
	}

	/** Run the native writer exactly once; only ordinary admin-post errors use a redirect and flash.
	 *
	 * @param array<string,mixed> $post Unslashed fields.
	 * @param bool                $on_checkout Already on the inquiry page.
	 */
	private function submit( array $post, bool $on_checkout ): void {
		wc_load_cart();
		$result = $this->process( $post );
		$handle = is_string( $post[ CheckoutRetry::HANDLE ] ?? null ) ? $post[ CheckoutRetry::HANDLE ] : '';
		if ( $result instanceof WC_Order && $result->get_meta( \Linker\Commerce\Protection\Intake::META ) ) {
			\Linker\Commerce\Protection\IntakeAdmin::remember( $result );
		}
		if ( $result instanceof WC_Order ) {
			if ( $on_checkout ) {
				CheckoutRetry::forget( $handle, fresh: isset( $post[ InquiryTransfer::FIELD ] ) );
			}
			if ( ! $on_checkout ) {
				WC()->session->set( 'linker_inquiry_fields', null );
				WC()->session->set( 'linker_intake_grouped', null );
				WC()->session->set( 'linker_inquiry_error', null );
				WC()->session->set( 'linker_inquiry_error_locale', null );
			}
			\Linker\Commerce\Consent\BasicMode::remember_conversion( 'generate_lead', array( 'lead_surface' => isset( $post[ Context::PROJECT_FIELD ] ) || isset( $post[ InquiryTransfer::FIELD ] ) ? 'configurator_inquiry' : 'inquiry' ) );
			wp_safe_redirect( $result->get_checkout_order_received_url(), $on_checkout ? 303 : 302 );
		} else {
			if ( WC()->session instanceof \WC_Session_Handler ) {
				WC()->session->set_customer_session_cookie( true );
			}
			$fields = array();
			foreach ( array( 'name', 'email', 'company', 'message', 'linker_request_id', 'linker_inquiry_receipt_only', 'linker_individual_review', \Linker\Commerce\Planning\DraftRecovery::FIELD, \Linker\Commerce\Planning\Context::PRESENT_FIELD ) as $key ) {
				$fields[ $key ] = isset( $post[ $key ] ) && is_string( $post[ $key ] ) ? sanitize_textarea_field( $post[ $key ] ) : '';
			}
			$fields['consent'] = '1' === ( $post['consent'] ?? '' ) ? '1' : '';
			$fields[ \Linker\Commerce\Planning\Context::INCLUDE_FIELD ] = '1' === ( $post[ \Linker\Commerce\Planning\Context::INCLUDE_FIELD ] ?? '' ) ? '1' : '';
			// A definite refusal returns to fresh verification. Unknown/pending
			// outcomes may first recover their existing UUID without a new proof.
			$fields['linker_recovery_available'] = \Linker\Commerce\Protection\FormRecovery::after_error( $result ) ? '1' : '0';
			$revisions                           = Context::submission_fingerprint( $post )['revisions'];
			if ( is_string( $post[ Context::PROJECT_FIELD ] ?? null ) && preg_match( '/\A[a-f0-9]{32}:[1-9][0-9]*\z/', $post[ Context::PROJECT_FIELD ] ) ) {
				$fields[ Context::PROJECT_FIELD ] = $post[ Context::PROJECT_FIELD ];
			} else {
				foreach ( array_keys( $revisions ) as $key ) {
					if ( is_string( $key ) && preg_match( '/\Aproject_([a-f0-9]{32})\z/', $key, $match ) ) {
						$fields['linker_note_project'] = $match[1];
						break;
					}
				}
			}
			if ( isset( $fields[ Context::PROJECT_FIELD ] ) || isset( $fields['linker_note_project'] ) ) {
				$fields[ Context::REVISIONS_FIELD ] = $revisions;
				if ( '1' === $fields['linker_recovery_available'] ) {
					$fields['linker_draft_hash'] = is_string( $post['linker_draft_hash'] ?? null ) ? $post['linker_draft_hash'] : '';
				}
			}
			if ( '1' === $fields['linker_recovery_available'] && isset( $post['linker_planner_handoff_id'], $post['linker_planner_draft_sha256'] ) ) {
				foreach ( array( 'linker_planner_handoff_id', 'linker_planner_draft_sha256', 'linker_draft_hash' ) as $key ) {
					$fields[ $key ] = is_string( $post[ $key ] ?? null ) ? sanitize_text_field( $post[ $key ] ) : '';
				}
				$fields[ Context::REVISIONS_FIELD ] = $revisions;
			}
			$fields['billing'] = BillingFields::values( $post );
			if ( \Linker\Commerce\Protection\FormRecovery::superseded( $result ) ) {
				// The journal holds this UUID for other input; a new one is the
				// only way past the changed-input refusal.
				$fields['linker_request_id'] = '';
			}
			$blocked  = 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode() && \Linker\Commerce\Protection\Campaign::recovery_matches( $post, false );
			$language = isset( $post['lang'] ) && is_string( $post['lang'] ) ? sanitize_key( $post['lang'] ) : null;
			if ( $on_checkout ) {
				$transfer = InquiryTransfer::read( $post[ InquiryTransfer::FIELD ] ?? null );
				if ( null !== $transfer && $this->preliminary_verified && ! $blocked && isset( $fields[ Context::PROJECT_FIELD ] ) ) {
					$locale = OrderLocale::current( $language );
					$page   = PageUrls::translated( 'solution-configurator', str_starts_with( $locale, 'de' ) ? 'de' : 'en' );
					if ( '' !== $page ) {
						$fields[ InquiryTransfer::FIELD ] = $transfer->value();
						if ( '1' === $fields['linker_recovery_available'] ) {
							$fields['linker_inquiry_receipt_only']      = '1';
							$fields['linker_inquiry_original_language'] = str_starts_with( $locale, 'de' ) ? 'de' : 'en';
						} elseif ( Business::enabled() ) {
							$fields['linker_request_id'] = wp_generate_uuid4();
						}
						$retry = CheckoutRetry::remember(
							array(
								'fields'       => $fields,
								'error'        => $result->get_error_message(),
								'error_locale' => $locale,
								'grouped'      => 'linker_intake_grouped' === $result->get_error_code(),
							),
							$handle,
							fresh: true
						);
						if ( null === $retry ) {
							wp_die(
								esc_html( $result->get_error_message() ),
								'',
								array(
									'response'  => 503,
									'back_link' => true,
								)
							);
						}
						list( $project_id, $review_revision ) = explode( ':', $fields[ Context::PROJECT_FIELD ], 2 );
						$url                                  = add_query_arg(
							array(
								'project'             => $project_id,
								'guided'              => 'inquiry',
								'run'                 => $transfer->report,
								'retry_revision'      => $review_revision,
								CheckoutRetry::HANDLE => $retry,
							),
							$page
						);
						wp_safe_redirect( $url . '#sc-review', 303 );
						exit;
					}
				}
				if ( $blocked || ! isset( $fields[ Context::PROJECT_FIELD ] ) ) {
					CheckoutRetry::forget( $handle );
					wp_die( esc_html( $result->get_error_message() ), '', array( 'response' => 400 ) );
				}
				$fields['linker_without_project'] = $this->without_project;
				$locale                           = OrderLocale::current( $language );
				if ( '1' === $fields['linker_recovery_available'] ) {
					$fields['linker_inquiry_original_language'] = str_starts_with( $locale, 'de' ) ? 'de' : 'en';
				}
				$this->form->retry( $fields, $result, $locale, $this->preliminary_verified ? $handle : null );
				return;
			}
			WC()->session->set( 'linker_inquiry_fields', $blocked ? null : $fields );
			WC()->session->set( 'linker_inquiry_error', $result->get_error_message() );
			WC()->session->set( 'linker_inquiry_error_locale', OrderLocale::current( $language ) );
			WC()->session->set( 'linker_intake_grouped', 'linker_intake_grouped' === $result->get_error_code() );
			wp_safe_redirect( Checkout::request_url( OrderLocale::current( $language ) ) );
		}
		exit;
	}
}
