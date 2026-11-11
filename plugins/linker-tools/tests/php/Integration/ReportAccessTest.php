<?php
/**
 * The server-only report reader: the seam the inquiry download depends on.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Products\Publication;
use Linker\Tools\Planner\ReportAccess;
use Linker\Tools\Planner\Transport;
use PHPUnit\Framework\TestCase;
use WC_Order;
use WP_Error;

/**
 * Only a report already attached to a native inquiry is readable, and only the
 * bytes the stored reference froze are returned. The reader is reached with a
 * server-built identity (team, scoped to the inquiry), never with browser
 * headers or a caller-supplied asset id.
 *
 * The order, its stored metadata and the hash comparisons are real; only the
 * engine answer is a transport double.
 *
 * @covers \Linker\Tools\Planner\ReportAccess
 */
final class ReportAccessTest extends TestCase {

	/**
	 * The frozen PDF of this test's report.
	 */
	private const PDF = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n";

	/**
	 * Every request the double saw.
	 *
	 * @var list<array{path: string, headers: array<string, mixed>, body: array<string, mixed>}>
	 */
	private array $calls = array();

	/**
	 * The order this test's report belongs to.
	 *
	 * @var WC_Order|null
	 */
	private ?WC_Order $order = null;

	/**
	 * The handoff the inquiry stores.
	 *
	 * @var array<string,mixed>
	 */
	private array $stored = array();

	/**
	 * The handoff the engine answers on handoffs/read.
	 *
	 * @var array<string,mixed>
	 */
	private array $answered = array();

	/**
	 * Substitutes for the service's own answer on a path.
	 *
	 * A status code answers as that HTTP refusal (the gateway maps it); a
	 * WP_Error stands for a transport failure, which is always a 503.
	 *
	 * @var array<string, int|WP_Error>
	 */
	private array $refusals = array();

	/**
	 * The PDF the service streams on assets/content.
	 *
	 * @var string
	 */
	private string $content = self::PDF;

	/**
	 * The reply status of assets/content.
	 *
	 * @var int
	 */
	private int $content_status = 200;

	/**
	 * Orders this test created.
	 *
	 * @var list<int>
	 */
	private array $orders = array();

	/**
	 * The instance's planner address, restored afterwards.
	 *
	 * @var mixed
	 */
	private mixed $planner_url = false;

	/**
	 * The planner address this test configured; the transport appends the path.
	 */
	private const PLANNER = 'https://engine.test';

	/**
	 * Skips unless the integration bootstrap loaded WordPress.
	 */
	public static function setUpBeforeClass(): void {
		if ( '1' !== getenv( 'LINKER_INTEGRATION' ) ) {
			self::markTestSkipped( 'Run phpunit.integration.xml.dist against a local instance (just up).' );
		}
	}

