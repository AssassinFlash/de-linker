<?php
/**
 * The customer's project note follows native Woo lines into an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Planning;

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\DraftPreview;
use Linker\Commerce\Planning\DraftRecovery;
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

	/**
	 * Current native cart lines.
	 *
	 * @var array<string,array<string,mixed>>
	 */
	private array $cart = array();

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
		$cart                 = &$this->cart;
		$woocommerce->cart    = new class( $cart ) extends \WC_Cart {
			/**
			 * Live cart fixture.
			 *
			 * @var array<string,array<string,mixed>>
			 */
			private array $lines;

			/**
			 * Bind the cart fixture.
			 *
			 * @param array<string,array<string,mixed>> $lines Native cart lines.
			 */
			public function __construct( array &$lines ) {
				$this->lines = &$lines;
			}

			/**
			 * Read native cart lines.
			 *
			 * @return array<string,array<string,mixed>>
			 */
			public function get_cart(): array {
				return $this->lines;
			}
		};
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );
	}

	/** A restored cart resolves each report once under the current planning identity. */
	public function test_restored_cart_recovers_owned_reports_and_flags_only_missing_links(): void {
		$this->plain_text();
		$owned      = $this->handoff();
		$gone       = str_repeat( 'a', 32 );
		$this->cart = array(
			'first'  => array( DraftTransfer::LINE_META => $owned['id'] ),
			'second' => array( DraftTransfer::LINE_META => $owned['id'] ),
			'old'    => array( DraftTransfer::LINE_META => $gone ),
			'manual' => array( 'quantity' => 3 ),
		);
		WP_Mock::onFilter( 'linker_tools_planning_inquiry_handoff' )->with( null, $owned['id'] )->reply( $owned );
		WP_Mock::onFilter( 'linker_tools_planning_inquiry_handoff' )->with( null, $gone )->reply( new \WP_Error( 'linker_planner_handoff_not_found', '', array( 'status' => 404 ) ) );
		$this->assertSame( array( 'old' ), DraftRecovery::review() );
		$this->assertSame( array( $owned['id'] => DraftTransfer::native_context( $owned ) ), Context::active() );
		$this->assertSame( $gone, $this->cart['old'][ DraftTransfer::LINE_META ] );
	}

	/** A service outage leaves the link available for a later retry. */
	public function test_temporary_lookup_failure_cannot_offer_to_remove_a_link(): void {
		$this->plain_text();
		$id         = str_repeat( 'a', 32 );
		$this->cart = array( 'old' => array( DraftTransfer::LINE_META => $id ) );
		WP_Mock::onFilter( 'linker_tools_planning_inquiry_handoff' )->with( null, $id )->reply( new \WP_Error( 'linker_planner_unavailable', '', array( 'status' => 503 ) ) );
		$this->assertInstanceOf( \WP_Error::class, DraftRecovery::review() );
		$this->assertSame( $id, $this->cart['old'][ DraftTransfer::LINE_META ] );
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

	/** Only a violated, frozen phase check reaches the native Woo draft. */
	public function test_cart_shows_the_frozen_phase_conflict_once_per_project(): void {
		$handoff                                     = $this->handoff();
		$handoff['snapshot']['report']['sections'][] = array(
			'id'    => 'check-2',
			'title' => 'Netzphasen',
			'rows'  => array(
				array(
					'label' => 'Prüfstatus',
					'value' => 'Anforderungen nicht erfüllt',
				),
				array(
					'label' => 'Ergebnis',
					'value' => '1',
				),
				array(
					'label' => 'Anforderung',
					'value' => '3',
				),
			),
		);
		$id                                       = $handoff['id'];
		$this->session[ DraftTransfer::CONTEXTS ] = array( $id => DraftTransfer::native_context( $handoff ) );
		$this->cart                               = array(
			'converter' => array( DraftTransfer::LINE_META => $id ),
			'battery'   => array( DraftTransfer::LINE_META => $id ),
		);
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_html__' );
		WP_Mock::userFunction(
			'wc_print_notice',
			array(
				'times' => 1,
				'args'  => array( 'Installer project: Grid phase mismatch. Selected inverter: 1. Project requirement: 3. You can send an inquiry to discuss the configuration.', 'notice' ),
			)
		);
		$context = new Context();
		$context->cart_phase_notices();

		$handoff['snapshot']['report']['sections'][1]['title'] = 'Grid phases';
		$handoff['snapshot']['report']['sections'][1]['rows']  = array(
			array(
				'label' => 'Assessment status',
				'value' => 'Checked requirements met',
			),
			array(
				'label' => 'Result',
				'value' => '3',
			),
			array(
				'label' => 'Requirement',
				'value' => '3',
			),
		);
		$this->session[ DraftTransfer::CONTEXTS ]              = array( $id => DraftTransfer::native_context( $handoff ) );
		$context->cart_phase_notices();

		$this->keep();
		$context->cart_phase_notices();
		$this->assertConditionsMet();
	}

	/** Frozen EN and DE unit checks distinguish hardware from the declared plant connection. */
	public function test_cart_shows_multiple_hardware_conflicts_but_not_the_plant_declaration(): void {
		$handoff = $this->handoff();
		$id      = $handoff['id'];
		WP_Mock::userFunction( 'wc_load_cart' );
		WP_Mock::userFunction(
			'get_option',
			array(
				'args'   => array( 'woocommerce_checkout_page_id' ),
				'return' => 1,
			)
		);
		WP_Mock::userFunction( 'pll_get_post', array( 'return' => 1 ) );
		WP_Mock::userFunction( 'get_permalink', array( 'return' => 'https://example.test/inquiry/' ) );
		WP_Mock::passthruFunction( 'esc_html' );
		WP_Mock::passthruFunction( 'esc_html__' );
		$notices = array();
		WP_Mock::userFunction(
			'wc_print_notice',
			array(
				'return' => static function ( string $text ) use ( &$notices ): void {
					$notices[] = $text;
				},
			)
		);

		foreach ( array( 'en', 'de' ) as $locale ) {
			$de                                        = 'de' === $locale;
			$hardware                                  = $de ? 'Netzphasen' : 'Grid phases';
			$plant                                     = $de ? 'Phasenanzahl am Netzanschluss der Gesamtanlage' : 'Plant grid phases';
			$rows                                      = array_map(
				static fn ( string $label, string $value ): array => array(
					'label' => $label,
					'value' => $value,
				),
				$de ? array( 'Prüfstatus', 'Ergebnis', 'Anforderung' ) : array( 'Assessment status', 'Result', 'Requirement' ),
				array( $de ? 'Anforderungen nicht erfüllt' : 'Requirements not met', '1', '3' )
			);
			$handoff['snapshot']['report']['sections'] = array(
				array(
					'id'    => 'check-1',
					'title' => 'Depot · East · ' . $hardware,
					'rows'  => $rows,
				),
				array(
					'id'    => 'check-9',
					'title' => 'Office · ' . $plant,
					'rows'  => $rows,
				),
				array(
					'id'    => 'check-14',
					'title' => 'West · ' . $hardware,
					'rows'  => $rows,
				),
			);
			foreach ( array( false, true ) as $structured ) {
				if ( $structured ) {
					$handoff['snapshot']['report']['phase_conflicts'] = array(
						array(
							'unit'     => 'Depot · East',
							'actual'   => 1,
							'required' => 3,
						),
						array(
							'unit'     => 'West',
							'actual'   => 1,
							'required' => 3,
						),
					);
				}
				$preview_handoff                            = $handoff;
				$preview_handoff['snapshot']['kind']        = 'planning_report_only_v1';
				$preview_handoff['snapshot']['publication'] = null;
				$preview_handoff['snapshot']['items']       = array();
				$this->cart                                 = array();
				$preview                                    = ( new DraftPreview() )->read( null, array(), $preview_handoff );
				$this->assertIsArray( $preview );
				$this->assertSame( array( 'Depot · East', 'West' ), array_column( $preview['phase_conflicts'], 'unit' ) );
				$this->assertSame( array( 1, 1 ), array_column( $preview['phase_conflicts'], 'actual' ) );
				$this->assertSame( array( 3, 3 ), array_column( $preview['phase_conflicts'], 'required' ) );
				$this->assertSame( array(), $preview['changes'] );

				$this->session[ DraftTransfer::CONTEXTS ] = array( $id => DraftTransfer::native_context( $handoff ) );
				$this->cart                               = array( 'converter' => array( DraftTransfer::LINE_META => $id ) );
				$notices                                  = array();
				( new Context() )->cart_phase_notices();
				$message = 'Grid phase mismatch. Selected inverter: 1. Project requirement: 3. You can send an inquiry to discuss the configuration.';
				$this->assertSame( array( 'Installer project: Depot · East: ' . $message, 'Installer project: West: ' . $message ), $notices );
			}
			unset( $handoff['snapshot']['report']['phase_conflicts'] );
		}
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

	/** A report attachment alone is sufficient and remains privately downloadable. */
	public function test_report_only_inquiry_keeps_the_report_without_products_or_a_note(): void {
		$handoff                                     = $this->handoff( '' );
		$handoff['snapshot']['kind']                 = 'planning_report_only_v1';
		$handoff['snapshot']['publication']          = null;
		$handoff['snapshot']['items']                = array();
		$handoff['snapshot']['input_sha256']         = str_repeat( '2', 64 );
		$handoff['snapshot']['report_source_sha256'] = str_repeat( '3', 64 );
		$handoff['snapshot']['report_sha256']        = str_repeat( '4', 64 );
		$handoff['snapshot_sha256']                  = Publication::revision( $handoff['snapshot'] );
		$this->session[ DraftTransfer::CONTEXTS ]    = array( $handoff['id'] => DraftTransfer::native_context( $handoff ) );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => $text ) );
		$this->assertStringContainsString( 'Planning report', Context::inquiry_notes_section() );
		$this->assertFalse( Context::has_included_notes(), 'A sender without a reviewed inquiry form cannot include the report.' );
		$order  = $this->getMockBuilder( \WC_Order::class )->disableOriginalConstructor()->onlyMethods( array( 'get_meta', 'update_meta_data' ) )->addMethods( array( 'get_items' ) )->getMock();
		$stored = array();
		$order->method( 'get_items' )->willReturn( array() );
		$order->method( 'update_meta_data' )->willReturnCallback(
			static function ( string $key, string $value ) use ( &$stored ): void {
				$stored[ $key ] = $value;
			}
		);
		$order->method( 'get_meta' )->willReturnCallback(
			static function ( string $key ) use ( &$stored ): string {
				return $stored[ $key ] ?? '';
			}
		);
		$post = array(
			Context::PRESENT_FIELD   => '1',
			Context::INCLUDE_FIELD   => '1',
			Context::REVISIONS_FIELD => array( $handoff['id'] => Context::note_revision( $handoff ) ),
		);
		Context::with_submission(
			$post,
			function () use ( $order ): void {
				$this->assertTrue( Context::has_included_notes() );
				$this->assertNull( Context::preflight() );
				( new Context() )->capture( $order );
			}
		);
		$this->assertSame( Context::reference( $handoff ), Context::stored( $order )[ $handoff['id'] ]['reference'] );
		$this->assertSame( array(), Context::stored_notes( $order ) );
		Context::consume_captured_notes( $order );
		$this->assertSame( array(), Context::session_notes() );
	}

	/** A report-free project is read only for the exact selection on this form. */
	public function test_preliminary_note_submission(): void {
		$id       = str_repeat( 'b', 32 );
		$key      = 'project_' . $id;
		$note     = array(
			'project_id'    => $id,
			'title'         => 'Installer project',
			'revision'      => 3,
			'note_revision' => '3',
			'text'          => self::NOTE,
		);
		$provider = WP_Mock::onFilter( 'linker_tools_planning_inquiry_note' )->with( null, $id );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $provider );
		$provider->reply( $note );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		$post  = array(
			Context::PRESENT_FIELD   => '1',
			Context::INCLUDE_FIELD   => '1',
			Context::REVISIONS_FIELD => array( $key => '3' ),
		);
		$order = $this->getMockBuilder( \WC_Order::class )->disableOriginalConstructor()->onlyMethods( array( 'get_meta', 'update_meta_data' ) )->addMethods( array( 'get_items' ) )->getMock();
		$order->method( 'get_items' )->willReturn( array() );
		$order->expects( $this->once() )->method( 'update_meta_data' )->with( Context::NOTES_META, wp_json_encode( array( $key => $note ) ) );
		$order->method( 'get_meta' )->with( Context::NOTES_META )->willReturn( wp_json_encode( array( $key => $note ) ) );
		Context::with_submission(
			$post,
			function () use ( $order ): void {
				$this->assertNull( Context::preflight() );
				$this->assertTrue( Context::has_included_notes() );
				( new Context() )->capture( $order );
			}
		);
		$this->assertSame( array( $key => $note ), Context::stored_notes( $order ) );
		$post[ Context::REVISIONS_FIELD ][ $key ] = '2';
		$error                                    = Context::with_submission( $post, Context::preflight( ... ) );
		$this->assertInstanceOf( \WP_Error::class, $error );
		$this->assertSame( 'linker_project_notes_changed', $error->get_error_code() );
		unset( $post[ Context::INCLUDE_FIELD ] );
		Context::with_submission(
			$post,
			function (): void {
				$this->assertNull( Context::preflight() );
				$this->assertFalse( Context::has_included_notes() );
			}
		);
		$this->assertSame( array(), Context::session_notes() );
	}

	/** The project follows its reviewed revision even when the note is empty or excluded.
	 *
	 * @return list<array{string,bool,string|null}>
	 */
	public static function preliminary_notes(): array {
		return array( array( '', false, 'pv_only' ), array( self::NOTE, true, 'pv_only' ), array( self::NOTE, false, 'pv_only' ), array( '', false, null ) );
	}

	/** Captures the reviewed project in the native Woo customer note.
	 *
	 * @dataProvider preliminary_notes
	 * @param string      $text Reviewed project note.
	 * @param bool        $include_note Whether the customer includes that note.
	 * @param string|null $scope Planned system, if the customer has chosen one.
	 */
	public function test_preliminary_project_reaches_sales( string $text, bool $include_note, ?string $scope ): void {
		$id   = str_repeat( 'b', 32 );
		$post = array( 'linker_preliminary_project' => $id . ':3' );
		$note = array(
			'project_id'    => $id,
			'title'         => 'Canal house',
			'revision'      => 3,
			'note_revision' => '3',
			'text'          => $text,
			'inputs'        => array(
				'brief'                    => array(
					'system_scope' => $scope,
					'site'         => array( 'location_label' => 'Oslo' ),
					'annual_load'  => array(
						'kwh'   => 6400,
						'basis' => 'bill_total',
					),
				),
				'pvgis_reference_setup'    => array(
					'model'  => 'pvgis_5_3_known_ac_reference_v1',
					'arrays' => array( array( 'peak_power_kwp' => 4.5 ), array( 'peak_power_kwp' => 3 ) ),
				),
				'equipment_setup'          => array( 'pv_dc_kw' => 9 ),
				'saved_solution_reference' => array( 'title' => 'April proposal' ),
				'energy_scenario'          => array(
					'controller' => 'peak_shaving_with_reserve_v1',
					'schedule'   => array(
						array(
							'mode'          => 'connected',
							'import_policy' => 'limited',
							'import_cap_kw' => 0,
						),
					),
				),
			),
		);
		if ( '' !== $text ) {
			$post[ Context::PRESENT_FIELD ]   = '1';
			$post[ Context::REVISIONS_FIELD ] = array( 'project_' . $id => '3' );
			if ( $include_note ) {
				$post[ Context::INCLUDE_FIELD ] = '1';
			}
		}
		$provider = WP_Mock::onFilter( 'linker_tools_planning_inquiry_note' )->with( null, $id, 3 );
		$this->assertInstanceOf( \WP_Mock\Filter_Responder::class, $provider );
		$provider->reply( $note );
		WP_Mock::userFunction( '__' )->andReturnUsing(
			static function ( string $text, string $domain = 'default' ): string {
				return 'linker-commerce' === $domain && 'Solution draft' === $text ? 'Lösungsentwurf' : $text;
			}
		);
		WP_Mock::passthruFunction( 'esc_html' );
		$order = $this->getMockBuilder( \WC_Order::class )->disableOriginalConstructor()->onlyMethods( array( 'get_meta', 'update_meta_data' ) )->addMethods( array( 'get_items', 'get_customer_note', 'set_customer_note' ) )->getMock();
		$order->method( 'get_items' )->willReturn( array() );
		$meta   = array();
		$output = '';
		$order->method( 'get_customer_note' )->willReturn( 'Please call.' );
		$order->method( 'set_customer_note' )->willReturnCallback(
			static function ( $value ) use ( &$output ): void {
				$output = $value;
			}
		);
		$order->method( 'update_meta_data' )->willReturnCallback(
			static function ( $key, $value ) use ( &$meta ): void {
				$meta[ $key ] = $value;
			}
		);
		$order->method( 'get_meta' )->willReturnCallback(
			static function ( $key ) use ( &$meta ) {
				return $meta[ $key ] ?? '';
			}
		);
		Context::with_submission(
			$post,
			function () use ( $order ): void {
				$this->assertNull( Context::preflight() );
				( new Context() )->capture( $order );
			}
		);
		$this->assertStringEndsWith( "\n\nPlease call.", $output );
		foreach ( array( 'Canal house', 'input revision 3', 'Oslo', '6400 kWh', 'Electricity bills', 'PV array size: 7.5 kWp', 'Grid phases: To confirm', 'Reduce peak demand', 'Target grid import limit: 0 kW', 'Lösungsentwurf: April proposal' ) as $fact ) {
			$this->assertStringContainsString( $fact, $output );
		}
		if ( null === $scope ) {
			$this->assertStringNotContainsString( 'Planned system:', $output );
		} else {
			$this->assertStringContainsString( 'Solar', $output );
		}
		$this->assertSame( $id . ':3', $meta['_linker_preliminary_project'] );
		$this->assertSame( array(), Context::stored( $order ) );
		$this->assertSame( array(), Context::stored_notes( $order ) );
		if ( $include_note ) {
			$this->assertStringContainsString( self::NOTE, $output );
			$post[ Context::REVISIONS_FIELD ][ 'project_' . $id ] = '4';
			$this->assertInstanceOf( \WP_Error::class, Context::with_submission( $post, Context::preflight( ... ) ) );
		} else {
			$this->assertStringNotContainsString( self::NOTE, $output );
		}
	}

	/** The planner keeps technical inputs in its summary and note controls in the contact form. */
	public function test_planner_review_keeps_distinct_capacities_and_optional_note_controls(): void {
		WP_Mock::userFunction( 'wc_format_localized_decimal', array( 'return' => static fn ( string $number ): string => $number ) );
		WP_Mock::userFunction( 'esc_html__', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_attr', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( 'esc_html', array( 'return' => static fn ( string $text ): string => $text ) );
		WP_Mock::userFunction( '__', array( 'return' => static fn ( string $text ): string => $text ) );
		$project = array(
			'project_id'    => str_repeat( 'b', 32 ),
			'note_revision' => '3',
			'revision'      => 3,
			'title'         => 'Canal house',
			'text'          => 'Meter is upstairs',
			'inputs'        => array(
				'brief'                    => array(
					'system_scope' => 'storage_addition',
					'site'         => array(
						'postal_code' => '78462',
						'latitude'    => 47.66,
						'longitude'   => 9.17,
						'timezone'    => 'Europe/Berlin',
					),
				),
				'pvgis_reference_setup'    => array(
					'model'  => 'pvgis_5_3_known_ac_reference_v1',
					'arrays' => array( array( 'peak_power_kwp' => 4.5 ), array( 'peak_power_kwp' => 3 ) ),
				),
				'known_panel_details'      => array(
					'count'      => 10,
					'power_w'    => 450,
					'system_kwp' => 4.5,
				),
				'equipment_setup'          => array(
					'pv_dc_kw'                 => 7.5,
					'required_discharge_ac_kw' => 0,
					'required_usable_kwh'      => 6,
				),
				'saved_solution_reference' => array( 'title' => 'April proposal' ),
			),
		);
		$facts   = array_column( Context::review_facts( $project ), 'value', 'label' );
		$this->assertSame( '78462', $facts['Location'] );
		$this->assertSame( '47.66', $facts['Latitude'] );
		$this->assertSame( '9.17', $facts['Longitude'] );
		$this->assertSame( 'Europe/Berlin', $facts['Time zone'] );
		$this->assertSame( '7.5 kWp', $facts['PV array size'] );
		$this->assertSame( '7.5 kWp', $facts['PV input power'] );
		$this->assertSame( '4.5 kWp', $facts['Solar capacity'] );
		$this->assertSame( '10', $facts['Number of modules'] );
		$this->assertSame( '450 Wp', $facts['Power per panel'] );
		$this->assertSame( '0 kW', $facts['Continuous discharge power'] );
		$this->assertSame( '6 kWh', $facts['Usable storage capacity'] );
		$this->assertContains( 'April proposal', $facts );
		$controls = Context::inquiry_notes_section( array(), null, $project, show_project: false );
		$this->assertStringContainsString( 'Meter is upstairs', $controls );
		$this->assertStringContainsString( 'name="linker_include_project_notes"', $controls );
		$this->assertStringContainsString( 'name="linker_project_note_revisions[project_' . $project['project_id'] . ']" value="3"', $controls );
		$this->assertStringNotContainsString( 'Europe/Berlin', $controls );
		$this->assertStringContainsString( 'Europe/Berlin', Context::inquiry_notes_section( array(), null, $project ) );
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
