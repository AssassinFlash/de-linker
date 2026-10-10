<?php
/**
 * WooCommerce's feature compatibility registry for the unit tests: each
 * declaration fires linker_test_feature_declared, which tests expect.
 *
 * @package Linker\Commerce
 */

// phpcs:disable -- a test double mirrors WooCommerce's own class name and signature.

namespace Automattic\WooCommerce\Utilities;

if ( ! class_exists( FeaturesUtil::class ) ) {
	class FeaturesUtil {
		public static function declare_compatibility( string $feature_id, string $plugin_file, bool $positive_compatibility = true ): bool {
			do_action( 'linker_test_feature_declared', $feature_id, $plugin_file, $positive_compatibility );
			return true;
		}
	}
}
