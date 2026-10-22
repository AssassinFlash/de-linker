<?php
/**
 * Current native VAT-review notification association, without another body queue.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Inquiry\Assessment\Lock;
use Linker\Commerce\Mail\NativeTransaction;
use Linker\Commerce\Mail\Capacity;
use Linker\Commerce\Mail\CapacityHealth;
use Linker\Commerce\Mail\JobStore;
use Linker\Commerce\Mail\Message;
use Linker\Commerce\Mail\NotificationHold;
use Linker\Commerce\Mail\Outbox;
use WP_Error;

/** One fixed-shape current version per native account, not a log of VAT events. */
class VatNotice {
	public const SOURCE  = '_linker_vat_notice_source';
	public const PENDING = '_linker_vat_notice_pending';

	/** Native erasure cannot leave an old unacknowledged source recoverable. */
	public function register(): void {
		add_filter( 'woocommerce_privacy_erase_personal_data_customer', array( $this, 'erase' ), 10, 2 );
	}

	/**
	 * Witness before VIES; erasure or another writer during HTTP invalidates it.
	 *
	 * @param int $id Native user.
	 */
	public function version( int $id ): string {
		wp_cache_delete( $id, 'user_meta' );
		$record = self::meta( $id, self::SOURCE, true );
		return is_array( $record ) && is_string( $record['version'] ?? null ) ? $record['version'] : '';
	}

	/**
	 * Persist source and actual verdict together after HTTP, under only a short user lock.
	 * This helper owns a transaction or refuses an outer one before changing anything.
	 *
	 * @param int                                $id Native user.
	 * @param string                             $number Normalized native VAT input.
	 * @param array{status:string,detail:string} $result Existing VIES/native result.
	 * @param bool                               $notify Existing notification policy, false at initial registration.
	 * @param string                             $witness Version read before provider work.
	 * @return array<string,mixed>|WP_Error Exact current source or explicit failure.
	 */
	public function persist( int $id, string $number, array $result, bool $notify, string $witness ): array|WP_Error {
		$saved = new WP_Error( 'vat_notice_unavailable' );
		Lock::run(
			'vat-source-' . $id,
			function () use ( $id, $number, $result, $notify, $witness, &$saved ): void {
				$user = get_userdata( $id );
				if ( ! $user instanceof \WP_User || $this->version( $id ) !== $witness || Capacity::transaction_active() ) {
					return;
				}
				$transaction = new NativeTransaction();
				try {
					$previous = (string) self::meta( $id, VatProfile::STATUS_META, true );
					$old      = self::meta( $id, self::SOURCE, true );
					$pending  = $notify && ( ( '' !== $previous && $previous !== $result['status'] ) || ( is_array( $old ) && 'yes' === self::meta( $id, self::PENDING, true ) && empty( $old['erased'] ) ) );
					$checked  = time();
					update_user_meta( $id, VatProfile::STATUS_META, $result['status'] );
					update_user_meta( $id, VatProfile::DETAIL_META, $result['detail'] );
					update_user_meta( $id, VatProfile::NUMBER_META, $number );
					update_user_meta( $id, VatProfile::CHECKED_META, $checked );
					wp_cache_delete( $id, 'user_meta' );
					if ( self::meta( $id, VatProfile::STATUS_META, true ) !== $result['status'] || self::meta( $id, VatProfile::DETAIL_META, true ) !== $result['detail'] || self::meta( $id, VatProfile::NUMBER_META, true ) !== $number || (int) self::meta( $id, VatProfile::CHECKED_META, true ) !== $checked ) {
						throw new \RuntimeException( 'vat_verdict_readback_failed' );
					}
					$record = array(
						'version'  => wp_generate_uuid4(),
						'source'   => self::fingerprint( $id ),
						'verdict'  => self::fingerprint( $id, false ),
						'previous' => self::status( $previous ),
						'current'  => self::status( $result['status'] ),
						'job'      => $pending ? 0 : -1,
					);
					update_user_meta( $id, self::SOURCE, $record );
					update_user_meta( $id, self::PENDING, $pending ? 'yes' : 'no' );
					wp_cache_delete( $id, 'user_meta' );
					if ( self::meta( $id, self::SOURCE, true ) !== $record || ( $pending ? 'yes' : 'no' ) !== self::meta( $id, self::PENDING, true ) ) {
						throw new \RuntimeException( 'vat_notice_source_readback_failed' );
					}
					$transaction->commit();
					$saved = $record;
				} catch ( \Throwable $error ) {
					self::rollback( $transaction );
					wp_cache_delete( $id, 'user_meta' );
				}
			},
			1
		);
		if ( $saved instanceof WP_Error ) {
			CapacityHealth::failed();
		}
		return $saved;
	}

