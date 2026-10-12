<?php
/**
 * Tests for the Proforma email.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Proforma;

use Linker\Commerce\Inquiry\OrderLocale;
use Linker\Commerce\Proforma\Emails\ProformaIssuedEmail;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Mock;

/**
 * Tests for ProformaIssuedEmail.
 *
 * @covers \Linker\Commerce\Proforma\Emails\ProformaIssuedEmail
 */
final class ProformaIssuedEmailTest extends TestCase {

	/**
	 * The plugin's text domain may reload while an email renders (LocaleSwitch).
	 */
	public function setUp(): void {
		parent::setUp();
		$this->reload_plugin_textdomain();
	}

	/**
	 * Issuing emails the customer, in the inquiry's language, the number, validity and a link; no attachment.
	 */
	public function test_sends_the_link(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_inquiry-received_to_proforma-issued_notification', ProformaIssuedEmail::class, 'trigger', 10, 2 );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_id' )->andReturn( 20 );
		$order->allows( 'get_billing_email' )->andReturn( 'maria@example.test' );
		$order->allows( 'get_order_number' )->andReturn( '20' );
		$order->allows( 'get_meta' )->with( OrderLocale::META )->andReturn( 'en_US' );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( 'PI-2026-0001' );
		$order->allows( 'get_meta' )->with( Issuer::ISSUED_META )->andReturn( '1760000000' );
		$order->allows( 'get_view_order_url' )->andReturn( 'https://example.test/my-account/inquiry/20/' );
		$this->allow_locale_switch( 'en_US' );
		WP_Mock::expectAction( 'linker_test_email_sent', 'linker_proforma_issued', 'maria@example.test' );

		$email = new ProformaIssuedEmail( '/plugin/linker-commerce.php' );
		$email->trigger( 20, $order );

		$this->assertSame( 'PI-2026-0001', $email->placeholders['{proforma_number}'] );
		$this->assertSame( 'Your Proforma invoice {proforma_number} for inquiry #{order_number}', $email->get_default_subject() );

		WP_Mock::userFunction( 'wp_date', array( 'return' => static fn ( string $format, int $time ): string => gmdate( 'Y-m-d', $time ) ) );
		WP_Mock::userFunction( 'home_url', array( 'return' => 'https://example.test/' ) );
		WP_Mock::userFunction( 'add_query_arg', array( 'return' => static fn ( array $args, string $url ): string => $url . '?' . http_build_query( $args ) ) );
		WP_Mock::userFunction(
			'wc_get_template_html',
			array(
				'times'  => 1,
				'args'   => array(
					'emails/linker-proforma-issued.php',
					Mockery::on(
						static fn ( array $args ): bool => 'PI-2026-0001' === $args['proforma_number']
							&& '2025-11-08' === $args['valid_until']
							&& 'https://example.test/?linker-document=proforma&id=20' === $args['download_url']
							&& 'https://example.test/my-account/inquiry/20/' === $args['inquiry_url']
					),
					'',
					'/plugin/templates/',
				),
				'return' => '<p>ok</p>',
			)
		);
		$this->assertSame( '<p>ok</p>', $email->get_content_html() );
		$this->assertConditionsMet();
	}

	/**
	 * A status change into "Proforma invoice issued" that could not issue — no
	 * bank account, an empty inquiry, a line without a price — leaves the number
	 * empty. That transition must not send the customer an email with an empty
	 * number, a validity of 1970 and a download that 404s.
	 */
	public function test_does_not_send_when_the_number_is_missing(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_inquiry-received_to_proforma-issued_notification', ProformaIssuedEmail::class, 'trigger', 10, 2 );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( '' );
		$order->allows( 'get_billing_email' )->never();
		$order->allows( 'get_meta' )->with( Issuer::ISSUED_META )->never();
		WP_Mock::userFunction( 'switch_to_locale' )->never();

		$email = new ProformaIssuedEmail( '/plugin/linker-commerce.php' );
		$email->trigger( 20, $order );

		$this->assertSame( '', $email->placeholders['{proforma_number}'] );
		$this->assertSame( '', $email->recipient );
		$this->assertConditionsMet();
	}

	/**
	 * The notification carries only the inquiry id when the mailer reloads the
	 * order. A reloaded inquiry that still has no number is the same refusal.
	 */
	public function test_does_not_send_when_a_reloaded_inquiry_has_no_number(): void {
		$this->plain_text();
		WP_Mock::userFunction( 'plugin_dir_path', array( 'return' => '/plugin/' ) );
		$this->expect_action_on_any( 'woocommerce_order_status_inquiry-received_to_proforma-issued_notification', ProformaIssuedEmail::class, 'trigger', 10, 2 );
		$order = Mockery::mock( WC_Order::class );
		$order->allows( 'get_meta' )->with( Issuer::NUMBER_META )->andReturn( '' );
		$order->allows( 'get_billing_email' )->never();
		WP_Mock::userFunction(
			'wc_get_order',
			array(
				'args'   => array( 20 ),
				'return' => $order,
			)
		);
		WP_Mock::userFunction( 'switch_to_locale' )->never();

		$email = new ProformaIssuedEmail( '/plugin/linker-commerce.php' );
		$email->trigger( 20, false );

		$this->assertSame( '', $email->recipient );
		$this->assertConditionsMet();
	}
}
