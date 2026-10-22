<?php
/**
 * Two bounded native registration notices, recovered from their owning user.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Outbox;
use Linker\Commerce\Protection\ReceiptBudget;
use Linker\Commerce\Registration\Emails\NewCustomerEmail;
use Linker\Commerce\Registration\Emails\RegistrationReceivedEmail;
use WP_Error;
use WP_User;

/**
 * User meta is a bounded handoff source, never another mail delivery queue.
 */
final class RegistrationNotices {

	public const META    = '_linker_registration_notices';
	public const PENDING = '_linker_registration_notice_pending';
	public const OWNER   = '_linker_registration_notice_owner';

	/**
	 * Freeze and pre-reserve each count-one native producer before creating a user.
	 *
	 * @param  array<string,string> $values    Validated business fields.
	 * @param  string               $email     Native validated email.
	 * @param  string               $username  Native login, when already chosen.
	 * @param  string               $locale    Native customer locale.
	 * @param  string               $operation Verified native operation.
	 * @return array<string,mixed>|WP_Error Two independently reserved notices.
	 */
	public static function prepare( array $values, string $email, string $username, string $locale, string $operation ): array|WP_Error {
		$user   = new WP_User(
			(object) array(
				'ID'              => 0,
				'user_login'      => $username,
				'user_email'      => $email,
				'display_name'    => trim( ( $values['billing_first_name'] ?? '' ) . ' ' . ( $values['billing_last_name'] ?? '' ) ),
				'user_registered' => gmdate( 'Y-m-d H:i:s' ),
			)
		);
		$emails = WC()->mailer()->get_emails();
		$result = array();
		foreach ( array(
			'team'     => NewCustomerEmail::class,
			'received' => RegistrationReceivedEmail::class,
		) as $kind => $class ) {
			$producer = $emails[ $class ] ?? null;
			if ( ! $producer instanceof NewCustomerEmail && ! $producer instanceof RegistrationReceivedEmail ) {
				self::cancel_uncreated( $result );
				return self::problem();
			}
			$plan = RegistrationMessage::prepare( $producer, $user, $values, $locale );
			if ( is_wp_error( $plan ) ) {
				self::cancel_uncreated( $result );
				return $plan;
			}
			$scope = Capacity::reserve_critical( 'registration|' . $operation . '|' . $kind, 1, $plan['max_bytes'] );
			if ( is_wp_error( $scope ) ) {
				self::cancel_uncreated( $result );
				return self::problem();
			}
			$plan['reservation'] = $scope['key'];
			$result[ $kind ]     = $plan;
		}
		return $result;
	}

	/**
	 * Only the pre-create caller can prove these notices never started.
	 *
	 * @param array<string,mixed> $plans Native prepared notices.
	 */
	public static function cancel_uncreated( array $plans ): void {
		foreach ( $plans as $plan ) {
			if ( is_array( $plan ) && is_string( $plan['reservation'] ?? null ) ) {
				Capacity::cancel_before_side_effect( $plan['reservation'] );
			}
		}
	}

	/**
	 * Existing unprotected/admin-created accounts retain their native mail path.
	 *
	 * @param int $id Native user.
	 */
	public static function owns( int $id ): bool {
		return '' !== get_user_meta( $id, \Linker\Commerce\Protection\RegistrationSlots::META, true ) || is_array( self::read( $id ) );
	}

