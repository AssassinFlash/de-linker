<?php
/** Durable content decisions and exact-message grants before either mail budget.
 *
 * @package Linker\Commerce
 */
declare( strict_types = 1 );
namespace Linker\Commerce\Inquiry\Assessment;

use Linker\Commerce\Inquiry\Emails\NewInquiryEmail;
use Linker\Commerce\Inquiry\Emails\InquiryReceivedEmail;
use Linker\Commerce\Inquiry\ReceiptLimit;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Mail\NotificationHold;
use WC_Order;
/** No model string, public flag or mail priority is a sending permission. */
final class SendAuthorization {
	public const MARKER = '_linker_inquiry_send_policy';
	/**
	 * @param int $id Native source. */
	public static function managed( int $id ): bool {
		$state = AuthorizationStore::read( $id );
		return is_array( $state ) && array() !== $state; }
	/**
	 * @param WC_Order $order Persisted native source. */
	public static function defer( WC_Order $order ): bool {
		$order->read_meta_data( true );
		if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
			return true;}
		Queue::prepare( $order );
		$order->save_meta_data();
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		if ( ! is_array( $data['snapshot'] ?? null ) ) {
			return true;}
		$ready = AuthorizationStore::edit(
			$order->get_id(),
			static function ( array &$state ) use ( $order, $data ): void {
				if ( array() !== $state ) {
					return;}
				$state = array(
					'policy'          => SendVerdict::POLICY,
					'status'          => 'pending',
					'snapshot_sha256' => self::hash( $data['snapshot'] ),
					'source_sha256'   => self::source( $order ),
					'review'          => self::review( $order ),
					'routing'         => self::routing(),
					'attempts'        => 0,
					'next_at'         => time(),
					'jobs'            => array(),
				);
			}
		);
		if ( $ready ) {
			self::recover( $order->get_id() );}
		return true;
	}
	/**
	 * @param int $id Source. Only schedules native durable work. */
	public static function recover( int $id ): void {
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}$order->read_meta_data( true );
		if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
			return;}
		$state = AuthorizationStore::read( $id );
		if ( ! is_array( $state ) ) {
			return;}
		if ( array() === $state ) {
			self::defer( $order );
			return;}
		if ( 'processing' === ( $state['status'] ?? '' ) && (float) ( $state['deadline'] ?? PHP_INT_MAX ) <= microtime( true ) ) {
			AuthorizationStore::edit(
				$id,
				static function ( array &$current ) use ( $order ): void {
					if ( 'processing' === ( $current['status'] ?? '' ) && (float) ( $current['deadline'] ?? PHP_INT_MAX ) <= microtime( true ) ) {
						self::retry( $current, $order );
					}}
			);
			$state = AuthorizationStore::read( $id );
			if ( ! is_array( $state ) ) {
				return;}
		}
		if ( 'approved' === ( $state['status'] ?? '' ) && (int) ( $state['next_at'] ?? 0 ) <= time() ) {
			self::handoff( $id );
			$state = AuthorizationStore::read( $id );
			if ( ! is_array( $state ) ) {
				return;}
		}
		if ( 'normal' === ( $state['status'] ?? '' ) ) {
			foreach ( $state['jobs'] ?? array()as$entry ) {
				$job = (int) ( $entry['id'] ?? 0 );
				if ( $job > 0 && null !== ( new JobStore() )->load( $job ) && JobStore::FAILED_STATUS !== get_post_status( $job ) ) {
					as_enqueue_async_action( Outbox::HOOK, array( $job ), Outbox::GROUP, true );
				}
			}return;}
		if ( 'pending' !== ( $state['status'] ?? '' ) ) {
			return;}
		as_schedule_single_action( max( time(), (int) ( $state['next_at'] ?? 0 ) ), Queue::PROCESS, array( $id ), Outbox::GROUP, true );
	}
	/**
	 * @param int $id Only one native background worker spends on a source at once. */
	public static function process( int $id ): void {
		$preflight = wc_get_order( $id );
		if ( ! $preflight instanceof WC_Order ) { return; }
		$preflight->read_meta_data( true );
		if ( NotificationHold::held( $preflight ) && ! self::owns_hold( $preflight ) ) { return; }
		if ( ! \Linker\Commerce\Mail\BudgetTransaction::begin() ) { return; }
		global $wpdb; $wpdb->query( 'ROLLBACK' );
		Lock::run(
			'send-process-' . $id,
			static function () use ( $id ): void {
				$input   = null;
				$claimed = AuthorizationStore::edit(
					$id,
					static function ( array &$state ) use ( $id, &$input ): void {
						$order = wc_get_order( $id );
						if ( ! $order instanceof WC_Order ) {
								return;
						}$order->read_meta_data( true );
						if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) || 'pending' !== ( $state['status'] ?? '' ) || (int) ( $state['next_at'] ?? 0 ) > time() ) {
							return;}
						if ( ! self::current( $order, $state ) ) {
							$state['status'] = 'invalidated';
							return;}
						$data     = Queue::data( $order );
						$snapshot = $data['snapshot'] ?? null;
						if ( ! is_array( $snapshot ) || self::hash( $snapshot ) !== ( $state['snapshot_sha256'] ?? '' ) ) {
							$state['status'] = 'invalidated';
							return;}
						$attempt            = (int) ( $state['attempts'] ?? 0 );
						$deadline           = 0 === $attempt ? (float) ( $data['deadline'] ?? 0 ) : microtime( true ) + Queue::WAIT_SECONDS;
						$state['attempts']  = $attempt + 1;
						$state['status']    = 'processing';
						$state['deadline']  = $deadline;
						$state['operation'] = wp_generate_uuid4();
						$input              = array(
							'snapshot'  => $snapshot,
							'deadline'  => $deadline,
							'operation' => $state['operation'],
							'binding'   => array(
								'protocol'        => SendVerdict::POLICY,
								'policy'          => SendVerdict::POLICY,
								'record_id'       => $id,
								'snapshot_sha256' => $state['snapshot_sha256'],
								'purpose'         => 'inquiry_mail',
							),
						);
					}
				);
				if ( ! $claimed || ! is_array( $input ) ) {
					return;}
				// The durable attempt is claimed before I/O; a killed worker cannot reset its retry count.
				as_schedule_single_action( (int) ceil( $input['deadline'] ), Queue::EXPIRE, array( $id ), Outbox::GROUP, true );
				$result = ( new Client() )->assess( $input['snapshot'], $input['deadline'], $input['binding'] );
				$saved  = AuthorizationStore::edit(
					$id,
					static function ( array &$state ) use ( $id, $input, $result ): void {
						if ( 'processing' !== ( $state['status'] ?? '' ) || ( $state['operation'] ?? '' ) !== $input['operation'] ) {
							return;}
						$order = wc_get_order( $id );
						if ( ! $order instanceof WC_Order ) {
							$state['status'] = 'invalidated';
							return;
						}$order->read_meta_data( true );
						if ( ! self::current( $order, $state ) || ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
							$state['status'] = 'invalidated';
							return;}
						$result           = microtime( true ) >= $input['deadline'] ? SendVerdict::unknown( 'deadline' ) : $result;
						$decision         = $result['decision'] ?? 'unknown';
						$state['verdict'] = $result;
						self::observation( $order, $result );
						if ( 'normal' === $decision ) {
							if ( self::owns_hold( $order ) ) {
								$order->delete_meta_data( NotificationHold::META );
								$order->update_meta_data( Queue::PENDING, 'yes' );
								$order->save_meta_data();}
							$state['status']  = 'approved';
							$state['next_at'] = time();
						} elseif ( 'malicious' === $decision ) {
							$state['status'] = 'quarantined';
							$order->update_meta_data( Queue::PENDING, 'quarantined' );
							$order->save_meta_data();
						} else {
							self::retry( $state, $order );}
					}
				);
				if ( ! $saved ) {
					wc_get_logger()->warning( 'Inquiry sending authorization is unavailable; native content remains pending.', array( 'source' => 'linker-inquiry-assessment' ) );}
				self::recover( $id );
			}
		);
	}
	/** Native job records and their permission become visible in the same owned transaction.
	 *
	 * @param int $id Classified native source.
	 */
	private static function handoff( int $id ): void {
		$written = AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( $id ): void {
				if ( 'approved' !== ( $state['status'] ?? '' ) ) {
					return;}
				$order = wc_get_order( $id );
				if ( ! $order instanceof WC_Order ) {
					$state['status'] = 'invalidated';
						return;
				}$order->read_meta_data( true );
				if ( ! self::current( $order, $state ) || $order->get_meta( Reviews::ERASED ) || ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) ) {
					$state['status'] = 'invalidated';
					return;}
				$state['jobs']   = self::jobs( $order, $state );
				$state['status'] = 'normal';
			},
			true
		);
		if ( ! $written ) {
			// No caller transaction is committed or rolled back; native recovery retains approval.
			AuthorizationStore::edit(
				$id,
				static function ( array &$state ): void {
					if ( 'approved' !== ( $state['status'] ?? '' ) ) {
						return;}
					$attempt                   = (int) ( $state['handoff_attempts'] ?? 0 );
					$state['handoff_attempts'] = $attempt + 1;
					$delay                     = Outbox::RETRY_DELAYS[ $attempt ] ?? null;
					$state['status']           = null === $delay ? 'manual' : 'approved';
					$state['next_at']          = null === $delay ? 0 : time() + $delay;
				}
			);
		}
	}
	/**
	 * @param array<string,mixed> $state Durable attempt.
	 * @param WC_Order            $order Native record. */
	private static function retry( array &$state, WC_Order $order ): void {
		$delay            = Outbox::RETRY_DELAYS[ max( 0, (int) $state['attempts'] - 1 ) ] ?? null;
		$state['status']  = null === $delay ? 'manual' : 'pending';
		$state['next_at'] = null === $delay ? 0 : time() + $delay;
		if ( null === $delay ) {
			$order->update_meta_data( Queue::PENDING, 'manual' );
			$order->save_meta_data();}
	}
	/** Only newly prepared native verification holds belong to this pipeline.
	 *
	 * @param WC_Order $order Native inquiry, never an existing incident record.
	 */
	private static function owns_hold( WC_Order $order ): bool {
		$hold = $order->get_meta( NotificationHold::META );
		return SendVerdict::POLICY === $order->get_meta( self::MARKER ) && $order->get_meta( \Linker\Commerce\Protection\Intake::META ) && is_array( $hold ) && 'verification_review' === ( $hold['reason'] ?? '' );
	}
	/**
	 * @param WC_Order            $order Source.
	 * @param array<string,mixed> $state Server decision. */
	private static function current( WC_Order $order, array $state ): bool {
		return SendVerdict::POLICY === ( $state['policy'] ?? '' ) && self::source( $order ) === ( $state['source_sha256'] ?? '' ) && self::review( $order ) === ( $state['review'] ?? '' ) && self::routing() === ( $state['routing'] ?? '' );}
	/**
	 * @param WC_Order $order Native business facts without unrelated browser history. */
	private static function source( WC_Order $order ): string {
		$snapshot = Snapshot::make( $order, array(), false );
		unset( $snapshot['context'] );
		return self::hash( $snapshot );}
	/**
	 * @param WC_Order $order Current staff and erasure revision. */
	private static function review( WC_Order $order ): string {
		return self::hash( array( Reviews::state( $order ), $order->get_meta( Admin::OVERRIDE ), $order->get_meta( Reviews::ERASED ) ) );}
	/** Current configuration affects native sender, real recipient and blind-copy route. */
	private static function routing(): string {
		$options = new \Linker\Commerce\Settings\Options();
		return self::hash( array( $options->notify_to(), $options->notify_bcc(), $options->notify_sender(), get_option( 'woocommerce_email_from_name' ), get_option( 'woocommerce_email_from_address' ) ) );
	}
	/**
	 * @param mixed $value Native canonical structure. */
	public static function hash( mixed $value ): string {
		$json = wp_json_encode( $value );
		return is_string( $json ) ? hash( 'sha256', $json ) : '';}
	/**
	 * @param Message $message Full arguments and actual attachment contents. */
	public static function message_hash( Message $message ): string {
		$files = array();
		foreach ( $message->attachments as $path ) {
			if ( ! is_file( $path ) || ! is_readable( $path ) ) {
				return '';
			}$digest = hash_file( 'sha256', $path );
			if ( ! is_string( $digest ) ) {
				return '';
			}$files[] = array(
				'path'   => $path,
				'sha256' => $digest,
			);}
		return self::hash( array( $message->to_array(), $files ) );
	}
	/**
	 * @param WC_Order            $order Native source.
	 * @param array<string,mixed> $result Validated response. */
	private static function observation( WC_Order $order, array $result ): void {
		$data  = Queue::data( $order );
		$label = match ( $result['decision'] ?? 'unknown' ) {
			'normal'=>'normal', 'malicious'=>'suspected_spam', default=>'uncertain'};
		$data['result']         = array_merge( $result, array( 'label' => $label ) );
		$data['initial_result'] = $data['result'];
		$data['completed_at']   = microtime( true );
		StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
	}
	/**
	 * @param WC_Order            $order Current native source.
	 * @param array<string,mixed> $state Pending grant.
	 * @return array<string,array{id:int,hash:string}> */
	private static function jobs( WC_Order $order, array $state ): array {
		if ( ! empty( $state['jobs'] ) ) { return $state['jobs']; }
		$emails = WC()->mailer()->get_emails();
		$jobs   = array();
		if ( 'assessment_pending' === $order->get_meta( ReceiptLimit::SKIPPED_META ) ) {
			$reason = 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode() ? \Linker\Commerce\Protection\ReceiptBudget::reason( $order->get_billing_email(), $order->get_id() ) : ( ( new ReceiptLimit() )->take() ? '' : 'daily_cap' );
			$order->update_meta_data( ReceiptLimit::SKIPPED_META, $reason );
			$order->save_meta_data();
		}
		foreach ( array(
			'team'    => NewInquiryEmail::class,
			'receipt' => InquiryReceivedEmail::class,
		)as$purpose => $class ) {
			if ( 'receipt' === $purpose && '' !== $order->get_meta( ReceiptLimit::SKIPPED_META ) ) {
				continue;}
			$email = $emails[ $class ] ?? null;
			if ( ! $email instanceof NewInquiryEmail && ! $email instanceof InquiryReceivedEmail ) {
				throw new \RuntimeException( 'authorization_email_unavailable' );}
			$captured = $email->capture( $order );
			if ( null === $captured ) {
				continue;}
			$message = new Message(
				$captured->to,
				$captured->subject,
				$captured->body,
				$captured->headers,
				$captured->attachments,
				false,
				Message::STANDARD,
				array(
					'kind'    => 'inquiry',
					'record'  => $order->get_id(),
					'purpose' => $purpose,
				)
			);
			$hash    = self::message_hash( $message );
			if ( '' === $hash ) {
				throw new \RuntimeException( 'authorization_message_unavailable' );}
			$job    = ( new JobStore() )->create( $message, $order->get_id() );
			$stored = $job > 0 ? ( new JobStore() )->load( $job ) : null;
			if ( null === $stored || $stored['message']->to_array() !== $message->to_array() ) {
				throw new \RuntimeException( 'authorization_job_unconfirmed' );}
			$jobs[ $purpose ] = array(
				'id'   => $job,
				'hash' => $hash,
			);
		}
		return $jobs;
	}
	/** Always called before transport selection and every SMTP/PHP budget debit.
	 *
	 * @phpstan-impure
	 *
	 * @param Message $message Frozen send arguments.
	 * @param int     $job Native job.
	 */
	public static function allows( Message $message, int $job ): bool {
		$origin = $message->origin;
		// A bound content job cannot turn itself into a security transaction by editing JSON.
		if ( $job > 0 && NotificationHold::inquiry( $job ) > 0 && 'inquiry' !== ( $origin['kind'] ?? '' ) ) {
			return false;}
		if ( $job > 0 && get_post_meta( $job, ConversationAuthorization::SOURCE, true ) && 'conversation' !== ( $origin['kind'] ?? '' ) ) {
			return false;}
		if ( 'conversation' === ( $origin['kind'] ?? '' ) ) {
			return ConversationAuthorization::allows( $message, $job );}
		if ( 'transaction' === ( $origin['kind'] ?? '' ) || 'security' === ( $origin['kind'] ?? '' ) ) {
			return \Linker\Commerce\Mail\NativeOrigin::valid( $message );}
		if ( 'inquiry' !== ( $origin['kind'] ?? '' ) || $job < 1 ) {
			return false;}
		$id      = $origin['record'] ?? 0;
		$purpose = $origin['purpose'] ?? '';
		if ( ! is_int( $id ) || $id < 1 || ! in_array( $purpose, array( 'team', 'receipt' ), true ) || NotificationHold::inquiry( $job ) !== $id ) {
			return false;}
		$order = wc_get_order( $id );
		if ( ! $order instanceof WC_Order ) {
			return false;
		}$order->read_meta_data( true );
		if ( NotificationHold::held( $order ) || $order->get_meta( Reviews::ERASED ) ) {
			return false;}
		$state = AuthorizationStore::read( $id );
		return is_array( $state ) && 'normal' === ( $state['status'] ?? '' ) && self::current( $order, $state ) && ( $state['jobs'][ $purpose ]['id'] ?? 0 ) === $job && '' !== self::message_hash( $message ) && ( $state['jobs'][ $purpose ]['hash'] ?? '' ) === self::message_hash( $message );
	}
	/** Persist physical success separately from a missing native job.
	 * @param Message $message Actual sent frozen arguments.
	 * @param int $job Original durable job.
	 */
	public static function delivered( Message $message, int $job ): void {
		if ( 'conversation' === ( $message->origin['kind'] ?? '' ) ) {
			AuthorizationStore::edit( 'conversation-' . $job, static function ( array &$state ) use ( $message ): void { if ( ( $state['message_sha256'] ?? '' ) === self::message_hash( $message ) ) { $state['status'] = 'delivered'; $state['delivered_at'] = time(); } } );
			return;
		}
		if ( 'inquiry' !== ( $message->origin['kind'] ?? '' ) ) { return; }
		$id = (int)( $message->origin['record'] ?? 0 ); $purpose = $message->origin['purpose'] ?? '';
		AuthorizationStore::edit( $id, static function ( array &$state ) use ( $message, $purpose, $job ): void { if ( ( $state['jobs'][$purpose]['id'] ?? 0 ) === $job && ( $state['jobs'][$purpose]['hash'] ?? '' ) === self::message_hash( $message ) ) { $state['jobs'][$purpose]['delivered_at'] = time(); } } );
	}

	/** Current native content is part of the staff form's optimistic version.
	 * @param WC_Order $order Displayed native source.
	 */
	public static function reference( WC_Order $order ): string { return self::source( $order ); }

	/** The existing capability/nonce/version checked staff event is not a browser permit.
	 * @param int $id Native inquiry.
	 * @param string $operation Saved native audit action.
	 * @param string $label Saved staff decision.
	 */
	public static function reviewed( int $id, string $operation, string $label ): void {
		if ( ! current_user_can( 'manage_woocommerce' ) || ! self::managed( $id ) ) { return; }
		AuthorizationStore::edit( $id, static function ( array &$state ) use ( $id, $operation, $label ): void {
			$order = wc_get_order( $id ); if ( ! $order instanceof WC_Order ) { return; } $order->read_meta_data( true );
			if ( $order->get_meta( Reviews::ERASED ) || ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || self::source( $order ) !== ( $state['source_sha256'] ?? '' ) ) { return; }
			$state['review'] = self::review( $order );
			if ( 'evidence' === $operation ) { return; }
			if ( 'withdraw' === $operation ) { $state['status']='pending';$state['attempts']=0;$state['next_at']=time(); }
			elseif ( 'normal' === $label ) { $state['status']=empty($state['jobs'])?'approved':'normal';$state['next_at']=time(); }
			else { $state['status']='suspected_spam'===$label?'quarantined':'manual'; }
			$order->update_meta_data( Queue::PENDING, in_array( $state['status'], array( 'pending','normal','approved' ), true )?'yes':$state['status'] );$order->save_meta_data();
		} );
		self::recover( $id );
	}

	/** Erasure revokes before deleting queued copies; a late worker cannot resurrect them.
	 * @param WC_Order $order Native privacy-authorized order.
	 * @throws \RuntimeException On an unconfirmed revocation or content removal.
	 */
	public static function erase( WC_Order $order ): void {
		$id=$order->get_id();$state=AuthorizationStore::read($id);if(!is_array($state)){throw new \RuntimeException('authorization_erasure_unavailable');}if(array()===$state){return;}
		$jobs=$state['jobs']??array();
		if(!AuthorizationStore::edit($id,static function(array &$state):void{$state['status']='erased';$state['verdict']=SendVerdict::unknown('erased');})){throw new \RuntimeException('authorization_erasure_unavailable');}
		foreach($jobs as $entry){$job=(int)($entry['id']??0);if($job>0){delete_post_meta($job,'_linker_mail_message');wp_cache_delete($job,'post_meta');if(metadata_exists('post',$job,'_linker_mail_message')){throw new \RuntimeException('authorization_mail_erasure_unavailable');}}}
		$order->read_meta_data(true);$data=Queue::data($order);unset($data['snapshot']);$data['result']=Result::unknown('erased');$data['initial_result']=$data['result'];StructuredMeta::update($order,Queue::META,$data);$order->update_meta_data(Queue::PENDING,'erased');$order->save_meta_data();
	}

}
