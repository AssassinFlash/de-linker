<?php
/**
 * One failed Genie turn and the customer's explicit Try again.
 *
 * The journal, the receipt store and the proxy callback are the real ones; the
 * service is this fixture's transport, so an answer arrives only when the
 * callback is actually dispatched.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

// phpcs:disable WordPress.PHP.DiscouragedPHPFunctions.runtime_configuration_putenv -- Isolated local-only private-mode fixtures restore every value.

namespace Linker\Tools\Tests\Integration;

use Linker\Commerce\Protection\Allowance;
use Linker\Commerce\Protection\Identity;
use Linker\Commerce\Protection\Ledger;
use Linker\Commerce\Protection\Proof;
use Linker\Tools\Genie\Conversations;
use Linker\Tools\Genie\Proxy;
use Linker\Tools\Genie\Thread;
use Linker\Tools\Protection\Replies;
use Linker\Tools\Protection\Resources;
use PHPUnit\Framework\TestCase;
use WP_REST_Request;
use WP_REST_Response;

/**
 * A turn the service never answered is not a stored result.
 *
 * @coversNothing
 */
final class GenieTurnRetryTest extends TestCase {
	/** The trusted marker a native callback sets when nothing was stored. */
	private const OUTCOME_HEADER = 'X-Linker-Resource-Outcome';

	/**
	 * Saved local journal.
	 *
	 * @var mixed
	 */
	private mixed $old;
	/**
	 * Saved private environment, no credentials.
	 *
	 * @var array<string,string|false>
	 */
	private array $environment = array();
	/**
	 * Native cookies.
	 *
	 * @var array<string,mixed>
	 */
	private array $cookies = array();
	/**
	 * Local synthetic conversations removed after each fixture.
	 *
	 * @var list<int>
	 */
	private array $created_conversations = array();
	/**
	 * Saved Genie address option.
	 *
	 * @var mixed
	 */
	private mixed $genie_url;
	/**
	 * Answers one service call: an int refuses like an unreachable service,
	 * a string is the SSE body.
	 *
	 * @var \Closure(): (string|int)
	 */
	private \Closure $service;
	/**
	 * Dispatches this fixture observed reaching the service.
	 *
	 * @var int
	 */
	private int $dispatched = 0;

	/** Isolate the journal and the synthetic service. */
	protected function setUp(): void {
		$this->old = get_option( Ledger::OPTION );
		delete_option( Ledger::OPTION );
		$this->genie_url = get_option( Proxy::OPTION );
		update_option( Proxy::OPTION, 'http://127.0.0.1:9' );
		$this->cookies               = $_COOKIE;
		$_COOKIE[ Identity::COOKIE ] = str_repeat( 'b', 32 );
		wp_set_current_user( 0 );
		$this->dispatched = 0;
		$this->service    = static fn (): int => 502;
		foreach ( array(
			'LINKER_PUBLIC_PROTECTION_MODE' => 'enforce',
			'LINKER_TURNSTILE_SITE_KEY'     => '1x00000000000000000000AA',
			'LINKER_TURNSTILE_SECRET_KEY'   => '1x0000000000000000000000000000000AA',
			'LINKER_TURNSTILE_HOSTNAME'     => '127.0.0.1',
		) as $key => $value ) {
			$this->environment[ $key ] = getenv( $key );
			putenv( $key . '=' . $value );
		}
	}

	/** Restore the local fixture without touching real service settings. */
	protected function tearDown(): void {
		delete_option( Ledger::OPTION );
		if ( false !== $this->old ) {
			update_option( Ledger::OPTION, $this->old, false );
		}
		if ( false === $this->genie_url ) {
			delete_option( Proxy::OPTION );
		} else {
			update_option( Proxy::OPTION, $this->genie_url );
		}
		foreach ( $this->environment as $key => $value ) {
			putenv( false === $value ? $key : $key . '=' . $value );
		}
		foreach ( $this->created_conversations as $conversation ) {
			wp_delete_post( $conversation, true );
		}
		$_COOKIE = $this->cookies;
		foreach ( get_posts(
			array(
				'post_type'      => Replies::TYPE,
				'post_status'    => 'any',
				'fields'         => 'ids',
				'posts_per_page' => -1,
			)
		) as $id ) {
			wp_delete_post( (int) $id, true );
		}
	}

