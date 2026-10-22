<?php
/**
 * Freeze native registration mail before creation, with two typed template holes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Mail\LocaleSwitch;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\Producer;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use WP_Error;
use WP_User;

/**
 * Arbitrary settings/filters are captured once; customer prose is never replaced.
 */
final class RegistrationMessage {

	/**
	 * Capture the actual configured native notification without user/VIES/mail writes.
	 *
	 * @param  NewCustomerEmail|RegistrationReceivedEmail $email  Native producer.
	 * @param  WP_User                                    $user   Password-free prospective user.
	 * @param  array<string,string>                       $values Native business values.
	 * @param  string                                     $locale Native customer locale.
	 * @return array<string,mixed>|WP_Error Frozen native message and complete JSON bound.
	 */
	public static function prepare( NewCustomerEmail|RegistrationReceivedEmail $email, WP_User $user, array $values, string $locale ): array|WP_Error {
		if ( ! $email->is_enabled() ) {
			return array(
				'state'     => 'skipped',
				'reason'    => 'disabled',
				'max_bytes' => 1,
			);
		}
		$nonce   = bin2hex( random_bytes( 32 ) );
		$tokens  = array(
			'account_url' => 'https://registration.invalid/' . $nonce,
			'vat'         => 'linker_registration_vat_' . $nonce,
		);
		$message = Producer::critical(
			static fn (): ?Message => $email instanceof NewCustomerEmail ? $email->preview( $user, $values, $tokens ) : $email->preview( $user, $locale )
		);
		if ( ! $message instanceof Message || array() === $message->to ) {
			return self::problem();
		}
		$plan = array(
			'state'       => 'pending',
			'message'     => $message->to_array(),
			'parts'       => array( array( 'text' => $message->body ) ),
			'account_url' => AccountsAdmin::url(),
			'vat_labels'  => array(),
		);
		if ( $email instanceof NewCustomerEmail ) {
			$body = $message->body;
			if ( ! self::typed_holes( $body, $tokens ) ) {
				return self::problem();
			}
			$outside = $message->to_array();
			unset( $outside['body'] );
			$positions = array();
			foreach ( $tokens as $field => $token ) {
				if ( 1 !== substr_count( $body, $token ) || str_contains( (string) wp_json_encode( $outside ), $token ) ) {
					return self::problem();
				}
				$position = strpos( $body, $token );
				if ( false === $position || ( 'account_url' === $field && 'href="' !== substr( $body, $position - 6, 6 ) ) || ( 'vat' === $field && ( '>' !== substr( $body, $position - 1, 1 ) || '<' !== substr( $body, $position + strlen( $token ), 1 ) ) ) ) {
					return self::problem();
				}
				$positions[ $position ] = array(
					'field'  => $field,
					'length' => strlen( $token ),
				);
			}
			ksort( $positions );
			$plan['parts'] = array();
			$offset        = 0;
			foreach ( $positions as $position => $hole ) {
				$plan['parts'][] = array( 'text' => substr( $body, $offset, $position - $offset ) );
				$plan['parts'][] = array( 'field' => $hole['field'] );
				$offset          = $position + $hole['length'];
			}
			$plan['parts'][] = array( 'text' => substr( $body, $offset ) );
			// Tokens are discarded now. Only typed structural holes survive in storage.
			$plan['message']['body'] = '';
			$switch                  = new LocaleSwitch();
			$switch->to( LocaleSwitch::site_default() );
			try {
				foreach ( array( '', VatProfile::VALID, VatProfile::INVALID, VatProfile::UNVERIFIED, VatProfile::NONE ) as $status ) {
					$plan['vat_labels'][ $status ] = esc_html( VatProfile::label( $status ) );
				}
			} finally {
				$switch->back();
			}
		}
		// The only future URL variation is a positive native PHP integer: at most
		// strlen(PHP_INT_MAX) decimal digits. VAT is one of these frozen labels.
		$maximum  = 0;
		$statuses = array_keys( $plan['vat_labels'] );
		foreach ( array() === $statuses ? array( '' ) : $statuses as $status ) {
			$built = self::build( $plan, PHP_INT_MAX, (string) $status );
			if ( null === $built ) {
				return self::problem();
			}
			$encoded = wp_json_encode( $built->to_array() );
			if ( ! is_string( $encoded ) ) {
				return self::problem();
			}
			$maximum = max( $maximum, strlen( $encoded ) );
		}
		// The bounded native pending source stores one body copy, not a second queue.
		$plan['message']['body'] = '';
		$plan['reservation']     = str_repeat( 'f', 64 );
		$plan['max_bytes']       = PHP_INT_MAX;
		$source                  = wp_json_encode( $plan );
		if ( ! is_string( $source ) ) {
			return self::problem();
		}
		$plan['max_bytes'] = max( $maximum, strlen( $source ) );
		unset( $plan['reservation'] );
		return $plan;
	}

