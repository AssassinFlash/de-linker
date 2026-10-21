<?php
/**
 * Server-selected public resource dimensions (#508 decision 6324114050).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Protection;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;

/** Resource writes never spend the separate direct-inquiry business allowance. */
final class ResourcePolicy {
	/**
	 * Map only actual mutating resource routes. Reads consume no turn allowance.
	 *
	 * @param string $route Native route.
	 * @param string $method Native method.
	 * @param bool   $select Existing conversation selection.
	 */
	public static function action( string $route, string $method, bool $select = false ): string {
		if ( ! in_array( $method, array( 'POST', 'DELETE' ), true ) ) {
			return '';
		}
		return match ( true ) {
			'/linker-ai/v1/genie/turn' === $route => 'genie',
			'/linker-ai/v1/genie/contact' === $route => 'genie_contact',
			'/linker-ai/v1/genie/inquiry' === $route => 'genie_inquiry',
			self::matches( '#\A/linker-ai/v1/genie/conversations/\d+/email\z#', $route ) => 'conversation_mail',
			self::matches( '#\A/linker-ai/v1/genie/turn/\d+/vote\z#', $route ) => 'vote',
			'/linker-ai/v1/genie/conversations' === $route => self::conversation_action( $select ),
			self::matches( '#\A/linker-ai/v1/genie/conversations/\d+\z#', $route ) => 'conversation_write',
			self::matches( '#\A/linker-ai/v1/engine/design/(residential|commercial)\z#', $route ) => 'design',
			self::matches( '#\A/linker-ai/v1/engine/roof/(outline|pack)\z#', $route ) => 'roof',
			'/linker-ai/v1/engine/report/pdf' === $route => 'report_pdf',
			'/linker/v1/solutions' === $route => 'solution_save',
			default => '',
		};
	}

	/**
	 * Match a server-owned route pattern.
	 *
	 * @param string $pattern Fixed route regex.
	 * @param string $route Native route.
	 */
	private static function matches( string $pattern, string $route ): bool {
		return 1 === preg_match( $pattern, $route );
	}

	/**
	 * Existing history selection has no model or creation cost.
	 *
	 * @param bool $select Existing native conversation ID.
	 */
	private static function conversation_action( bool $select ): string {
		if ( $select ) {
			return 'conversation_write';
		}
		return 'conversation_create';
	}

	/**
	 * Atomic dimensions and account carry, using the browser identity across login.
	 *
	 * @param string   $action Server action.
	 * @param Identity $identity Current private identity.
	 * @param int      $files Files in this turn, checked before decode.
	 * @return array{limits:Allowance[],carry:list<array{source:Allowance,target:Allowance}>}
	 */
	public static function plan( string $action, Identity $identity, int $files = 0 ): array {
		$limits  = array();
		$carry   = array();
		$account = '' !== $identity->account;
		$add     = static function ( string $name, int $anonymous, int $signed, int $window, int $units = 1 ) use ( $identity, $account, &$limits, &$carry ): void {
			$capacity = $account ? $signed : $anonymous;
			$limits[] = new Allowance( $name, $identity->browser, $capacity, $window, $units );
			if ( $account ) {
				$target   = new Allowance( $name, $identity->account, $signed, $window, $units );
				$limits[] = $target;
				if ( $window > 0 ) {
					$carry[] = array(
						'source' => new Allowance( $name, $identity->browser, $anonymous, $window ),
						'target' => $target,
					);
				}
			}
		};
		if ( in_array( $action, array( 'genie_contact', 'genie_inquiry', 'conversation_mail' ), true ) ) {
			/**
			 * Commerce owns one cross-entrance business policy.
			 *
			 * @since 0.1.0
			 */
			$limits = apply_filters( 'linker_commerce_public_business_limits', array(), $action, $identity ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce contract.
			/**
			 * Account carry is the same shared policy.
			 *
			 * @since 0.1.0
			 */
			$carry = apply_filters( 'linker_commerce_public_business_carry', array(), $action, $identity ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Commerce contract.
		} elseif ( 'genie' === $action ) {
			$add( 'genie_day', 30, 120, DAY_IN_SECONDS );
			$add( 'genie_burst', 10, 30, 10 * MINUTE_IN_SECONDS );
			$add( 'genie_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'genie_site_day', 'site', 500, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'genie_site_busy', 'site', 2, 0 );
			if ( $files > 0 ) {
				$add( 'genie_files_day', 10, 40, DAY_IN_SECONDS, $files );
				$limits[] = new Allowance( 'genie_site_files_day', 'site', 100, DAY_IN_SECONDS, $files );
			}
		} elseif ( in_array( $action, array( 'design', 'roof' ), true ) ) {
			// Roof and sizing share this allowance: changing the entrance is
			// not a new budget. #508 approved 30/120 recomputations per hour.
			$add( 'design_hour', 30, 120, HOUR_IN_SECONDS );
			$add( 'design_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'design_site_busy', 'site', 4, 0 );
		} elseif ( 'report_pdf' === $action ) {
			$add( 'report_day', 10, 10, DAY_IN_SECONDS );
			$add( 'design_busy', 1, 1, 0 );
			$limits[] = new Allowance( 'report_site_day', 'site', 100, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'design_site_busy', 'site', 4, 0 );
		} else {
			// Recommended storage-only ceiling, #521: 4 mutations per maximum
			// signed-in turn (120/day), rounded to 500. No model work or mail.
			$add( 'tool_write_day', 500, 500, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'tool_write_site_day', 'site', 2000, DAY_IN_SECONDS );
		}
		return array(
			'limits' => $limits,
			'carry'  => $carry,
		);
	}
}
