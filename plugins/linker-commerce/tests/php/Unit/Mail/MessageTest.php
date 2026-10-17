<?php
/**
 * Tests for a message as wp_mail() sends it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\Message;
use Linker\Commerce\Tests\TestCase;
use WP_Mock;

/**
 * Tests for Message.
 *
 * @covers \Linker\Commerce\Mail\Message
 */
final class MessageTest extends TestCase {

	/**
	 * All internal producers use the same helper for native wp_mail header forms.
	 */
	public function test_marks_string_and_array_headers_internal(): void {
		$this->assertSame( array( 'Bcc: copy@example.test', 'X-Linker-Internal: yes' ), Message::mark_internal( array( 'Bcc: copy@example.test' ) ) );
		$this->assertSame( "From: Linker <team@example.test>\r\nX-Linker-Internal: yes\r\n", Message::mark_internal( "From: Linker <team@example.test>\r\n" ) );
	}

	/**
	 * The site is https://www.de-linker.com.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'network_home_url', array( 'return' => 'https://www.de-linker.com' ) );
		WP_Mock::userFunction( 'wp_parse_url', array( 'return' => static fn ( string $url, int $part ) => parse_url( $url, $part ) ) );
		WP_Mock::userFunction( 'get_bloginfo', array( 'return' => 'UTF-8' ) );
	}

	/**
	 * WooCommerce's sender and content type, which exist only while WooCommerce sends, are kept as headers.
	 */
	public function test_settles_sender_and_content_type(): void {
		$this->filter_returns( 'wp_mail_from', 'sales@de-linker.com', array( 'wordpress@de-linker.com' ) );
		$this->filter_returns( 'wp_mail_from_name', 'Linker', array( 'WordPress' ) );
		$this->filter_returns( 'wp_mail_content_type', 'text/html', array( 'text/html' ) );
		$this->filter_returns( 'wp_mail_charset', 'UTF-8', array( 'UTF-8' ) );

		$message = Message::from_wp_mail(
			array(
				'to'          => 'sales@de-linker.com',
				'subject'     => 'New inquiry #20',
				'message'     => '<p>Hi</p>',
				'headers'     => "Content-Type: text/html\r\nReply-to: Maria <maria@example.test>\r\nBcc: a@example.test, b@example.test\r\n",
				'attachments' => array(),
			)
		);

		$this->assertSame( array( 'sales@de-linker.com' ), $message->to );
		$this->assertSame(
			array(
				'Reply-to: Maria <maria@example.test>',
				'Bcc: a@example.test, b@example.test',
				'From: Linker <sales@de-linker.com>',
				'Content-Type: text/html; charset=UTF-8',
			),
			$message->headers
		);
	}

	/**
	 * A sender given in the headers, with its name, is the starting value of the filters.
	 */
	public function test_sender_from_headers(): void {
		$this->filter_returns( 'wp_mail_from', 'team@example.test', array( 'team@example.test' ) );
		$this->filter_returns( 'wp_mail_from_name', 'Team', array( 'Team' ) );
		$this->filter_returns( 'wp_mail_content_type', 'text/plain', array( 'text/plain' ) );
		$this->filter_returns( 'wp_mail_charset', 'iso-8859-1', array( 'iso-8859-1' ) );

		$message = Message::from_wp_mail(
			array(
				'to'      => array( 'a@example.test', ' ', 'b@example.test' ),
				'subject' => 'S',
				'message' => 'Body',
				'headers' => array( 'From: "Team" <team@example.test>', 'Content-Type: text/plain; charset=iso-8859-1', 'broken' ),
			)
		);

		$this->assertSame( array( 'a@example.test', 'b@example.test' ), $message->to );
		$this->assertSame( array( 'From: Team <team@example.test>', 'Content-Type: text/plain; charset=iso-8859-1' ), $message->headers );
	}

	/**
	 * A queued message comes back as it was stored.
	 */
	public function test_round_trip(): void {
		$message = new Message( array( 'a@example.test' ), 'S', 'B', array( 'From: X <x@example.test>' ), array( '/tmp/file.pdf' ) );

		$this->assertEquals( $message, Message::from_array( $message->to_array() ) );
		$this->assertEquals( new Message( array(), '', '', array(), array() ), Message::from_array( array( 'subject' => 3 ) ) );
	}

	/**
	 * Only an explicit internal marker selects SMTP, including after queue storage.
	 */
	public function test_internal_marker_survives_the_queue(): void {
		$internal = new Message( array( 'tester@example.test' ), 'S', 'B', array( 'X-Linker-Internal: yes' ), array() );
		$this->assertTrue( Message::from_array( $internal->to_array() )->is_internal() );
		$customer = new Message( array( 'sales@sunriverinverter.com' ), 'S', 'B', array( 'From: Linker <sales@sunriverinverter.com>' ), array() );
		$this->assertFalse( $customer->is_internal(), 'Neither recipient nor From implies internal mail.' );
	}
}
