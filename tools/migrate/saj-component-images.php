<?php
/**
 * Select existing individual-product images for three SAJ components.
 *
 * Run with WP-CLI: eval-file this file with plan, apply, or rollback.
 * A production apply still requires the normal full database backup. The
 * original assembled-system images remain in both language galleries.
 *
 * @package Linker\Commerce
 */

( static function ( array $args ): void {
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		throw new RuntimeException( 'Run through WP-CLI.' );
	}
	$action = $args[0] ?? 'plan';
	if ( ! in_array( $action, array( 'plan', 'apply', 'rollback' ), true ) ) {
		WP_CLI::error( 'Expected plan, apply or rollback.' );
	}

	$products = array(
		2090 => array(
			'de'   => 6738,
			'slug' => 'saj-bu2-5-0-hv1',
			'sku'  => 'DLK-SAJ-BU250HV1',
			'old'  => 2065,
			'new'  => 2084,
		),
		2092 => array(
			'de'   => 6736,
			'slug' => 'saj-bc2-hv1',
			'sku'  => 'DLK-SAJ-BC2HV1',
			'old'  => 2065,
			'new'  => 2085,
		),
		2093 => array(
			'de'   => 6735,
			'slug' => 'saj-bu3-5-0-tv2-pro',
			'sku'  => 'DLK-SAJ-BU350TV2PRO',
			'old'  => 2131,
			'new'  => 2086,
		),
	);
	$images   = array(
		2065 => 'a8d274d63501ccfcdabf12c3690d1d5b73e5bb985f014ccb9d072526698da473',
		2131 => '9b4e70fa18937e4485ea01652d246c3e20568281e3aaf64cd0024ee8488b6088',
		2084 => '93fa2055cfffff3622dcf6e55c17784510a794d43c624bc14ee3bfe58bafb5c9',
		2085 => '1958e604745963110058ba0de720412d40ba6a0c72a4c0d6323af9033a1774b9',
		2086 => 'fc31f9b0debabc856e54fbba2ddab743f1ada74a8b26acfda3edb05af4ce58ca',
	);
	$ids      = array();
	foreach ( $products as $en => $entry ) {
		$ids[] = $en;
		$ids[] = $entry['de'];
	}

	global $wpdb;
	$clean = static function () use ( $ids ): void {
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			wc_delete_product_transients( $id );
		}
	};
	/** Refresh only the reviewed products and attachments before native reads. */
	$refresh = static function () use ( $ids, $images ): void {
		foreach ( array_merge( $ids, array_keys( $images ) ) as $id ) {
			clean_post_cache( $id );
		}
	};
	/** Read the exact persisted featured-image rows, rejecting duplicates. */
	$thumbnails = static function ( bool $lock ) use ( $wpdb, $ids ): array {
		$query = $wpdb->prepare( "SELECT post_id, meta_value FROM {$wpdb->postmeta} WHERE meta_key = '_thumbnail_id' AND post_id IN (%d,%d,%d,%d,%d,%d) ORDER BY post_id", $ids[0], $ids[1], $ids[2], $ids[3], $ids[4], $ids[5] );
		if ( $lock ) {
			$query .= ' FOR UPDATE';
		}
		$rows = $wpdb->get_results( $query, ARRAY_A ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- Prepared above; FOR UPDATE is a fixed suffix.
		if ( ! is_array( $rows ) || count( $rows ) !== count( $ids ) ) {
			throw new RuntimeException( 'Expected one featured-image row per product.' );
		}
		$out = array();
		foreach ( $rows as $row ) {
			$id = (int) $row['post_id'];
			if ( isset( $out[ $id ] ) || ! ctype_digit( (string) $row['meta_value'] ) ) {
				throw new RuntimeException( 'Duplicate or invalid featured-image row.' );
			}
			$out[ $id ] = (int) $row['meta_value'];
		}
		return $out;
	};
	/** Fingerprint every other post field and metadata value for these products. */
	$protected = static function () use ( $ids ): array {
		$out = array();
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			$post = get_post( $id, ARRAY_A );
			$meta = get_post_meta( $id );
			unset( $meta['_thumbnail_id'] );
			ksort( $meta );
			$json = wp_json_encode(
				array(
					'post' => $post,
					'meta' => $meta,
				),
				JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
			);
			if ( ! is_string( $json ) ) {
				throw new RuntimeException( 'Cannot fingerprint the protected product state.' );
			}
			$out[ $id ] = hash( 'sha256', $json );
		}
		return $out;
	};
	/** Confirm the product pairs and both existing galleries still match the plan. */
	$validate = static function () use ( $products, $images ): void {
		if ( ! function_exists( 'pll_get_post' ) || ! function_exists( 'pll_get_post_language' ) ) {
			throw new RuntimeException( 'Polylang is required.' );
		}
		$options = get_option( 'polylang' );
		if ( ! is_array( $options ) || ! empty( $options['media_support'] ) || ! in_array( '_thumbnail_id', $options['sync'] ?? array(), true ) ) {
			throw new RuntimeException( 'The reviewed featured-image synchronization changed.' );
		}
		foreach ( $images as $id => $sha ) {
			$file = get_attached_file( $id );
			if ( ! wp_attachment_is_image( $id ) || ! is_string( $file ) || ! is_file( $file ) || ! hash_equals( $sha, (string) hash_file( 'sha256', $file ) ) ) {
				throw new RuntimeException( 'An audited image is missing or has changed.' );
			}
		}
		foreach ( $products as $en => $entry ) {
			$de      = $entry['de'];
			$product = wc_get_product( $en );
			$en_pair = (int) pll_get_post( $en, 'de' );
			$de_pair = (int) pll_get_post( $de, 'en' );
			if ( ! $product instanceof WC_Product || $entry['slug'] !== $product->get_slug() || $entry['sku'] !== $product->get_sku()
				|| 'publish' !== get_post_status( $en ) || 'publish' !== get_post_status( $de )
				|| 'en' !== pll_get_post_language( $en ) || 'de' !== pll_get_post_language( $de )
				|| $de !== $en_pair || $en !== $de_pair ) {
				throw new RuntimeException( 'An audited product or language pair has changed.' );
			}
			foreach ( array( '_tv_legacy_acf_json', '_linker_de_acf_json' ) as $key ) {
				$raw = get_post_meta( $en, $key, true );
				$acf = is_string( $raw ) ? json_decode( $raw, true ) : null;
				if ( ! is_array( $acf ) || ! is_array( $acf['product_gallery'] ?? null ) || ! is_array( $acf['feature_cards'] ?? null ) ) {
					throw new RuntimeException( 'An audited language gallery is unavailable.' );
				}
				$gallery  = array_map( 'intval', array_column( $acf['product_gallery'], 'gallery_image' ) );
				$features = array_map( 'intval', array_column( $acf['feature_cards'], 'feature_image' ) );
				if ( ! in_array( $entry['old'], $gallery, true ) || ! in_array( $entry['new'], $features, true ) ) {
					throw new RuntimeException( 'The original system image or individual image is no longer in the gallery.' );
				}
			}
		}
	};
	$expected = static function ( string $which ) use ( $products ): array {
		$out = array();
		foreach ( $products as $en => $entry ) {
			$out[ $en ]          = $entry[ $which ];
			$out[ $entry['de'] ] = $entry[ $which ];
		}
		ksort( $out );
		return $out;
	};

	$started     = false;
	$commit      = false;
	$touched     = false;
	$failure     = null;
	$receipt     = null;
	$connection  = null;
	$reconnects  = null;
	$report_mode = null;
	$guard       = null;
	if ( 'plan' !== $action ) {
		if ( 'wpdb' !== get_class( $wpdb ) ) {
			WP_CLI::error( 'The native WordPress mysqli connection is required.' );
		}
		$connection = $wpdb->__get( 'dbh' );
		$reconnects = $wpdb->__get( 'reconnect_retries' );
		if ( ! $connection instanceof mysqli || ! is_int( $reconnects ) ) {
			WP_CLI::error( 'The native WordPress mysqli connection is required.' );
		}
		$thread      = mysqli_thread_id( $connection ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- Inspect the existing connection, never create one.
		$driver      = new mysqli_driver();
		$report_mode = $driver->report_mode;
		$guard       = static function ( string $query ) use ( $wpdb, $connection, $thread ): string {
			if ( $wpdb->__get( 'dbh' ) !== $connection || mysqli_thread_id( $connection ) !== $thread ) { // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_thread_id -- A reconnected transaction must fail before another query.
				throw new RuntimeException( 'Database connection changed during the image transaction.' );
			}
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Prevent a disconnected write replay in this CLI process only.
			return $query;
		};
	}
	try {
		if ( 'plan' !== $action ) {
			$wpdb->__set( 'reconnect_retries', 0 );
			mysqli_report( MYSQLI_REPORT_ERROR | MYSQLI_REPORT_STRICT ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restored in finally.
			add_filter( 'query', $guard, PHP_INT_MAX );
			foreach ( array( $wpdb->posts, $wpdb->postmeta ) as $table ) {
				$engine = $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $table ) );
				if ( 'InnoDB' !== $engine ) {
					throw new RuntimeException( 'Transactional post storage is required.' );
				}
			}
			if ( false === $wpdb->query( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' ) || false === $wpdb->query( 'START TRANSACTION' ) ) {
				throw new RuntimeException( 'Cannot start the guarded transaction.' );
			}
			$started = true;
			$locked  = $wpdb->get_col( $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE ID IN (%d,%d,%d,%d,%d,%d) ORDER BY ID FOR UPDATE", $ids[0], $ids[1], $ids[2], $ids[3], $ids[4], $ids[5] ) );
			if ( count( $locked ) !== count( $ids ) ) {
				throw new RuntimeException( 'An audited product no longer exists.' );
			}
		}
		$before = $thumbnails( $started );
		ksort( $before );
		$refresh();
		$validate();
		$old = $expected( 'old' );
		$new = $expected( 'new' );
		if ( $before !== $old && $before !== $new ) {
			throw new RuntimeException( 'The featured images differ from both complete reviewed states.' );
		}
		if ( 'plan' === $action ) {
			WP_CLI::log(
				(string) wp_json_encode(
					array(
						'site'    => home_url(),
						'action'  => $action,
						'current' => $before,
						'old'     => $old,
						'new'     => $new,
					)
				)
			);
			return;
		}
		$from = 'apply' === $action ? $old : $new;
		$to   = 'apply' === $action ? $new : $old;
		if ( $before !== $from ) {
			throw new RuntimeException( 'The requested operation does not match its exact preimage.' );
		}
		$other_before = $protected();
		foreach ( $products as $en => $entry ) {
			$source = 'apply' === $action ? $entry['old'] : $entry['new'];
			$target = 'apply' === $action ? $entry['new'] : $entry['old'];
			// The existing Polylang native metadata hook synchronizes the German twin.
			$touched = true;
			if ( ! update_post_meta( $en, '_thumbnail_id', $target, (string) $source ) ) {
				throw new RuntimeException( 'A native featured-image update failed.' );
			}
		}
		$after = $thumbnails( true );
		ksort( $after );
		if ( $after !== $to || $protected() !== $other_before ) {
			throw new RuntimeException( 'Paired image or protected product readback differs.' );
		}
		$commit = true;
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Commit result is unknown; inspect all six rows before any retry.' );
		}
		$started = false;
		$receipt = array(
			'site'      => home_url(),
			'action'    => $action,
			'before'    => $before,
			'after'     => $after,
			'protected' => $other_before,
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
				// Cache deletion does not query a possibly disconnected database.
				wp_cache_delete( $id, 'posts' );
				wp_cache_delete( $id, 'post_meta' );
			}
		}
		$failure = $commit || $rollback_failed
			? 'Transaction outcome is unknown; independently read all six products before retrying or rolling back.'
			: $error->getMessage();
	} finally {
		if ( null !== $guard ) {
			remove_filter( 'query', $guard, PHP_INT_MAX );
			$wpdb->__set( 'reconnect_retries', $reconnects );
			mysqli_report( $report_mode ); // phpcs:ignore WordPress.DB.RestrictedFunctions.mysql_mysqli_report -- Restore the caller's original report mode.
		}
	}
	if ( null !== $failure ) {
		WP_CLI::error( $failure );
	}
	if ( null !== $receipt ) {
		$clean();
		WP_CLI::log( (string) wp_json_encode( $receipt ) );
	}
} )( $args ?? array() );
