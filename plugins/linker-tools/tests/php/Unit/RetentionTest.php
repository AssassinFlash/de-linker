<?php
/**
 * Tests for the conversation retention rule and its scan.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Retention;
use WP_Mock;
use WP_Mock\Tools\TestCase;
use WP_Post;
use WP_User;

/**
 * Tests for Retention, with conversations in memory (WP_Mock).
 *
 * @covers \Linker\Tools\Genie\Retention
 */
final class RetentionTest extends TestCase {

	private const FILE = '/srv/www/wp-content/plugins/linker-tools/linker-tools.php';

	/**
	 * Posts by ID, as get_post() returns them.
	 *
	 * @var array<int, WP_Post>
	 */
	private array $posts = array();

	/**
	 * The users' email addresses by user ID.
	 *
	 * @var array<int, string>
	 */
	private array $users = array(
		7 => 'owner@example.test',
	);

	/**
	 * The delete jobs scheduled: conversation IDs.
	 *
	 * @var list<int>
	 */
	private array $scheduled = array();

	/**
	 * The conversation IDs whose delete job ran.
	 *
	 * @var list<int>
	 */
	private array $deleted = array();

	/**
	 * The scan's batches, by page: the conversation IDs each get_posts() call answers.
	 *
	 * @var list<list<int>>
	 */
	private array $batches = array();

	/**
	 * The paged values of the scan's get_posts() calls, in order.
	 *
	 * @var list<int>
	 */
	private array $paged = array();

	/**
	 * A conversation timestamp past the retention days (UTC).
	 */
	private static function expired(): string {
		return gmdate( 'Y-m-d H:i:s', time() - ( Retention::RETENTION_DAYS + 1 ) * DAY_IN_SECONDS );
	}

	/**
	 * A conversation timestamp inside the retention days (UTC).
	 */
	private static function fresh(): string {
		return gmdate( 'Y-m-d H:i:s', time() - DAY_IN_SECONDS );
	}

	/**
	 * An in-memory WordPress for posts, users, the scheduler and the delete jobs.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction(
			'get_post',
			array(
				'return' => fn ( int $id ): ?WP_Post => $this->posts[ $id ] ?? null,
			)
		);
		WP_Mock::userFunction(
			'get_userdata',
			array(
				'return' => function ( int $id ): ?WP_User {
					if ( ! array_key_exists( $id, $this->users ) ) {
						return null;
					}
					$user             = new WP_User();
					$user->ID         = $id;
					$user->user_email = $this->users[ $id ];
					return $user;
				},
			)
		);
		WP_Mock::userFunction(
			'wp_delete_post',
			array(
				'return' => function ( int $id, bool $force ): bool {
					$this->assertSame( true, $force, 'A conversation goes at once, not into the trash.' );
					$this->deleted[] = $id;
					unset( $this->posts[ $id ] );
					return true;
				},
			)
		);
		WP_Mock::userFunction(
			'as_schedule_single_action',
			array(
				'return' => function ( int $time, string $hook, array $args, string $group ): int {
					$this->assertSame( Retention::DELETE_HOOK, $hook );
					$this->assertSame( Retention::GROUP, $group );
					$this->assertCount( 1, $args );
					$this->scheduled[] = (int) $args[0];
					return count( $this->scheduled );
				},
			)
		);
	}

	/**
	 * A conversation post as get_post() returns it.
	 *
	 * @param string $date_gmt Creation time (UTC).
	 * @param int    $author   Post author.
	 * @param string $type     Post type.
	 * @param string $status   Post status.
	 */
	private function conversation( string $date_gmt, int $author = 0, string $type = Conversations::POST_TYPE, string $status = 'private' ): int {
		$id                 = 100 + count( $this->posts );
		$this->posts[ $id ] = new WP_Post(
			(object) array(
				'ID'            => $id,
				'post_type'     => $type,
				'post_status'   => $status,
				'post_author'   => (string) $author,
				'post_date_gmt' => $date_gmt,
			)
		);
		return $id;
	}

	/**
	 * The scan schedules one delete job per conversation the rule gives up, and
	 * none for the ones a user account with an email address holds.
	 */
	public function test_sweep_schedules_jobs_for_expired_guest_conversations(): void {
		$expired_guest  = $this->conversation( self::expired() );
		$retained       = $this->conversation( self::expired(), 7 );
		$ownerless      = $this->conversation( self::expired(), 42 );
		$emailless      = $this->conversation( self::expired(), 8 );
		$this->users[8] = '';
		$this->batches  = array( array( $expired_guest, $retained, $ownerless, $emailless ) );
		$this->mock_scan_batch();

		( new Retention( self::FILE ) )->sweep();
		$this->assertSame( array( $expired_guest, $ownerless, $emailless ), $this->scheduled );
		$this->assertCount( 1, $this->paged );
	}

	/**
	 * The scan stops when a batch comes back short: the window is drained.
	 */
	public function test_sweep_stops_at_an_empty_batch(): void {
		$this->batches = array( array(), array() );
		$this->mock_scan_batch();

		( new Retention( self::FILE ) )->sweep();
		$this->assertSame( array(), $this->scheduled );
		$this->assertCount( 1, $this->paged, 'No batch is asked beyond the empty one.' );
	}

