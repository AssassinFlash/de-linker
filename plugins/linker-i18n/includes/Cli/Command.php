<?php
/**
 * The `wp linker-i18n` command.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Cli;

	use Linker\I18n\Jobs;
	use Linker\I18n\Languages;
	use Linker\I18n\LinkLocalizer;
	use Linker\I18n\Setup;
	use Linker\I18n\Twins;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\TranslationFailed;
use Linker\I18n\Translation\Translator;
use WP_CLI;

/**
 * Sets up the languages and manages the German versions of pages, posts,
 * products and terms.
 */
final class Command {

	/**
	 * Sets up the command.
	 *
	 * @param Languages     $languages  The site's languages.
	 * @param Setup         $setup      Polylang's configuration.
	 * @param Translator    $translator Makes the German versions.
	 * @param Jobs          $jobs       The translation queue.
	 * @param State         $state      Translation state.
	 * @param LinkLocalizer $links      Rewrites links to German pages.
	 * @param Twins|null    $twins      Writes the German versions, for the category repair.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly Setup $setup,
		private readonly Translator $translator,
		private readonly Jobs $jobs,
		private readonly State $state,
		private readonly LinkLocalizer $links,
		private readonly ?Twins $twins = null,
	) {}

	/**
	 * Configures Polylang: English (default, no prefix) and German (/de/,
	 * de_DE_formal), the language from the directory, no browser detection,
	 * the synchronised fields.
	 *
	 * ## OPTIONS
	 *
	 * [--assign]
	 * : Also give English to every page, post, product and term without a language.
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function setup( array $args, array $assoc_args ): void {
		unset( $args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-i18n setup --user=<admin>.' );
		}
		$errors = 0;
		foreach ( $this->setup->apply() as $line ) {
			WP_CLI::log( $line );
			$errors += str_starts_with( $line, 'error:' ) ? 1 : 0;
		}
		if ( isset( $assoc_args['assign'] ) ) {
			$this->setup->assign_default();
			WP_CLI::log( 'English given to the objects without a language' );
		}
		if ( $errors > 0 ) {
			WP_CLI::error( 'Polylang is not configured.' );
		}
		WP_CLI::success( 'Polylang configured.' );
	}

	/**
	 * Translates English posts or terms.
	 *
	 * ## OPTIONS
	 *
	 * [<id>...]
	 * : English post IDs, or term IDs with --terms.
	 *
	 * [--terms]
	 * : The IDs are term IDs.
	 *
	 * [--pending]
	 * : Every pending English object, using preservation rules for existing German.
	 *
	 * [--missing]
	 * : Missing German and pending objects only; never a site-wide retranslation.
	 *
	 * [--all]
	 * : Compatibility alias for --missing.
	 *
	 * [--force]
	 * : Legacy option; existing German is always protected.
	 *
	 * [--now]
	 * : Translate here and now instead of queueing.
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function translate( array $args, array $assoc_args ): void {
		$kind    = isset( $assoc_args['terms'] ) ? State::TERM : State::POST;
		$targets = array();
		foreach ( $args as $id ) {
			$targets[] = array( $kind, (int) $id );
		}
		if ( isset( $assoc_args['all'] ) || isset( $assoc_args['missing'] ) ) {
			$targets = array_merge( $targets, $this->pending( true ) );
		} elseif ( isset( $assoc_args['pending'] ) ) {
			$targets = array_merge( $targets, $this->pending() );
		}
		$targets = array_values( array_unique( $targets, SORT_REGULAR ) );
		$failed  = 0;
		$reasons = array();
		$force   = false;
		foreach ( $targets as list( $target_kind, $id ) ) {
			if ( ! isset( $assoc_args['now'] ) ) {
				$queued = $this->jobs->queue( $target_kind, $id, $force );
				WP_CLI::log( sprintf( '%s %d: %s', $target_kind, $id, $queued ? 'queued' : 'excluded from automatic translation' ) );
				continue;
			}
			try {
				$status = State::POST === $target_kind ? $this->translator->post( $id, $force ) : $this->translator->term( $id, $force );
				if ( State::STRUCTURE_MISMATCH === $status ) {
					++$failed;
					$reasons[] = sprintf( '%s %d: %s', $target_kind, $id, $status );
				}
			} catch ( TranslationFailed $failure ) {
				$this->state->set_status( $target_kind, $id, State::FAILED, $failure->getMessage() );
				$status    = State::FAILED . ': ' . $failure->getMessage();
				$reasons[] = sprintf( '%s %d: %s', $target_kind, $id, $status );
				++$failed;
			}
			WP_CLI::log( sprintf( '%s %d: %s', $target_kind, $id, '' === $status ? 'not an English translated object' : $status ) );
		}
		if ( $failed > 0 ) {
			WP_CLI::error( sprintf( '%d of %d objects failed; previous German retained. %s', $failed, count( $targets ), implode( '; ', $reasons ) ) );
		}
		WP_CLI::success( sprintf( '%d objects considered.', count( $targets ) ) );
	}

	/**
	 * Retires translation jobs and status on present-owned templates only.
	 *
	 * Run after deploying the safety guard and before provisioning a live key.
	 * Content, revisions, language groups and presentation meta are retained.
	 *
	 * @subcommand retire-template-jobs
	 * @param array<int, string>    $args Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function retire_template_jobs( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator.' );
		}
		$cancelled = 0;
		foreach ( as_get_scheduled_actions(
			array(
				'hook'     => Jobs::HOOK,
				'group'    => Jobs::GROUP,
				'status'   => \ActionScheduler_Store::STATUS_PENDING,
				'per_page' => -1,
			),
			'ids'
		) as $action_id ) {
			$arguments = \ActionScheduler::store()->fetch_action( $action_id )->get_args();
			$post      = State::POST === ( $arguments[0] ?? '' ) ? get_post( (int) ( $arguments[1] ?? 0 ) ) : null;
			if ( $post instanceof \WP_Post && in_array( $post->post_type, \Linker\I18n\TranslatedTypes::PRESENT_TYPES, true ) ) {
				\ActionScheduler::store()->cancel_action( $action_id );
				++$cancelled;
			}
		}
		$cleared = 0;
		foreach ( get_posts(
			array(
				'post_type'   => \Linker\I18n\TranslatedTypes::PRESENT_TYPES,
				'post_status' => 'any',
				'lang'        => '',
				'numberposts' => -1,
			)
		) as $post ) {
			$cleared += delete_post_meta( $post->ID, State::STATUS ) ? 1 : 0;
			delete_post_meta( $post->ID, State::NOTE );
		}
		WP_CLI::success( sprintf( '%d template jobs cancelled; %d template statuses cleared.', $cancelled, $cleared ) );
	}

	/**
	 * Stores given German as the German versions: the migration of the old
	 * plugin's German, or an import.
	 *
	 * ## OPTIONS
	 *
	 * --input=<file>
	 * : A JSON file, or - for standard input: a list of
	 * {"kind": "post"|"term", "source": <English ID>, "slug": "<slug of a new German object>",
	 * "fields": {"post_title": "…", "post_content": "…", "post_excerpt": "…", "meta:<key>": "…"}}
	 * (terms: "name" and "description").
	 *
	 * [--format=<format>]
	 * : Output format.
	 * ---
	 * default: table
	 * options:
	 *   - table
	 *   - json
	 * ---
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function import( array $args, array $assoc_args ): void {
		unset( $args );
		$input = $assoc_args['input'] ?? '-';
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a local file or standard input of a command.
		$json  = file_get_contents( '-' === $input ? 'php://stdin' : $input );
		$items = false === $json ? null : json_decode( $json, true );
		if ( ! is_array( $items ) ) {
			WP_CLI::error( 'The input is not a JSON list.' );
		}
		$rows = array();
		foreach ( $items as $item ) {
			$kind   = is_array( $item ) && State::TERM === ( $item['kind'] ?? '' ) ? State::TERM : State::POST;
			$source = is_array( $item ) ? (int) ( $item['source'] ?? 0 ) : 0;
			$fields = is_array( $item ) && is_array( $item['fields'] ?? null ) ? array_filter( $item['fields'], 'is_string' ) : array();
			$slug   = is_array( $item ) && is_string( $item['slug'] ?? null ) && '' !== $item['slug'] ? $item['slug'] : null;
			try {
				$status = $this->translator->adopt( $kind, $source, $fields, $slug );
				$twin   = State::POST === $kind ? $this->languages->post_translation( $source, Languages::TARGET ) : $this->languages->term_translation( $source, Languages::TARGET );
				$rows[] = array(
					'kind'   => $kind,
					'source' => $source,
					'german' => (string) $twin,
					'status' => '' === $status ? 'skipped: not an English translated object' : $status,
				);
			} catch ( \RuntimeException $error ) {
				$rows[] = array(
					'kind'   => $kind,
					'source' => $source,
					'german' => '',
					'status' => 'error: ' . $error->getMessage(),
				);
			}
		}
		// Polylang keeps each language's front page and posts page in a cached
		// language list; a German front page made here is not in it yet.
		PLL()->model->clean_languages_cache();
		WP_CLI\Utils\format_items( $assoc_args['format'] ?? 'table', $rows, array( 'kind', 'source', 'german', 'status' ) );
	}

	/**
	 * Repairs the LiveCanvas partials' language pairs: the header, footer and
	 * product partials carry an is_* role meta, and a role's two partials —
	 * the snapshot's English one (the lower ID; the German version is minted
	 * after the snapshot load) — must each carry their language and share a
	 * translation group. An instance imported before Twins ensured the
	 * source's language has them unpaired or mislabelled, which makes
	 * LiveCanvas's ID-ordered partial lookup render the German partial for
	 * every language (#11's forensics, 2026-10-10).
	 *
	 * @subcommand repair-partials
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function repair_partials( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-i18n repair-partials --user=<admin>.' );
		}
		global $wpdb;
		// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- a walk of the partials, not a write.
		$ids   = array_map( 'intval', $wpdb->get_col( "SELECT ID FROM {$wpdb->posts} WHERE post_type = 'lc_partial' AND post_status <> 'trash' ORDER BY ID ASC" ) );
		$roles = array();
		foreach ( $ids as $id ) {
			foreach ( get_post_meta( $id ) as $key => $values ) {
				if ( str_starts_with( (string) $key, 'is_' ) ) {
					$roles[ $key . ':' . $values[0] ][] = $id;
				}
			}
		}
		$repaired = 0;
		$skipped  = 0;
		foreach ( $roles as $role => $members ) {
			if ( 2 !== count( $members ) ) {
				++$skipped;
				WP_CLI::log( sprintf( '%s: %d partials, left alone', $role, count( $members ) ) );
				continue;
			}
			list( $english, $german ) = $members;
			if ( Languages::SOURCE !== $this->languages->of_post( $english ) ) {
				$this->languages->set_post_language( $english, Languages::SOURCE );
				++$repaired;
			}
			if ( Languages::TARGET !== $this->languages->of_post( $german ) ) {
				$this->languages->set_post_language( $german, Languages::TARGET );
				++$repaired;
			}
			if ( $german !== $this->languages->post_translation( $english, Languages::TARGET ) ) {
				$this->languages->pair_posts( $english, $german );
				++$repaired;
			}
		}
		WP_CLI::success( sprintf( 'LiveCanvas partial pairs: %d repairs, %d roles left alone.', $repaired, $skipped ) );
	}

	/**
	 * Puts the snapshot's posts back on the categories the pre-cutover
	 * snapshot records (posts 551–560 on terms 10–14, two each), and their
	 * German versions on the German terms. Does not read the relationships
	 * already in the database: those rows are gone, so a lookup by the
	 * English term finds nothing.
	 *
	 * A write of nothing is an error, not a success: the guards (the post
	 * type, the term's language, the snapshot slug) refuse a database that
	 * is not the snapshot's, and both callers — the migration's apply and
	 * the operator's cutover step — read this exit code. A silent zero is
	 * what leaves the German archive on its 301 while the log says success
	 * (the 2026-10-14 online recheck, families 16/22).
	 *
	 * @subcommand repair-post-categories
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function repair_post_categories( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-i18n repair-post-categories --user=<admin>.' );
		}
		if ( ! $this->twins instanceof Twins ) {
			WP_CLI::error( 'No writer for the post categories.' );
		}
		$restored = $this->twins->restore_post_categories();
		$expected = count( Twins::POST_CATEGORIES );
		if ( 0 === $restored ) {
			WP_CLI::error( sprintf( 'No post restored: none of the snapshot\'s %d posts is a post in this database, or its category no longer carries the snapshot slug. The repair writes the pre-cutover snapshot\'s own objects only.', $expected ) );
		}
		WP_CLI::success( sprintf( 'Post categories restored for %d of the snapshot\'s %d posts.', $restored, $expected ) );
	}

	/**
	 * Rewrites the links in every German page, post and product to the German
	 * pages (after an import, when the targets exist).
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function relink( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		$changed = 0;
		$ids     = get_posts(
			array(
				'post_type'   => 'any',
				'post_status' => 'any',
				'lang'        => Languages::TARGET,
				'fields'      => 'ids',
				'numberposts' => -1,
			)
		);
		foreach ( $ids as $id ) {
			$post = get_post( (int) $id );
			if ( ! $post instanceof \WP_Post ) {
				continue;
			}
			$content = $this->links->localize( $post->post_content );
			$excerpt = $this->links->localize( $post->post_excerpt );
			if ( $content === $post->post_content && $excerpt === $post->post_excerpt ) {
				continue;
			}
			global $wpdb;
			// phpcs:ignore WordPress.DB.DirectDatabaseQuery -- only the links change; a post update would be an edit by a person and run the save hooks.
			$wpdb->update(
				$wpdb->posts,
				array(
					'post_content' => $content,
					'post_excerpt' => $excerpt,
				),
				array( 'ID' => $post->ID )
			);
			clean_post_cache( $post->ID );
			++$changed;
		}
		WP_CLI::success( sprintf( 'Links rewritten in %d German posts.', $changed ) );
	}

	/**
	 * Lists the English pages, posts, products and terms with their German version.
	 *
	 * ## OPTIONS
	 *
	 * [--format=<format>]
	 * : Output format.
	 * ---
	 * default: table
	 * options:
	 *   - table
	 *   - json
	 *   - csv
	 * ---
	 *
	 * @param array<int, string>    $args       Positional arguments.
	 * @param array<string, string> $assoc_args Options.
	 */
	public function status( array $args, array $assoc_args ): void {
		unset( $args );
		$rows = array();
		foreach ( $this->english_posts() as $post ) {
			$twin   = $this->languages->post_translation( $post->ID, Languages::TARGET );
			$rows[] = array(
				'kind'   => $post->post_type,
				'source' => $post->ID,
				'german' => null === $twin ? '' : (string) $twin,
				'url'    => null === $twin ? '' : (string) get_permalink( $twin ),
				'status' => $this->state->status( State::POST, $post->ID ),
				'note'   => $this->state->note( State::POST, $post->ID ),
			);
		}
		foreach ( $this->english_terms() as $term ) {
			$twin   = $this->languages->term_translation( $term->term_id, Languages::TARGET );
			$link   = null === $twin ? '' : get_term_link( $twin, $term->taxonomy );
			$rows[] = array(
				'kind'   => $term->taxonomy,
				'source' => $term->term_id,
				'german' => null === $twin ? '' : (string) $twin,
				'url'    => is_string( $link ) ? $link : '',
				'status' => $this->state->status( State::TERM, $term->term_id ),
				'note'   => $this->state->note( State::TERM, $term->term_id ),
			);
		}
		WP_CLI\Utils\format_items( $assoc_args['format'] ?? 'table', $rows, array( 'kind', 'source', 'german', 'url', 'status', 'note' ) );
	}

