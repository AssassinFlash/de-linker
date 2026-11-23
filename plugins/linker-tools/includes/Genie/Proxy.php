<?php
/**
 * REST proxy from the browser to the Genie service.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Protection\Identity;
use Linker\Tools\Protection\Replies;
use Linker\Tools\Protection\Resources;
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
	 * POST without an id opens a new conversation. `/<id>` with DELETE
	 * clears one; `/<id>/email` with POST sends it to the visitor.
	 */
	public const CONVERSATIONS_ROUTE = '/genie/conversations';

	/**
	 * Option that holds the Genie service URL (`just serve` writes it).
	 */
	public const OPTION = 'linker_genie_url';

	/**
	 * The wp-config.php constant that holds the token this site and its Genie
	 * service share (#236, review round 1 of PR #309, item 5): the service's
	 * endpoints are reachable from the Hostinger host's shared outgoing
	 * address, so each call carries it (services/genie gate.py). Without the
	 * constant Genie is not configured.
	 */
	public const TOKEN_CONSTANT = 'LINKER_GENIE_SERVICE_TOKEN';

	/**
	 * The header the token travels in (not Authorization: Bearer, which
	 * LiveCanvas reads as a JWT on this site's own REST requests).
	 */
	public const TOKEN_HEADER = 'X-Linker-Service-Token';

	/**
	 * Seconds for the native HTTP operation and its remaining commit-lock wait.
	 *
	 * Protection\Resources reserves the existing 90-second operation window.
	 * The service keeps its existing model, tool and price limits; fresh Woo
	 * publication checks surround that work and add transport time. Giving
	 * this outer HTTP call the former 60-second limit cut off a valid answer
	 * before SSE release during the 2026-10-24 public withdrawal check.
	 * The commit lock receives only the unused remainder of this window.
	 */
	public const TURN_BUDGET = 90;

	/**
	 * Sets up the proxy.
	 *
	 * @param Conversations                                                                               $conversations Conversation posts.
	 * @param callable( string, array<string, mixed>, array<string, string> ): (string|int|WP_Error)|null $fetch Optional HTTP client for tests (URL, body, headers): a body string (turn), an int status (vote), or WP_Error.
	 * @param Thread|null                                                                                 $thread        Conversation store; a default one is built when omitted.
	 * @param UserContext|null                                                                            $user_context  Identity handed to the service; a default one is built when omitted.
	 * @param PageContext|null                                                                            $pages         The page a turn comes from; a default one is built when omitted.
	 * @param ConversationMail|null                                                                       $mail          Sends a conversation to the visitor; a default one is built when omitted.
	 * @param Attachments|null                                                                            $attachments   Checks a turn's files; a default one is built when omitted.
	 * @param string|null                                                                                 $token         The shared service token; read from TOKEN_CONSTANT when null (tests pass one).
	 * @param PublicationGuard|null                                                                       $publication Current publication source.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private $fetch = null,
		?Thread $thread = null,
		?UserContext $user_context = null,
		?PageContext $pages = null,
		?ConversationMail $mail = null,
		?Attachments $attachments = null,
		?string $token = null,
		?PublicationGuard $publication = null
	) {
		$this->thread       = $thread ?? new Thread();
		$this->user_context = $user_context ?? new UserContext();
		$this->pages        = $pages ?? new PageContext();
		$this->mail         = $mail ?? new ConversationMail( $conversations, $this->thread );
		$this->attachments  = $attachments ?? new Attachments();
		$this->publication  = $publication ?? new PublicationGuard();
		$this->token        = $token ?? ( defined( self::TOKEN_CONSTANT ) ? (string) constant( self::TOKEN_CONSTANT ) : '' );
	}

	/**
	 * Current publication permission at preparation and release.
	 *
	 * @var PublicationGuard
	 */
	private readonly PublicationGuard $publication;

	/**
	 * The shared service token; '' when the site has none.
	 *
	 * @var string
	 */
	private readonly string $token;

	/** Service start duration for the current short REST request.
	 *
	 * @var float|null
	 */
	private ?float $service_start_ms = null;

	/**
	 * Checks a turn's files (#236).
	 *
	 * @var Attachments
	 */
	private readonly Attachments $attachments;

	/**
	 * The page-context seam (ticket #234).
	 *
	 * @var PageContext
	 */
	private readonly PageContext $pages;

	/**
	 * Sends a conversation to the visitor's own address.
	 *
	 * @var ConversationMail
	 */
	private readonly ConversationMail $mail;

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
		( new DraftActions() )->register();
		add_filter( 'linker_tools_restored_reply', array( PublicationGuard::class, 'restored' ), 10, 2 );
		add_filter( 'linker_tools_restored_reply', array( \Linker\Tools\Planner\GenieSources::class, 'replayed' ), 11, 2 );
		add_filter( 'rest_post_dispatch', array( $this, 'turn_headers' ), 99, 3 );
		$turn_args = array(
			'messages'    => array(
				'type'     => 'array',
				'required' => true,
			),
			'locale'      => array(
				'type' => 'string',
				'enum' => array( 'en', 'de' ),
			),
			'page'        => array(
				'type' => 'object',
			),
			// The turn's files, apart from its messages (#236): checked
			// by Attachments, sent once, never stored.
			'attachments' => array(
				'type' => 'array',
			),
		);
		foreach ( array(
			self::ROUTE            => 'turn',
			self::ROUTE . '/start' => 'start',
		) as $path => $callback ) {
			register_rest_route(
				self::NAMESPACE,
				$path,
				array(
					'methods'             => 'POST',
					'callback'            => array( $this, $callback ),
					'permission_callback' => '__return_true',
					'args'                => $turn_args,
				)
			);
		}
		register_rest_route(
			self::NAMESPACE,
			self::ROUTE . '/(?P<job_id>[a-f0-9-]{36})',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'poll' ),
				'permission_callback' => '__return_true',
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
		register_rest_route(
			self::NAMESPACE,
			self::CONVERSATIONS_ROUTE . '/(?P<id>[\d]+)',
			array(
				'methods'             => 'DELETE',
				'callback'            => array( $this, 'delete_conversation' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'id' => array(
						'type'              => 'integer',
						'required'          => true,
						'sanitize_callback' => 'absint',
					),
				),
			)
		);
		register_rest_route(
			self::NAMESPACE,
			self::CONVERSATIONS_ROUTE . '/(?P<id>[\d]+)/email',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'email_conversation' ),
				'permission_callback' => '__return_true',
				'args'                => array(
					'id'      => array(
						'type'              => 'integer',
						'required'          => true,
						'sanitize_callback' => 'absint',
					),
					// Checked by ConversationMail, so a bad address is the
					// route's own 400 with its own code.
					'email'   => array(
						'type'     => 'string',
						'required' => false,
					),
					'locale'  => array(
						'type' => 'string',
						'enum' => array( 'en', 'de' ),
					),
					// The guest form's hidden field.
					'website' => array(
						'type'     => 'string',
						'required' => false,
					),
				),
			)
		);
	}

	/**
	 * Clears one of the visitor's conversations and answers the list
	 * without it. An id the visitor may not use is a 404.
	 *
	 * @param WP_REST_Request $request Request with `id`.
	 * @return WP_REST_Response|WP_Error
	 */
	public function delete_conversation( WP_REST_Request $request ) {
		if ( ! $this->conversations->delete( (int) $request->get_param( 'id' ) ) ) {
			return new WP_Error( 'linker_genie_conversation', 'Unknown conversation.', array( 'status' => 404 ) );
		}
		return $this->conversations();
	}

	/**
	 * Sends one conversation to the visitor's own address.
	 *
	 * @param WP_REST_Request $request Request with `id`, `email` (a guest's) and `locale`.
	 * @return WP_REST_Response|WP_Error
	 */
	public function email_conversation( WP_REST_Request $request ) {
		$url     = $request->get_url_params();
		$outcome = $this->mail->send(
			(int) ( $url['id'] ?? 0 ),
			(string) $request->get_param( 'email' ),
			$this->locale( $request->get_param( 'locale' ) ),
			array(
				'website' => (string) $request->get_param( 'website' ),

			)
		);
		$http = ConversationMail::HTTP[ $outcome['status'] ] ?? 503;
		if ( $http >= 400 ) {
			return new WP_Error(
				'linker_genie_email_' . $outcome['status'],
				'The conversation was not sent.',
				array( 'status' => $http )
			);
		}
		// The address goes back to the visitor who sent it: a signed-in
		// customer sees which of their addresses the account used, a guest
		// where the confirmation link went.
		$reply = new WP_REST_Response(
			array(
				'status' => $outcome['status'],
				'to'     => $outcome['to'],
			),
			$http
		);
		$reply->header( 'Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0' );
		return $reply;
	}

	/**
	 * The stored thread of this request's conversation, empty when there is none.
	 *
	 * Read-only by design: a request without a conversation gets an empty
	 * answer, never a new conversation post (`Conversations::existing_id`).
	 *
	 * @param WP_REST_Request|null $request Current native owner proof for stored source cards.
	 * @return WP_REST_Response
	 */
	public function conversation( ?WP_REST_Request $request = null ): WP_REST_Response {
		$id              = $this->conversations->existing_id();
		$store           = $this->thread->read( $id );
		$source          = new \Linker\Tools\Planner\GenieSources();
		$owner_request   = $request ?? new WP_REST_Request( 'GET' );
		$locale          = 'de' === $request?->get_param( 'locale' ) ? 'de' : 'en';
		$store['stream'] = $source->restore( PublicationGuard::history_prices( $store['stream'] ), $owner_request, $locale );
		foreach ( $store['messages'] as $index => $message ) {
			if ( is_array( $message['planning_sources'] ?? null ) ) {
				$store['messages'][ $index ]['planning_sources'] = $source->restore_block( $message['planning_sources'], $owner_request, $locale );
			}
		}
		$pending = $this->pending_view( $id );
		$reply   = new WP_REST_Response(
			array(
				'conversation_id' => $id,
				...( array() !== $pending ? array( 'pending_job' => $pending ) : array() ),
				'messages'        => $store['messages'],
				'stream'          => $store['stream'],
				...( isset( $store['operation_id'] ) && Resources::completed_genie_operation( $store['operation_id'], $store['operation_fingerprint'] ?? '' ) ? array( 'operation_id' => $store['operation_id'] ) : array() ),
				// The sent contact cards, each after the answer that showed
				// it: history keeps them on a reload (#243).
				'contacts'        => ContactRequest::cards( $id ),
				// The inquiries sent from the confirmation card (#250).
				'inquiries'       => InquiryRequest::cards( $id ),
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
		} elseif ( ! is_user_logged_in() ) {
			$this->conversations->start_guest_conversation();
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
		return $this->begin( $request, false );
	}

	/** Start an asynchronous turn using the native request contract.
	 *
	 * @param WP_REST_Request $request Turn request.
	 */
	public function start( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		return $this->begin( $request, true );
	}

	/** Never cache a private job response, including native REST errors. Measure the PHP request separately from network latency.
	 *
	 * @param WP_REST_Response $response Native response.
	 * @param \WP_REST_Server  $server REST server.
	 * @param WP_REST_Request  $request Native request.
	 */
	public function turn_headers( WP_REST_Response $response, $server, WP_REST_Request $request ): WP_REST_Response {
		unset( $server );
		$route = strtolower( $request->get_route() );
		$base  = '/' . self::NAMESPACE . self::ROUTE;
		if ( $route === $base || $route === $base . '/start' || ( str_starts_with( $route, $base . '/' ) && wp_is_uuid( substr( $route, strlen( $base ) + 1 ), 4 ) ) ) {
			$response->header( 'Cache-Control', 'private, no-store, no-cache, must-revalidate, max-age=0' );
			if ( isset( $_SERVER['REQUEST_TIME_FLOAT'] ) ) {
				$timing = 'php;dur=' . number_format( ( microtime( true ) - (float) $_SERVER['REQUEST_TIME_FLOAT'] ) * 1000, 2, '.', '' );
				if ( $route === $base . '/start' && null !== $this->service_start_ms ) {
					$timing                .= ', genie;dur=' . number_format( $this->service_start_ms, 1, '.', '' );
					$this->service_start_ms = null;
				}
				$response->header( 'Server-Timing', $timing );
			}
		}
		return $response;
	}

	/** Prepare the shared turn input for either service endpoint.
	 *
	 * @param WP_REST_Request $request Frontend turn.
	 * @param bool            $async Whether to return the service job immediately.
	 */
	private function begin( WP_REST_Request $request, bool $async ): WP_REST_Response|WP_Error {
		$base = $this->base();
		if ( '' === $base ) {
			return self::unrecorded( new WP_Error( 'linker_genie_unconfigured', 'Genie is not configured.', array( 'status' => 503 ) ) );
		}
		// The files are checked before anything else happens, so a refused
		// upload opens no conversation and reaches no service.
		$files = $this->attachments->check( $request->get_param( 'attachments' ) );
		if ( is_wp_error( $files ) ) {
			return self::unrecorded( $files );
		}
		$conversation = $this->conversations->begin_turn();
		if ( $conversation < 1 ) {
			return self::unrecorded( new WP_Error( 'linker_genie_conversation', 'Could not open a conversation.', array( 'status' => 500 ) ) );
		}
		try {
			$reply = $this->answer( $request, $base, $files, $conversation, $async );
			return $reply;
		} finally {
			if ( ! isset( $reply ) || ! $reply instanceof WP_REST_Response || 202 !== $reply->get_status() ) {
				$this->conversations->discard_unanswered_guest();
			}
		}
	}

	/** Send and record one native conversation turn.
	 *
	 * @param WP_REST_Request           $request Native turn.
	 * @param string                    $base Private transport base.
	 * @param list<array<string,mixed>> $files Verified attachments.
	 * @param int                       $conversation Existing or provisional conversation.
	 * @param bool                      $async Release the request after the job is accepted.
	 * @return WP_Error|WP_REST_Response The recorded answer or the native refusal.
	 */
	private function answer( WP_REST_Request $request, string $base, array $files, int $conversation, bool $async ): WP_Error|WP_REST_Response {
		$locale = $this->locale( $request->get_param( 'locale' ) );
		// The page the browser names, checked key by key; the service reads
		// the page's content itself from it (#234). A solution draft's
		// products and their quantities come from the visitor's own draft,
		// never the browser (the cart line quantity the handoff already reads).
		$page = $this->pages->sanitize( $request->get_param( 'page' ) );
		if ( 'draft' === $page['type'] ) {
			$lines               = $this->pages->draft_lines();
			$page['draft_ids']   = array();
			$page['draft_lines'] = array();
			foreach ( $lines as $line ) {
				$page['draft_ids'][]   = $line['product_id'];
				$page['draft_lines'][] = $line;
			}
		}
		$partner  = PublicationGuard::sees_prices();
		$body     = array(
			'conversation_id' => (string) $conversation,
			'messages'        => $request->get_param( 'messages' ),
			'locale'          => $locale,
			'page_context'    => $page,
			// `partner` is whether this account sees prices, by the site's one
			// price rule (linker-commerce's CommerceState answers the filter;
			// without it nobody does): a signed-in pending or restricted
			// account is not a partner (#242). `context` is the signed-in
			// customer's short-lived token: the service sends it back on the
			// product abilities and the inquiry list, so they answer for this
			// customer without the service holding a WordPress session
			// (UserContext).
			'user'            => array(
				'logged_in' => is_user_logged_in(),
				'partner'   => $partner,
				'context'   => $this->user_context->mint(),
			),
		);
		$planning = ( new \Linker\Tools\Planner\GenieContext() )->read( $request, $page, $locale );
		if ( null !== $planning ) {
			$body['planning_context'] = $planning;
		}
		if ( array() !== $files ) {
			$body['attachments'] = $files;
		}
		// What earlier turns read from their files: the conversation's, never
		// the browser's (#236).
		$readings = $this->thread->readings( $conversation );
		if ( array() !== $readings ) {
			$body['readings'] = $readings;
		}
		$messages   = is_array( $body['messages'] ) ? $body['messages'] : array();
		$quantities = $this->thread->previous_card_quantities( $conversation, $messages );
		if ( array() !== $quantities ) {
			$body['previous_card_quantities'] = $quantities;
		}
		$publication = $this->publication->dependencies();
		if ( is_wp_error( $publication ) ) {
			return self::unrecorded( $publication );
		}
		$started = microtime( true );
		if ( $async ) {
			return $this->start_job( $base, $body, $publication, $started );
		}
		$stream = $this->post( $base . '/assistant/turn', $body );
		if ( is_wp_error( $stream ) ) {
			return self::unrecorded( $stream );
		}
		return $this->finish( $conversation, $messages, $stream, $publication, $locale, $started, Resources::genie_operation(), Resources::genie_fingerprint() );
	}

	/** Validate, record and release one fully checked answer.
	 *
	 * @param int                 $conversation Owned conversation.
	 * @param array<mixed>        $messages User input to commit.
	 * @param string              $stream Checked service SSE.
	 * @param array<string,mixed> $publication Dependencies from the beginning of the turn.
	 * @param string              $locale Requested language.
	 * @param float               $started Original start time.
	 * @param string              $operation Verified operation.
	 * @param string              $fingerprint Verified input.
	 */
	private function finish( int $conversation, array $messages, string $stream, array $publication, string $locale, float $started, string $operation, string $fingerprint ): WP_REST_Response|WP_Error {
		$permitted = $this->publication->validate( $publication );
		if ( is_wp_error( $permitted ) ) {
			return self::unrecorded( $permitted );
		}
		// An answered turn is the conversation's record, kept so a reload
		// restores it. A second turn that snapped the same history is
		// appended, not dropped (#373, Thread::record). The first customer
		// message names the conversation, which is the only title the
		// history rail has.
		$first = $messages[0] ?? null;
		if ( is_array( $first ) && isset( $first['content'] ) ) {
			$this->conversations->title_from_first_message(
				$conversation,
				mb_substr( trim( (string) $first['content'] ), 0, 80 )
			);
		}
		// The readings are the conversation's store (Thread::split, once per
		// turn); the browser gets what each file is, not its whole text again.
		$split = Thread::split( (string) $stream );
		// The model call already spent part of TURN_BUDGET. The lock waits
		// only for the rest, so the worst case stays one turn, not two.
		$left = (int) floor( self::TURN_BUDGET - ( microtime( true ) - $started ) );
		if ( $left < 0 ) {
			$left = 0;
		}
		if ( ! $this->thread->record( $conversation, $messages, $split['stream'], $split['readings'], $left, $operation, $fingerprint ) ) {
			// The answer was produced and is not stored. The other turn
			// stays. The shell re-reads the thread, puts the question back
			// in the field, and keeps the uploads so the customer can send
			// it again (App.tsx / Hero.tsx, the 409 path).
			return self::unrecorded(
				new WP_Error(
					'linker_genie_turn_conflict',
					'The conversation changed while Genie was answering. Send your question again.',
					array( 'status' => 409 )
				)
			);
		}
		if ( ! $this->conversations->publish_answer( $conversation ) ) {
			return self::unrecorded( new WP_Error( 'linker_genie_conversation', 'Could not open a conversation.', array( 'status' => 500 ) ) );
		}
		// Action tokens are issued only for this live checked answer; history stays unsigned.
		// The answer is already stored: these refusals are not a turn that
		// stored nothing, so they keep the reply's own status.
		$action_stream = $this->publication->release( $split['stream'], $publication, $locale );
		if ( $action_stream instanceof WP_Error ) {
			return $action_stream;
		}
		$reply = new WP_REST_Response(
			array(
				'conversation_id' => $conversation,
				'stream'          => $action_stream,
			)
		);
		$this->publication->remember( $reply, $publication );
		return $reply;
	}

	/** Start work while the native operation lock and receipt are owned by Resources.
	 *
	 * @param string              $base Service URL.
	 * @param array<string,mixed> $body Prepared input.
	 * @param array<string,mixed> $publication Current publication dependencies.
	 * @param float               $started Start of the turn budget.
	 */
	private function start_job( string $base, array $body, array $publication, float $started ): WP_REST_Response|WP_Error {
		$conversation = (int) $body['conversation_id'];
		$operation    = Resources::genie_operation();
		$receipt      = ( new Replies() )->operation( $operation );
		if ( '' === $operation || $receipt < 1 ) {
			return self::unrecorded( new WP_Error( 'linker_resource_result', 'The operation could not be confirmed.', array( 'status' => 503 ) ) );
		}
		$active = PendingTurns::current( $conversation );
		if ( $active ) {
			PendingTurns::expire( $conversation, $active['job_id'] );
			if ( PendingTurns::current( $conversation ) ) {
				return self::unrecorded( new WP_Error( 'linker_resource_pending', 'This conversation has a turn in progress.', array( 'status' => 409 ) ) );
			}
		}
		$subject = $this->resource_subject( $body );
		$job     = $this->job_request( $base . '/assistant/turn/start', $subject, $body );
		if ( is_wp_error( $job ) ) {
			return self::unrecorded( $job );
		}
		if ( ! wp_is_uuid( $job['job_id'] ?? '', 4 ) || 'running' !== ( $job['status'] ?? null ) || ! is_string( $job['stage'] ?? null ) ) {
			return self::unrecorded( self::job_error( 502 ) );
		}
		$turn = array(
			'job_id'          => $job['job_id'],
			'stage'           => $job['stage'],
			'started_at'      => $started,
			'conversation_id' => $conversation,
			'receipt'         => $receipt,
			'subject_hash'    => $subject,
			'owner_binding'   => get_post_meta( $receipt, '_linker_binding', true ),
			'operation_id'    => $operation,
			'fingerprint'     => Resources::genie_fingerprint(),
			'locale'          => $body['locale'],
			'partner'         => $body['user']['partner'],
			'messages'        => $body['messages'],
			'publication'     => $publication,
		);
		if ( ! PendingTurns::save( $turn ) ) {
			return self::unrecorded( self::job_error( 503 ) );
		}
				$this->conversations->select_pending_guest();
		return new WP_REST_Response( PendingTurns::progress( $turn ), 202 );
	}

	/** Restore only the active owner's question and progress.
	 *
	 * @param int $id Currently selected conversation.
	 * @return array<string,mixed>
	 */
	private function pending_view( int $id ): array {
		$turn = PendingTurns::current( $id );
		if ( ! $turn ) {
			return array();
		}
		if ( microtime( true ) - $turn['started_at'] >= self::TURN_BUDGET ) {
			PendingTurns::expire( $id, $turn['job_id'] );
			return array();
		}
		$identity = Identity::current();
		if ( is_wp_error( $identity ) || ! hash_equals( $turn['owner_binding'], $identity->binding() ) ) {
			return array();
		}
		$last = end( $turn['messages'] );
		return PendingTurns::progress( $turn ) + array(
			'operation_id' => $turn['operation_id'],
			'user_message' => $last['content'] ?? '',
		);
	}

	/** Read or finalize one owned service job.
	 *
	 * @param WP_REST_Request $request Native GET.
	 */
	public function poll( WP_REST_Request $request ): WP_REST_Response|WP_Error {
		$job          = (string) $request->get_url_params()['job_id'];
		$receipt      = PendingTurns::receipt( $job );
		$conversation = $receipt > 0 ? PendingTurns::conversation( $receipt, $job ) : 0;
		if ( $conversation < 1 || ! $this->conversations->may_use( $conversation ) ) {
			return self::unknown_job();
		}
		$identity = Identity::current();
		$binding  = (string) get_post_meta( $receipt, '_linker_binding', true );
		if ( is_wp_error( $identity ) || ! hash_equals( $binding, $identity->binding() ) ) {
			return self::unknown_job();
		}
		$operation = (string) get_post_field( 'post_name', $receipt );
		$turn      = PendingTurns::current( $conversation );
		if ( ( $turn['job_id'] ?? null ) !== $job ) {
			return ( new Replies() )->read( $receipt, $binding );
		}
		// A peer may already be finalizing. Return real progress and let the next poll read its receipt.
		$reply = new WP_REST_Response( PendingTurns::progress( $turn ) );
		Lock::run(
			'genie-operation-' . $operation,
			function () use ( &$reply, $job, $conversation, $receipt, $binding ): void {
				wp_cache_delete( $conversation, 'post_meta' );
				$current = PendingTurns::current( $conversation );
				$reply   = ( $current['job_id'] ?? null ) === $job ? $this->poll_owned( $current ) : ( new Replies() )->read( $receipt, $binding );
			}
		);
		return $reply;
	}

	/** Fetch current progress or finish a checked result under its operation lock.
	 *
	 * @param array<string,mixed> $turn Pending native turn.
	 */
	private function poll_owned( array $turn ): WP_REST_Response|WP_Error {
		$id        = $turn['conversation_id'];
		$recovered = PendingTurns::recover( $turn );
		if ( null !== $recovered ) {
			return is_wp_error( $recovered ) ? $recovered : ( new Replies() )->read( $turn['receipt'], $turn['owner_binding'] );
		}
		if ( microtime( true ) - $turn['started_at'] >= self::TURN_BUDGET ) {
			$result = self::job_error( 503 );
		} else {
			$result = $this->job_request( $this->base() . '/assistant/turn/' . $turn['job_id'], $turn['subject_hash'] );
		}
		if ( is_wp_error( $result ) ) {
			if ( 'linker_genie_connection' === $result->get_error_code() ) {
				return $result;
			}
			PendingTurns::fail( $turn );
			return self::unrecorded( $result );
		}
		if ( 'running' === $result['status'] && is_string( $result['stage'] ?? null ) ) {
			update_post_meta( $turn['receipt'], PendingTurns::STAGE, $result['stage'] );
			return new WP_REST_Response( PendingTurns::progress( $turn ) );
		}
		if ( 'completed' !== $result['status'] || ! is_string( $result['stream'] ?? null ) ) {
			$error = self::job_error( (int) ( $result['http_status'] ?? 502 ), (string) ( $result['code'] ?? '' ) );
			PendingTurns::fail( $turn );
			return self::unrecorded( $error );
		}
		if ( $turn['partner'] && ! PublicationGuard::sees_prices() ) {
			PendingTurns::fail( $turn );
			return self::unrecorded( PublicationGuard::refused() );
		}
		$this->conversations->resume_pending_guest( $id );
		$reply = $this->finish( $id, $turn['messages'], $result['stream'], $turn['publication'], $turn['locale'], $turn['started_at'], $turn['operation_id'], $turn['fingerprint'] );
		if ( is_wp_error( $reply ) ) {
			if ( ! empty( $reply->get_error_data()['unrecorded'] ) ) {
				PendingTurns::fail( $turn );
				return $reply;
			}
			$reply = rest_convert_error_to_response( $reply );
		} else {
			$reply->set_data(
				$reply->get_data() + array(
					'job_id' => $turn['job_id'],
					'status' => 'completed',
				)
			);
		}
		if ( ( new Replies() )->finish( $turn['receipt'], $reply ) !== $turn['receipt'] ) {
			return self::job_error( 503 );
		}
		PendingTurns::clear( $turn );
		return $reply;
	}

	/** Public error independent of whether another visitor owns the ID. */
	private static function unknown_job(): WP_Error {
		return new WP_Error( 'linker_genie_job', 'Unknown turn.', array( 'status' => 404 ) );
	}

	/** Convert the private typed service failure to the public API.
	 *
	 * @param int    $status Service status.
	 * @param string $code Service failure code.
	 */
	private static function job_error( int $status, string $code = '' ): WP_Error {
		if ( 'publication_changed' === $code || 'publication_unavailable' === $code ) {
			return PublicationGuard::refused( $status );
		}
		return new WP_Error( 429 === $status ? 'linker_genie_quota' : 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => $status ) );
	}

	/** Authenticated short service request. The browser never receives the raw upstream body.
	 *
	 * @param string                   $url Private URL.
	 * @param string                   $subject Native identity hash.
	 * @param array<string,mixed>|null $body Start payload or null for a poll.
	 * @return array<string,mixed>|WP_Error
	 */
	private function job_request( string $url, string $subject, ?array $body = null ): array|WP_Error {
		$headers = $this->headers() + array(
			'Accept'                    => 'application/json',
			'X-Linker-Resource-Subject' => $subject,
		);
		if ( is_callable( $this->fetch ) ) {
			$raw = ( $this->fetch )( $url, $body ?? array(), $headers );
		} else {
			$response = null === $body
				? wp_remote_get(
					$url,
					array(
						'headers' => $headers,
						'timeout' => 10,
					)
				)
				: wp_remote_post(
					$url,
					array(
						'headers' => $headers + array( 'Content-Type' => 'application/json' ),
						'timeout' => 15,
						'body'    => (string) wp_json_encode( $body ),
					)
				);
			if ( is_wp_error( $response ) ) {
				return new WP_Error( 'linker_genie_connection', 'Could not reach Genie.', array( 'status' => 503 ) );
			}
			if ( null !== $body ) {
				$timing = wp_remote_retrieve_header( $response, 'server-timing' );
				if ( is_string( $timing ) && preg_match( '/(?:^|,)\s*genie;dur=(\d+(?:\.\d+)?)(?=,|$)/', $timing, $duration ) ) {
					$this->service_start_ms = (float) $duration[1];
				}
			}
			$raw  = wp_remote_retrieve_body( $response );
			$code = (int) wp_remote_retrieve_response_code( $response );
			if ( $code >= 400 ) {
				$error = json_decode( $raw, true );
				return self::job_error( $code, (string) ( $error['code'] ?? ( is_string( $error['detail'] ?? null ) ? $error['detail'] : '' ) ) );
			}
		}
		$state = is_string( $raw ) ? json_decode( $raw, true ) : null;
		return is_array( $state ) && isset( $state['status'] ) ? $state : self::job_error( 502 );
	}

	/**
	 * A turn this proxy refused before it stored an answer.
	 *
	 * The conversation has no new turn, so the customer's Try again is a new
	 * attempt at the same question, never a replay of this refusal. The
	 * marker says so to the resource boundary, which otherwise treats any
	 * returned response as a completed result to hand back again (Resources).
	 * A reverse proxy's own 5xx never carries it: that refusal says nothing
	 * about whether this callback ran.
	 *
	 * @param WP_Error $error The refusal the callback would have returned.
	 */
	private static function unrecorded( WP_Error $error ): WP_Error {
		$data = $error->get_error_data();
		$data = is_array( $data ) ? $data + array( 'unrecorded' => true ) : array( 'unrecorded' => true );
		return new WP_Error( $error->get_error_code(), $error->get_error_message(), $data );
	}

	/**
	 * A conversation is being deleted (by the customer, by Retention, by
	 * staff): the reading text of its files leaves the service's turn log
	 * too (#236, review round 1 of PR #309, item 6). Hooked on
	 * `before_delete_post`, while the conversation's readings can still be
	 * read; a pending turn can still be producing its first reading. A failure
	 * is logged, never fatal to the deletion: the turn log's own retention
	 * removes the turn later.
	 *
	 * @param int $post_id The post being deleted.
	 */
	public function forget( int $post_id ): void {
		if ( Conversations::POST_TYPE !== get_post_type( $post_id ) || ( array() === $this->thread->readings( $post_id ) && ! PendingTurns::current( $post_id ) ) ) {
			return;
		}
		$base = $this->base();
		$code = '' === $base ? 503 : $this->post_status( $base . "/assistant/conversation/{$post_id}/forget", array() );
		if ( $code >= 400 && function_exists( 'wc_get_logger' ) ) {
			wc_get_logger()->error(
				sprintf( 'Genie: the file readings of conversation %d were not purged from the service turn log (status %d).', $post_id, $code ),
				array( 'source' => 'linker-genie' )
			);
		}
	}

	/**
	 * The service's address without a trailing slash; '' when Genie is not
	 * configured (no address, or no shared token, which is logged).
	 */
	private function base(): string {
		$base = rtrim( (string) get_option( self::OPTION, '' ), '/' );
		if ( '' !== $base && '' === $this->token ) {
			if ( function_exists( 'wc_get_logger' ) ) {
				wc_get_logger()->error(
					sprintf( 'Genie: %s is not defined in wp-config.php; Genie is closed.', self::TOKEN_CONSTANT ),
					array( 'source' => 'linker-genie' )
				);
			}
			return '';
		}
		return $base;
	}

	/**
	 * Forwards one customer vote to the service's log of the same turn.
	 *
	 * @param WP_REST_Request $request Request with `id` and `vote`.
	 * @return WP_REST_Response|WP_Error
	 */
	public function vote( WP_REST_Request $request ) {
		$base = $this->base();
		if ( '' === $base ) {
			return new WP_Error( 'linker_genie_unconfigured', 'Genie is not configured.', array( 'status' => 503 ) );
		}
		$id   = (int) $request->get_param( 'id' );
		$body = array( 'vote' => (int) $request->get_param( 'vote' ) );
		$code = $this->post_status( $base . "/turn/{$id}/vote", $body );
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
	 * @param float                $timeout Remaining HTTP budget in seconds.
	 * @return string|WP_Error
	 */
	private function post( string $url, array $body, float $timeout = self::TURN_BUDGET ) {
		if ( is_callable( $this->fetch ) ) {
			// A turn answers with its body string; anything else (the vote
			// test contract's int status) is no stream and maps to 502.
			$answer = ( $this->fetch )( $url, $body, $this->headers() );
			if ( is_string( $answer ) ) {
				return $answer;
			}
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		$started  = microtime( true );
		$response = wp_remote_post(
			$url,
			array(
				'headers' => array(
					'Content-Type'              => 'application/json',
					'Accept'                    => 'text/event-stream',
					self::TOKEN_HEADER          => $this->token,
					'X-Linker-Resource-Subject' => $this->resource_subject( $body ),
				),
				'body'    => (string) wp_json_encode( $body ),
				// Current Woo checks surround the service's bounded work.
				// HTTP and the later commit lock share the native operation
				// window; this does not extend model or price work limits.
				'timeout' => $timeout,
			)
		);
		if ( is_wp_error( $response ) ) {
			return $response;
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		if ( 422 === $code && isset( $body['previous_card_quantities'] ) ) {
			// A service rolled back since the stored answer may reject this field before executing the turn.
			$failure = json_decode( (string) wp_remote_retrieve_body( $response ), true );
			$errors  = $failure['detail'] ?? null;
			$left    = floor( $timeout - ( microtime( true ) - $started ) );
			if ( is_array( $errors ) && 1 === count( $errors ) && 'extra_forbidden' === ( $errors[0]['type'] ?? null ) &&
				array( 'body', 'previous_card_quantities' ) === ( $errors[0]['loc'] ?? null ) && $left >= 1 ) {
				unset( $body['previous_card_quantities'] );
				return $this->post( $url, $body, $left );
			}
		}
		if ( in_array( $code, array( 409, 503 ), true ) ) {
			$failure  = json_decode( (string) wp_remote_retrieve_body( $response ), true );
			$expected = 409 === $code ? 'publication_changed' : 'publication_unavailable';
			if ( is_array( $failure ) && isset( $failure['detail'] ) && $failure['detail'] === $expected ) {
				return PublicationGuard::refused( $code );
			}
		}
		if ( in_array( $code, array( 429, 503 ), true ) ) {
			$failure = json_decode( (string) wp_remote_retrieve_body( $response ), true );
			if ( is_array( $failure ) && ( str_starts_with( (string) ( $failure['code'] ?? '' ), 'provider_budget_' ) || str_starts_with( (string) ( $failure['code'] ?? '' ), 'genie_resource_' ) ) ) {
				return new WP_Error( 'linker_genie_quota', __( 'Genie is temporarily unavailable. Your message is still here. You can send an inquiry to our team.', 'linker-tools' ), array( 'status' => $code ) );
			}
		}
		if ( $code >= 400 ) {
			return new WP_Error( 'linker_genie_upstream', 'Genie did not answer.', array( 'status' => 502 ) );
		}
		return (string) wp_remote_retrieve_body( $response );
	}

	/**
	 * Server-selected stable subject for actual service work, across conversations.
	 *
	 * @param array<string,mixed> $body Native validated turn, never an arbitrary URL.
	 */
	private function resource_subject( array $body ): string {
		if ( class_exists( \Linker\Commerce\Protection\Identity::class ) ) {
			$identity = \Linker\Commerce\Protection\Identity::current();
			if ( ! is_wp_error( $identity ) ) {
				return '' !== $identity->account ? $identity->account : $identity->browser;
			}
		}
		// Off/observe must retain native behavior if a new cookie cannot be
		// issued. Enforce already established stable identity before callback.
		return hash( 'sha256', 'native-genie-conversation|' . (string) ( $body['conversation_id'] ?? '' ) );
	}

	/**
	 * The headers every call to the service carries besides its type.
	 *
	 * @return array<string, string>
	 */
	private function headers(): array {
		return array( self::TOKEN_HEADER => $this->token );
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
			$answer = ( $this->fetch )( $url, $body, $this->headers() );
			if ( is_wp_error( $answer ) ) {
				return 502;
			}
			return is_int( $answer ) ? $answer : 200;
		}
		$response = wp_remote_post(
			$url,
			array(
				'headers' => array(
					'Content-Type'     => 'application/json',
					self::TOKEN_HEADER => $this->token,
				),
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
