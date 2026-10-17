<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Assets;
use Linker\Tools\Configurator\EngineProxy;
use Linker\Tools\Configurator\Mount;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\QualityPage;
use Linker\Tools\Genie\QualityRoute;
use Linker\Tools\Genie\QualityStore;
use Linker\Tools\Genie\Thread;
use Linker\Tools\Genie\Retention;
use Linker\Tools\Genie\UserContext;
use Linker\Tools\Genie\WindPress;
use Linker\Tools\Plugin;
use Linker\Tools\Redirects;
use Linker\Tools\SiteChrome;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for Plugin.
 *
 * @covers \Linker\Tools\Plugin
 */
final class PluginTest extends TestCase {


	private const FILE = '/srv/www/wp-content/plugins/linker-tools/linker-tools.php';

	/**
	 * The plugin registers its scripts, conversations, redirects and chrome,
	 * the proxy on rest_api_init, the entries' hooks, the retention's hooks, the
	 * identity seam and the scan provider's hooks during registration.
	 */
	public function test_register_adds_the_hooks(): void {
		$assets        = new Assets( self::FILE );
		$redirects     = new Redirects();
		$chrome        = new SiteChrome( self::FILE );
		$conversations = new RecordingConversations();
		$proxy         = new RecordingProxy( $conversations );
		$entries       = new RecordingEntries( self::FILE );
		$retention     = new Retention( self::FILE );
		$user_context  = new class() extends UserContext {
			/**
			 * Records instead of hooking.
			 *
			 * @var bool
			 */
			public bool $registered = false;

			/**
			 * Records the call.
			 */
			public function register(): void {
				$this->registered = true;
			}
		};
		$windpress     = new WindPress();
		$mount         = new Mount();
		$engine        = new EngineProxy();
		$quality       = new QualityStore();
		$quality_route = new QualityRoute( $quality, 'token' );
		$quality_page  = new QualityPage( $quality, new Thread() );

		WP_Mock::expectActionAdded( 'init', array( $assets, 'register' ) );
		WP_Mock::expectActionAdded( 'init', array( $assets, 'load_text_domain' ) );
		WP_Mock::expectActionAdded( 'init', array( $conversations, 'register' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $proxy, 'register' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $engine, 'register' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $quality_route, 'register' ) );
		WP_Mock::expectFilterAdded( QualityStore::SUMMARY_FILTER, array( $quality, 'filter_summary' ), 10, 2 );
		WP_Mock::expectActionAdded( 'admin_menu', array( $quality_page, 'menu' ) );
		// Priority 1: the retired addresses answer ahead of WordPress's own
		// canonical redirects (Redirects::register()).
		WP_Mock::expectActionAdded( 'template_redirect', WP_Mock\Functions::type( 'Closure' ), 1 );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $chrome, 'assets' ) );
		WP_Mock::expectActionAdded( 'init', array( $retention, 'schedule' ) );
		WP_Mock::expectActionAdded( Retention::HOOK, array( $retention, 'sweep' ) );
		WP_Mock::expectActionAdded( Retention::DELETE_HOOK, array( $retention, 'delete' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		// The configurator page's LiveCanvas template prints this shortcode.
		WP_Mock::userFunction(
			'add_shortcode',
			array(
				'times' => 1,
				'args'  => array( 'linker_configurator', array( $mount, 'shortcode' ) ),
			)
		);
		WP_Mock::userFunction( 'register_deactivation_hook' );

		( new Plugin( $assets, $redirects, $chrome, $conversations, $proxy, $entries, $retention, $user_context, $windpress, $mount, $engine, $quality, $quality_route, $quality_page ) )->register();

		$this->assertSame( array( 'registered' ), $entries->calls );
		$this->assertTrue( $user_context->registered, 'the identity seam is hooked' );
		$this->assertConditionsMet();
	}
}
