<?php
/**
 * Native account grants for existing browser recovery namespaces.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Planner;

use WP_Error;

/** Grants local discovery only. Every project RPC still verifies ownership. */
final class RecoveryScopes {

	private const PREFIX = '_linker_planner_recovery_';
	/** Native discovery resource policy, not an account or retention ceiling. */
	public const PAGE_SIZE = 32;

	/**
	 * Record an authenticated session or an engine-confirmed native claim.
	 *
	 * @param int    $user Native account, never request JSON.
	 * @param string $scope Native query scope captured before identity changed.
	 */
	public function remember( int $user, string $scope ): bool {
		if ( $user < 1 || ! self::valid( $scope ) || false === get_userdata( $user ) ) {
			return false;
		}
		$key = self::PREFIX . $scope;
		if ( '1' !== get_user_meta( $user, $key, true ) ) {
			add_user_meta( $user, $key, '1', true );
		}
		return '1' === get_user_meta( $user, $key, true );
	}

	/**
	 * Read only this verified account's grants. Duplicated concurrent native
	 * meta inserts are harmless; DISTINCT makes page boundaries deterministic.
	 *
	 * @param int         $user Current native user.
	 * @param string|null $after Last scope from the preceding page.
	 * @return array{schema_version:int,scopes:list<string>,next:string|null}|WP_Error Native page.
	 */
	public function page( int $user, ?string $after ): array|WP_Error {
		if ( null !== $after && ! self::valid( $after ) ) {
			return Failure::make( 'recovery_cursor', 422 );
		}
		if ( $user < 1 ) {
			return array(
				'schema_version' => 1,
				'scopes'         => array(),
				'next'           => null,
			);
		}
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery.DirectQuery, WordPress.DB.DirectDatabaseQuery.NoCaching -- private cursor pagination with native account ownership on every read.
		$keys = $wpdb->get_col( $wpdb->prepare( 'SELECT DISTINCT meta_key FROM %i WHERE user_id = %d AND meta_key LIKE %s AND meta_key > %s AND meta_value = %s ORDER BY meta_key ASC LIMIT %d', $wpdb->usermeta, $user, $wpdb->esc_like( self::PREFIX ) . '%', self::PREFIX . ( $after ?? '' ), '1', self::PAGE_SIZE + 1 ) );
		if ( '' !== $wpdb->last_error ) {
			return Failure::make( 'recovery_unavailable', 503 );
		}
		$scopes = array();
		foreach ( $keys as $key ) {
			$scope = substr( (string) $key, strlen( self::PREFIX ) );
			if ( ! self::valid( $scope ) ) {
				return Failure::make( 'recovery_unavailable', 503 );
			}
			$scopes[] = $scope;
		}
		$more = count( $scopes ) > self::PAGE_SIZE;
		return array(
			'schema_version' => 1,
			'scopes'         => array_slice( $scopes, 0, self::PAGE_SIZE ),
			'next'           => $more ? $scopes[ self::PAGE_SIZE - 1 ] : null,
		);
	}

	/**
	 * Recognise an opaque, native-issued query/recovery namespace.
	 *
	 * @param string $scope Native hash.
	 */
	public static function valid( string $scope ): bool {
		return 1 === preg_match( '/\A[a-f0-9]{64}\z/', $scope );
	}
}
