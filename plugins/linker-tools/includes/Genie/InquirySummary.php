<?php
/**
 * The conversation summary an inquiry carries (#244, docs/specs/13-genie.md).
 *
 * A customer who talked with Genie and then sends an inquiry does not repeat the
 * quantities, conditions and note given in the conversation: this class builds one
 * checked summary of the thread, the inquiry stores it, and the team reads it in
 * the inquiry screen and the new-inquiry mail. The model is deepseek-flash on the
 * official API only (AGENTS.md §5), reached through the Genie service's `/summary`
 * route (services/genie/src/linker_genie/summary.py), which checks the answer:
 * the shape, no price or currency, every figure said in the conversation, and
 * each quantity naming a product of the conversation.
 *
 * Nothing here may hold up an inquiry: a missing service, a refused answer or a
 * timeout falls back to a summary assembled by rule from the customer's own
 * sentences, and the reason is recorded with it. The browser's conversation is
 * the cookie-bound one (Conversations::current_id), never an id from the form.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use Closure;
use WP_Error;

/**
 * Builds, checks and caches the inquiry summary of one conversation.
 */
final class InquirySummary {

	/**
	 * Filter linker-commerce asks with (Inquiry\Sender): answers the summary
	 * array, or null when the visitor has no conversation to summarize.
	 */
	public const FILTER = 'linker_genie_inquiry_summary';

	/**
	 * Order meta the summary array is stored under (read by the new-inquiry
	 * mail and the inquiry screen).
	 */
	public const META = '_linker_genie_summary';

	/**
	 * The service's summary route (services/genie/src/linker_genie/app.py).
	 */
	public const ROUTE = '/summary';

	/**
	 * The shell's service token, the names Proxy uses (#236): literals, so this
	 * class carries the header whether or not that token exists in this plugin.
	 */
	private const TOKEN_CONSTANT = 'LINKER_GENIE_SERVICE_TOKEN';
	private const TOKEN_HEADER   = 'X-Linker-Service-Token';

	/**
	 * Seconds one summary may take: the service's own budget (summary.py
	 * TIMEOUT_SECONDS) plus one round trip. The request page waits for it once;
	 * a slower answer falls back to the rule-based summary.
	 */
	private const TIMEOUT = 10.0;

	/**
	 * How long the answer is reused: the form's render and the submit of the
	 * same visit ask twice, and the conversation cannot have changed between.
	 */
	private const CACHE_TTL = 600;

	/**
	 * The bounds of the stored summary, the service's own (summary.py MAX_*):
	 * what the browser's request schema accepts.
	 */
	private const MAX_SUMMARY    = 800;
	private const MAX_CONDITION  = 120;
	private const MAX_NOTE       = 500;
	private const MAX_CONDITIONS = 6;
	private const MAX_QUANTITIES = 12;
	private const MAX_PRODUCTS   = 40;

	/**
	 * Sets up the summary builder.
	 *
	 * @param Conversations $conversations The browser's conversation.
	 * @param Thread        $thread        Its stored messages and products.
	 * @param Closure|null  $fetch         Test seam: fn(string $url, array $body): array|WP_Error.
	 */
	public function __construct(
		private readonly Conversations $conversations,
		private readonly Thread $thread,
		private readonly ?Closure $fetch = null
	) {}

	/**
	 * Answers Inquiry\Sender's filter.
	 */
	public function register(): void {
		add_filter( self::FILTER, array( $this, 'answer' ), 10, 2 );
	}

	/**
	 * The summary of the visitor's conversation, or null when there is none.
	 *
	 * @param mixed $value        Value passed through the filter.
	 * @param int   $conversation 0 asks for the browser's current conversation.
	 * @return array<string, mixed>|null
	 */
	public function answer( $value, int $conversation = 0 ): ?array {
		$id = $conversation > 0 ? $conversation : $this->conversations->current_id();
		return $this->for_conversation( $id );
	}

