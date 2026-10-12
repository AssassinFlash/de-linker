<?php
/**
 * Plugin bootstrap.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

use Linker\Tools\Configurator\Mount;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\Retention;
use Linker\Tools\Genie\UserContext;
use Linker\Tools\Genie\WindPress;

/**
 * Hooks Linker Tools into WordPress.
 */
final class Plugin {

	/**
	 * Sets up the plugin.
	 *
	 * @param Assets        $assets        Registers the built apps as scripts.
	 * @param Redirects     $redirects     Retires the tool entry addresses that moved.
	 * @param SiteChrome    $site_chrome   The chrome's scripts (menu images, hover).
	 * @param Conversations $conversations Conversation posts for Genie.
	 * @param Proxy         $proxy         REST proxy to the Genie service.
	 * @param Entries       $entries       Chips, dock and disclosure.
	 * @param Retention     $retention     Deletes expired guest conversations.
	 * @param UserContext   $user_context  The customer-identity seam.
	 * @param WindPress     $windpress     Scan provider for the entries' Tailwind classes.
	 * @param Mount         $mount         The Solution Configurator's mount point.
	 */
	public function __construct(
		private readonly Assets $assets,
		private readonly Redirects $redirects,
		private readonly SiteChrome $site_chrome,
		private readonly Conversations $conversations,
		private readonly Proxy $proxy,
		private readonly Entries $entries,
		private readonly Retention $retention,
		private readonly UserContext $user_context,
		private readonly WindPress $windpress,
		private readonly Mount $mount
	) {}

	/**
	 * Adds the plugin's hooks.
	 */
	public function register(): void {
		add_action( 'init', array( $this->assets, 'register' ) );
		add_action( 'init', array( $this->assets, 'load_text_domain' ) );
		add_action( 'init', array( $this->conversations, 'register' ) );
		add_action( 'rest_api_init', array( $this->proxy, 'register' ) );
		$this->redirects->register();
		$this->site_chrome->register();
		$this->entries->register();
		$this->retention->register();
		// Registered first in the bootstrap: `determine_current_user` must be
		// listening before anything asks who is making the request.
		$this->user_context->register();
		$this->windpress->register();
		$this->mount->register();
	}
}