	/**
	 * Mint the trusted synthetic verification parent; no Cloudflare request.
	 *
	 * @param string $action Exact native scope.
	 */
	private function proof( string $action ): string {
		$identity = Identity::current();
		$this->assertInstanceOf( Identity::class, $identity );
		$id     = wp_generate_uuid4();
		$ledger = new Ledger();
		$fp     = hash( 'sha256', $id );
		$this->assertIsArray( $ledger->reserve( $id, $fp, array( new Allowance( 'fixture_verify', 'site', 1000, DAY_IN_SECONDS ) ), 90, array(), 'verification_' . $action, $identity->binding() ) );
		$this->assertIsArray( $ledger->dispatch( $id, $fp ) );
		$this->assertIsArray( $ledger->complete( $id, $fp, 1 ) );
		return ( new Proof() )->issue( 'verified', $action, $identity, $id );
	}

	/**
	 * One native turn, one stable logical UUID.
	 *
	 * @param array<string,mixed> $input Synthetic turn fields.
	 * @param string              $operation The logical operation this request repeats.
	 */
	private function request( array $input, string $operation = '' ): WP_REST_Request {
		$request = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
		$request->set_header( 'Content-Type', 'application/json' );
		$request->set_header( 'X-Linker-Operation', '' === $operation ? wp_generate_uuid4() : $operation );
		$request->set_header( 'X-Linker-Proof', $this->proof( 'genie' ) );
		$request->set_body( (string) wp_json_encode( $input ) );
		$request->set_param( 'locale', $input['locale'] );
		$request->set_param( 'messages', $input['messages'] );
		$request->set_param( 'page', $input['page'] );
		return $request;
	}

	/**
	 * One conversation of this fixture, without the real cookie transport.
	 */
	private function conversation(): int {
		global $wp_filter;
		$held = array();
		foreach ( array( Conversations::COOKIE_ACTION, Conversations::BROWSER_ACTION ) as $hook ) {
			$held[ $hook ] = isset( $wp_filter[ $hook ] ) ? clone $wp_filter[ $hook ] : null;
			remove_all_actions( $hook );
		}
		try {
			$conversation                  = ( new Conversations() )->open();
			$this->created_conversations[] = $conversation;
			return $conversation;
		} finally {
			foreach ( $held as $hook => $callbacks ) {
				if ( null === $callbacks ) {
					unset( $wp_filter[ $hook ] );
				} else {
					$wp_filter[ $hook ] = $callbacks; } // phpcs:ignore WordPress.WP.GlobalVariablesOverride.Prohibited -- Restore this fixture's held cookie hooks.
			}
		}
	}

	/**
	 * The real proxy, whose transport is this fixture's service.
	 *
	 * @return array{callback: \Closure(): mixed}
	 */
	private function handler(): array {
		return array(
			'callback' => function () {
				++$this->dispatched;
				$service = $this->service;
				// The proxy's transport seam: (url, body, headers) -> SSE body or status.
				$transport = static function ( string $url, array $body, array $headers ) use ( $service ): string|int {
					unset( $url, $body, $headers );
					return $service();
				};
				$proxy = new Proxy( new Conversations(), $transport, token: 'synthetic-local-only' );
				$turn  = new WP_REST_Request( 'POST', '/linker-ai/v1/genie/turn' );
				$turn->set_param(
					'messages',
					array(
						array(
							'role'    => 'user',
							'content' => 'Which hybrid inverter fits this house?',
						),
					)
				);
				$turn->set_param( 'locale', 'en' );
				$turn->set_param(
					'page',
					array(
						'type' => 'home',
						'url'  => 'https://example.test/',
					)
				);
				$reply = $proxy->turn( $turn );
				return $reply instanceof WP_REST_Response ? $reply : rest_convert_error_to_response( $reply );
			},
		);
	}

	/**
	 * What the browser received, as the browser sees it.
	 *
	 * @param mixed $reply The dispatch result.
	 * @return array<string,mixed>
	 */
	private function body( mixed $reply ): array {
		$this->assertInstanceOf( WP_REST_Response::class, $reply );
		$data = $reply->get_data();
		return is_array( $data ) ? $data : array();
	}

