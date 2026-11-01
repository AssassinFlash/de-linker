<?php
/**
 * Tests for the compatibility contract's pattern matching.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Products;

use Linker\Commerce\Products\Compatibility;
use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\CompatibilityClaims;
use Linker\Commerce\Products\Publication\CompatibilityEditor;
use Linker\Commerce\Products\Publication\CompatibilityMigration;
use Linker\Commerce\Products\Publication\DocumentFiles;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Reuse the known manufacturer verdicts after one-time migration to Woo.
 *
 * @covers \Linker\Commerce\Products\Compatibility
 * @covers \Linker\Commerce\Products\Publication\CompatibilityClaims
 * @covers \Linker\Commerce\Products\Publication\CompatibilityMigration
 * @covers \Linker\Commerce\Products\Publication\CompatibilityEditor
 */
final class CompatibilityTest extends TestCase {

	/** Synthetic current Woo authority.
	 *
	 * @var array<string,mixed>
	 */
	private array $manifest;

	/** Native declaration values.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $claims = array();

	/** Migrate retained decisions into synthetic Woo records, without a WP writer. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_json_encode' )->andReturnUsing( static fn ( mixed $value, int $flags = 0 ): string => (string) json_encode( $value, $flags ) );
		WP_Mock::userFunction( 'wp_parse_url' )->andReturnUsing( static fn ( string $url, int $part = -1 ): mixed => parse_url( $url, $part ) );
		WP_Mock::userFunction( 'has_filter' )->andReturn( false );
		WP_Mock::userFunction( 'sanitize_text_field' )->andReturnUsing( static fn ( string $value ): string => trim( $value ) );
		WP_Mock::userFunction( 'sanitize_textarea_field' )->andReturnUsing( static fn ( string $value ): string => trim( $value ) );
		WP_Mock::userFunction( 'get_post_meta' )->andReturnUsing( fn ( int $id, string $key ): mixed => CompatibilityClaims::META_KEY === $key ? ( $this->claims[ $id ] ?? '' ) : '' );
		WP_Mock::userFunction( 'metadata_exists' )->andReturnUsing( fn ( string $type, int $id, string $key ): bool => CompatibilityClaims::META_KEY === $key && isset( $this->claims[ $id ] ) );
		$fixture  = json_decode( (string) file_get_contents( dirname( __DIR__, 6 ) . '/services/engine/tests/fixtures/feed.json' ), true );
		$products = array();
		foreach ( $fixture['products'] as $product ) {
			$products[ $product['model'] ] = array(
				'product_id' => $product['id'],
				'model'      => $product['model'],
			);
		}
		$models = array( 'BC2-HV1', 'SEC3000C', 'DTSU666', 'EF BD-B-S1', 'EF HD-P1-10K0-S2' );
		foreach ( $this->known_pairs() as $pair ) {
			$models = array_merge( $models, array_slice( $pair, 0, 2 ) );
		}
		foreach ( $this->on_sale_etr_models() as $model ) {
			$models[] = $model[0];
		}
		foreach ( array_unique( $models ) as $i => $model ) {
			$products[ $model ] ??= array(
				'product_id' => 90000 + $i,
				'model'      => $model,
			);
		}
		$products = array_intersect_key( $products, array_flip( $models ) );
		$input    = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		$this->assertIsArray( $input );
		$documents = array();
		foreach ( array_merge( $input['pairs'], $input['requirements'] ) as $row ) {
			foreach ( $row['documents'] as $doc ) {
				$id               = DocumentFiles::id( $doc['url'] );
				$documents[ $id ] = array(
					'document_id'       => $id,
					'document_revision' => $id,
					'blob_sha256'       => $id,
					'url'               => $doc['url'],
					'product_ids'       => array_column( $products, 'product_id' ),
				);
			}
		}
		$this->manifest = array(
			'source_revision' => 'fixture',
			'products'        => array_values( $products ),
			'documents'       => array_values( $documents ),
		);
		foreach ( CompatibilityMigration::plan( $input, str_repeat( 'a', 64 ), $this->manifest )['changes'] as $change ) {
			$this->claims[ $change['product_id'] ] = $change['after'];
		}
	}

	/**
	 * Ten known inverter-and-battery pairs decide to the verdict their old
	 * contract cell states, including released_with_accessory and
	 * not_released (the ticket's acceptance line).
	 *
	 * @dataProvider known_pairs
	 *
	 * @param string      $inverter The inverter model (pa_model).
	 * @param string      $battery  The battery model (pa_model).
	 * @param string|null $verdict  The verdict, null when no entry matches.
	 */
	public function test_known_pairs_decide_their_verdict( string $inverter, string $battery, ?string $verdict ): void {
		$answer = Compatibility::for_models( $inverter, $battery, $this->manifest );

		if ( null === $verdict ) {
			$this->assertNull( $answer );

			return;
		}
		$this->assertNotNull( $answer );
		$this->assertSame( $verdict, $answer['verdict'] );
		$this->assertNotSame( array(), $answer['conditions'] );
		$this->assertNotSame( array(), $answer['documents'] );
	}

