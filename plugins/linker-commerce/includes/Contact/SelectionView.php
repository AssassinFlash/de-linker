<?php
/**
 * Semantic selection context shared by the contact form and its team record.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use WC_Order;

/** Layout comes from the existing WindPress contact surface; data stays separate from message. */
final class SelectionView {
	/** Register native Woo team/admin consumers, not a second contact submission path. */
	public function register(): void {
		add_action( 'woocommerce_admin_order_data_after_order_details', array( $this, 'admin' ) );
		add_action( 'woocommerce_email_order_meta', array( $this, 'email' ), 10, 4 );
		add_filter( 'woocommerce_privacy_remove_order_personal_data_meta', array( $this, 'erase' ) );
	}

	/**
	 * The optional context is still useful without a script; unchecked visibly excludes it.
	 *
	 * @param array<string,mixed> $context Normalized public context.
	 * @param string              $raw Original field for a retry if its source is no longer available.
	 * @param bool                $included Original customer inclusion choice.
	 */
	public static function form( array $context, string $raw, bool $included ): string {
		if ( array() === $context && '' === $raw && $included ) {
			return '';
		}
		if ( array() !== $context ) {
			$raw = (string) wp_json_encode(
				array(
					'source'    => $context['source'],
					'selection' => $context['selection'],
				)
			);
		}
		$removed = array() === $context && '' === $raw && ! $included;
		$html    = '<fieldset class="linker-contact-selection' . ( $removed ? ' linker-contact-selection--excluded' : '' ) . '"><legend>' . esc_html( self::heading( $context ) ) . '</legend>';
		$html   .= '<input type="hidden" name="' . SelectionContext::INCLUDE_FIELD . '" value="0" />';
		if ( $removed ) {
			return $html . '<p class="linker-contact-selection__excluded" role="status">' . esc_html__( 'These details will not be sent.', 'linker-commerce' ) . '</p></fieldset>';
		}
		$html .= '<label class="linker-contact-selection__toggle"><input type="checkbox" name="' . SelectionContext::FIELD . '" value="' . esc_attr( $raw ) . '"' . ( $included ? ' checked' : '' ) . ' /><span>' . esc_html__( 'Include these details with my message', 'linker-commerce' ) . '</span></label>';
		$html .= '<div class="linker-contact-selection__summary">';
		$html .= array() !== $context ? self::summary( $context ) : '<p role="status">' . esc_html__( 'These details could not be loaded. To send your message without them, uncheck “Include these details with my message”.', 'linker-commerce' ) . '</p>';
		$html .= '</div><p class="linker-contact-selection__excluded" role="status">' . esc_html__( 'These details will not be sent.', 'linker-commerce' ) . '</p>';
		return $html . '</fieldset>';
	}

	/**
	 * Describe the actual public source/request without calling an ordinary page a product.
	 *
	 * @param array<string,mixed> $context Normalized public data or a compatible stored record.
	 */
	private static function heading( array $context ): string {
		$selection = (array) ( $context['selection'] ?? array() );
		$platform  = $selection['platform'] ?? null;
		if ( 'product' === ( $context['type'] ?? null ) || ( is_string( $platform ) && '' !== $platform ) ) {
			return __( 'Product selection', 'linker-commerce' );
		}
		if ( array() !== $context && array() === $selection ) {
			return __( 'Related page', 'linker-commerce' );
		}
		return __( 'Related details', 'linker-commerce' );
	}

	/**
	 * Current public labels plus escaped customer search text.
	 *
	 * @param array<string,mixed> $context Normalized public data stored with the request.
	 */
	public static function summary( array $context ): string {
		$source = (string) ( $context['url'] ?? '' );
		$html   = '<p><a href="' . esc_url( $source ) . '">' . esc_html( (string) ( $context['title'] ?? '' ) ) . '</a></p><dl>';
		foreach ( (array) ( $context['selection'] ?? array() ) as $key => $value ) {
			$html .= '<div><dt>' . esc_html( self::label( (string) $key ) ) . '</dt><dd>' . esc_html( self::value( (string) $key, (string) $value ) ) . '</dd></div>';
		}
		return $html . '</dl>';
	}