	/**
	 * Builds (or reuses) the summary of one conversation.
	 *
	 * @param int $conversation Conversation post ID.
	 * @return array<string, mixed>|null
	 */
	public function for_conversation( int $conversation ): ?array {
		if ( $conversation < 1 ) {
			return null;
		}
		$messages = $this->thread->transcript( $conversation );
		if ( array() === $messages ) {
			return null;
		}
		$last = (string) $messages[ array_key_last( $messages ) ]['content'];
		// The language is part of the key: the summary is written in the
		// language of the page that asked (#250 shows the same conversation's
		// card on an English and a German page).
		$lang = str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en';
		$key  = 'linker_genie_summary_' . $conversation . '_' . $lang . '_' . count( $messages ) . '_' . substr( md5( $last ), 0, 8 );
		$seen = get_transient( $key );
		if ( is_array( $seen ) ) {
			return $seen;
		}
		$summary = $this->make( $conversation, $messages );
		set_transient( $key, $summary, self::CACHE_TTL );
		return $summary;
	}

	/**
	 * The service's checked answer, or the rule-based summary with its reason.
	 *
	 * @param int                        $conversation Conversation post ID.
	 * @param list<array<string, mixed>> $messages     Thread::transcript().
	 * @return array<string, mixed>
	 */
	private function make( int $conversation, array $messages ): array {
		$locale   = str_starts_with( determine_locale(), 'de' ) ? 'de' : 'en';
		$products = $this->products( $messages );
		$url      = (string) get_option( Proxy::OPTION );
		if ( '' === $url ) {
			return $this->by_rule( $messages, 'no service url' );
		}
		$body   = array(
			'locale'   => $locale,
			'messages' => array_map(
				static fn ( array $message ): array => array(
					'role'    => (string) ( $message['role'] ?? 'user' ),
					'content' => (string) ( $message['content'] ?? '' ),
				),
				$messages
			),
			'products' => $products,
		);
		$answer = $this->post( rtrim( $url, '/' ) . self::ROUTE, $body );
		if ( $answer instanceof WP_Error ) {
			return $this->by_rule( $messages, $answer->get_error_message() );
		}
		$summary = isset( $answer['summary'] ) && is_string( $answer['summary'] ) ? trim( $answer['summary'] ) : '';
		if ( '' === $summary ) {
			return $this->by_rule( $messages, 'unreadable' );
		}
		return array(
			'summary'    => mb_substr( $summary, 0, self::MAX_SUMMARY ),
			'quantities' => $this->quantities( $answer['quantities'] ?? array() ),
			'conditions' => $this->conditions( $answer['conditions'] ?? array() ),
			'note'       => mb_substr( (string) ( $answer['note'] ?? '' ), 0, self::MAX_NOTE ),
			'source'     => 'model',
			'reason'     => null,
		);
	}

	/**
	 * The customer's own sentences, for when the service did not answer.
	 *
	 * The last five messages, newest first, as the hand-off already quotes them
	 * (ContactRequest::handoff); the note is the latest message, which is what
	 * the request form starts with.
	 *
	 * @param list<array<string, mixed>> $messages Thread::transcript().
	 * @param string                     $reason   Why the model's summary was not used.
	 * @return array<string, mixed>
	 */
	private function by_rule( array $messages, string $reason ): array {
		$said = array();
		foreach ( array_reverse( $messages ) as $message ) {
			if ( 'user' !== ( $message['role'] ?? '' ) ) {
				continue;
			}
			$content = trim( (string) ( $message['content'] ?? '' ) );
			if ( '' !== $content ) {
				$said[] = $content;
			}
			if ( count( $said ) >= 5 ) {
				break;
			}
		}
		$note = $said[0] ?? '';
		return array(
			'summary'    => mb_substr( implode( ' · ', $said ), 0, self::MAX_SUMMARY ),
			'quantities' => array(),
			'conditions' => array(),
			'note'       => mb_substr( $note, 0, self::MAX_NOTE ),
			'source'     => 'rule',
			'reason'     => $reason,
		);
	}