	/**
	 * The pairs: model names as the products' pa_model terms state them.
	 *
	 * @return list<array{string, string, string|null}>
	 */
	public function known_pairs(): array {
		return array(
			// gw-et-5-10|pyl-fh2: one_way -> released with the one-way condition.
			array( 'GW10K-ET', 'FH9637M', 'released' ),
			// gw-et-5-10|gw-lynx-d: listed.
			array( 'GW10K-ET', 'LX D5.0-10', 'released' ),
			// gw-et-5-10|pyl-fh1: not_listed -> not_released.
			array( 'GW10K-ET', 'FH48074', 'not_released' ),
			// saj-h2-t3|saj-bat: the B2 set runs through the BC2-HV1 control module.
			array( 'H2-10K-T3', 'B2-10.0-HV1', 'released_with_accessory' ),
			array( 'H2-10K-T3', 'BU2-5.0-HV1', 'released_with_accessory' ),
			// The one-module B2-5.0 runs below the H2 battery window (#481).
			array( 'H2-10K-T3', 'B2-5.0-HV1', 'not_released' ),
			// eco-po|eco-po-b: every tower takes the battery base article.
			array( 'EF HD-P1-5K-S1', 'EF BD-5.1-S1', 'released_with_accessory' ),
			// eco-ocean2-p3|eco-ocean2-bat: listed; the junction box is a condition of cascading.
			array( 'EF HD-P3-10K0-S2', 'EF BD-5-S2', 'released' ),
			// gw-etr-125k: listed and one_way.
			array( 'GW125K-ETR-G10', 'GW261.2-BAT-LCD-G10', 'released' ),
			array( 'GW125K-ETR-G10', 'GW208.9-BAT-LCD-G10', 'released' ),
			// saj-ek90-hs5|saj-ek90-bu5: the EK90 box is in the model names themselves.
			array( 'EK90 HS5-8K-T3-X', 'EK90 BU5-6.0-TV', 'released' ),
			// saj-hs2|saj-bat, scoped to BU2-5.0-HV1/5.
			array( 'HS2-10K-T2-X', 'BU2-5.0-HV1', 'released' ),
			// saj-hs2 with a battery family no cell releases for it.
			array( 'HS2-10K-T2-X', 'FH9637M', 'not_released' ),
			// gw-esa-eha|gw-esa-bat-g20: the ESA's own modules.
			array( 'GW5K-ETA-G20', 'GW6.0-BAT-D-G20', 'released' ),
			// An inverter the contract does not know answers nothing.
			array( 'GEN24 5.0', 'FH9637M', null ),
		);
	}

	/**
	 * Conditions are bilingual objects (the file folds the old parallel
	 * arrays), and documents are the slim {url, page?} references.
	 */
	public function test_conditions_are_bilingual_and_documents_are_slim(): void {
		$answer = Compatibility::for_models( 'GW10K-ET', 'FH9637M', $this->manifest );

		$this->assertNotNull( $answer );
		foreach ( $answer['conditions'] as $condition ) {
			$this->assertNotSame( '', $condition['en'] );
			$this->assertNotSame( '', $condition['de'] );
		}
		foreach ( $answer['documents'] as $document ) {
			$this->assertStringStartsWith( 'https://de-linker.com/', $document['url'] );
			$keys = array_keys( $document );
			$this->assertNotContains( 'title', $keys, 'documents carry no titles' );
			$this->assertNotContains( 'title_de', $keys, 'documents carry no German titles' );
		}
	}

