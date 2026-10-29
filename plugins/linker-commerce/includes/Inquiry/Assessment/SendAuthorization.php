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
	/** Native source.
	 *
	 * @param int $id Native source.
	 */
	public static function managed( int $id ): bool {
		$state = AuthorizationStore::read( $id );
		return is_array( $state ) && array() !== $state;
	}
	/** Persisted native source.
	 *
	 * @param WC_Order $order Persisted native source.
	 */
	public static function defer( WC_Order $order ): bool {
		$order->read_meta_data( true );
		if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
			return true;
		}
		Queue::prepare( $order );
		$order->save_meta_data();
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		if ( ! is_array( $data['snapshot'] ?? null ) ) {
			return true;
		}
		$ready = AuthorizationStore::edit(
			$order->get_id(),
			static function ( array &$state ) use ( $order, $data ): void {
				if ( array() !== $state ) {
					return;
				}
				$state = array(
					'policy'          => SendVerdict::POLICY,
					'status'          => 'pending',
					'snapshot_sha256' => self::hash( $data['snapshot'] ),
					'source_sha256'   => self::snapshot_source( $data['snapshot'] ),
					'review'          => self::review( $order ),
					'routing'         => self::routing(),
					'attempts'        => 0,
					'next_at'         => time(),
					'jobs'            => array(),
				);
			}
		);
		if ( $ready ) {
			self::recover( $order->get_id() );
			if ( Client::configured() && class_exists( \WP_Async_Request::class ) ) {
				AsyncRunner::enqueue( $order->get_id() );
			}
		}
		return true;
	}
	/** Source. Only schedules native durable work.
	 *
	 * @param int $id Source. Only schedules native durable work.
	 */
	public static function recover( int $id ): void {
		$order = CurrentSource::order( $id );
		if ( ! $order instanceof WC_Order ) {
			return;
		}
		$order->read_meta_data( true );
		if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
			return;
		}
		$state = AuthorizationStore::read( $id );
		if ( ! is_array( $state ) ) {
			return;
		}
		if ( array() === $state ) {
			self::defer( $order );
			return;
		}
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
				return;
			}
		}
		if ( 'approved' === ( $state['status'] ?? '' ) && (int) ( $state['next_at'] ?? 0 ) <= time() ) {
			self::handoff( $id );
			$state = AuthorizationStore::read( $id );
			if ( ! is_array( $state ) ) {
				return;
			}
		}
		if ( 'normal' === ( $state['status'] ?? '' ) ) {
			AuthorizationStore::edit(
				$id,
				static function ( array &$current ) use ( $order ): void {
					if ( 'normal' !== ( $current['status'] ?? '' ) ) {
						return;
					}
					$pending = false;
					foreach ( $current['jobs'] ?? array() as $purpose => $entry ) {
						if ( ! empty( $entry['delivered_at'] ) || ( 'receipt' === $purpose && ! empty( $current['team_only'] ) ) ) {
							continue;
						}
						$job = (int) ( $entry['id'] ?? 0 );
						if ( $job < 1 || null === ( new JobStore() )->load( $job ) || JobStore::FAILED_STATUS === get_post_status( $job ) ) {
							$current['status'] = 'manual';
							if ( isset( $current['jobs']['receipt'] ) && empty( $current['jobs']['receipt']['delivered_at'] ) ) {
								$order->update_meta_data( ReceiptLimit::SKIPPED_META, 'delivery_unconfirmed' );
							}
							self::hold( $order, 'authorization_job_unavailable' );
							$order->save_meta_data();
							return;
						}
						$pending = true;
					}
					if ( ! $pending ) {
						$order->update_meta_data( Queue::PENDING, 'complete' );
						$order->save_meta_data();
					}
				},
				true
			);
			$state = AuthorizationStore::read( $id );
			if ( ! is_array( $state ) || 'normal' !== ( $state['status'] ?? '' ) ) {
				return;
			}
			foreach ( $state['jobs'] ?? array() as $purpose => $entry ) {
				if ( empty( $entry['delivered_at'] ) && ( 'receipt' !== $purpose || empty( $state['team_only'] ) ) ) {
					as_enqueue_async_action( Outbox::HOOK, array( (int) $entry['id'] ), Outbox::GROUP, true );
				}
			}
			return;
		}
		if ( 'pending' !== ( $state['status'] ?? '' ) ) {
			return;
		}
		as_schedule_single_action( max( time(), (int) ( $state['next_at'] ?? 0 ) ), Queue::PROCESS, array( $id ), Outbox::GROUP, true );
	}
	/** Only one native background worker spends on a source at once.
	 *
	 * @param int $id Only one native background worker spends on a source at once.
	 */
	public static function process( int $id ): void {
		$preflight = CurrentSource::order( $id );
		if ( ! $preflight instanceof WC_Order ) {
			return;
		}
		$preflight->read_meta_data( true );
		if ( NotificationHold::held( $preflight ) && ! self::owns_hold( $preflight ) ) {
			return;
		}
		if ( ! \Linker\Commerce\Mail\BudgetTransaction::begin() ) {
			return;
		}
		global $wpdb;
		$wpdb->query( 'ROLLBACK' );
		Lock::run(
			'send-process-' . $id,
			static function () use ( $id ): void {
				$input   = null;
				$claimed = AuthorizationStore::edit(
					$id,
					static function ( array &$state ) use ( $id, &$input ): void {
						$order = CurrentSource::order( $id );
						if ( ! $order instanceof WC_Order ) {
								return;
						}
						$order->read_meta_data( true );
						if ( ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) || 'pending' !== ( $state['status'] ?? '' ) || (int) ( $state['next_at'] ?? 0 ) > time() ) {
							return;
						}
						if ( ! self::current( $order, $state ) ) {
							$state['status'] = 'invalidated';
							return;
						}
						$data     = Queue::data( $order );
						$snapshot = $data['snapshot'] ?? null;
						if ( ! is_array( $snapshot ) || self::hash( $snapshot ) !== ( $state['snapshot_sha256'] ?? '' ) ) {
							$state['status'] = 'invalidated';
							return;
						}
						$attempt            = (int) ( $state['attempts'] ?? 0 );
						$deadline           = microtime( true ) + Queue::WAIT_SECONDS;
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
					return;
				}
				// The durable attempt is claimed before I/O; a killed worker cannot reset its retry count.
				as_schedule_single_action( (int) ceil( $input['deadline'] ), Queue::EXPIRE, array( $id ), Outbox::GROUP, true );
				$result = ( new Client() )->assess( $input['snapshot'], $input['deadline'], $input['binding'] );
				$saved  = AuthorizationStore::edit(
					$id,
					static function ( array &$state ) use ( $id, $input, $result ): void {
						if ( 'processing' !== ( $state['status'] ?? '' ) || ( $state['operation'] ?? '' ) !== $input['operation'] ) {
							return;
						}
						$order = CurrentSource::order( $id );
						if ( ! $order instanceof WC_Order ) {
							$state['status'] = 'invalidated';
							return;
						}
						$order->read_meta_data( true );
						if ( ! self::current( $order, $state ) || ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) || $order->get_meta( Reviews::ERASED ) ) {
							$state['status'] = 'invalidated';
							return;
						}
						$result           = microtime( true ) >= $input['deadline'] ? SendVerdict::unknown( 'deadline' ) : $result;
						$decision         = $result['decision'] ?? 'unknown';
						$state['verdict'] = $result;
						self::observation( $order, $result );
						if ( 'normal' === $decision ) {
							if ( self::owns_hold( $order ) ) {
								$order->delete_meta_data( NotificationHold::META );
								$order->update_meta_data( Queue::PENDING, 'yes' );
								$order->save_meta_data();
							}
							$state['status']   = 'approved';
							$state['producer'] = 'classifier';
							$state['next_at']  = time();
						} elseif ( 'malicious' === $decision ) {
							$state['status'] = 'quarantined';
							self::hold( $order, 'content_quarantined' );
							$order->save_meta_data();
						} else {
							self::retry( $state, $order );
						}
					},
					true
				);
				if ( ! $saved ) {
					wc_get_logger()->warning( 'Inquiry sending authorization is unavailable; native content remains pending.', array( 'source' => 'linker-inquiry-assessment' ) );
				}
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
					return;
				}
				$order = CurrentSource::order( $id );
				if ( ! $order instanceof WC_Order ) {
					$state['status'] = 'invalidated';
						return;
				}
				$order->read_meta_data( true );
				if ( ! self::current( $order, $state ) || $order->get_meta( Reviews::ERASED ) || ( NotificationHold::held( $order ) && ! self::owns_hold( $order ) ) ) {
					$state['status'] = 'invalidated';
					return;
				}
				$state['jobs']   = self::jobs( $order, $state );
				$state['status'] = 'normal';
			},
			true
		);
		if ( ! $written ) {
			// Native Woo caches can contain values written before the owned transaction rolled back.
			// Evict this source only before native history or recovery reads the retained record.
			CurrentSource::order( $id );
			// No caller transaction is committed or rolled back; native recovery retains approval.
			AuthorizationStore::edit(
				$id,
				static function ( array &$state ): void {
					if ( 'approved' !== ( $state['status'] ?? '' ) ) {
						return;
					}
					$attempt                   = (int) ( $state['handoff_attempts'] ?? 0 );
					$state['handoff_attempts'] = $attempt + 1;
					$delay                     = Outbox::RETRY_DELAYS[ $attempt ] ?? null;
					$state['status']           = null === $delay ? 'manual' : 'approved';
					$state['next_at']          = null === $delay ? 0 : time() + $delay;
				}
			);
		}
	}
	/** Durable attempt.
	 *
	 * @param array<string,mixed> $state Durable attempt.
	 * @param WC_Order            $order Native record.
	 */
	private static function retry( array &$state, WC_Order $order ): void {
		$delay            = Outbox::RETRY_DELAYS[ max( 0, (int) $state['attempts'] - 1 ) ] ?? null;
		$state['status']  = null === $delay ? 'manual' : 'pending';
		$state['next_at'] = null === $delay ? 0 : time() + $delay;
		if ( null === $delay ) {
			self::hold( $order, 'assessment_unresolved' );
			$order->save_meta_data();
		}
	}
	/** Only newly prepared native verification holds belong to this pipeline.
	 *
	 * @param WC_Order $order Native inquiry, never an existing incident record.
	 */
	private static function owns_hold( WC_Order $order ): bool {
		$hold = $order->get_meta( NotificationHold::META );
		return SendVerdict::POLICY === $order->get_meta( self::MARKER ) && $order->get_meta( \Linker\Commerce\Protection\Intake::META ) && is_array( $hold ) && 'verification_review' === ( $hold['reason'] ?? '' );
	}
	/** Source.
	 *
	 * @param WC_Order            $order Source.
	 * @param array<string,mixed> $state Server decision.
	 */
	private static function current( WC_Order $order, array $state ): bool {
		return SendVerdict::POLICY === ( $state['policy'] ?? '' ) && self::source( $order ) === ( $state['source_sha256'] ?? '' ) && self::review( $order ) === ( $state['review'] ?? '' ) && self::routing() === ( $state['routing'] ?? '' );
	}
	/** Native business facts without unrelated browser history.
	 *
	 * @param WC_Order $order Native business facts without unrelated browser history.
	 */
	private static function source( WC_Order $order ): string {
		$current = CurrentSource::order( $order->get_id() );
		return $current instanceof WC_Order ? self::snapshot_source( Snapshot::make( $current, array(), false ) ) : '';
	}

	/** Compare exactly the classified business source; unrelated live browser context is excluded.
	 *
	 * @param array<string,mixed> $snapshot Frozen or freshly read native facts.
	 */
	private static function snapshot_source( array $snapshot ): string {
		unset( $snapshot['context'] );
		return self::hash( $snapshot );
	}
	/** Current staff and erasure revision.
	 *
	 * @param WC_Order $order Current staff and erasure revision.
	 */
	private static function review( WC_Order $order ): string {
		return self::hash( array( Reviews::state( $order ), $order->get_meta( Admin::OVERRIDE ), $order->get_meta( Reviews::ERASED ) ) );
	}
	/** Current configuration affects native sender, real recipient and blind-copy route. */
	private static function routing(): string {
		// A long-running provider or SMTP request must observe another process's route edit.
		foreach ( array( \Linker\Commerce\Settings\Options::NOTIFY_TO, \Linker\Commerce\Settings\Options::NOTIFY_BCC, \Linker\Commerce\Settings\Options::NOTIFY_FROM, 'woocommerce_email_from_name', 'woocommerce_email_from_address' ) as $name ) {
			wp_cache_delete( $name, 'options' );
		}
		wp_cache_delete( 'alloptions', 'options' );
		wp_cache_delete( 'notoptions', 'options' );
		$options = new \Linker\Commerce\Settings\Options();
		return self::hash( array( $options->notify_to(), $options->notify_bcc(), $options->notify_sender(), get_option( 'woocommerce_email_from_name' ), get_option( 'woocommerce_email_from_address' ) ) );
	}
	/** Native canonical structure.
	 *
	 * @param mixed $value Native canonical structure.
	 */
	public static function hash( mixed $value ): string {
		$json = wp_json_encode( $value );
		return is_string( $json ) ? hash( 'sha256', $json ) : '';
	}
	/** Full arguments and actual attachment contents.
	 *
	 * @param Message $message Full arguments and actual attachment contents.
	 */
	public static function message_hash( Message $message ): string {
		$files = array();
		foreach ( $message->attachments as $path ) {
			if ( ! is_file( $path ) || ! is_readable( $path ) ) {
				return '';
			}
			$digest = hash_file( 'sha256', $path );
			if ( ! is_string( $digest ) ) {
				return '';
			}
			$files[] = array(
				'path'   => $path,
				'sha256' => $digest,
			);
		}
		return self::hash( array( $message->to_array(), $files ) );
	}
	/** Native source.
	 *
	 * @param WC_Order            $order Native source.
	 * @param array<string,mixed> $result Validated response.
	 */
	private static function observation( WC_Order $order, array $result ): void {
		$data  = Queue::data( $order );
		$label = match ( $result['decision'] ?? 'unknown' ) {
			'normal'=>'normal', 'malicious'=>'suspected_spam', default=>'uncertain'};
		$data['result']         = array_merge( $result, array( 'label' => $label ) );
		$data['initial_result'] = $data['result'];
		$data['completed_at']   = microtime( true );
		$data['elapsed']        = max( 0.0, $data['completed_at'] - (float) ( $data['accepted_at'] ?? $data['completed_at'] ) );
		StructuredMeta::update( $order, Queue::META, $data );
		$order->save_meta_data();
	}
	/** Current native source.
	 *
	 * @param WC_Order            $order Current native source.
	 * @param array<string,mixed> $state Pending grant.
	 * @return array<string,array{id:int,hash:string}>
	 * @throws \RuntimeException If native capture or durable job readback is unavailable.
	 */
	private static function jobs( WC_Order $order, array $state ): array {
		if ( ! empty( $state['jobs'] ) ) {
			return $state['jobs'];
		}
		// Content is now authorized; capture the complete existing receipt instead of the pre-verdict fixed-text variant.
		$order->delete_meta_data( '_linker_fixed_receipt' );
		$order->save_meta_data();
		$emails = WC()->mailer()->get_emails();
		$jobs   = array();
		if ( ! empty( $state['team_only'] ) ) {
			$order->update_meta_data( ReceiptLimit::SKIPPED_META, 'staff_release_team_only' );
			$order->save_meta_data();
		}
		if ( empty( $state['team_only'] ) && 'assessment_pending' === $order->get_meta( ReceiptLimit::SKIPPED_META ) ) {
			$reason = 'enforce' === \Linker\Commerce\Protection\Configuration::active_mode() ? \Linker\Commerce\Protection\ReceiptBudget::reason( $order->get_billing_email(), $order->get_id() ) : ( ( new ReceiptLimit() )->take() ? '' : 'daily_cap' );
			$order->update_meta_data( ReceiptLimit::SKIPPED_META, $reason );
			$order->save_meta_data();
		}
		foreach ( array(
			'team'    => NewInquiryEmail::class,
			'receipt' => InquiryReceivedEmail::class,
		) as $purpose => $class ) {
			if ( 'receipt' === $purpose && '' !== $order->get_meta( ReceiptLimit::SKIPPED_META ) ) {
				continue;
			}
			$email = $emails[ $class ] ?? null;
			if ( ! $email instanceof NewInquiryEmail && ! $email instanceof InquiryReceivedEmail ) {
				throw new \RuntimeException( 'authorization_email_unavailable' );
			}
			$captured = $email->capture( $order );
			if ( null === $captured ) {
				continue;
			}
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
				throw new \RuntimeException( 'authorization_message_unavailable' );
			}
			$job    = ( new JobStore() )->create( $message, $order->get_id() );
			$stored = $job > 0 ? ( new JobStore() )->load( $job ) : null;
			if ( null === $stored || $stored['message']->to_array() !== $message->to_array() ) {
				throw new \RuntimeException( 'authorization_job_unconfirmed' );
			}
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
	 * @param Message $message Frozen send arguments.
	 * @param int     $job Native job.
	 */
	public static function allows( Message $message, int $job ): bool {
		if ( $job > 0 ) {
			clean_post_cache( $job );
			$stored = ( new JobStore() )->load( $job );
			if ( null === $stored || $stored['message']->to_array() !== $message->to_array() ) {
				return false;
			}
		}
		$origin = $message->origin;
		// A bound content job cannot turn itself into a security transaction by editing JSON.
		if ( $job > 0 && NotificationHold::inquiry( $job ) > 0 && 'inquiry' !== ( $origin['kind'] ?? '' ) ) {
			return false;
		}
		if ( $job > 0 && get_post_meta( $job, ConversationAuthorization::SOURCE, true ) && 'conversation' !== ( $origin['kind'] ?? '' ) ) {
			return false;
		}
		if ( 'conversation' === ( $origin['kind'] ?? '' ) ) {
			return ConversationAuthorization::allows( $message, $job );
		}
		if ( 'transaction' === ( $origin['kind'] ?? '' ) || 'security' === ( $origin['kind'] ?? '' ) ) {
			return \Linker\Commerce\Mail\NativeOrigin::valid( $message );
		}
		if ( 'inquiry' !== ( $origin['kind'] ?? '' ) || $job < 1 ) {
			return false;
		}
		$id      = $origin['record'] ?? 0;
		$purpose = $origin['purpose'] ?? '';
		if ( ! is_int( $id ) || $id < 1 || ! in_array( $purpose, array( 'team', 'receipt' ), true ) || NotificationHold::inquiry( $job ) !== $id ) {
			return false;
		}
		$order = CurrentSource::order( $id );
		if ( ! $order instanceof WC_Order ) {
			return false;
		}
		$order->read_meta_data( true );
		if ( NotificationHold::held( $order ) || $order->get_meta( Reviews::ERASED ) ) {
			return false;
		}
		$state = AuthorizationStore::read( $id );
		return is_array( $state ) && ( 'receipt' !== $purpose || empty( $state['team_only'] ) ) && 'normal' === ( $state['status'] ?? '' ) && self::current( $order, $state ) && ( $state['jobs'][ $purpose ]['id'] ?? 0 ) === $job && '' !== self::message_hash( $message ) && ( $state['jobs'][ $purpose ]['hash'] ?? '' ) === self::message_hash( $message );
	}
	/** Persist physical success separately from a missing native job.
	 *
	 * @param Message $message Actual sent frozen arguments.
	 * @param int     $job Original durable job.
	 * @param string  $message_id Native Message-ID of this successful transport, or empty.
	 */
	public static function delivered( Message $message, int $job, string $message_id = '' ): void {
		if ( 'conversation' === ( $message->origin['kind'] ?? '' ) ) {
			AuthorizationStore::edit(
				'conversation-' . $job,
				static function ( array &$state ) use ( $message ): void {
					if ( 'normal' === ( $state['status'] ?? '' ) && ( $state['message_sha256'] ?? '' ) === self::message_hash( $message ) ) {
						$state['status']       = 'delivered';
						$state['delivered_at'] = time();
					} }
			);
			return;
		}
		if ( 'inquiry' !== ( $message->origin['kind'] ?? '' ) ) {
			return;
		}
		$id      = (int) ( $message->origin['record'] ?? 0 );
		$purpose = $message->origin['purpose'] ?? '';
		AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( $message, $purpose, $job, $id, $message_id ): void {
				self::record_transport( $state, $message, $purpose, $job, $id, $message_id );
			}
		);
	}

	/**
	 * The Message-ID header PHPMailer actually wrote, or empty when it is not one.
	 *
	 * @param string $id Candidate from PHPMailer::getLastMessageID().
	 */
	public static function native_message_id( string $id ): string {
		$id = trim( $id );
		return 1 === preg_match( '/^<[^<>\s]{1,200}@[^<>\s]{1,200}>$/', $id ) ? $id : '';
	}

	/**
	 * Record one successful transport without replacing an earlier witness.
	 *
	 * @param array<string,mixed> $state Authorization row.
	 * @param Message             $message Frozen authorized arguments.
	 * @param string              $purpose Team or receipt purpose.
	 * @param int                 $job Original job.
	 * @param int                 $inquiry Inquiry that owns the job.
	 * @param string              $message_id Native transport ID, possibly empty.
	 */
	private static function record_transport( array &$state, Message $message, string $purpose, int $job, int $inquiry, string $message_id ): void {
		if ( ! in_array( $purpose, array( 'team', 'receipt' ), true ) || $inquiry < 1 || $job < 1 ) {
			return;
		}
		$hash = self::message_hash( $message );
		if ( ( $state['jobs'][ $purpose ]['id'] ?? 0 ) !== $job || '' === $hash || ( $state['jobs'][ $purpose ]['hash'] ?? '' ) !== $hash ) {
			return;
		}
		if ( \Linker\Commerce\Mail\NotificationHold::inquiry( $job ) !== $inquiry ) {
			return;
		}
		// Delivery is already physical. A reused Message-ID must not hide that.
		$state['jobs'][ $purpose ]['delivered_at'] = time();
		$message_id                                = self::native_message_id( $message_id );
		if ( '' === $message_id || is_array( $state['jobs'][ $purpose ]['witness'] ?? null ) ) {
			return;
		}
		foreach ( $state['jobs'] as $other => $entry ) {
			if ( $other !== $purpose && is_array( $entry ) && ( $entry['witness']['message_id'] ?? '' ) === $message_id ) {
				return;
			}
		}
		$state['jobs'][ $purpose ]['witness'] = array(
			'inquiry_id'     => $inquiry,
			'purpose'        => $purpose,
			'at'             => time(),
			'message_sha256' => $hash,
			'message_id'     => $message_id,
		);
	}

	/** Current native content is part of the staff form's optimistic version.
	 *
	 * @param WC_Order $order Displayed native source.
	 */
	public static function reference( WC_Order $order ): string {
		return self::source( $order );
	}

	/** The existing capability/nonce/version checked staff event is not a browser permit.
	 *
	 * @param int    $id Native inquiry.
	 * @param string $operation Saved native audit action.
	 * @param string $label Saved staff decision.
	 */
	public static function reviewed( int $id, string $operation, string $label ): void {
		if ( ! current_user_can( 'manage_woocommerce' ) || ! self::managed( $id ) ) {
			return;
		}
		AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( $id, $operation, $label ): void {
				$order = CurrentSource::order( $id );
				if ( ! $order instanceof WC_Order ) {
					return;
				}
				$order->read_meta_data( true );
				if ( $order->get_meta( Reviews::ERASED ) || ( NotificationHold::held( $order ) && ! self::policy_hold( $order ) ) || self::source( $order ) !== ( $state['source_sha256'] ?? '' ) ) {
					return;
				}
				$state['review'] = self::review( $order );
				if ( 'evidence' === $operation ) {
					return;
				}
				if ( 'withdraw' === $operation ) {
					$state['status']   = 'pending';
					$state['attempts'] = 0;
					$state['next_at']  = time();
				} elseif ( 'normal' === $label ) {
								$state['status'] = 'manual';
				} else {
						$state['status'] = 'suspected_spam' === $label ? 'quarantined' : 'manual';
				}
				if ( in_array( $state['status'], array( 'manual', 'quarantined' ), true ) ) {
					self::hold( $order, 'staff_content_review' );
				} else {
					$order->update_meta_data( Queue::PENDING, 'yes' );
				}
				$order->save_meta_data();
			}
		);
		self::recover( $id );
	}

	/** Erasure revokes before deleting queued copies; a late worker cannot resurrect them.
	 *
	 * @param WC_Order $order Native privacy-authorized order.
	 * @throws \RuntimeException On an unconfirmed revocation or content removal.
	 */
	public static function erase( WC_Order $order ): void {
		$id    = $order->get_id();
		$state = AuthorizationStore::read( $id );
		if ( ! is_array( $state ) ) {
			throw new \RuntimeException( 'authorization_erasure_unavailable' );
		}
		$order->read_meta_data( true );
		if ( array() === $state && SendVerdict::POLICY !== $order->get_meta( self::MARKER ) ) {
			return;
		}
		$jobs    = array();
		$revoked = AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( &$jobs ): void {
				$jobs = $state['jobs'] ?? array();
				if ( is_array( $state['jobs'] ?? null ) ) {
					foreach ( $state['jobs'] as $purpose => $entry ) {
						if ( is_array( $entry ) ) {
							unset( $entry['witness'] );
							$state['jobs'][ $purpose ] = $entry;
						}
					}
				}
				$state['status']  = 'erased';
				$state['verdict'] = SendVerdict::unknown( 'erased' );
			}
		);
		if ( ! $revoked ) {
			throw new \RuntimeException( 'authorization_erasure_unavailable' );
		}
		foreach ( $jobs as $entry ) {
			$job = (int) ( $entry['id'] ?? 0 );
			if ( $job > 0 ) {
				( new JobStore() )->erase_message( $job ); }
		}
		$order->read_meta_data( true );
		$data = Queue::data( $order );
		unset( $data['snapshot'] );
		$data['result']         = Result::unknown( 'erased' );
		$data['initial_result'] = $data['result'];
		StructuredMeta::update( $order, Queue::META, $data );
		$order->update_meta_data( Queue::PENDING, 'erased' );
		$order->save_meta_data();
	}

	/** Newly managed record.
	 *
	 * @param WC_Order $order Newly managed record.
	 * @param string   $reason Fixed server reason.
	 */
	private static function hold( WC_Order $order, string $reason ): void {
		$order->update_meta_data(
			NotificationHold::META,
			array(
				'reason' => $reason,
				'policy' => SendVerdict::POLICY,
				'at'     => time(),
			)
		);
		$order->update_meta_data( Queue::PENDING, 'held' );
	}

	/** Exact new-pipeline hold, never a historical incident marker.
	 *
	 * @param WC_Order $order Exact new-pipeline hold, never a historical incident marker.
	 */
	private static function policy_hold( WC_Order $order ): bool {
		$hold = $order->get_meta( NotificationHold::META );
		return self::owns_hold( $order ) || ( is_array( $hold ) && SendVerdict::POLICY === ( $hold['policy'] ?? '' ) && SendVerdict::POLICY === $order->get_meta( self::MARKER ) );
	}

	/** Explicit native staff release authorizes this source version and the team purpose alone.
	 *
	 * @param WC_Order $order Native source selected by the capability/nonce checked controller.
	 * @param string   $reference Version displayed in the release control.
	 * @return array<string,mixed>|\WP_Error Durable native audit or refusal.
	 */
	public static function release( WC_Order $order, string $reference ): array|\WP_Error {
		if ( ! current_user_can( 'manage_woocommerce' ) ) {
			return new \WP_Error( 'forbidden', __( 'You cannot release this notification.', 'linker-commerce' ) );
		}
		$id      = $order->get_id();
		$result  = new \WP_Error( 'notification_changed', __( 'This notification has changed. Reload the inquiry before trying again.', 'linker-commerce' ) );
		$written = AuthorizationStore::edit(
			$id,
			static function ( array &$state ) use ( $order, $reference, &$result ): void {
				$order->read_meta_data( true );
				$review     = Reviews::state( $order );
				$override   = $order->get_meta( Admin::OVERRIDE );
				$correction = (int) ( $review['event'] ?? 0 );
				if ( ! is_array( $override ) || 'correct' !== ( $override['operation'] ?? '' ) || 'normal' !== ( $override['label'] ?? '' ) || (int) ( $override['user'] ?? 0 ) < 1 || $correction < 1 || get_comment_meta( $correction, Reviews::EVENT, true ) !== $override ) {
					return;
				}
				if ( ! in_array( $state['status'] ?? '', array( 'manual', 'quarantined' ), true ) || ! self::current( $order, $state ) || $order->get_meta( Reviews::ERASED ) || ! NotificationHold::held( $order ) || ! hash_equals( NotificationHold::reference( $order ), $reference ) ) {
					return;
				}
				$event = array(
					'at'               => time(),
					'user'             => get_current_user_id(),
					'reference'        => $reference,
					'policy'           => SendVerdict::POLICY,
					'source_sha256'    => $state['source_sha256'],
					'purpose'          => 'team',
					'producer'         => 'human_override',
					'correction_event' => $correction,
				);
				$note  = $order->add_order_note( __( 'Notification released for delivery.', 'linker-commerce' ), 0, true );
				if ( $note < 1 || ! add_comment_meta( $note, NotificationHold::EVENT, wp_slash( $event ), true ) ) {
					throw new \RuntimeException( 'authorization_release_audit_failed' );
				}
				StructuredMeta::update( $order, NotificationHold::RELEASED, $event );
				$order->delete_meta_data( NotificationHold::META );
				$order->update_meta_data( Queue::PENDING, 'yes' );
				if ( empty( $state['jobs']['receipt']['delivered_at'] ) ) {
					$order->update_meta_data( ReceiptLimit::SKIPPED_META, 'staff_release_team_only' );
				}
				$order->save_meta_data();
				$order->read_meta_data( true );
				if ( $order->get_meta( NotificationHold::META ) || $order->get_meta( NotificationHold::RELEASED ) !== $event ) {
					throw new \RuntimeException( 'authorization_release_unconfirmed' );
				}
				if ( $order->get_meta( \Linker\Commerce\Protection\Intake::META ) ) {
					$released = \Linker\Commerce\Protection\IntakeStore::edit(
						static function ( array &$registry ) use ( $order ): array {
							$request = $order->get_meta( \Linker\Commerce\Protection\BusinessRecord::REQUEST );
							foreach ( $registry['entries'] as $key => $entry ) {
								if ( $order->get_id() === (int) ( $entry['order'] ?? 0 ) || ( $key === $request && in_array( (int) ( $entry['order'] ?? 0 ), array( 0, $order->get_id() ), true ) ) ) {
									unset( $registry['entries'][ $key ] );
								}
							}
							\Linker\Commerce\Protection\IntakeStore::save( $registry );
							return array();
						}
					);
					if ( is_wp_error( $released ) ) {
						throw new \RuntimeException( 'authorization_intake_release_unconfirmed' ); }
				}
				$state['staff_release'] = $event;
				$state['producer']      = 'human_override';
				$state['team_only']     = true;
				$state['status']        = empty( $state['jobs'] ) ? 'approved' : 'normal';
				$state['next_at']       = time();
				$result                 = $event;
			},
			true
		);
		if ( ! $written ) {
			return new \WP_Error( 'notification_busy', __( 'This notification is being processed. Reload the inquiry before trying again.', 'linker-commerce' ) );
		}
		if ( is_array( $result ) ) {
			self::recover( $id );
		}
		return $result;
	}
}
