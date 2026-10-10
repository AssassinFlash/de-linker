<?php
/**
 * LiveCanvas dynamic templates, exported as HTML in the plugin.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use WP_Post;

/**
 * One HTML file per Woo page type. sync() writes them into lc_dynamic_template
 * posts with LiveCanvas's official meta keys (modules/templating.php).
 */
final class Templates {

	/**
	 * LiveCanvas post type of a dynamic template.
	 */
	public const POST_TYPE = 'lc_dynamic_template';

	/**
	 * Directory of the exported HTML, relative to this plugin.
	 */
	private const RELATIVE_DIR = 'content/livecanvas';

	/**
	 * LiveCanvas assignment meta key → filename (without .html).
	 */
	private const FILES = array(
		'is_shop_page'                     => 'shop_page',
		'is_cart_page'                     => 'cart_page',
		'is_checkout_page'                 => 'checkout_page',
		'is_account_page'                  => 'account_page',
		'is_single_product'                => 'single_product',
		'is_archive_for_post_type_product' => 'archive_product',
	);

	/**
	 * Titles of the templates, in English (the editor list).
	 */
	private const TITLES = array(
		'is_shop_page'                     => 'Shop page',
		'is_cart_page'                     => 'Solution draft',
		'is_checkout_page'                 => 'Proforma request',
		'is_account_page'                  => 'Account',
		'is_single_product'                => 'Single product',
		'is_archive_for_post_type_product' => 'Product archive',
	);

	/**
	 * Absolute paths of the exported HTML, keyed by LiveCanvas meta.
	 *
	 * @return array<string, string>
	 */
	public static function catalog(): array {
		$dir = dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/';
		$out = array();
		foreach ( self::FILES as $meta => $file ) {
			$out[ $meta ] = $dir . $file . '.html';
		}
		return $out;
	}

	/**
	 * Creates or updates each template so the instance matches the files.
	 *
	 * @return array{created: int, updated: int, unchanged: int}
	 */
	public function sync(): array {
		$created   = 0;
		$updated   = 0;
		$unchanged = 0;
		foreach ( self::catalog() as $meta => $path ) {
			$html = Tokens::read( $path );
			$id   = $this->existing_id( $meta );
			if ( 0 === $id ) {
				$id = wp_insert_post(
					array(
						'post_type'    => self::POST_TYPE,
						'post_status'  => 'publish',
						'post_title'   => self::TITLES[ $meta ],
						'post_content' => $html,
					),
					true
				);
				if ( is_wp_error( $id ) ) {
					continue;
				}
				update_post_meta( (int) $id, $meta, '1' );
				++$created;
				continue;
			}
			$post = get_post( $id );
			if ( $post instanceof WP_Post && $post->post_content === $html ) {
				++$unchanged;
				continue;
			}
			wp_update_post(
				array(
					'ID'           => $id,
					'post_content' => wp_slash( $html ),
					'post_title'   => self::TITLES[ $meta ],
					'post_status'  => 'publish',
				)
			);
			++$updated;
		}
		return array(
			'created'   => $created,
			'updated'   => $updated,
			'unchanged' => $unchanged,
		);
	}

	/**
	 * The published template assigned to a LiveCanvas meta key, or 0.
	 *
	 * @param string $meta Assignment meta (is_cart_page, …).
	 */
	private function existing_id( string $meta ): int {
		$posts = get_posts(
			array(
				'post_type'      => self::POST_TYPE,
				'post_status'    => 'publish',
				'meta_key'       => $meta, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- LiveCanvas's own lookup.
				'meta_value'     => '1', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- LiveCanvas stores the assignment as "1".
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		);
		return isset( $posts[0] ) ? (int) $posts[0]->ID : 0;
	}
}