	/**
	 * A deterministic failure is followed by exactly one new dispatch.
	 */
	public function test_a_turn_the_service_never_answered_is_dispatched_once_more(): void {
		$conversation = $this->conversation();
		$input        = array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'Which hybrid inverter fits this house?',
				),
			),
			'page'     => array(
				'type' => 'home',
				'url'  => 'https://example.test/',
			),
		);
		$first        = $this->request( $input );
		$operation    = (string) $first->get_header( 'X-Linker-Operation' );
		$resources    = new Resources();
		$handler      = $this->handler();

		$refused = $resources->dispatch( null, $first, '', $handler );
		$this->assertSame( 502, $refused->get_status() );
		$this->assertSame( 'linker_genie_upstream', $this->body( $refused )['code'] ?? '' );
		$this->assertSame( 'failed', $refused->get_headers()[ self::OUTCOME_HEADER ] ?? null, 'The proxy names the turn as unrecorded.' );
		$this->assertSame( 1, $this->dispatched );
		$this->assertSame( '', ( new Thread() )->read( $conversation )['stream'], 'A refused turn stores no answer.' );

		// Try again: the same logical operation, and the service now answers.
		$this->service = static fn (): string => "event: block\ndata: {\"type\":\"text\",\"text\":\"A hybrid inverter covers that.\",\"refs\":[]}\n\nevent: done\ndata: {\"ok\":true}\n\n";
		$retried       = $resources->dispatch( null, $this->request( $input, $operation ), '', $handler );
		$this->assertInstanceOf( WP_REST_Response::class, $retried );
		$this->assertSame( 200, $retried->get_status() );
		$this->assertSame( 2, $this->dispatched, 'The retry reaches the service once.' );
		$this->assertStringContainsString( 'A hybrid inverter covers that.', (string) ( $this->body( $retried )['stream'] ?? '' ) );
		$this->assertNotSame( '', ( new Thread() )->read( $conversation )['stream'], 'The answered turn is stored.' );
	}

	/**
	 * Repeated explicit retries each reach the service while it keeps failing.
	 */
	public function test_repeated_retries_never_replay_a_refusal(): void {
		$conversation = $this->conversation();
		$input        = array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'Which hybrid inverter fits this house?',
				),
			),
			'page'     => array(
				'type' => 'home',
				'url'  => 'https://example.test/',
			),
		);
		$first        = $this->request( $input );
		$operation    = (string) $first->get_header( 'X-Linker-Operation' );
		$resources    = new Resources();
		$handler      = $this->handler();

		$refused = $resources->dispatch( null, $first, '', $handler );
		$this->assertSame( 502, $refused->get_status() );
		$this->assertSame( 'failed', $refused->get_headers()[ self::OUTCOME_HEADER ] ?? null );

		$second = $resources->dispatch( null, $this->request( $input, $operation ), '', $handler );
		$this->assertSame( 502, $second->get_status() );
		$this->assertSame( 2, $this->dispatched, 'The second Try again is a new dispatch.' );

		$this->service = static fn (): string => "event: block\ndata: {\"type\":\"text\",\"text\":\"A hybrid inverter covers that.\",\"refs\":[]}\n\nevent: done\ndata: {\"ok\":true}\n\n";
		$third         = $resources->dispatch( null, $this->request( $input, $operation ), '', $handler );
		$this->assertSame( 200, $third->get_status(), 'A later Try again still gets a new dispatch.' );
		$this->assertSame( 3, $this->dispatched );
		$this->assertStringContainsString( 'A hybrid inverter covers that.', (string) ( $this->body( $third )['stream'] ?? '' ) );
		$this->assertNotSame( '', ( new Thread() )->read( $conversation )['stream'] );
	}

	/**
	 * A stored answer is replayed, and the service is not asked a second time.
	 */
	public function test_a_stored_answer_is_replayed_without_another_dispatch(): void {
		$conversation  = $this->conversation();
		$input         = array(
			'locale'   => 'en',
			'messages' => array(
				array(
					'role'    => 'user',
					'content' => 'Which hybrid inverter fits this house?',
				),
			),
			'page'     => array(
				'type' => 'home',
				'url'  => 'https://example.test/',
			),
		);
		$first         = $this->request( $input );
		$operation     = (string) $first->get_header( 'X-Linker-Operation' );
		$resources     = new Resources();
		$handler       = $this->handler();
		$this->service = static fn (): string => "event: block\ndata: {\"type\":\"text\",\"text\":\"A hybrid inverter covers that.\",\"refs\":[]}\n\nevent: done\ndata: {\"ok\":true}\n\n";

		$answered = $resources->dispatch( null, $first, '', $handler );
		$this->assertSame( 200, $answered->get_status() );
		$this->assertArrayNotHasKey( self::OUTCOME_HEADER, $answered->get_headers(), 'An answered turn carries no retry marker.' );
		$stored = ( new Thread() )->read( $conversation )['stream'];

		$replayed = $resources->dispatch( null, $this->request( $input, $operation ), '', $handler );
		$this->assertSame( 200, $replayed->get_status() );
		$this->assertSame( 1, $this->dispatched, 'The stored answer is restored, not produced again.' );
		$this->assertSame( $this->body( $answered ), $this->body( $replayed ) );
		$this->assertSame( $stored, ( new Thread() )->read( $conversation )['stream'], 'The conversation keeps one turn.' );
	}
}
