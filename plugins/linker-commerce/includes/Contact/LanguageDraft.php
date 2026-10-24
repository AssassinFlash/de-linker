<?php
/**
 * Native Contact language navigation keeps only the current tab's unsent edit.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

/** No submission, session write, authorization field or customer CSS. */
final class LanguageDraft {


	/** Matches the existing Protection\FormRecovery five-minute retry lifetime. */
	public const LIFETIME_SECONDS = 300;

	/** Queue the head entry early; shortcode rendering reuses this native handle. */
	public static function enqueue(): void {
		$root = dirname( __DIR__, 2 );
		$file = $root . '/build/contact-language.asset.php';
		if ( ! is_file( $file ) ) {
			return;
		}
		$asset = require $file;
		wp_enqueue_script( 'linker-contact-language', plugins_url( 'build/contact-language.js', $root . '/linker-commerce.php' ), $asset['dependencies'], $asset['version'], false );
	}

	/**
	 * A public, opaque identity comparison; it grants no permission.
	 *
	 * @param bool                $recovered Native failed-POST values must take precedence.
	 * @param array<string,mixed> $context Current server-normalized public context.
	 */
	public static function attributes( bool $recovered, array $context ): string {
		$user    = get_current_user_id();
		$guest   = '';
		$session = 0 === $user && function_exists( 'WC' ) ? WC()->session : null;
		if ( $session instanceof \WC_Session_Handler && $session->has_session() ) {
			// Reuse an existing signed Woo session; never create one for navigation.
			$guest = (string) $session->get_customer_id();
		}
		// Guests without a native session remain isolated by the tab's sessionStorage.
		$owner = wp_hash( (string) $user . '|' . wp_get_session_token() . '|' . $guest, 'auth' );
		$type  = (string) ( $context['type'] ?? '' );
		$id    = (int) ( $context['id'] ?? 0 );
		$twin  = 0;
		if ( $id > 0 && 'term' === $type && function_exists( 'pll_get_term' ) ) {
			$twin = (int) pll_get_term( $id, 'en' );
		} elseif ( $id > 0 && function_exists( 'pll_get_post' ) ) {
			$twin = (int) pll_get_post( $id, 'en' );
		}
		$selection = is_array( $context['selection'] ?? null ) ? $context['selection'] : array();
		ksort( $selection );
		$encoded = wp_json_encode( $selection );
		$scope   = is_string( $encoded ) ? wp_hash( $type . '|' . (string) ( $twin > 0 ? $twin : $id ) . '|' . (string) ( $context['taxonomy'] ?? '' ) . '|' . $encoded, 'auth' ) : '';
		return ' data-linker-contact-draft-owner="' . esc_attr( $owner ) . '" data-linker-contact-draft-context="' . esc_attr( $scope ) . '" data-linker-contact-draft-lifetime="' . esc_attr( (string) ( self::LIFETIME_SECONDS * 1000 ) ) . '" data-linker-contact-recovered="' . ( $recovered ? '1' : '0' ) . '"';
	}

	/** Semantic fallback; the original form stays available if tab storage fails. */
	public static function notice(): string {
		// Translators: The other Contact language is German for English readers and English for German readers.
		$link = esc_html__( 'Open the German page in a new tab', 'linker-commerce' );
		return '<div class="linker-form-error" data-linker-contact-draft-error role="alert" hidden><p>' . esc_html__( 'Your entries could not be carried over to the other language version. They are still on this page.', 'linker-commerce' ) . '</p><a class="linker-form-primary" data-linker-contact-draft-new-tab target="_blank" rel="noopener noreferrer">' . $link . '</a></div>';
	}
}