	/**
	 * A released_with_accessory answer names the accessory the documents
	 * require: model pattern, quantity and what it is per.
	 */
	public function test_released_with_accessory_names_its_accessory(): void {
		$answer = Compatibility::for_models( 'H2-10K-T3', 'B2-10.0-HV1', $this->manifest );

		$this->assertNotNull( $answer );
		$this->assertSame(
			array(
				'product_id' => $this->product_id( 'BC2-HV1' ),
				'model'      => '^BC2\-HV1$',
				'quantity'   => 1,
				'per'        => 'system',
			),
			$answer['accessories'][0]
		);
		$ecoflow = Compatibility::for_models( 'EF HD-P1-5K-S1', 'EF BD-5.1-S1', $this->manifest );
		$this->assertNotNull( $ecoflow );
		$this->assertSame( '^EF BD\-B\-S1$', $ecoflow['accessories'][0]['model'] );
		$this->assertSame( 'stack', $ecoflow['accessories'][0]['per'] );
	}

	/**
	 * The not_released B2-5.0 names no accessory (#481): one module is not a
	 * released configuration, so the BC2-HV1 line drops.
	 */
	public function test_the_not_released_b2_5_0_names_no_bc2_accessory(): void {
		$answer = Compatibility::for_models( 'H2-10K-T3', 'B2-5.0-HV1', $this->manifest );

		$this->assertNotNull( $answer );
		$this->assertSame( 'not_released', $answer['verdict'] );
		$this->assertSame( array(), $answer['accessories'] );
	}

	/**
	 * The model-level entry joins with its family entry, the way the engine
	 * reads the file: the OCEAN 2 battery-model condition is part of the
	 * answer beside the family constraint.
	 */
	public function test_the_model_level_entry_joins_its_family_entry(): void {
		$answer = Compatibility::for_models( 'EF HD-P3-10K0-S2', 'EF BD-5-S2', $this->manifest );

		$this->assertNotNull( $answer );
		$joined = implode( "\n", array_column( $answer['conditions'], 'en' ) );
		$this->assertStringContainsString( 'The OCEAN 2 three-phase datasheet (p. 3) lists EF BD-5-S2 for its battery system.', $joined );
		$this->assertStringContainsString( 'junction box EF BD-JC-S2', $joined );
	}

	/**
	 * When entries that match disagree, the most restrictive verdict wins
	 * (not_released < released_with_accessory < released): the single-phase
	 * PowerOcean inverter joins its not_released model entry with the
	 * released_with_accessory family entry.
	 */
	public function test_the_most_restrictive_verdict_wins(): void {
		$answer = Compatibility::for_models( 'EF HD-P1-10K0-S2', 'EF BD-5.1-S1', $this->manifest );

		$this->assertNotNull( $answer );
		$this->assertSame( 'not_released', $answer['verdict'] );
		$joined = implode( "\n", array_column( $answer['conditions'], 'en' ) );
		$this->assertStringContainsString( 'The cited documents do not list this pair.', $joined );
		$this->assertStringContainsString( 'single-phase datasheet (p. 1)', $joined );
	}

	/**
	 * Every pattern of the file compiles: a malformed pattern would be loud
	 * in production (PHP warns) and match nothing here, so it must be seen.
	 */
	public function test_every_pattern_of_the_file_compiles(): void {
		$patterns = array();
		foreach ( Compatibility::pairs( $this->manifest ) as $pair ) {
			$patterns[] = (string) $pair['inverter'];
			$patterns[] = (string) $pair['battery'];
		}
		$this->assertNotEmpty( $patterns );
		foreach ( $patterns as $index => $pattern ) {
			// The point is the compile failure; the silencer hides PHP's warning so it can be asserted instead.
			// phpcs:ignore WordPress.PHP.NoSilencedErrors.Discouraged
			$result = @preg_match( '{' . $pattern . '}', 'anything' );
			$this->assertNotFalse( $result, "pattern #{$index} of the file does not compile: {$pattern}" );
		}
	}

