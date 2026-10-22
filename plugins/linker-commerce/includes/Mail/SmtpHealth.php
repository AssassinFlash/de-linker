<?php
/**
 * Staff-only web-context SMTP configuration and last-result readback (#297).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use WP_REST_Response;

/**
 * No configuration values, paths or credentials leave this endpoint.
 */
final class SmtpHealth {

	/**
	 * Sets up the read-only health boundary.
	 *
	 * @param InternalSmtp $smtp    Internal configuration status.
	 * @param SmtpOutcome  $outcome Last SMTP attempt.
	 */
	public function __construct( private readonly InternalSmtp $smtp = new InternalSmtp(), private readonly SmtpOutcome $outcome = new SmtpOutcome() ) {}

	/**
	 * Registers this module's sole staff health route.
	 */
	public function register_routes(): void {
		register_rest_route(
			'linker/v1',
			'/mail-health',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'read' ),
				'permission_callback' => array( $this, 'allowed' ),
			),
			true
		);
	}

	/**
	 * WooCommerce staff permission, enforced by the native REST server.
	 */
	public function allowed(): bool {
		return current_user_can( 'manage_woocommerce' );
	}

	/**
	 * Reads in the request's PHP context, rather than inferring from CLI results.
	 */
	public function read(): WP_REST_Response {
		$configured = $this->smtp->authenticated();
		return new WP_REST_Response(
			array(
				'smtp_configured'  => $configured,
				'label'            => $configured ? __( 'SMTP configured', 'linker-commerce' ) : __( 'SMTP not configured', 'linker-commerce' ),
				'last_outcome'     => $this->outcome->last(),
				'capacity_failure' => get_option( CapacityHealth::OPTION, null ),
			)
		);
	}
}
