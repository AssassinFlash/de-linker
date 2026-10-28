<?php
/**
 * The approval states of a customer account.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_Error;
use WP_User;

/**
 * The one rule for account approval (ticket 73): every registration starts
 * pending; the team approves, restricts or rejects it, all three reversible,
 * and a restriction or rejection carries a reason that is emailed to the
 * customer. A pending or restricted account reads the site like a guest
 * (docs/specs/11-commerce.md, approval): CommerceState is the single reader of
 * sees_prices(). A rejected account cannot sign in at all; the login form
 * shows the state. Surfaces outside this class read status(), never the meta.
 */
final class Approval {
	/** Native atomic write port; unit fixtures explicitly supply only their memory writer.
	 *
	 * @var \Closure
	 */
	private readonly \Closure $write;

	/**
	 * Production always owns/joins the native transaction; no runtime DB-type bypass.
	 *
	 * @param \Closure|null $write Explicit isolated writer for domain unit fixtures.
	 */
	public function __construct( ?\Closure $write = null ) {
		$this->write = $write ?? \Linker\Commerce\Mail\NativeTransaction::run( ... );
	}


	/**
	 * States.
	 */
	public const PENDING    = 'pending';
	public const APPROVED   = 'approved';
	public const RESTRICTED = 'restricted';
	public const REJECTED   = 'rejected';

	/**
	 * User meta: the state, the reason the team gave for a restriction or a
	 * rejection, and the audit stamps of the last change (who, when).
	 */
	public const STATUS_META     = 'linker_approval_status';
	public const REASON_META     = 'linker_approval_reason';
	public const CHANGED_AT_META = 'linker_approval_changed_at';
	public const CHANGED_BY_META = 'linker_approval_changed_by';

	/**
	 * The refusal of the attempt that is signing in, when there is one.
	 * WooCommerce applies `login_errors` in the same request as `gate_login`
	 * (class-wc-form-handler.php), so this is the message that attempt
	 * produced; a request without a refusal leaves it null.
	 *
	 * @var string|null
	 */
	private ?string $refusal = null;

	/**
	 * Fired when the state changes; the customer emails listen on its
	 * "_notification" form (the way WooCommerce queues transactional emails,
	 * NewCustomerEmail::register()).
	 */
	public const CHANGED_ACTION = 'linker_commerce_approval_changed';

	/**
	 * The states in their canonical order, for validation and the admin UI.
	 *
	 * @return list<string>
	 */
	public static function states(): array {
		return array( self::PENDING, self::APPROVED, self::RESTRICTED, self::REJECTED );
	}

	/**
	 * The reversible decisions an employee can submit (pending is the initial state).
	 *
	 * @return list<string>
	 */
	public static function decisions(): array {
		return array( self::APPROVED, self::RESTRICTED, self::REJECTED );
	}

	/**
	 * Adds the hooks: a rejected account cannot sign in (WordPress's own gate
	 * after the credentials were checked; no other callback was attached on
	 * this site), and the sign-in form shows this gate's message rather than
	 * the theme's blanket line.
	 */
	public function register(): void {
		// Core checks credentials at 20 and spam at 99. Preserve those failures
		// before showing an authenticated customer's approval refusal.
		add_filter( 'authenticate', array( $this, 'gate_login' ), 100 );
		// Priority 20: the theme's own blanket sign-in line is registered on
		// this filter at 10, and the last callback's return is the one the
		// customer reads.
		add_filter( 'login_errors', array( $this, 'login_errors' ), 20 );
	}

	/**
	 * What the sign-in form shows after a failed attempt.
	 *
	 * The approval refusal passes through with its state and the way back:
	 * it is the one message the customer has to read (ticket 73). Everything
	 * else reads one line — a missing username and a wrong password must
	 * look the same to an anonymous visitor.
	 */
	public function login_errors(): string {
		return $this->refusal ?? __( 'The username or the password is not correct.', 'linker-commerce' );
	}

	/**
	 * The account's state: the stored one, or the default for accounts without
	 * a recorded decision. The default is approved for everyone who is not a
	 * plain customer (staff roles were never subject to approval) and pending
	 * for customers, so an account created outside the registration form waits
	 * like a registered one.
	 *
	 * @param int $user_id User.
	 */
	public function status( int $user_id ): string {
		$status = get_user_meta( $user_id, self::STATUS_META, true );
		if ( is_string( $status ) && in_array( $status, self::states(), true ) ) {
			return $status;
		}
		return $this->is_subject( $user_id ) ? self::PENDING : self::APPROVED;
	}

	/**
	 * Whether this account's prices are open: only approved customers see net
	 * prices. The one question every price surface asks (CommerceState).
	 *
	 * @param int $user_id User, 0 for a guest.
	 */
	public function sees_prices( int $user_id ): bool {
		return 0 !== $user_id && self::APPROVED === $this->status( $user_id );
	}

	/**
	 * Whether the account is subject to approval: a plain customer. Staff and
	 * other roles read WordPress's own caps instead.
	 *
	 * @param int $user_id User.
	 */
	public function is_subject( int $user_id ): bool {
		$user = get_userdata( $user_id );
		return $user instanceof WP_User && array( 'customer' ) === $user->roles;
	}

