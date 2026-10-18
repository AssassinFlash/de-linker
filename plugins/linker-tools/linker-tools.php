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

use Linker\Tools\Configurator\EngineProxy;
use Linker\Tools\Configurator\Mount;
use Linker\Tools\Genie\ContactRequest;
use Linker\Tools\Genie\ConversationMail;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Entries;
use Linker\Tools\Genie\InquiryRequest;
use Linker\Tools\Genie\InquirySummary;
use Linker\Tools\Genie\PageContext;
use Linker\Tools\Genie\Preview;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\QualityPage;
use Linker\Tools\Genie\QualityRoute;
use Linker\Tools\Genie\QualityStore;
use Linker\Tools\Genie\Retention;
use Linker\Tools\Genie\Thread;
use Linker\Tools\Genie\UserContext;
use Linker\Tools\Genie\WindPress;

defined( 'ABSPATH' ) || exit;

require_once __DIR__ . '/vendor/autoload.php';
// Ahead of Composer's classmap: a request that meets a switched tree still
// loads this plugin's classes (the 2026-10-18 deploy-window fatals).
\Linker\Tools\Autoload::register();

$conversations = new Conversations(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used four times below.
$thread        = new Thread(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used four times below.
$mail          = new ConversationMail( $conversations, $thread ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used twice below.
$quality       = new QualityStore(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used three times below.
$page_context  = new PageContext(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used four times below.
$genie_preview = new Preview( $page_context ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- bootstrap scope, used twice below.
( new Plugin(
	new Assets( __FILE__ ),
	new Redirects(),
	new SiteChrome( __FILE__ ),
	$conversations,
	new Proxy( $conversations, null, $thread, null, $page_context, $mail ),
	new Entries( __FILE__, $page_context, $genie_preview ),
	new Retention( __FILE__ ),
	new UserContext(),
	new WindPress(),
	new Mount(),
	new EngineProxy(),
	$quality,
	new QualityRoute( $quality ),
	new QualityPage( $quality, $thread ),
	$genie_preview,
	$mail,
	new ContactRequest( $conversations, $thread, $page_context ),
	new InquirySummary( $conversations, $thread ),
	new InquiryRequest( $conversations, $thread, $page_context )
) )->register();
