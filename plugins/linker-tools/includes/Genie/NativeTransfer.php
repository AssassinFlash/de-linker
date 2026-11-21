<?php
/**
 * A confirmed Genie card and its original Woo inquiry.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Protection\Business;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Turnstile;
use WC_Order;
use WP_Error;
use WP_REST_Request;

/** The conversation owner is resolved by the native route before this handoff. */
final class NativeTransfer {
	/**
	 * Identifies the exact stored turn, including conversations at the history limit.
	 *
	 * @param int                            $conversation Owned conversation.
	 * @param array<string, mixed>           $thread Read from that conversation.
	 * @param array<int,array<string,mixed>> $draft  Contact handoff’s current draft lines.
	 */
	public static function source( int $conversation, array $thread, array $draft = array() ): string {
		$turn     = $thread['operation_id'] ?? hash( 'sha256', (string) wp_json_encode( array( $thread['messages'], $thread['stream'] ) ) );
		$revision = $conversation . ':' . count( $thread['messages'] ) . ':' . $turn;
		return array() === $draft ? $revision : $revision . ':' . hash( 'sha256', (string) wp_json_encode( $draft ) );
	}

	/**
	 * Submit or recover one intent. Record the history note under the same lock
	 * as the Woo record so two tabs publish one card.
	 *
	 * @param string                      $action Native route's action.
	 * @param int                         $conversation Owned conversation.
	 * @param string                      $meta Conversation history meta key.
	 * @param array<string,mixed>         $note Native note fields, including owner, recipient and message count.
	 * @param array<string,mixed>         $input Original customer selections and values.
	 * @param WP_REST_Request             $request Current submit.
	 * @param callable():mixed            $write Woo consumer.
	 * @param (callable():?WP_Error)|null $preflight Check a new write against the current draft.
	 * @return WC_Order|WP_Error
	 */
	public static function send( string $action, int $conversation, string $meta, array $note, array $input, WP_REST_Request $request, callable $write, ?callable $preflight = null ): WC_Order|WP_Error {
		if ( ! class_exists( Business::class ) ) {
			return self::unavailable( $action );
		}
		$source = $request->get_param( 'source' );
		if ( ! is_string( $source ) || ! str_starts_with( $source, $conversation . ':' ) ) {
			return self::stale( $action );
		}
		// This reference locates a retry. The private owner and exact input are
		// independently matched on the native Woo record before returning it.
		$hex   = hash_hmac( 'sha256', $action . '|' . $source . '|' . $note['user_id'] . '|' . strtolower( $note['email'] ), wp_salt( 'nonce' ) );
		$id    = substr( $hex, 0, 8 ) . '-' . substr( $hex, 8, 4 ) . '-4' . substr( $hex, 13, 3 ) . '-a' . substr( $hex, 17, 3 ) . '-' . substr( $hex, 20, 12 );
		$owner = new Identity( hash_hmac( 'sha256', 'owned-genie-conversation|' . $conversation, wp_salt( 'auth' ) ), Identity::account( get_current_user_id() ) );
		return Business::write_once(
			$id,
			$action,
			array(
				'source' => $source,
				'email'  => $note['email'],
				'input'  => $input,
			),
			static function () use ( $write, $action ) {
				$sent = $write();
				if ( is_wp_error( $sent ) ) {
					return $sent;
				}
				$order = is_array( $sent ) && ! empty( $sent['order'] ) ? wc_get_order( (int) $sent['order'] ) : false;
				return $order instanceof WC_Order ? $order : self::unavailable( $action );
			},
			static function () use ( $preflight, $request, $action, $note, $source ) {
				if ( $note['source'] !== $source ) {
					return self::stale( $action );
				}
				if ( null !== $preflight ) {
					$failure = $preflight();
					if ( is_wp_error( $failure ) ) {
						return $failure;
					}
				}
				return Turnstile::check( $action, array( 'cf-turnstile-response' => $request->get_param( 'cf-turnstile-response' ) ) );
			},
			$owner,
			static function ( WC_Order $order ) use ( $conversation, $meta, $note, $source, $action ) {
				foreach ( get_post_meta( $conversation, $meta, false ) as $previous ) {
					if ( is_array( $previous ) && $order->get_id() === (int) ( $previous['order'] ?? 0 ) ) {
						return true;
					}
				}
				$note['source']   = $source;
				$note['messages'] = (int) explode( ':', $source )[1];
				$history          = $note + array(
					'at'      => time(),
					'order'   => $order->get_id(),
					'receipt' => InquiryRequest::receipt_sent( $order ),
				);
				return false !== add_post_meta( $conversation, $meta, wp_slash( $history ) ) ? true : self::unavailable( $action );
			}
		);
	}

	/**
	 * A newer turn or draft needs a fresh confirmation.
	 *
	 * @param string $action Native transfer action.
	 */
	private static function stale( string $action ): WP_Error {
		return new WP_Error( 'genie_contact' === $action ? 'linker_genie_contact_retry' : 'linker_genie_inquiry_changed', '', array( 'status' => 409 ) );
	}

	/**
	 * Native card can safely retry its original intent.
	 *
	 * @param string $action Native transfer action.
	 */
	private static function unavailable( string $action ): WP_Error {
		return new WP_Error( 'linker_' . $action . '_unavailable', '', array( 'status' => 503 ) );
	}
}
