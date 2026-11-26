<?php
/**
 * Public contact channels shared by the storefront, Genie and planner.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** The two public desks and their click-to-chat link. */
final class ContactChannels {
	public const DIRECT_EMAIL  = 'chester@de-linker.com';
	public const GERMANY_PHONE = '+49 174 4276991';
	public const DIRECT_PHONE  = '+86 133 1289 2178';
	public const WHATSAPP_BASE = 'https://wa.me/8613312892178';

	/**
	 * Display or dial value for LiveCanvas contact rows.
	 *
	 * @param array<string,string>|string $attributes Shortcode attributes.
	 */
	public static function value( $attributes ): string {
		return match ( $attributes['channel'] ?? '' ) {
			'direct_email'  => self::DIRECT_EMAIL,
			'germany_phone' => self::GERMANY_PHONE,
			'direct_phone'  => self::DIRECT_PHONE,
			'germany_tel'   => str_replace( ' ', '', self::GERMANY_PHONE ),
			'direct_tel'    => str_replace( ' ', '', self::DIRECT_PHONE ),
			default         => '',
		};
	}

	/** Localized, editable message shown by WhatsApp when the customer opens it. */
	public static function message(): string {
		return __( 'Hello Linker team, I would like to discuss a solar storage inquiry.', 'linker-commerce' );
	}

	/**
	 * Public chat URL with a localized message.
	 *
	 * @param string $message Product or project message, or the general greeting.
	 */
	public static function url( string $message = '' ): string {
		return self::WHATSAPP_BASE . '?text=' . rawurlencode( '' === $message ? self::message() : $message );
	}

	/**
	 * Secondary link for a page or tool row.
	 *
	 * @param string $label   Visible label.
	 * @param string $message Contextual prefill.
	 * @param string $classes   Surface-specific styling.
	 */
	public static function link( string $label = 'WhatsApp', string $message = '', string $classes = '' ): string {
		return '<a class="' . esc_attr( trim( 'linker-whatsapp ' . $classes ) ) . '" href="' . esc_url( self::url( $message ) )
			. '" target="_blank" rel="noopener noreferrer"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.7 11.6a8.8 8.8 0 0 1-13.1 7.7L3 20.6l1.3-4.4a8.8 8.8 0 1 1 16.4-4.6Z"/><path d="m8.9 7.5 1.1 2.3-.8 1.2a8.5 8.5 0 0 0 3.8 3.5l1.1-1.3 2.4 1.2c-.2 1.4-1 2.1-2.3 2-3.6-.5-7.2-4.1-7.4-7.2 0-1.1.7-1.8 2.1-1.7Z"/></svg>'
			. esc_html( $label ) . '</a>';
	}

	/**
	 * Page-authored contact link.
	 *
	 * @param array<string,string>|string $attributes Shortcode attributes.
	 */
	public static function shortcode( $attributes ): string {
		return self::link( classes: 'outline' === ( $attributes['style'] ?? '' ) ? 'linker-whatsapp-outline' : '' );
	}
}
