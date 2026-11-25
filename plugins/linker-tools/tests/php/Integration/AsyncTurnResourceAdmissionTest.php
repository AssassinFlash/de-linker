<?php
/**
 * Private asynchronous Genie turns through real Woo authorization and WordPress storage.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Protection\Identity;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\PublicationGuard;
use Linker\Tools\Protection\Replies;
use Linker\Tools\Protection\Resources;
use PHPUnit\Framework\TestCase;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Worker and WordPress receipt integration.
 *
 * @coversNothing
 */
final class AsyncTurnResourceAdmissionTest extends TestCase {
	/** The same native receipt follows a guest from preparation through checked output or a recoverable refusal.
	 *
	 * @dataProvider async_outcomes
	 * @param string $outcome Terminal scenario or worker error code.
	 * @param int    $worker_status HTTP status recorded by a failed job.
	 */
	public function test_async_turn_uses_the_owned_receipt_until_completion( string $outcome, int $worker_status = 0 ): void {
		global $wp_filter;
		$hooks = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$hooks[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			remove_all_actions( $hook );
		}
		$service = static fn() => 'http://127.0.0.1:9';
		add_filter( 'pre_option_' . Proxy::OPTION, $service );
		$cookies = $_COOKIE;
		$user    = get_current_user_id();
		wp_set_current_user( 0 );
		$account  = 0;
		$approval = (object) array( 'status' => 'approved' );
		if ( 'approval-withdrawn' === $outcome ) {
			$account = (int) get_users(
				array(
					'role'   => 'administrator',
					'number' => 1,
					'fields' => 'ids',
				)
			)[0];
			wp_set_current_user( $account );
		}
		$account_status = static fn( $value, $id, $key ) => $id === $account && 'linker_approval_status' === $key ? $approval->status : $value;
		if ( $account > 0 ) {
			add_filter( 'get_user_metadata', $account_status, 10, 3 );
		}
		$_COOKIE   = array( Identity::COOKIE => bin2hex( random_bytes( 16 ) ) );
		$job       = wp_generate_uuid4();
		$question  = 'Where is the AC rating for C:\\manuals?';
		$request   = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn/start' );
		$operation = wp_generate_uuid4();
		$request->set_header( 'X-Linker-Operation', $operation );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_body(
			(string) wp_json_encode(
				array(
					'locale'   => 'en',
					'messages' => array(
						array(
							'role'    => 'user',
							'content' => $question,
						),
					),
				)
			)
		);
		$id   = $account > 0 ? ( new Conversations() )->open() : 0;
		$poll = new WP_REST_Request( 'GET', '/linker-ai/v1/genie/turn/' . $job );
		$poll->set_url_params( array( 'job_id' => $job ) );
		$permission_failure = in_array( $outcome, array( 'publication_changed', 'publication_unavailable' ), true );

		$stage  = $permission_failure ? 'understanding' : 'searching_documents';
		$scope  = '';
		$starts = 0;
		$reads  = 0;
		$stream = "event: reading\ndata: {\"id\":\"att1\",\"text\":\"private extraction\"}\n\nevent: block\ndata: {\"type\":\"text\",\"text\":\"Look at the AC output.\",\"refs\":[]}\n\nevent: done\ndata: {}\n\n";
		$queue  = new class() {
			public string $state = 'running';
		};
		$fetch  = function ( string $url, array $body, array $headers ) use ( &$job, &$scope, &$starts, &$reads, $stage, $stream, $outcome, $worker_status, &$id, $queue ) {
			if ( str_ends_with( $url, '/start' ) ) {
				++$starts;
				$scope = $headers['X-Linker-Resource-Subject'];
				$this->assertNotEmpty( $body['messages'] );
				return (string) wp_json_encode(
					array(
						'status' => 'running',
						'job_id' => $job,
						'stage'  => 'waited' === $outcome ? 'waiting' : 'understanding',
					)
				);
			}
			$this->assertStringEndsWith( $job, $url );
			$this->assertSame( $scope, $headers['X-Linker-Resource-Subject'] );
			++$reads;
			if ( 'owner-deleted' === $outcome && 3 === $reads ) {
				$this->assertTrue( ( new Conversations() )->delete( $id ) );
			}
			if ( 'waited' === $outcome && 'offline' === $queue->state ) {
				return new WP_Error( 'linker_genie_connection', 'Temporary disconnect', array( 'status' => 503 ) );
			}
			if ( 'waited' === $outcome ? 'running' === $queue->state : $reads <= 2 ) {
				return (string) wp_json_encode(
					array(
						'status'         => 'running',
						'stage'          => $stage,
						'queued_seconds' => 'waited' === $outcome ? Proxy::TURN_BUDGET : 0,
					)
				);
			}
			if ( $worker_status && 1 === $starts ) {
				return (string) wp_json_encode(
					array(
						'job_id'      => $job,
						'status'      => 'failed',
						'http_status' => $worker_status,
						'code'        => $outcome,
						'detail'      => $outcome,
					)
				);
			}
			return (string) wp_json_encode(
				array(
					'status'         => 'completed',
					'queued_seconds' => 'waited' === $outcome ? Proxy::TURN_BUDGET : 0,
					'stream'         => $stream,
				)
			);
		};
		try {

			$source  = new PublicationGuard(
				null,
				static function ( array $deps ) use ( $outcome ) {
					return 'revoked' === $outcome ? array( 'valid' => false ) : \Linker\Commerce\Products\Publication::validate( $deps );
				}
			);
			$proxy   = new Proxy( new Conversations(), $fetch, token: 'synthetic', publication: $source );
			$handler = array( 'callback' => array( $proxy, 'start' ) );
			$gate    = new Resources();
			$start   = $gate->dispatch( null, $request, '', $handler );
			$this->assertInstanceOf( WP_REST_Response::class, $start );
			$this->assertSame( 202, $start->get_status(), (string) wp_json_encode( $start->get_data() ) );
			$id = $start->get_data()['conversation_id'];

			$this->assertSame( $account ? 'private' : 'auto-draft', get_post_status( $id ) );
			$this->assertSame( $job, $start->get_data()['job_id'] );
			$pending = $proxy->conversation()->get_data()['pending_job'];
			$this->assertSame( $question, $pending['user_message'] );
			$this->assertSame( $job, $pending['job_id'] );
			$this->assertArrayNotHasKey( 'messages', $pending );
			$this->assertArrayNotHasKey( 'stream', $pending );
			$receipt     = ( new Replies() )->operation( $operation );
			$fingerprint = (string) get_post_meta( $receipt, '_linker_input', true );
			$this->assertFalse( Resources::completed_genie_operation( $operation, $fingerprint ) );
			$this->assertSame( 202, $gate->dispatch( null, $request, '', $handler )->get_status() );
			$this->assertSame( 1, $starts );

			$owner   = $_COOKIE;
			$_COOKIE = array( Identity::COOKIE => str_repeat( 'b', 32 ) );
			$foreign = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_Error::class, $foreign );
			$this->assertSame( 404, $foreign->get_error_data()['status'] );
			$this->assertSame( 'waited' === $outcome ? 1 : 0, $reads );
			$_COOKIE = $owner;
			$running = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_REST_Response::class, $running );
			$this->assertSame( $stage, $running->get_data()['stage'] );
			$this->assertSame( $stage, $proxy->conversation()->get_data()['pending_job']['stage'] );
			if ( in_array( $outcome, array( 'expired', 'waited' ), true ) ) {
				$input               = \Linker\Tools\Genie\PendingTurns::current( $id );
				$input['started_at'] = time() - Proxy::TURN_BUDGET - 1;
				update_post_meta( $id, \Linker\Tools\Genie\PendingTurns::PENDING, wp_slash( $input ) );
				wp_cache_delete( $job, 'linker_genie_poll' );
			}
			// A second native MySQL connection holds the terminal operation while this tab polls.
			$peer = new \wpdb( constant( 'DB_USER' ), constant( 'DB_PASSWORD' ), constant( 'DB_NAME' ), constant( 'DB_HOST' ) );
			$key  = \Linker\Commerce\Inquiry\Assessment\Lock::name( 'genie-operation-' . $operation );
			$this->assertSame( '1', $peer->get_var( $peer->prepare( 'SELECT GET_LOCK(%s, 0)', $key ) ) );
			try {
				$joining = $proxy->poll( $poll );
				$this->assertInstanceOf( WP_REST_Response::class, $joining );
				$this->assertSame( 'running', $joining->get_data()['status'] );
				$this->assertSame(
					array(
						'expired' => 1,
						'waited'  => 4,
					)[ $outcome ] ?? 2,
					$reads
				);
				$this->assertSame( '', get_post_meta( $receipt, \Linker\Tools\Genie\PendingTurns::STAGE, true ) );
			} finally {
				$peer->get_var( $peer->prepare( 'SELECT RELEASE_LOCK(%s)', $key ) );
				$peer->close();
			}

