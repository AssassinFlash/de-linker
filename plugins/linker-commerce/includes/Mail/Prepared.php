<?php
/**
 * Native-template preview and immutable critical notification handoff.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Mail;

/** Same native capture seam as NewInquiryEmail; never a model or SMTP call. */
final class Prepared {
	/** Immutable preview for this one trusted native producer.
	 *
	 * @var Message|null
	 */
	private static ?Message $message = null;
	/** True only while native templates render without transport.
	 *
	 * @var bool
	 */
	private static bool $preview = false;

	/** Native observers can distinguish a template preview from a real handoff. */
	public static function is_preview(): bool {
		return self::$preview;
	}

	/**
	 * Capture the actual final native template, locale, routing and sender filters.
	 * A preview is explicitly not a successful delivery and has no email log row.
	 *
	 * @param callable $render Native email trigger only.
	 */
	public static function capture( callable $render ): ?Message {
		$message = null;
		$capture = static function ( $pre, array $atts ) use ( &$message ): bool {
			if ( null === $pre ) {
				$message = Message::from_wp_mail( $atts );
			}
			return false;
		};
		$logging = static fn (): bool => false;
		add_filter( 'pre_wp_mail', $capture, 9, 2 );
		add_filter( 'woocommerce_email_log_enabled', $logging );
		$previous      = self::$preview;
		self::$preview = true;
		try {
			$render();
		} finally {
			self::$preview = $previous;
			remove_filter( 'pre_wp_mail', $capture, 9 );
			remove_filter( 'woocommerce_email_log_enabled', $logging );
		}
		return $message;
	}

	/**
	 * Deliver exactly the notification whose complete encoded bytes were reserved.
	 *
	 * @param Message  $message Frozen native message.
	 * @param callable $send The same native email producer after its business write.
	 * @return mixed Native result.
	 */
	public static function within( Message $message, callable $send ): mixed {
		$previous      = self::$message;
		self::$message = $message;
		try {
			return $send();
		} finally {
			self::$message = $previous;
		}
	}

	/** A trusted in-process producer, never a request header or field. */
	public static function current(): ?Message {
		return self::$message;
	}
}
