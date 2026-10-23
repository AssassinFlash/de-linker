<?php
/**
 * Tests for the route that saves solutions.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\DesignProof;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Account\SolutionsRoute;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WP_Error;
use WP_Mock;
use WP_REST_Request;
use WP_REST_Response;

/**
 * Tests for SolutionsRoute.
 *
 * @covers \Linker\Commerce\Account\SolutionsRoute
 */
final class SolutionsRouteTest extends TestCase {

	/**
	 * Current Woo authority, independent of the browser body.
	 *
	 * @var bool
	 */
	private bool $current = true;

	/**
	 * Complete verified engine fixture.
	 *
	 * @return array<string,mixed>
	 */
	private static function result(): array {
		return array(
			'selection_fingerprint' => str_repeat( 'a', 64 ),
			'publication'           => array(
				'products'               => array(
					array(
						'product_id'       => 4107,
						'product_revision' => str_repeat( 'b', 64 ),
					),
				),
				'documents'              => array(),
				'compatibility_revision' => str_repeat( 'c', 64 ),
			),
			'selected'              => array(
				'lines' => array(
					array(
						'product'  => array(
							'id'    => 4107,
							'brand' => 'Test',
							'model' => 'Recorded',
						),
						'quantity' => 2,
					),
				),
			),
		);
	}

	/**
	 * The immutable saved design.
	 *
	 * @return array<string,mixed>
	 */
	private static function design(): array {
		return array(
			'kind'                  => 'residential',
			'input'                 => array( 'plz' => '39179' ),
			'selection_fingerprint' => str_repeat( 'a', 64 ),
			'snapshot'              => self::result(),
		);
	}

	/**
	 * Uploads directory of the test.
	 *
	 * @var string
	 */
	private string $uploads;

	/**
	 * Post meta written by the store.
	 *
	 * @var array<string, mixed>
	 */
	private array $meta = array();

	/**
	 * Published product 4107, draft product 4108; a temporary uploads directory.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'get_option', array( 'return' => 'http://engine.test' ) );
		$this->uploads = sys_get_temp_dir() . '/linker-route-' . bin2hex( random_bytes( 4 ) );
		mkdir( $this->uploads );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $this->uploads ) ) );
		WP_Mock::userFunction( 'wp_mkdir_p', array( 'return' => static fn ( string $dir ): bool => is_dir( $dir ) || mkdir( $dir, 0777, true ) ) );
		WP_Mock::userFunction( 'sanitize_file_name', array( 'return' => static fn ( string $name ): string => $name ) );
		WP_Mock::userFunction( 'sanitize_title', array( 'return' => static fn ( string $title ): string => strtolower( str_replace( ' ', '-', $title ) ) ) );
		WP_Mock::userFunction( 'sanitize_text_field', array( 'return' => static fn ( string $text ): string => trim( strip_tags( $text ) ) ) );
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->meta[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_max_upload_size', array( 'return' => 1024 ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/saved-solutions/' ) );
		$products = array();
		foreach ( array(
			4107 => 'publish',
			4108 => 'draft',
		) as $id => $status ) {
			$products[ $id ] = Mockery::mock( \WC_Product::class );
			$products[ $id ]->allows( 'get_status' )->andReturn( $status );
		}
		WP_Mock::userFunction( 'wc_get_product', array( 'return' => static fn ( int $id ) => $products[ $id ] ?? false ) );
	}

	/**
	 * Removes the temporary directory.
	 */
	public function tearDown(): void {
		$files = new \RecursiveIteratorIterator( new \RecursiveDirectoryIterator( $this->uploads, \FilesystemIterator::SKIP_DOTS ), \RecursiveIteratorIterator::CHILD_FIRST );
		foreach ( $files as $file ) {
			$file->isDir() ? rmdir( $file->getPathname() ) : unlink( $file->getPathname() );
		}
		rmdir( $this->uploads );
		parent::tearDown();
	}

