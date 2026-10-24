<?php
/**
 * What happens when the contact form is sent.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Inquiry\PublicGuard;
use Linker\Commerce\Inquiry\Sender;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Presentation\PageUrls;
use WP_Error;
use Linker\Commerce\Protection\Business;

/**
 * The admin-post handler of the contact form (ticket #68, GAP-8): the form
 * posts here, the message goes through the mail pipeline (the receipt to the
 * visitor, the team letter with the settings' blind copies), and the visitor
 * returns to the page with the state in the address — none of it needs
 * JavaScript.
 *
 * The form is public, so it carries the protections a public form needs: a
 * nonce, a honeypot ("website"), and a small per-connection limit that keeps
 * one connection from filling the shared host's mail quota. Filled honeypots and forged clocks are rejected before any inquiry is written.
 */
final class Handler {


	/**
	 * The action the form posts (admin_post[_nopriv]_linker_contact).
	 */
	public const ACTION = Form::ACTION;

	/**
	 * Adds the handler; it runs for visitors and for signed-in customers alike.
	 */
	public function register(): void {
		add_action( 'admin_post_nopriv_' . self::ACTION, array( $this, 'handle' ) );
		add_action( 'admin_post_' . self::ACTION, array( $this, 'handle' ) );
	}

	/**
	 * Takes the posted form: validates, sends, and returns to the page.
	 */
	public function handle(): void {
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- the nonce is verified below, before anything is read or sent.
		$post  = wp_unslash( $_POST );
		$back  = $this->back_url( $post );
		$state = $this->process( $post );
		if ( ! in_array( $state, array( 'sent', 'sent_no_receipt', 'saved_review' ), true ) ) {
			\Linker\Commerce\Protection\FormRecovery::save( 'contact', $post );
		}
		$this->back( $back, $state );
	}

	/**
	 * The decision of one submission, without the redirect: the state the
	 * visitor returns to, and the sending a delivered message causes.
	 *
	 * @phpstan-impure
	 *
	 * @param  array<string, mixed> $post The posted values, unslashed.
	 * @return string `sent`, `sent_no_receipt`, `invalid` or `throttled`.
	 */
	public function process( array $post ): string {
		$nonce = isset( $post[ Form::NONCE_FIELD ] ) && is_string( $post[ Form::NONCE_FIELD ] ) ? sanitize_text_field( $post[ Form::NONCE_FIELD ] ) : '';
		if ( ! wp_verify_nonce( $nonce, Form::NONCE_ACTION ) ) {
			return 'invalid';
		}

		$submission = Submission::from_post( $post );
		if ( $submission instanceof WP_Error || ! ( new PublicGuard() )->allows( $post, ! Business::enabled() ) ) {
			return 'invalid';
		}

		if ( ! Business::enabled() && ! ( new PublicGuard() )->take() ) {
			return 'throttled';
		}

		$selection = $submission->selection();
		$payload   = get_object_vars( $submission );
		if ( array() !== $selection ) {
			$payload['selection'] = $selection;
		}
		// Woo handles string slashing consistently across classic and HPOS metadata stores.
		$order = Business::run( 'contact', $post, $payload, static fn () => ( new Sender() )->message( $submission, array() !== $selection ? array( SelectionContext::META => (string) wp_json_encode( $selection ) ) : array() ) );
		if ( $order instanceof WP_Error ) {
			$code = $order->get_error_code();
			return match ( $code ) {
				'linker_business_capacity' => 'reception_full',
				'linker_intake_size' => 'review_size',
				'linker_intake_full' => 'review_full',
				'linker_intake_grouped' => 'grouped',
				'linker_admission_quota' => 'throttled',
				'linker_intake_busy', 'linker_intake_pending', 'linker_admission_pending', 'linker_admission_already_completed' => 'pending',
				'linker_admission_proof', 'linker_admission_proof_reused', 'linker_admission_payload_changed', 'linker_admission_input' => 'verification_failed',
				default => 'verification_unavailable',
			};
		}
		if ( $order->get_meta( \Linker\Commerce\Protection\Intake::META ) ) {
			\Linker\Commerce\Protection\IntakeAdmin::remember( $order );
			return 'saved_review';
		}
		return ! in_array( $order->get_meta( ReceiptLimit::SKIPPED_META ), array( '', 'assessment_pending' ), true ) ? 'sent_no_receipt' : 'sent';
	}

	/**
	 * Where the visitor returns: the page the form was rendered on (posted by
	 * the form itself), without anything that is not this site.
	 *
	 * @param array<string, mixed> $post The posted values.
	 */
	private function back_url( array $post ): string {
		$posted = isset( $post[ Form::BACK_FIELD ] ) ? esc_url_raw( (string) $post[ Form::BACK_FIELD ] ) : '';
		if ( '' === $posted ) {
			return PageUrls::page( 'contact' );
		}
		$host = (string) wp_parse_url( $posted, PHP_URL_HOST );
		if ( '' !== $host && strtolower( $host ) !== strtolower( (string) wp_parse_url( home_url(), PHP_URL_HOST ) ) ) {
			return PageUrls::page( 'contact' );
		}
		return $posted;
	}

	/**
	 * Returns to the page with the state and leaves the request.
	 *
	 * @param string $back  The page.
	 * @param string $state `sent`, `sent_no_receipt`, `invalid` or `throttled`.
	 */
	private function back( string $back, string $state ): void {
		wp_safe_redirect( add_query_arg( Form::STATE_PARAM, $state, $back ) . '#' . Form::ANCHOR );
		exit;
	}
}
