<?php
/**
 * Server-owned mail priority contexts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

use Linker\Commerce\Proforma\Emails\ProformaIssuedEmail;
use Linker\Commerce\Registration\Emails\CustomerApprovalEmail;
use WC_Email;

/**
 * No header, model decision or public input can enter this context.
 */
final class Producer {

	/**
	 * Server-owned nested producer context, restored after every call.
	 *
	 * @var bool
	 */
	private static bool $critical = false;
	/**
	 * Native WordPress password-reset calls awaiting wp_mail.
	 *
	 * @var array<string, true>
	 */
	private static array $resets = array();

	/**
	 * Run a trusted critical producer.
	 *
	 * @param  callable $send Native producer's send operation.
	 * @return mixed Native result.
	 */
	public static function critical( callable $send ): mixed {
		$previous       = self::$critical;
		self::$critical = true;
		try {
			return $send();
		} finally {
			self::$critical = $previous;
		}
	}

	/**
	 * Wrap explicitly critical native WooCommerce producers.
	 *
	 * @param  callable $callback WooCommerce's selected callback.
	 * @param  WC_Email $email    Actual server-side email instance.
	 * @return callable Wrapped callback only for the explicitly critical native classes.
	 */
	public function woocommerce( callable $callback, WC_Email $email ): callable {
		$critical = $email instanceof CustomerApprovalEmail || $email instanceof ProformaIssuedEmail || $email instanceof \WC_Email_Customer_Reset_Password || $email instanceof \WC_Email_Admin_Payment_Gateway_Enabled;
		return $critical ? static fn ( ...$args ) => self::critical( static fn () => $callback( ...$args ) ) : $callback;
	}

	/**
	 * Remember one native WordPress reset message.
	 *
	 * @param  array<string, mixed> $email Native retrieve_password() notification.
	 * @return array<string, mixed> Unchanged notification.
	 */
	public function password_reset( array $email ): array {
		self::$resets[ self::signature( $email ) ] = true;
		return $email;
	}

	/**
	 * Read and consume the current producer priority.
	 *
	 * @param array<string, mixed> $atts Actual native wp_mail arguments.
	 */
	public static function priority( array $atts ): bool {
		if ( array() === self::$resets ) {
			return self::$critical;
		}
		$key   = self::signature( $atts );
		$reset = isset( self::$resets[ $key ] );
		unset( self::$resets[ $key ] );
		return self::$critical || $reset;
	}

	/**
	 * Bind the native reset producer to its exact next mail.
	 *
	 * @param array<string, mixed> $atts Native mail arguments.
	 */
	private static function signature( array $atts ): string {
		$to = $atts['to'] ?? '';
		$to = is_array( $to ) ? $to : explode( ',', is_string( $to ) ? $to : '' );
		return hash( 'sha256', (string) wp_json_encode( array( array_values( array_map( 'trim', $to ) ), $atts['subject'] ?? '', $atts['message'] ?? '' ) ) );
	}
}
