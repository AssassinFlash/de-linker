<?php
/**
 * Correct one German eManager spelling, including its translation baseline.
 *
 * Run with WP-CLI: eval-file this file with plan, apply, or rollback.
 * Rollback also requires the two modified timestamps returned by apply.
 * A production apply requires the normal full database backup first.
 *
 * @package Linker\Commerce
 */

( static function ( array $args ): void {
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		throw new RuntimeException( 'Run through WP-CLI.' );
	}
	$action         = $args[0] ?? 'plan';
	$home           = untrailingslashit( home_url() );
	$reviewed_local = (bool) preg_match( '#^https?://(?:127\.0\.0\.1|localhost):\d+$#', $home );
	if ( ! in_array( $action, array( 'plan', 'apply', 'rollback' ), true ) || ( 'https://de-linker.com' !== $home && ! $reviewed_local ) ) {
		WP_CLI::error( 'Expected a reviewed site and plan, apply or rollback.' );
	}
	$old_excerpt = 'b9703de003f70c6843594e85e5d3950cb7130042a4cdffa36c44e832fa172c3a';
	$new_excerpt = '5ea4f692c608b58f1f68056759e3180071ef6299d6e63a9cd504b02bda88c898';
	$old_units   = 'd91163c6bb58436a5fa523726d4b23558ca670b20c87f46058564855cb082191';
	$new_units   = '3b2b267ea0c3e1208a538681523792b7c0fd76cc670729b6cfd35013fcd5c483';
	$old_dates   = array( '2026-10-19 02:15:07', '2026-10-18 18:15:07' );
	$ids         = array( 3618, 6643 );
	global $wpdb;

	/** Fingerprint every unrelated post field and metadata value. */
	$protected = static function () use ( $ids ): array {
		$out = array();
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			$post = get_post( $id, ARRAY_A );
			$meta = get_post_meta( $id );
			if ( 3618 === $id ) {
				unset( $meta['_linker_de_excerpt'] );
			} else {
				unset( $post['post_excerpt'], $post['post_modified'], $post['post_modified_gmt'], $meta['_linker_i18n_units'] );
			}
			ksort( $meta );
			$json = wp_json_encode(
				array(
					'post' => $post,
					'meta' => $meta,
				),
				JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
			);
			if ( ! is_string( $json ) ) {
				throw new RuntimeException( 'Cannot fingerprint protected product state.' );
			}
			$out[ $id ] = hash( 'sha256', $json );
		}
		return $out;
	};
	/** Verify the pair, the exact wording and the current translation units. */
	$read = static function () use ( $old_excerpt, $new_excerpt, $old_units, $new_units ): array {
		foreach ( array( 3618, 6643 ) as $id ) {
			clean_post_cache( $id );
		}
		$en      = get_post( 3618 );
		$de      = get_post( 6643 );
		$product = wc_get_product( 3618 );
		if ( ! $en instanceof WP_Post || ! $de instanceof WP_Post || ! $product instanceof WC_Product
			|| 'product' !== $de->post_type || 'publish' !== $en->post_status || 'publish' !== $de->post_status
			|| 'saj-emanager-emanager-5-0-residential-energy-manager' !== $product->get_slug() || 'DLK-SAJ-EMANAGER' !== $product->get_sku()
			|| 'en' !== pll_get_post_language( 3618 ) || 'de' !== pll_get_post_language( 6643 )
			|| 6643 !== (int) pll_get_post( 3618, 'de' ) || 3618 !== (int) pll_get_post( 6643, 'en' ) ) {
			throw new RuntimeException( 'The reviewed product pair changed.' );
		}
		$legacy     = get_post_meta( 3618, '_linker_de_excerpt', false );
		$legacy_sha = get_post_meta( 3618, '_linker_de_excerpt_sha', false );
		$raw_units  = get_post_meta( 6643, '_linker_i18n_units', false );
		if ( array( $de->post_excerpt ) !== $legacy || array( sha1( $en->post_excerpt ) ) !== $legacy_sha || 1 !== count( $raw_units ) || ! is_string( $raw_units[0] )
			|| 'db3bb344d6a3d1ab121cc0e4ba6b1a7c10ed8f24ee7e05333caa66bb38e829d4' !== hash( 'sha256', $en->post_excerpt ) ) {
			throw new RuntimeException( 'The reviewed source or German excerpt changed.' );
		}
		$state = hash( 'sha256', $de->post_excerpt ) === $old_excerpt ? 'old' : 'new';
		if ( ( 'old' === $state ? $old_excerpt : $new_excerpt ) !== hash( 'sha256', $de->post_excerpt )
			|| ( 'old' === $state ? $old_units : $new_units ) !== hash( 'sha256', $raw_units[0] ) ) {
			throw new RuntimeException( 'The excerpt or translation units differ from the reviewed state.' );
		}
		$fields = new \Linker\I18n\Translation\Fields();
		$source = $fields->of_post( $en );
		$parts  = array();
		foreach ( $source as $key => list( $value ) ) {
			$parts[] = $key . "\0" . $value;
		}
		$state_api  = new \Linker\I18n\Translation\State();
		$source_sha = $state_api->source_hash( 'post', 6643 );
		$units      = $state_api->units( 'post', 6643 );
		$segmenter  = new \Linker\I18n\Translation\Segmenter( new \Linker\I18n\Translation\HtmlTokenizer() );
		$unit       = $units['post_excerpt'] ?? null;
		if ( sha1( implode( "\1", $parts ) ) !== $source_sha || 'synced' !== $state_api->status( 'post', 3618 ) || '' !== $state_api->note( 'post', 3618 )
			|| json_decode( $raw_units[0], true, 512, JSON_THROW_ON_ERROR ) !== $units || ! is_array( $unit )
			|| false !== $unit['conflict'] || $unit['src'] !== $segmenter->block_hashes( $en->post_excerpt, true )
			|| $unit['out'] !== $segmenter->block_hashes( $de->post_excerpt, true ) ) {
			throw new RuntimeException( 'The current translation baseline is not the reviewed one.' );
		}
		$word   = 'old' === $state ? 'Hutschiengerät' : 'Hutschienengerät';
		$target = 'old' === $state ? 'Hutschienengerät' : 'Hutschiengerät';
		if ( 1 !== substr_count( $de->post_excerpt, $word ) ) {
			throw new RuntimeException( 'The reviewed German word is missing or ambiguous.' );
		}
		$excerpt                      = str_replace( $word, $target, $de->post_excerpt );
		$units['post_excerpt']['out'] = $segmenter->block_hashes( $excerpt, true );
		if ( ( 'old' === $state ? $new_excerpt : $old_excerpt ) !== hash( 'sha256', $excerpt )
			|| ( 'old' === $state ? $new_units : $old_units ) !== hash( 'sha256', (string) wp_json_encode( $units ) ) ) {
			throw new RuntimeException( 'The corrected excerpt or baseline differs from the reviewed target.' );
		}
		return array(
			'state'      => $state,
			'excerpt'    => $de->post_excerpt,
			'target'     => $excerpt,
			'units'      => $units,
			'source_sha' => $source_sha,
			'dates'      => array( $de->post_modified, $de->post_modified_gmt ),
		);
	};

	$started     = false;
	$commit      = false;
	$touched     = false;
	$failure     = null;
	$receipt     = null;
	$guard       = null;
	$reconnects  = null;
	$report_mode = null;
	$restore     = static function ( array $data, array $postarr ) use ( $action, $old_dates ): array {
		if ( 'rollback' === $action && 6643 === (int) ( $postarr['ID'] ?? 0 ) ) {
			$data['post_modified']     = $old_dates[0];
			$data['post_modified_gmt'] = $old_dates[1];
		}
		return $data;
	};
	if ( 'plan' !== $action ) {
		if ( 'wpdb' !== get_class( $wpdb ) ) {
			WP_CLI::error( 'The native WordPress mysqli connection is required.' );
		}
		$connection = $wpdb->__get( 'dbh' );
		$reconnects = $wpdb->__get( 'reconnect_retries' );
		if ( ! $connection instanceof mysqli || ! is_int( $reconnects ) ) {
			WP_CLI::error( 'The native WordPress mysqli connection is required.' );
		}
		$thread      = mysqli_thread_id( $connection ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- Inspect the existing connection only.
		$driver      = new mysqli_driver();
		$report_mode = $driver->report_mode;
		$guard       = static function ( string $query ) use ( $wpdb, $connection, $thread ): string {
			if ( $wpdb->__get( 'dbh' ) !== $connection || mysqli_thread_id( $connection ) !== $thread ) { // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- Reject a reconnected transaction.
				throw new RuntimeException( 'Database connection changed during the excerpt transaction.' );
			}
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Prevent a disconnected write replay in this CLI process.
			return $query;
		};
	}
	try {
		if ( 'plan' !== $action ) {
			$wpdb->__set( 'reconnect_retries', 0 );
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restored in finally.
			add_filter( 'query', $guard, PHP_INT_MAX );
			add_filter( 'wp_insert_post_data', $restore, PHP_INT_MAX, 2 );
			foreach ( array( $wpdb->posts, $wpdb->postmeta ) as $table ) {
				if ( 'InnoDB' !== $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $table ) ) ) {
					throw new RuntimeException( 'Transactional post storage is required.' );
				}
			}
			if ( false === $wpdb->query( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' ) || false === $wpdb->query( 'START TRANSACTION' ) ) {
				throw new RuntimeException( 'Cannot start the guarded transaction.' );
			}
			$started = true;
			$locked  = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE ID IN (%d,%d) ORDER BY ID FOR UPDATE", $ids[0], $ids[1] ) );
			if ( array_map( 'intval', $locked ) !== $ids ) {
				throw new RuntimeException( 'The audited product pair no longer exists.' );
			}
			$wpdb->get_col( $wpdb->prepare( "SELECT meta_id FROM {$wpdb->postmeta} WHERE post_id IN (%d,%d) ORDER BY meta_id FOR UPDATE", $ids[0], $ids[1] ) );
			if ( '' !== $wpdb->last_error ) {
				throw new RuntimeException( 'Could not lock the product metadata.' );
			}
		}
		$before = $read();
		if ( 'plan' === $action ) {
			WP_CLI::log(
				(string) wp_json_encode(
					array(
						'site'  => $home,
						'state' => $before['state'],
						'dates' => $before['dates'],
					)
				)
			);
			return;
		}
		if ( ( 'apply' === $action && ( 'old' !== $before['state'] || $before['dates'] !== $old_dates ) )
			|| ( 'rollback' === $action && ( 'new' !== $before['state'] || array( $args[1] ?? null, $args[2] ?? null ) !== $before['dates'] ) ) ) {
			throw new RuntimeException( 'The requested operation does not match its exact preimage or receipt.' );
		}
		$other_before = $protected();
		$touched      = true;
		if ( ! update_post_meta( 3618, '_linker_de_excerpt', wp_slash( $before['target'] ), $before['excerpt'] ) ) {
			throw new RuntimeException( 'Could not update the legacy German excerpt.' );
		}
		$saved = wp_update_post(
			wp_slash(
				array(
					'ID'           => 6643,
					'post_excerpt' => $before['target'],
				)
			),
			true,
			false
		);
		if ( is_wp_error( $saved ) || 6643 !== $saved ) {
			throw new RuntimeException( 'Could not update the native German product excerpt.' );
		}
		( new \Linker\I18n\Translation\State() )->save( 'post', 6643, $before['source_sha'], $before['units'] );
		$after = $read();
		if ( $after['excerpt'] !== $before['target'] || $after['target'] !== $before['excerpt'] || $after['source_sha'] !== $before['source_sha']
			|| ( 'rollback' === $action && $after['dates'] !== $old_dates ) || $protected() !== $other_before ) {
			throw new RuntimeException( 'Excerpt, translation baseline or protected product readback differs.' );
		}
		$commit = true;
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Commit result is unknown; inspect both products before any retry.' );
		}
		$started = false;
		$receipt = array(
			'site'         => $home,
			'action'       => $action,
			'before_state' => $before['state'],
			'after_state'  => $after['state'],
			'before_dates' => $before['dates'],
			'after_dates'  => $after['dates'],
			'protected'    => $other_before,
		);
	} catch ( Throwable $error ) {
		$rollback_failed = false;
		if ( $started && ! $commit ) {
			try {
				$wpdb->query( 'ROLLBACK' );
			} catch ( Throwable $rollback_error ) {
				$rollback_failed = true;
			}
		}
		if ( $touched ) {
			foreach ( $ids as $id ) {
				wp_cache_delete( $id, 'posts' );
				wp_cache_delete( $id, 'post_meta' );
			}
		}
		$failure = $commit || $rollback_failed
			? 'Transaction outcome is unknown; independently read both products before retry or rollback.'
			: $error->getMessage();
	} finally {
		if ( null !== $guard ) {
			remove_filter( 'query', $guard, PHP_INT_MAX );
			remove_filter( 'wp_insert_post_data', $restore, PHP_INT_MAX );
			$wpdb->__set( 'reconnect_retries', $reconnects );
			mysqli_report( $report_mode ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restore the caller's original report mode.
		}
	}
	if ( null !== $failure ) {
		WP_CLI::error( $failure );
	}
	if ( null !== $receipt ) {
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			wc_delete_product_transients( $id );
		}
		WP_CLI::log( (string) wp_json_encode( $receipt ) );
	}
} )( $args ?? array() );
