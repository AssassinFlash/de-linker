<?php
/**
 * Local-only real HTTP timing fixture; its model boundary sleeps, never calls AI.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use Linker\Commerce\Inquiry\Assessment\Queue;
use Linker\Commerce\Inquiry\Assessment\Result;
use Linker\Commerce\Mail\TestMode;
use Linker\Commerce\Mail\Throttle;

if ( ! defined( 'LINKER_ASSESSMENT_HTTP_FIXTURE' ) ) {
	return;
}

/** Installed temporarily by AssessmentAsyncTest into its own local instance. */
final class AssessmentHttpFixture {
	/** The global AS runner is deliberately unavailable in these real HTTP requests. */
	public static function register(): void {
		if ( 'local' !== wp_get_environment_type() ) {
			return;
		}
		add_filter( 'action_scheduler_allow_async_request_runner', '__return_false' );
		add_filter( 'pre_http_request', array( self::class, 'provider' ), 10, 3 );
		add_action( 'wp_ajax_nopriv_linker_assessment_fixture', array( self::class, 'submit' ) );
		add_action( 'wp_ajax_linker_assessment_fixture', array( self::class, 'submit' ) );
	}

	/** Customer-equivalent save/defer over HTTP, with no customer mail. */
	public static function submit(): void {
		// phpcs:disable WordPress.Security.NonceVerification -- A per-test random capability, available only on the isolated local fixture, authorizes this test endpoint.
		$secret = isset( $_POST['fixture'] ) && is_string( $_POST['fixture'] ) ? sanitize_text_field( wp_unslash( $_POST['fixture'] ) ) : '';
		$tag    = isset( $_POST['tag'] ) && is_string( $_POST['tag'] ) ? sanitize_key( $_POST['tag'] ) : '';
		$delay  = isset( $_POST['delay'] ) ? absint( $_POST['delay'] ) : 0;
		// phpcs:enable
		if ( ! hash_equals( (string) constant( 'LINKER_ASSESSMENT_HTTP_FIXTURE' ), $secret ) || '' === $tag || ! in_array( $delay, array( 2, 8 ), true ) ) {
			wp_die( '', '', array( 'response' => 403 ) );
		}
		update_option( Queue::HEARTBEAT, microtime( true ), false );
		( new TestMode() )->enable( 'tester246@example.test' );
		update_option( Throttle::OPTION, array_fill( 0, Throttle::PER_MINUTE, time() ), false );
		$order = wc_create_order();
		if ( ! $order instanceof \WC_Order ) {
			wp_die( '', '', array( 'response' => 500 ) );
		}
		$order->set_billing_email( 'tester246@example.test' );
		$order->set_customer_note( 'assessment-fixture:' . $delay . ':' . $tag );
		$order->update_meta_data( '_linker_inquiry_source', 'contact' );
		Queue::prepare( $order );
		$order->save();
		add_option( 'linker_assessment_fixture_order_' . $tag, $order->get_id(), '', false );
		$defer_at = microtime( true );
		Queue::defer( $order );
		wp_send_json(
			array(
				'id'            => $order->get_id(),
				'defer_at'      => $defer_at,
				'responding_at' => microtime( true ),
			)
		);
	}

	/**
	 * Actual background PHP request sleeps at the service boundary.
	 *
	 * @param mixed                $pre Previous response.
	 * @param array<string, mixed> $args HTTP arguments.
	 * @param string               $url Destination.
	 * @return mixed Local simulated response or unchanged previous result.
	 */
	public static function provider( mixed $pre, array $args, string $url ): mixed {
		if ( ! str_ends_with( $url, '/inquiries/assess' ) ) {
			return $pre;
		}
		$body = json_decode( (string) ( $args['body'] ?? '' ), true );
		$text = $body['state']['submission']['message'] ?? '';
		if ( ! is_string( $text ) || 1 !== preg_match( '/\Aassessment-fixture:(2|8):([a-z0-9]+)\z/D', $text, $match ) ) {
			return new \WP_Error( 'fixture_unexpected_provider' );
		}
		$delay = (int) $match[1];
		$key   = 'linker_assessment_fixture_' . $match[2];
		$event = array(
			'started_at' => microtime( true ),
			'pid'        => getmypid(),
			'remaining'  => $body['remaining_seconds'] ?? null,
		);
		add_option( $key, $event, '', false );
		usleep( $delay * 1000000 );
		$event['completed_at'] = microtime( true );
		update_option( $key, $event, false );
		$result = array(
			'label'   => 'normal',
			'basis'   => 'business_request',
			'reason'  => 'classified',
			'model'   => Result::MODEL,
			'rubric'  => Result::RUBRIC,
			'seconds' => (float) $delay,
			'raw'     => array(
				'classification' => array(
					'type'   => 'choice',
					'choice' => 'normal',
				),
				'basis'          => array(
					'type'   => 'choice',
					'choice' => 'business_request',
				),
			),
		);
		return array(
			'response' => array( 'code' => 200 ),
			'body'     => wp_json_encode( $result ),
		);
	}
}

add_action( 'plugins_loaded', array( AssessmentHttpFixture::class, 'register' ) );
