<?php
/**
 * The test-mode switch on WordPress's own wp_mail() filter chain.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;

/**
 * WordPress applies the wp_mail filter and then pre_wp_mail
 * (wp-includes/pluggable.php). The outbox records the queue from the arguments
 * pre_wp_mail is handed and rewrites only the copy it sends. A unit test that
 * calls either filter by itself cannot see that order, so this one calls
 * wp_mail() and reads both ends: the file the local mailer wrote, and the
 * message the outbox stored.
 *
 * @coversNothing
 */
final class MailChainTest extends IntegrationTestCase {

	/** A VAT notification originates in the actual trusted native Woo producer.
	 *
	 * @param mixed ...$arguments Original wp_mail arguments.
	 */
	private function transaction_mail( mixed ...$arguments ): bool {
		$email = WC()->mailer()->get_emails()[ \Linker\Commerce\Registration\Emails\VatReviewEmail::class ];
		$send  = ( new \Linker\Commerce\Mail\Producer() )->woocommerce( static fn () => wp_mail( ...$arguments ), $email );
		return $send();
	}

	/**
	 * While the switch is on, a business notification leaves for the tester
	 * address alone, and the outbox queue keeps the recipients the caller
	 * named.
	 */
	public function test_the_chain_sends_to_the_tester_and_queues_the_real_route(): void {
		$switch = new TestMode();
		$switch->enable( 'tester@example.test' );
		$this->later(
			function () use ( $switch ): void {
				$switch->disable();
			}
		);

		$tag     = 'chain-' . self::tag();
		$subject = 'Linker VAT check needs review: ' . $tag;
		// Fill the minute quota so this call is stored instead of sent at once.
		// A call that goes out immediately never becomes a queue row, and the
		// assertion below is about that row.
		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$this->later(
			static function (): void {
				delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
				delete_option( Throttle::OPTION );
			}
		);
		$this->assertTrue( $this->transaction_mail( array( 'sales@de-linker.com' ), $subject, 'A Linker partner VAT check needs review. Bcc: archive@example.test', array( 'Bcc: archive@example.test' ) ) );

		$queued = $this->queued( $tag );
		$this->assertCount( 1, $queued, 'The outbox stored the call before sending it.' );
		$this->assertSame( array( 'sales@de-linker.com' ), $queued[0]['to'], 'The queue keeps the recipient the caller named, not the tester address.' );
		$this->assertContains( 'Bcc: archive@example.test', $queued[0]['headers'], 'The queue keeps the blind copy the caller named.' );

		delete_option( \Linker\Commerce\Mail\OptionBudgetLedger::OPTION );
		delete_option( Throttle::OPTION );
		$this->assertTrue( $this->transaction_mail( array( 'sales@de-linker.com' ), $subject, 'A Linker partner VAT check needs review.' ) );
		$sent = $this->files_naming( $tag );
		$this->assertNotSame( array(), $sent, 'The business notification was written.' );
		foreach ( $sent as $file ) {
			$this->assertSame( 'tester@example.test', $this->header( $file, 'To' ) );
			$this->assertNull( $this->header( $file, 'Cc' ) );
			$this->assertNull( $this->header( $file, 'Bcc' ) );
		}
	}

	/**
	 * Mail files whose body names the tag.
	 *
	 * @param string $tag     Tag.
	 * @param string $subject Subject the file must also name, when the tag alone is shared.
	 * @return list<string>
	 */
	private function files_naming( string $tag, string $subject = '' ): array {
		$directory = defined( 'LINKER_LOCAL_MAIL_DIR' ) ? LINKER_LOCAL_MAIL_DIR : '';
		$this->assertNotSame( '', $directory, 'The local instance names its mail directory.' );
		$found = array();
		$files = glob( $directory . '/*.eml' );
		foreach ( is_array( $files ) ? $files : array() as $file ) {
			$body = file_get_contents( $file );
			if ( is_string( $body ) && str_contains( $body, $tag ) && ( '' === $subject || str_contains( $body, $subject ) ) ) {
				$found[] = $file;
			}
		}
		return $found;
	}

	/**
	 * One header of a captured message, or null when it has none.
	 *
	 * @param string $file   Path.
	 * @param string $header Header name.
	 */
	private function header( string $file, string $header ): ?string {
		$raw = file_get_contents( $file );
		if ( ! is_string( $raw ) || 1 !== preg_match( '/^' . preg_quote( $header, '/' ) . ': (.+)$/mi', $raw, $match ) ) {
			return null;
		}
		return trim( $match[1] );
	}

	/**
	 * Outbox messages whose subject names the tag.
	 *
	 * @param string $tag Tag.
	 * @return list<array{to: list<string>, headers: list<string>}>
	 */
	private function queued( string $tag ): array {
		$posts = get_posts(
			array(
				'post_type'      => JobStore::POST_TYPE,
				'post_status'    => 'any',
				'posts_per_page' => 20,
				's'              => $tag,
			)
		);
		$found = array();
		foreach ( $posts as $post ) {
			$data = json_decode( (string) get_post_meta( $post->ID, '_linker_mail_message', true ), true );
			if ( ! is_array( $data ) || ! str_contains( (string) ( $data['subject'] ?? '' ), $tag ) ) {
				continue;
			}
			$found[] = array(
				'to'      => array_values( array_map( 'strval', (array) ( $data['to'] ?? array() ) ) ),
				'headers' => array_values( array_map( 'strval', (array) ( $data['headers'] ?? array() ) ) ),
			);
		}
		return $found;
	}
}
