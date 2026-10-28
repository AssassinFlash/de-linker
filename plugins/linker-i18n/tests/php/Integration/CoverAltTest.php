<?php
/**
 * Blog-cover translation against WordPress, Polylang and LiveCanvas.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

/** Tests only temporary posts and attachments; the translator is a local double. */
final class CoverAltTest extends SiteTestCase {
	/** Shared images, source changes and stale jobs preserve the displayed truth. */
	public function test_cover_lifecycle_and_native_attribute(): void {
		$result = self::php(
			'try { return require $input["fixture"]; } catch ( Throwable $error ) { return array( "error" => get_class( $error ) . ": " . $error->getMessage() . " at " . $error->getFile() . ":" . $error->getLine() ); }',
			array( 'fixture' => __DIR__ . '/fixtures/cover-lifecycle.fixture' )
		);
		$this->assertIsArray( $result );
		$this->assertArrayNotHasKey( 'error', $result, (string) ( $result['error'] ?? '' ) );
		$this->assertSame( 'passed', $result['result'] );
		$this->assertStringContainsString( '&quot;', $result['native_with_quotes'] );
		$this->assertStringContainsString( '&amp;', $result['native_with_quotes'] );
		$this->assertSame( '', $result['native_empty_alt'] );
	}
}