	/**
	 * Applies one of the three reversible actions and records the audit row.
	 * A change of state announces itself (the customer emails listen on
	 * CHANGED_ACTION); changing a restriction/rejection reason also notifies the
	 * customer. Repeating the same decision is a no-op. Rejecting ends the account's sessions: WordPress's
	 * session tokens are the one place a signed-in browser keeps its access.
	 *
	 * @param int    $user_id Customer.
	 * @param string $status  One of the four states.
	 * @param string $reason  Why the state was set; required for restrict and reject.
	 * @return bool Whether the state was written.
	 */
	public function set( int $user_id, string $status, string $reason = '' ): bool {
		if ( ! in_array( $status, self::states(), true ) ) {
			return false;
		}
		$reason   = trim( $reason );
		$previous = $this->status( $user_id );
		if ( in_array( $status, array( self::RESTRICTED, self::REJECTED ), true ) && '' === $reason ) {
			return false;
		}
		$reason = self::APPROVED === $status ? '' : $reason;
		if ( $previous === $status && $this->reason( $user_id ) === $reason && '' !== get_user_meta( $user_id, self::STATUS_META, true ) ) {
			return true;
		}
		$reason_changed = $this->reason( $user_id ) !== $reason;
		// Reserve the actual native template before changing approval or sessions.
		// A complete staff reason may be large; no guessed per-message cut-off.
		if ( $previous !== $status || $reason_changed ) {
			foreach ( WC()->mailer()->get_emails() as $email ) {
				if ( ! $email instanceof Emails\CustomerApprovalEmail ) {
					continue;
				}
				$message = $email->preview_approval( $user_id, $previous, $status, $reason );
				if ( null === $message ) {
					continue;
				}
				$encoded  = wp_json_encode( $message->to_array() );
				$reserved = \Linker\Commerce\Mail\Capacity::reserve_critical( 'approval:' . wp_generate_uuid4(), 1, is_string( $encoded ) ? strlen( $encoded ) : 0 );
				if ( is_wp_error( $reserved ) ) {
					return false;
				}
				$email->stage( $user_id, $message, $reserved );
			}
		}
		try {
			return ( $this->write )(
				function () use ( $user_id, $status, $reason, $previous, $reason_changed ): bool {
					update_user_meta( $user_id, self::STATUS_META, $status );
					update_user_meta( $user_id, self::REASON_META, $reason );
					$changed_at = time();
					update_user_meta( $user_id, self::CHANGED_AT_META, $changed_at );
					update_user_meta( $user_id, self::CHANGED_BY_META, get_current_user_id() );
					wp_cache_delete( $user_id, 'user_meta' );
					if ( get_user_meta( $user_id, self::STATUS_META, true ) !== $status || get_user_meta( $user_id, self::REASON_META, true ) !== $reason || (int) get_user_meta( $user_id, self::CHANGED_AT_META, true ) !== $changed_at || get_current_user_id() !== (int) get_user_meta( $user_id, self::CHANGED_BY_META, true ) ) {
						throw new \RuntimeException( 'approval_native_write_unconfirmed' );
					}

					if ( $previous !== $status || ( $reason_changed && in_array( $status, array( self::RESTRICTED, self::REJECTED ), true ) ) ) {
						if ( $previous !== $status && self::REJECTED === $status ) {
							\WP_Session_Tokens::get_instance( $user_id )->destroy_all();
						}
						/**
						 * Fires when the approval state of a customer changes; the customer
						 * emails listen on its "_notification" form.
						 *
						 * @since 0.2.1
						 *
						 * @param int    $user_id  Customer.
						 * @param string $previous State before.
						 * @param string $current  State now.
						 * @param string $reason   The reason the team gave.
						 */
						// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.DynamicHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- the hook name is this class's own constant, prefixed linker_commerce_, documented above.
						do_action( self::CHANGED_ACTION, $user_id, $previous, $status, $reason );
					}
					return true;
				}
			);
		} catch ( \Throwable $error ) {
			wp_cache_delete( $user_id, 'user_meta' );
			return false;
		}
	}

	/**
	 * The reason the team gave, '' when there is none.
	 *
	 * @param int $user_id Customer.
	 */
	public function reason( int $user_id ): string {
		$reason = get_user_meta( $user_id, self::REASON_META, true );
		return is_string( $reason ) ? $reason : '';
	}

	/**
	 * The audit stamps of the last change: who (user id, 0 for the system) and
	 * when (Unix time, 0 before the first change).
	 *
	 * @param int $user_id Customer.
	 * @return array{by: int, at: int}
	 */
	public function changed_by( int $user_id ): array {
		$by = get_user_meta( $user_id, self::CHANGED_BY_META, true );
		$at = get_user_meta( $user_id, self::CHANGED_AT_META, true );
		return array(
			'by' => is_numeric( $by ) ? (int) $by : 0,
			'at' => is_numeric( $at ) ? (int) $at : 0,
		);
	}

	/**
	 * The state's name, for staff.
	 *
	 * @param string $status State.
	 */
	public static function label( string $status ): string {
		$labels = array(
			self::PENDING    => __( 'Pending review', 'linker-commerce' ),
			self::APPROVED   => __( 'Approved', 'linker-commerce' ),
			self::RESTRICTED => __( 'Restricted', 'linker-commerce' ),
			self::REJECTED   => __( 'Rejected', 'linker-commerce' ),
		);
		return $labels[ $status ] ?? __( 'No decision yet', 'linker-commerce' );
	}

	/**
	 * Keeps a rejected account out: WordPress calls this after the username
	 * and password were found correct, so only the state decides. The message
	 * names the state and the way back (ticket 73: the login gate shows the
	 * state).
	 *
	 * @param WP_User|WP_Error|null $user The authenticated user, or an earlier failure.
	 * @return WP_User|WP_Error|null
	 */
	public function gate_login( $user ) {
		if ( ! $user instanceof WP_User || self::REJECTED !== $this->status( $user->ID ) ) {
			return $user;
		}
		$this->refusal = __( 'This account is not approved for sign-in. We have emailed you the reason. Write to sales@de-linker.com and we will look at it again.', 'linker-commerce' );
		return new WP_Error( 'linker_approval_rejected', $this->refusal );
	}
}