	/**
	 * Every verdict the file states is one of the three.
	 */
	public function test_the_file_states_known_verdicts(): void {
		$verdicts = array();
		foreach ( Compatibility::pairs( $this->manifest ) as $pair ) {
			$verdicts[ $pair['verdict'] ] = true;
		}
		$this->assertSame( array(), array_values( array_diff( array_keys( $verdicts ), Compatibility::VERDICTS ) ) );
		$this->assertEqualsCanonicalizing( Compatibility::VERDICTS, array_keys( $verdicts ) );
	}

	/**
	 * Every on-sale ETR model hits the parallel_controller requirement: one
	 * SEC3000C per system. The pattern matches the bare pa_model name — a
	 * brand prefix would leave all six without the requirement.
	 *
	 * @dataProvider on_sale_etr_models
	 *
	 * @param string $inverter The inverter model (pa_model).
	 */
	public function test_the_parallel_controller_requirement_hits_every_on_sale_etr( string $inverter ): void {
		$answer = Compatibility::requirements( $inverter, 'parallel_controller', null, $this->manifest );

		$this->assertCount( 1, $answer, "exactly one parallel_controller requirement for {$inverter}" );
		$this->assertSame( 'parallel_controller', $answer[0]['kind'] );
		$this->assertFalse( (bool) $answer[0]['included'] );
		$this->assertSame(
			array(
				'product_id' => $this->product_id( 'SEC3000C' ),
				'model'      => '^SEC3000C$',
				'quantity'   => 1,
				'per'        => 'system',
			),
			$answer[0]['accessories'][0]
		);
		$this->assertNotSame( array(), $answer[0]['conditions'] );
		$this->assertNotSame( array(), $answer[0]['documents'] );
	}

	/**
	 * The six on-sale ETR models, as the products' pa_model terms state them.
	 *
	 * @return list<list<string>>
	 */
	public function on_sale_etr_models(): array {
		return array(
			array( 'GW80K-ETR-G10' ),
			array( 'GW99.99K-ETR-G10' ),
			array( 'GW100K-ETR-G10' ),
			array( 'GW110K-ETR-G10' ),
			array( 'GW124.99K-ETR-G10' ),
			array( 'GW125K-ETR-G10' ),
		);
	}

	/** Exact canonical IDs keep their release when a model label is edited. */
	public function test_for_products_keeps_identity_on_a_model_rename(): void {
		$inverter = $this->product_id( 'H2-10K-T3' );
		$battery  = $this->product_id( 'B2-10.0-HV1' );
		foreach ( $this->manifest['products'] as &$product ) {
			if ( $inverter === $product['product_id'] ) {
				$product['model'] = 'Renamed inverter';
			}
		}
		unset( $product );
		$answer = Compatibility::for_products( $inverter, $battery, $this->manifest );
		$this->assertNotNull( $answer );
		$this->assertSame( 'released_with_accessory', $answer['verdict'] );
		$this->manifest['products'][] = array(
			'product_id' => 999999,
			'model'      => 'Renamed inverter',
		);
		$this->assertNull( Compatibility::for_models( 'Renamed inverter', 'B2-10.0-HV1', $this->manifest ) );
		$this->assertNull( Compatibility::for_products( 999999, $battery, $this->manifest ) );
	}

