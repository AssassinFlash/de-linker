<?php
/**
 * The `wp linker-commerce present` command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Presentation\Templates;
use Linker\Commerce\Presentation\Tokens;
use Linker\Commerce\Presentation\WindPressCache;
use Linker\Commerce\Presentation\WindPressVolume;
use WP_CLI;

/**
 * Writes LiveCanvas templates and Additional CSS from the files in this plugin.
 * Refuses to run on unreadable sources, refuses to report success when the
 * WindPress cache cannot serve the templates styled, and keeps a restorable
 * backup of everything it replaces.
 */
final class PresentCommand {

	/**
	 * Option name of the pre-write backup (consumed by `linker-commerce rollback`).
	 */
	public const BACKUP_OPTION = 'linker_commerce_present_backup';

	/**
	 * The WindPress cache checker.
	 *
	 * @var WindPressCache
	 */
	private WindPressCache $cache;

	/**
	 * Source files the run requires, overriding the exported ones (tests).
	 *
	 * @var list<string>|null
	 */
	private ?array $source_files;

	/**
	 * Constructor.
	 *
	 * @param WindPressCache|null $cache        Cache checker override (tests).
	 * @param list<string>|null   $source_files Source file list override (tests).
	 */
	public function __construct( ?WindPressCache $cache = null, ?array $source_files = null ) {
		$this->cache        = $cache ?? new WindPressCache();
		$this->source_files = $source_files;
	}

	/**
	 * Installs the presentation layer into the current site: LiveCanvas templates,
	 * Additional CSS tokens, and (optionally) stripping tokens from header partials.
	 * Refuses to report success when the WindPress cache cannot serve the
	 * templates styled.
	 *
	 * ## OPTIONS
	 *
	 * [--detach-partials]
	 * : Also remove the inlined tokens.css block from LiveCanvas header/footer partials.
	 *
	 * [--allow-stale]
	 * : Report an unusable WindPress cache — inactive, never compiled, or older
	 * than the templates/tokens — as a warning instead of failing. Only for runs
	 * where no browser is at hand.
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function present( array $args, array $assoc_args ): void {
		unset( $args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-commerce present --user=<admin>.' );
		}
		$this->require_sources();
		// The header partials are already in sources(). Re-check them here,
		// on the write path's own gate, so a run cannot pass require_sources()
		// and then reach backup/sync with a header that has since gone.
		( new Templates() )->require_header_partials();

		$this->backup( true );

		$settings = get_option( 'lc_settings', array() );
		if ( ! is_array( $settings ) ) {
			$settings = array();
		}
		$settings['enable-dynamic-templating'] = 1;
		update_option( 'lc_settings', $settings );

		$templates = new Templates();
		try {
			$report = $templates->sync();
		} finally {
			// Header sync runs after the template inserts. A refusal there
			// (a missing German twin) must still register the posts this
			// run already created, or a rollback cannot delete them.
			$this->backfill_backup( $templates->created_ids() );
		}
		WP_CLI::log( sprintf( 'templates: created %d, updated %d, unchanged %d', $report['created'], $report['updated'], $report['unchanged'] ) );

		$removed = ( new Tokens() )->uninstall();
		WP_CLI::log( $removed ? 'tokens: removed the Additional CSS copy (the WindPress volume serves content/windpress/tokens.css)' : 'tokens: no Additional CSS copy to remove' );

		( new WindPressVolume() )->install();
		WP_CLI::log( 'windpress volume: storefront styles' );

		if ( isset( $assoc_args['detach-partials'] ) ) {
			$stripped = ( new Tokens() )->detach_from_partials();
			WP_CLI::log( sprintf( 'partials: stripped tokens from %d', $stripped ) );
		}

		$this->check_windpress_cache( isset( $assoc_args['allow-stale'] ) );

		WP_CLI::success( 'Presentation installed. A rollback copy is in the ' . self::BACKUP_OPTION . ' option.' );
	}

	/**
	 * Restores the previous run's templates, Additional CSS, partials and
	 * settings: updated posts get their pre-run content and post status back,
	 * posts the run created are deleted, lc_settings returns to its pre-run
	 * value, and the backup is consumed. A write WordPress refuses fails the
	 * rollback loudly and keeps the backup, so the run can be retried.
	 *
	 * ## OPTIONS
	 *
	 * [--user=<login>]
	 * : Run as the given administrator.
	 *
	 * @when after_wp_load
	 *
	 * @param array<int, string>   $args       Positional arguments.
	 * @param array<string, mixed> $assoc_args Options.
	 */
	public function rollback( array $args, array $assoc_args ): void {
		unset( $args, $assoc_args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator: wp linker-commerce rollback --user=<admin>.' );
		}
		$backup = get_option( self::BACKUP_OPTION );
		if ( ! is_array( $backup ) || ! isset( $backup['at'], $backup['templates'], $backup['custom_css'] ) ) {
			WP_CLI::error( 'No present backup exists (option ' . self::BACKUP_OPTION . '): nothing to roll back.' );
		}

		$restored = 0;
		foreach ( (array) $backup['templates'] as $post ) {
			if ( ! is_array( $post ) || ! isset( $post['ID'], $post['post_content'] ) ) {
				continue;
			}
			$this->update_post(
				(int) $post['ID'],
				array(
					'ID'           => (int) $post['ID'],
					'post_content' => wp_slash( (string) $post['post_content'] ),
					'post_title'   => (string) ( $post['post_title'] ?? '' ),
					'post_status'  => (string) ( $post['post_status'] ?? 'publish' ),
				)
			);
			++$restored;
		}

		foreach ( (array) ( $backup['created_templates'] ?? array() ) as $created_id ) {
			if ( false === wp_delete_post( (int) $created_id, true ) ) {
				WP_CLI::error( sprintf( 'wp_delete_post refused template %d: the backup is kept, nothing consumed.', (int) $created_id ) );
			}
			++$restored;
		}

		if ( array_key_exists( 'settings', $backup ) ) {
			if ( $backup['settings_existed'] ?? true ) {
				update_option( 'lc_settings', (array) $backup['settings'] );
			} else {
				delete_option( 'lc_settings' );
			}
			++$restored;
		}

		wp_update_custom_css_post( (string) $backup['custom_css'] );
		++$restored;

		foreach ( (array) ( $backup['partials'] ?? array() ) as $partial ) {
			if ( ! is_array( $partial ) || ! isset( $partial['ID'], $partial['post_content'] ) ) {
				continue;
			}
			$this->update_post(
				(int) $partial['ID'],
				array(
					'ID'           => (int) $partial['ID'],
					'post_content' => wp_slash( (string) $partial['post_content'] ),
				)
			);
			++$restored;
		}

		delete_option( self::BACKUP_OPTION );
		WP_CLI::success( sprintf( 'Rolled back %d writes from the %s run.', $restored, (string) $backup['at'] ) );
	}