	/**
	 * The scan's batching is the guard against a head of retained threads:
	 * pages are walked in order until the batch limit, however many retained
	 * threads sit in the window.
	 */
	public function test_sweep_walks_the_batches_it_declares(): void {
		for ( $batch = 0; $batch < Retention::MAX_BATCHES; ++$batch ) {
			// Every batch full of retained threads: nothing to schedule, the walk goes on.
			$this->batches[] = array_fill( 0, Retention::SCAN_BATCH, $this->conversation( self::expired(), 7 ) );
		}
		$this->mock_scan_batch();

		( new Retention( self::FILE ) )->sweep();
		$this->assertSame( array(), $this->scheduled );
		$this->assertSame( range( 1, Retention::MAX_BATCHES ), $this->paged );
	}

	/**
	 * The delete job removes an expired guest conversation through
	 * wp_delete_post(), and re-checks the rule first.
	 */
	public function test_delete_removes_an_expired_guest_conversation(): void {
		$id = $this->conversation( self::expired() );

		( new Retention( self::FILE ) )->delete( $id );

		$this->assertSame( array( $id ), $this->deleted );
	}

	/**
	 * The delete job keeps a conversation a registered user owns — even one
	 * that was a guest thread when the scan scheduled the job.
	 */
	public function test_delete_keeps_a_claimed_conversation(): void {
		$id = $this->conversation( self::expired(), 7 );

		( new Retention( self::FILE ) )->delete( $id );

		$this->assertSame( array(), $this->deleted );
	}

	/**
	 * The delete job keeps a conversation inside its retention days, whatever
	 * its owner.
	 */
	public function test_delete_keeps_a_fresh_conversation(): void {
		$id = $this->conversation( self::fresh() );

		( new Retention( self::FILE ) )->delete( $id );

		$this->assertSame( array(), $this->deleted );
	}

	/**
	 * A post that is not a private conversation — a deleted one, a different
	 * type, another status — is not the rule's business.
	 */
	public function test_delete_ignores_what_is_not_a_conversation(): void {
		$gone    = 404;
		$other   = $this->conversation( self::expired(), 0, 'post' );
		$trashed = $this->conversation( self::expired(), 0, Conversations::POST_TYPE, 'trash' );

		( new Retention( self::FILE ) )->delete( $gone );
		( new Retention( self::FILE ) )->delete( $other );
		( new Retention( self::FILE ) )->delete( $trashed );

		$this->assertSame( array(), $this->deleted );
	}

	/**
	 * Without a daily event, one is scheduled.
	 */
	public function test_schedules_the_daily_sweep_once(): void {
		WP_Mock::userFunction(
			'wp_schedule_event',
			array(
				'times'  => 1,
				'args'   => array( WP_Mock\Functions::type( 'int' ), 'daily', Retention::HOOK ),
				'return' => true,
			)
		);
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => false ) );

		( new Retention( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * An event already being scheduled is left alone.
	 */
	public function test_leaves_the_scheduled_event_alone(): void {
		WP_Mock::userFunction( 'wp_schedule_event', array( 'times' => 0 ) );
		WP_Mock::userFunction( 'wp_next_scheduled', array( 'return' => 12345 ) );

		( new Retention( self::FILE ) )->schedule();
		$this->assertConditionsMet();
	}

	/**
	 * Deactivation removes the daily event and the delete jobs still pending.
	 */
	public function test_deactivate_clears_the_events(): void {
		WP_Mock::userFunction(
			'wp_clear_scheduled_hook',
			array(
				'times' => 1,
				'args'  => array( Retention::HOOK ),
			)
		);
		WP_Mock::userFunction(
			'as_unschedule_all_actions',
			array(
				'times' => 1,
				'args'  => array( Retention::DELETE_HOOK, null, Retention::GROUP ),
			)
		);

		( new Retention( self::FILE ) )->deactivate();
		$this->assertConditionsMet();
	}

	/**
	 * Mocks the scan's get_posts() to answer one batch per recorded page.
	 */
	private function mock_scan_batch(): void {
		$posts   = $this->posts;
		$batches = $this->batches;
		$self    = $this;
		WP_Mock::userFunction(
			'get_posts',
			array(
				'return' => static function ( array $args ) use ( $posts, $batches, $self ): array {
					$self->assertSame( Conversations::POST_TYPE, $args['post_type'] );
					$self->assertSame( 'private', $args['post_status'] );
					$self->assertSame( 'ids', $args['fields'] );
					$self->assertSame( Retention::SCAN_BATCH, $args['posts_per_page'] );
					$self->assertSame( 'date', $args['orderby'] );
					$self->assertSame( 'ASC', $args['order'] );
					$self->assertSame( 'post_date_gmt', $args['date_query'][0]['column'] );
					$cutoff = strtotime( $args['date_query'][0]['before'] . ' UTC' );
					$self->assertIsInt( $cutoff );
					$self->assertEqualsWithDelta( time() - Retention::RETENTION_DAYS * DAY_IN_SECONDS, $cutoff, 5 );
					$self->paged[] = (int) $args['paged'];
					$batch         = $batches[ (int) $args['paged'] - 1 ] ?? false;
					return false === $batch ? array() : array_values( array_intersect( $batch, array_keys( $posts ) ) );
				},
			)
		);
	}
}
