<?php
/**
 * An unapproved account cannot read a Proforma's amounts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Abilities\InquiryStatus;
use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\Documents;
use Linker\Commerce\Account\InquiryList;
use Linker\Commerce\Account\PrivateFiles;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Presentation\AccountTemplates;
use Linker\Commerce\Proforma\Document;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Proforma\Renderer;
use Linker\Commerce\Proforma\Sequence;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Settings\Options;
use RuntimeException;
use WC_Customer;
use WC_Order;
use WC_Order_Item_Product;
use WP_REST_Request;

/**
 * Four account states, in English and in German. A real Proforma is issued at
 * 1680. Pending and restricted accounts get no link, and a direct request for
 * the URL an approved account was given returns no PDF. An approved account
 * still receives the file. Guests stay on the ownership denial.
 *
 * The amount check is the fixture price (1680.00 / 1.680,00 / 1,680.00), not a
 * date and not the order id. The formatted totals are collected from the
 * approved inquiry, so a VAT line that is not 1680 is still an amount.
 *
 * @coversNothing
 */
final class ProformaPriceGateTest extends IntegrationTestCase {

	/**
	 * The fixture price as Woo prints it: 1680.00, 1680,00, 1.680,00, 1,680.00.
	 */
	private const AMOUNT = '/(?:1680[.,]00|1[.,]680)/';

	/**
	 * PDF bytes captured when the download is allowed to stream.
	 *
	 * @var string
	 */
	private static string $served = '';

	/**
	 * Response headers serve() sent before the PDF.
	 *
	 * @var string
	 */
	private static string $headers = '';

	/**
	 * Formatted amounts of the issued inquiry, taken while the account is approved.
	 *
	 * @var list<string>
	 */
	private array $marks = array();

	/**
	 * The download query an approved account was given, requested again without
	 * reading the link the page shows.
	 *
	 * @var string
	 */
	private string $issued_url = '';

	/**
	 * Pending and restricted responses carry no amount. The approved account's
	 * list, detail and PDF still do.
	 */
	public function test_proforma_amounts_follow_the_price_gate(): void {
		$this->bind_account_shortcodes();
		$this->with_bank_account();
		$this->with_german_vat();
		$customer = $this->customer();
		$order    = $this->send_inquiry( $customer, array( array( $this->product( '1680' ), 1 ) ) );
		$this->as_user( 0 );
		$number = $this->issuer()->issue( $order );
		$this->assertNotSame( '', $number );

		$order = wc_get_order( $order->get_id() );
		$this->assertInstanceOf( WC_Order::class, $order );
		$path = ( new PrivateFiles( Issuer::DIRECTORY ) )->path( (string) $order->get_meta( Issuer::FILE_META ) );
		$this->assertFileExists( $path );
		$this->later(
			static function () use ( $path ): void {
				wp_delete_file( $path );
			}
		);
		$pdf = (string) file_get_contents( $path );
		$this->assertStringStartsWith( '%PDF-', $pdf );
		$proof = self::pdf_text( $pdf );
		$this->assertMatchesRegularExpression( self::AMOUNT, $proof, 'The issued PDF contains the 1680 price. ' . substr( $proof, 0, 500 ) );

		$this->as_user( $customer->get_id() );
		$this->marks = $this->price_marks( $order );
		$this->assertNotEmpty( $this->marks, 'The approved inquiry formats an amount.' );
		$this->issued_url = DocumentDownload::proforma_url( $order );
		$this->assertStringContainsString( 'linker-document=proforma', $this->issued_url );
		$this->assertStringContainsString( 'id=' . $order->get_id(), $this->issued_url );

		foreach ( array( 'en_US', 'de_DE_formal' ) as $locale ) {
			$this->in_locale(
				$locale,
				function () use ( $customer, $order, $locale ): void {
					$this->set_state( $customer, Approval::APPROVED );
					$this->as_user( $customer->get_id() );
					$this->marks = $this->price_marks( $order );
					$this->assertNotEmpty( $this->marks, $locale );

					$this->as_user( 0 );
					$this->assert_closed( $customer, $order, $locale . ' guest', 403, true );

					foreach ( array( Approval::PENDING, Approval::RESTRICTED ) as $status ) {
						$reason = Approval::RESTRICTED === $status ? 'Net prices are for businesses.' : '';
						$this->set_state( $customer, $status, $reason );
						$this->as_user( $customer->get_id() );
						$this->assert_closed( $customer, $order, $locale . ' ' . $status, 404, false );
					}

					$this->set_state( $customer, Approval::APPROVED );
					$this->as_user( $customer->get_id() );
					$this->assert_open( $customer, $order, $locale );
				}
			);
		}

		// Staff still receive the file when the owning account may not.
		$this->set_state( $customer, Approval::PENDING, '' );
		$this->as_user( 1 );
		$this->assertStringContainsString( 'linker-document=proforma', DocumentDownload::proforma_url( $order ) );
		$staff = $this->download_url( $this->issued_url );
		$this->assertSame( 200, $staff['status'], 'staff' );
		$this->assertStringStartsWith( '%PDF-', $staff['body'], 'staff' );
		$this->assertStringContainsString( 'Content-Type: application/pdf', self::$headers, 'staff' );
		$this->assertMatchesRegularExpression( self::AMOUNT, self::pdf_text( $staff['body'] ), 'staff' );
	}

