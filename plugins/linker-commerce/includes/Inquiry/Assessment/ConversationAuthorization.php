<?php
/** Frozen conversation mail uses its own source, purpose and durable native job.
 *
 * @package Linker\Commerce
 */
declare(strict_types=1);
namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Genie\Conversation;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
/** No browser session is required after a native confirmed guest capability. */
final class ConversationAuthorization {
	public const PROCESS = 'linker_conversation_mail_assess';
	public const PENDING = '_linker_conversation_mail_pending';
	public const SOURCE  = '_linker_conversation_mail_source';
	/**
	 * @param int          $id Trusted conversation.
	 * @param array<mixed> $messages Native full messages.
	 * @param Conversation $conversation Validated rendered source.
	 * @param Message      $captured Actual native email.
	 * @return bool|array{status:string} */
	public static function enqueue( int $id, array $messages, Conversation $conversation, Message $captured ): bool|array {
		$source = array(
			'conversation_id'   => $id,
			'messages'          => $messages,
			'to'                => $conversation->to,
			'locale'            => $conversation->locale,
			'rendered_messages' => $conversation->messages,
		);
		if ( ! self::current( $source ) ) {
			return false;}
		$message = new Message(
			$captured->to,
			$captured->subject,
			$captured->body,
			$captured->headers,
			$captured->attachments,
			false,
			Message::STANDARD,
			array(
				'kind'    => 'conversation',
				'record'  => $id,
				'purpose' => 'conversation_mail',
			)
		);
		$key     = 'conversation-source-' . SendAuthorization::hash( $source );
		$answer  = false;
		$saved   = AuthorizationStore::edit(
			$key,
			static function ( array &$state ) use ( $source, $message, &$answer ): void {
				$job = (int) ( $state['job'] ?? 0 );
				if ( $job > 0 ) {
					$old = ( new JobStore() )->load( $job );
					$decision = AuthorizationStore::read( 'conversation-' . $job );
					$status = is_array( $decision ) ? ( $decision['status'] ?? '' ) : '';
					$answer = 'delivered' === $status ? true : ( null !== $old && in_array( $status, array( '', 'pending', 'processing', 'normal' ), true ) ? array( 'status' => 'pending' ) : false );
					return;}
				$job = ( new JobStore() )->create( $message );
				if ( $job < 1 ) {
					return;}
				$encoded = wp_json_encode( $source );
				if ( ! is_string( $encoded ) ) {
					return;}
				update_post_meta( $job, self::SOURCE, wp_slash( $encoded ) );
				update_post_meta( $job, self::PENDING, 'yes' );
				wp_cache_delete( $job, 'post_meta' );
				if ( get_post_meta( $job, self::SOURCE, true ) !== $encoded || 'yes' !== get_post_meta( $job, self::PENDING, true ) ) {
					return;}
				$state  = array( 'job' => $job );
				$answer = array( 'status' => 'pending' );
			}
		);
		if ( ! $saved || false === $answer ) {
			return false;}
		$state = AuthorizationStore::read( $key );
		$job   = is_array( $state ) ? (int) ( $state['job'] ?? 0 ) : 0;
		if ( $job > 0 && null !== ( new JobStore() )->load( $job ) ) {
			self::recover_job( $job );}
		return $answer;
	}
	/**
	 * @param array<string,mixed> $source Frozen native source. */
	private static function current( array $source ): bool {
		/**
		* @since 0.1.0
		* @param bool $current Default-deny authoritative native thread check.
		* @param int $id Native conversation.
		* @param array<mixed> $messages Exact frozen raw transcript. */
		return true === apply_filters( 'linker_commerce_conversation_mail_source_current', false, (int) ( $source['conversation_id'] ?? 0 ), $source['messages'] ?? array() );
	}
	/**
	 * @param int $job Private immutable content job.
	 * @return array<string,mixed>|null */
	private static function source( int $job ): ?array {
		wp_cache_delete( $job, 'post_meta' );
		$raw    = get_post_meta( $job, self::SOURCE, true );
		$source = is_string( $raw ) ? json_decode( $raw, true ) : null;
		return is_array( $source ) ? $source : null;}
	/**
	 * @param int $job Private native job. */
	public static function recover_job( int $job ): void {
		$loaded = ( new JobStore() )->load( $job );
		$source = self::source( $job );
		if ( null === $loaded || null === $source || ! self::current( $source ) ) {
			return;}
		$key = 'conversation-' . $job;
		AuthorizationStore::edit(
			$key,
			static function ( array &$state ) use ( $job, $source, $loaded ): void {
				if ( array() === $state ) {
					$state = array(
						'policy'          => SendVerdict::POLICY,
						'status'          => 'pending',
						'attempts'        => 0,
						'next_at'         => time(),
						'snapshot_sha256' => SendAuthorization::hash( $source ),
						'message_sha256'  => SendAuthorization::message_hash( $loaded['message'] ),
					);}
				if ( 'processing' === ( $state['status'] ?? '' ) && (float) ( $state['deadline'] ?? PHP_INT_MAX ) <= microtime( true ) ) {
					self::retry( $state );}
			}
		);
		$state = AuthorizationStore::read( $key );
		if ( ! is_array( $state ) ) {
			return;}
		if ( 'normal' === ( $state['status'] ?? '' ) ) {
			as_enqueue_async_action( Outbox::HOOK, array( $job ), Outbox::GROUP, true );
		} elseif ( 'pending' === ( $state['status'] ?? '' ) ) {
			as_schedule_single_action( max( time(), (int) $state['next_at'] ), self::PROCESS, array( $job ), Outbox::GROUP, true );}
	}
	/**
	 * @param int $job Only native background callbacks classify a persisted source. */
	public function process( int $job ): void {
		Lock::run(
			'conversation-mail-' . $job,
			static function () use ( $job ): void {
				$input   = null;
				$key     = 'conversation-' . $job;
				$claimed = AuthorizationStore::edit(
					$key,
					static function ( array &$state ) use ( $job, &$input ): void {
						$source = self::source( $job );
						$loaded = ( new JobStore() )->load( $job );
						if ( null === $source || null === $loaded || ! self::current( $source ) || 'pending' !== ( $state['status'] ?? '' ) || (int) ( $state['next_at'] ?? 0 ) > time() ) {
							return;}
						if ( SendAuthorization::hash( $source ) !== ( $state['snapshot_sha256'] ?? '' ) || SendAuthorization::message_hash( $loaded['message'] ) !== ( $state['message_sha256'] ?? '' ) ) {
							$state['status'] = 'invalidated';
							return;}
						$state['status']    = 'processing';
						$state['attempts']  = (int) $state['attempts'] + 1;
						$state['deadline']  = microtime( true ) + Queue::WAIT_SECONDS;
						$state['operation'] = wp_generate_uuid4();
						$input              = array(
							'source'    => $source,
							'deadline'  => $state['deadline'],
							'operation' => $state['operation'],
							'binding'   => array(
								'protocol'        => SendVerdict::POLICY,
								'policy'          => SendVerdict::POLICY,
								'record_id'       => $job,
								'snapshot_sha256' => $state['snapshot_sha256'],
								'purpose'         => 'conversation_mail',
							),
						);
					}
				);
				if ( ! $claimed || ! is_array( $input ) ) {
					return;}
				$verdict = ( new Client() )->assess( $input['source'], $input['deadline'], $input['binding'] );
				AuthorizationStore::edit(
					$key,
					static function ( array &$state ) use ( $input, $verdict, $job ): void {
						if ( 'processing' !== ( $state['status'] ?? '' ) || ( $state['operation'] ?? '' ) !== $input['operation'] ) {
							return;}
						$source = self::source( $job );
						$loaded = ( new JobStore() )->load( $job );
						if ( null === $source || null === $loaded || ! self::current( $source ) || SendAuthorization::hash( $source ) !== ( $state['snapshot_sha256'] ?? '' ) || SendAuthorization::message_hash( $loaded['message'] ) !== ( $state['message_sha256'] ?? '' ) ) {
							$state['status'] = 'invalidated';
							return;}
						$verdict          = microtime( true ) >= $input['deadline'] ? SendVerdict::unknown( 'deadline' ) : $verdict;
						$state['verdict'] = $verdict;
						$decision         = $verdict['decision'] ?? 'unknown';
						if ( 'normal' === $decision ) {
							$state['status'] = 'normal';
						} elseif ( 'malicious' === $decision ) {
								$state['status'] = 'quarantined';
										update_post_meta( $job, self::PENDING, 'quarantined' );
						} else {
							self::retry( $state );
							if ( 'manual' === $state['status'] ) {
									update_post_meta( $job, self::PENDING, 'manual' );}
						}
					}
				);
				self::recover_job( $job );
			}
		);
	}
	/**
	 * @param array<string,mixed> $state Durable count; reuse the existing bounded mail recovery intervals. */
	private static function retry( array &$state ): void {
		$delay            = Outbox::RETRY_DELAYS[ max( 0, (int) $state['attempts'] - 1 ) ] ?? null;
		$state['status']  = null === $delay ? 'manual' : 'pending';
		$state['next_at'] = null === $delay ? 0 : time() + $delay;}
	/**
	 * @param Message $message Actual frozen send.
	 * @param int     $job Private native source. */
	public static function allows( Message $message, int $job ): bool {
		if ( $job < 1 || \Linker\Commerce\Mail\NotificationHold::job_held( $job ) ) {
			return false;}
		$source = self::source( $job );
		$state  = AuthorizationStore::read( 'conversation-' . $job );
		return null !== $source && self::current( $source ) && is_array( $state ) && SendVerdict::POLICY === ( $state['policy'] ?? '' ) && 'normal' === ( $state['status'] ?? '' ) && 'conversation_mail' === ( $message->origin['purpose'] ?? '' ) && ( $message->origin['record'] ?? 0 ) === ( $source['conversation_id'] ?? null ) && SendAuthorization::hash( $source ) === ( $state['snapshot_sha256'] ?? '' ) && '' !== SendAuthorization::message_hash( $message ) && SendAuthorization::message_hash( $message ) === ( $state['message_sha256'] ?? '' );
	}
	/** Independent native heartbeat recovers persisted private jobs. */
	public function recover(): void {
		foreach ( get_posts(
			array(
				'post_type'   => JobStore::POST_TYPE,
				'post_status' => 'private',
				'numberposts' => -1,
				'fields'      => 'ids',
				'meta_key'    => self::PENDING,
				'meta_value'  => 'yes',
			)
		)as$job ) {
			self::recover_job( (int) $job );}}
	/** Native handlers only; no new public endpoint. */
	public function register(): void {
		add_action( self::PROCESS, array( $this, 'process' ) );
		add_action( RecoverySchedule::HOOK, array( $this, 'recover' ) );}
}
