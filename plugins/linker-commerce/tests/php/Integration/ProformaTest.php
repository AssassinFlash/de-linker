<?php
/**
 * Issuing a Proforma invoice in a real WooCommerce.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Settings\Options;
use RuntimeException;
use WC_Order;
use WC_Order_Item_Product;

/**
 * Staff price the lines, issue the Proforma; it takes the next number of the
 * year, its VAT follows the prices even without "Recalculate", the PDF is kept
 * privately, and nobody but the customer may download it.
 *
 * @coversNothing
 */
final class ProformaTest extends IntegrationTestCase {

	/**
	 * Issuing after staff priced a line without recalculating.
	 */
	public function test_issue(): void {
		$this->with_bank_account();
		$this->with_german_vat();
		$customer = $this->customer();
		$priced   = $this->product( '1680' );
		$unpriced = $this->product( '' );
		$order    = $this->send_inquiry(
			$customer,
			array(
				array( $priced, 2 ),
				array( $unpriced, 1 ),
			)
		);
		$this->as_user( 0 );
		$issuer = $this->issuer();
		$this->assertSame( 'Set a price for every product before issuing the Proforma invoice.', $issuer->blocker( $order ) );

		// Staff set the missing price as in the inquiry screen, without "Recalculate".
		foreach ( $order->get_items() as $item ) {
			if ( $item instanceof WC_Order_Item_Product && $item->get_product_id() === $unpriced->get_id() ) {
				$item->set_subtotal( '1000' );
				$item->set_total( '1000' );
				$item->save();
			}
		}
		$order = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $order );
		$year   = (int) wp_date( 'Y' );
		$before = (int) get_option( Sequence::OPTION_PREFIX . $year, 0 );

		$number = $issuer->issue( $order );

