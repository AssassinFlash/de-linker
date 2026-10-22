<?php
/**
 * Synthetic service capability scoped to a local fixture's PHP process.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

/** Never writes configuration, replaces an existing token or contacts a provider. */
final class AssessmentFixtureEnvironment {
	/**
	 * Enable the simulated service only for the lifetime of this local process.
	 *
	 * @throws \RuntimeException Refuse a nonlocal WordPress runtime.
	 */
	public static function configure(): void {
		if ( 'local' !== wp_get_environment_type() ) {
			throw new \RuntimeException( 'Assessment fixtures require a local WordPress runtime.' );
		}
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', bin2hex( random_bytes( 32 ) ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Existing production constant, synthetic value only within this isolated test process.
		}
	}
}
