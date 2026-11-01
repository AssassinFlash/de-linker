<?php
/**
 * Typed installation metadata binding and withdrawal.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Publication\InstallationFacts;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Installation facts tests.
 *
 * @covers \Linker\Commerce\Products\Publication\InstallationFacts
 */
final class InstallationFactsTest extends TestCase {
	/**
	 * Stored declaration under test.
	 *
	 * @var array<string,mixed>
	 */
	private array $stored;

	/** Prepare one valid source-backed declaration. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__' )->andReturnArg( 0 );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( static fn ( string $url, int $part ): mixed => parse_url( $url, $part ) );
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string|false => json_encode( $value, $flags ) );
		$this->stored = array(
			'schema_version' => 1,
			'items'          => array( $this->row() ),
		);
	}

	/** A valid declaration retains its exact source semantics. */
	public function test_documented_projection_keeps_quote_and_exact_bytes(): void {
		WP_Mock::userFunction( 'get_post_meta' )->once()->with( 41, InstallationFacts::META_KEY, true )->andReturn( $this->stored );

		$projection = InstallationFacts::projection( 41, $this->manifest() );
		self::assertIsArray( $projection );

		$this->assertSame( 'documented', $projection['status'] );
		$this->assertSame( 'site_engineering_required', $projection['items'][0]['handling'] );
		$this->assertSame( 12, $projection['items'][0]['source']['page'] );
		$this->assertSame( str_repeat( 'b', 64 ), $projection['items'][0]['source']['blob_sha256'] );
		$this->assertSame( 'Recommended PV conductor 4-6 mm²', $projection['items'][0]['source']['quote'] );
		$this->assertSame( 'https://de-linker.com/manual.pdf', $projection['items'][0]['source']['url'] );
		$this->assertIsObject( $projection['items'][0]['specification'] );
		$encoded = json_decode( (string) wp_json_encode( $projection['items'][0]['specification'] ), true );
		$this->assertSame( 'pv_dc', $encoded['terminal_domain'] );
		$this->assertSame( array( 'PV1', 'PV2' ), $encoded['terminals'] );
	}

	/** Only an identified communication terminal can carry a documented use. */
	public function test_communication_use_requires_a_manufacturer_terminal(): void {
		$row                  = $this->row();
		$row['basis']         = 'manufacturer_terminal_map';
		$row['specification'] = array(
			'terminal_domain' => 'communication',
			'terminals'       => array( 'COM1' ),
			'terminal_use'    => 'external_communication',
		);
		$fact                 = InstallationFacts::bind( 41, $row, $this->manifest() );
		$this->assertSame( 'external_communication', $fact['specification']->terminal_use );

		$row['basis'] = 'manufacturer_recommended_conductor';
		$this->expectException( \RuntimeException::class );
		InstallationFacts::bind( 41, $row, $this->manifest() );
	}

	/** An empty specification remains an object in the projected JSON. */
	public function test_empty_specification_encodes_as_object(): void {
		$row                  = $this->row();
		$row['specification'] = array();
		WP_Mock::userFunction( 'get_post_meta' )->once()->with( 41, InstallationFacts::META_KEY, true )->andReturn(
			array(
				'schema_version' => 1,
				'items'          => array( $row ),
			)
		);

		$projection = InstallationFacts::projection( 41, $this->manifest() );
		self::assertIsArray( $projection );

		$this->assertIsObject( $projection['items'][0]['specification'] );
		$this->assertSame( '{}', wp_json_encode( $projection['items'][0]['specification'] ) );
	}

	/** Stale document evidence withdraws the whole projection. */
	public function test_stale_revision_withdraws_every_fact(): void {
		$this->stored['items'][0]['source']['document_revision'] = str_repeat( 'c', 64 );
		WP_Mock::userFunction( 'get_post_meta' )->once()->with( 41, InstallationFacts::META_KEY, true )->andReturn( $this->stored );

		$this->assertSame(
			array(
				'status' => 'unresolved',
				'items'  => array(),
			),
			InstallationFacts::projection( 41, $this->manifest() )
		);
	}

	/** A document bound to another product is rejected. */
	public function test_wrong_product_document_fails(): void {
		$row                          = $this->row();
		$row['source']['document_id'] = 'doc-other';

		$this->expectException( \RuntimeException::class );
		$this->expectExceptionMessage( 'current product document' );
		InstallationFacts::bind( 41, $row, $this->manifest() );
	}

	/** Invalid domain and language gaps are rejected. */
	public function test_wrong_domain_and_nonlocalized_condition_fail(): void {
		$row                                     = $this->row();
		$row['specification']['terminal_domain'] = 'pv';
		try {
			InstallationFacts::bind( 41, $row, $this->manifest() );
			$this->fail( 'An invalid domain must be rejected.' );
		} catch ( \RuntimeException $error ) {
			$this->assertSame( 'Installation specifications must retain their typed terminal and requirement semantics.', $error->getMessage() );
		}

		$row                 = $this->row();
		$row['conditions'][] = array( 'en' => 'Local rule may apply' );
		try {
			InstallationFacts::bind( 41, $row, $this->manifest() );
			$this->fail( 'A German-only gap must be rejected.' );
		} catch ( \RuntimeException $error ) {
			$this->assertSame( 'Installation conditions need English and German text.', $error->getMessage() );
		}
	}

