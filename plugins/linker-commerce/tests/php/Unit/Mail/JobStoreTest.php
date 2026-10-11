<?php
/**
 * Tests for the mail queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Mail;

use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Tests\TestCase;
use WP_Error;
use WP_Mock;

/**
 * Tests for JobStore.
 *
 * @covers \Linker\Commerce\Mail\JobStore
 */
final class JobStoreTest extends TestCase {

	/**
	 * Post meta of job 7.
	 *
	 * @var array<string, mixed>
	 */
	private array $meta = array();

	/**
	 * Post meta per job id, for tests with more than one job.
	 *
	 * @var array<int, array<string, mixed>>
	 */
	private array $meta_by_id = array();

	/**
	 * Job 7 is a queued email; post meta lives in $meta.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'wp_slash', array( 'return' => static fn ( $value ) => $value ) );
		WP_Mock::userFunction( 'wp_strip_all_tags', array( 'return' => static fn ( string $text ): string => strip_tags( $text ) ) );
		WP_Mock::userFunction(
			'update_post_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->meta[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'get_post_meta', array( 'return' => fn ( int $id, string $key ) => $this->meta_by_id[ $id ][ $key ] ?? $this->meta[ $key ] ?? '' ) );
		WP_Mock::userFunction( 'get_post_type', array( 'return' => static fn ( int $id ) => 7 === $id ? JobStore::POST_TYPE : false ) );
	}

	/**
	 * A message is stored as a private post and comes back with its attempts.
	 */
	public function test_create_and_load(): void {
		WP_Mock::userFunction(
			'wp_insert_post',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => JobStore::POST_TYPE,
						'post_status' => 'private',
						'post_title'  => 'New inquiry #20',
					),
					true,
				),
				'return' => 7,
			)
		);
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => false ) );
		$message = new Message( array( 'sales@de-linker.com' ), 'New <b>inquiry</b> #20', '<p>Body</p>', array( 'Bcc: a@example.test' ), array() );
		$jobs    = new JobStore();

		$this->assertSame( 7, $jobs->create( $message ) );
		$job = $jobs->load( 7 );
		$this->assertNotNull( $job );
		$this->assertEquals( $message, $job['message'] );
		$this->assertSame( 0, $job['attempts'] );
		$this->assertNull( $jobs->load( 8 ) );
	}

	/**
	 * A post that cannot be written gives 0.
	 */
	public function test_create_fails(): void {
		WP_Mock::userFunction( 'wp_insert_post', array( 'return' => new WP_Error( 'db', 'No.' ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => true ) );

		$this->assertSame( 0, ( new JobStore() )->create( new Message( array(), 'S', 'B', array(), array() ) ) );
	}

	/**
	 * Failures are counted; a message that failed its last attempt becomes a draft; a sent one is deleted.
	 */
	public function test_failure_and_deletion(): void {
		WP_Mock::userFunction(
			'wp_update_post',
			array(
				'times' => 1,
				'args'  => array(
					array(
						'ID'          => 7,
						'post_status' => JobStore::FAILED_STATUS,
					),
				),
			)
		);
		WP_Mock::userFunction(
			'wp_delete_post',
			array(
				'times' => 1,
				'args'  => array( 7, true ),
			)
		);
		$jobs = new JobStore();

		$jobs->record_failure( 7, 2, 'Could not instantiate mail function.' );
		$this->assertSame( 2, $this->meta['_linker_mail_attempts'] );
		$jobs->fail( 7, 8, 'Still failing.' );
		$this->assertSame( 'Still failing.', $this->meta['_linker_mail_error'] );
		$jobs->delete( 7 );

		$this->assertConditionsMet();
	}

	/**
	 * The post type is private and has no screens.
	 */
	public function test_post_type(): void {
		WP_Mock::passthruFunction( '__' );
		WP_Mock::userFunction(
			'register_post_type',
			array(
				'times' => 1,
				'args'  => array(
					JobStore::POST_TYPE,
					\Mockery::on( static fn ( array $args ): bool => false === $args['public'] && false === $args['show_ui'] ),
				),
			)
		);

		( new JobStore() )->register_post_type();

		$this->assertConditionsMet();
	}

	/**
	 * The failed() reader brings back the failed posts: recipients, subject and
	 * last error,
	 * oldest first; a job whose stored message is unreadable stays out.
	 */
	public function test_failed_reads_the_queue(): void {
		$first            = new \stdClass();
		$first->ID        = 7;
		$second           = new \stdClass();
		$second->ID       = 9;
		$unreadable       = new \stdClass();
		$unreadable->ID   = 11;
		$this->meta_by_id = array(
			7  => array(
				'_linker_mail_message' => json_encode(
					array(
						'to'      => array( 'sales@de-linker.com', 'copy@example.test' ),
						'subject' => 'New inquiry #20 from Solarbau GmbH',
						'body'    => '<p>…</p>',
						'headers' => array(),
					)
				),
				'_linker_mail_error'   => 'Could not instantiate mail function.',
			),
			9  => array(
				'_linker_mail_message' => json_encode(
					array(
						'to'      => array( 'maria@example.test' ),
						'subject' => 'Your Proforma invoice is ready',
						'body'    => '<p>…</p>',
						'headers' => array(),
					)
				),
				'_linker_mail_error'   => 'SMTP Error: data not accepted.',
			),
			11 => array(
				'_linker_mail_message' => 'not json',
				'_linker_mail_error'   => 'nobody reads this',
			),
		);
		WP_Mock::userFunction(
			'get_posts',
			array(
				'times'  => 1,
				'args'   => array(
					array(
						'post_type'   => JobStore::POST_TYPE,
						'post_status' => JobStore::FAILED_STATUS,
						'numberposts' => -1,
						'orderby'     => 'date',
						'order'       => 'ASC',
					),
				),
				'return' => array( $first, $second, $unreadable ),
			)
		);

		$failed = ( new JobStore() )->failed();

		$this->assertSame(
			array(
				array(
					'id'      => 7,
					'to'      => array( 'sales@de-linker.com', 'copy@example.test' ),
					'subject' => 'New inquiry #20 from Solarbau GmbH',
					'error'   => 'Could not instantiate mail function.',
				),
				array(
					'id'      => 9,
					'to'      => array( 'maria@example.test' ),
					'subject' => 'Your Proforma invoice is ready',
					'error'   => 'SMTP Error: data not accepted.',
				),
			),
			$failed
		);
	}

	/**
	 * An empty queue reads as no failed messages.
	 */
	public function test_failed_of_an_empty_queue(): void {
		WP_Mock::userFunction( 'get_posts', array( 'return' => array() ) );

		$this->assertSame( array(), ( new JobStore() )->failed() );
	}
}
