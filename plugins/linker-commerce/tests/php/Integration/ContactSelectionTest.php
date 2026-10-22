<?php
/**
 * Contact selection through real protection, Woo storage and the isolated Outbox.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Tests\Integration;

// phpcs:disable WordPress.Security.NonceVerification -- Actual native nonce/proof consumers are under test; fixture globals are restored.
// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Private local protection fixtures only, restored after each test.

use Linker\Commerce\Contact\Form;
use Linker\Commerce\Contact\Handler;
use Linker\Commerce\Contact\SelectionContext;
use Linker\Commerce\Contact\Submission;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Throttle;
use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\BusinessRecord;
use Linker\Commerce\Protection\Fingerprint;
use Linker\Commerce\Protection\FormRecovery;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Proof;

/**
 * No SMTP delivery: full throttle holds native rendered notifications in the Outbox.
 *
 * @coversNothing
 */
final class ContactSelectionTest extends IntegrationTestCase {
	/** Preserve native journal/cookies/settings; test only local synthetic identities. */
	protected function setUp(): void {
		parent::setUp();
		$this->as_user( 0 );
		$old    = get_option( Ledger::OPTION );
		$cookie = $_COOKIE;
		$env    = array();
		foreach ( array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => 'localhost',
		) as $key => $value ) {
			$env[ $key ] = getenv( $key );
			putenv( $key . '=' . $value );
		}
		delete_option( Ledger::OPTION );
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'c', 32 );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_DAY, time() ) );
		$delivery_attempts = 0;
		$no_delivery       = static function ( $pre ) use ( &$delivery_attempts ) {
			if ( null === $pre ) {
				++$delivery_attempts;
				return false;
			}
			return $pre;
		};
		add_filter( 'pre_wp_mail', $no_delivery, PHP_INT_MAX );
		$this->later(
			static function () use ( $no_delivery, &$delivery_attempts ): void {
				remove_filter( 'pre_wp_mail', $no_delivery, PHP_INT_MAX );
				self::assertSame( 0, $delivery_attempts, 'Outbox assertions never enter a real transport attempt.' );
			}
		);

		$this->later(
			static function () use ( $old, $cookie, $env ): void {
				delete_option( Ledger::OPTION );
				if ( false !== $old ) {
					update_option( Ledger::OPTION, $old, false );
				}
				$_COOKIE = $cookie;
				foreach ( $env as $key => $value ) {
					putenv( false === $value ? $key : $key . '=' . $value );
				}
			}
		);
	}

	/**
	 * Real included/excluded choices survive proof normalization and exact request replay.
	 *
	 * @testWith [true]
	 *           [false]
	 * @param bool $included Customer checkbox state.
	 */
	public function test_native_message_keeps_selection_separate_and_team_queue_reflects_the_choice( bool $included ): void {
		$needle  = 'Owned search needle \\ "quotes" & Rückfrage';
		$product = $this->product( '100' );
		$product->set_slug( 'contact-context-' . self::tag() . '-ä' );
		$product->save();
		$raw = wp_json_encode(
			array(
				'source'    => get_permalink( $product->get_id() ),
				'title'     => 'Forged browser title',
				'selection' => array(
					'q'      => $needle,
					'brand'  => 'saj',
					'sort'   => 'name',
					'kw_min' => '5,5',
					'token'  => 'must-not-leave',
				),
			)
		);
		$this->assertIsString( $raw );
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$challenge    = wp_generate_uuid4();
		$challenge_fp = hash( 'sha256', $challenge );
		$ledger       = new Ledger();
		$this->assertIsArray( $ledger->reserve( $challenge, $challenge_fp, array( new Allowance( 'fixture_verify', $identity->browser, 100, HOUR_IN_SECONDS ) ), 10, array(), 'verification_contact', $identity->binding() ) );
		$this->assertIsArray( $ledger->dispatch( $challenge, $challenge_fp ) );
		$this->assertIsArray( $ledger->complete( $challenge, $challenge_fp, 1 ) );
		$started = (string) time();
		$post    = array(
			'name'                          => 'Context Fixture',
			'email'                         => 'context-' . self::tag() . '@example.test',
			'message'                       => "My unchanged message.\nCustomer's second line.",
			'intent'                        => 'product',
			'consent'                       => '1',
			'linker_request_id'             => wp_generate_uuid4(),
			'linker_proof'                  => ( new Proof() )->issue( 'verified', 'contact', $identity, $challenge ),
			Form::NONCE_FIELD               => wp_create_nonce( Form::NONCE_ACTION ),
			'linker_started'                => $started,
			'linker_started_nonce'          => wp_create_nonce( 'linker_inquiry_started_' . $started ),
			SelectionContext::FIELD         => $raw,
			SelectionContext::INCLUDE_FIELD => '0',
		);
		if ( ! $included ) {
			unset( $post[ SelectionContext::FIELD ] );
		}
		$submission = Submission::from_post( $post );
		$this->assertInstanceOf( Submission::class, $submission );
		$marker = self::newest_mail_job();
		$this->assertSame( 'sent', ( new Handler() )->process( $post ) );
		$orders = wc_get_orders(
			array(
				'billing_email' => $post['email'],
				'limit'         => -1,
			)
		);
		$this->assertIsArray( $orders );
		$this->assertCount( 1, $orders );
		$order = $orders[0];
		$this->later(
			static function () use ( $order ): void {
				$order->delete( true );
			}
		);
		$this->assertSame( $post['message'], $order->get_customer_note() );
		$this->assertSame( $post['linker_request_id'], $order->get_meta( BusinessRecord::REQUEST ) );
		$this->assertSame( Fingerprint::make( $identity, 'contact', $included ? array_merge( get_object_vars( $submission ), array( 'selection' => $submission->selection() ) ) : get_object_vars( $submission ) ), $order->get_meta( BusinessRecord::INPUT ) );
		if ( $included ) {
			$fresh = wc_get_order( $order->get_id() );
			$this->assertInstanceOf( \WC_Order::class, $fresh );
			$fresh->read_meta_data( true );
			$stored = $fresh->get_meta( SelectionContext::META );
			$this->assertIsString( $stored );
			$this->assertSame( $submission->selection(), SelectionContext::stored( $stored ) );
			$this->assertSame( $needle, SelectionContext::stored( $stored )['selection']['q'] );
		} else {
			$this->assertSame( '', $order->get_meta( SelectionContext::META ) );
		}
		$jobs = self::mail_jobs_after( $marker );
		$this->assertCount( 2, $jobs );
		$team_found = false;
		foreach ( $jobs as $id ) {
			$stored = ( new JobStore() )->load( $id );
			$this->assertNotNull( $stored );
			$row = $stored['message']->to_array();
			if ( array( $post['email'] ) === $row['to'] ) {
				$this->assertStringNotContainsString( 'Owned search needle', $row['body'], 'Unverified receipt stays fixed.' );
				continue;
			}
			$team_found = true;
			$this->assertSame( $included, str_contains( $row['body'], 'Owned search needle' ) );
			$this->assertStringNotContainsString( 'Forged browser title', $row['body'] );
			$this->assertStringNotContainsString( 'must-not-leave', $row['body'] );
		}
		$this->assertTrue( $team_found );
		$this->assertSame( 'sent', ( new Handler() )->process( $post ), 'Same logical retry recovers the same native record.' );
		$this->assertSame( $jobs, self::mail_jobs_after( $marker ), 'Retry does not queue duplicate mail.' );
		$changed = $post;
		if ( $included ) {
			unset( $changed[ SelectionContext::FIELD ] );
		} else {
			$changed[ SelectionContext::FIELD ] = $raw;
		}
		$this->assertSame( 'verification_failed', ( new Handler() )->process( $changed ), 'Changing context changes the protected payload.' );

		wc_load_cart();
		$_COOKIE['wp_woocommerce_session_context_fixture'] = 'native-presence';
		$post['linker_individual_review']                  = '1';
		FormRecovery::save( 'contact', $post );
		$recovered = FormRecovery::consume( 'contact' );
		if ( $included ) {
			$this->assertSame(
				array(
					'source'    => $submission->selection()['source'],
					'selection' => $submission->selection()['selection'],
				),
				json_decode( $recovered[ SelectionContext::FIELD ], true )
			);
		} else {
			$this->assertSame( '', $recovered[ SelectionContext::FIELD ] );
		}

		$this->assertSame( $post[ SelectionContext::INCLUDE_FIELD ], $recovered[ SelectionContext::INCLUDE_FIELD ] );
		$this->assertSame( $post['message'], $recovered['message'] );
		$this->assertSame( $post['linker_request_id'], $recovered['linker_request_id'] );
		$this->assertSame( '1', $recovered['linker_individual_review'], 'Selection and the individual-review request survive the same native recovery.' );
		$this->assertArrayNotHasKey( 'linker_proof', $recovered );
		FormRecovery::save( 'contact', $post );
		$html = ( new Form() )->render();
		$this->assertStringContainsString( 'name="linker_request_id" value="' . $post['linker_request_id'] . '"', $html );
		$this->assertStringContainsString( esc_textarea( $post['message'] ), $html );
		if ( $included ) {
			$this->assertStringContainsString( ' checked /><span>', $html );
		} else {
			$this->assertStringNotContainsString( 'name="' . SelectionContext::FIELD . '"', $html );
			$this->assertStringNotContainsString( 'Owned search needle', $html );
		}
		$this->assertSame( array(), FormRecovery::consume( 'contact' ) );
	}
}
