<?php
/**
 * Server-owned mail priority contexts.
 *
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
	 *
 * @var bool
	 */
	private static bool $critical = false;
	/**
 * @var array<string,mixed> Native producer identity, never a public header. */
	private static array $origin = array();
	/**
	 * Native WordPress password-reset calls awaiting wp_mail.
	 *
	 *
 * @var array<string, string>
	 */
	private static array $resets = array();

	/**
	 * Run a trusted critical producer.
	 *
	 *
 * @param  callable $send Native producer's send operation.
	 *
 * @return mixed Native result.
	 */
	public static function critical( callable $send ): mixed {
		$previous_origin = self::$origin;
		self::$origin = array( 'kind' => 'security', 'producer' => self::$origin['producer'] ?? 'health_alert' );
		$previous       = self::$critical;
		self::$critical = true;
		try {
			return $send();
		} finally {
			self::$critical = $previous;
			self::$origin = $previous_origin;
		}
	}

	/**
	 * Wrap explicitly critical native WooCommerce producers.
	 *
	 *
 * @param  callable $callback WooCommerce's selected callback.
	 *
 * @param  WC_Email $email    Actual server-side email instance.
	 *
 * @return callable Wrapped callback only for the explicitly critical native classes.
	 */
	public function woocommerce( callable $callback, WC_Email $email ): callable {
		$critical = $email instanceof CustomerApprovalEmail || $email instanceof ProformaIssuedEmail || $email instanceof \WC_Email_Customer_Reset_Password || $email instanceof \WC_Email_Admin_Payment_Gateway_Enabled;
		return static function ( ...$args ) use ( $critical, $callback, $email ) {
			$previous = self::$origin;
			$content = $email instanceof \Linker\Commerce\Inquiry\Emails\NewInquiryEmail || $email instanceof \Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail || $email instanceof \Linker\Commerce\Genie\ConversationEmail;
			self::$origin = array( 'kind' => $content ? 'unclassified' : 'transaction', 'producer' => $email->id );
			try { return $critical ? self::critical( static fn () => $callback( ...$args ) ) : $callback( ...$args ); }
			finally { self::$origin = $previous; }
		};
	}

	/**
	 * Remember one native WordPress reset message.
	 *
	 *
 * @param  array<string, mixed> $email Native retrieve_password() notification.
	 *
 * @return array<string, mixed> Unchanged notification.
	 */
	public function password_reset( array $email ): array {
		self::$resets[ self::signature( $email ) ] = 'password_reset';
		return $email;
	}

	/** Core profile notifications substitute placeholders after their native filter.
	 * @param array<string,mixed> $email Native notification template.
	 * @param array<string,mixed> $user Authoritative original account.
	 * @param array<string,mixed> $updated Native updated data.
	 * @return array<string,mixed> Original native template.
	 */
	public function account_change( array $email, array $user, array $updated ): array {
		$final = $email;
		$site = wp_specialchars_decode( (string)get_option( 'blogname' ), ENT_QUOTES );
		$text = (string)( $email['message'] ?? '' );
		foreach ( array( '###USERNAME###'=>(string)( $user['user_login'] ?? '' ), '###ADMIN_EMAIL###'=>(string)get_option( 'admin_email' ), '###NEW_EMAIL###'=>(string)( $updated['user_email'] ?? '' ), '###EMAIL###'=>(string)( $user['user_email'] ?? '' ), '###SITENAME###'=>$site, '###SITEURL###'=>home_url() ) as $key=>$value ) { $text = str_replace( $key, $value, $text ); }
		$final['message'] = $text;
		$final['subject'] = sprintf( (string)( $email['subject'] ?? '' ), $site );
		self::$resets[ self::signature( $final ) ] = 'account_change';
		return $email;
	}

	/**
	 * Read and consume the current producer priority.
	 *
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
 * @param array<string,mixed> $atts Exact native call.
 * @return array<string,mixed> */
	public static function origin( array $atts ): array {
		return isset( self::$resets[ self::signature( $atts ) ] ) ? array( 'kind' => 'security', 'producer' => self::$resets[ self::signature( $atts ) ] ) : self::$origin;
	}

	/**
	 * Bind the native reset producer to its exact next mail.
	 *
	 *
 * @param array<string, mixed> $atts Native mail arguments.
	 */
	private static function signature( array $atts ): string {
		$to = $atts['to'] ?? '';
		$to = is_array( $to ) ? $to : explode( ',', is_string( $to ) ? $to : '' );
		return hash( 'sha256', (string) wp_json_encode( array( array_values( array_map( 'trim', $to ) ), $atts['subject'] ?? '', $atts['message'] ?? '' ) ) );
	}
}
