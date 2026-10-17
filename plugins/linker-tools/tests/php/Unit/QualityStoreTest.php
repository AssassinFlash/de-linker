<?php
/**
 * The quality check's verdicts on their conversations.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\QualityStore;
use WP_Mock;
use WP_Mock\Tools\TestCase;

/**
 * Tests for QualityStore.
 *
 * @covers \Linker\Tools\Genie\QualityStore
 */
final class QualityStoreTest extends TestCase {

	/**
	 * The conversation's post meta, as the fakes below keep it.
	 *
	 * @var array<string, list<mixed>>
	 */
	private array $meta = array();

	/**
	 * A verdict as the worker sends it.
	 *
	 * @param array<string, mixed> $changes Overrides.
	 * @return array<string, mixed>
	 */
	private function record( array $changes = array() ): array {
		return array_merge(
			array(
				'turn_id'         => 41,
				'conversation_id' => '812',
				'turn_at'         => '2026-10-17 09:00:00',
				'judged_at'       => gmdate( 'Y-m-d\TH:i:s\Z' ),
				'locale'          => 'de',
				'status'          => 'judged',
				'question'        => 'Welche Batterie passt?',
				'answer'          => 'Diese.',
				'cards'           => array( 4107, '6507', 'x' ),
				'labels'          => array(
					'grounded'    => '2',
					'appropriate' => 'yes',
					'better_pick' => 'A',
				),
				'sources'         => array(
					'grounded'    => 'jev',
					'appropriate' => 'jev',
					'better_pick' => 'jev',
				),
				'confidence'      => array( 'grounded' => 0.95 ),
				'escalated'       => false,
				'escalation'      => array(),
				'reasons'         => array( 'jev' => null ),
				'citations'       => array(),
				'flags'           => array(),
				'flagged'         => false,
			),
			$changes
		);
	}