	/**
	 * Native callback and recovery both hand off the exact same prepared message.
	 * Accepted means durably in Outbox, never a claim that mail was delivered.
	 *
	 * @param int    $id   Native user.
	 * @param string $kind One of the two native notices.
	 */
	public static function deliver( int $id, string $kind ): void {
		try {
			Lock::run(
				'registration-notices-' . $id,
				static function () use ( $id, $kind ): void {
					$user  = get_userdata( $id );
					$state = self::read( $id );
					if ( ! $user instanceof WP_User || ! is_array( $state ) || ! is_array( $state[ $kind ] ?? null ) ) {
						return;
					}
					$plan = $state[ $kind ];
					if ( 'skipped' === ( $plan['state'] ?? '' ) ) {
						self::cancel_skipped( $id, $kind, $state );
						return;
					}
					if ( 'pending' !== ( $plan['state'] ?? '' ) ) {
						return;
					}
					$emails = WC()->mailer()->get_emails();
					$class  = 'team' === $kind ? NewCustomerEmail::class : RegistrationReceivedEmail::class;
					$reason = isset( $emails[ $class ] ) && ! $emails[ $class ]->is_enabled() ? 'disabled' : '';
					if ( '' === $reason && 'received' === $kind ) {
						$reason = ReceiptBudget::reason( $user->user_email, $id, 'registration' );
					}
					if ( in_array( $reason, array( 'disabled', 'daily_cap', 'target_cap' ), true ) ) {
						$state[ $kind ] = array(
							'state'       => 'skipped',
							'reason'      => $reason,
							'reservation' => $plan['reservation'],
						);
						self::write( $id, $state );
						self::cancel_skipped( $id, $kind, $state );
						return;
					}
					if ( '' !== $reason ) {
						return; // Unknown receipt policy never becomes an explicit policy skip.
					}
					$vat = (string) get_user_meta( $id, VatProfile::STATUS_META, true );
					if ( '' === $vat ) {
						// A crash before Fields::save/VIES left the native business values intact.
						$vat = ( new VatProfile( new ViesClient() ) )->update( $id, (string) get_user_meta( $id, VatProfile::VAT_META, true ), false );
					}
					$message = RegistrationMessage::complete( $plan, $id, $vat );
					if ( null === $message ) {
						return; // Account exists; keep visible pending instead of inventing success.
					}
					try {
						Capacity::within(
							$plan['reservation'],
							static function () use ( $message, $id, $kind, $state ): void {
								( new JobStore() )->create(
									$message,
									0,
									static function ( int $job ) use ( $id, $kind, $state ): void {
										update_post_meta( $job, '_linker_registration_user', $id );
										if ( (int) get_post_meta( $job, '_linker_registration_user', true ) !== $id ) {
											throw new \RuntimeException( 'registration_notice_owner_failed' );
										}
										$next          = $state;
										$next[ $kind ] = array(
											'state' => 'accepted',
											'job'   => $job,
										);
										self::write( $id, $next );
									}
								);
							}
						);
					} finally {
						wp_cache_delete( $id, 'user_meta' );
					}
				}
			);
		} catch ( \Throwable $error ) {
			// The account already exists; its durable pending source remains the recovery authority.
			wp_cache_delete( $id, 'user_meta' );
		}
	}

	/**
	 * Explicit skips are durable before unused count-one scope cancellation.
	 *
	 * @param int                 $id    Native user.
	 * @param string              $kind  Native notice.
	 * @param array<string,mixed> $state Durable notice state.
	 */
	private static function cancel_skipped( int $id, string $kind, array $state ): void {
		$scope = $state[ $kind ]['reservation'] ?? '';
		if ( ! is_string( $scope ) || '' === $scope ) {
			return; }
		self::acknowledge(
			static function () use ( $id, $kind, $state, $scope ): bool {
				if ( ! Capacity::cancel_before_side_effect( $scope ) ) {
					return false; }
				unset( $state[ $kind ]['reservation'], $state[ $kind ]['max_bytes'] );
				self::write( $id, $state );
				return true;
			}
		);
	}

	/**
	 * Native independent maintenance/CLI can recover without a browser retry.
	 *
	 * @return void Native action callback; no delivery count is returned.
	 */
	public static function maintain(): void {
		self::recover();
	}

	/**
	 * Number examined by independent recovery, never a delivered-mail count.
	 */
	public static function recover(): int {
		$ids = get_users(
			array(
				'fields'   => 'ID',
				'number'   => 128,
				'meta_key' => self::PENDING, // phpcs:ignore WordPress.DB.SlowDBQuery -- Bounded native recovery source, not a public listing.
			'meta_value'   => 'yes', // phpcs:ignore WordPress.DB.SlowDBQuery -- Only unresolved owners, never every historical user.
			)
		);
		foreach ( $ids as $id ) {
			self::deliver( (int) $id, 'team' );
			self::deliver( (int) $id, 'received' );
		}
		return count( $ids );
	}

	/**
	 * Delete only these notices' native jobs and pending body copies.
	 * Unknown reservations keep their minimal accounting reference, never a timer refund.
	 *
	 * @param int $id Native user.
	 */
	public static function erase( int $id ): bool {
		$done = false;
		try {
			Lock::run(
				'registration-notices-' . $id,
				static function () use ( $id, &$done ): void {
					$state = self::read( $id );
					if ( null === $state ) {
						$done = true;
						return; }
					if ( count( $state ) > 2 || array() !== array_diff( array_keys( $state ), array( 'team', 'received' ) ) ) {
						return; }
					$jobs = array_values( array_filter( array_map( static fn ( array $plan ): int => (int) ( $plan['job'] ?? 0 ), $state ), static fn ( int $job ): bool => $job > 0 ) );
					$done = self::with_jobs(
						$jobs,
						static function () use ( $id, $state, $jobs ): bool {
							try {
								return self::acknowledge(
									static function () use ( $id, $state ): bool {
										global $wpdb;
										foreach ( $state as $kind => $plan ) {
											$job = (int) ( $plan['job'] ?? 0 );
											if ( 0 < $job && get_post( $job ) ) {
												if ( (int) get_post_meta( $job, '_linker_registration_user', true ) !== $id ) {
													return false; }
												as_unschedule_all_actions( Outbox::HOOK, array( $job ), Outbox::GROUP );
												( new JobStore() )->delete( $job );
												clean_post_cache( $job );
												if ( null !== ( new JobStore() )->load( $job ) ) {
													return false; }
											}
											if ( '' !== $wpdb->last_error ) {
												return false; }
											$state[ $kind ] = array( 'state' => 'erased' );
											if ( isset( $plan['reservation'] ) && ! Capacity::cancel_before_side_effect( $plan['reservation'] ) ) {
												$state[ $kind ]['reservation'] = $plan['reservation']; }
										}
										self::write( $id, $state );
										delete_user_meta( $id, self::OWNER );
										wp_cache_delete( $id, 'user_meta' );
										return '' === get_user_meta( $id, self::OWNER, true );
									}
								);
							} finally {
								// These connection-owned mail locks stay held through COMMIT/ROLLBACK.
								foreach ( $jobs as $job ) {
									clean_post_cache( $job ); }
								wp_cache_set_posts_last_changed();
							}
						}
					);
				}
			);
		} catch ( \Throwable $error ) {
			return false; } finally {
			wp_cache_delete( $id, 'user_meta' ); }
			return $done;
	}

