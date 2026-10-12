<?php
/**
 * Tests for the presentation installer command.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Cli;

use Linker\Commerce\Cli\PresentCommand;
use Linker\Commerce\Presentation\WindPressCache;
use Linker\Commerce\Tests\TestCase;
use WP_CLI;
use WP_CLI\ExitException;
use WP_Mock;
use WP_Post;

/**
 * Tests for PresentCommand. The WP_CLI double (tests/php/Doubles/wordpress.php)
 * prints every log/warning/success line, so the expectations read the output.
 *
 * @covers \Linker\Commerce\Cli\PresentCommand
 */
final class PresentCommandTest extends TestCase {

	/**
	 * The compiled selectors of every anchor class, as Tailwind emits them.
	 */
	private const COMPILED_ALL = '.sf-catalog{}.catalog-grid{}.sf-card{}.wb-strip{}'
		. '.pdp-layout{}.pdp-purchase{}.pdp-scene-reel{}.pdp-disclose{}';

	/**
	 * The option name of the staged backup.
	 */
	private const BACKUP = 'linker_commerce_present_backup';

	/**
	 * The per-test compiled-cache file.
	 *
	 * @var string
	 */
	private string $cache_path;

	/**
	 * The per-test source files (readable, non-empty).
	 *
	 * @var list<string>
	 */
	private array $source_paths;

	/**
	 * The option store the run reads and writes.
	 *
	 * @var array<string, mixed>
	 */
	private array $options;

	/**
	 * Header partials written by the mocked installer, post id => content.
	 *
	 * @var array<int, string>
	 */
	private array $written_partials = array();

	/** Prepares the per-test cache and source files. */
	public function setUp(): void {
		parent::setUp();
		$this->cache_path   = sys_get_temp_dir() . '/linker-commerce-present-command-test.css';
		$this->source_paths = array(
			sys_get_temp_dir() . '/linker-commerce-present-command-source-a.html',
			sys_get_temp_dir() . '/linker-commerce-present-command-source-b.css',
		);
		foreach ( array( $this->cache_path, ...$this->source_paths ) as $path ) {
			if ( file_exists( $path ) ) {
				unlink( $path );
			}
		}
		file_put_contents( $this->source_paths[0], '<section>template</section>' );
		file_put_contents( $this->source_paths[1], ':root{--proto-accent:#0c7f73}' );
		$this->options               = array();
		$this->written_partials      = array();
		WP_CLI::$registered_commands = array();
	}

	/** Deletes the per-test files. */
	public function tearDown(): void {
		foreach ( array( $this->cache_path, ...$this->source_paths ) as $path ) {
			if ( file_exists( $path ) ) {
				unlink( $path );
			}
		}
		parent::tearDown();
	}