	/**
	 * Updates a post and refuses a silent failure: wp_update_post answers a
	 * WP_Error when WordPress declines the write, and continuing from there
	 * would consume a backup whose content is not actually restored.
	 *
	 * @param int                  $id   Post id, for the error message.
	 * @param array<string, mixed> $data wp_update_post arguments.
	 */
	private function update_post( int $id, array $data ): void {
		$updated = wp_update_post( $data, true );
		if ( is_wp_error( $updated ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- an operator-facing CLI message, not page output.
			WP_CLI::error( sprintf( 'wp_update_post refused post %d (%s): the backup is kept, nothing consumed.', $id, $updated->get_error_message() ) );
		}
	}

	/**
	 * The templates' Tailwind classes only reach the visitor through the
	 * WindPress cache, which the WindPress admin compiles in the browser
	 * (Tailwind v4 has no server-side compile). Installing templates or tokens
	 * therefore outdates the cache, and a cache without the templates' classes
	 * means the visitor sees unstyled templates: report it loudly instead of a
	 * plain success. An absent or inactive cache is the same failure — nothing
	 * will ever serve the classes — so it fails the run on the same channel;
	 * `--allow-stale` is its escape. Only a current cache that merely misses
	 * the classes stays a warning (a recompile picks them up without a
	 * reinstall).
	 *
	 * @param bool $allow_stale Warn instead of fail on an unusable cache.
	 */
	private function check_windpress_cache( bool $allow_stale ): void {
		$defect = $this->cache->defect();
		if ( null === $defect ) {
			WP_CLI::log( 'windpress: cache is newer than the templates/tokens and contains the template classes' );
			return;
		}
		if ( 'missing-classes' === $defect['kind'] ) {
			WP_CLI::warning( sprintf( '%s — the classes are not compiled; recompile from the WindPress admin (admin.php?page=windpress).', ucfirst( $defect['detail'] ) ) );
			return;
		}
		$message = match ( $defect['kind'] ) {
			'inactive' => 'WindPress is not active: the Tailwind classes of the templates will not be compiled. Activate it and compile from its admin (admin.php?page=windpress), or rerun with --allow-stale.',
			'no-cache' => sprintf( 'No compiled WindPress cache exists (%s): the templates would reach the visitor unstyled. Compile from the WindPress admin (admin.php?page=windpress), or rerun with --allow-stale.', $defect['detail'] ),
			default    => sprintf( 'WindPress cache is stale (%s). Compile from the WindPress admin (admin.php?page=windpress), or rerun with --allow-stale.', $defect['detail'] ),
		};
		WP_CLI::warning( $message );
		if ( $allow_stale ) {
			return;
		}
		WP_CLI::error( $message );
	}

	/**
	 * Every file this run installs from must be readable and non-empty: a
	 * silent fallback would overwrite the live templates or the tokens with
	 * nothing.
	 */
	private function require_sources(): void {
		$broken = array();
		foreach ( $this->sources() as $path ) {
			if ( ! is_readable( $path ) || '' === trim( (string) file_get_contents( $path ) ) ) { // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- local plugin file on disk, not a remote URL.
				$broken[] = $path;
			}
		}
		if ( array() !== $broken ) {
			WP_CLI::error( sprintf( 'Source files are unreadable or empty (%s): refusing to overwrite the installed presentation with nothing.', implode( ', ', $broken ) ) );
		}
	}

	/**
	 * The files this run installs from or serves: the LiveCanvas templates, the
	 * two header partials, the tokens stylesheet (the same
	 * content/windpress/tokens.css the volume publishes — not a second copy),
	 * and the fonts its @font-face rules point at (the visitor loads them
	 * straight from the plugin, so a missing font file is the same broken
	 * presentation as an empty template). A missing or empty header partial
	 * is refused here, before anything is written. The volume glob already
	 * includes the tokens file; listing Tokens::path() beside it is the
	 * named requirement, and a duplicate path is the same file.
	 *
	 * @return list<string>
	 */
	private function sources(): array {
		if ( null !== $this->source_files ) {
			return $this->source_files;
		}
		return array_merge( array_values( Templates::paths() ), Templates::header_partials(), array( Tokens::path() ), Tokens::fonts(), WindPressVolume::files() );
	}

	/**
	 * Keeps a restorable copy of everything the run may replace: the existing
	 * LiveCanvas templates (content, title and post status), Additional CSS,
	 * lc_settings, and — for --detach-partials — the LiveCanvas partials.
	 * Templates the run creates (they had no backup row) are added by
	 * backfill_backup() in the finally around sync(), including a sync that
	 * throws after inserting templates, so a rollback both restores the
	 * updated posts and deletes the created ones. `wp linker-commerce rollback`
	 * restores it.
	 *
	 * @param bool $with_partials The run will strip the partials too.
	 */
	private function backup( bool $with_partials ): void {
		$templates = array();
		foreach ( get_posts(
			array(
				'post_type'      => Templates::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => -1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
			)
		) as $post ) {
			$templates[] = array(
				'ID'           => $post->ID,
				'post_title'   => $post->post_title,
				'post_content' => $post->post_content,
				'post_status'  => $post->post_status,
			);
		}

		$partials = array();
		if ( $with_partials ) {
			foreach ( get_posts(
				array(
					'post_type'      => 'lc_partial',
					'post_status'    => 'any',
					'posts_per_page' => -1,
					'orderby'        => 'ID',
					'order'          => 'ASC',
				)
			) as $post ) {
				$partials[] = array(
					'ID'           => $post->ID,
					'post_content' => $post->post_content,
				);
			}
		}

		$settings         = get_option( 'lc_settings', null );
		$settings_existed = null !== $settings;
		if ( ! is_array( $settings ) ) {
			$settings = array();
		}

		update_option(
			self::BACKUP_OPTION,
			array(
				'at'                => gmdate( 'Y-m-d H:i:s' ) . ' UTC',
				'templates'         => $templates,
				'custom_css'        => (string) wp_get_custom_css(),
				'partials'          => $partials,
				'settings'          => $settings,
				'settings_existed'  => $settings_existed,
				'created_templates' => array(),
			),
			false
		);
		WP_CLI::log( sprintf( 'backup: %d templates, additional css, %d partials staged for rollback', count( $templates ), count( $partials ) ) );
	}

	/**
	 * Adds the posts sync() created to the staged backup: they had no row when
	 * the backup was taken (nothing pre-run to restore), so a rollback deletes
	 * them instead of pretending their content is restorable.
	 *
	 * @param int[] $created_ids Post ids of this run's inserts.
	 */
	private function backfill_backup( array $created_ids ): void {
		if ( array() === $created_ids ) {
			return;
		}
		$backup = get_option( self::BACKUP_OPTION );
		if ( ! is_array( $backup ) ) {
			WP_CLI::error( 'The present backup staged at the start of the run is gone: created templates cannot be registered for rollback.' );
		}
		$backup['created_templates'] = array_merge(
			(array) ( $backup['created_templates'] ?? array() ),
			array_map( 'intval', $created_ids )
		);
		update_option( self::BACKUP_OPTION, $backup, false );
	}
}