	/**
	 * At most two native notice jobs stay locked until the source/job transaction ends.
	 *
	 * @param array<int,int>  $jobs Owned native candidates, verified again under the locks.
	 * @param callable():bool $work Atomic erasure.
	 */
	private static function with_jobs( array $jobs, callable $work ): bool {
		if ( array() === $jobs ) {
			return $work(); }
		$job  = array_shift( $jobs );
		$done = false;
		Lock::run(
			'mail-job-' . $job,
			static function () use ( $jobs, $work, &$done ): void {
				$done = self::with_jobs( $jobs, $work );
			}
		);
		return $done;
	}

	/**
	 * A notice's cancellation/deletion and source ACK share one native owned scope.
	 *
	 * @param callable():bool $work This bounded registration source only; no transport/model.
	 */
	private static function acknowledge( callable $work ): bool {
		try {
			return \Linker\Commerce\Mail\NativeTransaction::run(
				static function () use ( $work ): bool {
					if ( ! $work() ) {
						throw new \RuntimeException( 'registration_notice_ack_failed' ); }
					return true;
				}
			);
		} catch ( \Throwable $error ) {
			return false;
		} finally {
			foreach ( array( \Linker\Commerce\Protection\IntakeStore::OPTION, 'alloptions', 'notoptions' ) as $key ) {
				wp_cache_delete( $key, 'options' ); }
		}
	}

	/**
	 * Cache-free native readback; a rolled-back callback cannot leave false success.
	 *
	 * @param  int $id Native user.
	 * @return array<string,mixed>|null Native durable notice states.
	 * @throws \RuntimeException A failed native read is never absence.
	 */
	public static function read( int $id ): ?array {
		wp_cache_delete( $id, 'user_meta' );
		$state = get_user_meta( $id, self::META, true );
		global $wpdb;
		if ( '' !== $wpdb->last_error ) {
			throw new \RuntimeException( 'registration_notice_read_failed' ); }
		return is_array( $state ) ? $state : null;
	}

	/**
	 * Every source acknowledgement joins the native JobStore transaction/readback.
	 *
	 * @param  int                 $id    Native user.
	 * @param  array<string,mixed> $state Native notices.
	 * @throws \RuntimeException Storage failure must roll back the native job too.
	 */
	private static function write( int $id, array $state ): void {
		update_user_meta( $id, self::META, wp_slash( $state ) );
		if ( self::read( $id ) !== $state ) {
			throw new \RuntimeException( 'registration_notice_readback_failed' );
		}
		$pending = array_filter( $state, static fn ( array $plan ): bool => 'pending' === ( $plan['state'] ?? '' ) || isset( $plan['reservation'] ) );
		if ( array() === $pending ) {
			delete_user_meta( $id, self::PENDING );
			wp_cache_delete( $id, 'user_meta' );
			if ( '' !== get_user_meta( $id, self::PENDING, true ) ) {
				throw new \RuntimeException( 'registration_notice_index_failed' );
			}
		} else {
			update_user_meta( $id, self::PENDING, 'yes' );
			wp_cache_delete( $id, 'user_meta' );
			if ( 'yes' !== get_user_meta( $id, self::PENDING, true ) ) {
				throw new \RuntimeException( 'registration_notice_index_failed' );
			}
		}
	}

	/**
	 * Honest pre-create refusal; later failures keep an existing account pending.
	 */
	private static function problem(): WP_Error {
		return new WP_Error( 'linker_registration_capacity', __( 'Registration is currently unavailable. Your account has not been created. Please try again later or email sales@de-linker.com.', 'linker-commerce' ) );
	}
}