	/**
	 * Labels match the archive's native filter vocabulary.
	 *
	 * @param string $key Known selection key.
	 */
	private static function label( string $key ): string {
		return match ( $key ) {
			'q' => __( 'Search', 'linker-commerce' ),
			'platform' => __( 'Product', 'linker-commerce' ),
			'document' => __( 'Documents', 'linker-commerce' ),
			'brand' => __( 'Brand', 'linker-commerce' ),
			'application' => __( 'Application', 'linker-commerce' ),
			'phase' => __( 'Phase', 'linker-commerce' ),
			'power' => __( 'Power', 'linker-commerce' ),
			'kw_min' => __( 'Minimum power (kW)', 'linker-commerce' ),
			'kw_max' => __( 'Maximum power (kW)', 'linker-commerce' ),
			'kwh_min' => __( 'Minimum capacity (kWh)', 'linker-commerce' ),
			'kwh_max' => __( 'Maximum capacity (kWh)', 'linker-commerce' ),
			'sort' => __( 'Sort products', 'linker-commerce' ),
			default => $key,
		};
	}

	/**
	 * Display names are server-owned; an unrecognized filter remains a customer selection.
	 *
	 * @param string $key Known selection key.
	 * @param string $value Sanitized selected value.
	 */
	private static function value( string $key, string $value ): string {
		if ( 'document' === $key && 'Datasheets & certificates' === $value ) {
			return __( 'Datasheets & certificates', 'linker-commerce' );
		}
		if ( 'sort' === $key ) {
			return match ( $value ) {
				'newest' => __( 'Newest first', 'linker-commerce' ),
				'name' => __( 'Name A-Z', 'linker-commerce' ),
				'power-desc' => __( 'Power high-low', 'linker-commerce' ),
				'power-asc' => __( 'Power low-high', 'linker-commerce' ),
				default => __( 'Recommended', 'linker-commerce' ),
			};
		}
		if ( in_array( $key, array( 'application', 'phase', 'power' ), true ) ) {
			$labels = ( new \Linker\Commerce\Storefront\ProductFilters() )->value_labels();
			if ( isset( $labels[ $key ][ $value ] ) ) {
				return $labels[ $key ][ $value ];
			}
		}

		$taxonomies = match ( $key ) {
			'brand' => array( 'product_brand', 'pa_brand' ),
			'application' => array( 'pa_application' ),
			'phase' => array( 'pa_phase' ),
			default => array(),
		};
		foreach ( $taxonomies as $taxonomy ) {
			$term = get_term_by( 'slug', $value, $taxonomy );
			if ( $term instanceof \WP_Term ) {
				return $term->name;
			}
		}
		return $value;
	}

	/**
	 * Native order screen, available for both classic and HPOS storage.
	 *
	 * @param WC_Order $order Native inquiry.
	 */
	public function admin( WC_Order $order ): void {
		$context = SelectionContext::stored( $order->get_meta( SelectionContext::META ) );
		if ( array() !== $context ) {
			echo '<section class="linker-contact-selection-record"><h3>' . esc_html( self::heading( $context ) ) . '</h3>' . wp_kses_post( self::summary( $context ) ) . '</section>';
		}
	}

	/**
	 * Context accompanies only the team notification, never an unverified destination receipt.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param bool     $sent_to_admin Team letter.
	 * @param bool     $plain_text Plain-text format.
	 * @param mixed    $email Current email instance.
	 */
	public function email( WC_Order $order, bool $sent_to_admin, bool $plain_text, mixed $email ): void {
		unset( $email );
		if ( ! $sent_to_admin ) {
			return;
		}
		$context = SelectionContext::stored( $order->get_meta( SelectionContext::META ) );
		if ( array() === $context ) {
			return;
		}
		if ( $plain_text ) {

			$lines = array( self::heading( $context ), (string) ( $context['title'] ?? '' ), (string) ( $context['url'] ?? '' ) );
			foreach ( (array) ( $context['selection'] ?? array() ) as $key => $value ) {
				$lines[] = self::label( (string) $key ) . ': ' . self::value( (string) $key, (string) $value );
			}
			echo implode( "\n", $lines ) . "\n"; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- native plaintext email; HTML escaping changes the message bytes.
			return;
		}
		echo '<h2>' . esc_html( self::heading( $context ) ) . '</h2>' . wp_kses_post( self::summary( $context ) );
	}

	/**
	 * Search text is customer input and follows the order's native erasure.
	 *
	 * @param array<string,string> $fields Native meta erasure keys.
	 * @return array<string,string>
	 */
	public function erase( array $fields ): array {
		$fields[ SelectionContext::META ] = 'text';
		return $fields;
	}
}
