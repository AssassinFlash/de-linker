<?php
/**
 * Guarded, receipt-backed correction of two shared SAJ document titles.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;
try {
	( static function ( string $payload ): void {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- The companion CLI transports JSON as a base64 argument.
		$decoded = base64_decode( $payload, true );
		if ( false === $decoded ) {
			throw new RuntimeException( 'Invalid request encoding.' );
		}
		$request = json_decode( $decoded, true, 512, JSON_THROW_ON_ERROR );
		$action  = $request['action'] ?? '';
		$target  = $request['target'] ?? '';
		$site    = untrailingslashit( home_url() );
		if ( ! in_array( $action, array( 'preview', 'apply', 'inspect', 'verify', 'rollback' ), true ) || ! in_array( $target, array( 'local', 'production' ), true ) || ( 'local' === $target && 'http://127.0.0.1:9347' !== $site ) || ( 'production' === $target && 'https://de-linker.com' !== $site ) ) {
			throw new RuntimeException( 'Unexpected action or target site.' );
		}
		global $wpdb;
		$lock = 'linker-hs3-' . substr( hash( 'sha256', $site ), 0, 32 );
		if ( '1' !== (string) $wpdb->get_var( $wpdb->prepare( 'SELECT GET_LOCK(%s, 0)', $lock ) ) ) {
			throw new RuntimeException( 'HS3 migration lock is unavailable.' );
		}
		try {
			if ( ! is_callable( array( '\\Linker\\Commerce\\Products\\Materials', 'localized_document_title' ) ) ) {
				throw new RuntimeException( 'The German document title consumer is unavailable.' );
			}
			$pairs         = array(
				1185 => array( 6833, 12, 'DLK-SAJ-HS312KT2WP' ),
				1186 => array( 6832, 6, 'DLK-SAJ-HS36KT2WP' ),
				1187 => array( 6831, 8, 'DLK-SAJ-HS38KT2WP' ),
				2198 => array( 6730, 5, 'DLK-SAJ-HS35KT2WP' ),
				2199 => array( 6729, 10, 'DLK-SAJ-HS310KT2WP' ),
			);
			$defs          = array(
				array(
					'id'    => 'doc-77669d4a1e6c821e1f1909c3b2309da96f0241565072952e68d6ec5499797411',
					'sha'   => '43d6efd869b4c66f485eb40f602e369d95a47665f33fb6330607a99884012479',
					'url'   => 'https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_BU3_BC3-TV_EU-Declaration-of-Conformity_V2.pdf',
					'type'  => 'certificate',
					'lang'  => 'EN/DE',
					'role'  => 'certificate',
					'title' => 'SAJ HS3, BU3 and BC3-TV EU Declaration of Conformity (Multilingual)',
					'de'    => 'SAJ HS3, BU3 und BC3-TV EU-Konformitätserklärung (mehrsprachig)',
				),
				array(
					'id'    => 'doc-784554fad43dd1b2f49c5dc618cbe1c22a7afcb7e3451c29efe50aecbd6d4638',
					'sha'   => 'e00f9645d187c241570a4037afa6a1dd54c23cd3d41b189bc44a0e0b24e4f7b3',
					'url'   => 'https://de-linker.com/wp-content/uploads/2026/10/SAJ_HS3_5-12K-T2_Datasheet_DE.pdf',
					'type'  => 'datasheet',
					'lang'  => 'DE',
					'role'  => 'datasheet',
					'title' => 'SAJ HS3 5–12K-T2 Three-Phase Datasheet (German)',
					'de'    => 'SAJ HS3 5–12K-T2 Datenblatt für das dreiphasige System (Deutsch)',
				),
			);
			$old_title     = static function ( array $def, int $kw ): string {
				return 'certificate' === $def['type']
					? "EU declaration of conformity for the SAJ HS3 systems, several languages including English and German (names the HS3-{$kw}K-T2-W/G-PX)"
					: "SAJ HS3 5-12K three-phase datasheet, German (covers the HS3-{$kw}K-T2-W/G-PX)";
			};
			$build         = static function ( array $before, int $kw ) use ( $defs, $old_title ): array {
				if ( ! array_is_list( $before ) ) {
					throw new RuntimeException( 'Document metadata is not a native list.' );
				}
				$after = $before;
				foreach ( $defs as $def ) {
					$found = 0;
					foreach ( $after as &$row ) {
						if ( is_array( $row ) && ( $row['url'] ?? null ) === $def['url'] ) {
							if ( ( $row['title'] ?? null ) !== $old_title( $def, $kw ) || ( $row['type'] ?? null ) !== $def['type'] || ( $row['lang'] ?? null ) !== $def['lang'] || ( $row['role'] ?? null ) !== $def['role'] ) {
								throw new RuntimeException( 'A reviewed document title, URL, type, language or role differs.' );
							}
							$row['title'] = $def['title'];
							++$found;
						}
					}
					unset( $row );
					if ( 1 !== $found ) {
						throw new RuntimeException( 'Expected exactly one row for each reviewed document.' );
					}
				}
				return $after;
			};
			$option        = static function (): array {
				global $wpdb;
				$row = $wpdb->get_row( $wpdb->prepare( "SELECT option_id, option_value FROM {$wpdb->options} WHERE option_name=%s", 'linker_de_document_titles' ), ARRAY_A );
				if ( ! is_array( $row ) || ! is_array( maybe_unserialize( $row['option_value'] ) ) ) {
					throw new RuntimeException( 'The German title option is missing or invalid.' );
				}
				return array(
					'id'  => (int) $row['option_id'],
					'raw' => $row['option_value'],
				);
			};
			$option_after  = static function ( string $raw ) use ( $defs, $pairs, $old_title ): string {
				$map = maybe_unserialize( $raw );
				if ( ! is_array( $map ) ) {
					throw new RuntimeException( 'Invalid German title preimage.' );
				}
				foreach ( $defs as $def ) {
					if ( array_key_exists( $def['title'], $map ) ) {
						throw new RuntimeException( 'A new German title key already exists.' );
					}
					foreach ( $pairs as $pair ) {
						$key = $old_title( $def, $pair[1] );
						if ( ! array_key_exists( $key, $map ) || ! is_string( $map[ $key ] ) || '' === $map[ $key ] ) {
							throw new RuntimeException( 'An original German title mapping is missing.' );
						}
					}
					$map[ $def['title'] ] = $def['de'];
				}
				return maybe_serialize( $map );
			};
			$read_products = static function () use ( $pairs ): array {
				$records = array();
				foreach ( $pairs as $id => $pair ) {
					list( $de, $kw, $sku ) = $pair;
					wp_cache_delete( $id, 'post_meta' );
					if ( ! function_exists( 'pll_get_post' ) || 'publish' !== get_post_status( $id ) || 'publish' !== get_post_status( $de ) || pll_get_post( $id, 'en' ) !== $id || pll_get_post( $id, 'de' ) !== $de || pll_get_post( $de, 'en' ) !== $id || pll_get_post( $de, 'de' ) !== $de || 'en' !== pll_get_post_language( $id ) || 'de' !== pll_get_post_language( $de ) || get_post_meta( $id, '_sku', true ) !== $sku || get_post_meta( $id, '_linker_documents_managed', false ) !== array( '1' ) ) {
						throw new RuntimeException( "Product $id identity, status, language pair or document authority changed." ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Fixed numeric product ID in a CLI error.
					}
					$all = get_post_meta( $id, '_linker_documents', false );
					if ( 1 !== count( $all ) || ! is_array( $all[0] ) ) {
						throw new RuntimeException( "Product $id document metadata is missing or duplicated." ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Fixed numeric product ID in a CLI error.
					}
					$records[ $id ] = $all[0];
				}
				return $records;
			};
			$relations     = static function () use ( $defs, $pairs ): array {
				global $wpdb;
				$result = array();
				foreach ( $defs as $def ) {
					$rows = $wpdb->get_results( $wpdb->prepare( "SELECT post_id, meta_id FROM {$wpdb->postmeta} WHERE meta_key='_linker_documents' AND meta_value LIKE %s ORDER BY post_id, meta_id", '%' . $wpdb->esc_like( $def['url'] ) . '%' ), ARRAY_A );
					if ( ! is_array( $rows ) || array_map( 'intval', array_column( $rows, 'post_id' ) ) !== array_keys( $pairs ) ) {
						throw new RuntimeException( 'Raw document associations differ from the five reviewed products.' );
					}
					$result[ $def['id'] ] = $rows;
				}
				return $result;
			};
			$authority     = static function () use ( $defs, $pairs, $site ): array {
				foreach ( $defs as $def ) {
					$file         = \Linker\Commerce\Products\Publication\DocumentFiles::resolve( $def['url'] );
					$expected_url = $site . substr( $def['url'], strlen( 'https://de-linker.com' ) );
					if ( null === $file || $file['url'] !== $expected_url || $file['blob_sha256'] !== $def['sha'] || \Linker\Commerce\Products\Publication\DocumentFiles::id( $file['url'] ) !== $def['id'] ) {
						throw new RuntimeException( 'A reviewed original PDF, hosted URL or document identity changed.' );
					}
				}
				$manifest          = \Linker\Commerce\Products\Publication::manifest();
				$products          = array_column( $manifest['products'], null, 'product_id' );
				$docs              = array_column( $manifest['documents'], null, 'document_id' );
				$selected          = array();
				$product_revisions = array();
				foreach ( $pairs as $id => $pair ) {
					$p = $products[ $id ] ?? null;
					if ( ! is_array( $p ) || ( $p['locale_product_ids']['en'] ?? null ) !== $id || ( $p['locale_product_ids']['de'] ?? null ) !== $pair[0] || ! in_array( $id, $p['published_locale_ids'] ?? array(), true ) || ! in_array( $pair[0], $p['published_locale_ids'] ?? array(), true ) ) {
						throw new RuntimeException( "Product $id is absent from the current bilingual manifest." ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Fixed numeric product ID in a CLI error.
					}
					foreach ( $defs as $def ) {
						if ( ! in_array( $def['id'], $p['documents'] ?? array(), true ) ) {
							throw new RuntimeException( "Product $id is missing a reviewed manifest document." ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Fixed numeric product ID in a CLI error.
						}
					}
					foreach ( $p['documents'] as $doc_id ) {
						if ( ! isset( $docs[ $doc_id ] ) ) {
							throw new RuntimeException( 'A manifest document is missing.' );
						}
						$selected[ $doc_id ] = $docs[ $doc_id ];
					}
					$product_revisions[ $id ] = $p['product_revision'];
					unset( $p['product_revision'], $p['ready'] );
					$products[ $id ] = $p;
				}
				$products = array_intersect_key( $products, $pairs );
				ksort( $selected );
				$target_display = array();
				foreach ( $defs as $def ) {
					$d            = $selected[ $def['id'] ] ?? null;
					$expected_url = $site . substr( $def['url'], strlen( 'https://de-linker.com' ) );
					if ( ! is_array( $d ) || $d['blob_sha256'] !== $def['sha'] || $d['url'] !== $expected_url || array_keys( $pairs ) !== $d['product_ids'] || $d['type'] !== $def['type'] || $d['lang'] !== $def['lang'] || $d['role'] !== $def['role'] ) {
						throw new RuntimeException( 'Manifest document identity, role or complete product associations changed.' );
					}
					$target_display[ $def['id'] ] = array(
						'title'             => $d['title'],
						'document_revision' => $d['document_revision'],
						'title_de'          => $d['title_de'] ?? null,
					);
					unset( $selected[ $def['id'] ]['title'], $selected[ $def['id'] ]['title_de'], $selected[ $def['id'] ]['document_revision'] );
				}
				return array(
					'source_revision'   => $manifest['source_revision'],
					'products'          => $products,
					'documents'         => $selected,
					'target_display'    => $target_display,
					'product_revisions' => $product_revisions,
				);
			};
			$current       = $read_products();
			$loc           = $option();
			$links         = $relations();
			$auth          = $authority();
			if ( in_array( $action, array( 'preview', 'apply', 'rollback' ), true ) ) {
				// A title change changes the document revision. Do not invalidate
				// existing engineering claims bound to either current document.
				$bindings = $wpdb->get_results(
					$wpdb->prepare(
						"SELECT meta_id FROM {$wpdb->postmeta} WHERE meta_key IN (%s, %s, %s) AND (meta_value LIKE %s OR meta_value LIKE %s) LIMIT 1",
						'_linker_installation_facts',
						'_linker_package_contents',
						'_linker_compatibility_claims',
						'%' . $wpdb->esc_like( $defs[0]['id'] ) . '%',
						'%' . $wpdb->esc_like( $defs[1]['id'] ) . '%'
					),
					ARRAY_A
				);
				if ( '' !== $wpdb->last_error || ! is_array( $bindings ) || array() !== $bindings ) {
					throw new RuntimeException( 'A reviewed document is bound to engineering metadata, or the binding check failed.' );
				}
			}
			if ( 'preview' === $action ) {
				$products = array();
				foreach ( $pairs as $id => $pair ) {
					$products[ $id ] = array(
						'de'     => $pair[0],
						'sku'    => $pair[2],
						'before' => $current[ $id ],
						'after'  => $build( $current[ $id ], $pair[1] ),
					);
				}
				foreach ( $defs as $def ) {
					$valid = array_map( static fn ( array $pair ): string => $old_title( $def, $pair[1] ), array_values( $pairs ) );
					if ( ! in_array( $auth['target_display'][ $def['id'] ]['title'], $valid, true ) ) {
						throw new RuntimeException( 'Manifest title does not match a reviewed original row.' );
					}
				}
				$receipt = array(
					'schema_version'           => 1,
					'scope'                    => 'hs3-document-titles-v1',
					'site'                     => $site,
					'action'                   => 'preview',
					'source_revision'          => $auth['source_revision'],
					'target_display_before'    => $auth['target_display'],
					'product_revisions_before' => $auth['product_revisions'],
					'products'                 => $products,
					'relations'                => $links,
					'authority'                => array(
						'products'  => $auth['products'],
						'documents' => $auth['documents'],
					),
					'option'                   => array(
						'id'            => $loc['id'],
						'before_base64' => base64_encode( $loc['raw'] ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Preserve serialized option bytes in the CLI receipt.
						'after_base64'  => base64_encode( $option_after( $loc['raw'] ) ), // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Preserve serialized option bytes in the CLI receipt.
					),
					'title_changes'            => array_map(
						static fn ( array $d ): array => array(
							'document_id' => $d['id'],
							'en'          => $d['title'],
							'de'          => $d['de'],
						),
						$defs
					),
				);
				$result  = $receipt;
			} else {
				$receipt = $request['receipt'] ?? null;
				if ( ! is_array( $receipt ) || 1 !== ( $receipt['schema_version'] ?? null ) || 'hs3-document-titles-v1' !== ( $receipt['scope'] ?? null ) || 'preview' !== ( $receipt['action'] ?? null ) || ( $receipt['site'] ?? null ) !== $site || ! is_array( $receipt['products'] ?? null ) || array_keys( $receipt['products'] ) !== array_keys( $pairs ) || ( $receipt['relations'] ?? null ) !== $links || ( $receipt['authority'] ?? null ) !== array(
					'products'  => $auth['products'],
					'documents' => $auth['documents'],
				) ) {
					throw new RuntimeException( 'Receipt identity, associated products or manifest fields changed.' );
				}
				$before_option = base64_decode( $receipt['option']['before_base64'] ?? '', true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Recover the receipt's serialized option preimage.
				$after_option  = base64_decode( $receipt['option']['after_base64'] ?? '', true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Recover the receipt's serialized option postimage.
				if ( false === $before_option || false === $after_option || $after_option !== $option_after( $before_option ) || ( $receipt['option']['id'] ?? null ) !== $loc['id'] ) {
					throw new RuntimeException( 'German title receipt is invalid.' );
				}
				foreach ( $pairs as $id => $pair ) {
					$r = $receipt['products'][ $id ];
					if ( ! is_array( $r ) || $r['de'] !== $pair[0] || $r['sku'] !== $pair[2] || ! is_array( $r['before'] ) || $build( $r['before'], $pair[1] ) !== $r['after'] ) {
						throw new RuntimeException( "Product $id receipt is invalid or changes unrelated fields." );
					}
				}
				$states_for = static function () use ( $read_products, $option, $receipt, $pairs, $before_option, $after_option ): array {
					$now    = $read_products();
					$map    = $option();
					$states = array();
					foreach ( $pairs as $id => $pair ) {
						$r                      = $receipt['products'][ $id ];
						$states[ (string) $id ] = $now[ $id ] === $r['before'] ? 'before' : ( $now[ $id ] === $r['after'] ? 'after' : 'conflict' );
					}
					$states['german_titles'] = $map['id'] !== $receipt['option']['id'] ? 'conflict' : ( $map['raw'] === $before_option ? 'before' : ( $map['raw'] === $after_option ? 'after' : 'conflict' ) );
					return $states;
				};
				$states     = $states_for();
				if ( 'inspect' !== $action && in_array( 'conflict', $states, true ) ) {
					throw new RuntimeException( 'At least one field conflicts with both receipt states: ' . wp_json_encode( $states ) );
				}
				if ( in_array( $action, array( 'apply', 'rollback' ), true ) ) {
					$wanted       = 'apply' === $action ? 'after' : 'before';
					$write_option = static function () use ( $option, $before_option, $after_option, $wanted, $receipt ): void {
						global $wpdb;
						$now  = $option();
						$to   = 'after' === $wanted ? $after_option : $before_option;
						$from = 'after' === $wanted ? $before_option : $after_option;
						if ( $now['id'] !== $receipt['option']['id'] ) {
							throw new RuntimeException( 'German title option identity changed; inspect the receipt.' );
						}
						if ( $now['raw'] === $to ) {
							return;
						}
						if ( $now['raw'] !== $from || 1 !== $wpdb->query( $wpdb->prepare( "UPDATE {$wpdb->options} SET option_value=%s WHERE option_id=%d AND option_name=%s AND BINARY option_value=BINARY %s", $to, $now['id'], 'linker_de_document_titles', $from ) ) ) {
							throw new RuntimeException( 'German title option CAS failed; inspect the receipt.' );
						}
						wp_cache_delete( 'linker_de_document_titles', 'options' );
						wp_cache_delete( 'alloptions', 'options' );
						wp_cache_delete( 'notoptions', 'options' );
						if ( $option()['raw'] !== $to ) {
							throw new RuntimeException( 'German title option readback failed; inspect the receipt.' );
						}
					};
					// Install the translations first; restore them only after all rows are restored.
					if ( 'apply' === $action ) {
						$write_option();
					}
					foreach ( $pairs as $id => $pair ) {
						$states = $states_for();
						if ( in_array( 'conflict', $states, true ) ) {
							throw new RuntimeException( 'A field changed during migration: ' . wp_json_encode( $states ) );
						}
						if ( $states[ (string) $id ] === $wanted ) {
							continue;
						}
						$from = $receipt['products'][ $id ][ 'after' === $wanted ? 'before' : 'after' ];
						$to   = $receipt['products'][ $id ][ $wanted ];
						if ( ! update_post_meta( $id, '_linker_documents', wp_slash( $to ), $from ) ) {
							throw new RuntimeException( "Product $id CAS failed; inspect the receipt." );
						}
						wp_cache_delete( $id, 'post_meta' );
						wc_delete_product_transients( $id );
						if ( get_post_meta( $id, '_linker_documents', false ) !== array( $to ) ) {
							throw new RuntimeException( "Product $id readback failed; inspect the receipt." );
						}
					}
					if ( 'rollback' === $action ) {
						$states = $states_for();
						if ( in_array( 'conflict', $states, true ) ) {
							throw new RuntimeException( 'A field changed during rollback: ' . wp_json_encode( $states ) );
						}
						$write_option();
					}
					$states = $states_for();
				}
				if ( 'inspect' !== $action ) {
					$expected = 'rollback' === $action ? 'before' : 'after';
					if ( array_unique( array_values( $states ) ) !== array( $expected ) ) {
						throw new RuntimeException( 'Final receipt state is incomplete: ' . wp_json_encode( $states ) );
					}
					$fresh = $authority();
					if ( ( $receipt['authority'] ?? null ) !== array(
						'products'  => $fresh['products'],
						'documents' => $fresh['documents'],
					) || $relations() !== $links ) {
						throw new RuntimeException( 'Final manifest or associations changed; inspect the receipt.' );
					}
					if ( 'after' === $expected ) {
						foreach ( $defs as $def ) {
							if ( $fresh['target_display'][ $def['id'] ]['title'] !== $def['title'] || \Linker\Commerce\Products\Materials::localized_document_title( $def['title'], true ) !== $def['de'] ) {
								throw new RuntimeException( 'Final English or German document title readback failed.' );
							}
						}
					}
					$auth = $fresh;
				}
				$result = array(
					'action'            => $action,
					'states'            => $states,
					'source_revision'   => $auth['source_revision'],
					'target_display'    => $auth['target_display'],
					'product_revisions' => $auth['product_revisions'],
				);
			}
			echo '@@548-hs3-titles@@' . wp_json_encode( $result, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
		} finally {
			$wpdb->get_var( $wpdb->prepare( 'SELECT RELEASE_LOCK(%s)', $lock ) );
		}
	} )( '548-hs3-titles-payload' );
} catch ( Throwable $error ) {
	WP_CLI::error( $error->getMessage() );
}