	/**
	 * Materialize only the two typed template fields; no re-render or global replace.
	 *
	 * @param array<string,mixed> $plan Frozen native producer.
	 * @param int                 $id   Existing native user ID.
	 * @param string              $vat  Native verdict.
	 */
	public static function complete( array $plan, int $id, string $vat ): ?Message {
		$message = self::build( $plan, $id, $vat );
		return null !== $message && strlen( (string) wp_json_encode( $message->to_array() ) ) <= (int) ( $plan['max_bytes'] ?? 0 ) ? $message : null;
	}

	/**
	 * Complete JSON is checked after structural assembly, including headers/routing.
	 *
	 * @param array<string,mixed> $plan Frozen native message.
	 * @param int                 $id   Native ID.
	 * @param string              $vat  Native VAT status.
	 */
	private static function build( array $plan, int $id, string $vat ): ?Message {
		if ( $id < 1 || ! is_array( $plan['message'] ?? null ) || ! is_array( $plan['parts'] ?? null ) ) {
			return null;
		}
		$body = '';
		foreach ( $plan['parts'] as $part ) {
			if ( isset( $part['text'] ) && is_string( $part['text'] ) ) {
				$body .= $part['text'];
			} elseif ( 'account_url' === ( $part['field'] ?? '' ) ) {
				$body .= esc_url( add_query_arg( 'focus', $id, $plan['account_url'] ) );
			} elseif ( 'vat' === ( $part['field'] ?? '' ) ) {
				$body .= $plan['vat_labels'][ $vat ] ?? $plan['vat_labels'][''] ?? '';
			} else {
				return null;
			}
		}
		$data         = $plan['message'];
		$data['body'] = $body;
		return Message::from_array( $data );
	}

	/**
	 * The native template must preserve a real anchor href and VAT table text.
	 *
	 * @param string               $body   Native final HTML, after all filters.
	 * @param array<string,string> $tokens Private preview markers.
	 */
	private static function typed_holes( string $body, array $tokens ): bool {
		$previous = libxml_use_internal_errors( true );
		try {
			$document = new \DOMDocument();
			if ( ! $document->loadHTML( '<?xml encoding="utf-8" ?>' . $body, LIBXML_NONET ) ) {
				return false;
			}
			$xpath = new \DOMXPath( $document );
			$url   = $xpath->query( '//a[@href="' . $tokens['account_url'] . '"]' );
			$vat   = $xpath->query( '//td[text()="' . $tokens['vat'] . '"]' );
			return false !== $url && 1 === $url->length && false !== $vat && 1 === $vat->length;
		} finally {
			libxml_clear_errors();
			libxml_use_internal_errors( $previous );
		}
	}

	/**
	 * A template override that cannot preserve typed holes cannot be pre-reserved.
	 */
	private static function problem(): WP_Error {
		return new WP_Error( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
	}
}
