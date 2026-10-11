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
	 * Templates of single pages, by template slug (the LiveCanvas post name):
	 * file, title, the page slug they render and that page's language. A page
	 * of this kind is not a Woo page type — it is one page, and LiveCanvas
	 * gives it its template through its own per-post choice,
	 * `lc_use_template_of_slug` (modules/templating.php), which this class
	 * writes onto the page. Two files and two pages per tool: English has no
	 * prefix, German lives under /de/ with its own words
	 * (docs/specs/19-tool-pages.md).
	 */
	private const PAGES = array(
		'linker-compare'    => array( 'compare_page', 'Compare products', 'compare-products', 'en' ),
		'linker-compare-de' => array( 'de/compare_page', 'Produkte vergleichen', 'compare-products', 'de' ),
		'linker-faq'        => array( 'faq_page', 'FAQ & documents', 'faq-download', 'en' ),
		'linker-faq-de'     => array( 'de/faq_page', 'FAQ & Dokumente', 'faq-download', 'de' ),
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
		foreach ( self::PAGES as $slug => $page ) {
			$out[ $slug ] = $dir . $page[0] . '.html';
		}
		return $out;
	}

	/**
	 * Creates or updates each template so the instance matches the files.
	 *
	 * @return array{created: int, updated: int, unchanged: int, created_ids: list<int>}
	 *         The ids of the posts this sync created (a rollback deletes them;
	 *         the ones it only updated keep their pre-run content in the backup).
	 * @throws \RuntimeException When WordPress refuses a template insert.
	 */
	public function sync(): array {
		$created     = 0;
		$updated     = 0;
		$unchanged   = 0;
		$created_ids = array();
		foreach ( self::FILES as $meta => $file ) {
			$html = Tokens::read( dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $file . '.html' );
			$id   = $this->existing_id( $meta );
			if ( 0 === $id ) {
				$id = wp_insert_post(
					array(
						'post_type'    => self::POST_TYPE,
						'post_status'  => 'publish',
						'post_title'   => self::TITLES[ $meta ],
						'post_content' => wp_slash( $html ),
					),
					true
				);
				if ( is_wp_error( $id ) ) {
					// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an exception message for the operator log, not page output.
					throw new \RuntimeException( sprintf( 'wp_insert_post refused the %s template: %s', $meta, $id->get_error_message() ) );
				}
				update_post_meta( (int) $id, $meta, '1' );
				$created_ids[] = (int) $id;
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
		foreach ( self::PAGES as $slug => $page ) {
			$report      = $this->sync_page_template( $slug, $page[0], $page[1] );
			$created    += $report['created'];
			$updated    += $report['updated'];
			$unchanged  += $report['unchanged'];
			$created_ids = array_merge( $created_ids, $report['created_ids'] );
		}
		$this->assign_pages();

		return array(
			'created'     => $created,
			'updated'     => $updated,
			'unchanged'   => $unchanged,
			'created_ids' => $created_ids,
		);
	}

	/**
	 * Creates or updates one page template: its post name is the slug
	 * LiveCanvas looks the template up by, so the page that carries the
	 * per-post choice gets exactly this template.
	 *
	 * @param string $slug  Template slug (LiveCanvas post name).
	 * @param string $file  Exported HTML file, without .html.
	 * @param string $title Template title.
	 * @return array{created: int, updated: int, unchanged: int, created_ids: list<int>}
	 * @throws \RuntimeException When WordPress refuses a template insert.
	 */
	private function sync_page_template( string $slug, string $file, string $title ): array {
		$html = Tokens::read( dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $file . '.html' );
		$post = $this->template_by_slug( $slug );
		if ( null === $post ) {
			$id = wp_insert_post(
				array(
					'post_type'    => self::POST_TYPE,
					'post_status'  => 'publish',
					'post_name'    => $slug,
					'post_title'   => $title,
					'post_content' => wp_slash( $html ),
				),
				true
			);
			if ( is_wp_error( $id ) ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an exception message for the operator log, not page output.
				throw new \RuntimeException( sprintf( 'wp_insert_post refused the %s template: %s', $slug, $id->get_error_message() ) );
			}

			return array(
				'created'     => 1,
				'updated'     => 0,
				'unchanged'   => 0,
				'created_ids' => array( (int) $id ),
			);
		}
		if ( $post->post_content === $html && $post->post_title === $title ) {
			return array(
				'created'     => 0,
				'updated'     => 0,
				'unchanged'   => 1,
				'created_ids' => array(),
			);
		}
		wp_update_post(
			array(
				'ID'           => $post->ID,
				'post_content' => wp_slash( $html ),
				'post_title'   => $title,
				'post_status'  => 'publish',
			)
		);

		return array(
			'created'     => 0,
			'updated'     => 1,
			'unchanged'   => 0,
			'created_ids' => array(),
		);
	}

	/**
	 * Gives each tool page its template: the LiveCanvas per-post choice
	 * (`lc_use_template_of_slug`), which its template loader reads from the
	 * queried post — so the German page carries the German template, and the
	 * German page is the translation of the English one when the language
	 * layer is loaded. An assignment that is already right is left alone.
	 */
	private function assign_pages(): void {
		foreach ( self::PAGES as $slug => $page ) {
			list( , , $page_slug, $language ) = $page;
			$id                               = $this->page_id( $page_slug, $language );
			if ( 0 === $id || get_post_meta( $id, 'lc_use_template_of_slug', true ) === $slug ) {
				continue;
			}
			update_post_meta( $id, 'lc_use_template_of_slug', $slug );
		}
	}

	/**
	 * The page a template renders: its slug in that page's language. The
	 * language layer (Polylang) answers which of the pages of that slug is
	 * the language's; without it, there is only one.
	 *
	 * @param string $page_slug Page slug.
	 * @param string $language  `en` or `de`.
	 */
	private function page_id( string $page_slug, string $language ): int {
		$posts = get_posts(
			array(
				'post_type'      => 'page',
				'post_status'    => 'publish',
				'name'           => $page_slug,
				'posts_per_page' => -1,
				'lang'           => '', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Polylang's own query var; without Polylang WordPress ignores it.
			)
		);
		if ( ! function_exists( 'pll_get_post_language' ) ) {
			return isset( $posts[0] ) ? (int) $posts[0]->ID : 0;
		}
		foreach ( $posts as $post ) {
			if ( pll_get_post_language( $post->ID ) === $language ) {
				return (int) $post->ID;
			}
		}

		return 0;
	}

	/**
	 * The published template of a slug, or null.
	 *
	 * @param string $slug Template slug (the post name).
	 */
	private function template_by_slug( string $slug ): ?WP_Post {
		$posts = get_posts(
			array(
				'post_type'      => self::POST_TYPE,
				'post_status'    => 'any',
				'name'           => $slug,
				'posts_per_page' => 1,
			)
		);

		return $posts[0] ?? null;
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
