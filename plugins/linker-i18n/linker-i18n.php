<?php
/**
 * Plugin Name:       Linker i18n
 * Description:       Polylang companion for de-linker.com: one slug for English and German, German URL segments, German versions made on save, REST in one language, and the German shop on the English products.
 * Version:           0.3.0
 * Requires at least: 7.1
 * Requires PHP:      8.3
 * Requires Plugins:  polylang, woocommerce
 * Author:            Linker Technology GmbH
 * Text Domain:       linker-i18n
 * Domain Path:       /languages
 *
 * The production host runs WordPress 7.1.3 on PHP 8.3.33
 * (docs/research/2026-10-09/framework-choice.md §2).
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

defined( 'ABSPATH' ) || exit;

require_once __DIR__ . '/vendor/autoload.php';

( new Plugin( __FILE__ ) )->register();
