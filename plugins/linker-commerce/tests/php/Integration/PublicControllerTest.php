<?php
/**
 * Real REST permission, verification replay and business proof consumption.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Integration;

use Linker\Commerce\Protection\Admission;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Configuration;
use Linker\Commerce\Protection\Controller;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Proof;
use Linker\Commerce\Protection\Privacy;
use WP_REST_Request;
use WP_REST_Response;
use WP_Error;

/**
 * No native business write or model/mail occurs during verification itself.
 *
 * @coversNothing
 */
final class PublicControllerTest extends IntegrationTestCase {
	/**
	 * Explicit dummy configuration shared by the real REST fixture.
	 *
	 * @var Configuration
	 */
	private Configuration $configuration;
	/**
	 * Count only calls to the fixed verification endpoint.
	 *
	 * @var int
	 */
	private int $calls = 0;

	/** Isolate cookie, journal, REST registrations and only the fixed HTTP endpoint. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$cookie                      = $_COOKIE[ Identity::COOKIE ] ?? null; // phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Preserve the exact fixture runner value.
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'a', 32 );
		$old                         = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		global $wp_rest_server; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Native WordPress REST server fixture isolation.
		$server              = $wp_rest_server;
		$wp_rest_server      = new \WP_REST_Server(); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Native WordPress global replacement in isolated test.
		$this->configuration = new Configuration( 'enforce', '1x00000000000000000000AA', '1x0000000000000000000000000000000AA', 'example.test' );
		( new Controller( $this->configuration ) )->register();
		$http = function ( $pre, $args, $url ) {
			if ( 'https://challenges.cloudflare.com/turnstile/v0/siteverify' !== $url ) {
				return $pre;
			}
			++$this->calls;
			$valid = 'synthetic-valid' === $args['body']['response'];
			return array(
				'response' => array( 'code' => 200 ),
				'body'     => wp_json_encode(
					array(
						'success'     => $valid,
						'hostname'    => 'example.test',
						'action'      => 'inquiry',
						'error-codes' => $valid ? array() : array( 'invalid-input-response' ),
					)
				),
			);
		};
		add_filter( 'pre_http_request', $http, 10, 3 );
		$this->later(
			static function () use ( $cookie, $old, $server, $http ): void {
				global $wp_rest_server; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Restore native WordPress REST server.
				$wp_rest_server = $server; // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedVariableFound -- Restore native WordPress global.
				if ( null === $cookie ) {
					unset( $_COOKIE[ Identity::COOKIE ] );
				} else {
					$_COOKIE[ Identity::COOKIE ] = $cookie;
				}
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				remove_filter( 'pre_http_request', $http );
			}
		);
	}

	/**
	 * Use the real REST server so schema and permission callbacks both execute.
	 *
	 * @param string              $operation Controller operation.
	 * @param array<string,mixed> $input Body.
	 * @param string|null         $origin Alternate origin.
	 */
	private function request( string $operation, array $input, ?string $origin = null ): WP_REST_Response {
		$request = new WP_REST_Request( 'POST', '/linker/v1/protection/' . $operation );
		$request->set_header( 'origin', $origin ?? self::origin() );
		$request->set_body_params( $input );
		return rest_do_request( $request );
	}

	/**
	 * Current site authority, not a guessed localhost port.
	 *
	 * @throws \RuntimeException Invalid fixture configuration.
	 */
	private static function origin(): string {
		$parts = wp_parse_url( home_url() );
		if ( ! is_array( $parts ) || ! isset( $parts['scheme'], $parts['host'] ) ) {
			throw new \RuntimeException( 'Fixture site has no valid origin.' );
		}
		return $parts['scheme'] . '://' . $parts['host'] . ( isset( $parts['port'] ) ? ':' . $parts['port'] : '' );
	}

	/** Public validation is fixed-scope and may not be invoked across origins. */
	public function test_schema_and_origin_refuse_before_upstream_or_business_side_effects(): void {
		$foreign = $this->request( 'prepare', array( 'action' => 'inquiry' ), 'https://other.test' );
		$this->assertSame( 403, $foreign->get_status() );
		$credentials = $this->request( 'prepare', array( 'action' => 'inquiry' ), str_replace( '://', '://name@', self::origin() ) );
		$this->assertSame( 403, $credentials->get_status() );
		$this->assertSame( 400, $this->request( 'prepare', array( 'action' => 'approve_account' ) )->get_status() );
		$this->assertSame( 0, $this->calls );
		$this->assertFalse( get_option( Ledger::OPTION ) );
	}

