<?php
/** Native transaction provenance is bound to all frozen send arguments.
 *
 * @package Linker\Commerce
 */
declare(strict_types=1);
namespace Linker\Commerce\Mail;

/** Public headers/category/priority and a changed queued JSON cannot forge this witness. */
final class NativeOrigin {
	/**
	 * @param Message $message Actual call captured inside a native producer. */
	public static function seal( Message $message ): Message {
		if ( ! in_array( $message->origin['kind'] ?? '', array( 'transaction', 'security' ), true ) ) {
			return $message;}
		$origin         = $message->origin;
		$origin['seal'] = self::signature( $message );
		return new Message( $message->to, $message->subject, $message->body, $message->headers, $message->attachments, $message->critical, $message->category, $origin );
	}
	/**
	 * @param Message $message Immutable attempted native transaction. */
	public static function valid( Message $message ): bool {
		$seal = $message->origin['seal'] ?? null;
		return is_string( $seal ) && strlen( $seal ) === 64 && hash_equals( self::signature( $message ), $seal );
	}
	/**
	 * @param Message $message Frozen actual arguments, excluding the witness itself. */
	private static function signature( Message $message ): string {
		$origin = $message->origin;
		unset( $origin['seal'] );
		$data           = $message->to_array();
		$data['origin'] = $origin;
		$attachments    = array();
		foreach ( $message->attachments as$path ) {
			$digest = is_file( $path ) && is_readable( $path ) ? hash_file( 'sha256', $path ) : false;
			if ( ! is_string( $digest ) ) {
				return '';
			}$attachments[] = array( $path, $digest );}
		return hash_hmac( 'sha256', (string) wp_json_encode( array( $data, $attachments ) ), wp_salt( 'auth' ) );
	}
}
