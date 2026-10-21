<?php
/**
 * Plugin Name:       Linker Commerce
 * Description:       Inquiry chain, product facts and Abilities for de-linker.com.
 * Version:           0.2.0
 * Requires at least: 7.1
 * Requires PHP:      8.3
 * Author:            Linker Technology GmbH
 * Text Domain:       linker-commerce
 * Domain Path:       /languages
 *
 * The production host runs WordPress 7.1.3 on PHP 8.3.33
 * (docs/research/2026-10-09/framework-choice.md §2).
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce;

defined( 'ABSPATH' ) || exit;

require_once __DIR__ . '/vendor/autoload.php';
// Ahead of Composer's classmap: a request that meets a switched tree still
// loads this plugin's classes (the 2026-10-18 deploy-window fatals).
\Linker\Commerce\Autoload::register();
require_once __DIR__ . '/includes/Presentation/template-functions.php';

// One store of saved solutions: the account module owns the pages, and the
// read ability (#496) reads the same posts.
$linker_commerce_solutions = new Account\SavedSolutions(
	new Account\PrivateFiles( Account\SavedSolutions::REPORTS_DIRECTORY ),
	plugin_dir_path( __FILE__ ) . 'templates/'
);

( new Plugin(
	__FILE__,
	new Abilities\Registrar( __FILE__, $linker_commerce_solutions ),
	new Products\SelectionFactsController(),
	new Products\EngineeringFeedController(),
	new Products\ProductSearchController(),
	new Products\SearchScope(),
	new Contact\Module(),
	new Admin\FiguresMetaBox(),
	new Admin\FaqsMetaBox(),
	new Admin\DocumentsMetaBox(),
	$linker_commerce_solutions
) )->register();
