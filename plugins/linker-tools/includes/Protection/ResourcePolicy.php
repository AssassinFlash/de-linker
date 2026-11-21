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
	 * @return array{limits:list<Allowance>,carry:array{}}
	 */
	public static function plan( string $action, Identity $identity ): array {
		$guest  = '' === $identity->account;
		$limits = array();
		if ( 'genie' === $action ) {
			if ( ! $guest ) {
				$limits[] = new Allowance( 'genie_busy', $identity->account, 1, 0 );
			}
			$limits[] = new Allowance( 'genie_busy', $identity->browser, 1, 0 );
			$limits[] = new Allowance( 'genie_site_busy', 'site', 2, 0 );
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