	/**
	 * The English objects whose status is pending.
	 *
	 * @param bool $include_missing Also include objects without a German twin.
	 * @return list<array{string, int}>
	 */
	private function pending( bool $include_missing = false ): array {
		$pending = array();
		foreach ( $this->english_posts() as $post ) {
			if ( State::PENDING === $this->state->status( State::POST, $post->ID ) || ( $include_missing && null === $this->languages->post_translation( $post->ID, Languages::TARGET ) ) ) {
				$pending[] = array( State::POST, $post->ID );
			}
		}
		foreach ( $this->english_terms() as $term ) {
			if ( State::PENDING === $this->state->status( State::TERM, $term->term_id ) || ( $include_missing && null === $this->languages->term_translation( $term->term_id, Languages::TARGET ) ) ) {
				$pending[] = array( State::TERM, $term->term_id );
			}
		}
		return $pending;
	}

	/**
	 * The English posts of the translated types.
	 *
	 * @return list<\WP_Post>
	 */
	private function english_posts(): array {
		$posts = get_posts(
			array(
				'post_type'   => array_values( array_filter( get_post_types(), array( $this->languages, 'automatically_translates_post_type' ) ) ),
				'post_status' => array( 'publish', 'future', 'private', 'draft', 'pending' ),
				'lang'        => Languages::SOURCE,
				'numberposts' => -1,
				'orderby'     => 'ID',
				'order'       => 'ASC',
			)
		);
		return array_values( $posts );
	}

	/**
	 * The English terms of the translated taxonomies.
	 *
	 * @return list<\WP_Term>
	 */
	private function english_terms(): array {
		$terms = get_terms(
			array(
				'taxonomy'   => array_values( array_filter( get_taxonomies(), array( $this->languages, 'translates_taxonomy' ) ) ),
				'lang'       => Languages::SOURCE,
				'hide_empty' => false,
			)
		);
		return is_array( $terms ) ? array_values( $terms ) : array();
	}
}