	/**
	 * The products the conversation's answers showed, as the service's request
	 * schema wants them (id and name, bounded).
	 *
	 * @param list<array<string, mixed>> $messages Thread::transcript().
	 * @return list<array{id: int, name: string}>
	 */
	private function products( array $messages ): array {
		$ids = array();
		foreach ( $messages as $message ) {
			foreach ( (array) ( $message['products'] ?? array() ) as $id ) {
				$id = (int) $id;
				if ( $id > 0 ) {
					$ids[ $id ] = true;
				}
			}
		}
		$out = array();
		foreach ( array_slice( array_keys( $ids ), 0, self::MAX_PRODUCTS ) as $id ) {
			$out[] = array(
				'id'   => $id,
				'name' => mb_substr( wp_strip_all_tags( (string) get_the_title( $id ) ), 0, 300 ),
			);
		}
		return $out;
	}

	/**
	 * The service's quantities, kept only in the shape the request form takes.
	 *
	 * @param mixed $raw The answer's quantities.
	 * @return list<array{product_id: int, quantity: int}>
	 */
	private function quantities( mixed $raw ): array {
		$out = array();
		foreach ( is_array( $raw ) ? $raw : array() as $line ) {
			if ( ! is_array( $line ) ) {
				continue;
			}
			$product  = (int) ( $line['product_id'] ?? 0 );
			$quantity = (int) ( $line['quantity'] ?? 0 );
			if ( $product > 0 && $quantity > 0 ) {
				$out[] = array(
					'product_id' => $product,
					'quantity'   => $quantity,
				);
			}
			if ( count( $out ) >= self::MAX_QUANTITIES ) {
				break;
			}
		}
		return $out;
	}

	/**
	 * The service's conditions, trimmed and bounded.
	 *
	 * @param mixed $raw The answer's conditions.
	 * @return list<string>
	 */
	private function conditions( mixed $raw ): array {
		$out = array();
		foreach ( is_array( $raw ) ? $raw : array() as $condition ) {
			if ( ! is_string( $condition ) ) {
				continue;
			}
			$condition = trim( $condition );
			if ( '' !== $condition ) {
				$out[] = mb_substr( $condition, 0, self::MAX_CONDITION );
			}
			if ( count( $out ) >= self::MAX_CONDITIONS ) {
				break;
			}
		}
		return $out;
	}

	/**
	 * POSTs the summary request; the shell's token rides when configured
	 * (the same constant and header Proxy sends, #236).
	 *
	 * @param string               $url  Service URL.
	 * @param array<string, mixed> $body Request body.
	 * @return array<string, mixed>|WP_Error
	 */
	private function post( string $url, array $body ): array|WP_Error {
		if ( null !== $this->fetch ) {
			$answer = ( $this->fetch )( $url, $body );
			if ( $answer instanceof WP_Error ) {
				return $answer;
			}
			return is_array( $answer ) ? $answer : new WP_Error( 'linker_genie_summary', 'no answer' );
		}
		$headers = array( 'Content-Type' => 'application/json' );
		if ( defined( self::TOKEN_CONSTANT ) && '' !== (string) constant( self::TOKEN_CONSTANT ) ) {
			$headers[ self::TOKEN_HEADER ] = (string) constant( self::TOKEN_CONSTANT );
		}
		$response = wp_remote_post(
			$url,
			array(
				'headers' => $headers,
				'body'    => (string) wp_json_encode( $body ),
				'timeout' => self::TIMEOUT,
			)
		);
		if ( is_wp_error( $response ) ) {
			return $response;
		}
		$code = (int) wp_remote_retrieve_response_code( $response );
		if ( 200 !== $code ) {
			return new WP_Error( 'linker_genie_summary', 'HTTP ' . $code );
		}
		$decoded = json_decode( (string) wp_remote_retrieve_body( $response ), true );
		return is_array( $decoded ) ? $decoded : new WP_Error( 'linker_genie_summary', 'unreadable' );
	}
}