	/** A stale restrictive row cannot disappear and expose a positive overlap. */
	public function test_replaced_document_revokes_the_entire_pair_scope(): void {
		$inverter                             = $this->product_id( 'H2-10K-T3' );
		$battery                              = $this->product_id( 'B2-10.0-HV1' );
		$row                                  = array_values( array_filter( $this->claims[ $inverter ]['pairs'], static fn ( array $row ): bool => $battery === $row['battery_product_id'] ) )[0];
		$stale                                = $row;
		$stale['id']                          = 'stale-restriction';
		$stale['verdict']                     = 'not_released';
		$stale['documents'][0]['blob_sha256'] = str_repeat( 'b', 64 );
		$this->claims[ $inverter ]['pairs']   = array( $row, $stale );
		$this->assertNull( Compatibility::for_products( $inverter, $battery, $this->manifest ) );
		$this->claims[ $inverter ]['pairs'] = array( $row );
		$this->assertNotNull( Compatibility::for_products( $inverter, $battery, $this->manifest ) );
		foreach ( $this->manifest['documents'] as &$document ) {
			if ( $row['documents'][0]['document_id'] === $document['document_id'] ) {
				$document['blob_sha256'] = str_repeat( 'c', 64 );
			}
		}
		unset( $document );
		$this->assertNull( Compatibility::for_products( $inverter, $battery, $this->manifest ) );
	}

	/** Normal saving keeps old proof; only explicit confirmation adopts new bytes. */
	public function test_editor_preserves_unchanged_evidence_and_requires_confirmation(): void {
		$inverter                  = $this->product_id( 'H2-10K-T3' );
		$row                       = $this->claims[ $inverter ]['pairs'][0];
		$before                    = array(
			'schema_version' => 1,
			'pairs'          => array( $row ),
			'requirements'   => array(),
		);
		$raw                       = json_decode( (string) json_encode( $row ), true );
		$raw['battery_product_id'] = (string) $raw['battery_product_id'];
		foreach ( $raw['accessories'] as &$part ) {
			$part['product_id'] = (string) $part['product_id'];
			$part['quantity']   = (string) $part['quantity'];
		}
		unset( $part );
		foreach ( $raw['documents'] as &$doc ) {
			if ( isset( $doc['page'] ) ) {
				$doc['page'] = (string) $doc['page'];
			}
		}
		unset( $doc );
		foreach ( $this->manifest['documents'] as &$document ) {
			$document['blob_sha256'] = str_repeat( 'd', 64 );
		}
		unset( $document );
		$draft = array(
			'complete'     => '1',
			'pairs'        => array( $raw ),
			'requirements' => array(),
		);
		$this->assertSame( $before, CompatibilityEditor::prepare( $inverter, $draft, $before, $this->manifest ) );
		$draft['pairs'][0]['confirm'] = '1';
		$confirmed                    = CompatibilityEditor::prepare( $inverter, $draft, $before, $this->manifest );
		$this->assertSame( str_repeat( 'd', 64 ), $confirmed['pairs'][0]['documents'][0]['blob_sha256'] );
		unset( $draft['pairs'][0]['confirm'] );
		$draft['pairs'][0]['conditions'][] = array(
			'en' => 'A changed condition.',
			'de' => 'Eine geänderte Bedingung.',
		);
		$this->expectException( \RuntimeException::class );
		CompatibilityEditor::prepare( $inverter, $draft, $before, $this->manifest );
	}

	/** An unchanged migration cannot overwrite maintenance or silently rebind a PDF. */
	public function test_migration_is_idempotent_and_missing_evidence_stays_unresolved(): void {
		$input = EngineeringData::json( EngineeringData::COMPATIBILITY_FILE );
		$this->assertIsArray( $input );
		$plan = CompatibilityMigration::plan( $input, str_repeat( 'a', 64 ), $this->manifest );
		$this->assertSame( array(), $plan['changes'] );
		$this->assertNotEmpty( $plan['preserved'] );
		$this->claims                = array();
		$this->manifest['documents'] = array();
		$plan                        = CompatibilityMigration::plan( $input, str_repeat( 'a', 64 ), $this->manifest );
		$this->assertNotEmpty( $plan['unresolved'] );
		foreach ( $plan['changes'] as $change ) {
			$this->assertSame(
				array(
					'exists' => false,
					'value'  => '',
				),
				$change['before']
			);
			$this->assertFalse( $change['recovery_meta']['before']['exists'] );
			$this->assertSame( Publication::revision( $change['after'] ), $change['recovery_meta']['after']['after_sha256'] );
			$this->claims[ $change['product_id'] ] = $change['after'];
		}
		$this->assertSame( array(), Compatibility::pairs( $this->manifest ) );
		$this->claims = array();
		$this->assertSame( array(), Compatibility::pairs( $this->manifest ), 'No static runtime fallback.' );
	}