		$this->assertSame( Sequence::format( ( new Options() )->proforma_prefix(), $year, $before + 1 ), $number );
		$order = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $order );
		$this->assertSame( Statuses::PROFORMA, $order->get_status() );
		$this->assertSame( $number, $order->get_meta( Issuer::NUMBER_META ) );
		$this->assertEqualsWithDelta( ( 3360 + 1000 ) * 0.19, (float) $order->get_total_tax(), 0.005, 'VAT on the prices staff set.' );
		$path = ( new PrivateFiles( Issuer::DIRECTORY ) )->path( (string) $order->get_meta( Issuer::FILE_META ) );
		$this->assertFileExists( $path );
		$this->assertStringStartsWith( '%PDF-', (string) file_get_contents( $path ) );
		$this->later(
			static function () use ( $path ): void {
				wp_delete_file( $path );
			}
		);

		// A guest and another customer get a 403 from the download link.
		$download = new DocumentDownload( new PrivateFiles( Issuer::DIRECTORY ), new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' ) );
		$this->as_user( 0 );
		$this->assertSame( 403, $this->download_status( $download, $order->get_id() ) );
		$this->as_user( $this->customer()->get_id() );
		$this->assertSame( 403, $this->download_status( $download, $order->get_id() ) );

		$this->expectException( RuntimeException::class );
		$this->expectExceptionMessage( 'This inquiry already has a Proforma invoice.' );
		$issuer->issue( $order );
	}

	/**
	 * Two requests issuing the same inquiry at once open exactly one Proforma:
	 * the per-inquiry claim keeps the second out (review 2026-10-10, S1).
	 */
	public function test_two_concurrent_issues_open_one_proforma(): void {
		$this->with_bank_account();
		$this->with_german_vat();
		$order = $this->send_inquiry( $this->customer(), array( array( $this->product( '1000' ), 1 ) ) );
		$this->as_user( 0 );

		$number = $this->issuer()->issue( $order );
		$this->assertMatchesRegularExpression( '/^PI-\d{4}-\d{4}$/', $number );

		// A second process races the first on a fresh, unissued inquiry.
		$second = $this->send_inquiry( $this->customer(), array( array( $this->product( '1000' ), 1 ) ) );
		$this->as_user( 0 );
		$results = $this->issue_concurrently( $second->get_id() );
		$opened  = array_values( array_filter( $results, static fn ( string $out ): bool => str_starts_with( $out, 'OK ' ) ) );
		$refused = array_values( array_filter( $results, static fn ( string $out ): bool => str_starts_with( $out, 'REFUSED' ) ) );
		$this->assertCount( 1, $opened, 'Exactly one Proforma: ' . implode( ' | ', $results ) );
		$this->assertCount( 1, $refused, 'The other request is refused: ' . implode( ' | ', $results ) );
		// The winning process wrote the number in its own request; read it past
		// this process's HPOS meta cache.
		$stored = $GLOBALS['wpdb']->get_var(
			$GLOBALS['wpdb']->prepare(
				'SELECT meta_value FROM ' . $GLOBALS['wpdb']->prefix . 'wc_orders_meta WHERE order_id = %d AND meta_key = %s',
				$second->get_id(),
				Issuer::NUMBER_META
			)
		);
		$this->assertSame( (string) $stored, substr( $opened[0], 3 ) );
	}

	/**
	 * Two PHP processes issue the inquiry at the same moment.
	 *
	 * @param int $order_id Inquiry.
	 * @return list<string> Their outcomes: "OK <number>" or "REFUSED <message>".
	 */
	private function issue_concurrently( int $order_id ): array {
		$script = sys_get_temp_dir() . '/linker-issue-' . $order_id . '-' . wp_generate_password( 6, false ) . '.php';
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_file_put_contents -- a test fixture outside WP_Filesystem's scope.
		file_put_contents(
			$script,
			<<<'LINKER_SCRIPT'
<?php
define( 'WP_USE_THEMES', false );
// The suite runs with 2048M (phpunit.integration.xml.dist): dompdf renders a
// Proforma in memory. A proc_open child does not inherit that ini.
ini_set( 'memory_limit', '2048M' );
$_SERVER['HTTP_HOST']   = getenv( 'WP_HOST' );
$_SERVER['REQUEST_URI'] = '/';
require getenv( 'WP_ROOT' ) . '/wp-load.php';
$options = new \Linker\Commerce\Settings\Options();
$issuer  = new \Linker\Commerce\Proforma\Issuer(
	$options,
	new \Linker\Commerce\Proforma\Sequence(),
	new \Linker\Commerce\Proforma\Document( $options ),
	new \Linker\Commerce\Proforma\Renderer( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' ),
	new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Proforma\Issuer::DIRECTORY ),
	new \Linker\Commerce\Gating\PriceDisplay( new \Linker\Commerce\Gating\CommerceState() )
);
try {
	echo 'OK ' . $issuer->issue( wc_get_order( (int) getenv( 'ORDER' ) ) );
} catch ( \Throwable $refused ) {
	echo 'REFUSED ' . $refused->getMessage();
}
LINKER_SCRIPT
		);
		$this->later(
			static function () use ( $script ): void {
				unlink( $script );
			}
		);
		$env  = array(
			'WP_ROOT' => rtrim( (string) getenv( 'LINKER_WP_ROOT' ), '/' ),
			'WP_HOST' => wp_parse_url( home_url(), PHP_URL_HOST ),
			'ORDER'   => (string) $order_id,
		);
		$runs = array();
		for ( $i = 0; $i < 2; ++$i ) {
			$pipes = array();
			// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- the concurrency under test needs a real second process.
			$runs[ $i ]    = proc_open(
				array( PHP_BINARY, $script ),
				array(
					1 => array( 'pipe', 'w' ),
					2 => array( 'pipe', 'w' ),
				),
				$pipes,
				null,
				$env
			);
			$streams[ $i ] = $pipes[1];
			$errs[ $i ]    = $pipes[2];
		}
		$out = array( '', '' );
		foreach ( $streams as $i => $stream ) {
			$out[ $i ] = (string) stream_get_contents( $stream );
			fclose( $stream );
			fclose( $errs[ $i ] );
			if ( is_resource( $runs[ $i ] ) ) {
				proc_close( $runs[ $i ] );
			}
		}
		return array_values( array_map( static fn ( string $line ): string => trim( $line ), $out ) );
	}

	/**
	 * The issuer as the plugin builds it.
	 */
	private function issuer(): Issuer {
		$options = new Options();
		return new Issuer( $options, new Sequence(), new Document( $options ), new Renderer( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php' ), new PrivateFiles( Issuer::DIRECTORY ), new PriceDisplay( new CommerceState() ) );
	}

	/**
	 * A bank account in the settings, the example IBAN of ISO 13616 when none is set.
	 */
	private function with_bank_account(): void {
		if ( '' !== ( new Options() )->bank()['iban'] ) {
			return;
		}
		update_option( Options::BANK_IBAN, 'DE89370400440532013000' );
		$this->later(
			static function (): void {
				delete_option( Options::BANK_IBAN );
			}
		);
	}

	/**
	 * German VAT of 19 % as on the live site (tax rate "MwSt. 19%"), when the instance has no German rate.
	 */
	private function with_german_vat(): void {
		if ( 'yes' !== get_option( 'woocommerce_calc_taxes' ) ) {
			update_option( 'woocommerce_calc_taxes', 'yes' );
			$this->later(
				static function (): void {
					update_option( 'woocommerce_calc_taxes', 'no' );
				}
			);
		}
		if ( array() !== \WC_Tax::find_rates( array( 'country' => 'DE' ) ) ) {
			return;
		}
		$rate_id = \WC_Tax::_insert_tax_rate(
			array(
				'tax_rate_country'  => 'DE',
				'tax_rate'          => '19.0000',
				'tax_rate_name'     => 'MwSt. 19%',
				'tax_rate_priority' => 1,
				'tax_rate_shipping' => 1,
			)
		);
		$this->later(
			static function () use ( $rate_id ): void {
				\WC_Tax::_delete_tax_rate( $rate_id );
			}
		);
	}

	/**
	 * The HTTP status the download link answers with, where it refuses.
	 *
	 * @param DocumentDownload $download The download handler.
	 * @param int              $order_id Inquiry.
	 */
	private function download_status( DocumentDownload $download, int $order_id ): int {
		$_GET = array(
			DocumentDownload::QUERY_VAR => 'proforma',
			'id'                        => (string) $order_id,
		);
		// wp_die() ends the request; here it throws with the HTTP status instead.
		$die     = static function ( $message, $title, $args ): void {
			throw new RuntimeException( 'wp_die', (int) ( $args['response'] ?? 500 ) );
		};
		$handler = static fn (): callable => $die;
		add_filter( 'wp_die_handler', $handler );
		try {
			$download->serve();
			$this->fail( 'The document was served.' );
		} catch ( RuntimeException $refused ) {
			return $refused->getCode();
		} finally {
			remove_filter( 'wp_die_handler', $handler );
			$_GET = array();
		}
	}
}
