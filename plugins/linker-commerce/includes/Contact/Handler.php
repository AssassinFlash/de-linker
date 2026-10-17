<?php
/**
 * What happens when the contact form is sent.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\Commerce\Contact\Emails\ReceiptEmail;
use Linker\Commerce\Contact\Emails\TeamMessageEmail;
use Linker\Commerce\Settings\Options;
use WP_Error;

/**
 * The admin-post handler of the contact form (ticket #68, GAP-8): the form
 * posts here, the message goes through the mail pipeline (the receipt to the
 * visitor, the team letter with the settings' blind copies), and the visitor
 * returns to the page with the state in the address — none of it needs
 * JavaScript.
 *
 * The form is public, so it carries the protections a public form needs: a
 * nonce, a honeypot ("website"), and a small per-connection limit that keeps
 * one connection from filling the shared host's mail quota. A filled honeypot
 * is answered like a delivered message and sent nowhere.
 */
final class Handler {


	/**
	 * The action the form posts (admin_post[_nopriv]_linker_contact).
	 */
	public const ACTION = Form::ACTION;

	/**
	 * Messages one connection may send per window.
	 */
	public const LIMIT = 3;

	/**
	 * Length of the window, in seconds.
	 */
	public const WINDOW = HOUR_IN_SECONDS;

	/**
	 * Sets up the handler.
	 *
	 * @param string  $plugin_file Absolute path of the main plugin file.
	 * @param Options $options     The plugin settings (internal notification address, blind copies).
	 */
	public function __construct(
		private readonly string $plugin_file,
		private readonly Options $options
	) {
	}

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
		$post = wp_unslash( $_POST );
		$back = $this->back_url( $post );
		$this->back( $back, $this->process( $post ) );
	}

	/**
	 * The decision of one submission, without the redirect: the state the
	 * visitor returns to, and the sending a delivered message causes.
	 *
	 * @param  array<string, mixed> $post The posted values, unslashed.
	 * @return string `sent`, `invalid` or `throttled`.
	 */
	public function process( array $post ): string {
		$nonce = isset( $post[ Form::NONCE_FIELD ] ) ? sanitize_text_field( (string) $post[ Form::NONCE_FIELD ] ) : '';
		if ( ! wp_verify_nonce( $nonce, Form::NONCE_ACTION ) ) {
			return 'invalid';
		}

		if ( '' !== trim( (string) ( $post[ Form::TRAP_FIELD ] ?? '' ) ) ) {
			// A filled honeypot is a bot: answer like a delivery, send nothing.
			return 'sent';
		}

		if ( ! $this->within_limit() ) {
			return 'throttled';
		}

		$submission = Submission::from_post( $post );
		if ( $submission instanceof WP_Error ) {
			return 'invalid';
		}

		$this->count();
		$this->send( $submission );
		return 'sent';
	}

	/**
	 * Both emails: the receipt to the visitor, the letter to the internal
	 * notification address with the settings' blind copies. The email classes are built here, not
	 * when the plugin loads: WC_Email exists once WooCommerce is loaded.
	 *
	 * @param Submission $submission The visitor's message.
	 */
	private function send( Submission $submission ): void {
		( new ReceiptEmail( $this->plugin_file ) )->notify( $submission );
		( new TeamMessageEmail( $this->plugin_file, $this->options ) )->notify( $submission );
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
			return home_url( '/contact/' );
		}
		$host = (string) wp_parse_url( $posted, PHP_URL_HOST );
		if ( '' !== $host && strtolower( $host ) !== strtolower( (string) wp_parse_url( home_url(), PHP_URL_HOST ) ) ) {
			return home_url( '/contact/' );
		}
		return $posted;
	}

	/**
	 * Returns to the page with the state and leaves the request.
	 *
	 * @param string $back  The page.
	 * @param string $state `sent`, `invalid` or `throttled`.
	 */
	private function back( string $back, string $state ): void {
		wp_safe_redirect( add_query_arg( Form::STATE_PARAM, $state, $back ) . '#' . Form::ANCHOR );
		exit;
	}

	/**
	 * Whether this connection may send another message.
	 */
	private function within_limit(): bool {
		return \count( $this->recent() ) < self::LIMIT;
	}

	/**
	 * Counts this attempt.
	 */
	private function count(): void {
		$recent   = $this->recent();
		$recent[] = time();
		set_transient( $this->key(), $recent, self::WINDOW );
	}

	/**
	 * The times of this connection's messages within the window.
	 *
	 * @return list<int>
	 */
	private function recent(): array {
		$stored = get_transient( $this->key() );
		$times  = array();
		foreach ( \is_array( $stored ) ? $stored : array() as $time ) {
			if ( \is_int( $time ) && $time > time() - self::WINDOW ) {
				$times[] = $time;
			}
		}
		return $times;
	}

	/**
	 * The transient of this connection. The address is the one the connection
	 * came from — never a forwarded header, which a sender could set freely.
	 */
	private function key(): string {
		$address = isset( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( (string) $_SERVER['REMOTE_ADDR'] ) ) : '';
		return 'linker_contact_' . md5( $address );
	}
}
