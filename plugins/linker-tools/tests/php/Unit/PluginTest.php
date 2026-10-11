<?php
/**
 * Tests for the plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Assets;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\Retention;
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
	 * the proxy on rest_api_init, and the entries', the retention's and the
	 * scan provider's hooks during registration.
	 */
	public function test_register_adds_the_hooks(): void {
		$assets        = new Assets( self::FILE );
		$redirects     = new Redirects();
		$chrome        = new SiteChrome( self::FILE );
		$conversations = new RecordingConversations();
		$proxy         = new RecordingProxy( $conversations );
		$entries       = new RecordingEntries( self::FILE );
		$retention     = new Retention( self::FILE );
		$windpress     = new WindPress();

		WP_Mock::expectActionAdded( 'init', array( $assets, 'register' ) );
		WP_Mock::expectActionAdded( 'init', array( $assets, 'load_text_domain' ) );
		WP_Mock::expectActionAdded( 'init', array( $conversations, 'register' ) );
		WP_Mock::expectActionAdded( 'rest_api_init', array( $proxy, 'register' ) );
		// Priority 1: the retired addresses answer ahead of WordPress's own
		// canonical redirects (Redirects::register()).
		WP_Mock::expectActionAdded( 'template_redirect', WP_Mock\Functions::type( 'Closure' ), 1 );
		WP_Mock::expectActionAdded( 'wp_enqueue_scripts', array( $chrome, 'assets' ) );
		WP_Mock::expectActionAdded( 'init', array( $retention, 'schedule' ) );
		WP_Mock::expectActionAdded( Retention::HOOK, array( $retention, 'sweep' ) );
		WP_Mock::expectActionAdded( Retention::DELETE_HOOK, array( $retention, 'delete' ) );
		WP_Mock::expectFilterAdded( 'f!windpress/core/cache:compile.providers', array( $windpress, 'providers' ) );
		WP_Mock::userFunction( 'register_deactivation_hook' );

		( new Plugin( $assets, $redirects, $chrome, $conversations, $proxy, $entries, $retention, $windpress ) )->register();

		$this->assertSame( array( 'registered' ), $entries->calls );
		$this->assertConditionsMet();
	}
}
