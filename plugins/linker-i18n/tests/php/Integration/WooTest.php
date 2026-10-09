<?php
/**
 * The German shop on the English products.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Tests\Integration;

// phpcs:disable WordPress.WP.AlternativeFunctions -- these tests run outside WordPress.

/**
 * Stock the ERP pushes by SKU reaches both languages; an inquiry placed in
 * German orders the English product under its German name, in an order that
 * remembers German, and the customer's emails are German while the shop's
 * stay English.
 *
 * @coversNothing
 */
final class WooTest extends SiteTestCase {

	/**
	 * The fixture product the tests use.
	 */
	private const SLUG = 'chint-dtsu666';

	/**
	 * The pair: English and German ID, SKU, German name, and the English stock fields to restore.
	 *
	 * @var array<string, mixed>
	 */
	private static array $pair = array();

	/**
	 * Reads the pair.
	 */
	public static function setUpBeforeClass(): void {
		parent::setUpBeforeClass();
		$pair = self::php(
			'
			$english = get_page_by_path( $input["slug"], OBJECT, "product" );
			$id      = pll_get_post( $english->ID, "en" );
			$product = wc_get_product( $id );
			$german  = pll_get_post( $id, "de" );
			return array(
				"en"             => $id,
				"de"             => $german,
				"sku"            => $product->get_sku(),
				"name"           => get_post_field( "post_title", $german ),
				"manage_stock"   => $product->get_manage_stock(),
				"stock_quantity" => $product->get_stock_quantity(),
				"stock_status"   => $product->get_stock_status(),
				"mail"           => defined( "LINKER_LOCAL_DIR" ) ? LINKER_LOCAL_DIR . "/mail" : "",
				"admin_email"    => get_option( "admin_email" ),
			);
			',
			array( 'slug' => self::SLUG )
		);
		self::assertIsArray( $pair );
		self::assertNotSame( '', $pair['sku'] );
		self::$pair = $pair;
	}

	/**
	 * Puts the English product's stock back as it was.
	 */
	public static function tearDownAfterClass(): void {
		if ( array() !== self::$pair ) {
			self::php(
				'$product = wc_get_product( $input["en"] ); $product->set_manage_stock( $input["manage_stock"] ); $product->set_stock_quantity( $input["stock_quantity"] ); $product->set_stock_status( $input["stock_status"] ); return $product->save();',
				self::$pair
			);
		}
		parent::tearDownAfterClass();
	}

	/**
	 * The stock state of the pair as the Store API shows it in each language.
	 *
	 * @return array{en: bool, de: bool}
	 */
	private static function in_stock(): array {
		$english = self::rest( '/wc/store/v1/products/' . self::SLUG );
		$german  = self::rest( '/wc/store/v1/products/' . self::SLUG . '?lang=de' );
		self::assertSame( self::$pair['de'], $german['id'] );
		return array(
			'en' => $english['is_in_stock'],
			'de' => $german['is_in_stock'],
		);
	}

	/**
	 * The ERP finds the product by SKU through wc/v3 (only the English
	 * product has it) and pushes a stock level: both languages follow.
	 */
	public function test_stock_pushed_by_sku_reaches_both_languages(): void {
		$found = json_decode( self::wp( array( 'wc', 'product', 'list', '--sku=' . self::$pair['sku'], '--fields=id', '--format=json' ) ), true );
		$this->assertSame( array( array( 'id' => self::$pair['en'] ) ), $found );
		$this->assertSame(
			array(
				'en' => true,
				'de' => true,
			),
			self::in_stock()
		);

		self::wp( array( 'wc', 'product', 'update', (string) self::$pair['en'], '--manage_stock=true', '--stock_quantity=0' ) );
		$this->assertSame(
			array(
				'en' => false,
				'de' => false,
			),
			self::in_stock()
		);

		self::wp( array( 'wc', 'product', 'update', (string) self::$pair['en'], '--stock_quantity=12' ) );
		$this->assertSame(
			array(
				'en' => true,
				'de' => true,
			),
			self::in_stock()
		);
		$german = self::php( '$product = wc_get_product( $input["de"] ); return array( (string) get_post_meta( $input["de"], "_sku", true ), $product->get_manage_stock(), $product->get_stock_status() );', self::$pair );
		$this->assertSame( array( '', false, 'instock' ), $german );
	}

	/**
	 * The add-to-cart notice of a German request names the German product:
	 * WooCommerce builds the notice's name from get_the_title(), which the
	 * get_name() filter does not reach, so the plugin filters the name in
	 * the quotes itself. The fixture product's titles differ between the
	 * languages (Chint DTSU666's do not: both are the model name).
	 */
	public function test_german_add_to_cart_notice_names_the_german_product(): void {
		$pair = self::php(
			'
			$english = get_page_by_path( "saj-cb2-100-3-hv5", OBJECT, "product" );
			$id      = pll_get_post( $english->ID, "en" );
			return array(
				"en"      => $id,
				"name"    => get_post_field( "post_title", pll_get_post( $id, "de" ) ),
				"name_en" => get_post_field( "post_title", $id ),
			);
			'
		);
		self::assertIsArray( $pair );
		$this->assertNotSame( $pair['name_en'], $pair['name'] );

		$message = self::php(
			'
			$languages = new Linker\I18n\Languages();
			$entered   = $languages->enter( "de" );
			$message   = wc_add_to_cart_message( $input["en"], false, true );
			$languages->leave( $entered );
			return $message;
			',
			array( 'en' => $pair['en'] )
		);
		$this->assertIsString( $message );
		$decoded = html_entity_decode( $message, ENT_QUOTES | ENT_HTML5, 'UTF-8' );
		$this->assertStringNotContainsString( $pair['name_en'], $decoded );
		$this->assertStringContainsString( $pair['name'], $decoded );
		$this->assertStringContainsString( 'wurde Ihrem Warenkorb', $decoded );
	}

