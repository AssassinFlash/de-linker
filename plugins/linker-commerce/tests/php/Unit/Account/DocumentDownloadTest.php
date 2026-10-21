<?php
/**
 * Tests for document downloads.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Account;

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use RuntimeException;
use WC_Order;
use WP_Mock;

/**
 * Tests for DocumentDownload. wp_die() throws here, as it ends the request in WordPress.
 *
 * @covers \Linker\Commerce\Account\DocumentDownload
 */
final class DocumentDownloadTest extends TestCase {

	/**
	 * The public error response body.
	 *
	 * @var string
	 */
	private string $denial = '';

	/**
	 * Translation and escaping return their input; wp_die() reports its status by exception.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		WP_Mock::userFunction( 'sanitize_key', array( 'return' => static fn ( string $key ): string => strtolower( $key ) ) );
		WP_Mock::userFunction( 'wp_unslash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'absint', array( 'return' => static fn ( $value ): int => abs( (int) $value ) ) );
		WP_Mock::userFunction( 'nocache_headers' );
		WP_Mock::userFunction( 'wc_get_page_permalink', array( 'return' => 'https://example.test/my-account/' ) );
		$this->options( array( 'woocommerce_enable_myaccount_registration' => 'yes' ) );
		WP_Mock::userFunction( 'wc_get_account_endpoint_url', array( 'return' => 'https://example.test/my-account/register/' ) );
		WP_Mock::userFunction(
			'wp_die',
			array(
				'return' => function ( $message, $title, array $args ): void {
					$this->denial = (string) $message;
					throw new RuntimeException( (string) $args['response'] );
				},
			)
		);
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_customer_id' )->andReturn( 5 );
		$order->allows( 'get_meta' )->with( Issuer::FILE_META )->andReturn( '20/PI-2026-0001-abc.pdf' );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0001' );
		WP_Mock::userFunction( 'wc_get_order', array( 'return' => $order ) );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => '/nonexistent' ) ) );
		WP_Mock::userFunction( 'get_post', array( 'return' => null ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => '' ) );
	}

	/** Registration remains secondary to the original account's ownership check. */
	public function test_guest_denial_has_a_register_entry_but_keeps_403(): void {
		$this->assertSame( '403', $this->status( false ) );
		$this->assertStringContainsString( 'Please log in with that account.', $this->denial );
		$this->assertStringContainsString( 'href="https://example.test/my-account/register/"', $this->denial );
	}

	/**
	 * Clears the request.
	 */
	public function tearDown(): void {
		$_GET = array();
		parent::tearDown();
	}

	/**
	 * The downloads of a test.
	 */
	private function downloads(): DocumentDownload {
		return new DocumentDownload( new PrivateFiles( 'proforma' ), new SavedSolutions( new PrivateFiles( 'solution-reports' ), '/plugin/templates/' ) );
	}

	/**
	 * Asks for a document and returns the HTTP status wp_die() gave.
	 *
	 * @param bool $logged_in Whether someone is logged in.
	 * @param int  $user_id   Who.
	 * @param bool $is_staff  Whether that user manages the shop.
	 */
	private function status( bool $logged_in, int $user_id = 0, bool $is_staff = false ): string {
		$_GET = array(
			DocumentDownload::QUERY_VAR => 'proforma',
			'id'                        => '20',
		);
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => $logged_in ) );
		WP_Mock::userFunction( 'get_current_user_id', array( 'return' => $user_id ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => $is_staff ) );
		try {
			$this->downloads()->serve();
		} catch ( RuntimeException $answer ) {
			return $answer->getMessage();
		}
		return 'served';
	}

	/**
	 * A visitor who is not logged in gets 403 (docs/specs/11-commerce.md, acceptance).
	 */
	public function test_guest_gets_403(): void {
		$this->assertSame( '403', $this->status( false ) );
	}

	/**
	 * Another customer gets 403.
	 */
	public function test_other_customer_gets_403(): void {
		$this->assertSame( '403', $this->status( true, 6 ) );
	}

	/**
	 * The owner passes the check (here the file is missing, so the answer is 404).
	 */
	public function test_owner_passes(): void {
		WP_Mock::userFunction(
			'get_user_meta',
			array(
				'return' => static fn ( int $user_id, string $key ): string => 5 === $user_id && Approval::STATUS_META === $key ? Approval::APPROVED : '',
			)
		);
		$this->assertSame( '404', $this->status( true, 5 ) );
	}

	/**
	 * Shop staff pass the check for any customer's document.
	 */
	public function test_staff_passes(): void {
		$this->assertSame( '404', $this->status( true, 9, true ) );
	}

	/**
	 * Requests without the query variable are not touched.
	 */
	public function test_other_requests(): void {
		$_GET = array();
		$this->downloads()->serve();
		$this->assertConditionsMet();
	}

	/**
	 * Links name the kind of document and its id.
	 */
	public function test_urls(): void {
		WP_Mock::userFunction( 'current_user_can', array( 'return' => true ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );

		$this->assertSame( 'https://example.test/?linker-document=proforma&id=20', DocumentDownload::proforma_url( $order ) );
		$this->assertSame( 'https://example.test/?linker-document=report&id=45', DocumentDownload::report_url( 45 ) );
	}

	/**
	 * Account states for the report link, which is not a price gate.
	 *
	 * @return array<string, array{string, bool}>
	 */
	public static function report_link_states(): array {
		return array(
			'pending'    => array( Approval::PENDING, false ),
			'restricted' => array( Approval::RESTRICTED, false ),
			'rejected'   => array( Approval::REJECTED, false ),
			'approved'   => array( Approval::APPROVED, true ),
		);
	}

	/**
	 * A design report has no amounts, so its link stays for every approval
	 * state. The Proforma link stays empty unless the account sees prices.
	 *
	 * @dataProvider report_link_states
	 *
	 * @param string $status Approval state.
	 * @param bool   $prices Whether that state sees net prices.
	 */
	public function test_report_url_is_not_a_price_gate( string $status, bool $prices ): void {
		$this->approval_meta( array( Approval::STATUS_META => $status ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'current_user_can', array( 'return' => false ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );

		$proforma = DocumentDownload::proforma_url( $order );
		$report   = DocumentDownload::report_url( 45 );

		$this->assertSame( $prices ? 'http://linker.test/?linker-document=proforma&id=20' : '', $proforma );
		$this->assertSame( 'http://linker.test/?linker-document=report&id=45', $report );
	}
}