	/** Repeating an identical validation reuses its result, timestamp and budget. */
	public function test_valid_verification_replay_never_renews_or_calls_twice(): void {
		$prepare = $this->request( 'prepare', array( 'action' => 'inquiry' ) );
		$this->assertSame( 200, $prepare->get_status() );
		$input = array(
			'action'  => 'inquiry',
			'prepare' => $prepare->get_data()['prepare'],
			'token'   => 'synthetic-valid',
		);
		$first = $this->request( 'verify', $input );
		$this->assertSame( 200, $first->get_status() );
		$this->assertSame( $first->get_data(), $this->request( 'verify', $input )->get_data() );
		$this->assertSame( 1, $this->calls );
		$this->assertSame( 409, $this->request( 'verify', array_merge( $input, array( 'token' => 'changed' ) ) )->get_status() );
		$this->assertSame( 1, $this->calls, 'A changed replay never reaches Siteverify.' );
		$this->assertStringContainsString( 'no-store', $first->get_headers()['Cache-Control'] );
	}

	/** One verified form proof cannot create two logical business submissions. */
	public function test_native_admission_consumes_proof_once_and_refunds_rejected_second_hold(): void {
		$prepared = $this->request( 'prepare', array( 'action' => 'inquiry' ) )->get_data();
		$verified = $this->request(
			'verify',
			array(
				'action'  => 'inquiry',
				'prepare' => $prepared['prepare'],
				'token'   => 'synthetic-valid',
			)
		);
		$this->assertSame( 200, $verified->get_status() );
		$proof     = $verified->get_data()['proof'];
		$admission = new Admission( $this->configuration );
		$limits    = array( new Allowance( 'business_day', 'synthetic-browser', 2, DAY_IN_SECONDS ) );
		$id        = wp_generate_uuid4();
		$first     = $admission->reserve( 'inquiry', $proof, $id, array( 'message' => 'Synthetic request' ), $limits, 60, true );
		$this->assertIsArray( $first );
		$this->assertIsArray( $admission->dispatch( $first ) );
		$this->assertIsArray( $admission->complete( $first, 42 ) );
		$repeat = $admission->reserve( 'inquiry', '', $id, array( 'message' => 'Synthetic request' ), $limits, 60, true );
		$this->assertIsArray( $repeat );
		$this->assertTrue( $repeat['reused'] );
		$this->assertSame( 42, $repeat['receipt']['outcome'] );
		$second = $admission->reserve( 'inquiry', $proof, wp_generate_uuid4(), array( 'message' => 'Another request' ), $limits, 60, true );
		$this->assertIsArray( $second );
		$this->assertInstanceOf( WP_Error::class, $admission->dispatch( $second ) );
		$this->assertIsArray( ( new Ledger() )->reserve( wp_generate_uuid4(), hash( 'sha256', 'fresh request' ), $limits, 60 ), 'Rejected proof reuse did not consume the last business allowance.' );
	}

	/** A signed stamp alone cannot substitute for a durable successful Siteverify. */
	public function test_signed_proof_without_a_successful_verification_receipt_never_dispatches(): void {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$proof  = ( new Proof() )->issue( 'verified', 'inquiry', $identity, wp_generate_uuid4() );
		$gate   = new Admission( $this->configuration );
		$permit = $gate->reserve( 'inquiry', $proof, wp_generate_uuid4(), array( 'message' => 'Fixture' ), array( new Allowance( 'business_day', 'fixture', 1, DAY_IN_SECONDS ) ), 60, true );
		$this->assertIsArray( $permit );
		$result = $gate->dispatch( $permit );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_admission_proof', $result->get_error_code() );
		$receipt = ( new Ledger() )->lookup( $permit['id'], $permit['fingerprint'] );
		$this->assertIsArray( $receipt );
		$this->assertSame( 'cancelled', $receipt['status'] );
		$this->assertSame( 0, $this->calls );
	}

	/** The actually wired pre-dispatch cap rejects JSON before route schema work. */
	public function test_oversized_verification_body_has_no_provider_side_effect(): void {
		$request = new WP_REST_Request( 'POST', '/linker/v1/protection/verify' );
		$request->set_header( 'origin', self::origin() );
		$request->set_header( 'content-type', 'application/json' );
		$request->set_body( str_repeat( 'x', 16385 ) );
		$this->assertSame( 413, rest_do_request( $request )->get_status() );
		$this->assertSame( 0, $this->calls );
		$this->assertFalse( get_option( Ledger::OPTION ) );
	}