	/**
	 * An inquiry through the Store API in German: the order line is the
	 * English product with its German name, the order is German, the
	 * customer's confirmation is German and formal, the shop's notice English;
	 * and when the shop completes the order, that email is German too.
	 */
	public function test_german_inquiry(): void {
		$mail_dir = (string) self::$pair['mail'];
		if ( '' === $mail_dir ) {
			$this->markTestSkipped( 'The site writes no mail to files (LINKER_LOCAL_DIR).' );
		}
		$before = self::mails( $mail_dir );

		$cart    = self::request( 'GET', '/wp-json/wc/store/v1/cart?lang=de' );
		$headers = array(
			'Content-Type' => 'application/json',
			'Cart-Token'   => $cart['headers']['cart-token'] ?? '',
			'Nonce'        => $cart['headers']['nonce'] ?? '',
		);
		$added   = self::request(
			'POST',
			'/wp-json/wc/store/v1/cart/add-item?lang=de',
			$headers,
			(string) json_encode(
				array(
					'id'       => self::$pair['de'],
					'quantity' => 1,
				)
			)
		);
		$this->assertSame( 201, $added['status'], $added['body'] );
		$items = json_decode( $added['body'], true )['items'];
		$this->assertSame( self::$pair['en'], $items[0]['id'] );
		$this->assertSame( self::$pair['name'], html_entity_decode( $items[0]['name'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );

		$address = array(
			'first_name' => 'Erika',
			'last_name'  => 'Muster',
			'company'    => 'Muster Solar GmbH',
			'address_1'  => 'Teststraße 1',
			'city'       => 'Magdeburg',
			'postcode'   => '39106',
			'country'    => 'DE',
			'phone'      => '+49 391 000000',
		);
		$placed  = self::request(
			'POST',
			'/wp-json/wc/store/v1/checkout?lang=de',
			$headers,
			(string) json_encode(
				array(
					'billing_address'  => $address + array( 'email' => 'inquiry@example.test' ),
					'shipping_address' => $address,
					'payment_method'   => 'bacs',
				)
			)
		);
		$this->assertSame( 200, $placed['status'], $placed['body'] );
		$order_id = json_decode( $placed['body'], true )['order_id'];

		$order = self::php(
			'
			$order = wc_get_order( $input["order"] );
			$items = array_values( $order->get_items() );
			return array( "product" => $items[0]->get_product_id(), "name" => $items[0]->get_name(), "language" => $order->get_meta( "_linker_i18n_language" ) );
			',
			array( 'order' => $order_id )
		);
		$this->assertSame(
			array(
				'product'  => self::$pair['en'],
				'name'     => self::$pair['name'],
				'language' => 'de',
			),
			$order
		);

		$sent = array_diff_key( self::mails( $mail_dir ), $before );
		$this->assertCount( 2, $sent );
		$by_recipient = array_column( $sent, null, 'to' );
		$customer     = $by_recipient['inquiry@example.test'];
		$shop         = $by_recipient[ self::$pair['admin_email'] ];
		$this->assertStringStartsWith( 'Ihre Bestellung bei ', $customer['subject'] );
		$this->assertStringContainsString( '<html lang="de-DE">', $customer['body'] );
		$this->assertStringContainsString( self::$pair['name'], html_entity_decode( $customer['body'], ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		$this->assertMatchesRegularExpression( '/\bIhre?\b/u', $customer['body'] );
		$this->assertDoesNotMatchRegularExpression( '/\b(du|dich|dir|dein|deine|deiner)\b/iu', strip_tags( $customer['body'] ) );
		$this->assertStringContainsString( 'New order #' . $order_id, $shop['subject'] );
		$this->assertStringContainsString( '<html lang="en-US">', $shop['body'] );

		// The shop completes the order from the English admin.
		$before = self::mails( $mail_dir );
		self::php( 'return wc_get_order( $input["order"] )->update_status( "completed" );', array( 'order' => $order_id ) );
		$sent = array_values( array_diff_key( self::mails( $mail_dir ), $before ) );
		$this->assertCount( 1, $sent );
		$this->assertSame( 'inquiry@example.test', $sent[0]['to'] );
		$this->assertStringContainsString( 'abgeschlossen', $sent[0]['subject'] );
		$this->assertStringContainsString( '<html lang="de-DE">', $sent[0]['body'] );

		self::php( 'return wc_get_order( $input["order"] )->delete( true );', array( 'order' => $order_id ) );
	}

	/**
	 * The mails written to files, by file name: recipient, decoded subject, body.
	 *
	 * @param string $directory Mail directory.
	 * @return array<string, array{to: string, subject: string, body: string}>
	 */
	private static function mails( string $directory ): array {
		$mails = array();
		foreach ( (array) glob( $directory . '/*.eml' ) as $file ) {
			$raw                 = str_replace( "\r\n", "\n", (string) file_get_contents( (string) $file ) );
			list( $head, $body ) = array_pad( explode( "\n\n", $raw, 2 ), 2, '' );
			$head                = (string) preg_replace( "/\n[ \t]+/", ' ', $head ); // Unfolds long headers.
			preg_match( '/^To: (.*)$/mi', $head, $to );
			preg_match( '/^Subject: (.*)$/mi', $head, $subject );
			$mails[ basename( (string) $file ) ] = array(
				'to'      => trim( $to[1] ?? '' ),
				'subject' => (string) iconv_mime_decode( trim( $subject[1] ?? '' ), ICONV_MIME_DECODE_CONTINUE_ON_ERROR, 'UTF-8' ),
				'body'    => $body,
			);
		}
		return $mails;
	}
}