	/**
	 * Each test gets its own stored report and a configured transport.
	 */
	protected function setUp(): void {
		parent::setUp();
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			self::markTestSkipped( 'The instance defines no LINKER_GENIE_SERVICE_TOKEN.' );
		}
		$this->planner_url = get_option( 'linker_planner_url' );
		update_option( 'linker_planner_url', self::PLANNER, false );
		$this->calls    = array();
		$this->content  = self::PDF;
		$this->stored   = $this->handoff();
		$this->answered = $this->stored;
		$this->order    = $this->inquiry( $this->stored );
	}

	/**
	 * Removes the orders and restores the instance's settings.
	 */
	protected function tearDown(): void {
		foreach ( $this->orders as $id ) {
			$order = wc_get_order( $id );
			if ( $order instanceof WC_Order ) {
				$order->delete( true );
			}
		}
		if ( false === $this->planner_url ) {
			delete_option( 'linker_planner_url' );
		} else {
			update_option( 'linker_planner_url', $this->planner_url, false );
		}
		$this->orders = array();
		$this->order  = null;
		wp_set_current_user( 0 );
		parent::tearDown();
	}

	/**
	 * The stored report is read through the inquiry's own identity and its
	 * frozen bytes come back untouched.
	 */
	public function test_the_stored_report_is_read_for_the_inquiry(): void {
		$reference = $this->reference();
		$id        = (string) $reference['handoff_id'];

		$reader = new ReportAccess( $this->transport() );
		$body   = $reader->read( new WP_Error( 'unavailable' ), $reference, (int) $this->inquiry_id() );

		$this->assertSame( self::PDF, $body );
		$this->assertCount( 2, $this->calls );
		$this->assertSame( 'handoffs/read', $this->calls[0]['path'] );
		$this->assertSame(
			array(
				'schema_version' => 1,
				'handoff_id'     => $id,
			),
			$this->calls[0]['body']
		);
		$this->assertSame( 'assets/content', $this->calls[1]['path'] );
		$this->assertSame(
			array(
				'schema_version' => 1,
				'project_id'     => $this->stored['snapshot']['project_id'],
				'asset_id'       => $this->stored['snapshot']['pdf']['asset_id'],
			),
			$this->calls[1]['body']
		);
	}

	/**
	 * The reader's identity is the inquiry, built on the server; no browser
	 * header and no caller-chosen asset id travels with it.
	 */
	public function test_the_service_identity_is_the_inquiry_and_carries_no_browser_headers(): void {
		$reader = new ReportAccess( $this->transport() );
		$reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );

		$this->assertCount( 2, $this->calls );
		foreach ( $this->calls as $call ) {
			$this->assertSame( array( 'Content-Type', 'X-Linker-Service-Token', 'X-Linker-Planner-Principal-Kind', 'X-Linker-Planner-Principal-Subject' ), array_keys( $call['headers'] ) );
			$this->assertSame( 'team', $call['headers']['X-Linker-Planner-Principal-Kind'] );
			$this->assertSame( 'wp:' . get_current_blog_id() . ':inquiry:' . $this->inquiry_id(), $call['headers']['X-Linker-Planner-Principal-Subject'] );
			$this->assertSame( (string) constant( 'LINKER_GENIE_SERVICE_TOKEN' ), $call['headers']['X-Linker-Service-Token'] );
		}
	}

	/**
	 * An inquiry that does not exist is refused before any call leaves the site.
	 */
	public function test_an_unknown_inquiry_is_unavailable(): void {
		$reader  = new ReportAccess( $this->transport() );
		$refused = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), 999999 );

		$this->assertInstanceOf( WP_Error::class, $refused );
		$this->assertSame( 503, $refused->get_error_data()['status'] );
		$this->assertSame( array(), $this->calls );
	}

	/**
	 * A reference the inquiry does not store — a foreign handoff, another
	 * inquiry's report — never reaches the service.
	 */
	public function test_a_reference_the_inquiry_does_not_store_is_refused(): void {
		$reader    = new ReportAccess( $this->transport() );
		$reference = $this->reference();

		$foreign                     = $reference;
		$foreign['handoff_id']       = str_repeat( 'a', 32 );
		$foreign['pdf']['asset_id']  = str_repeat( 'b', 32 );
		$foreign['reference_sha256'] = Publication::revision( array_diff_key( $foreign, array( 'reference_sha256' => true ) ) );

		$tampered                  = $reference;
		$tampered['pdf']['sha256'] = hash( 'sha256', 'another report' );

		foreach ( array( $foreign, $tampered ) as $candidate ) {
			$refused = $reader->read( new WP_Error( 'unavailable' ), $candidate, (int) $this->inquiry_id() );
			$this->assertInstanceOf( WP_Error::class, $refused );
			$this->assertSame( 403, $refused->get_error_data()['status'] );
		}
		$this->assertSame( array(), $this->calls );
	}

	/**
	 * A service refusal keeps its own meaning; it is not flattened into bytes.
	 */
	public function test_a_service_refusal_is_passed_through(): void {
		$this->refusals['handoffs/read'] = 404;

		$reader = new ReportAccess( $this->transport() );
		$result = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 404, $result->get_error_data()['status'] );
		$this->assertCount( 1, $this->calls );
		$this->assertSame( 'handoffs/read', $this->calls[0]['path'] );
	}

	/**
	 * An engine answer that names a different handoff than the stored one is
	 * not trusted to decide which report is served, and no file is requested.
	 */
	public function test_an_answer_that_does_not_match_the_stored_reference_is_invalid(): void {
		$other                                       = $this->handoff();
		$this->answered                              = $other;
		$this->answered['snapshot']['pdf']['sha256'] = hash( 'sha256', "another report\n" );

		$reader = new ReportAccess( $this->transport() );
		$result = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 502, $result->get_error_data()['status'] );
		$this->assertCount( 1, $this->calls );
		$this->assertSame( 'handoffs/read', $this->calls[0]['path'] );
	}

	/**
	 * Bytes that are not the frozen PDF — another file, a truncated file, an
	 * HTML page — are refused rather than streamed.
	 */
	public function test_content_that_is_not_the_frozen_pdf_is_refused(): void {
		$reader = new ReportAccess( $this->transport() );

		foreach ( array( str_replace( 'Catalog', 'Pages', self::PDF ), substr( self::PDF, 0, 20 ), '<html>report</html>' ) as $content ) {
			$this->content = $content;
			$result        = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );
			$this->assertInstanceOf( WP_Error::class, $result );
			$this->assertSame( 503, $result->get_error_data()['status'] );
		}

		$this->content        = self::PDF;
		$this->content_status = 500;
		$status               = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );
		$this->assertInstanceOf( WP_Error::class, $status );
		$this->assertSame( 503, $status->get_error_data()['status'] );
	}

	/**
	 * A report whose file was withdrawn (the handoff reads but its asset no
	 * longer streams) is unavailable: the downloadable file is not replaced by
	 * an error page and nothing partial is returned.
	 */
	public function test_a_withdrawn_file_is_unavailable(): void {
		$this->refusals['assets/content'] = 404;

		$reader = new ReportAccess( $this->transport() );
		$result = $reader->read( new WP_Error( 'unavailable' ), $this->reference(), (int) $this->inquiry_id() );

		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 503, $result->get_error_data()['status'] );
		$this->assertCount( 2, $this->calls );
		$this->assertSame( 'assets/content', $this->calls[1]['path'] );
	}

	/**
	 * The transport double: answers per path, records every request.
	 */
	private function transport(): Transport {
		return new Transport(
			function ( string $url, array $args ): array|WP_Error {
				$path          = (string) preg_replace( '~\Ahttps?://[^/]+/~', '', $url );
				$this->calls[] = array(
					'path'    => $path,
					'headers' => (array) $args['headers'],
					'body'    => (array) json_decode( (string) $args['body'], true ),
				);
				if ( isset( $this->refusals[ $path ] ) ) {
					$refusal = $this->refusals[ $path ];
					if ( $refusal instanceof WP_Error ) {
						return $refusal;
					}
					// The service's own refusal: a reply the gateway maps by status.
					return array(
						'response' => array( 'code' => $refusal ),
						'headers'  => array( 'content-type' => 'application/json' ),
						'body'     => (string) wp_json_encode( array( 'error' => array( 'code' => 'not_found' ) ) ),
					);
				}
				if ( 'handoffs/read' === $path ) {
					return array(
						'response' => array( 'code' => 200 ),
						'headers'  => array( 'content-type' => 'application/json' ),
						'body'     => (string) wp_json_encode( $this->answered ),
					);
				}
				if ( 'assets/content' === $path ) {
					return array(
						'response' => array( 'code' => $this->content_status ),
						'headers'  => array( 'content-type' => 200 === $this->content_status ? 'application/octet-stream' : 'application/json' ),
						'body'     => 200 === $this->content_status ? $this->content : '{"error":"unavailable"}',
					);
				}
				return new WP_Error( 'fixture_unexpected_path' );
			}
		);
	}

	/**
	 * An inquiry storing the reference of this test's handoff.
	 *
	 * @param array<string,mixed> $handoff Frozen handoff.
	 */
	private function inquiry( array $handoff ): WC_Order {
		$order = wc_create_order( array( 'customer_id' => 0 ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$order->update_meta_data( Context::META, (string) wp_json_encode( array( $handoff['id'] => array( 'reference' => Context::reference( $handoff ) ) ) ) );
		$order->save();
		$this->orders[] = $order->get_id();
		return $order;
	}

	/**
	 * The inquiry this test's report belongs to.
	 */
	private function inquiry_id(): int {
		$this->assertInstanceOf( WC_Order::class, $this->order );
		return (int) $this->order->get_id();
	}

	/**
	 * The reference the inquiry stores, as the Commerce writer froze it.
	 *
	 * @return array<string,mixed>
	 */
	private function reference(): array {
		return Context::reference( $this->stored );
	}

	/**
	 * A minimal engine-owned handoff naming this test's PDF.
	 *
	 * @return array<string,mixed>
	 */
	private function handoff(): array {
		return array(
			'schema_version'  => 1,
			'id'              => bin2hex( random_bytes( 16 ) ),
			'snapshot_sha256' => hash( 'sha256', 'snapshot' ),
			'snapshot'        => array(
				'schema_version'       => 1,
				'kind'                 => 'planning_products_v1',
				'project_id'           => bin2hex( random_bytes( 16 ) ),
				'title'                => 'Roof plan',
				'revision'             => 3,
				'input_sha256'         => hash( 'sha256', 'input' ),
				'report_run_id'        => bin2hex( random_bytes( 16 ) ),
				'report_source_sha256' => hash( 'sha256', 'source' ),
				'report_sha256'        => hash( 'sha256', 'report' ),
				'pdf'                  => array(
					'asset_id'   => bin2hex( random_bytes( 16 ) ),
					'sha256'     => hash( 'sha256', self::PDF ),
					'media_type' => 'application/pdf',
				),
				'items'                => array(
					array(
						'product_id' => 1,
						'quantity'   => 1,
						'label'      => 'Linker integration test product',
					),
				),
			),
		);
	}
}
