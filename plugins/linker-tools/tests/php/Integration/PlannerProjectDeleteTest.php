<?php
/**
 * Public project deletion against native Woo order storage.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Planning\Context;
use Linker\Commerce\Protection\Identity;
use Linker\Tools\Planner\Gateway;
use Linker\Tools\Planner\NativeIdentity;
use Linker\Tools\Planner\Transport;
use PHPUnit\Framework\TestCase;

/**
 * The planner only removes a prepared project after checking native orders.
 *
 * @covers \Linker\Tools\Planner\Gateway
 */
final class PlannerProjectDeleteTest extends TestCase {
	/**
	 * Exercise both Woo authoritative storage modes.
	 *
	 * @return array<string,array{string}>
	 */
	public static function stores(): array {
		return array(
			'HPOS' => array( 'yes' ),
			'CPT'  => array( 'no' ),
		);
	}

	/**
	 * Current compact references and historical full snapshots both freeze trashed inquiries.
	 *
	 * @dataProvider stores
	 * @param string $hpos Select the native order data store for this request.
	 */
	public function test_native_references_guard_delete_and_allow_recovery( string $hpos ): void {
		if ( ! defined( 'LINKER_GENIE_SERVICE_TOKEN' ) ) {
			define( 'LINKER_GENIE_SERVICE_TOKEN', 'synthetic-delete-fixture' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedConstantFound -- Private transport fixture only.
		}
		$project = bin2hex( random_bytes( 16 ) );
		$handoff = bin2hex( random_bytes( 16 ) );
		$user    = get_current_user_id();
		$cookies = $_COOKIE;
		$storage = static fn (): string => $hpos;
		$no_sync = static fn (): string => 'no';
		add_filter( 'pre_option_woocommerce_custom_orders_table_enabled', $storage );
		add_filter( 'pre_option_woocommerce_custom_orders_table_data_sync_enabled', $no_sync );
		$order   = new \WC_Order();
		$command = array(
			'schema_version'    => 1,
			'project_id'        => $project,
			'expected_revision' => 1,
			'key'               => wp_generate_uuid4(),
		);
		$body    = (string) wp_json_encode( $command );
		$request = new \WP_REST_Request( 'POST', '/linker/v1/planner/rpc/projects/delete' );
		$request->set_url_params( array( 'path' => 'projects/delete' ) );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_body( $body );
		$state_read  = 0;
		$race        = new \ArrayIterator( array( false, true ) );
		$raw_deletes = 0;
		$attempts    = 0;
		$deleted     = false;
		$result      = array(
			'project_id' => $project,
			'revision'   => 1,
			'deleted'    => true,
		);
		$reply       = static fn ( int $status, array $value ): array => array(
			'response' => array( 'code' => $status ),
			'headers'  => array( 'content-type' => 'application/json' ),
			'body'     => wp_json_encode( $value ),
		);
		$endpoint    = static fn (): string => 'https://engine.test';
		add_filter( 'pre_option_linker_planner_url', $endpoint );
		try {
			if ( 'yes' === $hpos && array() !== \WC_Install::get_missing_base_tables() ) {
				// A fresh standalone inquiry fixture starts with only CPT order storage.
				self::assertSame( array(), \WC_Install::verify_base_tables( false, true ) );
			}
			wp_set_current_user( 1 );
			$_COOKIE[ constant( 'LOGGED_IN_COOKIE' ) ] = wp_generate_auth_cookie( 1, time() + HOUR_IN_SECONDS, 'logged_in', 'deletion-test-token' );
			$_COOKIE[ Identity::COOKIE ]               = bin2hex( random_bytes( 16 ) );
			$request->set_header( 'x-wp-nonce', wp_create_nonce( 'wp_rest' ) );
			$transport = new Transport(
				static function ( string $url, array $args ) use ( $command, $body, $reply, $result, $project, &$attempts, &$deleted, &$state_read, &$raw_deletes, $race ): array|\WP_Error {
					self::assertSame( NativeIdentity::user_subject( 1 ), $args['headers']['X-Linker-Planner-Principal-Subject'] );
					if ( str_ends_with( $url, '/operations/replay/projects/delete' ) ) {
						self::assertSame( $body, $args['body'] );
						return $reply(
							200,
							array(
								'schema_version' => 1,
								'command_scope'  => 'delete:' . $project,
								'command_sha256' => str_repeat( 'a', 64 ),
								'status'         => $deleted ? 'replayed' : 'absent',
								'result'         => $deleted ? $result : null,
							)
						);
					}
					if ( str_ends_with( $url, '/projects/prepared-handoffs' ) ) {
						++$state_read;
						if ( $race->current() ) {
							$deleted = true;
						}
						if ( 1 === $state_read || $deleted ) {
							return $reply( 404, array( 'error' => array( 'code' => 'not_found' ) ) );
						}
						self::assertSame(
							array(
								'schema_version' => 1,
								'project_id'     => $project,
							),
							json_decode( $args['body'], true )
						);
						return $reply(
							200,
							array(
								'has_handoffs'       => false,
								'inquiry_generation' => 7,
							)
						);
					}
					if ( str_ends_with( $url, '/projects/delete' ) ) {
						self::assertSame( $body, $args['body'] );
						++$raw_deletes;
						return $reply( 200, $result );
					}
					self::assertStringEndsWith( '/projects/delete-after-inquiry-check', $url );
					self::assertSame( $command + array( 'inquiry_generation' => 7 ), json_decode( $args['body'], true ) );
					++$attempts;
					$deleted = true;
					return new \WP_Error( 'timeout' ); // The engine committed but the HTTP reply was lost.
				}
			);
			$gateway   = new Gateway( new NativeIdentity(), $transport );
			$ledger    = new \Linker\Commerce\Protection\Ledger();
			$summary   = $ledger->summary();
			self::assertIsArray( $summary );
			$before  = $summary['counts']['planner_write']['dispatched'] ?? 0;
			$missing = $gateway->forward( $request );
			self::assertInstanceOf( \WP_Error::class, $missing );
			self::assertSame( 0, $raw_deletes );
			$order->set_status( 'pending' );
			$order_id = $order->save();
			$order->delete( false );
			$order = wc_get_order( $order_id );
			self::assertInstanceOf( \WC_Order::class, $order );
			self::assertSame( 'trash', $order->get_status( 'edit' ) );
			$order->update_meta_data( '_linker_preliminary_project', $project . ':12' );
			$order->save_meta_data();
			$refused = $gateway->forward( $request );
			self::assertInstanceOf( \WP_REST_Response::class, $refused );
			self::assertSame( 409, $refused->get_status() );
			self::assertSame( 'inquiry_linked', $refused->get_data()->error->code );
			$order->update_meta_data( '_linker_preliminary_project', $handoff . ':12' );
			$order->save_meta_data();
			foreach ( array( array( 'reference' => array( 'project_id' => $project ) ), array( 'handoff' => array( 'snapshot' => array( 'project_id' => $project ) ) ) ) as $entry ) {
				$metadata = wp_json_encode( array( $handoff => $entry ) );
				self::assertIsString( $metadata );
				$order->update_meta_data( Context::META, $metadata );
				$order->save_meta_data();
				$refused = $gateway->forward( $request );
				self::assertInstanceOf( \WP_REST_Response::class, $refused );
				self::assertSame( 409, $refused->get_status() );
				self::assertSame( 'inquiry_linked', $refused->get_data()->error->code );
			}
			$order->update_meta_data( Context::META, 'truncated-json' );
			$order->save_meta_data();
			$unreadable = $gateway->forward( $request );
			self::assertInstanceOf( \WP_Error::class, $unreadable );
			self::assertSame( 503, $unreadable->get_error_data()['status'] );
			self::assertSame( 0, $attempts );
			$metadata = wp_json_encode(
				array(
					$handoff => array(
						'reference' => array(
							'project_id' => $handoff,
							'title'      => $project,
						),
					),
				)
			);
			self::assertIsString( $metadata );
			$order->update_meta_data( Context::META, $metadata );
			$order->save_meta_data();
			$lost = $gateway->forward( $request );
			self::assertInstanceOf( \WP_Error::class, $lost );
			self::assertSame( 503, $lost->get_error_data()['status'] );
			$summary = $ledger->summary();
			self::assertIsArray( $summary );
			self::assertSame( $before, $summary['counts']['planner_write']['dispatched'] ?? 0 );
			self::assertSame( 1, $attempts );
			$replay = $gateway->forward( $request );
			self::assertInstanceOf( \WP_REST_Response::class, $replay );
			self::assertTrue( $replay->get_data()->deleted );
			self::assertSame( 1, $attempts );
			// A peer can commit between the gateway's first lookup and the state read.
			$deleted = false;
			$race->next();
			$replay = $gateway->forward( $request );
			self::assertInstanceOf( \WP_REST_Response::class, $replay );
			self::assertTrue( $replay->get_data()->deleted );
			self::assertSame( 0, $raw_deletes );
		} finally {
			if ( $order instanceof \WC_Order ) {
				$order->delete( true );
			}
			remove_filter( 'pre_option_woocommerce_custom_orders_table_data_sync_enabled', $no_sync );
			remove_filter( 'pre_option_woocommerce_custom_orders_table_enabled', $storage );
			remove_filter( 'pre_option_linker_planner_url', $endpoint );
			wp_set_current_user( $user );
			$_COOKIE = $cookies;
		}
	}
}