	/**
	 * No link, no amount, and the recorded URL returns no PDF.
	 *
	 * @param WC_Customer $customer Account that owns the inquiry.
	 * @param WC_Order    $order    Issued inquiry.
	 * @param string      $where    Assertion context.
	 * @param int         $status   HTTP status of the direct download.
	 * @param bool        $guest    Whether the visitor is logged out.
	 */
	private function assert_closed( WC_Customer $customer, WC_Order $order, string $where, int $status, bool $guest ): void {
		$row = ( new AccountTemplates() )->inquiry_row( $order );
		$this->assertSame( '', $row['proforma_url'], $where );
		$this->assertSame( '', $row['total'], $where );

		$list      = $this->render( 'myaccount/orders.php', $this->list_args( $order ) );
		$detail    = $this->render( 'myaccount/view-order.php', array( 'order' => $order ) );
		$documents = $this->documents( $customer->get_id() );
		$docs      = $this->render( 'myaccount/linker-documents.php', array( 'documents' => $documents ) );
		$actions   = ( new InquiryList() )->actions( array(), $order );
		$this->assertArrayNotHasKey( 'proforma', $actions, $where );
		foreach ( $documents as $document ) {
			$this->assertNotSame( 'proforma', $document['kind'] ?? '', $where );
		}

		$rest = $this->status_response();
		if ( $guest ) {
			$this->assertSame( 401, $rest['status'], $where );
		} else {
			$this->assertSame( 200, $rest['status'], $where );
			$inquiry = $this->only_inquiry( $rest['data'] );
			$this->assertSame( $order->get_id(), $inquiry['id'], $where );
			$this->assertArrayNotHasKey( 'total', $inquiry, $where );
		}

		// The query is the one the approved link carried. Nothing on this page points at it.
		$download = $this->download_url( $this->issued_url );
		$this->assertSame( $status, $download['status'], $where );
		$this->assertStringStartsNotWith( '%PDF-', $download['body'], $where );

		$this->assert_no_amount(
			$list . $detail . $docs . (string) wp_json_encode( $row ) . (string) wp_json_encode( $actions ) . (string) wp_json_encode( $documents ) . $rest['raw'] . $download['body'],
			$where
		);
	}

