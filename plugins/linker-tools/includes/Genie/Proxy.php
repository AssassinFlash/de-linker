<?php
/**
 * REST proxy from the browser to the Genie service.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/**
 * POST linker-ai/v1/genie/turn streams the service's SSE. Locale, page
 * context and conversation_id are filled here; the browser does not
 * pick them (docs/specs/13-genie.md).
 *
 * GET linker-ai/v1/genie/conversation reads the conversation back, so a
 * reload restores the thread instead of starting over (Thread).
 */
class Proxy {

	/**
	 * REST namespace and route.
	 */
	public const NAMESPACE = 'linker-ai/v1';
	public const ROUTE     = '/genie/turn';

	/**
	 * Route that reads the stored thread back.
	 */
	public const THREAD_ROUTE = '/genie/conversation';

	/**
	 * Route that lists the visitor's conversations, and selects one.
	 *
	 * GET returns the history rail. POST `{id}` makes that conversation
	 * the current one, so the dock and the workspace read the same thread.
	 * POST without an id opens a new conversation.
	 */
	public const CONVERSATIONS_ROUTE = '/genie/conversations';

	/**
	 * Option that holds the Genie service URL (`just serve` writes it).
	 */
	public const OPTION = 'linker_genie_url';

	/**
	 * Sets up the proxy.
	 *
	 * @param Conversations                                                        $conversations Conversation posts.
	 * @param callable( string, array<string, mixed> ): (string|int|WP_Error)|null $fetch         Optional HTTP client for tests: a body string (turn), an int status (vote), or WP_Error.
	 * @param Thread|null                                                          $thread        Conversation store; a default one is built when omitted.
	 * @param UserContext|null                                                     $user_context  Identity handed to the service; a default one is built when omitted.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private $fetch = null,
		?Thread $thread = null,
		?UserContext $user_context = null
	) {
		$this->thread       = $thread ?? new Thread();
		$this->user_context = $user_context ?? new UserContext();
	}

	/**
	 * The conversation store.
	 *
	 * @var Thread
	 */
	private readonly Thread $thread;

	/**
	 * The customer-identity seam.
	 *
	 * @var UserContext
	 */
	private readonly UserContext $user_context;

