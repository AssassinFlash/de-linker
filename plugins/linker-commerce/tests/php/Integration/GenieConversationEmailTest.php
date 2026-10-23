<?php
/**
 * Integration test: Genie's two customer emails, read from the Outbox queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Genie\Module;
use Linker\Commerce\Settings\Options;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Tests\Fixtures\NormalMailAuthorizationFixture;
use Linker\Tools\Genie\Thread;

/**
 * The tools plugin asks on two filters; this plugin answers each with one
 * customer email (ticket #235). The routing is read from the Outbox queue
 * (AGENTS.md §5, test mail rule): the minute quota is full, so each call is
 * stored as a queue row instead of being sent, and the row is what the
 * sender named — the visitor alone, no blind copy, the site's customer
 * sender, in the page's language.
 *
 * @coversNothing
 */
final class GenieConversationEmailTest extends IntegrationTestCase {

	/** Typed local service with native consumers.
	 *
	 * @var NormalMailAuthorizationFixture
	 */
	private NormalMailAuthorizationFixture $authorization;

	/**
	 * A published product of the live snapshot: SAJ H2-10K-T3.
	 */
	private const PRODUCT = 4107;

	/**
	 * The customer sender, as live has it; the quota full, so every call
	 * becomes a queue row.
	 */
	protected function setUp(): void {
		parent::setUp();
		require_once dirname( __DIR__, 2 ) . '/fixtures/NormalMailAuthorizationFixture.php';
		$this->authorization = NormalMailAuthorizationFixture::install(
			function ( callable $remove ): void {
				$this->later( $remove );
			}
		);
		$saved               = array();
		foreach ( array( 'woocommerce_email_from_name', 'woocommerce_email_from_address' ) as $name ) {
			$saved[ $name ] = get_option( $name );
		}
		$this->later(
			static function () use ( $saved ): void {
				foreach ( $saved as $name => $value ) {
					if ( false === $value ) {
						delete_option( $name );
					} else {
						update_option( $name, $value );
					}
				}
			}
		);
		update_option( 'woocommerce_email_from_name', 'Linker' );
		update_option( 'woocommerce_email_from_address', 'sales@de-linker.com' );
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
	}

