<?php
/**
 * The customer's project note follows native Woo lines into an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Planning;

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\DraftTransfer;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Note revisions, inclusion choice and the order snapshot.
 *
 * @covers \Linker\Commerce\Planning\Context
 */
final class ProjectNotesTest extends TestCase {

	/**
	 * The native Woo session store.
	 *
	 * @var array<string,mixed>
	 */
	private array $session = array();

	/** Shared fixtures: the note text carried by the handoff snapshot. */
	private const NOTE = "SAJ H2-10K, -40 °C, 6000 W\nwest roof, no backup.";

	/**
	 * The engine-owned snapshot a solution draft line references.
	 *
	 * @param string $note       Customer note carried by the project.
	 * @param string $note_label The report's own label for that row.
	 * @return array<string,mixed>
	 */
	private function handoff( string $note = self::NOTE, string $note_label = 'Project note' ): array {
		$handoff_id = str_repeat( 'c', 32 );
		$snapshot   = array(
			'schema_version' => 1,
			'kind'           => 'planning_products_v1',
			'project_id'     => str_repeat( 'a', 32 ),
			'title'          => 'Installer project',
			'revision'       => 4,
			'report_run_id'  => str_repeat( 'b', 32 ),
			'items'          => array(
				array(
					'product_id' => 3556,
					'quantity'   => 1,
					'label'      => 'GoodWe GW10K-ETA-G20',
				),
			),
			'publication'    => array(
				'engineering_contract'   => 2,
				'compatibility_revision' => str_repeat( 'e', 64 ),
			),
			'report'         => array(
				'sections' => array(
					array(
						'id'    => 'site',
						'title' => 'Site and project inputs',
						// The engine's own row order and labels: the note is the
						// fourth row of the site section, in the report's locale.
						'rows'  => array(
							array(
								'label' => 'Location',
								'value' => '—',
							),
							array(
								'label' => 'Country',
								'value' => '—',
							),
							array(
								'label' => 'Time zone',
								'value' => '—',
							),
							array(
								'label' => $note_label,
								'value' => $note,
							),
						),
					),
				),
			),
			'pdf'            => array(
				'asset_id'   => str_repeat( 'f', 32 ),
				'sha256'     => str_repeat( '1', 64 ),
				'media_type' => 'application/pdf',
			),
		);
		return array(
			'schema_version'  => 1,
			'id'              => $handoff_id,
			'snapshot_sha256' => Publication::revision( $snapshot ),
			'snapshot'        => $snapshot,
		);
	}

	/** Native session and encoder doubles. */
	public function setUp(): void {
		parent::setUp();
		$this->session = array();
		$session       = &$this->session;
		WP_Mock::userFunction(
			'wp_json_encode',
			array(
				'return' => static fn ( mixed $value ): string => (string) json_encode( $value, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE ),
			)
		);
		// The plugin reads the native session through WC()->session; the cart
		// lines are supplied by each case that needs them.
		$woocommerce          = new \stdClass();
		$woocommerce->session = new class( $session ) {
			/**
			 * Live session store owned by the native session.
			 *
			 * @var array<string,mixed>
			 */
			private array $store;

			/**
			 * Bind the shared store.
			 *
			 * @param array<string,mixed> $store Session store by reference.
			 */
			public function __construct( array &$store ) {
				$this->store = &$store;
			}

			/**
			 * Native get().
			 *
			 * @param string $key      Session key.
			 * @param mixed  $fallback Default.
			 */
			public function get( string $key, mixed $fallback = null ): mixed {
				return $this->store[ $key ] ?? $fallback;
			}

			/**
			 * Native set().
			 *
			 * @param string $key   Session key.
			 * @param mixed  $value Value.
			 */
			public function set( string $key, mixed $value ): void {
				$this->store[ $key ] = $value;
			}
		};
		$woocommerce->cart    = new class() {
			/**
			 * No cart lines: the note cases prove the note path alone.
			 *
			 * @return array<int,array<string,mixed>>
			 */
			public function get_cart(): array {
				return array();
			}
		};
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
	}

	/**
	 * The verbatim note is the one stored in the native Woo session.
	 *
	 * @return array<string,mixed>
	 */
	private function keep(): array {
		$handoff                                  = DraftTransfer::native_context( $this->handoff() );
		$this->session[ DraftTransfer::CONTEXTS ] = array( $handoff['id'] => $handoff );
		return $handoff;
	}

	/** The customer's note reaches the inquiry snapshot without being parsed. */
	public function test_the_customer_note_is_read_verbatim_from_the_native_session(): void {
		$handoff = $this->keep();
		$notes   = Context::session_notes();

		$this->assertCount( 1, $notes );
		$note = reset( $notes );
		$this->assertIsArray( $note );
		$this->assertSame( self::NOTE, $note['text'] );
		$this->assertSame( $handoff['id'], $note['handoff_id'] );
		$this->assertSame( 4, $note['revision'] );
		$this->assertMatchesRegularExpression( '/\A[a-f0-9]{64}\z/', $note['note_revision'] );
		// The note is context, never an inferred sizing number or product fact.
		$this->assertStringContainsString( '6000 W', $note['text'] );
	}

	/** The German report labels the same row, so a DE project keeps its note. */
	public function test_the_german_report_label_carries_the_same_note(): void {
		$this->session[ DraftTransfer::CONTEXTS ] = array(
			str_repeat( 'c', 32 ) => DraftTransfer::native_context( $this->handoff( self::NOTE, 'Projektnotiz' ) ),
		);
		$notes                                    = Context::session_notes();
		$this->assertCount( 1, $notes );
		$note = reset( $notes );
		$this->assertIsArray( $note );
		$this->assertSame( self::NOTE, $note['text'] );
	}

