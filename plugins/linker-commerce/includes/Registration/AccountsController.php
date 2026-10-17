<?php
/**
 * Authenticated staff routes for reviewing customer accounts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use Linker\Commerce\Mail\LocaleSwitch;
use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

/** Cookie authentication uses WordPress's REST nonce; target access is checked too. */
final class AccountsController {

	/**
	 * Shared readers/writer.
	 *
	 * @param Accounts $accounts Card data.
	 * @param Approval $approval Approval authority.
	 */
	public function __construct( private readonly Accounts $accounts, private readonly Approval $approval ) {}

	/** Registers the collection and the POST-only decision route. */
	public function register_routes(): void {
		register_rest_route(
			'linker/v1',
			'/accounts',
			array(
				'methods'             => 'GET',
				'callback'            => array( $this, 'read' ),
				'permission_callback' => array( $this, 'permissions' ),
				'args'                => array(
					'focus'  => array(
						'type'    => 'integer',
						'minimum' => 0,
						'default' => 0,
					),
					'status' => array(
						'type'    => 'string',
						'enum'    => array( Approval::PENDING, Approval::RESTRICTED ),
						'default' => Approval::PENDING,
					),
				),
			)
		);
		register_rest_route(
			'linker/v1',
			'/accounts/(?P<id>\d+)/approval',
			array(
				'methods'             => 'POST',
				'callback'            => array( $this, 'decide' ),
				'permission_callback' => array( $this, 'permissions' ),
				'args'                => array(
					'id'     => array(
						'type'    => 'integer',
						'minimum' => 1,
					),
					'status' => array(
						'type'     => 'string',
						'enum'     => Approval::decisions(),
						'required' => true,
					),
					'reason' => array(
						'type'              => 'string',
						'default'           => '',
						'sanitize_callback' => 'sanitize_textarea_field',
					),
				),
			)
		);
	}

	/**
	 * Only staff allowed to edit users can see registration data.
	 *
	 * @return true|WP_Error
	 */
	public function permissions() {
		return current_user_can( 'edit_users' ) ? true : new WP_Error( 'linker_accounts_forbidden', __( 'You are not allowed to review accounts.', 'linker-commerce' ), array( 'status' => 403 ) );
	}

	/**
	 * The queue, or the specifically requested card.
	 *
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return WP_REST_Response|WP_Error
	 */
	public function read( WP_REST_Request $request ) {
		return $this->present( (int) $request->get_param( 'focus' ), false, (string) $request->get_param( 'status' ) );
	}

	/**
	 * All interfaces write through Approval, which triggers the customer email.
	 *
	 * @param WP_REST_Request $request Request.
	 * @phpstan-param WP_REST_Request<array<string, mixed>> $request
	 * @return WP_REST_Response|WP_Error
	 */
	public function decide( WP_REST_Request $request ) {
		$locale = new LocaleSwitch();
		$locale->to( get_user_locale() );
		try {
			$id = (int) $request->get_param( 'id' );
			if ( ! current_user_can( 'edit_user', $id ) || ! $this->approval->is_subject( $id ) ) {
				return new WP_Error( 'linker_account_forbidden', __( 'You are not allowed to change this account.', 'linker-commerce' ), array( 'status' => 403 ) );
			}
			$status = (string) $request->get_param( 'status' );
			$reason = sanitize_textarea_field( (string) $request->get_param( 'reason' ) );
			if ( ! in_array( $status, Approval::decisions(), true ) || ! $this->approval->set( $id, $status, $reason ) ) {
				return new WP_Error( 'linker_account_reason_required', __( 'Enter a reason for the customer before restricting or rejecting the account.', 'linker-commerce' ), array( 'status' => 400 ) );
			}
		} finally {
			$locale->back();
		}
		return $this->present( $id, true );
	}

	/**
	 * Render after transactional email scopes close: Polylang can reload domains
	 * during its notification hooks even if the WordPress locale stays the same.
	 *
	 * @param int    $focus  Focused customer, or zero for the queue.
	 * @param bool   $single Whether the response contains the saved account.
	 * @param string $status Collection state when no account is focused.
	 * @return WP_REST_Response|WP_Error
	 */
	private function present( int $focus, bool $single = false, string $status = Approval::PENDING ) {
		$locale = new LocaleSwitch();
		$locale->to( get_user_locale() );
		try {
			$items = $this->accounts->items( $focus, $status );
			if ( $focus > 0 && array() === $items ) {
				return new WP_Error( 'linker_account_missing', __( 'This account is unavailable or you do not have permission to review it.', 'linker-commerce' ), array( 'status' => 404 ) );
			}
			return new WP_REST_Response(
				array(
					( $single ? 'account' : 'accounts' ) => $single ? $items[0] : $items,
					'counts'                             => $this->accounts->counts(),
				)
			);
		} finally {
			$locale->back();
		}
	}
}
