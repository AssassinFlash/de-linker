<?php
/**
 * Guarded repair: German pages may show an existing reviewed document title.
 *
 * The option stores exact English string => existing German title. It does not
 * rewrite stored English wording, official titles, or number formatting.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

try {
	( static function ( string $payload ): void {
		$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport from the companion CLI.
		if ( ! is_array( $request ) || ! is_string( $request['action'] ?? null ) ) {
			throw new RuntimeException( 'Unreadable migration request.' );
		}
		$key     = \Linker\Commerce\Products\Materials::DE_DOCUMENT_TITLES;
		$site    = home_url();
		$read    = static function () use ( $key ) {
			global $wpdb;
			$found = $wpdb->get_var( $wpdb->prepare( "SELECT option_value FROM {$wpdb->options} WHERE option_name = %s", $key ) );
			if ( ! is_string( $found ) ) {
				return null;
			}
			$value = maybe_unserialize( $found );
			return is_array( $value ) ? $value : null;
		};
		$plan    = static function () use ( $site ): array {
			$editorial = static function ( string $title ): bool {
				return 1 === preg_match( '/names the|covers the|including English|German and English/i', $title );
			};
			$file_of   = static function ( string $url ): string {
				return strtolower( rawurldecode( basename( (string) wp_parse_url( $url, PHP_URL_PATH ) ) ) );
			};
			$by_file   = static function ( int $id, string $meta ) use ( $file_of ): array {
				$raw  = get_post_meta( $id, $meta, true );
				$data = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
				$out  = array();
				$rows = is_array( $data ) && is_array( $data['downloads'] ?? null ) ? $data['downloads'] : array();
				foreach ( $rows as $row ) {
					if ( ! is_array( $row ) ) {
						continue;
					}
					$url = wp_get_attachment_url( (int) ( $row['download_file'] ?? 0 ) );
					if ( ! is_string( $url ) || '' === $url ) {
						continue;
					}
					$file  = $file_of( $url );
					$title = trim( (string) ( $row['download_title'] ?? '' ) );
					if ( isset( $out[ $file ] ) && $out[ $file ] !== $title ) {
						$out[ $file ] = false;
						continue;
					}
					$out[ $file ] = $title;
				}
				return $out;
			};
			$ids       = get_posts(
				array(
					'post_type'      => 'product',
					'post_status'    => 'publish',
					'posts_per_page' => -1,
					'fields'         => 'ids',
					'lang'           => '',
				)
			);
			$pairs     = array();
			$blockers  = array();
			$seen_live = array();
			foreach ( $ids as $id ) {
				$id = (int) $id;
				$en = $by_file( $id, '_tv_legacy_acf_json' );
				$de = $by_file( $id, '_linker_de_acf_json' );
				foreach ( $en as $file => $english ) {
					if ( false === $english || '' === $english || ! $editorial( $english ) ) {
						continue;
					}
					$german = $de[ $file ] ?? '';
					if ( false === $german || ! is_string( $german ) || '' === $german || $german === $english ) {
						$blockers[ 'acf:' . $english ] = array(
							'kind'    => 'missing-reviewed-german-title',
							'english' => $english,
							'file'    => $file,
							'product' => $id,
						);
						continue;
					}
					$pairs[ $english ]['de'][ $german ]   = true;
					$pairs[ $english ]['files'][ $file ]  = true;
					$pairs[ $english ]['products'][ $id ] = true;
				}
				$docs = get_post_meta( $id, '_linker_documents', true );
				$docs = is_string( $docs ) ? json_decode( $docs, true ) : $docs;
				foreach ( is_array( $docs ) ? $docs : array() as $row ) {
					if ( ! is_array( $row ) ) {
						continue;
					}
					$title = trim( (string) ( $row['title'] ?? '' ) );
					$file  = $file_of( (string) ( $row['url'] ?? '' ) );
					if ( 'chint dtsu666 catalog en' === $title ) {
						$german = $de[ $file ] ?? '';
						if ( ! is_string( $german ) || '' === $german || false === $german ) {
							$blockers[ 'catalog:' . $file ] = array(
								'kind'    => 'catalog-title-without-reviewed-german',
								'english' => $title,
								'file'    => $file,
								'product' => $id,
							);
						} else {
							$pairs[ $title ]['de'][ $german ]   = true;
							$pairs[ $title ]['files'][ $file ]  = true;
							$pairs[ $title ]['products'][ $id ] = true;
						}
					}
					if ( $editorial( $title ) ) {
						$seen_live[ $title ] = true;
					}
				}
				$faqs = get_post_meta( $id, '_linker_faqs', true );
				$faqs = is_string( $faqs ) ? json_decode( $faqs, true ) : $faqs;
				foreach ( is_array( $faqs ) ? $faqs : array() as $faq ) {
					$title = trim( (string) ( is_array( $faq ) ? ( $faq['citation']['title'] ?? '' ) : '' ) );
					if ( $editorial( $title ) ) {
						$seen_live[ $title ] = true;
					}
				}
			}
			$map = array();
			foreach ( $pairs as $english => $pair ) {
				$germans = array_keys( $pair['de'] );
				if ( 1 !== count( $germans ) ) {
					throw new RuntimeException( 'Refusing ambiguous reviewed German title for: ' . esc_html( $english ) );
				}
				$map[ $english ] = $germans[0];
				unset( $blockers[ 'acf:' . $english ] );
			}
			ksort( $map );
			foreach ( array_keys( $seen_live ) as $english ) {
				if ( ! isset( $map[ $english ] ) ) {
					$blockers[ 'live:' . $english ] = array(
						'kind'    => 'rendered-english-description-without-reviewed-german',
						'english' => $english,
					);
				}
			}
			ksort( $blockers );
			return array(
				'site'     => $site,
				'map'      => $map,
				'evidence' => array_map(
					static function ( string $english ) use ( $pairs, $map ): array {
						return array(
							'english'  => $english,
							'german'   => $map[ $english ],
							'files'    => array_keys( $pairs[ $english ]['files'] ),
							'products' => count( $pairs[ $english ]['products'] ),
						);
					},
					array_keys( $map )
				),
				'blockers' => array_values( $blockers ),
			);
		};
		$current = $read();
		if ( 'plan' === $request['action'] ) {
			$built = $plan();
			echo '@@de-document-descriptions@@' . wp_json_encode(
				array(
					'site'     => $site,
					'before'   => $current,
					'map'      => $built['map'],
					'evidence' => $built['evidence'],
					'blockers' => $built['blockers'],
					'changes'  => $current === $built['map'] ? 0 : 1,
				)
			);
			return;
		}
		$receipt = $request['receipt'] ?? null;
		if ( ! is_array( $receipt ) || ( $receipt['site'] ?? null ) !== $site || ! is_array( $receipt['map'] ?? null ) ) {
			throw new RuntimeException( 'Receipt does not belong to this site.' );
		}
		$built = $plan();
		if ( $built['map'] !== $receipt['map'] ) {
			throw new RuntimeException( 'Reviewed titles changed since the receipt was planned.' );
		}
		if ( 'verify' === $request['action'] ) {
			$ok = $current === $receipt['map'];
			echo '@@de-document-descriptions@@' . wp_json_encode(
				array(
					'site'     => $site,
					'ok'       => $ok,
					'changes'  => count( $receipt['map'] ),
					'blockers' => $built['blockers'],
				)
			);
			if ( ! $ok ) {
				throw new RuntimeException( 'Stored German document titles do not match the receipt.' );
			}
			return;
		}
		if ( 'apply' === $request['action'] ) {
			if ( $current === $receipt['map'] ) {
				echo '@@de-document-descriptions@@' . wp_json_encode(
					array(
						'site'    => $site,
						'changes' => 0,
						'action'  => 'apply',
					)
				);
				return;
			}
			if ( ( $receipt['before'] ?? null ) !== $current ) {
				throw new RuntimeException( 'The option changed after planning; refusing to overwrite it.' );
			}
			if ( ! update_option( $key, $receipt['map'], false ) && get_option( $key, null ) !== $receipt['map'] ) {
				throw new RuntimeException( 'The German document-title option was not stored.' );
			}
			echo '@@de-document-descriptions@@' . wp_json_encode(
				array(
					'site'    => $site,
					'changes' => 1,
					'action'  => 'apply',
					'titles'  => count( $receipt['map'] ),
				)
			);
			return;
		}
		if ( 'rollback' === $request['action'] ) {
			if ( ( $receipt['before'] ?? null ) === $current ) {
				echo '@@de-document-descriptions@@' . wp_json_encode(
					array(
						'site'    => $site,
						'changes' => 0,
						'action'  => 'rollback',
					)
				);
				return;
			}
			if ( $current !== $receipt['map'] ) {
				throw new RuntimeException( 'The option no longer matches the applied receipt.' );
			}
			$before = $receipt['before'] ?? null;
			$done   = null === $before ? delete_option( $key ) : update_option( $key, $before, false );
			if ( ! $done && $read() !== $before ) {
				throw new RuntimeException( 'Rollback did not restore the previous option.' );
			}
			echo '@@de-document-descriptions@@' . wp_json_encode(
				array(
					'site'    => $site,
					'changes' => 1,
					'action'  => 'rollback',
				)
			);
			return;
		}
		throw new RuntimeException( 'Unknown migration action.' );
	} )( 'de-document-descriptions-payload' );
} catch ( Throwable $error ) {
	fwrite( STDERR, $error->getMessage() . PHP_EOL ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fwrite -- CLI error stream, not a WordPress filesystem operation.
	exit( 1 );
}
