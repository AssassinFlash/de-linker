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

	/**
	 * While the switch is on, a business notification and the owner copy the
	 * legacy plugin queues for it both leave for the tester address alone, and
	 * the outbox queue of each keeps the recipient the caller named.
	 */
	public function test_the_chain_sends_to_the_tester_and_queues_the_real_route(): void {
		$switch = new TestMode();
		$switch->enable( 'tester@example.test' );
		$this->later(
			static function () use ( $switch ): void {
				$switch->disable();
			}
		);

		$tag     = 'chain-' . self::tag();
		$subject = 'Linker VAT check needs review: ' . $tag;
		// Fill the minute quota so this call is stored instead of sent at once.
		// A call that goes out immediately never becomes a queue row, and the
		// assertion below is about that row.
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$this->later(
			static function (): void {
				delete_option( Throttle::OPTION );
			}
		);
		$this->assertTrue( wp_mail( array( 'sales@de-linker.com' ), $subject, 'A Linker partner VAT check needs review. Bcc: archive@example.test', array( 'Bcc: archive@example.test' ) ) );

		$queued = $this->queued( $tag );
		$this->assertCount( 1, $queued, 'The outbox stored the call before sending it.' );
		$this->assertSame( array( 'sales@de-linker.com' ), $queued[0]['to'], 'The queue keeps the recipient the caller named, not the tester address.' );
		$this->assertContains( 'Bcc: archive@example.test', $queued[0]['headers'], 'The queue keeps the blind copy the caller named.' );

		delete_option( Throttle::OPTION );
		$this->assertTrue( wp_mail( array( 'sales@de-linker.com' ), $subject, 'A Linker partner VAT check needs review.' ) );
		$sent = $this->files_naming( $tag );
		$this->assertNotSame( array(), $sent, 'The business notification was written.' );
		foreach ( $sent as $file ) {
			$this->assertSame( 'tester@example.test', $this->header( $file, 'To' ) );
			$this->assertNull( $this->header( $file, 'Cc' ) );
			$this->assertNull( $this->header( $file, 'Bcc' ) );
		}

		if ( ! function_exists( 'tv_b2b_business_mail_copy_job' ) ) {
			return;
		}
		$payload = $this->take_copy_payload( $tag );
		$this->assertNotNull( $payload, 'The legacy plugin queued an owner copy because the business inbox was a recipient.' );
		$this->assertNotSame( array(), $payload['copies'] );
		foreach ( $payload['copies'] as $address ) {
			$this->assertNotSame( 'tester@example.test', $address, 'The copy queue names the owner inbox, not the tester address.' );
		}
		// Hold the quota so each owner copy is stored before it is sent. The
		// stored row is the routing data; releasing the quota then sends that
		// same row, once.
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		tv_b2b_business_mail_copy_job( $payload );
		$routes  = array();
		$job_ids = array();
		foreach ( $this->queued( $tag ) as $message ) {
			$this->assertNotContains( 'tester@example.test', $message['to'], 'The queue is the routing data, not the rewritten send.' );
			$routes  = array_merge( $routes, $message['to'] );
			$job_ids = array_merge( $job_ids, $message['ids'] );
		}
		foreach ( $payload['copies'] as $address ) {
			$this->assertContains( $address, $routes, 'The owner copy is in the outbox queue under the address the legacy plugin named.' );
		}
		delete_option( Throttle::OPTION );
		$before_release = $this->files_naming( $tag );
		$outbox         = new \Linker\Commerce\Mail\Outbox( new \Linker\Commerce\Mail\JobStore(), new Throttle() );
		foreach ( $job_ids as $job_id ) {
			$outbox->retry( $job_id );
		}
		$copy_files = array_values( array_diff( $this->files_naming( $tag ), $before_release ) );
		$this->assertGreaterThanOrEqual( count( $payload['copies'] ), count( $copy_files ), 'Each owner copy was written.' );
		foreach ( $copy_files as $file ) {
			$this->assertSame( 'tester@example.test', $this->header( $file, 'To' ), 'A released copy leaves for the tester address, not the owner inbox the queue names.' );
			$this->assertNull( $this->header( $file, 'Cc' ) );
			$this->assertNull( $this->header( $file, 'Bcc' ) );
			$raw = file_get_contents( $file );
			$this->assertIsString( $raw );
			foreach ( $payload['copies'] as $address ) {
				$this->assertStringNotContainsString( $address, $this->header( $file, 'To' ) . $raw, 'The owner address is not a recipient of the file that left.' );
			}
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
	 * @return list<array{to: list<string>, headers: list<string>, ids: list<int>}>
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
				'ids'     => array( (int) $post->ID ),
			);
		}
		return $found;
	}

	/**
	 * The legacy plugin's copy payload for this subject, taken off the scheduler
	 * so a later run does not send it again.
	 *
	 * @param string $tag Tag.
	 * @return array{copies: list<string>, subject: string, message: string, content_type: string, attachments: list<string>}|null
	 */
	private function take_copy_payload( string $tag ): ?array {
		if ( ! function_exists( 'as_get_scheduled_actions' ) ) {
			return null;
		}
		$actions = as_get_scheduled_actions(
			array(
				'hook'     => 'tv_b2b_business_mail_copy_job',
				'status'   => 'pending',
				'per_page' => 20,
				'group'    => 'tv-b2b',
			)
		);
		foreach ( $actions as $id => $action ) {
			$args    = $action->get_args();
			$payload = $args[0] ?? array();
			if ( ! is_array( $payload ) || ! str_contains( (string) ( $payload['subject'] ?? '' ), $tag ) ) {
				continue;
			}
			if ( class_exists( '\ActionScheduler' ) ) {
				\ActionScheduler::store()->cancel_action( (int) $id );
			}
			return array(
				'copies'       => array_values( array_map( 'strval', (array) ( $payload['copies'] ?? array() ) ) ),
				'subject'      => (string) ( $payload['subject'] ?? '' ),
				'message'      => (string) ( $payload['message'] ?? '' ),
				'content_type' => (string) ( $payload['content_type'] ?? '' ),
				'attachments'  => array_values( array_map( 'strval', (array) ( $payload['attachments'] ?? array() ) ) ),
			);
		}
		return null;
	}
}