	/**
	 * One German conversation: one row to the visitor alone, from and
	 * replying to the team mailbox, German subject, every message, the
	 * product the answer showed (German name, model, German page), the AI
	 * note and the datasheet rule.
	 */
	public function test_the_conversation_goes_to_the_visitor_alone_in_their_language(): void {
		$marker = self::newest_mail_job();
		$to     = 'visitor-' . self::tag() . '@example.test';

		$conversation = wp_insert_post(
			array(
				'post_type'   => \Linker\Tools\Genie\Conversations::POST_TYPE,
				'post_status' => 'private',
				'post_title'  => 'Synthetic mail source',
			)
		);
		$this->assertGreaterThan( 0, $conversation );
		$this->later(
			static function () use ( $conversation ): void {
				wp_delete_post( $conversation, true );
			}
		);
		$stream = 'event: block' . "\n" . 'data: ' . wp_json_encode(
			array(
				'type' => 'text',
				'text' => 'Der SAJ H2-10K-T3 passt zu Ihrem Projekt.',
			)
		) . "\n\n" . 'event: block' . "\n" . 'data: ' . wp_json_encode(
			array(
				'type'        => 'cards',
				'product_ids' => array( self::PRODUCT ),
			)
		) . "\n\nevent: done\ndata: {}\n\n";
		$this->assertTrue(
			( new Thread() )->record(
				$conversation,
				array(
					array(
						'role'    => 'user',
						'content' => 'Welcher Wechselrichter passt?',
					),
				),
				$stream
			)
		);
		$messages = ( new Thread() )->transcript( $conversation );

		$sent = ( new Module( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->send(
			false,
			array(
				'to'              => $to,
				'locale'          => 'de_DE_formal',
				'conversation_id' => $conversation,
				'messages'        => $messages,
			)
		);

		$this->assertSame( array( 'status' => 'pending' ), $sent );
		$jobs = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $jobs );
		$permit = $this->authorization->conversation( $jobs[0] );
		$this->assertSame( 'normal', $permit['verdict']['decision'] );
		$this->assertSame( 'conversation_mail', $this->authorization->requests[0]['binding']['purpose'] );
		$row = $this->only_row( $marker );
		$this->assertSame( array( $to ), $row['to'] );
		$this->assertSame( 'Ihr Gespräch mit Genie', $row['subject'] );
		$this->assertContains( 'From: Linker <sales@de-linker.com>', $row['headers'] );
		$this->assertContains( 'Reply-to: Linker <sales@de-linker.com>', $row['headers'] );
		$this->assertStringNotContainsStringIgnoringCase( 'bcc:', implode( "\n", $row['headers'] ), 'Nobody else is copied.' );
		$this->assertStringContainsString( 'Welcher Wechselrichter passt?', $row['body'] );
		$this->assertStringContainsString( 'Der SAJ H2-10K-T3 passt zu Ihrem Projekt.', $row['body'] );
		$german = (int) pll_get_post( self::PRODUCT, 'de' );
		$this->assertStringContainsString( esc_html( get_the_title( $german ) ), $row['body'] );
		$this->assertStringContainsString( 'Modell H2-10K-T3', $row['body'] );
		$this->assertStringContainsString( esc_url( (string) get_permalink( $german ) ), $row['body'] );
		$this->assertStringContainsString( 'Genie ist ein KI-System', $row['body'] );
		$this->assertStringContainsString( 'Maßgeblich sind die Datenblätter', $row['body'] );
	}

	/**
	 * The address confirmation: fixed words and the link, nothing of the
	 * conversation, from the team mailbox.
	 */
	public function test_the_confirmation_carries_the_link_and_nothing_else(): void {
		$marker = self::newest_mail_job();
		$to     = 'visitor-' . self::tag() . '@example.test';
		$link   = add_query_arg(
			array(
				'action' => 'linker_tools_genie_email',
				'token'  => '1.' . str_repeat( 'a', 64 ),
			),
			admin_url( 'admin-post.php' )
		);

		$sent = ( new Module( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->confirm(
			false,
			array(
				'to'     => $to,
				'locale' => 'en_US',
				'link'   => $link,
				'hours'  => 24,
			)
		);

		$this->assertTrue( $sent );
		$row = $this->only_row( $marker );
		$this->assertSame( array( $to ), $row['to'] );
		$this->assertSame( 'Conversation with Genie requested for this email address', $row['subject'] );
		$this->assertContains( 'From: Linker <sales@de-linker.com>', $row['headers'] );
		$this->assertStringContainsString( 'admin-post.php?action=linker_tools_genie_email&amp;token=1.' . str_repeat( 'a', 64 ), $row['body'] );
		$this->assertStringContainsString( 'expires after 24 hours', $row['body'] );
	}

	/**
	 * The German confirmation counts its hours in German, plural and all.
	 */
	public function test_the_german_confirmation_says_24_stunden(): void {
		$marker = self::newest_mail_job();
		$this->assertTrue(
			( new Module( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() ) )->confirm(
				false,
				array(
					'to'     => 'visitor-' . self::tag() . '@example.test',
					'locale' => 'de_DE_formal',
					'link'   => admin_url( 'admin-post.php' ) . '?action=linker_tools_genie_email&token=1.' . str_repeat( 'b', 64 ),
					'hours'  => 24,
				)
			)
		);
		$row = $this->only_row( $marker );
		$this->assertSame( 'Gespräch mit Genie für diese E-Mail-Adresse angefordert', $row['subject'] );
		$this->assertStringContainsString( 'läuft nach 24 Stunden ab', $row['body'] );
	}

	/**
	 * What is not a conversation or a confirmation is not sent: no address,
	 * no message, a role nobody sends, a link that is not this site's.
	 */
	public function test_an_incomplete_request_sends_nothing(): void {
		$marker  = self::newest_mail_job();
		$module  = new Module( WP_PLUGIN_DIR . '/linker-commerce/linker-commerce.php', new Options() );
		$refused = array(
			array(
				'to'       => 'not an address',
				'messages' => array(
					array(
						'role'    => 'user',
						'content' => 'Hi',
					),
				),
			),
			array(
				'to'       => 'visitor@example.test',
				'messages' => array(),
			),
			array(
				'to'       => 'visitor@example.test',
				'messages' => array(
					array(
						'role'    => 'system',
						'content' => 'Hi',
					),
				),
			),
		);
		foreach ( $refused as $request ) {
			$this->assertFalse( $module->send( false, $request ) );
		}
		$this->assertFalse(
			$module->confirm(
				false,
				array(
					'to'   => 'visitor@example.test',
					'link' => 'https://example.test/x',
				)
			)
		);
		$this->assertSame( array(), self::mail_jobs_after( $marker ) );
	}

	/**
	 * The one queue row written after $marker.
	 *
	 * @param int $marker The newest row id before the test.
	 * @return array{to: list<string>, subject: string, headers: list<string>, body: string}
	 */
	private function only_row( int $marker ): array {
		$rows = self::mail_jobs_after( $marker );
		$this->assertCount( 1, $rows, 'One email, one row.' );
		$data = json_decode( (string) get_post_meta( $rows[0], '_linker_mail_message', true ), true );
		$this->assertIsArray( $data );
		return array(
			'to'      => array_values( array_map( 'strval', (array) $data['to'] ) ),
			'subject' => (string) $data['subject'],
			'headers' => array_values( array_map( 'strval', (array) $data['headers'] ) ),
			'body'    => (string) $data['body'],
		);
	}
}
