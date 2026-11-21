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
		// WP_REST_Server matches registered paths with the i modifier.
		$route = strtolower( $route );
		return match ( true ) {
			'/linker-ai/v1/genie/turn' === $route => 'genie',
			'/linker-ai/v1/genie/solution' === $route => 'solution_save',
			'/linker-ai/v1/genie/conversations' === $route => $select ? '' : 'conversation_create',
			default => '',
		};
	}

	/**
	 * Account saves retain native replay. Anonymous snapshots also consume storage.
	 * Concurrent turns share the running-work budget; provider costs are metered at dispatch.
	 *
	 * @param string   $action Server-selected resource operation.
	 * @param Identity $identity Native browser and account identity.
	 * @param int      $files Number of accepted attachment descriptors.
	 * @return array{limits:list<Allowance>,carry:array{}}
	 */
	public static function plan( string $action, Identity $identity, int $files = 0 ): array {
		$guest  = '' === $identity->account;
		$limits = array();
		if ( 'genie' === $action ) {
			if ( $guest ) {
				$limits[] = new Allowance( 'genie_day', $identity->browser, 30, DAY_IN_SECONDS );
				$limits[] = new Allowance( 'genie_burst', $identity->browser, 10, 10 * MINUTE_IN_SECONDS );
			} else {
				$limits[] = new Allowance( 'genie_busy', $identity->account, 1, 0 );
			}
			$limits[] = new Allowance( 'genie_busy', $identity->browser, 1, 0 );
			$limits[] = new Allowance( 'genie_site_busy', 'site', 2, 0 );
			if ( $guest && $files > 0 ) {
				$limits[] = new Allowance( 'genie_files_day', $identity->browser, 10, DAY_IN_SECONDS, $files );
			}
		} elseif ( $guest && in_array( $action, array( 'solution_save', 'conversation_create' ), true ) ) {
			$limits[] = new Allowance( 'tool_write_day', $identity->browser, 500, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'tool_write_site_day', 'site', 2000, DAY_IN_SECONDS );
		}
		return array(
			'limits' => $limits,
			'carry'  => array(),
		);
	}
}
