<?php
/**
 * Tests for a customer's VAT ID and its verdict.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Registration;

use Linker\Commerce\Registration\VatProfile;
use Linker\Commerce\Registration\ViesClient;
use Linker\Commerce\Tests\TestCase;
use Mockery;
use WC_Order;
use WP_Error;
use WP_Mock;

/**
 * Tests for VatProfile, with the real VIES client on a mocked HTTP API.
 *
 * @covers \Linker\Commerce\Registration\VatProfile
 */
final class VatProfileTest extends TestCase {

	/**
	 * User meta of customer 5.
	 *
	 * @var array<string, mixed>
	 */
	private array $meta = array();

	/**
	 * What VIES answers next ("valid", "invalid", "down").
	 *
	 * @var list<string>
	 */
	private array $answers = array();

	/**
	 * Calls to VIES.
	 *
	 * @var int
	 */
	private int $vies_calls = 0;

	/**
	 * User meta lives in $meta; VIES answers from $answers.
	 */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( 'get_user_meta', array( 'return' => fn ( int $id, string $key ) => $this->meta[ $key ] ?? '' ) );
		WP_Mock::userFunction(
			'update_user_meta',
			array(
				'return' => function ( int $id, string $key, $value ): bool {
					$this->meta[ $key ] = $value;
					return true;
				},
			)
		);
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn ( $value ) => json_encode( $value ) ) );
		WP_Mock::userFunction( 'is_wp_error', array( 'return' => static fn ( $value ): bool => $value instanceof WP_Error ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_body', array( 'return' => static fn ( array $response ): string => $response['body'] ) );
		WP_Mock::userFunction( 'wp_remote_retrieve_response_code', array( 'return' => 200 ) );
		WP_Mock::userFunction(
			'wp_remote_post',
			array(
				'return' => function () {
					++$this->vies_calls;
					$answer = array_shift( $this->answers );
					if ( 'down' === $answer ) {
						return array( 'body' => '{"actionSucceed":false,"errorWrappers":[{"error":"MS_UNAVAILABLE"}]}' );
					}
					return array( 'body' => json_encode( array( 'valid' => 'valid' === $answer ) ) );
				},
			)
		);
	}

	/**
	 * At registration the number is checked once and nothing is announced (the new-customer email
	 * carries the verdict). WP_Mock's strict mode fails the test on any unexpected action.
	 */
	public function test_first_check_is_not_announced(): void {
		$this->answers = array( 'valid' );

		$this->assertSame( VatProfile::VALID, ( new VatProfile( new ViesClient() ) )->update( 5, 'de 143 454 214', false ) );
		$this->assertSame( 'DE143454214', $this->meta[ VatProfile::NUMBER_META ] );
		$this->assertSame( 1, $this->vies_calls );
	}

	/**
	 * The same number is not checked again, and an unchanged verdict announces nothing
	 * (mail-root-cause.md §5 M5: the old site re-checked and re-notified on every order).
	 */
	public function test_same_number_is_not_checked_again(): void {
		$this->meta = array(
			VatProfile::STATUS_META => VatProfile::INVALID,
			VatProfile::DETAIL_META => '',
			VatProfile::NUMBER_META => 'DE000000000',
		);

		$this->assertSame( VatProfile::INVALID, ( new VatProfile( new ViesClient() ) )->update( 5, 'DE 000 000 000', true ) );
		$this->assertSame( 0, $this->vies_calls );
	}

	/**
	 * A changed number is checked, and a changed verdict is announced once.
	 */
	public function test_changed_verdict_is_announced(): void {
		$this->meta    = array(
			VatProfile::STATUS_META => VatProfile::INVALID,
			VatProfile::DETAIL_META => '',
			VatProfile::NUMBER_META => 'DE000000000',
		);
		$this->answers = array( 'valid' );
		WP_Mock::expectAction( VatProfile::CHANGED_ACTION, 5, VatProfile::INVALID, VatProfile::VALID );

		$this->assertSame( VatProfile::VALID, ( new VatProfile( new ViesClient() ) )->update( 5, 'DE143454214', true ) );
		$this->assertConditionsMet();
	}

	/**
	 * A check VIES could not answer is repeated next time; the same verdict again announces nothing.
	 */
	public function test_unanswered_check_is_repeated(): void {
		$this->answers = array( 'down', 'down', 'valid' );
		WP_Mock::expectAction( VatProfile::CHANGED_ACTION, 5, VatProfile::UNVERIFIED, VatProfile::VALID );
		$profile = new VatProfile( new ViesClient() );

		$this->assertSame( VatProfile::UNVERIFIED, $profile->update( 5, 'DE143454214', false ) );
		$this->assertSame( 'MS_UNAVAILABLE', $this->meta[ VatProfile::DETAIL_META ] );
		$this->assertSame( VatProfile::UNVERIFIED, $profile->update( 5, 'DE143454214', true ) );
		$this->assertSame( VatProfile::VALID, $profile->update( 5, 'DE143454214', true ) );
		$this->assertSame( 3, $this->vies_calls );
	}

	/**
	 * No number, or one VIES cannot check, needs no call to VIES; a non-EU number is not checked again.
	 */
	public function test_without_a_checkable_number(): void {
		$profile = new VatProfile( new ViesClient() );

		$this->assertSame( VatProfile::NONE, $profile->update( 5, '', false ) );
		$this->assertSame( VatProfile::UNVERIFIED, $profile->update( 6, 'CHE-123.456.789 MWST', false ) );
		$this->assertSame( VatProfile::NOT_EU, $this->meta[ VatProfile::DETAIL_META ] );
		$this->assertSame( VatProfile::UNVERIFIED, $profile->update( 6, 'CHE-123.456.789 MWST', true ) );
		$this->assertSame( 0, $this->vies_calls );
	}

	/**
	 * The inquiry keeps the verdict at the time it was sent.
	 */
	public function test_snapshot(): void {
		$this->meta = array( VatProfile::STATUS_META => VatProfile::VALID );
		$order      = Mockery::mock( WC_Order::class );
		$order->allows( 'get_customer_id' )->andReturn( 5 );
		$order->expects( 'update_meta_data' )->with( VatProfile::ORDER_STATUS, VatProfile::VALID );

		( new VatProfile( new ViesClient() ) )->snapshot( $order );

		$this->assertConditionsMet();
	}

	/**
	 * Every verdict has a name for staff.
	 */
	public function test_labels(): void {
		WP_Mock::passthruFunction( '__' );

		foreach ( array( VatProfile::VALID, VatProfile::INVALID, VatProfile::UNVERIFIED, VatProfile::NONE, '' ) as $status ) {
			$this->assertNotSame( '', VatProfile::label( $status ) );
		}
		$this->assertStringContainsString( 'review', VatProfile::label( VatProfile::INVALID ) );
	}
}
