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
	 * The private turn handler owns model work. A first guest turn can also create a conversation.
	 *
	 * @param string   $action Server-selected resource operation.
	 * @param Identity $identity Native browser and account identity.
	 * @param bool     $opens_conversation A guest turn needs a new native conversation.
	 * @return array{limits:list<Allowance>,carry:array{}}
	 */
	public static function plan( string $action, Identity $identity, bool $opens_conversation = false ): array {
		$limits = array();
		$writes = in_array( $action, array( 'solution_save', 'conversation_create' ), true ) || ( 'genie' === $action && $opens_conversation );
		if ( '' === $identity->account && $writes ) {
			$limits[] = new Allowance( 'tool_write_day', $identity->browser, 500, DAY_IN_SECONDS );
			$limits[] = new Allowance( 'tool_write_site_day', 'site', 2000, DAY_IN_SECONDS );
		}
		return array(
			'limits' => $limits,
			'carry'  => array(),
		);
	}
}
