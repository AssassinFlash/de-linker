<?php
/**
 * Receipt-backed correction of the four bilingual CB2 quick-guide titles.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;
( static function ( string $payload ): void {
		$decoded = base64_decode( $payload, true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Private CLI request.
	if ( false === $decoded ) {
		throw new RuntimeException( 'Invalid request encoding.' );
	}
		$request = json_decode( $decoded, true, 512, JSON_THROW_ON_ERROR );
		$action  = $request['action'] ?? '';
		$target  = $request['target'] ?? '';
		$site    = untrailingslashit( home_url() );
	if ( ! in_array( $action, array( 'preview', 'apply', 'inspect', 'verify', 'rollback' ), true ) || ! in_array( $target, array( 'local', 'production' ), true ) || ( 'local' === $target && 'http://127.0.0.1:9347' !== $site ) || ( 'production' === $target && 'https://de-linker.com' !== $site ) ) {
		throw new RuntimeException( 'Unexpected action or site.' );
	}
		global $wpdb;
		$lock = 'linker-cb2-' . substr( hash( 'sha256', $site ), 0, 32 );
	if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) ) {
		throw new RuntimeException( 'Document title migration lock unavailable.' );
	}
	try {
		$pairs            = array(
			4103 => array( 6632, '57.3', 'DLK-SAJ-CB2573HV5' ),
			4104 => array( 6631, '71.6', 'DLK-SAJ-CB2716HV5' ),
			4105 => array( 6630, '85.9', 'DLK-SAJ-CB2859HV5' ),
			4106 => array( 6629, '100.3', 'DLK-SAJ-CB21003HV5' ),
		);
		$keys             = array( '_tv_legacy_acf_json', '_linker_de_acf_json', '_linker_de_source_acf_json' );
		$doc              = 'doc-74c741e3ff765006ebff2c089f627bf1ff20b13c12b991ec9047f100e3ec87fd';
		$sha              = 'a70cb4c39824185fb9f570a59f4966c54ec94a33c870d00c7ccd756393321dac';
		$url              = 'https://de-linker.com/wp-content/uploads/2026/10/SAJ_CB2_57.3-100.3-HV5_Quick-Installation-Guide_EN.pdf';
		$new_en           = 'SAJ CB2-(57.3K-100.3K)-HV5 quick installation guide (English)';
		$new_de           = 'SAJ CB2-(57.3K-100.3K)-HV5 Kurzanleitung zur Installation (englisches Original)';
		$changed          = static function ( string $raw, string $key, string $model ) use ( $new_en, $new_de ): string {
			$data = json_decode( $raw, true, 512, JSON_THROW_ON_ERROR );
			$row  = $data['downloads'][3] ?? null;
			$old  = '_linker_de_acf_json' === $key ? "SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-{$model}-HV5)" : "SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-{$model}-HV5)";
			if ( ! is_array( $row ) || ( $row['download_file'] ?? null ) !== 6337 || ( $row['download_title'] ?? null ) !== $old || ( $row['download_role'] ?? null ) !== 'manual' || ( $row['download_language'] ?? null ) !== 'EN' ) {
				throw new RuntimeException( 'Reviewed attachment, title or role differs.' );
			}
			$data['downloads'][3]['download_title'] = '_linker_de_acf_json' === $key ? $new_de : $new_en;
			return (string) wp_json_encode( $data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		};
			$read_option  = static function (): array {
				global $wpdb;
				$row = $wpdb->get_row( $wpdb->prepare( "SELECT option_id,option_value FROM {$wpdb->options} WHERE option_name=%s", 'linker_de_document_titles' ), ARRAY_A );
				if ( ! is_array( $row ) || ! is_array( maybe_unserialize( $row['option_value'] ) ) ) {
					throw new RuntimeException( 'German title map missing.' );
				}
				return array(
					'id'  => (int) $row['option_id'],
					'raw' => $row['option_value'],
				);
			};
			$option_after = static function ( string $raw ) use ( $new_en, $new_de, $pairs ): string {
				$map = maybe_unserialize( $raw );
				if ( ! is_array( $map ) || array_key_exists( $new_en, $map ) ) {
					throw new RuntimeException( 'German target mapping already exists.' );
				}
				foreach ( $pairs as $pair ) {
					$model  = $pair[1];
					$old_en = "SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-{$model}-HV5)";
					$old_de = "SAJ CB2 57.3-100.3-HV5 Kurzanleitung zur Installation, Englisch (gilt für den CB2-{$model}-HV5)";
					if ( ( $map[ $old_en ] ?? null ) !== $old_de ) {
						throw new RuntimeException( 'A reviewed German title mapping differs.' );
					}
				}
				$map[ $new_en ] = $new_de;
				return maybe_serialize( $map );
			};
			$read_field   = static function ( int $id, string $key ): string {
				$all = get_post_meta( $id, $key, false );
				if ( 1 !== count( $all ) || ! is_string( $all[0] ) ) {
					throw new RuntimeException( 'A reviewed product meta is absent or duplicated.' );
				}
				return $all[0];
			};
			$read         = static function () use ( $pairs, $read_field ): array {
				$out = array();
				foreach ( $pairs as $id => $pair ) {
					if ( 'publish' !== get_post_status( $id ) || 'publish' !== get_post_status( $pair[0] ) || ! function_exists( 'pll_get_post' ) || pll_get_post( $id, 'en' ) !== $id || pll_get_post( $id, 'de' ) !== $pair[0] || pll_get_post( $pair[0], 'en' ) !== $id || pll_get_post( $pair[0], 'de' ) !== $pair[0] || 'en' !== pll_get_post_language( $id ) || 'de' !== pll_get_post_language( $pair[0] ) || get_post_meta( $id, '_sku', true ) !== $pair[2] || '1' === get_post_meta( $id, '_linker_documents_managed', true ) ) {
						throw new RuntimeException( 'Product, locale, SKU or document authority changed.' );
					}
					wp_cache_delete( $id, 'post_meta' );
					$out[ $id ] = array(
						'_tv_legacy_acf_json'        => $read_field( $id, '_tv_legacy_acf_json' ),
						'_linker_de_acf_json'        => $read_field( $id, '_linker_de_acf_json' ),
						'_linker_de_source_acf_json' => $read_field( $id, '_linker_de_source_acf_json' ),
					);
				}
				return $out;
			};
			$authority    = static function () use ( $pairs, $doc, $sha, $url, $site, $new_en ): array {
				$file = \Linker\Commerce\Products\Publication\DocumentFiles::resolve( $url );
				if ( ! is_array( $file ) || $file['blob_sha256'] !== $sha || $file['url'] !== $site . substr( $url, strlen( 'https://de-linker.com' ) ) || \Linker\Commerce\Products\Publication\DocumentFiles::id( $file['url'] ) !== $doc ) {
					throw new RuntimeException( 'Reviewed PDF identity or bytes changed.' );
				}
				$manifest = \Linker\Commerce\Products\Publication::manifest();
				$products = array_column( $manifest['products'], null, 'product_id' );
				$docs     = array_column( $manifest['documents'], null, 'document_id' );
				foreach ( $docs as $id => $other ) {
					if ( $id !== $doc && ( $other['title'] ?? null ) === $new_en ) {
						throw new RuntimeException( 'Another document already uses the proposed title.' );
					}
				}
				$d = $docs[ $doc ] ?? null;
				if ( ! is_array( $d ) || $d['blob_sha256'] !== $sha || array_keys( $pairs ) !== $d['product_ids'] || 'manual' !== $d['type'] || 'manual' !== $d['role'] ) {
					throw new RuntimeException( 'Manifest document or full association set changed.' );
				}
				$display = array(
					'title'    => $d['title'],
					'title_de' => $d['title_de'],
					'revision' => $d['document_revision'],
				);
				unset( $docs[ $doc ]['title'], $docs[ $doc ]['title_de'], $docs[ $doc ]['document_revision'] );
				foreach ( $pairs as $id => $pair ) {
					if ( ! isset( $products[ $id ] ) || ! in_array( $doc, $products[ $id ]['documents'], true ) ) {
						throw new RuntimeException( 'Product source association changed.' );
					}
					unset( $products[ $id ]['product_revision'], $products[ $id ]['ready'] );
				}
				$target_products = array_intersect_key( $products, $pairs );
				$target_stable   = hash( 'sha256', (string) wp_json_encode( array( $target_products, $docs[ $doc ] ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
				return array(
					'source'        => $manifest['source_revision'],
					'display'       => $display,
					'target_stable' => $target_stable,
					'stable'        => hash( 'sha256', (string) wp_json_encode( array( $products, $docs, $manifest['compatibility_revision'], $manifest['model_identity_revision'] ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) ),
				);
			};
			$unbound      = static function () use ( $doc ): void {
				global $wpdb;
				$rows = $wpdb->get_results( $wpdb->prepare( "SELECT meta_id FROM {$wpdb->postmeta} WHERE meta_key IN (%s,%s,%s) AND meta_value LIKE %s LIMIT 1", '_linker_installation_facts', '_linker_package_contents', '_linker_compatibility_claims', '%' . $wpdb->esc_like( $doc ) . '%' ), ARRAY_A );
				if ( '' !== $wpdb->last_error || ! is_array( $rows ) || array() !== $rows ) {
					throw new RuntimeException( 'Document is bound to an engineering revision, or binding check failed.' );
				}
			};
			$current      = $read();
			$opt          = $read_option();
			$auth         = $authority();
		if ( in_array( $action, array( 'preview', 'apply', 'rollback' ), true ) ) {
			$unbound();
		}
		if ( 'preview' === $action ) {
			$expected_titles = array_map( static fn( array $pair ): string => "SAJ CB2 57.3-100.3-HV5 quick installation guide, English (covers the CB2-{$pair[1]}-HV5)", array_values( $pairs ) );
			if ( ! in_array( $auth['display']['title'], $expected_titles, true ) ) {
				throw new RuntimeException( 'Manifest document title is not one of the reviewed rows.' );
			}
			$products = array();
			foreach ( $pairs as $id => $pair ) {
				foreach ( $keys as $key ) {
					$before                  = $current[ $id ][ $key ];
					$after                   = $changed( $before, $key, $pair[1] );
					$products[ $id ][ $key ] = array(
						'before'        => $before,
						'after'         => $after,
						'before_sha256' => hash( 'sha256', $before ),
						'after_sha256'  => hash( 'sha256', $after ),
					);
				}
				if ( $current[ $id ]['_tv_legacy_acf_json'] !== $current[ $id ]['_linker_de_source_acf_json'] ) {
					throw new RuntimeException( 'English translation baseline is not current.' );
				}
			}
			$option_after_raw = $option_after( $opt['raw'] );
			$result           = array(
				'schema_version' => 1,
				'scope'          => 'cb2-guide-titles-v1',
				'site'           => $site,
				'action'         => 'preview',
				'authority'      => $auth,
				'products'       => $products,
				'option'         => array(
					'id'            => $opt['id'],
					'before'        => base64_encode( $opt['raw'] ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Preserve option bytes.
					'after'         => base64_encode( $option_after_raw ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Preserve option bytes.
					'before_sha256' => hash( 'sha256', $opt['raw'] ),
					'after_sha256'  => hash( 'sha256', $option_after_raw ),
				),
			); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Preserve option bytes.
		} else {
			$receipt = $request['receipt'] ?? null;
			if ( ! is_array( $receipt ) || 1 !== ( $receipt['schema_version'] ?? null ) || 'cb2-guide-titles-v1' !== ( $receipt['scope'] ?? null ) || 'preview' !== ( $receipt['action'] ?? null ) || ( $receipt['site'] ?? null ) !== $site || ( $receipt['authority']['target_stable'] ?? null ) !== $auth['target_stable'] || array_keys( $receipt['products'] ?? array() ) !== array_keys( $pairs ) ) {
				throw new RuntimeException( 'Receipt or source authority differs.' );
			}
			if ( in_array( $action, array( 'apply', 'verify' ), true ) && ( $receipt['authority']['stable'] ?? null ) !== $auth['stable'] ) {
				throw new RuntimeException( 'Other source authority changed; inspect receipt.' );
			}
			$before_opt = base64_decode( $receipt['option']['before'] ?? '', true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Recover receipt bytes.
			$after_opt  = base64_decode( $receipt['option']['after'] ?? '', true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Recover receipt bytes.
			if ( ! is_string( $before_opt ) || ! is_string( $after_opt ) || $option_after( $before_opt ) !== $after_opt || hash( 'sha256', $before_opt ) !== ( $receipt['option']['before_sha256'] ?? null ) || hash( 'sha256', $after_opt ) !== ( $receipt['option']['after_sha256'] ?? null ) || ( $receipt['option']['id'] ?? null ) !== $opt['id'] ) {
				throw new RuntimeException( 'Option receipt differs.' );
			}
			$states = array();
			foreach ( $pairs as $id => $pair ) {
				foreach ( $keys as $key ) {
					$row = $receipt['products'][ $id ][ $key ] ?? null;
					if ( ! is_array( $row ) || ! is_string( $row['before'] ?? null ) || $changed( $row['before'], $key, $pair[1] ) !== ( $row['after'] ?? null ) || hash( 'sha256', $row['before'] ) !== ( $row['before_sha256'] ?? null ) || hash( 'sha256', $row['after'] ) !== ( $row['after_sha256'] ?? null ) ) {
						throw new RuntimeException( 'Receipt changes unreviewed metadata.' );
					}
					$states[ "$id:$key" ] = $current[ $id ][ $key ] === $row['before'] ? 'before' : ( $current[ $id ][ $key ] === $row['after'] ? 'after' : 'conflict' );
				}
			}
			$states['option'] = $opt['raw'] === $before_opt ? 'before' : ( $opt['raw'] === $after_opt ? 'after' : 'conflict' );
			if ( 'inspect' !== $action && in_array( 'conflict', $states, true ) ) {
				throw new RuntimeException( 'Receipt conflicts with current state.' );
			}
			if ( 'apply' === $action && array_unique( array_values( $states ) ) === array( 'before' ) && ( $receipt['authority']['source'] ?? null ) !== $auth['source'] ) {
				throw new RuntimeException( 'The reviewed source revision changed before apply.' );
			}
			if ( in_array( $action, array( 'apply', 'rollback' ), true ) ) {
				$wanted       = 'apply' === $action ? 'after' : 'before';
				$write_option = static function () use ( $read_option, $receipt, $before_opt, $after_opt, $wanted ): void {
					global $wpdb;
					$now  = $read_option();
					$to   = 'after' === $wanted ? $after_opt : $before_opt;
					$from = 'after' === $wanted ? $before_opt : $after_opt;
					if ( $now['id'] !== $receipt['option']['id'] ) {
						throw new RuntimeException( 'Option identity changed.' );
					}
					if ( $now['raw'] === $to ) {
						return;
					}
					if ( $now['raw'] !== $from || 1 !== $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_id=%d AND option_name=%s AND BINARY option_value=BINARY %s", $to, $now['id'], 'linker_de_document_titles', $from ) ) ) {
						throw new RuntimeException( 'Option CAS failed; inspect receipt.' );
					}
					wp_cache_delete( 'linker_de_document_titles', 'options' );
					wp_cache_delete( 'alloptions', 'options' );
					wp_cache_delete( 'notoptions', 'options' );
					if ( $read_option()['raw'] !== $to ) {
						throw new RuntimeException( 'Option readback failed.' );
					}
				};
				if ( 'apply' === $action ) {
					$write_option();
				}
				foreach ( $pairs as $id => $pair ) {
					foreach ( $keys as $key ) {
						$row  = $receipt['products'][ $id ][ $key ];
						$from = $row[ 'after' === $wanted ? 'before' : 'after' ];
						$to   = $row[ $wanted ];
						$now  = get_post_meta( $id, $key, true );
						if ( $now === $to ) {
							continue;
						}
						if ( $now !== $from || ! update_post_meta( $id, $key, wp_slash( $to ), $from ) ) {
							throw new RuntimeException( 'Product CAS failed; inspect receipt.' );
						}
						wp_cache_delete( $id, 'post_meta' );
						wc_delete_product_transients( $id );
						if ( get_post_meta( $id, $key, false ) !== array( $to ) ) {
							throw new RuntimeException( 'Product readback failed.' );
						}
					}
				}
				if ( 'rollback' === $action ) {
					$write_option();
				}
				$current  = $read();
					$opt  = $read_option();
					$auth = $authority();
				if ( $auth['target_stable'] !== $receipt['authority']['target_stable'] || ( 'apply' === $action && $auth['stable'] !== $receipt['authority']['stable'] ) ) {
					throw new RuntimeException( 'Source authority changed; inspect receipt.' );
				}
				foreach ( $pairs as $id => $pair ) {
					foreach ( $keys as $key ) {
						if ( $current[ $id ][ $key ] !== $receipt['products'][ $id ][ $key ][ $wanted ] ) {
							throw new RuntimeException( 'Final product state incomplete.' );
						}
						$states[ "$id:$key" ] = $wanted;
					}
				}
				if ( ( 'after' === $wanted ? $after_opt : $before_opt ) !== $opt['raw'] ) {
					throw new RuntimeException( 'Final option state incomplete.' );
				}
					$states['option'] = $wanted;
			}
			if ( 'verify' === $action && array_unique( array_values( $states ) ) !== array( 'after' ) ) {
				throw new RuntimeException( 'Receipt is not fully applied.' );
			}
			if ( ( 'verify' === $action || 'apply' === $action ) && ( $auth['display']['title'] !== $new_en || $auth['display']['title_de'] !== $new_de || \Linker\Commerce\Products\Materials::localized_document_title( $new_en, true ) !== $new_de ) ) {
				throw new RuntimeException( 'Bilingual manifest or library title readback failed.' );
			}
			if ( 'rollback' === $action && $auth['display'] !== $receipt['authority']['display'] ) {
				throw new RuntimeException( 'Original document display revision was not restored.' );
			}
			$result = array(
				'action'    => $action,
				'states'    => $states,
				'authority' => $auth,
			);
			if ( 'rollback' === $action ) {
					$result['source_restored'] = ( $receipt['authority']['source'] ?? null ) === $auth['source'];
				$result['recovery']            = $result['source_restored'] ? 'fields_restored_source_revision_matches' : 'fields_restored_source_requires_reconcile';
			}
		}
			echo '@@548-cb2-guide-titles@@' . wp_json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
	} finally {
		$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
	}
} )( '548-cb2-guide-titles-payload' );
