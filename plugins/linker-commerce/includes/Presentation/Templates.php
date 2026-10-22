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
	 * Template posts this instance has inserted and not yet reported.
	 * present() reads this from a finally block: a header refusal after the
	 * inserts must still be able to register those ids for rollback.
	 *
	 * @var list<int>
	 */
	private array $created_ids = array();

	/**
	 * Directory of the exported HTML, relative to this plugin.
	 */
	private const RELATIVE_DIR = 'content/livecanvas';

	/**
	 * LiveCanvas assignment meta key → filename (without .html).
	 *
	 * The three blog faces below are the assignments the instance's old
	 * templates carried (`is_blog_posts_index`, `is_search`,
	 * `is_archive_for_tax_category`): sync() reclaims those posts by their own
	 * key, so `present` replaces the old implementation in place instead of
	 * installing a second template (#175).
	 */
	private const FILES = array(
		'is_shop_page'                     => 'shop_page',
		'is_cart_page'                     => 'cart_page',
		'is_checkout_page'                 => 'checkout_page',
		'is_account_page'                  => 'account_page',
		'is_single_product'                => 'single_product',
		'is_archive_for_post_type_product' => 'archive_product',
		'is_single_post'                   => 'blog_single',
		'is_blog_posts_index'              => 'blog_index',
		'is_search'                        => 'search',
		'is_archive_for_tax_category'      => 'category_archive',
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
		'is_single_post'                   => 'Blog single post',
		'is_blog_posts_index'              => 'Blog posts index',
		'is_search'                        => 'Blog search results',
		'is_archive_for_tax_category'      => 'Blog category archive',
	);

	/**
	 * Page types whose German page carries an export of its own, keyed by the
	 * LiveCanvas assignment meta of the English template.
	 *
	 * A Woo page type is not a page: LiveCanvas looks its assignment up in the
	 * request's language (livecanvas 4.9.3 modules/templating.php,
	 * lc_get_template_id(), whose get_posts() Polylang narrows to the current
	 * language). The English post is the anchor and the German page type
	 * renders through the anchor's German twin, so a German export belongs on
	 * the twin — the same write the German header partial gets. The four
	 * structural page types need none: their markup is shortcodes and their
	 * words come out of the shortcodes' own translations, and
	 * Linker\I18n\DynamicTemplates answers a German request with the English
	 * template when no German one exists. The product page prints a model's
	 * breadcrumb, section titles and tab labels — words of its own — and it is
	 * the page both languages show, so it has a German markup file
	 * (content/livecanvas/de/single_product.html). Measured 2026-10-13 on the
	 * review instance before this: /product/<slug>/ rendered the export by
	 * template 234 while /de/produkt/<slug>/ fell through to the legacy
	 * template the snapshot carried, because nothing ever wrote that twin.
	 *
	 * The product archive (the shop and the category pages that share its
	 * export) is the second such type: its English anchor is the legacy
	 * `is_archive_for_post_type_product` template the sync reclaims by its
	 * meta key (#231), the German page resolves that key to its own legacy
	 * twin (#6915), and the export carries words ("Filters", the two aria
	 * labels) — so the twin gets a German file too.
	 *
	 * The blog single post is the third. Its words — the rail's labels, the
	 * checkpoints, the band's heading and both of its buttons, the related
	 * grid's title — are markup, not shortcode output, so the German face
	 * needs a file of its own. The sync reclaims the legacy templates the
	 * snapshot carries by the same `is_single_post` key (the live pair), which
	 * is what closes the blog face out of the instance's old implementation.
	 *
	 * The blog posts index, the search results and the category archive are
	 * the three faces #175 brought in. Their markup is English words too (the
	 * hero, the section headings, the card labels), the instance's old
	 * template pair carries each of their assignments (`is_blog_posts_index`,
	 * `is_search`, `is_archive_for_tax_category`), and the German twin holds
	 * the German export the way the faces above do. Their card links were the
	 * defect: the old templates wrote `/{Field name}/`, the slug under the
	 * site root, so every article a German archive listed linked out of the
	 * German tree into a 404 (issue #175).
	 */
	private const DE_FILES = array(
		'is_single_product'                => 'de/single_product',
		'is_archive_for_post_type_product' => 'de/archive_product',
		'is_single_post'                   => 'de/blog_single',
		'is_blog_posts_index'              => 'de/blog_index',
		'is_search'                        => 'de/search',
		'is_archive_for_tax_category'      => 'de/category_archive',
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
		'linker-compare'         => array( 'compare_page', 'Compare products', 'compare-products', 'en' ),
		'linker-compare-de'      => array( 'de/compare_page', 'Produkte vergleichen', 'compare-products', 'de' ),
		'linker-faq'             => array( 'faq_page', 'FAQ & documents', 'faq-download', 'en' ),
		'linker-faq-de'          => array( 'de/faq_page', 'FAQ & Dokumente', 'faq-download', 'de' ),
		'linker-advisor'         => array( 'advisor_page', 'Genie', 'genie', 'en' ),
		'linker-advisor-de'      => array( 'de/advisor_page', 'Genie', 'genie', 'de' ),
		// The Solution Configurator's page: the tool is a React app and the
		// template prints its mount point, so the page needs this template
		// instead of the application markup the old site stored in its body
		// (docs/specs/14-solution-configurator.md). The page lives at
		// `solution-configurator` (German `/de/loesungskonfigurator/`) since
		// the owner's 2026-10-12 ruling; the former addresses redirect
		// (Redirects). One file serves both languages: the mount and its
		// words come from the app.
		'linker-configurator'    => array( 'configurator_page', 'Solution Configurator', 'solution-configurator', 'en' ),
		'linker-configurator-de' => array( 'configurator_page', 'Lösungskonfigurator', 'loesungskonfigurator', 'de' ),
	);

		/**
		 * Template post ids inserted by the current sync(), including a sync
		 * that later refused the header twin. Empty before sync() and after a
		 * sync that inserted nothing.
		 *
		 * @return list<int>
		 */
	public function created_ids(): array {
			return $this->created_ids;
	}

	/**
	 * Whether the site's templates are what the exported files say they are:
	 * the read-only twin of sync(), for a deploy to assert after it ran
	 * instead of re-running the install to find out. Every lookup is sync()'s
	 * own, and the comparison is the one thing a file carries: the post
	 * content. A template the site does not carry, a German page-type twin the
	 * anchor's translation group does not resolve, a tool page pointed at
	 * another template, a partial pair whose German twin cannot be resolved,
	 * and a volume file that is absent or hashes differently are each one drift
	 * row. Nothing here writes.
	 *
	 * Rows follow sync()'s own write rule, not a stricter one: what check
	 * reports, a present run repairs, and a row present would not repair is
	 * not reported (a draft post whose content matches, for instance, is left
	 * alone by sync()). A page type without a twin is drift only where sync()
	 * would have one to write: a site without the language layer has no German
	 * page for the twin to serve, and its absence is not a gap
	 * (sync_page_type_twins()).
	 *
	 * @param list<string>|null $header_partials Header exports to compare against, the two files
	 *                                           from header_partials() when null.
	 * @return list<array{surface: string, target: string, detail: string}> Drift rows, empty when in sync.
	 */
	public function drift( ?array $header_partials = null ): array {
		$rows = array();
		foreach ( self::FILES as $meta => $file ) {
			$this->drift_template_row( $rows, 'page type ' . $meta, dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $file . '.html', $this->existing_id( $meta ) );
		}
		foreach ( self::PAGES as $slug => $page ) {
			$this->drift_template_row( $rows, 'page ' . $slug, dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $page[0] . '.html', $this->existing_id_by_slug( $slug ), $page[1] );
			list( , , $page_slug, $language ) = $page;
			$page_id                          = $this->page_id( $page_slug, $language );
			if ( 0 === $page_id ) {
				$rows[] = $this->row( 'page assignment ' . $slug, $page_slug . ' (' . $language . ')', 'the page this template belongs to is not installed' );
				continue;
			}
			if ( get_post_meta( $page_id, 'lc_use_template_of_slug', true ) !== $slug ) {
				$rows[] = $this->row( 'page assignment ' . $slug, $page_slug . ' (' . $language . ')', sprintf( 'post %d points at another template (or none)', $page_id ) );
			}
		}
		foreach ( self::DE_FILES as $meta => $file ) {
			$anchor = $this->existing_id( $meta );
			if ( 0 === $anchor ) {
				continue; // The English row above already reported the missing anchor.
			}
			$twin = $this->german_twin( $anchor );
			if ( 0 === $twin ) {
				if ( function_exists( 'pll_get_post' ) ) {
					$rows[] = $this->row( 'German twin ' . $meta, sprintf( 'post %d', $anchor ), 'the translation group carries no German twin for this page type' );
				}
				continue;
			}
			$this->drift_content_row( $rows, 'German twin ' . $meta, dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $file . '.html', $twin );
		}
		$rows = array_merge( $rows, $this->drift_partial_rows( 'header', $header_partials ?? self::header_partials() ) );
		$rows = array_merge( $rows, $this->drift_partial_rows( 'footer', self::footer_partials() ) );
		try {
			$rows = array_merge( $rows, ( new ArchiveAssignments() )->drift( $this->archive_targets() ) );
		} catch ( \RuntimeException $error ) {
			$rows[] = $this->row( 'archive assignments', 'product archive templates', $error->getMessage() );
		}
		return $rows;
	}

	/**
	 * Exact pre-present metadata for only the existing owned archive pair.
	 *
	 * @return array<int, array<string, list<mixed>>>
	 */
	public function archive_assignment_snapshot(): array {
		return ( new ArchiveAssignments() )->snapshot( $this->archive_targets() );
	}

	/**
	 * The existing native English anchor and its existing Polylang German twin.
	 * No assignment creates a second template or guesses a translated slug.
	 *
	 * @return array<string, int>
	 */
	private function archive_targets(): array {
		if ( array() === ( new ArchiveAssignments() )->keys() ) {
			return array();
		}
		$anchor = $this->existing_id( 'is_archive_for_post_type_product' );
		if ( 0 === $anchor ) {
			return array();
		}
		$targets = array( 'en' => $anchor );
		$twin    = $this->german_twin( $anchor );
		if ( $twin > 0 ) {
			$targets['de'] = $twin;
		}
		return $targets;
	}

	/**
	 * One page-type or page template against its export: absent, or content
	 * that differs from the file. The comparison is exactly what sync() writes
	 * and can repair: page templates carry a repo title sync_page_template()
	 * also restores (a title-only drift there is drift), page-type templates
	 * and their twins carry none — a status is never judged here.
	 *
	 * @param list<array{surface: string, target: string, detail: string}> $rows    Rows collected so far (by reference).
	 * @param string                                                       $surface Row label.
	 * @param string                                                       $path    The exported file.
	 * @param int                                                          $id      The site's template post, 0 when absent.
	 * @param string|null                                                  $title   The repo title, when sync writes one for this template.
	 */
	private function drift_template_row( array &$rows, string $surface, string $path, int $id, ?string $title = null ): void {
		if ( 0 === $id ) {
			$rows[] = $this->row( $surface, basename( $path ), 'not installed' );
			return;
		}
		$post = get_post( $id );
		if ( ! $post instanceof WP_Post ) {
			$rows[] = $this->row( $surface, sprintf( 'post %d', $id ), 'the template post cannot be read' );
			return;
		}
		$html = Tokens::read( $path );
		if ( $post->post_content !== $html ) {
			$rows[] = $this->row( $surface, sprintf( 'post %d', $id ), 'content differs from ' . basename( $path ) );
		}
		if ( null !== $title && $post->post_title !== $title ) {
			$rows[] = $this->row( $surface, sprintf( 'post %d', $id ), 'title "' . $post->post_title . '" differs from "' . $title . '"' );
		}
	}

	/**
	 * A translated template (a page-type twin) against its export.
	 *
	 * @param list<array{surface: string, target: string, detail: string}> $rows    Rows collected so far (by reference).
	 * @param string                                                       $surface Row label.
	 * @param string                                                       $path    The exported file.
	 * @param int                                                          $id      The site's post id.
	 */
	private function drift_content_row( array &$rows, string $surface, string $path, int $id ): void {
		$post = get_post( $id );
		$html = Tokens::read( $path );
		if ( ! $post instanceof WP_Post || $post->post_content !== $html ) {
			$rows[] = $this->row( $surface, sprintf( 'post %d', $id ), 'content differs from ' . basename( $path ) );
		}
	}

	/**
	 * The English header/footer partial and its German twin against their
	 * exports. A site without the partial has nothing to compare (sync writes
	 * none either); an English partial whose German twin cannot be resolved is
	 * drift, the same refusal sync_header_partials() raises as a write.
	 *
	 * @param string             $which 'header' or 'footer'.
	 * @param array<int, string> $files The two exports, English then German.
	 * @return list<array{surface: string, target: string, detail: string}>
	 */
	private function drift_partial_rows( string $which, array $files ): array {
		$rows = array();
		try {
			$ids = 'header' === $which ? $this->header_partial_ids() : $this->footer_partial_ids();
		} catch ( \RuntimeException $e ) {
			return array( $this->row( $which . ' partial', $which, $e->getMessage() ) );
		}
		foreach ( $ids as $lang => $id ) {
			$this->drift_content_row( $rows, $which . ' partial ' . $lang, $files[ 'de' === $lang ? 1 : 0 ], $id );
		}
		return $rows;
	}

	/**
	 * The live template of a slug, 0 when there is none. The lookup is sync's
	 * own (template_by_slug reads every status, because a tool page's template
	 * is found by its post name and updated in place either way).
	 *
	 * @param string $slug Template slug (the post name).
	 */
	private function existing_id_by_slug( string $slug ): int {
		$post = $this->template_by_slug( $slug );
		return null === $post ? 0 : (int) $post->ID;
	}

	/**
	 * One drift row.
	 *
	 * @param string $surface The kind of thing that drifted.
	 * @param string $target  Which one.
	 * @param string $detail  What is wrong.
	 * @return array{surface: string, target: string, detail: string}
	 */
	private function row( string $surface, string $target, string $detail ): array {
		return array(
			'surface' => $surface,
			'target'  => $target,
			'detail'  => $detail,
		);
	}

		/**
		 * The header partials `present` installs, English then German. Both
		 * must be readable and non-empty before a run may write: an empty
		 * source would blank the live header.
		 *
		 * @return list<string> Absolute paths.
		 */
	public static function header_partials(): array {
		$dir = dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/partials/';
		return array( $dir . 'header.html', $dir . 'de/header.html' );
	}

		/**
		 * The footer partials `present` installs, English then German.
		 *
		 * Same shape as the headers: the German file is already localized,
		 * and the live twin is `pll_get_post` of the English `footer` partial
		 * (slug `fuszeile` on the instances, not `footer`).
		 *
		 * @return list<string> Absolute paths.
		 */
	public static function footer_partials(): array {
		$dir = dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/partials/';
		return array( $dir . 'footer.html', $dir . 'de/footer.html' );
	}

	/**
	 * Absolute paths of the exported HTML, keyed by LiveCanvas meta.
	 *
	 * @return array<string, string>
	 */
	public static function paths(): array {
		$dir = dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/';
		$out = array();
		foreach ( self::FILES as $meta => $file ) {
			$out[ $meta ] = $dir . $file . '.html';
		}
		foreach ( self::PAGES as $slug => $page ) {
			$out[ $slug ] = $dir . $page[0] . '.html';
		}
		foreach ( self::DE_FILES as $meta => $file ) {
			$out[ $meta . '__de' ] = $dir . $file . '.html';
		}
		return $out;
	}

	/**
	 * Creates or updates each template so the instance matches the files.
	 *
	 * @param list<string>|null $header_partials Header exports to install, the two
	 *                                           files from header_partials() when null.
	 *                                           Proved non-empty before any write.
	 * @return array{created: int, updated: int, unchanged: int, created_ids: list<int>, de_twins_updated: int, de_twins_missing: list<string>, archive_assignments_updated: int}
	 *         The ids of the posts this sync created (a rollback deletes them;
	 *         the ones it only updated keep their pre-run content in the backup),
	 *         the German page-type twins it wrote, and the page types whose twin
	 *         this site does not have (see sync_page_type_twins()).
	 * @throws \RuntimeException When a header source is missing or empty, or WordPress refuses a template insert.
	 */
	public function sync( ?array $header_partials = null ): array {
		// Header sources are checked before any template write. present()
		// also refuses them in require_sources(); this is the same gate on
		// the write path, so a direct sync() cannot land templates and then
		// discover a missing header with nothing to roll back. A test passes
		// the missing export in; production passes nothing and reads the exports.
		$this->require_header_partials( $header_partials );
		( new ArchiveAssignments() )->preflight( $this->archive_targets() );
		$created           = 0;
		$updated           = 0;
		$unchanged         = 0;
		$this->created_ids = array();
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
					$this->assign_source_language( (int) $id );
					$this->created_ids[] = (int) $id;
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
			$this->assign_source_language( $id );
			++$updated;
		}
		foreach ( self::PAGES as $slug => $page ) {
			$report                = $this->sync_page_template( $slug, $page[0], $page[1] );
			$created              += $report['created'];
			$updated              += $report['updated'];
				$unchanged        += $report['unchanged'];
				$this->created_ids = array_merge( $this->created_ids, $report['created_ids'] );
		}
		$this->assign_pages();
		$twins               = $this->sync_page_type_twins();
		$updated            += $twins['updated'];
		$archive_assignments = ( new ArchiveAssignments() )->sync( $this->archive_targets() );
		$updated            += $this->sync_header_partials( $header_partials );
		// After the header write. A missing German header twin refuses
		// the run before the footer is touched, so a header refusal does
		// not also create footer posts.
		$updated += $this->sync_footer_partials();

		return array(
			'created'                     => $created,
			'updated'                     => $updated,
			'unchanged'                   => $unchanged,
			'created_ids'                 => $this->created_ids,
			'de_twins_updated'            => $twins['updated'],
			'de_twins_missing'            => $twins['missing'],
			'archive_assignments_updated' => $archive_assignments,
		);
	}

	/**
	 * Both header exports, after proving each is readable and non-empty.
	 *
	 * Called from present() before backup and from sync() before any
	 * template write. A missing or empty export is a refusal, not a write:
	 * writing '' would blank the live header, and discovering it after the
	 * templates are written leaves nothing to roll back.
	 *
	 * @param list<string>|null $files Paths to prove, the two exports when null.
	 *                                 A test passes a missing or empty export here
	 *                                 and then calls sync(); sync() reads the same list.
	 * @return list<string> Absolute paths, English then German.
	 * @throws \RuntimeException When a source is missing or empty.
	 */
	public function require_header_partials( ?array $files = null ): array {
		$files = $files ?? self::header_partials();
		foreach ( $files as $file ) {
			if ( '' === trim( Tokens::read( $file ) ) ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an exception message for the operator log, not page output.
				throw new \RuntimeException( sprintf( 'Header partial source is missing or empty: %s', $file ) );
			}
		}
		return $files;
	}

		/**
		 * Syncs the existing English header and its Polylang twin from the LC exports.
		 * Does not create substitute partials or change the theme's assignments.
		 *
		 * The sources are refused again here: sync() already refused them, and
		 * a write that reached this point with a missing export must still stop
		 * rather than blank the live header. The German export is already
		 * localized (its links are German addresses), so the write is the file itself.
		 *
		 * The English partial is the anchor (`post_name` header). The German
		 * partial is that post's Polylang twin (`pll_get_post`), not a second
		 * lookup by the English slug: Twins derives the German slug from the
		 * German title, so the live pair is header/en and kopfzeile/de. A site
		 * with an English header and no resolvable German twin is refused —
		 * skipping the language and reporting success would leave the German
		 * header stale. A site with no header partial at all has nothing to
		 * sync (LiveCanvas has not assigned one).
		 *
		 * @param list<string>|null $files Paths already proved by sync(), the exports when null.
		 * @throws \RuntimeException When a source is missing or empty, the German twin cannot be resolved, or WordPress refuses the update.
		 */
	private function sync_header_partials( ?array $files = null ): int {
		$files   = $this->require_header_partials( $files );
		$ids     = $this->header_partial_ids();
		$updated = 0;
		foreach ( $ids as $lang => $id ) {
			$html = Tokens::read( $files[ 'de' === $lang ? 1 : 0 ] );
			$post = get_post( $id );
			if ( $post instanceof WP_Post && $post->post_content === $html ) {
				continue;
			}
			$result = wp_update_post(
				array(
					'ID'           => $id,
					'post_content' => wp_slash( $html ),
				),
				true
			);
			if ( is_wp_error( $result ) ) {
				throw new \RuntimeException( 'Header partial update failed.' );
			}
			++$updated;
		}
		return $updated;
	}

		/**
		 * The published English header partial and its German Polylang twin.
		 *
		 * The English row is the anchor: a name query for `header`. The German
		 * row is `pll_get_post( $english, 'de' )`. Looking both languages up by
		 * the English slug misses the twin — on the live instances the German
		 * partial's slug is `kopfzeile`, derived from its German title, not
		 * `header`. When Polylang is absent and a published `kopfzeile` partial
		 * exists, that slug is the explicit fallback and is named as such; it
		 * is not a same-slug query. An English header whose German twin cannot
		 * be resolved is a refusal, not a skipped language.
		 *
		 * @return array{en?: int, de?: int} Partial ids, empty when the site has no header partial.
		 * @throws \RuntimeException When the English header has no resolvable German twin.
		 */
	private function header_partial_ids(): array {
		$posts = get_posts(
			array(
				'post_type'      => 'lc_partial',
				'post_status'    => 'publish',
				'name'           => 'header',
				'lang'           => '',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		);
		if ( ! isset( $posts[0] ) ) {
			return array();
		}
		$english = (int) $posts[0]->ID;
		$german  = $this->german_header_twin( $english );
		if ( $german <= 0 ) {
			throw new \RuntimeException(
				sprintf(
					'German header partial could not be resolved from English partial %d (pll_get_post de, fallback slug kopfzeile): refusing to report a header sync that skipped a language.',
					$english // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator log, not page output.
				)
			);
		}
			return array(
				'en' => $english,
				'de' => $german,
			);
	}

		/**
		 * Both footer exports, after proving each is readable and non-empty.
		 *
		 * A missing export is a refusal, not a write: writing '' would blank
		 * the live footer. Called from sync() before the footer write.
		 *
		 * @return list<string> Absolute paths, English then German.
		 * @throws \RuntimeException When a source is missing or empty.
		 */
	public function require_footer_partials(): array {
		$files = self::footer_partials();
		foreach ( $files as $file ) {
			if ( '' === trim( Tokens::read( $file ) ) ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an exception message for the operator log, not page output.
				throw new \RuntimeException( sprintf( 'Footer partial source is missing or empty: %s', $file ) );
			}
		}
		return $files;
	}

		/**
		 * Syncs the existing English footer and its Polylang twin from the LC exports.
		 *
		 * The English partial is the anchor (`post_name` footer). The German
		 * partial is that post's Polylang twin, not a second lookup by the
		 * English slug: Twins derives the German slug from the German title,
		 * so the live pair is footer/en and fuszeile/de. A site with an English
		 * footer and no resolvable German twin is refused. A site with no
		 * footer partial at all has nothing to sync.
		 *
		 * @throws \RuntimeException When a source is missing or empty, the German twin cannot be resolved, or WordPress refuses the update.
		 */
	private function sync_footer_partials(): int {
		$ids = $this->footer_partial_ids();
		if ( array() === $ids ) {
			return 0;
		}
		$files   = $this->require_footer_partials();
		$updated = 0;
		foreach ( $ids as $lang => $id ) {
			$html = Tokens::read( $files[ 'de' === $lang ? 1 : 0 ] );
			$post = get_post( $id );
			if ( $post instanceof WP_Post && $post->post_content === $html ) {
				continue;
			}
			$result = wp_update_post(
				array(
					'ID'           => $id,
					'post_content' => wp_slash( $html ),
				),
				true
			);
			if ( is_wp_error( $result ) ) {
				throw new \RuntimeException( 'Footer partial update failed.' );
			}
			++$updated;
		}
		return $updated;
	}

		/**
		 * The published English footer partial and its German Polylang twin.
		 *
		 * @return array{en?: int, de?: int} Partial ids, empty when the site has no footer partial.
		 * @throws \RuntimeException When the English footer has no resolvable German twin.
		 */
	private function footer_partial_ids(): array {
		$posts = get_posts(
			array(
				'post_type'      => 'lc_partial',
				'post_status'    => 'publish',
				'name'           => 'footer',
				'lang'           => '',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		);
		if ( ! isset( $posts[0] ) ) {
			return array();
		}
		$english = (int) $posts[0]->ID;
		$german  = $this->german_footer_twin( $english );
		if ( $german <= 0 ) {
			throw new \RuntimeException(
				sprintf(
					'German footer partial could not be resolved from English partial %d (pll_get_post de, fallback slug fuszeile): refusing to report a footer sync that skipped a language.',
					$english // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator log, not page output.
				)
			);
		}
		return array(
			'en' => $english,
			'de' => $german,
		);
	}

		/**
		 * The German twin of the English footer partial.
		 *
		 * Polylang's translation group is the authority. The `fuszeile` slug
		 * is only the fallback when that API is not loaded.
		 *
		 * @param int $english English footer partial id.
		 */
	private function german_footer_twin( int $english ): int {
		if ( function_exists( 'pll_get_post' ) ) {
			return (int) pll_get_post( $english, 'de' );
		}
		$posts = get_posts(
			array(
				'post_type'      => 'lc_partial',
				'post_status'    => 'publish',
				'name'           => 'fuszeile',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		);
		return isset( $posts[0] ) ? (int) $posts[0]->ID : 0;
	}

		/**
		 * The German twin of the English header partial.
		 *
		 * Polylang's translation group is the authority. The `kopfzeile` slug
		 * is only the fallback when that API is not loaded: Twins names the
		 * German partial from its German title, and a same-slug lookup would
		 * miss it. A loaded Polylang that returns no twin is not papered over
		 * with the slug — the caller refuses.
		 *
		 * @param int $english English header partial id.
		 */
	private function german_header_twin( int $english ): int {
		if ( function_exists( 'pll_get_post' ) ) {
			return $this->german_twin( $english );
		}
		$posts = get_posts(
			array(
				'post_type'      => 'lc_partial',
				'post_status'    => 'publish',
				'name'           => 'kopfzeile',
				'posts_per_page' => 1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		);
		return isset( $posts[0] ) ? (int) $posts[0]->ID : 0;
	}

	/**
	 * The German twin of an English post, by Polylang's translation group, or 0.
	 *
	 * The one lookup every German twin goes through. There is no slug fallback
	 * here: the German post's name is derived from its German title (Twins), so
	 * a same-slug lookup would miss it, and without the language layer there is
	 * no German page type for a twin to serve.
	 *
	 * @param int $english English post id.
	 */
	private function german_twin( int $english ): int {
		if ( ! function_exists( 'pll_get_post' ) ) {
			return 0;
		}
		return (int) pll_get_post( $english, 'de' );
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
			$this->assign_source_language( (int) $id );

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
		$this->assign_source_language( $post->ID );

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
	 * Writes each German page-type export into its template's German twin.
	 *
	 * The English post is the anchor: it carries the LiveCanvas assignment,
	 * and on a German page LiveCanvas looks that assignment up in the request's
	 * language, so the German page type renders through the anchor's German
	 * twin (modules/templating.php under Polylang's language-scoped query). A
	 * twin that already holds the file is left alone, so a second run writes
	 * nothing.
	 *
	 * A page type without a twin is reported, not guessed at: this site has no
	 * German page type for that export to serve (no Polylang, or no German
	 * language), and inventing one here would make a translation decision this
	 * class does not own. present() prints the list.
	 *
	 * @return array{updated: int, missing: list<string>} Twins written, and the
	 *         LiveCanvas meta keys whose anchor has no German twin.
	 * @throws \RuntimeException When WordPress refuses the update.
	 */
	private function sync_page_type_twins(): array {
		$updated = 0;
		$missing = array();
		foreach ( self::DE_FILES as $meta => $file ) {
			$anchor = $this->existing_id( $meta );
			if ( 0 === $anchor ) {
				continue; // No English template of this page type: nothing to twin.
			}
			$twin = $this->german_twin( $anchor );
			if ( 0 === $twin ) {
				// Only a site with a language layer can be missing a German
				// page type; without one the German export has nothing to
				// serve, and its absence is not a gap to report.
				if ( function_exists( 'pll_get_post' ) ) {
					$missing[] = $meta;
				}
				continue;
			}
			$html = Tokens::read( dirname( __DIR__, 2 ) . '/' . self::RELATIVE_DIR . '/' . $file . '.html' );
			$post = get_post( $twin );
			if ( $post instanceof WP_Post && $post->post_content === $html ) {
				continue;
			}
			$result = wp_update_post(
				array(
					'ID'           => $twin,
					'post_content' => wp_slash( $html ),
					'post_status'  => 'publish',
				),
				true
			);
			if ( is_wp_error( $result ) ) {
				// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an exception message for the operator log, not page output.
				throw new \RuntimeException( sprintf( 'wp_update_post refused the German twin %d of the %s template: %s', $twin, $meta, $result->get_error_message() ) );
			}
			++$updated;
		}
		return array(
			'updated' => $updated,
			'missing' => $missing,
		);
	}

	/**
	 * Gives a template without a language the site's source language, when
	 * Polylang runs: a German twin is later found only through its
	 * translation group, and Polylang silently skips a languageless member
	 * when the twin is paired (#11's LiveCanvas forensics, 2026-10-10). The
	 * default language is the one objects are written in (`wp linker-i18n
	 * setup` makes it English); a template that already carries a language
	 * keeps it. Without Polylang there is nothing to answer to, and the
	 * setup's own assignment covers the templates later.
	 *
	 * @param int $id Template post id.
	 */
	private function assign_source_language( int $id ): void {
		if ( ! function_exists( 'pll_set_post_language' ) || ! function_exists( 'pll_default_language' ) || ! function_exists( 'pll_get_post_language' ) ) {
			return;
		}
		$source = pll_default_language();
		if ( is_string( $source ) && false === pll_get_post_language( $id ) ) {
			pll_set_post_language( $id, $source );
		}
	}

	/**
	 * Resolves the English source slug, then its native translation pair.
	 * German page renames must not detach the template that present owns.
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
			if ( 'en' === pll_get_post_language( $post->ID ) && 'en' !== $language && function_exists( 'pll_get_post' ) ) {
				$id = pll_get_post( $post->ID, $language );
				if ( $id > 0 && get_post( $id ) instanceof WP_Post ) {
					return $id;
				}
			}
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