	/**
	 * The list, the detail, the document row and the PDF all keep the amount.
	 *
	 * @param WC_Customer $customer Approved account.
	 * @param WC_Order    $order    Issued inquiry.
	 * @param string      $where    Assertion context.
	 */
	private function assert_open( WC_Customer $customer, WC_Order $order, string $where ): void {
		$row = ( new AccountTemplates() )->inquiry_row( $order );
		$this->assertIsString( $row['proforma_url'] );
		$this->assertStringContainsString( 'linker-document=proforma', $row['proforma_url'], $where );
		$this->assertStringContainsString( 'id=' . $order->get_id(), $row['proforma_url'], $where );
		$this->assertNotSame( '', $row['total'], $where );

		$list      = $this->render( 'myaccount/orders.php', $this->list_args( $order ) );
		$detail    = $this->render( 'myaccount/view-order.php', array( 'order' => $order ) );
		$documents = $this->documents( $customer->get_id() );
		$docs      = $this->render( 'myaccount/linker-documents.php', array( 'documents' => $documents ) );
		$actions   = ( new InquiryList() )->actions( array(), $order );
		$this->assertArrayHasKey( 'proforma', $actions, $where );
		$this->assertStringContainsString( 'linker-document=proforma', $actions['proforma']['url'], $where );
		$kinds = array();
		foreach ( $documents as $document ) {
			$kinds[] = $document['kind'] ?? '';
			if ( 'proforma' === ( $document['kind'] ?? '' ) ) {
				$this->assertStringContainsString( 'id=' . $order->get_id(), $document['url'], $where );
			}
		}
		$this->assertContains( 'proforma', $kinds, $where );

		$rest = $this->status_response();
		$this->assertSame( 200, $rest['status'], $where );
		$inquiry = $this->only_inquiry( $rest['data'] );
		$this->assertSame( (string) $order->get_total(), $inquiry['total'] ?? '', $where );

		$download = $this->download_url( $this->issued_url );
		$this->assertSame( 200, $download['status'], $where );
		$this->assertStringStartsWith( '%PDF-', $download['body'], $where );
		$this->assertStringContainsString( 'Content-Type: application/pdf', self::$headers, $where );
		$this->assertMatchesRegularExpression( self::AMOUNT, self::pdf_text( $download['body'] ), $where );

		$this->assert_shows_amount( $list, $where . ' list' );
		$this->assert_shows_amount( $detail, $where . ' detail' );
		$this->assertStringContainsString( 'data-action="proforma"', $detail, $where );
		$this->assertStringContainsString( 'linker-document=proforma', $detail, $where );
		$this->assertStringContainsString( 'linker-document=proforma', $docs, $where );
	}

	/**
	 * The rendered page itself carries a formatted amount. The row array is not
	 * the page.
	 *
	 * @param string $html  List or detail markup.
	 * @param string $where Assertion context.
	 */
	private function assert_shows_amount( string $html, string $where ): void {
		$found = false;
		foreach ( $this->marks as $mark ) {
			if ( str_contains( $html, $mark ) ) {
				$found = true;
				break;
			}
		}
		$this->assertTrue( $found, $where . ' is missing a formatted amount.' );
	}

	/**
	 * PHPUnit loads WordPress inside a function, then copies that function's
	 * $shortcode_tags — the empty array shortcodes.php assigned — onto the
	 * global add_shortcode() filled. do_shortcode() then finds no tag. The
	 * account adapter is static and survives; these are its own callbacks.
	 */
	private function bind_account_shortcodes(): void {
		$adapter = ( new \ReflectionProperty( AccountTemplates::class, 'adapter' ) )->getValue();
		$this->assertInstanceOf( AccountTemplates::class, $adapter );
		$tags = $GLOBALS['shortcode_tags'] ?? array();
		$this->later(
			static function () use ( $tags ): void {
				$GLOBALS['shortcode_tags'] = $tags;
			}
		);
		add_shortcode( 'linker_account_field', array( $adapter, 'field' ) );
		add_shortcode( 'linker_account_rows', array( $adapter, 'rows' ) );
		add_shortcode( 'linker_account_hook', array( $adapter, 'hook' ) );
		add_shortcode( 'linker_account_text', array( $adapter, 'text' ) );
		add_shortcode( 'linker_account_url', array( $adapter, 'url' ) );
		add_shortcode( 'linker_account_nav', array( $adapter, 'nav' ) );
	}

	/**
	 * Woo's list arguments for the inquiries fragment.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return array<string, mixed>
	 */
	private function list_args( WC_Order $order ): array {
		return array(
			'customer_orders' => (object) array(
				'orders'        => array( $order ),
				'max_num_pages' => 1,
				'total'         => 1,
			),
			'has_orders'      => true,
			'current_page'    => 1,
		);
	}

