<?php
/**
 * The host-insensitivity of a figure entry's binding fingerprint.
 *
 * @package Linker\Commerce\Tests\Unit
 */

declare( strict_types=1 );

namespace Linker\Commerce\Tests\Unit\Products\Publication;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

final class FigureRevisionTest extends TestCase {

	/**
	 * The WordPress URL and JSON helpers the fingerprint hashing reads.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_json_encode' )
			->andReturnUsing( static fn ( mixed $value ): string => (string) json_encode( $value ) );
		WP_Mock::userFunction( 'wp_parse_url' )
			->andReturnUsing( static fn ( string $url, ?int $component = null ): mixed => parse_url( $url, $component ) );
	}

	/**
	 * A rewritten citation host keeps the figure's binding identity.
	 *
	 * A local instance's database rewrite replaces de-linker.com with its own
	 * host; the fact and the cited bytes are unchanged, so the fingerprint the
	 * evidence binding compares must not change with the host either.
	 */
	public function test_the_citation_host_does_not_change_the_fingerprint(): void {
		$production = array(
			'unit'     => 'W',
			'value'    => '10000',
			'citation' => array(
				'url'  => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf',
				'page' => 2,
			),
		);
		$local      = array(
			'unit'     => 'W',
			'value'    => '10000',
			'citation' => array(
				'url'  => 'http://127.0.0.1:8889/wp-content/uploads/2026/09/datasheet.pdf',
				'page' => 2,
			),
		);

		$this->assertNotSame( Publication::revision( $production ), Publication::revision( $local ) );
		$this->assertSame( Publication::figure_revision( $production ), Publication::figure_revision( $local ) );
	}

	/**
	 * Any other change to the entry still changes the fingerprint.
	 */
	public function test_a_changed_value_still_changes_the_fingerprint(): void {
		$one   = array(
			'value'    => '10000',
			'citation' => array( 'url' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf' ),
		);
		$other = array(
			'value'    => '11000',
			'citation' => array( 'url' => 'https://de-linker.com/wp-content/uploads/2026/09/datasheet.pdf' ),
		);

		$this->assertNotSame( Publication::figure_revision( $one ), Publication::figure_revision( $other ) );
	}

	/**
	 * An entry without a citation URL keeps revision semantics.
	 */
	public function test_an_entry_without_a_citation_url_falls_back_to_the_revision(): void {
		$entry = array( 'value' => '10000' );

		$this->assertSame( Publication::revision( $entry ), Publication::figure_revision( $entry ) );
	}
}
