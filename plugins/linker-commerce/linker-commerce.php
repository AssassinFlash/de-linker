<?php
/**
 * Plugin Name:       Linker Commerce
 * Description:       Inquiry chain, product facts and Abilities for de-linker.com.
 * Version:           0.1.0
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

( new Plugin( __FILE__ ) )->register();
