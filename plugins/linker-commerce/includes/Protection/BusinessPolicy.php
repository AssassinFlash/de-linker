<?php
/**
 * Shared subject policy for actual business submissions from either door.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** Chat/resource writes do not consume the customer's business-message budget. */
final class BusinessPolicy {
	private const ACTIONS = array( 'contact', 'inquiry', 'genie_contact', 'genie_inquiry', 'conversation_mail' );

	/** Register the trusted PHP seams used by Commerce and Tools. */
	public function register(): void {
		add_filter( 'linker_commerce_public_business_limits', array( $this, 'limits' ), 10, 3 );
		add_filter( 'linker_commerce_public_business_carry', array( $this, 'carry' ), 10, 3 );
	}

	/**
	 * Initial operating recommendations accepted in #508, not customer facts.
	 * Account and browser counters preserve use across login/logout.
	 *
	 * @param Allowance[] $existing Earlier trusted policy.
	 * @param string      $action Native business action.
	 * @param Identity    $identity Server-derived subject.
	 * @return Allowance[]
	 */
	public function limits( array $existing, string $action, Identity $identity ): array {
		if ( ! in_array( $action, self::ACTIONS, true ) ) {
			return $existing;
		}
		$account = '' !== $identity->account;
		$limits  = array(
			new Allowance( 'business_browser_hour', $identity->browser, $account ? 20 : 10, HOUR_IN_SECONDS ),
			new Allowance( 'business_browser_day', $identity->browser, $account ? 100 : 20, DAY_IN_SECONDS ),
		);
		if ( $account ) {
			$limits[] = new Allowance( 'business_account_hour', $identity->account, 20, HOUR_IN_SECONDS );
			$limits[] = new Allowance( 'business_account_day', $identity->account, 100, DAY_IN_SECONDS );
		}
		$address    = isset( $_SERVER['REMOTE_ADDR'] ) && is_string( $_SERVER['REMOTE_ADDR'] ) ? sanitize_text_field( wp_unslash( $_SERVER['REMOTE_ADDR'] ) ) : '';
		$connection = hash_hmac( 'sha256', 'direct-connection|' . $address, wp_salt( 'auth' ) );
		$limits[]   = new Allowance( 'business_connection_hour', $connection, 100, HOUR_IN_SECONDS );
		return array_merge( $existing, $limits );
	}

	/**
	 * Import anonymous spend into the first account without adding it twice.
	 *
	 * @param list<array{source:Allowance,target:Allowance}> $existing Earlier links.
	 * @param string                                         $action Native business action.
	 * @param Identity                                       $identity Current server subject.
	 * @return list<array{source:Allowance,target:Allowance}>
	 */
	public function carry( array $existing, string $action, Identity $identity ): array {
		if ( ! in_array( $action, self::ACTIONS, true ) || '' === $identity->account ) {
			return $existing;
		}
		$existing[] = array(
			'source' => new Allowance( 'business_browser_hour', $identity->browser, 10, HOUR_IN_SECONDS ),
			'target' => new Allowance( 'business_account_hour', $identity->account, 20, HOUR_IN_SECONDS ),
		);
		$existing[] = array(
			'source' => new Allowance( 'business_browser_day', $identity->browser, 20, DAY_IN_SECONDS ),
			'target' => new Allowance( 'business_account_day', $identity->account, 100, DAY_IN_SECONDS ),
		);
		return $existing;
	}
}
