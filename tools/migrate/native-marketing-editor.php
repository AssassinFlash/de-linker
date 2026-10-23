<?php
/**
 * Restore native LiveCanvas filtering on the two designed page families.
 *
 * Usage:
 * wp eval-file tools/migrate/native-marketing-editor.php plan
 * wp eval-file tools/migrate/native-marketing-editor.php apply STATE_SHA256
 * wp eval-file tools/migrate/native-marketing-editor.php rollback CURRENT_SHA256 BEFORE_SHA256 ADDED_IDS
 *
 * Back up the database and current four full metadata objects locally first.
 * No content, template, translation, CSS or other metadata is written here.
 *
 * @package Linker\Commerce
 */

( static function ( array $args ): void {
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		throw new RuntimeException( 'Run through WP-CLI.' );
	}

	$snapshot    = static function (): array {
		if ( ! function_exists( 'pll_get_post' ) || ! function_exists( 'lc_post_is_using_livecanvas' ) ) {
			throw new RuntimeException( 'Polylang and LiveCanvas must be active.' );
		}
		$rows  = array();
		$metas = array();
		foreach ( array(
			'utility-storage'  => 'tv-utility-page-v1',
			'services-support' => 'service-redesign',
		) as $slug => $root ) {
			$posts = get_posts(
				array(
					'name'             => $slug,
					'post_type'        => 'page',
					'post_status'      => 'publish',
					'posts_per_page'   => 2,
					'lang'             => '',
					'suppress_filters' => true,
				)
			);
			if ( count( $posts ) !== 1 || pll_get_post_language( $posts[0]->ID ) !== 'en' ) {
				throw new RuntimeException( 'Expected one published English page for each specified family.' );
			}
			$english_id = (int) $posts[0]->ID;
			$german_id  = (int) pll_get_post( $english_id, 'de' );
			if ( ! $german_id || $german_id === $english_id || (int) pll_get_post( $german_id, 'en' ) !== $english_id ) {
				throw new RuntimeException( 'Expected a reciprocal German pair for each specified family.' );
			}
			foreach ( array(
				'en' => $english_id,
				'de' => $german_id,
			) as $language => $id ) {
				$post = get_post( $id );
				if ( ! $post || 'page' !== $post->post_type || 'publish' !== $post->post_status
				|| pll_get_post_language( $id ) !== $language
				|| ! preg_match( '/\bid=([\x22\x27])' . preg_quote( $root, '/' ) . '\1/', $post->post_content )
				|| 'page-templates/empty.php' !== get_post_meta( $id, '_wp_page_template', true )
				|| '' !== get_post_meta( $id, 'lc_use_template_of_slug', true ) ) {
					throw new RuntimeException( 'Page shape or template changed in the specified families.' );
				}
				$meta = get_post_meta( $id );
				ksort( $meta );
				$values = $meta['_lc_livecanvas_enabled'] ?? array();
				if ( array() !== $values && array( '1' ) !== $values ) {
					throw new RuntimeException( 'Preserve an explicit editor choice in the specified families.' );
				}
				$pairs = pll_get_post_translations( $id );
				ksort( $pairs );
				$rows[ $id ]  = array(
					'id'               => $id,
					'language'         => $language,
					'translations'     => $pairs,
					'post_sha256'      => hash( 'sha256', wp_json_encode( $post ) ),
					'meta_sha256'      => hash( 'sha256', wp_json_encode( $meta ) ),
					'values'           => $values,
					'using_livecanvas' => lc_post_is_using_livecanvas( $id ),
				);
				$metas[ $id ] = $meta;
			}
		}
		return array(
			'rows'  => $rows,
			'metas' => $metas,
		);
	};
	$fingerprint = static fn ( array $rows ): string => hash(
		'sha256',
		wp_json_encode(
			array(
				'site' => home_url(),
				'rows' => $rows,
			)
		)
	);
	$predict     = static function ( array $state, array $ids, bool $enabled ): array {
		foreach ( $ids as $id ) {
			if ( $enabled ) {
				$state['metas'][ $id ]['_lc_livecanvas_enabled'] = array( '1' );
			} else {
				unset( $state['metas'][ $id ]['_lc_livecanvas_enabled'] );
			}
			ksort( $state['metas'][ $id ] );
			$state['rows'][ $id ]['values']           = $enabled ? array( '1' ) : array();
			$state['rows'][ $id ]['using_livecanvas'] = $enabled;
			$state['rows'][ $id ]['meta_sha256']      = hash( 'sha256', wp_json_encode( $state['metas'][ $id ] ) );
		}
		return $state;
	};

	$execute = static function () use ( $snapshot, $fingerprint, $predict, $args ): void {
		$operation = $args[0] ?? 'plan';
		if ( ! in_array( $operation, array( 'plan', 'apply', 'rollback' ), true ) ) {
			throw new RuntimeException( 'Expected plan, apply or rollback.' );
		}
		$before     = $snapshot();
		$before_sha = $fingerprint( $before['rows'] );
		$changed    = array();
		if ( 'plan' !== $operation ) {
			if ( ! isset( $args[1] ) || ! hash_equals( $before_sha, $args[1] ) ) {
				throw new RuntimeException( 'State changed since the reviewed plan; nothing written.' );
			}
			if ( 'apply' === $operation ) {
				$ids      = array_keys( array_filter( $before['rows'], static fn ( array $row ): bool => array() === $row['values'] ) );
				$expected = $predict( $before, $ids, true );
			} else {
				if ( ! isset( $args[2], $args[3] ) || ! preg_match( '/^[1-9][0-9]*(?:,[1-9][0-9]*)*$/', $args[3] ) ) {
					throw new RuntimeException( 'Rollback needs the original state digest and apply result IDs.' );
				}
				$ids = array_map( 'intval', explode( ',', $args[3] ) );
				if ( count( array_unique( $ids ) ) !== count( $ids ) ) {
					throw new RuntimeException( 'Rollback IDs must be unique.' );
				}
				foreach ( $ids as $id ) {
					if ( ! isset( $before['rows'][ $id ] ) || array( '1' ) !== $before['rows'][ $id ]['values'] ) {
						throw new RuntimeException( 'Rollback is outside the exact added rows.' );
					}
				}
				$expected = $predict( $before, $ids, false );
				if ( ! hash_equals( $fingerprint( $expected['rows'] ), $args[2] ) ) {
					throw new RuntimeException( 'Rollback would not restore the reviewed original state; nothing written.' );
				}
			}
			foreach ( $ids as $id ) {
				$ok = 'apply' === $operation
				? add_post_meta( $id, '_lc_livecanvas_enabled', '1', true )
				: delete_post_meta( $id, '_lc_livecanvas_enabled', '1' );
				if ( ! $ok ) {
					throw new RuntimeException( 'Native metadata write failed; inspect all scoped rows and the backup before continuing.' );
				}
				$changed[] = $id;
			}
			$after = $snapshot();
			if ( $fingerprint( $after['rows'] ) !== $fingerprint( $expected['rows'] ) ) {
				throw new RuntimeException( 'Readback differs from the exact one-key plan.' );
			}
		} else {
			$after = $before;
		}
		echo wp_json_encode(
			array(
				'site'          => home_url(),
				'operation'     => $operation,
				'before_sha256' => $before_sha,
				'after_sha256'  => $fingerprint( $after['rows'] ),
				'changed_ids'   => $changed,
				'rows'          => array_values( $after['rows'] ),
			),
			JSON_UNESCAPED_SLASHES
		), PHP_EOL;
	};

	try {
		$execute();
	} catch ( Throwable $exception ) {
		WP_CLI::error( $exception->getMessage() );
	}
} )( $args ?? array() );