	/**
	 * Post meta in memory, for one conversation post (812).
	 */
	private function fake_meta(): void {
		WP_Mock::userFunction( 'wp_check_invalid_utf8', array( 'return' => static fn ( $text ) => $text ) );
		WP_Mock::userFunction(
			'get_post_type',
			array( 'return' => static fn ( $id ) => 812 === $id ? Conversations::POST_TYPE : false )
		);
		WP_Mock::userFunction(
			'get_post_meta',
			array( 'return' => fn ( $id, $key, $single = false ) => $single ? ( $this->meta[ $key ][0] ?? '' ) : ( $this->meta[ $key ] ?? array() ) )
		);
		WP_Mock::userFunction(
			'add_post_meta',
			array(
				'return' => function ( $id, $key, $value ) {
					$this->meta[ $key ][] = $value;
					return 1;
				},
			)
		);
		WP_Mock::userFunction(
			'delete_post_meta',
			array(
				'return' => function ( $id, $key, $value ) {
					$this->meta[ $key ] = array_values( array_filter( $this->meta[ $key ] ?? array(), static fn ( $row ) => serialize( $row ) !== serialize( $value ) ) ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.serialize_serialize -- the comparison WordPress itself makes.
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( $id, $key, $value ) {
					$this->meta[ $key ] = array( $value );
					return true;
				},
			)
		);
	}

	/**
	 * Unknown labels, flags and keys are dropped; strings are bounded; only a
	 * judged verdict with flags counts as flagged.
	 */
	public function test_sanitize_keeps_only_what_the_page_reads(): void {
		WP_Mock::userFunction( 'wp_check_invalid_utf8', array( 'return' => static fn ( $text ) => $text ) );
		$clean = QualityStore::sanitize(
			$this->record(
				array(
					'labels'   => array(
						'grounded'    => '7',
						'appropriate' => 'no',
						'extra'       => 'yes',
					),
					'flags'    => array( 'out_of_remit', '<script>' ),
					'question' => str_repeat( 'a', 1200 ),
					'secret'   => 'dropped',
				)
			)
		);
		$this->assertSame( array( 'appropriate' => 'no' ), $clean['labels'] );
		$this->assertSame( array( 'out_of_remit' ), $clean['flags'] );
		$this->assertTrue( $clean['flagged'] );
		$this->assertSame( 1000, mb_strlen( $clean['question'] ) );
		$this->assertSame( array( 4107, 6507 ), $clean['cards'] );
		$this->assertSame( 812, $clean['conversation_id'] );
		$this->assertArrayNotHasKey( 'secret', $clean );

		$failed = QualityStore::sanitize(
			$this->record(
				array(
					'status' => 'failed',
					'flags'  => array( 'citation' ),
				)
			)
		);
		$this->assertFalse( $failed['flagged'] );
		$this->assertSame( 'failed', QualityStore::sanitize( $this->record( array( 'status' => 'bogus' ) ) )['status'] );
	}

	/**
	 * A verdict for something that is not a conversation of this site is refused.
	 */
	public function test_a_verdict_for_an_unknown_conversation_is_not_stored(): void {
		$this->fake_meta();
		$this->assertFalse( ( new QualityStore() )->store( $this->record( array( 'conversation_id' => 9999 ) ) ) );
		$this->assertSame( array(), $this->meta );
	}

	/**
	 * A retried turn replaces its earlier verdict, and the counts follow.
	 */
	public function test_a_turn_judged_again_replaces_its_verdict(): void {
		$this->fake_meta();
		$store = new QualityStore();
		$this->assertTrue( $store->store( $this->record( array( 'status' => 'failed' ) ) ) );
		$this->assertTrue( $store->store( $this->record( array( 'turn_id' => 40 ) ) ) );
		$this->assertSame( array( 1 ), $this->meta[ QualityStore::FAILED_META ] );

		$this->assertTrue(
			$store->store(
				$this->record(
					array(
						'flags'   => array( 'contradicted' ),
						'flagged' => true,
					)
				)
			)
		);
		$rows = $store->judgments( 812 );
		$this->assertSame( array( 40, 41 ), array_column( $rows, 'turn_id' ) );
		$this->assertSame( 'judged', $rows[1]['status'] );
		$this->assertSame( array( 1 ), $this->meta[ QualityStore::FLAGGED_META ] );
		$this->assertSame( array( 0 ), $this->meta[ QualityStore::FAILED_META ] );
		$this->assertIsInt( $this->meta[ QualityStore::AT_META ][0] );
	}

	/**
	 * The digest's summary counts the window's verdicts and says when the
	 * worker went quiet.
	 */
	public function test_the_summary_counts_the_day_and_names_a_stopped_worker(): void {
		$this->fake_meta();
		$store = new QualityStore();
		$store->store( $this->record( array( 'turn_id' => 1 ) ) );
		$store->store(
			$this->record(
				array(
					'turn_id'    => 2,
					'escalated'  => true,
					'flags'      => array( 'unverifiable' ),
					'escalation' => array( 'grounded 0.42 < 0.6' ),
				)
			)
		);
		$store->store(
			$this->record(
				array(
					'turn_id' => 3,
					'status'  => 'failed',
				)
			)
		);
		$store->store(
			$this->record(
				array(
					'turn_id'   => 4,
					'judged_at' => '2026-01-01T00:00:00Z',
				)
			)
		);

		WP_Mock::userFunction( 'get_posts', array( 'return' => array( 812 ) ) );
		WP_Mock::userFunction(
			'get_option',
			array(
				'return' => array(
					'received'   => time() - QualityStore::STALE_AFTER - 1,
					'last_error' => 'OpenRouter: HTTP 402',
				),
			)
		);
		WP_Mock::userFunction( 'admin_url', array( 'return' => static fn ( $path ) => 'https://site.example/wp-admin/' . $path ) );
		WP_Mock::passthruFunction( '__' );

		$summary = $store->filter_summary( null );

		$this->assertSame( 2, $summary['judged'] );
		$this->assertSame( 1, $summary['flagged'] );
		$this->assertSame( 1, $summary['escalated'] );
		$this->assertSame( 1, $summary['failed'] );
		$this->assertTrue( $summary['worker_stale'] );
		$this->assertSame( 'OpenRouter: HTTP 402', $summary['last_error'] );
		$this->assertStringContainsString( '2 answers judged, 1 flagged, 1 decided by the second judge, 1 could not be judged.', $summary['line'] );
		$this->assertStringEndsWith( 'The quality check has stopped reporting.', $summary['line'] );
		$this->assertSame( 'https://site.example/wp-admin/admin.php?page=linker-genie-quality', $summary['url'] );
	}

	/**
	 * The status report is kept with the time it arrived.
	 */
	public function test_the_status_report_is_stamped_and_bounded(): void {
		WP_Mock::userFunction( 'wp_check_invalid_utf8', array( 'return' => static fn ( $text ) => $text ) );
		WP_Mock::userFunction(
			'update_option',
			array(
				'times'  => 1,
				'return' => function ( $name, $value, $autoload ) {
					$this->assertSame( QualityStore::STATUS_OPTION, $name );
					$this->assertFalse( $autoload );
					$this->assertSame( 2, $value['retrying'] );
					$this->assertSame( 'deepseek-flash (api.deepseek.com)', $value['escalation'] );
					$this->assertGreaterThan( time() - 5, $value['received'] );
					$this->assertArrayNotHasKey( 'token', $value );
					return true;
				},
			)
		);
		( new QualityStore() )->store_status(
			array(
				'retrying'   => '2',
				'escalation' => 'deepseek-flash (api.deepseek.com)',
				'token'      => 'x',
			)
		);
		$this->assertConditionsMet();
	}
}
