<?php
/** Guarded HCA warranty attachment and nine exact metadata transitions. */
defined( 'ABSPATH' ) || exit;
try {
	( static function ( string $payload ): void {
		$request = json_decode( base64_decode( $payload, true ), true, 512, JSON_THROW_ON_ERROR );
		$action  = $request['action'] ?? '';
		$target  = $request['target'] ?? '';
		$site    = untrailingslashit( home_url() );
		if ( ! in_array( $action, array( 'preview', 'stage', 'apply', 'inspect', 'verify', 'rollback' ), true ) || ! in_array( $target, array( 'local', 'production' ), true ) || ( 'local' === $target && 'http://127.0.0.1:9347' !== $site ) || ( 'production' === $target && 'https://de-linker.com' !== $site ) ) {
			throw new RuntimeException( 'Unexpected action or target site.' );
		}
		global $wpdb;
		$lock = 'linker-hca-' . substr( hash( 'sha256', $site ), 0, 32 );
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) ) {
			throw new RuntimeException( 'HCA migration is already running or the database lock is unavailable.' );
		}
		try {
		$reviewed = $request['reviewed'] ?? null;
		$pairs    = array( 3557 => 6689, 3586 => 6663, 3587 => 6662 );
		if ( ! is_array( $reviewed ) || array_map( 'intval', array_keys( $reviewed ) ) !== array_keys( $pairs ) ) {
			throw new RuntimeException( 'The three reviewed product pairs are required.' );
		}
		$receipt = $request['receipt'] ?? null;
		if ( 'preview' !== $action && ( ! is_array( $receipt ) || 'hca-warranty-rev12-v1' !== ( $receipt['scope'] ?? null ) || $site !== ( $receipt['site'] ?? null ) || $reviewed !== ( $receipt['reviewed'] ?? null ) ) ) {
			throw new RuntimeException( 'Receipt, site or reviewed fields differ.' );
		}
		$old_sha  = '9f5b0d2b24306f95fe7ac1f3892a98e0b4799f99b26508c063dc88be3d75aace';
		$new_sha  = '88a8a5bd9e70bc398fe990069272526c660c1731103ff113e53f93f7fd789307';
		$old_file = get_attached_file( 6426 );
		$uploads  = wp_upload_dir( null, false );
		$old_url  = 'https://de-linker.com/wp-content/uploads/2026/10/GW_Limited-Warranty_EV-Charger_Europe.pdf';
		$relative = 'linker-hca-warranty/goodwe-ev-warranty-europe-rev-1-2-88a8a5bd9e70.pdf';
		$slug     = 'linker-hca-warranty-rev-1-2-88a8a5bd9e70';
		$path     = $uploads['basedir'] . '/' . $relative;
		$url      = $uploads['baseurl'] . '/' . $relative;
		if ( $uploads['baseurl'] !== $site . '/wp-content/uploads' ) {
			throw new RuntimeException( 'The expected hosted uploads origin changed.' );
		}
		if ( ! is_string( $old_file ) || ! is_file( $old_file ) || hash_file( 'sha256', $old_file ) !== $old_sha || 'application/pdf' !== get_post_mime_type( 6426 ) || get_post_meta( 6426, '_wp_attached_file', true ) !== '2026/10/GW_Limited-Warranty_EV-Charger_Europe.pdf' || wp_get_attachment_url( 6426 ) !== $uploads['baseurl'] . '/2026/10/GW_Limited-Warranty_EV-Charger_Europe.pdf' || ! empty( $uploads['error'] ) ) {
			throw new RuntimeException( 'The original warranty attachment changed.' );
		}
		foreach ( $pairs as $id => $de ) {
			$r = $reviewed[ $id ];
			if ( ! is_array( $r ) || ( $r['de'] ?? null ) !== $de || 'publish' !== get_post_status( $id ) || 'publish' !== get_post_status( $de ) || ! function_exists( 'pll_get_post' ) || pll_get_post( $id, 'en' ) !== $id || pll_get_post( $id, 'de' ) !== $de || pll_get_post( $de, 'en' ) !== $id || pll_get_post( $de, 'de' ) !== $de || 'en' !== pll_get_post_language( $id ) || 'de' !== pll_get_post_language( $de ) || get_post_meta( $id, '_sku', true ) !== ( $r['sku'] ?? null ) || '1' !== get_post_meta( $id, '_linker_documents_managed', true ) ) {
				throw new RuntimeException( 'Product identity, language pair or authority changed.' );
			}
		}
		$attachment = static function () use ( $path, $url, $relative, $slug, $new_sha ): int {
			global $wpdb;
			$ids = $wpdb->get_col( $wpdb->prepare( "SELECT DISTINCT ID FROM {$wpdb->posts} WHERE post_type='attachment' AND (guid=%s OR post_name=%s OR ID IN (SELECT post_id FROM {$wpdb->postmeta} WHERE meta_key='_wp_attached_file' AND meta_value=%s))", $url, $slug, $relative ) );
			if ( count( $ids ) > 1 ) {
				throw new RuntimeException( 'Multiple candidate attachments require inspection.' );
			}
			if ( ! $ids ) {
				return 0;
			}
			$id   = (int) $ids[0];
			$post = get_post( $id );
			if ( ! $post || $post->post_name !== $slug || $post->guid !== $url || 'application/pdf' !== $post->post_mime_type || ! is_file( $path ) || is_link( $path ) || hash_file( 'sha256', $path ) !== $new_sha ) {
				throw new RuntimeException( 'Existing attachment or bytes differ.' );
			}
			$file = get_post_meta( $id, '_wp_attached_file', true );
			if ( '' !== $file && $file !== $relative ) {
				throw new RuntimeException( 'Existing attachment file identity differs.' );
			}
			return $id;
		};
		$attachment_id = $attachment();
		$english_title = 'GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)';
		$german_title  = 'GoodWe Garantie für EV-Ladestationen (Europa, Rev. 1.2, englisches Original)';
		$read_locale = static function () use ( $english_title ): array {
			global $wpdb;
			$row = $wpdb->get_row( $wpdb->prepare( "SELECT option_id, option_value FROM {$wpdb->options} WHERE option_name=%s", 'linker_de_document_titles' ), ARRAY_A );
			$map = null === $row ? array() : maybe_unserialize( $row['option_value'] );
			if ( ! is_array( $map ) ) {
				throw new RuntimeException( 'German document title mapping is invalid.' );
			}
			return array( 'row' => $row, 'map' => $map, 'exists' => array_key_exists( $english_title, $map ), 'value' => $map[ $english_title ] ?? null );
		};
		$locale = $read_locale();
		$locale_before = 'preview' === $action ? array( 'option_existed' => null !== $locale['row'], 'exists' => $locale['exists'], 'value' => $locale['value'] ) : ( $receipt['locale_before'] ?? null );
		if ( ! is_array( $locale_before ) || ! is_bool( $locale_before['option_existed'] ?? null ) || ! is_bool( $locale_before['exists'] ?? null ) || ! array_key_exists( 'value', $locale_before ) ) {
			throw new RuntimeException( 'Missing exact German title preimage.' );
		}
		$locale_is_before = $locale['exists'] === $locale_before['exists'] && $locale['value'] === $locale_before['value'];
		$locale_is_after = $locale['exists'] && $locale['value'] === $german_title;
		if ( ! $locale_is_before && ! $locale_is_after ) {
			throw new RuntimeException( 'German title changed after preview.' );
		}
		$write_locale = static function ( bool $restore ) use ( $read_locale, $locale_before, $english_title, $german_title ): void {
			global $wpdb;
			$current = $read_locale();
			$is_before = $current['exists'] === $locale_before['exists'] && $current['value'] === $locale_before['value'];
			$is_after = $current['exists'] && $current['value'] === $german_title;
			if ( ! $is_before && ! $is_after ) {
				throw new RuntimeException( 'German title changed during migration.' );
			}
			$map = $current['map'];
			if ( $restore && ! $locale_before['exists'] ) {
				unset( $map[ $english_title ] );
			} else {
				$map[ $english_title ] = $restore ? $locale_before['value'] : $german_title;
			}
			if ( $map === $current['map'] ) {
				return;
			}
			if ( null === $current['row'] ) {
				if ( ! add_option( 'linker_de_document_titles', $map, '', false ) ) {
					throw new RuntimeException( 'Could not add German title mapping.' );
				}
			} elseif ( $restore && ! $locale_before['option_existed'] && ! $map ) {
				$changed = $wpdb->query( $wpdb->prepare( "DELETE FROM {$wpdb->options} WHERE option_id=%d AND BINARY option_value=BINARY %s", $current['row']['option_id'], $current['row']['option_value'] ) );
				if ( 1 !== $changed ) {
					throw new RuntimeException( 'German title option changed concurrently.' );
				}
			} else {
				$changed = $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_id=%d AND BINARY option_value=BINARY %s", maybe_serialize( $map ), $current['row']['option_id'], $current['row']['option_value'] ) );
				if ( 1 !== $changed ) {
					throw new RuntimeException( 'German title option changed concurrently.' );
				}
			}
			wp_cache_delete( 'linker_de_document_titles', 'options' );
			wp_cache_delete( 'alloptions', 'options' );
			wp_cache_delete( 'notoptions', 'options' );
		};
		$build = static function ( int $id, string $key, array $r, int $media ) use ( $old_url, $url ): array {
			if ( '_linker_documents' === $key ) {
				$before = $r['documents'] ?? null;
				if ( ! is_array( $before ) || 8 !== count( $before ) ) {
					throw new RuntimeException( 'Reviewed documents are incomplete.' );
				}
				$after = $before;
				$found = 0;
				foreach ( $after as &$row ) {
					if ( ( $row['url'] ?? null ) === $old_url ) {
						if ( 'warranty' !== ( $row['type'] ?? null ) || 'EN' !== ( $row['lang'] ?? null ) ) {
							throw new RuntimeException( 'Old policy role changed.' );
						}
						$row['url'] = $url;
						$row['title'] = 'GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)';
						++$found;
					}
				}
				unset( $row );
				if ( 1 !== $found ) {
					throw new RuntimeException( 'Expected exactly one old policy URL.' );
				}
				return array( $before, $after );
			}
			$before = $r[ '_tv_legacy_acf_json' === $key ? 'acf_en' : 'acf_de' ] ?? null;
			if ( ! is_string( $before ) ) {
				throw new RuntimeException( 'Reviewed ACF source is missing.' );
			}
			$obj = json_decode( $before, false, 512, JSON_THROW_ON_ERROR );
			if ( ! is_object( $obj ) || ! is_array( $obj->downloads ?? null ) || 8 !== count( $obj->downloads ) ) {
				throw new RuntimeException( 'Reviewed ACF downloads are incomplete.' );
			}
			$found = 0;
			foreach ( $obj->downloads as $row ) {
				if ( is_object( $row ) && 6426 === ( $row->download_file ?? null ) ) {
					if ( 'EN' !== ( $row->download_language ?? null ) ) {
						throw new RuntimeException( 'Original document language changed.' );
					}
					$row->download_file = $media;
					$row->download_type = '_tv_legacy_acf_json' === $key ? 'Warranty' : 'Garantie';
					$row->download_role = 'warranty';
					$row->download_title = '_tv_legacy_acf_json' === $key ? 'GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)' : 'GoodWe Garantie für EV-Ladestationen (Europa, Rev. 1.2, englisches Original)';
					++$found;
				}
			}
			if ( 1 !== $found ) {
				throw new RuntimeException( 'Expected exactly one original attachment in ACF.' );
			}
			return array( $before, wp_json_encode( $obj, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
		};
		$keys = array( '_linker_documents', '_tv_legacy_acf_json', '_linker_de_acf_json' );
		$states = array();
		foreach ( $pairs as $id => $de ) {
			foreach ( $keys as $key ) {
				$all = get_post_meta( $id, $key, false );
				list( $before, $after ) = $build( $id, $key, $reviewed[ $id ], $attachment_id );
				if ( 1 !== count( $all ) || ( $all[0] !== $before && ( ! $attachment_id || $all[0] !== $after ) ) ) {
					throw new RuntimeException( "Product $id field $key differs from both receipt states." );
				}
				$states[ $id . ':' . $key ] = $all[0] === $before ? 'before' : 'after';
			}
		}
		if ( 'preview' === $action ) {
			if ( array_unique( array_values( $states ) ) !== array( 'before' ) ) {
				throw new RuntimeException( 'Preview requires the reviewed before state.' );
			}
			$states['german_title'] = 'before';
			$result = array( 'scope' => 'hca-warranty-rev12-v1', 'site' => $site, 'reviewed' => $reviewed, 'locale_before' => $locale_before, 'action' => $action, 'states' => $states, 'title_change' => array( 'before' => $locale_before['value'], 'after' => $german_title ) );
		} elseif ( 'stage' === $action ) {
			$bytes = base64_decode( $request['pdf'] ?? '', true );
			if ( ! is_string( $bytes ) || 491728 !== strlen( $bytes ) || hash( 'sha256', $bytes ) !== $new_sha ) {
				throw new RuntimeException( 'PDF bytes do not match the reviewed original.' );
			}
			if ( ! wp_mkdir_p( dirname( $path ) ) || is_link( dirname( $path ) ) || is_link( $path ) ) {
				throw new RuntimeException( 'Unsafe or unavailable upload directory.' );
			}
			$partial = $path . '.partial';
			if ( ! file_exists( $path ) ) {
				if ( is_link( $partial ) ) {
					throw new RuntimeException( 'Unsafe staged partial.' );
				}
				if ( file_exists( $partial ) ) {
					$part = file_get_contents( $partial );
					if ( ! is_string( $part ) || strlen( $part ) > strlen( $bytes ) || $part !== substr( $bytes, 0, strlen( $part ) ) ) {
						throw new RuntimeException( 'Staged partial differs; inspect before retry.' );
					}
				} else {
					$part = '';
				}
				$h = fopen( $partial, file_exists( $partial ) ? 'ab' : 'xb' );
				if ( ! $h || fwrite( $h, substr( $bytes, strlen( $part ) ) ) !== strlen( $bytes ) - strlen( $part ) || ! fflush( $h ) ) {
					throw new RuntimeException( 'PDF staging failed; retain the partial for inspection.' );
				}
				fclose( $h );
				if ( hash_file( 'sha256', $partial ) !== $new_sha || ! link( $partial, $path ) || ! unlink( $partial ) ) {
					throw new RuntimeException( 'PDF staging verification failed.' );
				}
			}
			if ( ! is_file( $path ) || hash_file( 'sha256', $path ) !== $new_sha ) {
				throw new RuntimeException( 'Hosted PDF bytes differ.' );
			}
			if ( file_exists( $partial ) ) {
				if ( is_link( $partial ) || hash_file( 'sha256', $partial ) !== $new_sha || ! unlink( $partial ) ) {
					throw new RuntimeException( 'Staged partial differs; inspect before retry.' );
				}
			}
			if ( ! $attachment_id ) {
				$attachment_id = wp_insert_attachment( array( 'post_mime_type' => 'application/pdf', 'post_title' => 'GoodWe EV Charger Limited Warranty (Europe, Rev. 1.2, English)', 'post_name' => $slug, 'guid' => $url, 'post_status' => 'inherit' ), $path, 0, true );
				if ( is_wp_error( $attachment_id ) ) {
					throw new RuntimeException( 'Could not register warranty attachment.' );
				}
			}
			if ( '' === get_post_meta( $attachment_id, '_wp_attached_file', true ) ) {
				update_attached_file( $attachment_id, $path );
			}
			if ( $attachment() !== $attachment_id || get_post_meta( $attachment_id, '_wp_attached_file', true ) !== $relative || wp_get_attachment_url( $attachment_id ) !== $url ) {
				throw new RuntimeException( 'Attachment readback failed; retain the receipt.' );
			}
			$result = array( 'action' => $action, 'attachment_id' => $attachment_id, 'url' => $url, 'state' => 'staged' );
		} elseif ( 'inspect' === $action && ( ! $attachment_id || get_post_meta( $attachment_id, '_wp_attached_file', true ) !== $relative ) ) {
			$stage_state = $attachment_id ? 'attachment_incomplete' : ( is_file( $path ) ? 'file_unregistered' : ( is_file( $path . '.partial' ) ? 'partial' : 'not_started' ) );
			$states['german_title'] = $locale_is_after ? 'after' : 'before';
			$result = array( 'action' => $action, 'state' => $stage_state, 'attachment_id' => $attachment_id, 'states' => $states );
		} else {
			if ( ! $attachment_id || get_post_meta( $attachment_id, '_wp_attached_file', true ) !== $relative || wp_get_attachment_url( $attachment_id ) !== $url ) {
				throw new RuntimeException( 'The verified staged attachment is required.' );
			}
			if ( 'apply' === $action ) {
				$write_locale( false );
			}
			foreach ( $pairs as $id => $de ) {
				foreach ( $keys as $key ) {
					list( $before, $after ) = $build( $id, $key, $reviewed[ $id ], $attachment_id );
					$all     = get_post_meta( $id, $key, false );
					if ( 1 !== count( $all ) || ( $all[0] !== $before && $all[0] !== $after ) ) {
						throw new RuntimeException( "Concurrent change in $id $key; retain the receipt." );
					}
					$current = $all[0];
					$wanted  = 'rollback' === $action ? $before : $after;
					if ( ! in_array( $action, array( 'verify', 'inspect' ), true ) && $current !== $wanted ) {
						update_post_meta( $id, $key, wp_slash( $wanted ), $current );
						if ( get_post_meta( $id, $key, true ) !== $wanted ) {
							throw new RuntimeException( "CAS failed for $id $key; retain the receipt." );
						}
						$current = $wanted;
					}
					$states[ $id . ':' . $key ] = $current === $before ? 'before' : ( $current === $after ? 'after' : 'changed' );
				}
				if ( ! in_array( $action, array( 'verify', 'inspect' ), true ) ) {
					wc_delete_product_transients( $id );
				}
			}
			if ( 'rollback' === $action ) {
				$write_locale( true );
			}
			$locale = $read_locale();
			$locale_is_before = $locale['exists'] === $locale_before['exists'] && $locale['value'] === $locale_before['value'];
			$locale_is_after = $locale['exists'] && $locale['value'] === $german_title;
			$states['german_title'] = $locale_is_after ? 'after' : ( $locale_is_before ? 'before' : 'changed' );
			if ( 'inspect' !== $action ) {
				$expected = 'rollback' === $action ? 'before' : 'after';
				if ( ( 'before' === $expected && ! $locale_is_before ) || ( 'after' === $expected && ! $locale_is_after ) ) {
					throw new RuntimeException( 'German title readback failed; inspect the receipt.' );
				}
				foreach ( $pairs as $id => $de ) {
					foreach ( $keys as $key ) {
						list( $before, $after ) = $build( $id, $key, $reviewed[ $id ], $attachment_id );
						$all = get_post_meta( $id, $key, false );
						if ( 1 !== count( $all ) || $all[0] !== ( 'before' === $expected ? $before : $after ) ) {
							throw new RuntimeException( "Final $expected readback failed for $id $key; inspect the receipt." );
						}
					}
				}
			}
			$result = array( 'action' => $action, 'attachment_id' => $attachment_id, 'url' => $url, 'states' => $states );
		}
		echo '@@548-hca-warranty@@' . wp_json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
		} finally {
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
		}
	} )( '548-hca-warranty-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}
