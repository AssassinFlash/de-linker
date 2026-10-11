<?php
/**
 * Tests for issuing a Proforma invoice.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Tests\Fixtures\WooCommerce;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use RuntimeException;
use WC_Order;
use WC_Order_Item_Product;
use WP_Mock;

/**
 * Tests for Issuer, with the real numbering, document, dompdf renderer and file storage.
 *
 * @covers \Linker\Commerce\Proforma\Issuer
 */
final class IssuerTest extends TestCase {

	/**
	 * Uploads directory of the test.
	 *
	 * @var string
	 */
	private string $uploads;

	/**
	 * The options table of the fake $wpdb.
	 *
	 * @var array<string, string>
	 */
	private array $table = array();

	/**
	 * Numbers another request claims just before this one commits.
	 *
	 * @var int
	 */
	private int $competitors = 0;

	/**
	 * Option values of the test.
	 *
	 * @var array<string, mixed>
	 */
	private array $option_values = array( Options::BANK_IBAN => 'DE89370400440532013000' );

	/**
	 * A temporary uploads directory, a fake $wpdb, WordPress's file and date helpers, and the language switch.
	 */
	public function setUp(): void {
		parent::setUp();
		$this->plain_text();
		$this->reload_plugin_textdomain();
		$this->uploads = sys_get_temp_dir() . '/linker-issuer-' . bin2hex( random_bytes( 4 ) );
		mkdir( $this->uploads );
		WP_Mock::userFunction( 'wp_upload_dir', array( 'return' => array( 'basedir' => $this->uploads ) ) );
		WP_Mock::userFunction( 'wp_mkdir_p', array( 'return' => static fn ( string $dir ): bool => is_dir( $dir ) || mkdir( $dir, 0777, true ) ) );
		WP_Mock::userFunction( 'sanitize_file_name', array( 'return' => static fn ( string $name ): string => $name ) );
		WP_Mock::userFunction( 'wp_delete_file', array( 'return' => static fn ( string $file ): bool => unlink( $file ) ) );
		WP_Mock::userFunction( 'wp_timezone', array( 'return' => new \DateTimeZone( 'Europe/Berlin' ) ) );
		WP_Mock::userFunction( 'wp_date', array( 'return' => static fn ( string $format, int $time ): string => gmdate( 'Y-m-d', $time ) ) );
		WP_Mock::userFunction( 'wc_price', array( 'return' => static fn ( float $amount ): string => '€' . number_format( $amount, 2 ) ) );
		WP_Mock::userFunction( 'sanitize_email', array( 'return' => static fn ( string $email ): string => $email ) );
		WP_Mock::userFunction( 'get_option', array( 'return' => fn ( string $name, $default_value = false ) => $this->option_values[ $name ] ?? $default_value ) );
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => dirname( __DIR__, 4 ) . '/' ) );
		WP_Mock::userFunction( 'get_temp_dir', array( 'return' => sys_get_temp_dir() . '/' ) );
		WP_Mock::userFunction( 'wc_get_template_html', array( 'return' => static fn ( string $template, array $args ): string => '<html><body><h1>' . $args['proforma']['number'] . '</h1></body></html>' ) );
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => 'orderable' ) );
		WP_Mock::userFunction( 'is_user_logged_in', array( 'return' => true ) );
		WP_Mock::userFunction( 'WC', array( 'return' => new WooCommerce() ) );
		WP_Mock::userFunction( 'switch_to_locale', array( 'return' => true ) );
		WP_Mock::userFunction( 'restore_previous_locale', array( 'return' => true ) );
		WP_Mock::userFunction( 'remove_filter', array( 'return' => true ) );

		$wpdb          = Mockery::mock( \stdClass::class );
		$wpdb->options = 'wp_options';
		$wpdb->allows( 'prepare' )->andReturnUsing( static fn ( string $sql, ...$args ): array => $args );
		$wpdb->allows( 'get_var' )->andReturnUsing( fn ( array $args ) => $this->table[ $args[0] ] ?? null );
		$wpdb->allows( 'query' )->andReturnUsing(
			function ( array $args ): int {
				[ $value, $name, $expected ] = $args;
				if ( $this->competitors > 0 ) {
					--$this->competitors;
					$this->table[ $name ] = (string) ( (int) $this->table[ $name ] + 1 );
				}
				if ( $this->table[ $name ] !== $expected ) {
					return 0;
				}
				$this->table[ $name ] = $value;
				return 1;
			}
		);
		$GLOBALS['wpdb'] = $wpdb;
		WP_Mock::userFunction(
			'add_option',
			array(
				'return' => function ( string $name, $value ): bool {
					// The sequence's option rows live in the faked option table
					// (Sequence reads them past the cache); the claim is read
					// through get_option(), so both stores are kept in step.
					if ( isset( $this->table[ $name ] ) || isset( $this->option_values[ $name ] ) ) {
						return false;
					}
					$this->table[ $name ]        = (string) $value;
					$this->option_values[ $name ] = (string) $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_cache_delete', array( 'return' => true ) );
		WP_Mock::userFunction(
			'delete_option',
			array(
				'return' => function ( string $name ): bool {
					$had = isset( $this->option_values[ $name ] );
					unset( $this->table[ $name ], $this->option_values[ $name ] );
					return $had;
				},
			)
		);
	}

	/**
	 * Removes the temporary files and the fake $wpdb.
	 */
	public function tearDown(): void {
		unset( $GLOBALS['wpdb'] );
		$files = new \RecursiveIteratorIterator( new \RecursiveDirectoryIterator( $this->uploads, \FilesystemIterator::SKIP_DOTS ), \RecursiveIteratorIterator::CHILD_FIRST );
		foreach ( $files as $file ) {
			$file->isDir() ? rmdir( $file->getPathname() ) : unlink( $file->getPathname() );
		}
		rmdir( $this->uploads );
		parent::tearDown();
	}

	/**
	 * Rendering switches to the inquiry's language.
	 */
	private function expect_rendering(): void {
		// @phpstan-ignore argument.type (an AnyInstance callback, see TestCase::expect_action_on_any)
		WP_Mock::expectFilterAdded( 'plugin_locale', array( new WP_Mock\Matcher\AnyInstance( \Linker\Commerce\Mail\LocaleSwitch::class ), 'plugin_locale' ) );
	}

	/**
	 * The issuer of a test.
	 */
	private function issuer(): Issuer {
		$options = new Options();
		return new Issuer( $options, new Sequence(), new Document( $options ), new Renderer( dirname( __DIR__, 4 ) . '/linker-commerce.php' ), new PrivateFiles( Issuer::DIRECTORY ), new PriceDisplay( $this->approved_state() ) );
	}

	/**
	 * A received inquiry with one priced line.
	 *
	 * @param string $status Status.
	 * @param string $number Proforma number already issued.
	 * @param bool   $priced Whether the line has a price.
	 * @return WC_Order&\Mockery\MockInterface
	 */
	private function inquiry( string $status = Statuses::RECEIVED, string $number = '', bool $priced = true ) {
		$line = Mockery::mock( WC_Order_Item_Product::class );
		$line->allows( 'get_meta' )->with( '_linker_price_reason' )->andReturn( $priced ? '' : 'unpriced' );
		$line->allows( 'get_total' )->andReturn( $priced ? '1680' : '0' );
		$line->allows( 'get_product' )->andReturn( null );
		$line->allows( 'get_name' )->andReturn( 'SAJ H2-10K-T3' );
		$line->allows( 'get_quantity' )->andReturn( 1 );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_status' )->andReturn( $status );
		$order->allows( 'get_items' )->andReturn( array( $line ) );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( $number );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'de_DE_formal' );
		$order->allows( 'get_meta' )->with( '_billing_vat_id' )->andReturn( '' );
		$order->allows( 'get_currency' )->andReturn( 'EUR' );
		$order->allows( 'get_item_subtotal' )->andReturn( 1680.0 );
		$order->allows( 'get_fees' )->andReturn( array() );
		$order->allows( 'get_tax_totals' )->andReturn( array() );
		$order->allows( 'get_address' )->andReturn( array() );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_billing_company' )->andReturn( 'Solarbau GmbH' );
		$order->allows( 'get_formatted_billing_full_name' )->andReturn( 'Maria Beispiel' );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_subtotal' )->andReturn( 1680.0 );
		$order->allows( 'get_total' )->andReturn( '1999.20' );
		return $order;
	}

	/**
	 * Only a received inquiry with products, every product priced and a bank account configured gets a Proforma.
	 */
	public function test_blockers(): void {
		$issuer = $this->issuer();

		$this->assertSame( '', $issuer->blocker( $this->inquiry() ) );
		$this->assertSame( 'This inquiry already has a Proforma invoice.', $issuer->blocker( $this->inquiry( Statuses::PROFORMA, 'PI-2026-0001' ) ) );
		$this->assertSame( 'Only a received inquiry gets a Proforma invoice.', $issuer->blocker( $this->inquiry( 'completed' ) ) );
		$this->assertSame( 'Set a price for every product before issuing the Proforma invoice.', $issuer->blocker( $this->inquiry( Statuses::RECEIVED, '', false ) ) );
		$this->option_values = array();
		$this->assertStringStartsWith( 'Enter the bank account', $issuer->blocker( $this->inquiry() ) );
	}

	/**
	 * Issuing recalculates the VAT for the prices staff set, stores the PDF under the next number, records it on the inquiry and moves it to "Proforma invoice issued".
	 */
	public function test_issue(): void {
		$order = $this->inquiry();
		$year  = ( new \DateTimeImmutable( 'now', new \DateTimeZone( 'Europe/Berlin' ) ) )->format( 'Y' );
		$meta  = array();
		$order->allows( 'update_meta_data' )->andReturnUsing(
			function ( string $key, $value ) use ( &$meta ): void {
				$meta[ $key ] = $value;
			}
		);
		$order->expects( 'calculate_totals' )->with( true )->once()->ordered();
		$order->expects( 'update_status' )->with( Statuses::PROFORMA, "Proforma invoice PI-$year-0001 issued." )->ordered();
		$this->expect_rendering();

		$this->assertSame( "PI-$year-0001", $this->issuer()->issue( $order ) );

		$this->assertSame( "PI-$year-0001", $meta[ Issuer::NUMBER_META ] );
		$this->assertMatchesRegularExpression( "#^20/PI-$year-0001-[0-9a-f]{16}\\.pdf$#", $meta[ Issuer::FILE_META ] );
		$this->assertSame( '%PDF-', substr( (string) file_get_contents( $this->uploads . '/proforma/' . $meta[ Issuer::FILE_META ] ), 0, 5 ) );
		$this->assertFileExists( $this->uploads . '/proforma/.htaccess' );
		$this->assertStringContainsString( 'Require all denied', (string) file_get_contents( $this->uploads . '/proforma/.htaccess' ) );
	}

	/**
	 * When another request takes the number meanwhile, the PDF is discarded and rendered again with the next number.
	 */
	public function test_retries_with_the_next_number(): void {
		$this->competitors = 1;
		$order             = $this->inquiry();
		$order->allows( 'update_meta_data' );
		$order->allows( 'update_status' );
		$order->allows( 'calculate_totals' );
		$year = ( new \DateTimeImmutable( 'now', new \DateTimeZone( 'Europe/Berlin' ) ) )->format( 'Y' );
		$this->expect_rendering();

		$this->assertSame( "PI-$year-0002", $this->issuer()->issue( $order ) );
		$pdfs = glob( $this->uploads . '/proforma/20/*.pdf' );
		$this->assertIsArray( $pdfs );
		$this->assertCount( 1, $pdfs, 'The PDF rendered with the lost number is gone.' );
	}

	/**
	 * A blocked inquiry is refused with the reason.
	 */
	public function test_refuses_a_blocked_inquiry(): void {
		$this->expectException( RuntimeException::class );
		$this->expectExceptionMessage( 'Only a received inquiry gets a Proforma invoice.' );

		$this->issuer()->issue( $this->inquiry( 'cancelled' ) );
	}

	/**
	 * A live claim of another request refuses the second issue (review 2026-10-10:
	 * two concurrent presses opened two Proformas and sent two emails).
	 */
	public function test_refuses_an_inquiry_another_request_is_issuing(): void {
		$this->option_values['linker_proforma_claim_20'] = (string) time();
		$order = $this->inquiry();
		$order->allows( 'update_meta_data' );
		$order->allows( 'update_status' );
		$order->allows( 'calculate_totals' )->never();

		try {
			$this->issuer()->issue( $order );
			$this->fail( 'The second issue was not refused.' );
		} catch ( RuntimeException $refused ) {
			$this->assertStringContainsString( 'being issued a Proforma invoice right now', $refused->getMessage() );
		}
	}

	/**
	 * A claim from a request that died is taken over once it is older than an hour.
	 */
	public function test_takes_over_a_stale_claim(): void {
		$this->option_values['linker_proforma_claim_20'] = (string) ( time() - 2 * HOUR_IN_SECONDS );
		$order = $this->inquiry();
		$order->allows( 'update_meta_data' );
		$order->allows( 'update_status' );
		$order->allows( 'calculate_totals' );
		$year = ( new \DateTimeImmutable( 'now', new \DateTimeZone( 'Europe/Berlin' ) ) )->format( 'Y' );
		$this->expect_rendering();

		$this->assertSame( "PI-$year-0001", $this->issuer()->issue( $order ) );
	}

	/**
	 * The claim is released after issuing, also when the body fails.
	 */
	public function test_releases_the_claim_in_both_endings(): void {
		$order = $this->inquiry();
		$order->allows( 'update_meta_data' );
		$order->allows( 'update_status' );
		$order->allows( 'calculate_totals' )->andThrow( new RuntimeException( 'body fails' ) );

		try {
			$this->issuer()->issue( $order );
			$this->fail( 'The failure did not surface.' );
		} catch ( RuntimeException $ignored ) {
			$this->assertSame( 'body fails', $ignored->getMessage() );
		}
		$this->assertArrayNotHasKey( 'linker_proforma_claim_20', $this->option_values );
	}
}