	/**
	 * Capture current native facts, atomically acknowledge only their exact version.
	 *
	 * @param int      $id Native account.
	 * @param callable $capture Native template preview.
	 * @phpstan-param callable(array<string,mixed>):?Message $capture
	 */
	public function deliver( int $id, callable $capture ): void {
		$job = 0;
		Lock::run(
			'vat-source-' . $id,
			static function () use ( $id, $capture, &$job ): void {
				wp_cache_delete( $id, 'user_meta' );
				$record = self::meta( $id, self::SOURCE, true );
				if ( ! get_userdata( $id ) || ! is_array( $record ) || ! empty( $record['erased'] ) || 0 !== ( $record['job'] ?? -1 ) || 'yes' !== self::meta( $id, self::PENDING, true ) || ! is_string( $record['source'] ?? null ) ) {
					return;
				}
				if ( ! hash_equals( $record['source'], self::fingerprint( $id ) ) ) {
					// Only unchanged native VAT facts permit rebinding a current email.
					// Erasure/new verdict generations remain authoritative and cannot revive.
					if ( ! is_string( $record['verdict'] ?? null ) || ! hash_equals( $record['verdict'], self::fingerprint( $id, false ) ) ) {
						return;
					}
					try {
						$record = NativeTransaction::run(
							static function () use ( $id, $record ): array {
								wp_cache_delete( $id, 'user_meta' );
								if ( self::meta( $id, self::SOURCE, true ) !== $record || ! hash_equals( $record['verdict'], self::fingerprint( $id, false ) ) ) {
									throw new \RuntimeException( 'vat_notice_rebind_source_changed' );
								}
								$latest = array_merge(
									$record,
									array(
										'version' => wp_generate_uuid4(),
										'source'  => self::fingerprint( $id ),
									)
								);
								update_user_meta( $id, self::SOURCE, $latest );
								wp_cache_delete( $id, 'user_meta' );
								if ( self::meta( $id, self::SOURCE, true ) !== $latest ) {
									throw new \RuntimeException( 'vat_notice_rebind_readback_failed' );
								}
								return $latest;
							}
						);
					} catch ( \Throwable $error ) {
						CapacityHealth::failed();
						return;
					}
				}
				$message = $capture( $record );
				if ( ! $message instanceof Message ) {
					// Explicit native disabled/no-recipient policy, not accepted mail.
					return;
				}
				$job = ( new JobStore() )->create(
					$message,
					0,
					static function ( int $job ) use ( $id, $record ): void {
						wp_cache_delete( $id, 'user_meta' );
						if ( self::meta( $id, self::SOURCE, true ) !== $record || ! hash_equals( $record['source'], self::fingerprint( $id ) ) ) {
							throw new \RuntimeException( 'vat_notice_generation_changed' );
						}
						$accepted = array_merge( $record, array( 'job' => $job ) );
						update_user_meta( $id, self::SOURCE, $accepted );
						update_user_meta( $id, self::PENDING, 'no' );
						wp_cache_delete( $id, 'user_meta' );
						if ( self::meta( $id, self::SOURCE, true ) !== $accepted || 'no' !== self::meta( $id, self::PENDING, true ) ) {
							throw new \RuntimeException( 'vat_notice_ack_readback_failed' );
						}
					}
				);
				if ( $job < 1 ) {
					CapacityHealth::failed();
				}
			}
		);
		if ( $job > 0 ) {
			/** This action is documented in Mail\Module::register(). */
			do_action( Outbox::HOOK, $job ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound -- Existing original-job consumer, outside user/site locks.
		}
	}

	/** Existing minute recovery handles a pool-sized batch, never re-runs VIES. */
	public static function recover(): void {
		$emails = WC()->mailer()->get_emails();
		$email  = $emails[ Emails\VatReviewEmail::class ] ?? null;
		if ( ! $email instanceof Emails\VatReviewEmail ) {
			return;
		}
		// phpcs:disable WordPress.DB.SlowDBQuery -- Pool-sized current-source lookup, not body/event history.
		$users = get_users(
			array(
				'fields'     => 'ID',
				'number'     => Capacity::LIMITS['ordinary']['count'],
				'orderby'    => 'ID',
				'order'      => 'ASC',
				'meta_key'   => self::PENDING,
				'meta_value' => 'yes',
			)
		); // phpcs:ignore WordPress.DB.SlowDBQuery -- Bounded native pending source query, no copied body queue.
		// phpcs:enable
		foreach ( $users as $id ) {
			$email->trigger( (int) $id );
		}
	}

	/**
	 * Native approved privacy erasure tombstones pending generations and holds an old job.
	 *
	 * @param array<string,mixed> $response Woo's native erasure result.
	 * @param \WC_Customer        $customer Native erased account.
	 * @return array<string,mixed> Unchanged native response.
	 * @throws \RuntimeException Busy erasure cannot claim completion.
	 */
	public function erase( array $response, \WC_Customer $customer ): array {
		$id   = $customer->get_id();
		$done = false;
		Lock::run(
			'vat-source-' . $id,
			static function () use ( $id, &$done ): void {
				if ( Capacity::transaction_active() ) {
					return;
				}
				$transaction = new NativeTransaction();
				try {
					wp_cache_delete( $id, 'user_meta' );
					$old = self::meta( $id, self::SOURCE, true );
					$job = is_array( $old ) ? (int) ( $old['job'] ?? 0 ) : 0;
					if ( $job > 0 && ( new JobStore() )->load( $job ) ) {
						$hold = array( 'reason' => 'erased_vat_source' );
						update_post_meta( $job, NotificationHold::META, $hold );
						wp_cache_delete( $job, 'post_meta' );
						if ( get_post_meta( $job, NotificationHold::META, true ) !== $hold ) {
							throw new \RuntimeException( 'vat_notice_erasure_hold_failed' );
						}
					}
					// Even an account with no previous source needs a witness tombstone:
					// an in-flight first VIES response must not revive erased metadata.
					$tombstone = array(
						'version' => wp_generate_uuid4(),
						'erased'  => true,
						'job'     => $job,
					);
					update_user_meta( $id, self::SOURCE, $tombstone );
					update_user_meta( $id, self::PENDING, 'no' );
					wp_cache_delete( $id, 'user_meta' );
					if ( self::meta( $id, self::SOURCE, true ) !== $tombstone || 'no' !== self::meta( $id, self::PENDING, true ) ) {
						throw new \RuntimeException( 'vat_notice_erasure_readback_failed' );
					}
					$transaction->commit();
					$done = true;
				} catch ( \Throwable $error ) {
					self::rollback( $transaction );
					wp_cache_delete( $id, 'user_meta' );
				}
			},
			1
		);
		if ( ! $done ) {
			throw new \RuntimeException( 'vat_notice_erasure_unconfirmed' );
		}
		return $response;
	}

	/**
	 * A lost native commit is explicit unknown, never a new-connection compensation.
	 *
	 * @param NativeTransaction $transaction Original short writer.
	 */
	private static function rollback( NativeTransaction $transaction ): void {
		try {
			$transaction->rollback();
		} catch ( \Throwable $error ) { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedCatch -- Caller returns an explicit unavailable result; no query or fake rollback proof follows.
		}
	}

	/**
	 * Native current fields remain in their original place; only their HMAC is stored.
	 *
	 * @param int  $id Native account.
	 * @param bool $email Include the mutable native contact address.
	 */
	private static function fingerprint( int $id, bool $email = true ): string {
		clean_user_cache( $id );
		$user   = $email ? get_userdata( $id ) : false;
		$fields = $email ? array( $user instanceof \WP_User ? $user->user_email : '' ) : array();
		foreach ( array( VatProfile::STATUS_META, VatProfile::DETAIL_META, VatProfile::NUMBER_META, VatProfile::CHECKED_META ) as $key ) {
			$fields[] = (string) self::meta( $id, $key, true );
		}
		return hash_hmac( 'sha256', (string) wp_json_encode( $fields ), wp_salt( 'nonce' ) );
	}

	/**
	 * Read mutable native metadata after another acknowledged transaction.
	 *
	 * @param int    $id Native account.
	 * @param string $key Exact source field.
	 * @param bool   $single WordPress native single-value mode.
	 * @phpstan-impure
	 * @return mixed Actual native metadata, never a cached rule assumption.
	 */
	private static function meta( int $id, string $key, bool $single = true ): mixed {
		return get_user_meta( $id, $key, $single );
	}

	/**
	 * Native verdict enum only; corrupt arbitrary metadata is not copied to a marker.
	 *
	 * @param string $status Native status.
	 */
	private static function status( string $status ): string {
		return in_array( $status, array( VatProfile::VALID, VatProfile::INVALID, VatProfile::UNVERIFIED, VatProfile::NONE ), true ) ? $status : '';
	}
}
