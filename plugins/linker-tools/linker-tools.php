<?php
/**
 * Plugin Name:       Linker Tools
 * Description:       Genie and Solution Configurator apps for de-linker.com.
 * Version:           0.1.0
 * Requires at least: 7.1
 * Requires PHP:      8.3
 * Author:            Linker Technology GmbH
 * Text Domain:       linker-tools
 * Domain Path:       /languages
 *
 * The production host runs WordPress 7.1.3 on PHP 8.3.33
 * (docs/research/2026-10-09/framework-choice.md §2).
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\Retention;

defined( 'ABSPATH' ) || exit;

require_once __DIR__ . '/vendor/autoload.php';

$conversations = new Conversations(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used twice below.
( new Plugin(
	new Assets( __FILE__ ),
	new Redirects(),
	new SiteChrome( __FILE__ ),
	$conversations,
	new Proxy( $conversations ),
	new Entries( __FILE__ ),
	new Retention( __FILE__ )
) )->register();