	/** A changed note produces a different revision, so stale reviews are refused. */
	public function test_a_changed_note_revision_differs(): void {
		$first         = Context::note_revision( $this->keep() );
		$this->session = array();
		$second        = Context::note_revision( $this->keep() );

		$this->assertSame( $first, $second );

		$this->session = array();
		$third         = Context::note_revision(
			DraftTransfer::native_context( $this->handoff( 'a different requirement' ) )
		);
		$this->assertNotSame( $first, $third );
	}

	/** An excluded note is not consumed and stays available for a later inquiry. */
	public function test_excluding_the_note_keeps_it_in_the_session(): void {
		$handoff = $this->keep();
		Context::with_submission(
			array(
				Context::PRESENT_FIELD => '1',
				Context::INCLUDE_FIELD => '0',
			),
			static function (): void {
				if ( Context::has_included_notes() ) {
					echo 'included';
				}
			}
		);
		$this->assertSame(
			$this->session[ DraftTransfer::CONTEXTS ][ $handoff['id'] ]['id'],
			$handoff['id']
		);
	}

	/** An included note counts as a valid inquiry even with an empty cart and message. */
	public function test_an_included_note_is_a_valid_inquiry_without_products_or_message(): void {
		$this->keep();
		$included = null;
		Context::with_submission(
			array(
				Context::PRESENT_FIELD => '1',
				Context::INCLUDE_FIELD => '1',
			),
			static function () use ( &$included ): void {
				$included = Context::has_included_notes();
			}
		);
		$this->assertTrue( $included );

		$excluded = null;
		Context::with_submission(
			array(
				Context::PRESENT_FIELD => '1',
				Context::INCLUDE_FIELD => '0',
			),
			static function () use ( &$excluded ): void {
				$excluded = Context::has_included_notes();
			}
		);
		$this->assertFalse( $excluded );
	}

	/** The reviewed inclusion choice is part of the admission fingerprint. */
	public function test_submission_fingerprint_covers_inclusion_and_revisions(): void {
		$included = Context::submission_fingerprint(
			array(
				Context::INCLUDE_FIELD   => '1',
				Context::REVISIONS_FIELD => array(
					str_repeat( 'c', 32 ) => str_repeat( 'a', 64 ),
				),
			)
		);
		$excluded = Context::submission_fingerprint(
			array(
				Context::REVISIONS_FIELD => array(
					str_repeat( 'c', 32 ) => str_repeat( 'a', 64 ),
				),
			)
		);
		$this->assertTrue( $included['included'] );
		$this->assertFalse( $excluded['included'] );
		$this->assertNotSame( $included, $excluded );
	}

	/** The reviewed note section is rendered separately from the customer message. */
	public function test_the_inquiry_section_shows_the_note_and_its_scope(): void {
		$this->keep();
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		$html = Context::inquiry_notes_section();
		$this->assertStringContainsString( 'Include project notes with this inquiry', $html );
		$this->assertStringContainsString( 'This note is not used in the calculation.', $html );
		$this->assertStringContainsString( 'SAJ H2-10K', $html );
		$this->assertStringContainsString( 'name="' . Context::INCLUDE_FIELD . '"', $html );
		$this->assertStringContainsString( 'name="' . Context::REVISIONS_FIELD . '[', $html );
	}

	/** A failed POST keeps a deliberately unchecked inclusion choice. */
	public function test_a_failed_submission_keeps_an_unchecked_inclusion_choice(): void {
		$this->keep();
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		$html = Context::inquiry_notes_section(
			array(
				Context::PRESENT_FIELD => '1',
				Context::INCLUDE_FIELD => '',
			)
		);
		$this->assertStringNotContainsString( 'checked', $html );
	}

	/** A customer note longer than the engine brief bound is still a valid note. */
	public function test_a_note_above_the_engine_brief_bound_is_not_truncated(): void {
		$long                                     = str_repeat( 'a', 5000 );
		$this->session[ DraftTransfer::CONTEXTS ] = array(
			str_repeat( 'c', 32 ) => DraftTransfer::native_context( $this->handoff( $long ) ),
		);
		$notes                                    = Context::session_notes();
		$this->assertCount( 1, $notes );
		$note = reset( $notes );
		$this->assertIsArray( $note );
		$this->assertSame( 5000, mb_strlen( $note['text'], 'UTF-8' ) );
	}

	/** A report that stopped labelling the note must not report another row as it. */
	public function test_a_row_without_the_project_note_label_is_not_read_by_position(): void {
		$snapshot = $this->handoff( 'Time zone value', 'Time zone' )['snapshot'];
		// Rows are the production order; the fourth row is deliberately mislabelled.
		$snapshot['report']['sections'][0]['rows'] = array(
			array(
				'label' => 'Location',
				'value' => '—',
			),
			array(
				'label' => 'Country',
				'value' => 'DE',
			),
			array(
				'label' => 'Time zone',
				'value' => 'Europe/Berlin',
			),
			array(
				'label' => 'Time zone',
				'value' => 'Europe/Berlin',
			),
		);
		$this->assertSame( '', Context::project_note( $snapshot ) );
	}

	/** An absent note yields no section at all, not an empty one. */
	public function test_a_project_without_a_note_has_no_notes_section(): void {
		$this->session[ DraftTransfer::CONTEXTS ] = array(
			str_repeat( 'c', 32 ) => DraftTransfer::native_context( $this->handoff( '' ) ),
		);
		$this->assertSame( array(), Context::session_notes() );
		$this->assertSame( '', Context::inquiry_notes_section() );
	}
}
