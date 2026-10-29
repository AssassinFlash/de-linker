<?php
/**
 * Correct the German smart-meter term in seven existing SAJ product FAQs.
 *
 * Run with WP-CLI: eval-file this file with plan, apply, or rollback.
 * Native FAQ encoding and mirroring preserve all other content and citations.
 * A production apply requires the normal full database backup first.
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
	$home           = untrailingslashit( home_url() );
	$reviewed_local = (bool) preg_match( '#^https?://(?:127\.0\.0\.1|localhost):\d+$#', $home );
	if ( 'https://de-linker.com' !== $home && ! $reviewed_local ) {
		WP_CLI::error( 'This correction is limited to the reviewed production and local sites.' );
	}
	$nom      = array(
		'intelligente Messuhr' => 'intelligenter Stromzähler',
		'Messuhr COMM-Kabel'   => 'Stromzähler-COMM-Kabel',
	);
	$acc      = array(
		'eine intelligente Messuhr' => 'einen intelligenten Stromzähler',
		'Messuhr-COMM-Kabel'        => 'Stromzähler-COMM-Kabel',
	);
	$products = array(
		4107 => array( 6628, 'saj-h2-10k-t3', 'DLK-SAJ-H210KT3', 0, 'a37a0b9111519b88e721f96491c340ff4b413ce9ae6a295625845306c8de1b3d', '4b9a9b0952b9aa77296662b47ccf3b0c5a45eeb0979a6c69c0803495a31e759d', $nom ),
		4108 => array( 6627, 'saj-h2-12k-t3', 'DLK-SAJ-H212KT3', 0, '0578d027515048735845ca42d106e62726a57888101494bc96ce554fe7dbbaf7', '688b8f1b19685755a7250804b12542dfa8f26062b96f23b4fe8b08e207da906c', $nom ),
		2063 => array( 6752, 'saj-h2-15k-t3', 'DLK-SAJ-H215KT3', 0, '235e405be8a5dc97d98468cdc2b47565487650b25f86d44fd4746698c51e7144', '52f9c968dbfd1fb197b70c10dd9e1180c3654a2f352bc8559f572c26a492b8a6', $acc ),
		2064 => array( 6751, 'saj-h2-20k-t3', 'DLK-SAJ-H220KT3', 0, '506b0898f812f6602d4b27125848341c7f1cd7f0e93e650047a4c2b7898ee691', '3c1afbc799af9e0669608aed6ba1b7c6c149f33bcac3d081b148b8add50ad2b8', $acc ),
		1179 => array( 6838, 'saj-h2-25k-t3', 'DLK-SAJ-H225KT3', 0, 'cc48b5cb22384d62c81f1d09019db10cf2ca03c6dceac06c97491b74696e4097', '829e64d4ab0ed578b7dbb220c590345cde7626e90730b5e8a175b38d4e7b02fc', $acc ),
		1181 => array( 6837, 'saj-h2-30k-t3-de', 'DLK-SAJ-H230KT3DE', 1, 'ff475060aa188ca2b9363d16db334240a9239a8c9dfddfd56bb6443b082e67b3', 'c89dd0c46fb96d0067a108729e179ff07f1990e5932101530a2fd08c85911b7c', $nom ),
		1973 => array( 6784, 'saj-emanager-c1-pro', 'DLK-SAJ-EMANAGERC1PRO', 0, '1da23db47751efcf69e64d2541bab0ced797a0df4986e6c3cc3d2e3948a7a8b9', '3fcb6433101b3e789dd421b3756bb959c4af7b7cd9b4ef58094b4c23702d9fef', array( 'smarte Messuhren' => 'intelligente Stromzähler' ) ),
	);
	$ids      = array();
	foreach ( $products as $en => $row ) {
		$ids[] = $en;
		$ids[] = $row[0];
	}
	sort( $ids );

	global $wpdb;
	/** Hash the local fixture as the same content with production citation URLs. */
	$digest = static fn( string $raw ): string => hash( 'sha256', str_replace( $home, 'https://de-linker.com', $raw ) );
	/** Read persisted values directly so duplicate metadata rows cannot be hidden. */
	$faqs = static function () use ( $wpdb, $ids ): array {
		$query = $wpdb->prepare( "SELECT post_id, meta_value FROM {$wpdb->postmeta} WHERE meta_key = '_linker_faqs' AND post_id IN (%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d) ORDER BY post_id", ...$ids ); // phpcs:ignore WordPress.DB.PreparedSQLPlaceholders.ReplacementsWrongNumber -- Fourteen fixed IDs are unpacked.
		$rows  = $wpdb->get_results( $query, ARRAY_A ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- Prepared above.
		if ( ! is_array( $rows ) || count( $rows ) !== count( $ids ) ) {
			throw new RuntimeException( 'Expected one FAQ metadata row per product.' );
		}
		$out = array();
		foreach ( $rows as $row ) {
			$id = (int) $row['post_id'];
			if ( isset( $out[ $id ] ) || ! in_array( $id, $ids, true ) || ! is_string( $row['meta_value'] ) ) {
				throw new RuntimeException( 'Duplicate or invalid FAQ metadata.' );
			}
			$out[ $id ] = $row['meta_value'];
		}
		return $out;
	};
	/** Fingerprint every post and every metadata field outside this correction. */
	$protected = static function () use ( $ids, $products ): array {
		$out = array();
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			$post = get_post( $id, ARRAY_A );
			$meta = get_post_meta( $id );
			unset( $meta['_linker_faqs'] );
			if ( isset( $products[ $id ] ) ) {
				unset( $meta['_linker_publication_faqs'], $meta['_linker_faqs_managed'] );
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
	/** Check existing citation bindings and predict only their new content identities. */
	$binding_targets = static function ( array $before, array $after, string $from ) use ( $products ): array {
		$out = array();
		foreach ( $products as $en => $entry ) {
			$rows = get_post_meta( $en, '_linker_publication_faqs', false );
			if ( 1 !== count( $rows ) || ! is_array( $rows[0] ) ) {
				throw new RuntimeException( 'The original FAQ evidence bindings are unavailable or ambiguous.' );
			}
			$managed = get_post_meta( $en, '_linker_faqs_managed', false );
			if ( ( 'old' === $from ? array() : array( '1' ) ) !== $managed ) {
				throw new RuntimeException( 'The reviewed FAQ management state changed.' );
			}
			$items       = json_decode( $before[ $en ], true, 512, JSON_THROW_ON_ERROR );
			$next_items  = json_decode( $after[ $en ], true, 512, JSON_THROW_ON_ERROR );
			$bindings    = $rows[0];
			$before_keys = array();
			$next        = array();
			$document    = 1973 === $en
				? array( 'doc-9f652adf333e183ed703e91566fc79709368b466aa53ad0cc8e87aaab2eade04', 'f9e736af39f7b50f7760d6369cab6c95ff38882b49ac42496ce5e3751c4b1436' )
				: array( 'doc-71f7f3e62a4027f2314d84c508116dcfc51e08b7aae750b747d055c94fc41551', '770ccafa080cb6f4484453c976e48a44df71d7fe63bc220506c1f3e9191a75b3' );
			foreach ( $items as $index => $item ) {
				$old_key       = \Linker\Commerce\Products\Publication::revision( $item );
				$new_key       = \Linker\Commerce\Products\Publication::revision( $next_items[ $index ] );
				$before_keys[] = $old_key;
				$expected      = array(
					'document_id'     => $document[0],
					'blob_sha256'     => $document[1],
					'figure_revision' => $old_key,
				);
				if ( ( $bindings[ $old_key ] ?? null ) !== $expected ) {
					throw new RuntimeException( 'A cited FAQ no longer has its reviewed document binding.' );
				}
				$expected['figure_revision'] = $new_key;
				$next[ $new_key ]            = $expected;
			}
			if ( array_keys( $bindings ) !== $before_keys || count( $next ) !== count( $items ) ) {
				throw new RuntimeException( 'Unexpected or duplicate FAQ evidence binding.' );
			}
			$out[ $en ] = $next;
		}
		return $out;
	};
	/** Validate identities, exact paired content and the narrowly edited target. */
	$targets = static function ( array $current, string $from ) use ( $products, $digest ): array {
		if ( ! function_exists( 'pll_get_post' ) || ! function_exists( 'pll_get_post_language' ) || ! class_exists( \Linker\Commerce\Products\Faqs::class ) ) {
			throw new RuntimeException( 'Polylang and native FAQs are required.' );
		}
		$out = array();
		foreach ( $products as $en => $entry ) {
			list( $de, $slug, $sku, $index, $old_hash, $new_hash, $replacements ) = $entry;
			$product = wc_get_product( $en );
			$en_pair = (int) pll_get_post( $en, 'de' );
			$de_pair = (int) pll_get_post( $de, 'en' );
			if ( ! $product instanceof WC_Product || $slug !== $product->get_slug() || $sku !== $product->get_sku()
				|| 'publish' !== get_post_status( $en ) || 'publish' !== get_post_status( $de )
				|| 'en' !== pll_get_post_language( $en ) || 'de' !== pll_get_post_language( $de )
				|| $de !== $en_pair || $en !== $de_pair ) {
				throw new RuntimeException( 'An audited product or language pair has changed.' );
			}
			$raw           = $current[ $en ] ?? '';
			$de_raw        = $current[ $de ] ?? null;
			$expected_hash = 'old' === $from ? $old_hash : $new_hash;
			if ( $raw !== $de_raw || $expected_hash !== $digest( $raw ) ) {
				throw new RuntimeException( 'A paired FAQ differs from its complete reviewed preimage.' );
			}
			$items = json_decode( $raw, true, 512, JSON_THROW_ON_ERROR );
			if ( ! is_array( $items ) || \Linker\Commerce\Products\Faqs::encode( $items ) !== $raw || ! is_string( $items[ $index ]['answer_de'] ?? null ) ) {
				throw new RuntimeException( 'The native FAQ representation changed.' );
			}
			$answer = $items[ $index ]['answer_de'];
			if ( 'new' === $from ) {
				$replacements = array_flip( $replacements );
			}
			foreach ( $replacements as $old => $new ) {
				if ( 1 !== substr_count( $answer, $old ) ) {
					throw new RuntimeException( 'A reviewed term is missing or ambiguous.' );
				}
			}
			$items[ $index ]['answer_de'] = strtr( $answer, $replacements );
			$target                       = \Linker\Commerce\Products\Faqs::encode( $items );
			if ( $digest( $target ) !== ( 'old' === $from ? $new_hash : $old_hash ) ) {
				throw new RuntimeException( 'A corrected FAQ differs from its reviewed target.' );
			}
			$out[ $en ] = $target;
		}
		return $out;
	};

	$started     = false;
	$commit      = false;
	$touched     = false;
	$failure     = null;
	$receipt     = null;
	$guard       = null;
	$reconnects  = null;
	$report_mode = null;
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
				throw new RuntimeException( 'Database connection changed during the FAQ transaction.' );
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
			foreach ( array( $wpdb->posts, $wpdb->postmeta ) as $table ) {
				if ( 'InnoDB' !== $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $table ) ) ) {
					throw new RuntimeException( 'Transactional post storage is required.' );
				}
			}
			if ( false === $wpdb->query( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' ) || false === $wpdb->query( 'START TRANSACTION' ) ) {
				throw new RuntimeException( 'Cannot start the guarded transaction.' );
			}
			$started = true;
			$query   = $wpdb->prepare( "SELECT ID FROM {$wpdb->posts} WHERE ID IN (%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d) ORDER BY ID FOR UPDATE", ...$ids ); // phpcs:ignore WordPress.DB.PreparedSQLPlaceholders.ReplacementsWrongNumber -- Fourteen fixed IDs are unpacked.
			$locked  = $wpdb->get_col( $query ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- Prepared above.
			if ( array_map( 'intval', $locked ) !== $ids ) {
				throw new RuntimeException( 'An audited product no longer exists.' );
			}
			$query = $wpdb->prepare( "SELECT meta_id FROM {$wpdb->postmeta} WHERE post_id IN (%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d) ORDER BY meta_id FOR UPDATE", ...$ids ); // phpcs:ignore WordPress.DB.PreparedSQLPlaceholders.ReplacementsWrongNumber -- Fourteen fixed IDs are unpacked.
			$wpdb->get_col( $query ); // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared -- Prepared above.
			if ( '' !== $wpdb->last_error ) {
				throw new RuntimeException( 'Could not lock product metadata.' );
			}
		}
		$before = $faqs();
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
		}
		$first = array_key_first( $products );
		if ( ! isset( $before[ $first ] ) ) {
			throw new RuntimeException( 'The first audited FAQ is missing.' );
		}
		$from         = $digest( $before[ $first ] ) === $products[ $first ][4] ? 'old' : 'new';
		$next         = $targets( $before, $from );
		$binding_next = $binding_targets( $before, $next, $from );
		if ( 'plan' === $action ) {
			WP_CLI::log(
				(string) wp_json_encode(
					array(
						'site'     => $home,
						'action'   => $action,
						'state'    => $from,
						'products' => array_keys( $products ),
					)
				)
			);
			return;
		}
		if ( ( 'apply' === $action && 'old' !== $from ) || ( 'rollback' === $action && 'new' !== $from ) ) {
			throw new RuntimeException( 'The requested operation does not match its exact preimage.' );
		}
		$other_before = $protected();
		foreach ( $products as $en => $entry ) {
			if ( ! isset( $before[ $en ] ) ) {
				throw new RuntimeException( 'An audited FAQ preimage is missing.' );
			}
			$touched = true;
			if ( ! update_post_meta( $en, \Linker\Commerce\Products\Faqs::META_KEY, wp_slash( $next[ $en ] ), $before[ $en ] ) ) {
				throw new RuntimeException( 'A native FAQ update failed.' );
			}
			\Linker\Commerce\Products\Faqs::mirror_to_twin( $en, $next[ $en ] );
		}
		if ( 'rollback' === $action ) {
			foreach ( array_keys( $products ) as $en ) {
				if ( ! delete_post_meta( $en, '_linker_faqs_managed', '1' ) ) {
					throw new RuntimeException( 'Could not restore the original FAQ management state.' );
				}
			}
		}
		$after = $faqs();
		foreach ( $products as $en => $entry ) {
			if ( ( $after[ $en ] ?? null ) !== $next[ $en ] || ( $after[ $entry[0] ] ?? null ) !== $next[ $en ] ) {
				throw new RuntimeException( 'Paired FAQ readback differs.' );
			}
			clean_post_cache( $en );
			$binding_rows = get_post_meta( $en, '_linker_publication_faqs', false );
			$managed      = get_post_meta( $en, '_linker_faqs_managed', false );
			if ( array( $binding_next[ $en ] ) !== $binding_rows || ( 'apply' === $action ? array( '1' ) : array() ) !== $managed ) {
				throw new RuntimeException( 'Native FAQ evidence binding or management readback differs.' );
			}
		}
		if ( $protected() !== $other_before ) {
			throw new RuntimeException( 'An unrelated post or metadata field changed.' );
		}
		$commit = true;
		if ( false === $wpdb->query( 'COMMIT' ) ) {
			throw new RuntimeException( 'Commit result is unknown; inspect all paired FAQs before any retry.' );
		}
		$started = false;
		$receipt = array(
			'site'      => $home,
			'action'    => $action,
			'before'    => array_map( $digest, $before ),
			'after'     => array_map( $digest, $after ),
			'bindings'  => $binding_next,
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
				wp_cache_delete( $id, 'posts' );
				wp_cache_delete( $id, 'post_meta' );
			}
		}
		$failure = $commit || $rollback_failed
			? 'Transaction outcome is unknown; independently read all paired FAQs before retry or rollback.'
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
		foreach ( $ids as $id ) {
			clean_post_cache( $id );
			wc_delete_product_transients( $id );
		}
		WP_CLI::log( (string) wp_json_encode( $receipt ) );
	}
} )( $args ?? array() );