	/**
	 * The account template the plugin registered, with these Woo arguments.
	 *
	 * @param string               $template Woo template name.
	 * @param array<string, mixed> $args     Template arguments.
	 */
	private function render( string $template, array $args ): string {
		$_GET = array();
		ob_start();
		AccountTemplates::output(
			array(
				'template_name' => $template,
				'args'          => $args,
			)
		);
		return (string) ob_get_clean();
	}

	/**
	 * Documents of one customer, through the same assembly the page uses.
	 *
	 * @param int $customer_id Customer.
	 * @return list<array{title: string, date: int, url: string, kind?: string}>
	 */
	private function documents( int $customer_id ): array {
		return ( new Documents( new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' ), '' ) )->for_customer( $customer_id );
	}

	/**
	 * Numeric amounts Woo formatted for this inquiry.
	 *
	 * @param WC_Order $order Issued inquiry.
	 * @return list<string>
	 */
	private function price_marks( WC_Order $order ): array {
		$html = $order->get_formatted_order_total();
		foreach ( $order->get_items() as $item ) {
			if ( $item instanceof WC_Order_Item_Product ) {
				$html .= ' ' . $order->get_formatted_line_subtotal( $item );
			}
		}
		foreach ( $order->get_tax_totals() as $tax ) {
			if ( isset( $tax->formatted_amount ) && is_string( $tax->formatted_amount ) ) {
				$html .= ' ' . $tax->formatted_amount;
			}
		}
		$found = array();
		preg_match_all( '/\d[\d.,]*\d/', wp_strip_all_tags( $html ), $found );
		$marks = array();
		foreach ( $found[0] as $token ) {
			if ( strlen( $token ) < 4 || in_array( $token, $marks, true ) ) {
				continue;
			}
			$marks[] = $token;
		}
		return $marks;
	}

	/**
	 * No fixture amount, no currency mark, and no download link.
	 *
	 * @param string $text  Rendered response.
	 * @param string $where Assertion context.
	 */
	private function assert_no_amount( string $text, string $where ): void {
		$this->assertDoesNotMatchRegularExpression( self::AMOUNT, $text, $where );
		$this->assertDoesNotMatchRegularExpression( '/€|&euro;|\bEUR\b/', $text, $where );
		$this->assertStringNotContainsString( 'linker-document=proforma', $text, $where );
		$this->assertStringNotContainsString( 'data-action="proforma"', $text, $where );
		foreach ( $this->marks as $mark ) {
			$this->assertStringNotContainsString( $mark, $text, $where );
		}
	}

	/**
	 * GET linker/inquiry-status as the current session.
	 *
	 * @return array{status: int, raw: string, data: array<string, mixed>}
	 */
	private function status_response(): array {
		$request  = new WP_REST_Request( 'GET', '/wp-abilities/v1/abilities/' . InquiryStatus::NAME . '/run' );
		$server   = rest_get_server();
		$response = $server->dispatch( $request );
		$data     = $response->get_data();
		$raw      = wp_json_encode( $server->response_to_data( $response, false ) );
		$this->assertIsArray( $data );
		$this->assertIsString( $raw );

		return array(
			'status' => $response->get_status(),
			'raw'    => $raw,
			'data'   => $data,
		);
	}

	/**
	 * The one inquiry in a successful payload.
	 *
	 * @param array<string, mixed> $data Response data.
	 * @return array<string, mixed>
	 */
	private function only_inquiry( array $data ): array {
		$this->assertArrayHasKey( 'inquiries', $data );
		$this->assertIsArray( $data['inquiries'] );
		$this->assertCount( 1, $data['inquiries'] );
		$inquiry = $data['inquiries'][0];
		$this->assertIsArray( $inquiry );

		return $inquiry;
	}

	/**
	 * Requests the recorded download URL. The page's link is not consulted:
	 * $_GET is the query that URL carried.
	 *
	 * @param string $url Approved account's Proforma URL.
	 * @return array{status: int, body: string}
	 * @throws \RuntimeException When the download ends in an unexpected exception.
	 */
	private function download_url( string $url ): array {
		$query = array();
		$raw   = wp_parse_url( $url, PHP_URL_QUERY );
		parse_str( is_string( $raw ) ? $raw : '', $query );
		$kind          = $query[ DocumentDownload::QUERY_VAR ] ?? '';
		$id            = $query['id'] ?? '';
		$_GET          = array(
			DocumentDownload::QUERY_VAR => is_string( $kind ) ? $kind : '',
			'id'                        => is_string( $id ) ? $id : '',
		);
		self::$served  = '';
		self::$headers = '';
		$status        = 0;
		$body          = '';
		$die           = static function ( string $message, string $title, array $args ) use ( &$status, &$body ): void {
			unset( $title );
			$status = (int) ( $args['response'] ?? 500 );
			$body   = $message;
			throw new RuntimeException( 'wp_die' );
		};
		$handler       = static fn (): callable => $die;
		add_filter( 'wp_die_handler', $handler );
		try {
			( new DocumentDownload( new PrivateFiles( Issuer::DIRECTORY ), new SavedSolutions( new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ), '' ) ) )->serve();
			$this->fail( 'The download returned without a response.' );
		} catch ( RuntimeException $answer ) {
			if ( 'proforma-bytes' === $answer->getMessage() ) {
				$status = 200;
				$body   = self::$served;
			} elseif ( 'wp_die' !== $answer->getMessage() ) {
				throw $answer;
			}
		} finally {
			remove_filter( 'wp_die_handler', $handler );
			$_GET = array();
		}

		return array(
			'status' => $status,
			'body'   => $body,
		);
	}

	/**
	 * Runs the check in $locale. German must actually switch.
	 *
	 * @param string           $locale Locale.
	 * @param callable(): void $check  Assertions.
	 */
	private function in_locale( string $locale, callable $check ): void {
		$switched = switch_to_locale( $locale );
		if ( 'de_DE_formal' === $locale ) {
			$this->assertTrue( $switched, 'German did not switch.' );
		}
		try {
			$check();
		} finally {
			if ( $switched ) {
				restore_previous_locale();
			}
		}
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
	 * German VAT of 19 % as on the live site, when the instance has no German rate.
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
	 * Records the PDF serve() is about to stream, in place of the process exiting.
	 *
	 * @param string $filename Private PDF.
	 */
	public static function keep_pdf( string $filename ): void {
		$bytes        = file_get_contents( $filename );
		self::$served = is_string( $bytes ) ? $bytes : '';
	}

	/**
	 * Records a response header serve() would have sent.
	 *
	 * @param string $header        Header line.
	 * @param bool   $replace       Replaces a previous header of the same name.
	 * @param int    $response_code HTTP status.
	 */
	public static function keep_header( string $header, bool $replace, int $response_code ): void {
		self::$headers .= ( $replace ? '1' : '0' ) . $response_code . ' ' . $header . "\n";
	}

	/**
	 * Text of a Proforma PDF. dompdf draws Identity-H glyph ids, so the amount
	 * is not a byte sequence in the file. pdftotext applies the font's
	 * ToUnicode map. CI installs poppler for this; a missing binary fails the
	 * assertion instead of skipping it.
	 *
	 * @param string $bytes PDF file.
	 */
	private static function pdf_text( string $bytes ): string {
		$pdf = tempnam( sys_get_temp_dir(), 'linker-pf-' );
		if ( ! is_string( $pdf ) ) {
			return '';
		}
		$txt = $pdf . '.txt';
		file_put_contents( $pdf, $bytes );
		$pipes = array();
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- reads the PDF's text; the bytes themselves are glyph ids.
		$process = proc_open(
			array( 'pdftotext', '-layout', $pdf, $txt ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'pipe', 'w' ),
			),
			$pipes
		);
		$error   = '';
		if ( is_resource( $process ) ) {
			fclose( $pipes[1] );
			$error = (string) stream_get_contents( $pipes[2] );
			fclose( $pipes[2] );
			proc_close( $process );
		}
		$text = is_file( $txt ) ? (string) file_get_contents( $txt ) : '';
		wp_delete_file( $pdf );
		if ( is_file( $txt ) ) {
			wp_delete_file( $txt );
		}
		return '' === $text ? 'pdftotext produced no text. ' . $error : $text;
	}
}

require_once __DIR__ . '/proforma-price-gate-capture.php';