	/** An optional fact remains an assessment obligation. */
	public function test_optional_fact_is_not_downgraded_to_a_documented_inclusion(): void {
		$row                  = $this->row();
		$row['handling']      = 'site_engineering_required';
		$row['quantity']      = null;
		$row['specification'] = array( 'rating_note' => 'Type I+II optional, selected only after local assessment' );

		$bound = InstallationFacts::bind( 41, $row, $this->manifest() );

		$this->assertSame( 'site_engineering_required', $bound['handling'] );
		$this->assertNull( $bound['quantity'] );
	}

	/** Every non-finite, explicit-null or out-of-contract field withdraws all facts. */
	public function test_typed_alignment_failures_withdraw_the_projection(): void {
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing( fn(): array => $this->stored );
		$cases = array();

		$row                         = $this->row();
		$row['quantity']             = INF;
		$row['unit']                 = 'm';
		$cases['infinite quantity']  = $row;
		$row                         = $this->row();
		$row['quantity']             = NAN;
		$cases['nan quantity']       = $row;
		$row                         = $this->row();
		$row['quantity']             = 9007199254740992.0;
		$row['unit']                 = 'm';
		$cases['quantity above max'] = $row;
		$row                         = $this->row();
		$row['source']['page']       = 9007199254740992;
		$cases['page above max']     = $row;
		$row                         = $this->row();
		$row['source']['quote']      = str_repeat( 'x', 2001 );
		$cases['quote too long']     = $row;
		$row                         = $this->row();
		$row['source']['quote']      = "   \t";
		$cases['blank quote']        = $row;

		$row = $this->row();
		$row['specification']['recommended_conductor_mm2']['low'] = NAN;
		$cases['nan interval']                                    = $row;
		$row = $this->row();
		$row['specification']['cable_od_mm']['high'] = INF;
		$cases['infinite interval']                  = $row;
		$row = $this->row();
		$row['specification']['cable_od_mm']['extra'] = 1;
		$cases['interval extra key']                  = $row;
		$row                                       = $this->row();
		$row['specification']['minimum_voltage_v'] = INF;
		$cases['infinite voltage']                 = $row;
		$row                                       = $this->row();
		$row['specification']['minimum_current_a'] = NAN;
		$cases['nan current']                      = $row;
		$row                                       = $this->row();
		$row['specification']['terminal_domain']   = null;
		$cases['null terminal domain']             = $row;
		$row                                       = $this->row();
		$row['specification']['terminals']         = null;
		$cases['null terminals']                   = $row;
		$row                                       = $this->row();
		$row['specification']['rating_note']       = null;
		$cases['null rating note']                 = $row;

		foreach ( $cases as $case ) {
			$this->stored['items'] = array( $case );
			$this->assertSame(
				array(
					'status' => 'unresolved',
					'items'  => array(),
				),
				InstallationFacts::projection( 41, $this->manifest() )
			);
		}
	}

		/**
		 * Return the synthetic source-backed row.
		 *
		 * @return array<string,mixed>
		 */
	private function row(): array {
		return array(
			'id'            => 'pv-terminal',
			'handling'      => 'site_engineering_required',
			'label'         => array(
				'en' => 'PV terminal specification',
				'de' => 'PV-Anschluss Spezifikation',
			),
			'quantity'      => null,
			'unit'          => 'piece',
			'basis'         => 'manufacturer_recommended_conductor',
			'specification' => array(
				'terminal_domain'           => 'pv_dc',
				'terminals'                 => array( 'PV1', 'PV2' ),
				'recommended_conductor_mm2' => array(
					'low'  => 4,
					'high' => 6,
				),
				'cable_od_mm'               => array(
					'low'  => 4.7,
					'high' => 6.4,
				),
			),
			'conditions'    => array(),
			'source'        => array(
				'document_id'       => 'doc-a',
				'document_revision' => str_repeat( 'a', 64 ),
				'blob_sha256'       => str_repeat( 'b', 64 ),
				'product_id'        => 41,
				'page'              => 12,
				'quote'             => 'Recommended PV conductor 4-6 mm²',
			),
		);
	}

		/**
		 * Return the synthetic current publication assembly.
		 *
		 * @return array<string,mixed>
		 */
	private function manifest(): array {
		return array(
			'products'  => array( array( 'product_id' => 41 ) ),
			'documents' => array(
				array(
					'document_id'       => 'doc-a',
					'document_revision' => str_repeat( 'a', 64 ),
					'blob_sha256'       => str_repeat( 'b', 64 ),
					'product_ids'       => array( 41 ),
					'url'               => 'https://de-linker.com/manual.pdf',
				),
				array(
					'document_id'       => 'doc-other',
					'document_revision' => str_repeat( 'd', 64 ),
					'blob_sha256'       => str_repeat( 'e', 64 ),
					'product_ids'       => array( 42 ),
					'url'               => 'https://de-linker.com/other.pdf',
				),
			),
		);
	}
}