	/**
	 * A non-administrator is refused before any write.
	 */
	public function test_refuses_a_non_administrator(): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => false,
			)
		);

		try {
			$this->present();
			$this->fail( 'WP_CLI::error should stop the command' );
		} catch ( ExitException $e ) {
			$this->assertNotSame( '', $e->getMessage() );
		}
	}

	/**
	 * An unreadable or empty source stops the run: the fallback would
	 * overwrite the installed presentation with nothing.
	 */
	public function test_unreadable_or_empty_sources_fail_the_run(): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => true,
			)
		);
		file_put_contents( $this->source_paths[0], '' );
		try {
				$this->present( array(), array( $this->source_paths[0], sys_get_temp_dir() . '/linker-commerce-missing-source.css' ) );
			$this->fail( 'A run on unreadable sources should fail' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'unreadable or empty', $e->getMessage() );
			$this->assertStringContainsString( 'linker-commerce-missing-source.css', $e->getMessage() );
			$this->assertSame( 0, substr_count( $this->output(), 'wp-cli success:' ) );
		}
	}

	/**
	 * The two header partials are sources of the run: a missing one is refused
	 * before anything is written.
	 */
	public function test_header_partials_are_required_sources(): void {
		$partials = \Linker\Commerce\Presentation\Templates::header_partials();
		$this->assertCount( 2, $partials );
		foreach ( $partials as $path ) {
			$this->assertNotSame( '', trim( (string) file_get_contents( $path ) ), $path );
		}
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => true,
			)
		);
		try {
				$this->present( array(), array( $partials[0], $partials[1] . '.missing' ) );
			$this->fail( 'A missing header partial should fail the run' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'unreadable or empty', $e->getMessage() );
			$this->assertStringContainsString( 'header.html.missing', $e->getMessage() );
		}
	}

	/**
	 * An absent WindPress cache stops the run: the templates would reach the
	 * visitor unstyled while the command reports success.
	 */
	public function test_absent_cache_fails_the_run(): void {
		$this->mock_install();

		try {
			$this->present();
			$this->fail( 'A run without a compiled WindPress cache should fail' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'never compiled', $this->output() );
			$this->assertStringContainsString( '--allow-stale', $e->getMessage() );
			$this->assertSame( 0, substr_count( $this->output(), 'wp-cli success:' ) );
		}
	}

	/**
	 * A cache older than the templates/tokens stops the run, with the newer
	 * source files named in a warning.
	 */
	public function test_stale_cache_names_the_newer_sources_and_fails(): void {
		$this->mock_install();
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() - 3600 );

		try {
			$this->present();
			$this->fail( 'A run on a stale WindPress cache should fail' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'admin.php?page=windpress', $e->getMessage() );
		}
		$warning_line = (string) strstr( $this->output(), 'WindPress cache is stale' );
		$this->assertStringContainsString( 'newer source files:', $warning_line );
		$this->assertStringContainsString( 'source-b.css', $warning_line );
	}

	/**
	 * --allow-stale downgrades the stale cache to a warning so a run without a
	 * browser at hand can still install the templates and tokens.
	 */
	public function test_allow_stale_downgrades_to_a_warning(): void {
		$this->mock_install();
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() - 3600 );

		$this->present( array( 'allow-stale' => true ) );

		$this->assertSame( 1, substr_count( $this->output(), 'WindPress cache is stale' ) );
		$this->assertStringContainsString( '--allow-stale', $this->output() );
		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success:' ) );
	}

	/**
	 * An inactive WindPress is the same failure as an absent cache — nothing
	 * will ever serve the templates' classes — so it fails the run instead of
	 * the lenient warning (the consequence is heavier than a stale cache).
	 */
	public function test_inactive_windpress_fails_the_run(): void {
		$this->mock_install();

		try {
			$this->present( array(), null, new WindPressCache( null, $this->source_paths ) );
			$this->fail( 'A run on an inactive WindPress should fail' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'not active', $this->output() );
			$this->assertStringContainsString( '--allow-stale', $e->getMessage() );
			$this->assertSame( 0, substr_count( $this->output(), 'wp-cli success:' ) );
		}
	}

	/**
	 * --allow-stale is the escape for the inactive WindPress too.
	 */
	public function test_allow_stale_downgrades_an_inactive_windpress(): void {
		$this->mock_install();

		$this->present( array( 'allow-stale' => true ), null, new WindPressCache( null, $this->source_paths ) );

		$this->assertSame( 1, substr_count( $this->output(), 'not active' ) );
		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success:' ) );
	}

	/**
	 * A fresh cache without the templates' classes warns that the classes are
	 * not compiled, and the run still succeeds (the cache itself is current).
	 */
	public function test_missing_classes_warn_but_the_run_succeeds(): void {
		$this->mock_install();
		file_put_contents( $this->cache_path, '.pdp-layout{display:grid}' );
		touch( $this->cache_path, time() + 60 );

		$this->present();

		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli warning:' ) );
		$this->assertStringContainsString( 'not compiled', $this->output() );
		$this->assertStringContainsString( 'sf-card', $this->output() );
		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success:' ) );
	}

	/**
	 * The real WP-CLI dispatch: WP_CLI\Runner invokes an object command's
	 * method with the positional arguments and the options as two separate
	 * arrays. The flags have to arrive in the second array — a signature that
	 * binds them elsewhere silently turns --allow-stale into a dead flag (the
	 * stale-cache run below would fail instead of succeeding).
	 */
	public function test_the_wp_cli_dispatch_shape_reaches_the_flags(): void {
		$this->mock_install();
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() - 3600 );

		WP_CLI::add_command( 'linker-commerce', new PresentCommand( new WindPressCache( $this->cache_path, $this->source_paths ), $this->source_paths ) );
		$command = WP_CLI::$registered_commands['linker-commerce'] ?? null;
		$this->assertInstanceOf( PresentCommand::class, $command );

		// The call shape of WP_CLI\Runner::run_command for an object command.
		$command->present( array(), array( 'allow-stale' => true ) );

		$this->assertSame( 1, substr_count( $this->output(), 'WindPress cache is stale' ) );
		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success:' ) );
	}

	/**
	 * The run stages a rollback copy of the templates (with their post
	 * status), the Additional CSS and lc_settings before its first write.
	 */
	public function test_the_run_stages_a_rollback_backup(): void {
		$shop_template = array(
			'ID'           => 6564,
			'post_title'   => 'Shop page',
			'post_content' => '<section class="old">live</section>',
			'post_status'  => 'publish',
		);
		$this->mock_install(
			array(
				'templates' => array( $shop_template ),
				'assigned'  => array( 'is_shop_page' => $shop_template ),
				'partials'  => array(),
				'settings'  => array(
					'header'                    => '1',
					'enable-dynamic-templating' => 0,
				),
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->present();

		$backup = $this->options[ self::BACKUP ] ?? null;
		$this->assertIsArray( $backup );
		$this->assertSame( array( 6564 ), array_column( $backup['templates'], 'ID' ) );
		$this->assertSame( '<section class="old">live</section>', $backup['templates'][0]['post_content'] );
		$this->assertSame( 'publish', $backup['templates'][0]['post_status'] );
		$this->assertSame( '', $backup['custom_css'] );
		$this->assertSame(
			array(
				'header'                    => '1',
				'enable-dynamic-templating' => 0,
			),
			$backup['settings']
		);
		$this->assertTrue( $backup['settings_existed'] );
			$this->assertSame( array( 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511 ), $backup['created_templates'], 'the templates missing on this site joined the backup' );
	}

	/**
	 * Templates the run created had no backup row (nothing pre-run to
	 * restore), so present registers their ids in the backup after the sync —
	 * the distinction between the posts it updated and the posts it created.
	 */
	public function test_created_templates_join_the_backup(): void {
		$shop_template = array(
			'ID'           => 6564,
			'post_title'   => 'Shop page',
			'post_content' => '<section class="old">live</section>',
			'post_status'  => 'publish',
		);
		$this->mock_install(
			array(
				'templates' => array( $shop_template ),
				'assigned'  => array( 'is_shop_page' => $shop_template ),
				'partials'  => array(),
				'settings'  => null,
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->present();

		$backup = $this->options[ self::BACKUP ] ?? null;
		$this->assertIsArray( $backup );
		$this->assertSame( array( 6564 ), array_column( $backup['templates'], 'ID' ), 'the already-installed template is staged as an update' );
			$this->assertSame( array( 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511 ), $backup['created_templates'], 'the missing templates are staged as creations' );
		$this->assertFalse( $backup['settings_existed'] );
		$this->assertSame( array(), $backup['settings'] );
	}

	/**
	 * --detach-partials stages the partials too.
	 */
	public function test_detach_partials_stages_the_partials(): void {
		$this->mock_install(
			array(
				'templates' => array(),
				'partials'  => array(
					array(
						'ID'           => 17,
						'post_content' => '<header><style data-site-css="tokens.css">x</style></header>',
					),
				),
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

			$this->present( array( 'detach-partials' => true ) );

		$backup = $this->options[ self::BACKUP ] ?? null;
		$this->assertIsArray( $backup );
		$this->assertSame( array( 17 ), array_column( $backup['partials'], 'ID' ) );
		$this->assertStringContainsString( 'data-site-css="tokens.css"', (string) $backup['partials'][0]['post_content'] );
	}

	/**
	 * A fresh install's round trip: six templates created, the run rolled
	 * back — the six posts are deleted, the absent lc_settings stays absent
	 * (the switch does not survive as a ghost option), and the backup is
	 * consumed.
	 */
	public function test_a_fresh_install_round_trip_deletes_what_it_created(): void {
		$this->mock_install(
			array(
				'templates' => array(),
				'partials'  => array(),
				'settings'  => null,
			)
		);
		$deleted = array();
		WP_Mock::userFunction(
			'wp_delete_post',
			array(
				'return' => static function ( int $id ) use ( &$deleted ): int {
					$deleted[] = $id;
					return $id;
				},
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->present();

		$backup = $this->options[ self::BACKUP ] ?? null;
		$this->assertIsArray( $backup );
			$this->assertSame( array( 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512 ), $backup['created_templates'], 'the fresh install created every template' );
		$this->assertSame( array( 'enable-dynamic-templating' => 1 ), $this->options['lc_settings'], 'the run switched dynamic templating on' );

		$this->rollback();

			$this->assertSame( array( 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512 ), $deleted, 'the rollback deleted exactly the created templates' );
		$this->assertArrayNotHasKey( 'lc_settings', $this->options, 'the absent lc_settings is not resurrected as an empty option' );
		$this->assertArrayNotHasKey( self::BACKUP, $this->options, 'the backup is consumed' );
			$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success: Rolled back 14 writes' ) );
	}

	/**
	 * The rollback restores the lc_settings of before the run: an existing
	 * switch that present turned on is off again afterwards, and the other
	 * keys keep their pre-run values.
	 */
	public function test_the_rollback_restores_the_previous_settings(): void {
		$this->mock_install(
			array(
				'templates' => array(),
				'partials'  => array(),
				'settings'  => array(
					'header'                    => '1',
					'footerV2'                  => '1',
					'enable-dynamic-templating' => 0,
				),
			)
		);
		WP_Mock::userFunction( 'wp_delete_post', array( 'return' => static fn ( int $id ): int => $id ) );
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->present();
		$this->assertSame( 1, $this->options['lc_settings']['enable-dynamic-templating'], 'the run switched dynamic templating on' );

		$this->rollback();

		$this->assertSame(
			array(
				'header'                    => '1',
				'footerV2'                  => '1',
				'enable-dynamic-templating' => 0,
			),
			$this->options['lc_settings'],
			'the rollback restored the pre-run settings'
		);
	}

	/**
	 * A rollback without a backup refuses with a clear message.
	 */
	public function test_rollback_without_a_backup_refuses(): void {
		$this->mock_rollback( null );

		try {
			$this->rollback();
			$this->fail( 'A rollback without a backup should fail' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'No present backup exists', $e->getMessage() );
		}
	}

	/**
	 * A rollback restores the backed-up templates (with their original post
	 * status), Additional CSS and partials, then consumes the backup.
	 */
	public function test_rollback_restores_the_backup(): void {
		$updated = array();
		$this->mock_rollback(
			array(
				'at'         => '2026-10-10 12:00:00 UTC',
				'templates'  => array(
					array(
						'ID'           => 6564,
						'post_title'   => 'Shop page',
						'post_content' => '<section class="old">live</section>',
						'post_status'  => 'publish',
					),
				),
				'custom_css' => ':root{--proto-accent:#0c7f73}',
				'partials'   => array(
					array(
						'ID'           => 17,
						'post_content' => '<header>with tokens</header>',
					),
				),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$updated ): int {
					$updated[ (int) $data['ID'] ] = $data;
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		$css_restored = array( '' );
		WP_Mock::userFunction(
			'wp_update_custom_css_post',
			array(
				'return' => static function ( string $css ) use ( &$css_restored ): int {
					$css_restored[0] = $css;
					return 1;
				},
			)
		);

		$this->rollback();

		$this->assertSame( 6564, $updated[6564]['ID'] );
		$this->assertSame( '<section class="old">live</section>', $updated[6564]['post_content'] );
		$this->assertSame( 'publish', $updated[6564]['post_status'] );
		$this->assertSame( 17, $updated[17]['ID'] );
		$this->assertSame( ':root{--proto-accent:#0c7f73}', $css_restored[0] );
		$this->assertArrayNotHasKey( self::BACKUP, $this->options, 'the backup is consumed' );
		$this->assertSame( 1, substr_count( $this->output(), 'wp-cli success: Rolled back 3 writes' ) );
	}

	/**
	 * The rollback restores the recorded post status, not a hardcoded
	 * publish: a template the operator had unpublished before the run comes
	 * back unpublished.
	 */
	public function test_the_rollback_restores_the_original_post_status(): void {
		$updated = array();
		$this->mock_rollback(
			array(
				'at'         => '2026-10-10 12:00:00 UTC',
				'templates'  => array(
					array(
						'ID'           => 6564,
						'post_title'   => 'Shop page',
						'post_content' => '<section class="old">live</section>',
						'post_status'  => 'draft',
					),
				),
				'custom_css' => '',
				'partials'   => array(),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static function ( array $data ) use ( &$updated ): int {
					$updated[ (int) $data['ID'] ] = $data;
					return (int) $data['ID'];
				},
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_update_custom_css_post', array( 'return' => 1 ) );

		$this->rollback();

		$this->assertSame( 'draft', $updated[6564]['post_status'] );
	}

	/**
	 * A write WordPress refuses (wp_update_post answers a WP_Error) fails the
	 * rollback loudly and keeps the backup, so nothing is consumed that is
	 * not actually restored.
	 */
	public function test_the_rollback_refuses_a_silent_update_failure(): void {
		$this->mock_rollback(
			array(
				'at'         => '2026-10-10 12:00:00 UTC',
				'templates'  => array(
					array(
						'ID'           => 6564,
						'post_title'   => 'Shop page',
						'post_content' => '<section class="old">live</section>',
						'post_status'  => 'publish',
					),
				),
				'custom_css' => '',
				'partials'   => array(),
			)
		);
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => static fn (): \WP_Error => new \WP_Error( 'db_update_error', 'Could not update post in the database' ),
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );

		try {
			$this->rollback();
			$this->fail( 'A refused template write should fail the rollback' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'wp_update_post refused post 6564', $e->getMessage() );
			$this->assertStringContainsString( 'Could not update post in the database', $e->getMessage() );
			$this->assertStringContainsString( 'backup is kept', $e->getMessage() );
		}
		$this->assertArrayHasKey( self::BACKUP, $this->options, 'the backup survives a failed rollback' );
		$this->assertSame( 0, substr_count( $this->output(), 'wp-cli success:' ) );
	}

	/**
	 * A created template WordPress refuses to delete fails the rollback
	 * loudly and keeps the backup.
	 */
	public function test_the_rollback_refuses_a_failed_delete(): void {
		$this->mock_rollback(
			array(
				'at'                => '2026-10-10 12:00:00 UTC',
				'templates'         => array(),
				'created_templates' => array( 501 ),
				'custom_css'        => '',
				'partials'          => array(),
			)
		);
		WP_Mock::userFunction( 'wp_delete_post', array( 'return' => false ) );

		try {
			$this->rollback();
			$this->fail( 'A refused template delete should fail the rollback' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'wp_delete_post refused template 501', $e->getMessage() );
		}
		$this->assertArrayHasKey( self::BACKUP, $this->options, 'the backup survives a failed rollback' );
	}

		/**
		 * The live pair is header/en and kopfzeile/de. The German partial is
		 * newer, which is the row a same-slug date order would return first.
		 * Each export is written into the partial pll_get_post names, not into
		 * a second header slug.
		 */
	public function test_header_twin_is_written_from_the_english_anchor(): void {
		$this->mock_install(
			array(
				'templates' => array(),
				'partials'  => array(
					array(
						'ID'           => 17,
						'post_name'    => 'header',
						'post_content' => '<header>stale english</header>',
						'post_date'    => '2026-10-01 09:00:00',
						'lang'         => 'en',
					),
					array(
						'ID'           => 6919,
						'post_name'    => 'kopfzeile',
						'post_content' => '<header>stale deutsch</header>',
						'post_date'    => '2026-10-12 09:00:00',
						'lang'         => 'de',
					),
				),
				'twins'     => array( 17 => array( 'de' => 6919 ) ),
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		$this->present();

		$exports = \Linker\Commerce\Presentation\Templates::header_partials();
		$this->assertSame( (string) file_get_contents( $exports[0] ), $this->written_partials[17] );
		$this->assertSame( (string) file_get_contents( $exports[1] ), $this->written_partials[6919] );
		$this->assertStringContainsString( 'href="/de/loesung/heimspeicher/"', $this->written_partials[6919] );
		$this->assertStringNotContainsString( 'href="/de/loesung/', $this->written_partials[17] );
		$this->assertArrayNotHasKey( 40, $this->written_partials );
	}

		/**
		 * A present run that cannot resolve the German header twin fails before
		 * either partial is written. The refusal is the present path, not a
		 * silent skip followed by success.
		 */
	public function test_a_missing_german_header_twin_refuses_present_without_writing_either_side(): void {
		$this->mock_install(
			array(
				'templates' => array(),
				'partials'  => array(
					array(
						'ID'           => 17,
						'post_name'    => 'header',
						'post_content' => '<header>stale english</header>',
						'lang'         => 'en',
					),
				),
				'twins'     => array(),
			)
		);
		file_put_contents( $this->cache_path, self::COMPILED_ALL );
		touch( $this->cache_path, time() + 60 );

		try {
			$this->present();
			$this->fail( 'A missing German header twin should fail present' );
		} catch ( \RuntimeException $e ) {
			$this->assertStringContainsString( 'German header partial could not be resolved', $e->getMessage() );
		}
		$this->assertSame( array(), $this->written_partials, 'neither language is written' );
		$this->assertSame( 0, substr_count( $this->output(), 'wp-cli success:' ) );
		$backup = $this->options[ self::BACKUP ] ?? null;
		$this->assertIsArray( $backup );
		$this->assertSame(
			array( 501, 502, 503, 504, 505, 506, 507, 508, 509, 510, 511, 512 ),
			$backup['created_templates'],
			'templates inserted before the header refusal are registered for rollback'
		);
	}

	/**
	 * A non-administrator is refused before anything is restored.
	 */
	public function test_rollback_refuses_a_non_administrator(): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => false,
			)
		);

		try {
			$this->rollback();
			$this->fail( 'WP_CLI::error should stop the rollback' );
		} catch ( ExitException $e ) {
			$this->assertStringContainsString( 'rollback', $e->getMessage() );
		}
	}

	/**
	 * Runs the command the way this test suite prepares it: with a checker
	 * pointed at the test's cache file.
	 *
	 * @param array<string, bool> $assoc_args   Options.
	 * @param list<string>|null   $source_files Source override.
	 * @param WindPressCache|null $cache        Cache checker override.
	 */
	private function present( array $assoc_args = array(), ?array $source_files = null, ?WindPressCache $cache = null ): void {
		$command = new PresentCommand(
			$cache ?? new WindPressCache( $this->cache_path, $this->source_paths ),
			$source_files ?? $this->source_paths
		);
		// WP_CLI\Runner::run_command dispatches an object command with the
		// positional arguments and the options as two arrays.
		$command->present( array(), $assoc_args );
	}

	/**
	 * Runs the rollback the way WP-CLI dispatches it.
	 */
	private function rollback(): void {
		( new PresentCommand( new WindPressCache( $this->cache_path, $this->source_paths ) ) )->rollback( array(), array() );
	}

	/**
	 * The output the command printed so far.
	 */
	private function output(): string {
		return $this->getActualOutput();
	}

	/**
	 * Mocks a rollback run reading the given backup from the option.
	 *
	 * @param array<string, mixed>|null $backup The stored backup, null for none.
	 */
	private function mock_rollback( ?array $backup ): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => true,
			)
		);
		if ( null !== $backup ) {
			$this->options[ self::BACKUP ] = $backup;
		}
		$this->mock_option_store();
		WP_Mock::userFunction(
			'is_wp_error',
			array(
				'return' => static fn ( $value ): bool => $value instanceof \WP_Error,
			)
		);
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
	}

	/**
	 * Mocks a full installation: an administrator, the LiveCanvas settings,
	 * templates and Additional CSS writes, the pre-write backup (with the
	 * given existing posts) and the option store.
	 *
	 * @param array<string, mixed>|null $existing Pre-existing posts ('templates' for the backup,
	 *                                            'partials', 'assigned' keyed by LiveCanvas meta
	 *                                            for sync's lookups), lc_settings ('settings':
	 *                                            an array to store it, null to have the option
	 *                                            absent) and Additional CSS ('custom_css').
	 */
	private function mock_install( ?array $existing = null ): void {
		WP_Mock::userFunction(
			'current_user_can',
			array(
				'args'   => array( 'manage_options' ),
				'return' => true,
			)
		);
		if ( is_array( $existing ) && array_key_exists( 'settings', $existing ) ) {
			if ( null !== $existing['settings'] ) {
				$this->options['lc_settings'] = $existing['settings'];
			}
		} else {
			$this->options['lc_settings'] = array();
		}
		$this->mock_option_store();
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $existing ): array {
					if ( 'lc_partial' === $args['post_type'] && 'header' === ( $args['name'] ?? '' ) ) {
						foreach ( $existing['partials'] ?? array() as $row ) {
							if ( 'header' === ( $row['post_name'] ?? '' ) ) {
								return self::wp_posts( array( $row ), 'lc_partial' );
							}
						}
						// The default fixture is the live pair: English header
						// 17, German twin 6919 (kopfzeile). A test that passes
						// partials and omits header has no header to sync.
						if ( ! isset( $existing['partials'] ) ) {
							return self::wp_posts(
								array(
									array(
										'ID'        => 17,
										'post_name' => 'header',
										'lang'      => 'en',
									),
								),
								'lc_partial'
							);
						}
						return array();
					}
					if ( 'lc_partial' === $args['post_type'] && 'footer' === ( $args['name'] ?? '' ) ) {
						foreach ( $existing['partials'] ?? array() as $row ) {
							if ( 'footer' === ( $row['post_name'] ?? '' ) ) {
								return self::wp_posts( array( $row ), 'lc_partial' );
							}
						}
						// A fixture that lists partials and omits footer has no
						// footer to sync. The default fixture has none either:
						// these tests cover the header pair.
						return array();
					}
					if ( 'lc_partial' === $args['post_type'] && 'fuszeile' === ( $args['name'] ?? '' ) ) {
						foreach ( $existing['partials'] ?? array() as $row ) {
							if ( 'fuszeile' === ( $row['post_name'] ?? '' ) ) {
								return self::wp_posts( array( $row ), 'lc_partial' );
							}
						}
						return array();
					}
					if ( 'lc_partial' === $args['post_type'] && 'kopfzeile' === ( $args['name'] ?? '' ) ) {
						foreach ( $existing['partials'] ?? array() as $row ) {
							if ( 'kopfzeile' === ( $row['post_name'] ?? '' ) ) {
								return self::wp_posts( array( $row ), 'lc_partial' );
							}
						}
						return array();
					}
					if ( 'lc_partial' === $args['post_type'] ) {
							return self::wp_posts( $existing['partials'] ?? array(), 'lc_partial' );
					}
					if ( 'page' === $args['post_type'] ) {
						return self::wp_posts( $existing['pages'] ?? array(), 'page' );
					}
					if ( isset( $args['name'] ) ) {
						foreach ( $existing['templates'] ?? array() as $row ) {
							if ( ( $row['post_name'] ?? '' ) === $args['name'] ) {
								return self::wp_posts( array( $row ) );
							}
						}
						return array();
					}
					if ( isset( $args['meta_key'] ) ) {
						$assigned = $existing['assigned'][ (string) $args['meta_key'] ] ?? null;
						return null === $assigned ? array() : self::wp_posts( array( $assigned ) );
					}
						return self::wp_posts( $existing['templates'] ?? array() );
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => static fn ( int $id ): WP_Post => self::wp_posts(
					array(
						array(
							'ID'           => $id,
							'post_title'   => 'Assigned template',
							'post_content' => '<section>assigned</section>',
						),
					)
				)[0],
			)
		);
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'return' => static function (): int {
					static $created = 0;
					++$created;
					return 500 + $created;
				},
			)
		);
		WP_Mock::userFunction( 'update_post_meta', array( 'return' => true ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction(
			'wp_get_custom_css',
			array(
				'return' => $existing['custom_css'] ?? '',
			)
		);
		WP_Mock::userFunction( 'wp_update_custom_css_post', array( 'return' => 1 ) );
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'return' => function ( array $data ): int {
					if ( ! isset( $data['post_title'] ) ) {
						$this->written_partials[ (int) $data['ID'] ] = (string) $data['post_content'];
					}
					return (int) $data['ID'];
				},
			)
		);
		// The volume styles land in a throwaway directory.
		WP_Mock::userFunction(
			'wp_get_upload_dir',
			array(
				'return' => static fn (): array => array( 'basedir' => sys_get_temp_dir() . '/linker-commerce-present-command-uploads' ),
			)
		);
		WP_Mock::userFunction( 'wp_mkdir_p', array( 'return' => true ) );
			WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => sys_get_temp_dir() ) ) );
			// WP_Mock defines pll_get_post as soon as any test registers it, so
			// function_exists() is true for the rest of the process. Every
			// install fixture therefore registers a handler. The default pair
			// is the live one: English partial 17, German twin 6919.
			$twins = $existing['twins'] ?? array( 17 => array( 'de' => 6919 ) );
			WP_Mock::userFunction(
				'pll_get_post',
				array(
					'return' => static function ( int $id, string $language ) use ( $twins ): int {
						return (int) ( $twins[ $id ][ $language ] ?? 0 );
					},
				)
			);
	}

	/**
	 * The option store behind get_option/update_option/delete_option, reading
	 * and writing the test's $options array (WP's convention: an absent
	 * option answers with the default, false when none is given).
	 */
	private function mock_option_store(): void {
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => function ( string $name, $fallback = false ) {
					return array_key_exists( $name, $this->options ) ? $this->options[ $name ] : $fallback;
				},
			)
		);
		WP_Mock::userFunction(
			'update_option',
			array(
				'return' => function ( string $name, $value, $autoload = null ): bool { // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter.FoundAfterLastUsed -- update_option's third argument, mirrored for the call shape.
					$this->options[ $name ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_option',
			array(
				'return' => function ( string $name ): bool {
					unset( $this->options[ $name ] );
					return true;
				},
			)
		);
	}

	/**
	 * The stored rows as WP_Post objects, the shape get_posts returns.
	 *
	 * @param array<int, array<string, mixed>> $rows Stored rows.
	 * @param string                           $type Post type of the fixtures.
	 * @return list<WP_Post>
	 */
	private static function wp_posts( array $rows, string $type = 'lc_dynamic_template' ): array {
		$posts = array();
		foreach ( $rows as $row ) {
			$posts[] = new WP_Post(
				(object) array(
					'ID'           => (int) $row['ID'],
					'post_title'   => (string) ( $row['post_title'] ?? '' ),
					'post_name'    => (string) ( $row['post_name'] ?? '' ),
					'post_content' => (string) ( $row['post_content'] ?? '' ),
					'post_type'    => (string) ( $row['post_type'] ?? $type ),
					'post_status'  => (string) ( $row['post_status'] ?? 'publish' ),
					'post_date'    => (string) ( $row['post_date'] ?? '2026-10-01 09:00:00' ),
				)
			);
		}
		return $posts;
	}
}
