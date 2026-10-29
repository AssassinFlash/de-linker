<?php
/**
 * Removes the two CookieYes categories the privacy policy does not disclose.
 *
 * CookieYes 3.5.7 still publishes a hidden category in `_ckyConfig`. Accept all
 * then records consent for it. Functional and Performance have no cookies and
 * are already hidden from the banner. This script deletes exactly those rows.
 * It does not edit privacy pages, banner copy, or the disclosed categories.
 *
 * @package Linker\Migrate
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	exit( 1 );
}

const LINKER_COOKIEYES_DISCLOSURE_MARKER = '@@cookieyes-disclosure@@';

try {
	( static function ( string $encoded ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON payload transported as one WP-CLI argument, never executable code.
		$decoded = base64_decode( $encoded, true );
		if ( false === $decoded ) {
			throw new RuntimeException( 'Invalid JSON transport.' );
		}
		$payload = json_decode( $decoded, true, 512, JSON_THROW_ON_ERROR );
		if ( ! is_array( $payload ) ) {
			throw new RuntimeException( 'Payload must be an object.' );
		}
		$operation = isset( $payload['operation'] ) ? (string) $payload['operation'] : 'read';
		if ( 'read' === $operation ) {
			linker_cookieyes_disclosure_emit( linker_cookieyes_disclosure_read() );
			return;
		}
		if ( 'apply' === $operation ) {
			linker_cookieyes_disclosure_apply( $payload );
			linker_cookieyes_disclosure_emit( linker_cookieyes_disclosure_read() );
			return;
		}
		if ( 'rollback' === $operation ) {
			linker_cookieyes_disclosure_rollback( $payload );
			linker_cookieyes_disclosure_emit( linker_cookieyes_disclosure_read() );
			return;
		}
		throw new RuntimeException( 'Unknown operation.' );
	} )( '__LINKER_COOKIEYES_DISCLOSURE_PAYLOAD__' );
} catch ( Throwable $error ) {
	fwrite( STDERR, $error->getMessage() . PHP_EOL );
	exit( 1 );
}

/**
 * Prints one marked JSON line. WP-CLI noise stays off this line.
 *
 * @param array<string, mixed> $data Snapshot.
 */
function linker_cookieyes_disclosure_emit( array $data ): void {
	echo LINKER_COOKIEYES_DISCLOSURE_MARKER . wp_json_encode( $data ) . PHP_EOL;
}

/**
 * Current categories, cookies, and the privacy pages this migration must not edit.
 *
 * @return array<string, mixed>
 */