	/** Conditional declarations survive the native editor and cannot become general requirements. */
	public function test_native_requirement_scope_stays_bound_and_contextual(): void {
		$owner                = $this->product_id( 'GW100K-ETR-G10' );
		$row                  = $this->claims[ $owner ]['requirements'][0];
		$row['applicability'] = array(
			'operating_mode'        => 'backup',
			'topology'              => 'parallel_group',
			'control_network'       => 'lan',
			'controller_product_id' => $this->product_id( 'SEC3000C' ),
		);
		$raw                  = $row;
		$raw['applicability']['controller_product_id'] = (string) $row['applicability']['controller_product_id'];
		$raw['included']                               = $row['included'] ? '1' : '0';
		$raw['confirm']                                = '1';
		$raw['documents']                              = array_map( static fn( array $doc ): array => array_intersect_key( $doc, array_flip( array( 'document_id', 'page' ) ) ), $row['documents'] );
		$before                                        = $this->claims[ $owner ];
		$draft = array(
			'complete'     => '1',
			'pairs'        => array(),
			'requirements' => array( $raw ),
		);
		// Preserve existing pairs while changing only this maintained requirement.
		$draft['pairs']         = array_map(
			static function ( array $pair ): array {
				$pair['documents'] = array_map( static fn( array $doc ): array => array_intersect_key( $doc, array_flip( array( 'document_id', 'page' ) ) ), $pair['documents'] );
				return $pair;
			},
			$before['pairs']
		);
		$this->claims[ $owner ] = CompatibilityEditor::prepare( $owner, $draft, $before, $this->manifest );
		$this->assertSame( $row['applicability'], $this->claims[ $owner ]['requirements'][0]['applicability'] );
		$this->assertSame( array(), Compatibility::requirements( 'GW100K-ETR-G10', 'parallel_controller', $owner, $this->manifest ) );
		$this->assertCount( 1, Compatibility::requirements( 'GW100K-ETR-G10', 'parallel_controller', $owner, $this->manifest, $row['applicability'] ) );
		$without_controller = $row['applicability'];
		unset( $without_controller['controller_product_id'] );
		$this->assertSame( array(), Compatibility::requirements( 'GW100K-ETR-G10', 'parallel_controller', $owner, $this->manifest, $without_controller ) );
		$row['applicability']['control_network'] = 'wifi';
		$this->expectException( \RuntimeException::class );
		CompatibilityClaims::bind_row( $owner, $row, 'requirements', $this->manifest, true );
	}

	/** Optional control schemes must name a current canonical Woo controller. */
	public function test_control_scheme_cannot_reference_an_unpublished_controller(): void {
		$owner                = $this->product_id( 'GW100K-ETR-G10' );
		$row                  = $this->claims[ $owner ]['requirements'][0];
		$row['applicability'] = array(
			'operating_mode'        => 'grid_connected',
			'topology'              => 'parallel_group',
			'control_network'       => 'lan',
			'controller_product_id' => 90000001,
		);
		$this->expectException( \RuntimeException::class );
		CompatibilityClaims::bind_row( $owner, $row, 'requirements', $this->manifest, true );
	}

	/** Truncated native POST fields cannot erase declarations from later rows. */
	public function test_truncated_editor_preserves_all_stored_declarations(): void {
		$owner = $this->product_id( 'H2-10K-T3' );
		$this->expectException( \RuntimeException::class );
		CompatibilityEditor::prepare(
			$owner,
			array(
				'complete'     => '1',
				'pairs'        => array(),
				'requirements' => array(),
			),
			$this->claims[ $owner ],
			$this->manifest
		);
	}

	/**
	 * Unique fixture model.
	 *
	 * @param string $model Unique fixture model.
	 */
	private function product_id( string $model ): int {
		return array_column( $this->manifest['products'], 'product_id', 'model' )[ $model ];
	}
}