	/**
	 * The route of the test.
	 */
	private function route(): SolutionsRoute {
		return new SolutionsRoute( new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '/plugin/templates/' ), new DesignProof( fn (): array => array( 'valid' => $this->current ), static fn (): array => array( 200, (string) json_encode( self::result() ) ) ) );
	}

	/**
	 * A request as the configurator sends it.
	 *
	 * @param array<string, mixed> $changes Parameters that differ.
	 */
	private static function request( array $changes = array() ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', '/linker/v1/solutions' );
		$params  = array_merge(
			array(
				'kind'                  => 'residential',
				'title'                 => 'House <b>Barleben</b>',
				'selection_fingerprint' => str_repeat( 'a', 64 ),
				'input'                 => array( 'plz' => '39179' ),
				'lines'                 => array(
					array(
						'product_id' => 4107,
						'quantity'   => 2,
					),
				),
			),
			$changes
		);
		foreach ( $params as $key => $value ) {
			$request->set_param( $key, $value );
		}
		return $request;
	}

	/**
	 * The route takes POST from anyone, with the configurator's body described for validation.
	 */
	public function test_register(): void {
		$route = $this->route();
		WP_Mock::userFunction(
			'register_rest_route',
			array(
				'times'  => 1,
				'return' => function ( string $route_namespace, string $path, array $options ) use ( $route ): bool {
					$this->assertSame( 'linker/v1', $route_namespace );
					$this->assertSame( '/solutions', $path );
					$this->assertSame( 'POST', $options['methods'] );
					$this->assertSame( array( $route, 'create' ), $options['callback'] );
					$this->assertSame( '__return_true', $options['permission_callback'] );
					$this->assertSame( array( 'system_index', 'kind', 'title', 'input', 'lines', 'selection_fingerprint', 'report_pdf' ), array_keys( $options['args'] ) );
					$this->assertSame( SolutionsRoute::KINDS, $options['args']['kind']['enum'] );
					$this->assertSame( array( 'product_id', 'quantity' ), $options['args']['lines']['items']['required'] );
					$this->assertFalse( $options['args']['lines']['items']['additionalProperties'] );
					return true;
				},
			)
		);

		$route->register();

		$this->assertConditionsMet();
	}

	/**
	 * A customer's solution is saved with its design and report and opens at its row.
	 */
	public function test_customer_save(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => SavedSolutions::POST_TYPE,
						'post_status' => 'private',
						'post_author' => 5,
						'post_title'  => 'House Barleben',
					),
					true,
				),
				'return' => 45,
			)
		);

		$response = $this->route()->create( self::request( array( 'report_pdf' => self::base64( '%PDF-1.7 report' ) ) ) );

		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 201, $response->get_status() );
		$this->assertSame(
			array(
				'id'          => 45,
				'url'         => 'https://example.test/my-account/saved-solutions/#linker-solution-45',
				'publication' => self::result()['publication'],
			),
			$response->get_data()
		);
		$this->assertSame( '[{"product_id":4107,"quantity":2}]', $this->meta[ SavedSolutions::ITEMS_META ] );
		$this->assertSame( self::design(), json_decode( $this->meta[ SavedSolutions::DESIGN_META ], true ) );
		$this->assertSame( '%PDF-1.7 report', file_get_contents( $this->uploads . '/solution-reports/' . $this->meta[ SavedSolutions::REPORT_META ] ) );
	}

	/**
	 * A guest's solution waits in their session; the answer says it is accepted, not yet saved.
	 */
	public function test_guest_save(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 0 ) );
		WP_Mock::userFunction( 'wc_load_cart', array( 'times' => 1 ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );
		$session = Mockery::mock( \WC_Session_Handler::class );
		$session->allows( 'get' )->andReturn( array() );
		$session->expects( 'set' )->with(
			SavedSolutions::SESSION_KEY,
			array(
				array(
					'title'  => 'House Barleben',
					'items'  => array(
						array(
							'product_id' => 4107,
							'quantity'   => 2,
						),
					),
					'design' => self::design(),
				),
			)
		);
		$session->expects( 'set_customer_session_cookie' )->with( true );
		$woocommerce          = new \stdClass();
		$woocommerce->session = $session;
		WP_Mock::userFunction( 'WC', array( 'return' => $woocommerce ) );

		$response = $this->route()->create( self::request() );

		$this->assertInstanceOf( WP_REST_Response::class, $response );
		$this->assertSame( 202, $response->get_status() );
		$this->assertSame(
			array(
				'id'          => 0,
				'url'         => 'https://example.test/my-account/saved-solutions/',
				'publication' => self::result()['publication'],
			),
			$response->get_data()
		);
	}

	/**
	 * Unknown and unpublished products and a report that is not a PDF within the upload limit are refused.
	 *
	 * @dataProvider refused_requests
	 *
	 * @param array<string, mixed> $changes Parameters that differ from a valid request.
	 * @param string               $code    Expected error code.
	 */
	public function test_refusals( array $changes, string $code ): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );

		$response = $this->route()->create( self::request( $changes ) );

		$this->assertInstanceOf( WP_Error::class, $response );
		$this->assertSame( $code, $response->get_error_code() );
		$this->assertSame( array( 'status' => 'linker_solution_changed' === $code ? 409 : 400 ), $response->get_error_data() );
	}

	/**
	 * Requests the route refuses.
	 *
	 * @return array<string, array{array<string, mixed>, string}>
	 */
	public static function refused_requests(): array {
		$line = static fn ( int $product_id ): array => array(
			'lines' => array(
				array(
					'product_id' => $product_id,
					'quantity'   => 1,
				),
			),
		);
		return array(
			'unknown product'   => array( $line( 9999 ), 'linker_solution_changed' ),
			'draft product'     => array( $line( 4108 ), 'linker_solution_changed' ),
			'report not base64' => array( array( 'report_pdf' => '%%%' ), 'linker_solution_report' ),
			'report not a PDF'  => array( array( 'report_pdf' => self::base64( '<html>' ) ), 'linker_solution_report' ),
			'report too large'  => array( array( 'report_pdf' => self::base64( '%PDF-' . str_repeat( 'x', 1024 ) ) ), 'linker_solution_report' ),
		);
	}

	/**
	 * When WordPress cannot store the solution, the customer is told.
	 */
	public function test_store_failure(): void {
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => 5 ) );
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => new WP_Error( 'db', 'down' ) ) );

		$response = $this->route()->create( self::request() );

		$this->assertInstanceOf( WP_Error::class, $response );
		$this->assertSame( 'linker_solution_not_saved', $response->get_error_code() );
		$this->assertSame( array( 'status' => 500 ), $response->get_error_data() );
	}

	/** A stale full candidate set cannot be saved using a still-published subset. */
	public function test_current_authority_refuses_the_whole_design(): void {
		$this->current = false;
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );
		$error = $this->route()->create( self::request() );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 409, $error->get_error_data()['status'] );
	}

	/** A pre-contract or tampered request cannot fall back to product IDs alone. */
	public function test_missing_fingerprint_is_refused_before_writing(): void {
		WP_Mock::userFunction( 'wp_insert_post', array( 'times' => 0 ) );
		$error = $this->route()->create( self::request( array( 'selection_fingerprint' => '' ) ) );
		$this->assertInstanceOf( WP_Error::class, $error );
		$this->assertSame( 'linker_solution_changed', $error->get_error_code() );
	}

	/**
	 * Base64 text of a file, as the configurator sends the design report.
	 *
	 * @param string $bytes File content.
	 */
	private static function base64( string $bytes ): string {
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- the route's report format.
		return base64_encode( $bytes );
	}
}