function linker_cookieyes_disclosure_read(): array {
	global $wpdb;
	linker_cookieyes_disclosure_require_tables();
	$categories = $wpdb->get_results( "SELECT * FROM `{$wpdb->prefix}cky_cookie_categories` ORDER BY category_id ASC", ARRAY_A ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	$cookies    = $wpdb->get_results( "SELECT cookie_id, name, category FROM `{$wpdb->prefix}cky_cookies` ORDER BY cookie_id ASC", ARRAY_A ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	$contents   = $wpdb->get_var( "SELECT contents FROM `{$wpdb->prefix}cky_banners` WHERE banner_id = 1" ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	if ( ! is_array( $categories ) || ! is_array( $cookies ) || ! is_string( $contents ) ) {
		throw new RuntimeException( 'CookieYes tables did not read.' );
	}
	return array(
		'home'            => (string) get_option( 'home' ),
		'categories'      => array_map( 'linker_cookieyes_disclosure_category', $categories ),
		'cookies'         => array_map( 'linker_cookieyes_disclosure_cookie', $cookies ),
		'privacy'         => linker_cookieyes_disclosure_privacy(),
		'banner_contents' => hash( 'sha256', $contents ),
	);
}

/**
 * Deletes the planned rows only while they still match the backup.
 *
 * @param array<string, mixed> $payload Apply payload.
 */
function linker_cookieyes_disclosure_apply( array $payload ): void {
	$rows = $payload['rows'] ?? null;
	if ( ! is_array( $rows ) || array() === $rows ) {
		throw new RuntimeException( 'Apply needs the backed-up rows.' );
	}
	linker_cookieyes_disclosure_mutate( $rows, 'delete' );
}

/**
 * Restores the backed-up rows with their original ids.
 *
 * @param array<string, mixed> $payload Rollback payload.
 */
function linker_cookieyes_disclosure_rollback( array $payload ): void {
	$rows = $payload['rows'] ?? null;
	if ( ! is_array( $rows ) || array() === $rows ) {
		throw new RuntimeException( 'Rollback needs the backed-up rows.' );
	}
	linker_cookieyes_disclosure_mutate( $rows, 'restore' );
}

/**
 * One transaction for either deleting or restoring the undisclosed rows.
 *
 * @param array<int, mixed> $rows Backed-up category rows.
 * @param string            $mode delete or restore.
 */
function linker_cookieyes_disclosure_mutate( array $rows, string $mode ): void {
	global $wpdb;
	linker_cookieyes_disclosure_require_tables();
	$expected_privacy = linker_cookieyes_disclosure_privacy();
	$connection       = $wpdb->__get( 'dbh' );
	$thread           = mysqli_thread_id( $connection ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id
	$guard            = static function ( string $query ) use ( $wpdb, $connection, $thread ): string {
		if ( $wpdb->__get( 'dbh' ) !== $connection || mysqli_thread_id( $connection ) !== $thread ) { // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id
			throw new RuntimeException( 'Database connection changed during the category transaction.' );
		}
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report
		return $query;
	};
	try {
		$wpdb->__set( 'reconnect_retries', 0 );
		mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report
		add_filter( 'query', $guard, PHP_INT_MAX );
		if ( false === $wpdb->query( 'START TRANSACTION' ) ) {
			throw new RuntimeException( 'Could not begin the category transaction.' );
		}
		foreach ( $rows as $row ) {
			if ( ! is_array( $row ) ) {
				throw new RuntimeException( 'A category row is not an object.' );
			}
			if ( 'delete' === $mode ) {
				linker_cookieyes_disclosure_delete_row( $row );
			} else {
				linker_cookieyes_disclosure_restore_row( $row );
			}
		}
		if ( linker_cookieyes_disclosure_privacy() !== $expected_privacy ) {
			throw new RuntimeException( 'Privacy pages changed during the category transaction.' );
		}
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Could not commit the category transaction.' );
		}
	} catch ( Throwable $error ) {
		try {
			$wpdb->query( 'ROLLBACK' );
		} catch ( Throwable $rollback_error ) {
			error_log( 'Category transaction rollback unavailable: ' . get_class( $rollback_error ) ); // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_error_log
		}
		throw $error;
	} finally {
		remove_filter( 'query', $guard, PHP_INT_MAX );
		mysqli_report( MYSQLI_REPORT_OFF ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report
	}
	do_action( 'cky_after_update_cookie_category' );
	if ( class_exists( '\CookieYes\Lite\Includes\Cache' ) ) {
		\CookieYes\Lite\Includes\Cache::delete( 'categories' );
	}
}

/**
 * Deletes one backed-up row after locking and comparing it.
 *
 * @param array<string, mixed> $row Backed-up row.
 */
function linker_cookieyes_disclosure_delete_row( array $row ): void {
	global $wpdb;
	$current = linker_cookieyes_disclosure_lock( (int) $row['category_id'] );
	if ( linker_cookieyes_disclosure_category( $current ) !== linker_cookieyes_disclosure_category( $row ) ) {
		throw new RuntimeException( 'Category changed since backup; nothing written.' );
	}
	if ( 0 !== (int) $current['visibility'] ) {
		throw new RuntimeException( 'Refusing to delete a visible category.' );
	}
	$cookies = (int) $wpdb->get_var( $wpdb->prepare( "SELECT COUNT(*) FROM `{$wpdb->prefix}cky_cookies` WHERE category = %d", (int) $current['category_id'] ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	if ( 0 !== $cookies ) {
		throw new RuntimeException( 'Refusing to delete a category that has cookies.' );
	}
	$deleted = $wpdb->delete(
		$wpdb->prefix . 'cky_cookie_categories',
		array( 'category_id' => (int) $current['category_id'] ),
		array( '%d' )
	);
	if ( 1 !== $deleted ) {
		throw new RuntimeException( 'Category delete did not remove one row.' );
	}
}

/**
 * Inserts one backed-up row when it is absent. An identical row is already restored.
 *
 * @param array<string, mixed> $row Backed-up row.
 */
function linker_cookieyes_disclosure_restore_row( array $row ): void {
	global $wpdb;
	$wanted = linker_cookieyes_disclosure_category( $row );
	$found  = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM `{$wpdb->prefix}cky_cookie_categories` WHERE category_id = %d FOR UPDATE", (int) $wanted['category_id'] ), ARRAY_A ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	if ( is_array( $found ) ) {
		if ( linker_cookieyes_disclosure_category( $found ) !== $wanted ) {
			throw new RuntimeException( 'Category id is already used by a different row.' );
		}
		return;
	}
	$inserted = $wpdb->insert(
		$wpdb->prefix . 'cky_cookie_categories',
		array(
			'category_id'        => $wanted['category_id'],
			'name'               => $wanted['name'],
			'slug'               => $wanted['slug'],
			'description'        => $wanted['description'],
			'prior_consent'      => $wanted['prior_consent'],
			'visibility'         => $wanted['visibility'],
			'priority'           => $wanted['priority'],
			'sell_personal_data' => $wanted['sell_personal_data'],
			'meta'               => $wanted['meta'],
			'date_created'       => $wanted['date_created'],
			'date_modified'      => $wanted['date_modified'],
		),
		array( '%d', '%s', '%s', '%s', '%d', '%d', '%d', '%d', '%s', '%s', '%s' )
	);
	if ( 1 !== $inserted ) {
		throw new RuntimeException( 'Category restore did not insert one row.' );
	}
}

/**
 * Locks one category row.
 *
 * @param int $id Category id.
 * @return array<string, mixed>
 */
function linker_cookieyes_disclosure_lock( int $id ): array {
	global $wpdb;
	$row = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM `{$wpdb->prefix}cky_cookie_categories` WHERE category_id = %d FOR UPDATE", $id ), ARRAY_A ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
	if ( ! is_array( $row ) ) {
		throw new RuntimeException( 'Category disappeared before it could be locked.' );
	}
	return $row;
}

/**
 * Stable category fields. JSON transport preserves these types.
 *
 * @param array<string, mixed> $row Database row.
 * @return array<string, mixed>
 */
function linker_cookieyes_disclosure_category( array $row ): array {
	$labels = json_decode( (string) $row['name'], true );
	return array(
		'category_id'        => (int) $row['category_id'],
		'slug'               => (string) $row['slug'],
		'name'               => (string) $row['name'],
		'labels'             => is_array( $labels ) ? $labels : array(),
		'description'        => (string) $row['description'],
		'prior_consent'      => (int) $row['prior_consent'],
		'visibility'         => (int) $row['visibility'],
		'priority'           => (int) $row['priority'],
		'sell_personal_data' => (int) $row['sell_personal_data'],
		'meta'               => isset( $row['meta'] ) && null !== $row['meta'] ? (string) $row['meta'] : null,
		'date_created'       => (string) $row['date_created'],
		'date_modified'      => (string) $row['date_modified'],
	);
}

/**
 * Cookie identity used to prove a category is empty and stays empty.
 *
 * @param array<string, mixed> $row Cookie row.
 * @return array<string, int|string>
 */
function linker_cookieyes_disclosure_cookie( array $row ): array {
	return array(
		'cookie_id' => (int) $row['cookie_id'],
		'name'      => (string) $row['name'],
		'category'  => (int) $row['category'],
	);
}

/**
 * English and German privacy pages, hashed so a write can prove it did not edit them.
 *
 * @return array<int, array<string, int|string>>
 */
function linker_cookieyes_disclosure_privacy(): array {
	$page = get_page_by_path( 'privacy-policy' );
	if ( ! $page instanceof WP_Post ) {
		throw new RuntimeException( 'privacy-policy is missing.' );
	}
	$german_id = function_exists( 'pll_get_post' ) ? pll_get_post( $page->ID, 'de' ) : 0;
	$german    = $german_id ? get_post( $german_id ) : null;
	if ( ! $german instanceof WP_Post ) {
		throw new RuntimeException( 'German privacy page is missing.' );
	}
	$pages = array();
	foreach ( array( $page, $german ) as $post ) {
		$pages[] = array(
			'id'     => (int) $post->ID,
			'slug'   => (string) $post->post_name,
			'sha256' => hash( 'sha256', (string) $post->post_content ),
		);
	}
	return $pages;
}

/**
 * Refuses to run unless the CookieYes tables this migration edits are present.
 */
function linker_cookieyes_disclosure_require_tables(): void {
	global $wpdb;
	foreach ( array( 'cky_cookie_categories', 'cky_cookies', 'cky_banners' ) as $table ) {
		$found = $wpdb->get_var( $wpdb->prepare( 'SHOW TABLES LIKE %s', $wpdb->prefix . $table ) ); // phpcs:ignore WordPress.DB.DirectDatabaseQuery
		if ( $found !== $wpdb->prefix . $table ) {
			throw new RuntimeException( 'Missing CookieYes table: ' . $table );
		}
	}
}