	/**
	 * Registers the routes; runs on rest_api_init.
	 */
	public function register(): void {
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE,
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'turn' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'messages' => array(
						'type'     => 'array',
						'required' => true,
					),
					'locale'   => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
					'page'     => array(
						'type' => 'object',
					),
				),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/(?P<id>[\d]+)/vote',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'vote' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'id'   => array(
						'type'              => 'integer',
						'required'          => true,
						'sanitize_callback' => 'absint',
					),
					'vote' => array(
						'type'     => 'integer',
						'required' => true,
						'enum'     => array( 1, -1 ),
					),
				),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::THREAD_ROUTE,
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'conversation' ),
					'permission_callback' => '__return_true',
				)
			);
		register_rest_route(
			self::NAMESPACE,
			self::CONVERSATIONS_ROUTE,
			array(
				array(
					'methods'             => 'GET',
					'callback'            => array( $this, 'conversations' ),
					'permission_callback' => '__return_true',
				),
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, 'select_conversation' ),
					'permission_callback' => '__return_true',
					'args'                => array(
						'id' => array(
							'type'              => 'integer',
							'required'          => false,
							'sanitize_callback' => 'absint',
						),
					),
				),
			)
		);
	}

	/**
	 * The stored thread of this request's conversation, empty when there is none.
	 *
	 * Read-only by design: a request without a conversation gets an empty
	 * answer, never a new conversation post (`Conversations::existing_id`).
	 *
	 * @return WP_REST_Response
	 */
	public function conversation(): WP_REST_Response {
		$id    = $this->conversations->existing_id();
		$store = $this->thread->read( $id );
		$reply = new WP_REST_Response(
			array(
				'conversation_id' => $id,
				'messages'        => $store['messages'],
				'stream'          => $store['stream'],
			)
		);
		// The answer depends on the visitor's cookie: it must never be reused
		// from a cache. Without this a browser that read the thread once (empty,
		// before the first turn) serves that empty copy to the reload, and the
		// conversation looks lost (measured 2026-10-11).
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * The conversations this visitor may continue.
	 *
	 * Read-only: an empty list is an empty list, never a new conversation.
	 *
	 * @return WP_REST_Response
	 */
	public function conversations(): WP_REST_Response {
		$reply = new WP_REST_Response(
			array(
				'current_id'    => $this->conversations->existing_id(),
				'conversations' => $this->conversations->list_for_visitor(),
			)
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * Continues one conversation, or opens a new one.
	 *
	 * The cookie is what the next turn and the thread read use, so this
	 * is the switch the dock and the workspace share. An id the visitor
	 * may not use is a 404, not a new conversation.
	 *
	 * @param WP_REST_Request $request Request; `id` selects, its absence opens.
	 * @return WP_REST_Response|WP_Error
	 */
	public function select_conversation( WP_REST_Request $request ) {
		$id = (int) $request->get_param( 'id' );
		if ( $id > 0 ) {
			if ( ! $this->conversations->activate( $id ) ) {
				return new WP_Error( 'linker_genie_conversation', 'Unknown conversation.', array( 'status' => 404 ) );
			}
		} else {
			$id = $this->conversations->open();
			if ( $id < 1 ) {
				return new WP_Error( 'linker_genie_conversation', 'Could not open a conversation.', array( 'status' => 500 ) );
			}
		}
		$reply = new WP_REST_Response(
			array(
				'conversation_id' => $id,
				'conversations'   => $this->conversations->list_for_visitor(),
			)
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * Forwards one turn to the service and streams SSE back.
	 *
	 * @param WP_REST_Request $request Request.
	 * @return WP_REST_Response|WP_Error
	 */
	public function turn( WP_REST_Request $request ) {
		$base = (string) get_option( self::OPTION, '' );
		if ( '' === $base ) {
			return new WP_Error( 'linker_genie_unconfigured', 'Genie is not configured.', array( 'status' => 503 ) );
		}
		$conversation = $this->conversations->current_id();
		if ( $conversation < 1 ) {
			return new WP_Error( 'linker_genie_conversation', 'Could not open a conversation.', array( 'status' => 500 ) );
		}
		$locale = $this->locale( $request->get_param( 'locale' ) );
		$page   = $request->get_param( 'page' );
		$body   = array(
			'conversation_id' => (string) $conversation,
			'messages'        => $request->get_param( 'messages' ),
			'locale'          => $locale,
			'page_context'    => is_array( $page ) ? $page : array( 'type' => 'other' ),
			// `partner` is deliberately absent: this shell cannot know the
			// customer's partner status, and a fake value would lie to the
			// service. `context` is the signed-in customer's short-lived
			// token, so the service can ask about *their* inquiries without
			// holding a WordPress session (UserContext).
			'user'            => array(
				'logged_in' => is_user_logged_in(),
				'context'   => $this->user_context->mint(),
			),
		);
		$stream = $this->post( rtrim( $base, '/' ) . '/assistant/turn', $body );
		if ( is_wp_error( $stream ) ) {
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		// An answered turn is the conversation's record: the thread the
		// browser sent plus the answer, kept so a reload restores both.
		// The first customer message names the conversation, which is
		// the only title the history rail has.
		$messages = is_array( $body['messages'] ) ? $body['messages'] : array();
		$first    = $messages[0] ?? null;
		if ( is_array( $first ) && isset( $first['content'] ) ) {
			$this->conversations->title_from_first_message(
				$conversation,
				mb_substr( trim( (string) $first['content'] ), 0, 80 )
			);
		}
		$this->thread->record(
			$conversation,
			$messages,
			(string) $stream
		);
		return new WP_REST_Response(
			array(
				'conversation_id' => $conversation,
				'stream'          => $stream,
			)
		);
	}

	/**
	 * Forwards one customer vote to the service's log of the same turn.
	 *
	 * @param WP_REST_Request $request Request with `id` and `vote`.
	 * @return WP_REST_Response|WP_Error
	 */
	public function vote( WP_REST_Request $request ) {
		$base = (string) get_option( self::OPTION, '' );
		if ( '' === $base ) {
			return new WP_Error( 'linker_genie_unconfigured', 'Genie is not configured.', array( 'status' => 503 ) );
		}
		$id   = (int) $request->get_param( 'id' );
		$body = array( 'vote' => (int) $request->get_param( 'vote' ) );
		$code = $this->post_status( rtrim( $base, '/' ) . "/turn/{$id}/vote", $body );
		if ( 404 === $code ) {
			return new WP_Error( 'linker_genie_turn', 'Unknown turn.', array( 'status' => 404 ) );
		}
		if ( $code >= 400 ) {
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		return new WP_REST_Response( array( 'ok' => true ) );
	}

	/**
	 * `en` or `de`.
	 *
	 * @param mixed $locale Requested locale.
	 * @return 'en'|'de'
	 */
	private function locale( mixed $locale ): string {
		if ( is_string( $locale ) && str_starts_with( strtolower( $locale ), 'de' ) ) {
			return 'de';
		}
		return 'en';
	}

	/**
	 * POST JSON to the service; returns the raw body (SSE text).
	 *
	 * @param string               $url  Service URL.
	 * @param array<string, mixed> $body Request body.
	 * @return string|WP_Error
	 */
	private function post( string $url, array $body ) {
		if ( is_callable( $this->fetch ) ) {
			// A turn answers with its body string; anything else (the vote
			// test contract's int status) is no stream and maps to 502.
			$answer = ( $this->fetch )( $url, $body );
			if ( is_string( $answer ) ) {
				return $answer;
			}
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		$response = wp_remote_post(
			$url,
			array(
				'headers' => array(
					'Content-Type' => 'application/json',
					'Accept'       => 'text/event-stream',
				),
				'body'    => (string) wp_json_encode( $body ),
				// Sixty seconds: one turn makes at most four ability calls
				// (each capped at twenty seconds in the service) plus the
				// model's own latency, so the browser's single request must
				// outlast the worst legitimate turn.
				'timeout' => 60.0,
			)
		);
		if ( is_wp_error( $response ) ) {
			return $response;
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		if ( $code >= 400 ) {
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		return (string) wp_remote_retrieve_body( $response );
	}

	/**
	 * POST JSON to the service; returns only the response status code.
	 *
	 * @param string               $url  Service URL.
	 * @param array<string, mixed> $body Request body.
	 * @return int The status code; 502 when the service could not be reached.
	 */
	private function post_status( string $url, array $body ): int {
		if ( is_callable( $this->fetch ) ) {
			// Test contract: the fetch double answers WP_Error, or an int
			// status code, or a body string (which means 200).
			$answer = ( $this->fetch )( $url, $body );
			if ( is_wp_error( $answer ) ) {
				return 502;
			}
			return is_int( $answer ) ? $answer : 200;
		}
		$response = wp_remote_post(
			$url,
			array(
				'headers' => array( 'Content-Type' => 'application/json' ),
				'body'    => (string) wp_json_encode( $body ),
				'timeout' => 60.0,
			)
		);
		if ( is_wp_error( $response ) ) {
			return 502;
		}
		return (int) wp_remote_retrieve_response_code( $response );
	}
}