	/** Recipient erasure removes a consumed record link without reviving its proof. */
	public function test_erasure_drops_consumed_record_reference_but_preserves_single_use(): void {
		$prepared  = $this->request( 'prepare', array( 'action' => 'inquiry' ) )->get_data();
		$verified  = $this->request(
			'verify',
			array(
				'action'  => 'inquiry',
				'prepare' => $prepared['prepare'],
				'token'   => 'synthetic-valid',
			)
		)->get_data();
		$recipient = Identity::recipient( 'synthetic@example.test' );
		$gate      = new Admission( $this->configuration );
		$limits    = array( new Allowance( 'business_day', $recipient, 3, DAY_IN_SECONDS ) );
		$id        = wp_generate_uuid4();
		$permit    = $gate->reserve( 'inquiry', $verified['proof'], $id, array( 'message' => 'Fixture' ), $limits, 60, true );
		$this->assertIsArray( $permit );
		$this->assertIsArray( $gate->dispatch( $permit ) );
		$this->assertIsArray( $gate->complete( $permit, 42 ) );
		$this->assertIsArray( ( new Ledger() )->privacy( array( Allowance::owner_for( $recipient ) ), true ) );
		$journal = json_decode( get_option( Ledger::OPTION ), true );
		$this->assertSame( 'erased', $journal['receipts'][ $id ]['status'] );
		$this->assertSame( array( 'erased' ), array_column( $journal['receipts'], 'consumed_by' ) );
		$second = $gate->reserve( 'inquiry', $verified['proof'], wp_generate_uuid4(), array( 'message' => 'Retry after erasure' ), $limits, 60, true );
		$this->assertIsArray( $second );
		$result = $gate->dispatch( $second );
		$this->assertInstanceOf( WP_Error::class, $result );
		$this->assertSame( 'linker_admission_proof_reused', $result->get_error_code() );
	}

	/** Native privacy resolves signed-in verification, including failed-only visits. */
	public function test_native_privacy_covers_account_verifications_without_a_business_submission(): void {
		$customer = $this->customer();
		$this->as_user( $customer->get_id() );
		foreach ( array( 'synthetic-valid', 'synthetic-invalid' ) as $token ) {
			$prepare = $this->request( 'prepare', array( 'action' => 'inquiry' ) )->get_data();
			$this->request(
				'verify',
				array(
					'action'  => 'inquiry',
					'prepare' => $prepare['prepare'],
					'token'   => $token,
				)
			);
		}
		$privacy = new Privacy();
		$export  = $privacy->export( $customer->get_email() );
		$this->assertCount( 2, $export['data'] );
		$this->assertTrue( $privacy->erase( $customer->get_email() )['items_removed'] );
		$this->assertSame( array(), $privacy->export( $customer->get_email() )['data'] );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$this->assertStringNotContainsString( $identity->binding(), get_option( Ledger::OPTION ) );
		$this->assertStringNotContainsString( Allowance::owner_for( $identity->account ), get_option( Ledger::OPTION ) );
	}

	/** Observe records would-deny and retry data without refusing the real flow. */
	public function test_observe_accounts_for_dispatch_quota_replay_and_storage_failure_without_blocking(): void {
		$gate   = new Admission( new Configuration( 'observe', '', '', '' ) );
		$limits = array( new Allowance( 'observed_day', 'synthetic', 1, DAY_IN_SECONDS ) );
		$id     = wp_generate_uuid4();
		$first  = $gate->reserve( 'inquiry', '', $id, array( 'message' => 'Fixture' ), $limits, 60 );
		$this->assertIsArray( $first );
		$this->assertFalse( $first['enforced'] );
		$this->assertSame( 0, $first['advisory']['allowances'][0]['remaining'] );
		$this->assertIsArray( $gate->dispatch( $first ) );
		$this->assertIsArray( $gate->complete( $first, 42 ) );
		$retry = $gate->reserve( 'inquiry', '', $id, array( 'message' => 'Fixture' ), $limits, 60 );
		$this->assertIsArray( $retry );
		$this->assertSame( 'completed', $retry['advisory']['reason'] );
		$denied = $gate->reserve( 'inquiry', '', wp_generate_uuid4(), array( 'message' => 'Another' ), $limits, 60 );
		$this->assertIsArray( $denied );
		$this->assertFalse( $denied['enforced'] );
		$this->assertSame( 'linker_admission_quota', $denied['advisory']['reason'] );
		$this->assertIsArray( $gate->dispatch( $denied ) );
		$this->assertIsArray( $gate->complete( $denied, 43 ) );
		$summary = ( new Ledger() )->summary();
		$this->assertIsArray( $summary );
		$this->assertContains( 'replay', array_column( $summary['events'], 'reason' ) );
		$this->assertContains( 'quota', array_column( $summary['events'], 'reason' ) );
		$this->assertSame( Ledger::POLICY, $summary['policy'] );
		update_option( Ledger::OPTION, 'synthetic corruption', false );
		$unavailable = $gate->reserve( 'inquiry', '', wp_generate_uuid4(), array(), $limits, 60 );
		$this->assertIsArray( $unavailable );
		$this->assertFalse( $unavailable['enforced'] );
		$this->assertSame( 'linker_admission_storage', $unavailable['advisory']['reason'] );
		$this->assertSame( 0, $this->calls, 'Observations never invoke a model, mail or Siteverify.' );
	}
}
