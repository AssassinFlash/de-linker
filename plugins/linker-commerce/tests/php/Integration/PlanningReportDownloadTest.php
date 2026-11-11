<?php
/**
 * Private inquiry report downloads on their native REST route.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Planning\ReportDownload;
use Linker\Commerce\Products\Publication;
use WC_Order;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * The one channel through which a customer receives the report of their inquiry:
 * GET /linker/v1/inquiries/<id>/planning-report/<handoff>, with the order key
 * or the owner's session. Staff reads too. Every other caller gets the same 404,
 * so a stranger learns nothing about the inquiry or its report. The bytes must
 * be the frozen PDF of the stored context; anything else is a 503 and never a
 * partial file.
 *
 * The Tools reader is the production seam; these tests replace it with a double
 * so the route's own authorisation, identity and hash decisions are what is
 * under test. ReportAccessTest covers the reader itself.
 *
 * @covers \Linker\Commerce\Planning\ReportDownload
 */
final class PlanningReportDownloadTest extends IntegrationTestCase {

	/**
	 * The PDF this test's stored reference names.
	 */
	private const PDF = "%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n";

	/**
	 * What the seam answered, per call.
	 *
	 * @var list<array{reference: array<string,mixed>, order: int}>
	 */
	private array $reads = array();

	/**
	 * The engine handoff stored per inquiry, keyed by order id.
	 *
	 * @var array<int,array<string,mixed>>
	 */
	private array $handoffs = array();

	/**
	 * Decides what the report seam answers for this test: bytes, or the
	 * refusal to pass through.
	 *
	 * The registered Tools reader would reach a real service; the in-process
	 * tests are about the route, so the seam is replaced and put back afterwards.
	 *
	 * @var string|WP_Error
	 */
	private string|WP_Error $answer = self::PDF;

	/**
	 * Installs the seam double and keeps the production wiring aside.
	 */
	protected function setUp(): void {
		parent::setUp();
		global $wp_filter;
		$hook = $wp_filter['linker_tools_planning_report_content'] ?? null;
		$kept = $hook instanceof \WP_Hook ? $hook->callbacks : array();
		remove_all_filters( 'linker_tools_planning_report_content' );
		$seam = function ( mixed $previous, array $reference, int $order_id ): string|WP_Error {
			unset( $previous );
			$this->reads[] = array(
				'reference' => $reference,
				'order'     => $order_id,
			);
			return $this->answer;
		};
		add_filter( 'linker_tools_planning_report_content', $seam, 10, 3 );
		$this->later(
			static function () use ( $kept, $seam ): void {
				remove_filter( 'linker_tools_planning_report_content', $seam, 10 );
				// Put the production reader back exactly as the Tools plugin
				// registered it, so a later test sees the instance unchanged.
				foreach ( $kept as $priority => $callbacks ) {
					foreach ( $callbacks as $callback ) {
						add_filter( 'linker_tools_planning_report_content', $callback['function'], (int) $priority, $callback['accepted_args'] );
					}
				}
			}
		);
	}

	/**
	 * The customer's link carries the order key; the browser gets the file.
	 */
	public function test_the_order_key_delivers_the_frozen_pdf(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$handoff  = $this->handoff_of( $order );

		$response = $this->dispatch( $order->get_id(), $handoff, $order->get_order_key() );

		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( self::PDF, $response->get_data() );
		$this->assertSame( 'application/pdf', $response->get_headers()['Content-Type'] ?? '' );
		$this->assertSame(
			'attachment; filename="linker-planning-' . $order->get_id() . '.pdf"',
			$response->get_headers()['Content-Disposition'] ?? ''
		);
		$this->assertCount( 1, $this->reads );
		$this->assertSame( $order->get_id(), $this->reads[0]['order'] );
		$this->assertSame( $this->stored_reference( $order ), $this->reads[0]['reference'] );
	}

	/**
	 * The signed-in owner reads without the key; the key is not the identity.
	 */
	public function test_the_signed_in_owner_reads_without_the_key(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );

		$this->as_user( $customer->get_id() );
		$response = $this->dispatch( $order->get_id(), $this->handoff_of( $order ) );

		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( self::PDF, $response->get_data() );
		$this->assertSame( 'application/pdf', $response->get_headers()['Content-Type'] ?? '' );
		$this->assertCount( 1, $this->reads );
	}

	/**
	 * Team access is the shop manager's; it needs neither key nor ownership.
	 */
	public function test_staff_read_the_report(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );

		$this->as_user( 1 );
		$response = $this->dispatch( $order->get_id(), $this->handoff_of( $order ) );

		$this->assertSame( 200, $response->get_status() );
		$this->assertSame( self::PDF, $response->get_data() );
	}

	/**
	 * A guest without the key, a guest with a wrong key, and another customer
	 * all read the same "not available" answer: possession of an inquiry id
	 * confirms nothing, and the seam is never reached.
	 */
	public function test_strangers_cannot_tell_an_inquiry_from_a_missing_one(): void {
		$owner = $this->customer();
		$other = $this->customer();
		$order = $this->inquiry( $owner, self::PDF );
		$id    = $order->get_id();

		$this->as_user( 0 );
		$anonymous = $this->dispatch( $id, $this->handoff_of( $order ) );
		$this->assertSame( 404, $anonymous->get_status() );
		$this->assertSame( 'planning_report_not_found', $anonymous->get_data()['code'] );

		$wrong_key = $this->dispatch( $id, $this->handoff_of( $order ), str_repeat( 'a', 32 ) );
		$this->assertSame( 404, $wrong_key->get_status() );
		$this->assertSame( 'planning_report_not_found', $wrong_key->get_data()['code'] );

		$missing = $this->dispatch( 999999, $this->handoff_of( $order ) );
		$this->assertSame( 404, $missing->get_status() );
		$this->assertSame( 'planning_report_not_found', $missing->get_data()['code'] );

		$this->as_user( $other->get_id() );
		$foreign = $this->dispatch( $id, $this->handoff_of( $order ) );
		$this->assertSame( 404, $foreign->get_status() );
		$this->assertSame( 'planning_report_not_found', $foreign->get_data()['code'] );

		$this->assertSame( array(), $this->reads );
	}

	/**
	 * The report is the one named by the stored context: a handoff the order
	 * does not carry, and an inquiry with no report at all, are both 404.
	 */
	public function test_only_the_stored_handoff_is_readable(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$empty    = $this->inquiry( $customer, null );

		$this->as_user( $customer->get_id() );
		$this->assertSame( 404, $this->dispatch( $order->get_id(), str_repeat( 'b', 32 ) )->get_status() );
		$this->assertSame( 404, $this->dispatch( $empty->get_id(), $this->handoff_of( $order ) )->get_status() );
		$this->assertSame( array(), $this->reads );
	}

	/**
	 * The route serves the frozen bytes or nothing: a seam that refuses, and
	 * bytes that are not the stored PDF, are both 503 without a file.
	 */
	public function test_content_that_is_not_the_frozen_pdf_is_unavailable(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$this->as_user( $customer->get_id() );

		$this->answer = new WP_Error( 'planning_report_unavailable', '', array( 'status' => 503 ) );
		$refused      = $this->dispatch( $order->get_id(), $this->handoff_of( $order ) );
		$this->assertSame( 503, $refused->get_status() );
		$this->assertSame( 'planning_report_unavailable', $refused->get_data()['code'] );

		$this->answer = str_replace( 'Catalog', 'Pages', self::PDF );
		$replaced     = $this->dispatch( $order->get_id(), $this->handoff_of( $order ) );
		$this->assertSame( 503, $replaced->get_status() );
		$this->assertSame( 'planning_report_unavailable', $replaced->get_data()['code'] );

		$this->answer = '<html>not a report</html>';
		$html         = $this->dispatch( $order->get_id(), $this->handoff_of( $order ) );
		$this->assertSame( 503, $html->get_status() );
		$this->assertSame( 'planning_report_unavailable', $html->get_data()['code'] );
	}

	/**
	 * An inquiry that carries no report answers the same 404 as an unknown one,
	 * to its own owner: no report exists, and the answer says no more than that.
	 */
	public function test_an_inquiry_without_a_report_answers_like_an_unknown_one(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, null );

		$this->as_user( $customer->get_id() );
		$absent = $this->dispatch( $order->get_id(), str_repeat( 'c', 32 ) );
		$this->assertSame( 404, $absent->get_status() );
		$this->assertSame( 'planning_report_not_found', $absent->get_data()['code'] );
	}

	/**
	 * The browser chain end to end over HTTP: the route, the stored order
	 * context, the Tools reader and the engine seam. The bytes arrive as a
	 * private attachment, not as a cached or referrer-leaking response.
	 */
	public function test_the_browser_download_serves_the_frozen_pdf_with_private_headers(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$handoff  = $this->handoff_of( $order );
		$this->engine( $order, $handoff, self::PDF );

		$response = $this->download( $order->get_id(), $handoff, $order->get_order_key() );

		$this->assertSame( 200, $response['status'] );
		$this->assertSame( 'application/pdf', $response['headers']['content-type'] ?? '' );
		$this->assertSame(
			'attachment; filename="linker-planning-' . $order->get_id() . '.pdf"',
			$response['headers']['content-disposition'] ?? ''
		);
		$this->assertSame( self::PDF, $response['body'] );
		$this->assertSame( 'no-store, private', $response['headers']['cache-control'] ?? '' );
		$this->assertSame( 'no-cache', $response['headers']['pragma'] ?? '' );
		$this->assertSame( 'no-referrer', $response['headers']['referrer-policy'] ?? '' );
		$this->assertSame( 'nosniff', $response['headers']['x-content-type-options'] ?? '' );
		$this->assertSame( '', $response['headers']['access-control-allow-origin'] ?? '' );
	}

	/**
	 * Bytes that are not the stored PDF are refused over HTTP as well: the
	 * customer never receives a damaged or replaced document.
	 */
	public function test_the_browser_download_refuses_bytes_that_are_not_the_frozen_pdf(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$handoff  = $this->handoff_of( $order );
		$this->engine( $order, $handoff, self::PDF );
		$this->answer( array( 'replace_content' => true ) );

		$response = $this->download( $order->get_id(), $handoff, $order->get_order_key() );

		$this->assertSame( 503, $response['status'] );
		$this->assertStringNotContainsString( '%PDF-', $response['body'] );
		$this->assertSame( 'no-store, private', $response['headers']['cache-control'] ?? '' );
		$this->assertSame( 'no-referrer', $response['headers']['referrer-policy'] ?? '' );
	}

	/**
	 * A refusal still carries the private cache and referrer policy: an error
	 * page must not be cached or leak the inquiry address onward.
	 *
	 * Read over HTTP: the policy is applied on the server's serving path
	 * (`rest_post_dispatch`), which in-process dispatch does not run.
	 */
	public function test_refusals_keep_the_private_header_policy(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );

		$this->as_user( 0 );
		$refused = $this->download( $order->get_id(), $this->handoff_of( $order ), '' );

		$this->assertSame( 404, $refused['status'] );
		$this->assertSame( 'no-store, private', $refused['headers']['cache-control'] ?? '' );
		$this->assertSame( 'no-cache', $refused['headers']['pragma'] ?? '' );
		$this->assertSame( 'no-referrer', $refused['headers']['referrer-policy'] ?? '' );
		$this->assertSame( 'nosniff', $refused['headers']['x-content-type-options'] ?? '' );
		$this->assertStringNotContainsString( '%PDF-', $refused['body'] );
	}

	/**
	 * A wrong key is refused over HTTP exactly like a missing one: no file, no
	 * hint that the inquiry or its report exists.
	 */
	public function test_a_wrong_key_gets_no_file_and_no_hint(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );

		$this->as_user( 0 );
		$wrong = $this->download( $order->get_id(), $this->handoff_of( $order ), str_repeat( 'f', 32 ) );

		$this->assertSame( 404, $wrong['status'] );
		$this->assertStringNotContainsString( '%PDF-', $wrong['body'] );
		$this->assertSame( array(), $this->reads );
	}

	/**
	 * The route answers the address the customer's receipt links to.
	 */
	public function test_the_receipt_link_is_the_download_address(): void {
		$customer = $this->customer();
		$order    = $this->inquiry( $customer, self::PDF );
		$handoff  = $this->handoff_of( $order );

		$this->assertSame( Context::report_url( $order, $handoff ), $this->address( $order->get_id(), $handoff, $order->get_order_key() ) );
	}

	/**
	 * An inquiry of this test, with one frozen report when $pdf is given.
	 *
	 * The stored reference is derived from the engine-owned handoff exactly as
	 * the planner wrote it, so the Tools reader's hash comparison sees the real
	 * pair rather than a restatement of it.
	 *
	 * @param \WC_Customer $customer The inquiry's owner.
	 * @param string|null  $pdf      Frozen PDF bytes, null for no report.
	 */
	private function inquiry( \WC_Customer $customer, ?string $pdf ): WC_Order {
		$order = wc_create_order( array( 'customer_id' => $customer->get_id() ) );
		$this->assertInstanceOf( WC_Order::class, $order );
		$order->set_payment_method( 'linker_inquiry' );
		$order->set_billing_email( $customer->get_billing_email() );
		$order->add_product( $this->product( '100' ), 1 );
		$order->calculate_totals( false );
		if ( null !== $pdf ) {
			$handoff = $this->handoff( $pdf );
			$order->update_meta_data(
				Context::META,
				(string) wp_json_encode( array( $handoff['id'] => array( 'reference' => Context::reference( $handoff ) ) ) )
			);
			$this->handoffs[ $order->get_id() ] = $handoff;
		}
		$order->save();
		$this->later(
			static function () use ( $order ): void {
				$stored = wc_get_order( $order->get_id() );
				if ( $stored instanceof WC_Order ) {
					$stored->delete( true );
				}
			}
		);
		return $order;
	}

	/**
	 * The stored reference of an inquiry's report, as the route passes it on.
	 *
	 * @param WC_Order $order The inquiry.
	 * @return array<string,mixed>
	 */
	private function stored_reference( WC_Order $order ): array {
		$stored = Context::stored( $order );
		$this->assertCount( 1, $stored );
		return $stored[ $this->handoff_of( $order ) ]['reference'];
	}

	/**
	 * Installs the engine seam for the browser half of the chain.
	 *
	 * @param WC_Order $order   The inquiry holding the report.
	 * @param string   $handoff The stored handoff identity.
	 * @param string   $pdf     The frozen PDF bytes.
	 */
	private function engine( WC_Order $order, string $handoff, string $pdf ): void {
		$answer = $this->handoffs[ $order->get_id() ] ?? null;
		$this->assertIsArray( $answer );
		$this->assertSame( $handoff, $answer['id'] );
		require_once dirname( __DIR__, 2 ) . '/fixtures/PlanningReportEngineFixture.php';
		\Linker\Commerce\Tests\Fixtures\PlanningReportEngineFixture::install( $answer, $pdf );
		$this->later(
			static function (): void {
				\Linker\Commerce\Tests\Fixtures\PlanningReportEngineFixture::remove();
			}
		);
	}

	/**
	 * Changes what the installed engine seam answers.
	 *
	 * @param array{refuse_handoff?: bool, refuse_content?: bool, replace_content?: bool} $changes Answers to switch.
	 */
	private function answer( array $changes ): void {
		\Linker\Commerce\Tests\Fixtures\PlanningReportEngineFixture::answer( $changes );
	}

	/**
	 * A minimal engine-owned handoff naming this test's PDF.
	 *
	 * @param string $pdf Frozen PDF bytes.
	 * @return array<string,mixed>
	 */
	private function handoff( string $pdf ): array {
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
					'sha256'     => hash( 'sha256', $pdf ),
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

	/**
	 * The stored handoff identity of an inquiry's first report.
	 *
	 * @param WC_Order $order The inquiry.
	 */
	private function handoff_of( WC_Order $order ): string {
		$stored = Context::stored( $order );
		$this->assertCount( 1, $stored );
		return (string) array_key_first( $stored );
	}

	/**
	 * Dispatches the route in-process, as the REST server does.
	 *
	 * @param int    $order_id Inquiry id.
	 * @param string $handoff  Handoff identity.
	 * @param string $key      Order key, '' for none.
	 */
	private function dispatch( int $order_id, string $handoff, string $key = '' ): WP_REST_Response {
		$request = new WP_REST_Request( 'GET', '/linker/v1/inquiries/' . $order_id . '/planning-report/' . $handoff );
		if ( '' !== $key ) {
			$request->set_param( 'key', $key );
		}
		$response = rest_do_request( $request );
		$this->assertInstanceOf( WP_REST_Response::class, $response );
		return $response;
	}

	/**
	 * The address the receipt links to.
	 *
	 * @param int    $order_id Inquiry id.
	 * @param string $handoff  Handoff identity.
	 * @param string $key      Order key.
	 */
	private function address( int $order_id, string $handoff, string $key ): string {
		return add_query_arg(
			'key',
			$key,
			rest_url( 'linker/v1/inquiries/' . $order_id . '/planning-report/' . $handoff )
		);
	}

	/**
	 * Requests the download over HTTP, so the streaming path runs too.
	 *
	 * @param int    $order_id Inquiry id.
	 * @param string $handoff  Handoff identity.
	 * @param string $key      Order key.
	 * @return array{status: int, headers: array<string, string>, body: string}
	 */
	private function download( int $order_id, string $handoff, string $key ): array {
		$response = wp_remote_get(
			$this->address( $order_id, $handoff, $key ),
			array(
				'redirection' => 0,
				'timeout'     => 30,
			)
		);
		$this->assertNotInstanceOf( WP_Error::class, $response );
		return array(
			'status'  => (int) wp_remote_retrieve_response_code( $response ),
			'headers' => self::headers( $response ),
			'body'    => (string) wp_remote_retrieve_body( $response ),
		);
	}

	/**
	 * The response's headers, lower-cased, as one value per name.
	 *
	 * @param array<string,mixed> $response WP_HTTP reply.
	 * @return array<string,string>
	 */
	private static function headers( array $response ): array {
		// Requests' CaseInsensitiveDictionary keeps its entries in a private
		// member a plain cast would hide; a plain array reply has none.
		$collected = wp_remote_retrieve_headers( $response );
		$all       = $collected instanceof \WpOrg\Requests\Utility\CaseInsensitiveDictionary ? $collected->getAll() : (array) $collected;
		$headers   = array();
		foreach ( $all as $name => $value ) {
			$headers[ strtolower( (string) $name ) ] = is_array( $value ) ? implode( ', ', array_map( 'strval', $value ) ) : (string) $value;
		}
		return $headers;
	}
}