			if ( 'waited' === $outcome ) {
				$this->assertEquals( Proxy::TURN_BUDGET, $joining->get_data()['queued_seconds'] );
				wp_clear_scheduled_hook( 'linker_tools_expire_genie_turn', array( $id, $job ) );
				$queue->state = 'offline';
				$proxy->expire( $id, $job );
				$this->assertSame( $job, $proxy->conversation()->get_data()['pending_job']['job_id'] );
				$queue->state = 'running';
				$proxy->expire( $id, $job );
				$this->assertGreaterThan( time(), wp_next_scheduled( 'linker_tools_expire_genie_turn', array( $id, $job ) ) );
				$reopened = $proxy->conversation()->get_data()['pending_job'];
				$this->assertSame( $job, $reopened['job_id'] );
				$this->assertEquals( Proxy::TURN_BUDGET, $reopened['queued_seconds'] );
				$this->assertSame( $stage, $reopened['stage'] );
				$queue->state = 'completed';
			}
			$recover = in_array( $outcome, array( 'receipt-poll', 'receipt-cron' ), true );
			if ( $recover ) {
				$interrupt = static function ( array $post ) {
					if ( Replies::TYPE === $post['post_type'] ) {
						$post['post_content'] = '';
					}
					return $post;
				};
				add_filter( 'wp_insert_post_data', $interrupt );
				try {
					$interrupted = $proxy->poll( $poll );
					$this->assertInstanceOf( WP_Error::class, $interrupted );
					$this->assertSame( 503, $interrupted->get_error_data()['status'] );
					$this->assertArrayNotHasKey( 'unrecorded', $interrupted->get_error_data() );
				} finally {
					remove_filter( 'wp_insert_post_data', $interrupt );
				}
				$this->assertSame( $operation, ( new \Linker\Tools\Genie\Thread() )->read( $id )['operation_id'] ?? null );
				$input               = \Linker\Tools\Genie\PendingTurns::current( $id );
				$input['started_at'] = time() - Proxy::TURN_BUDGET - 1;
				update_post_meta( $id, \Linker\Tools\Genie\PendingTurns::PENDING, wp_slash( $input ) );
				if ( 'receipt-cron' === $outcome ) {
					$proxy->expire( $id, $job );
					$this->assertSame( array(), \Linker\Tools\Genie\PendingTurns::current( $id ) );
				}
			}
			$final = $proxy->poll( $poll );
			if ( 'owner-deleted' === $outcome ) {
				$this->assertInstanceOf( WP_Error::class, $final );
				$this->assertSame( 404, $final->get_error_data()['status'] );
				$this->assertSame( '', ( new \Linker\Tools\Genie\Thread() )->read( $id )['stream'] );
				return;
			}
			if ( ! $recover && ! in_array( $outcome, array( 'completed', 'approval-withdrawn', 'waited' ), true ) ) {
				$this->assertInstanceOf( WP_Error::class, $final );
				$this->assertSame( in_array( $outcome, array( 'revoked', 'publication_changed' ), true ) ? 409 : 503, $final->get_error_data()['status'] );
				$this->assertTrue( $final->get_error_data()['unrecorded'] );
				$this->assertNull( get_post( $id ) );
				$this->assertFalse( Resources::completed_genie_operation( $operation, $fingerprint ) );
				$this->assertSame( 0, ( new Replies() )->operation( $operation ) );
				if ( $permission_failure ) {
					$this->assertSame( 'linker_genie_' . $outcome, $final->get_error_code() );
					$this->assertArrayNotHasKey( 'stream', $final->get_error_data() );
					$this->assertSame( array(), \Linker\Tools\Genie\PendingTurns::current( $id ) );
					$job   = wp_generate_uuid4();
					$retry = $gate->dispatch( null, $request, '', $handler );
					$this->assertSame( 202, $retry->get_status() );
					$id = $retry->get_data()['conversation_id'];
					$this->assertSame( $job, $retry->get_data()['job_id'] );
					$poll->set_url_params( array( 'job_id' => $job ) );
					$answer = $proxy->poll( $poll );
					$this->assertInstanceOf( WP_REST_Response::class, $answer );
					$this->assertSame( 'completed', $answer->get_data()['status'] );
					$this->assertTrue( Resources::completed_genie_operation( $operation, $fingerprint ) );
					$this->assertSame( $question, $proxy->conversation()->get_data()['messages'][0]['content'] );
				}
				return;
			}
			$this->assertInstanceOf( WP_REST_Response::class, $final );
			$this->assertSame( 'completed', $final->get_data()['status'] );
			$this->assertStringNotContainsString( 'private extraction', $final->get_data()['stream'] );
			$this->assertSame( 'private', get_post_status( $id ) );
			$this->assertTrue( Resources::completed_genie_operation( $operation, $fingerprint ) );
			$again = $proxy->poll( $poll );
			$this->assertInstanceOf( WP_REST_Response::class, $again );
			$this->assertSame( $final->get_data(), $again->get_data() );
			$this->assertSame( 'waited' === $outcome ? 9 : 3, $reads );
			$thread = $proxy->conversation()->get_data();
			$this->assertArrayNotHasKey( 'pending_job', $thread );
			$this->assertSame( $operation, $thread['operation_id'] );
			$this->assertCount( 1, $thread['messages'] );
			$this->assertSame( $question, $thread['messages'][0]['content'] );
			if ( $account ) {
				$this->assertTrue( PublicationGuard::sees_prices() );
				$approval->status = 'restricted';
				$this->assertFalse( PublicationGuard::sees_prices() );
				$replay = $proxy->poll( $poll );
				$this->assertInstanceOf( WP_Error::class, $replay );
				$this->assertSame( 409, $replay->get_error_data()['status'] );
				$this->assertSame( 3, $reads );
			}
		} finally {
			foreach ( $hooks as $hook => $callbacks ) {
				if ( null === $callbacks ) {
					unset( $wp_filter[ $hook ] );
				} else {
					$wp_filter[ $hook ] = $callbacks; // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore this fixture's cookie hooks.
				}
			}
			if ( $id > 0 ) {
				wp_clear_scheduled_hook( 'linker_tools_expire_genie_turn', array( $id, $job ) );
				wp_delete_post( $id, true );
			}
			$receipt = ( new Replies() )->operation( $operation );
			if ( $receipt > 0 ) {
				wp_delete_post( $receipt, true );
			}
			remove_filter( 'get_user_metadata', $account_status, 10 );
			remove_filter( 'pre_option_' . Proxy::OPTION, $service );
			$_COOKIE = $cookies;
			wp_set_current_user( $user );
		}
	}

	/** Terminal states of a real WordPress receipt.
	 *
	 * @return array<string,array{0:string,1?:int}>
	 */
	public static function async_outcomes(): array {
		return array(
			'deleted while the final response is in flight' => array( 'owner-deleted' ),
			'completed then restricted'       => array( 'approval-withdrawn' ),
			'resume committed after deadline' => array( 'receipt-poll' ),
			'cron recovers unsigned receipt'  => array( 'receipt-cron' ),
			'checked'                         => array( 'completed' ),
			'publication withdrawn'           => array( 'revoked' ),
			'worker failed'                   => array( 'genie_job_failed', 503 ),
			'worker starts after withdrawal'  => array( 'publication_changed', 409 ),
			'worker authority unavailable'    => array( 'publication_unavailable', 503 ),
			'deadline'                        => array( 'expired' ),
			'work queued before execution'    => array( 'waited' ),
		);
	}
}
