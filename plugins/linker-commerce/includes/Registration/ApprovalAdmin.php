<?php
/**
 * The approval actions in WordPress's own screens.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Registration;

use WP_User;

/**
 * Where the team applies the three actions: the one-click "Approve" in the
 * users list (the highest-frequency action, ticket 73) and the Linker block on
 * the user's profile page with all three actions, the reason and the current
 * state. Both reach admin-post.php with a per-user nonce — the list through
 * its link, the profile block through buttons whose formaction overrides the
 * page's own form target (the profile form belongs to WordPress, so the block
 * adds fields to it instead of nesting a form). There is no admin page of this
 * plugin and no admin-ajax call. The capability is WordPress's own edit_users,
 * the same one that guards the profile screen.
 */
final class ApprovalAdmin {

	/**
	 * The admin-post action both forms post to.
	 */
	public const ACTION = 'linker_approval';

	/**
	 * The nonce field's name.
	 */
	public const NONCE_FIELD = 'linker_approval_nonce';

	/**
	 * The three actions, their labels and the states they set.
	 *
	 * @return array<string, array{label: string, status: string}>
	 */
	public static function actions(): array {
		return array(
			'approve'  => array(
				'label'  => __( 'Approve', 'linker-commerce' ),
				'status' => Approval::APPROVED,
			),
			'restrict' => array(
				'label'  => __( 'Restrict', 'linker-commerce' ),
				'status' => Approval::RESTRICTED,
			),
			'reject'   => array(
				'label'  => __( 'Reject', 'linker-commerce' ),
				'status' => Approval::REJECTED,
			),
		);
	}

	/**
	 * The nonce action of one customer's form.
	 *
	 * @param int $user_id Customer.
	 */
	public static function nonce_action( int $user_id ): string {
		return self::ACTION . '-' . $user_id;
	}

	/**
	 * Sets up the admin hooks.
	 *
	 * @param Approval $approval The approval rule.
	 */
	public function __construct( private readonly Approval $approval ) {}

	/**
	 * Adds the hooks.
	 */
	public function register(): void {
		add_filter( 'manage_users_columns', array( $this, 'column_header' ) );
		add_filter( 'manage_users_custom_column', array( $this, 'column_cell' ), 10, 3 );
		add_filter( 'user_row_actions', array( $this, 'row_action' ), 10, 2 );
		add_action( 'edit_user_profile', array( $this, 'profile_block' ) );
		add_action( 'admin_post_' . self::ACTION, array( $this, 'handle' ) );
	}

	/**
	 * The approval column, first after the username.
	 *
	 * @param array<string, string> $columns Users list columns.
	 * @return array<string, string>
	 */
	public function column_header( array $columns ): array {
		$position = array_search( 'username', array_keys( $columns ), true );
		$column   = array( Approval::STATUS_META => __( 'Approval', 'linker-commerce' ) );
		if ( false === $position ) {
			return $columns + $column;
		}
		return array_slice( $columns, 0, (int) $position + 1, true )
			+ $column
			+ array_slice( $columns, (int) $position + 1, null, true );
	}

	/**
	 * The account's state and, where one was given, the reason; runs on
	 * manage_users_custom_column.
	 *
	 * @param string $output  Cell HTML so far.
	 * @param string $column  Column name.
	 * @param int    $user_id User.
	 */
	public function column_cell( string $output, string $column, int $user_id ): string {
		if ( Approval::STATUS_META !== $column ) {
			return $output;
		}
		if ( ! $this->approval->is_subject( $user_id ) ) {
			return $output;
		}
		$reason = $this->approval->reason( $user_id );
		return Approval::label( $this->approval->status( $user_id ) )
			. ( '' !== $reason ? '<br /><span class="description">' . esc_html( $reason ) . '</span>' : '' );
	}

	/**
	 * The one-click "Approve" for an account whose prices are not open; runs on
	 * user_row_actions.
	 *
	 * @param array<string, string> $actions Row actions.
	 * @param WP_User               $user    The row's user.
	 * @return array<string, string>
	 */
	public function row_action( array $actions, WP_User $user ): array {
		if ( Approval::APPROVED === $this->approval->status( $user->ID ) || ! current_user_can( 'edit_users' ) ) {
			return $actions;
		}
		$actions[ Approval::STATUS_META ] = sprintf(
			'<a href="%s">%s</a>',
			esc_url( $this->action_url( $user->ID, 'approve' ) ),
			esc_html__( 'Approve', 'linker-commerce' )
		);
		return $actions;
	}

	/**
	 * The Linker block on the profile page: the state with its audit row, then
	 * the reason field and the three action buttons; runs on
	 * edit_user_profile, so only on another user's screen and only for editors
	 * of users. The buttons' formaction sends WordPress's form to admin-post;
	 * the handler reads only this block's fields.
	 *
	 * @param WP_User $user The user being edited.
	 */
	public function profile_block( WP_User $user ): void {
		if ( ! $this->approval->is_subject( $user->ID ) ) {
			return;
		}
		$status = $this->approval->status( $user->ID );
		$reason = $this->approval->reason( $user->ID );
		$audit  = $this->approval->changed_by( $user->ID );
		$editor = $audit['by'] > 0 ? get_userdata( $audit['by'] ) : null;
		?>
		<h2><?php esc_html_e( 'Linker approval', 'linker-commerce' ); ?></h2>
		<p>
			<strong><?php echo esc_html( Approval::label( $status ) ); ?></strong>
			<?php if ( 0 !== $audit['at'] ) : ?>
				<span class="description">
				<?php
				printf(
					/* translators: 1: date, 2: name of the staff member who set the state. */
					esc_html__( 'Last change %1$s by %2$s.', 'linker-commerce' ),
					esc_html( date_i18n( (string) get_option( 'date_format' ), $audit['at'] ) ),
					esc_html( $editor instanceof WP_User ? $editor->display_name : '' )
				);
				?>
				</span>
			<?php endif; ?>
			<?php if ( '' !== $reason ) : ?>
				<br /><span class="description"><?php echo esc_html( $reason ); ?></span>
			<?php endif; ?>
		</p>
		<table class="form-table" role="presentation">
			<tr>
				<th><label for="linker_approval_reason"><?php esc_html_e( 'Reason', 'linker-commerce' ); ?></label></th>
				<td>
					<textarea name="linker_approval_reason" id="linker_approval_reason" rows="3" class="large-text"></textarea>
					<p class="description"><?php esc_html_e( 'Required for restrict and reject; the customer reads it in the email about the change.', 'linker-commerce' ); ?></p>
				</td>
			</tr>
		</table>
		<p>
			<?php foreach ( self::actions() as $action => $definition ) : ?>
				<button
					type="submit"
					class="button"
					name="linker_approval_action"
					value="<?php echo esc_attr( $action ); ?>"
					formaction="<?php echo esc_url( admin_url( 'admin-post.php' ) ); ?>"
				><?php echo esc_html( $definition['label'] ); ?></button>
			<?php endforeach; ?>
		</p>
		<input type="hidden" name="action" value="<?php echo esc_attr( self::ACTION ); ?>" />
		<input type="hidden" name="user" value="<?php echo esc_attr( (string) $user->ID ); ?>" />
		<?php wp_nonce_field( self::nonce_action( $user->ID ), self::NONCE_FIELD ); ?>
		<?php
	}

	/**
	 * Applies the requested action; runs on admin_post_linker_approval. The
	 * users list's one-click link arrives as a GET request and the profile
	 * block's buttons as a POST (their formaction sends WordPress's own form),
	 * so the fields are read from the request as a whole — the nonce
	 * check_admin_referer() performs reads its field from there too.
	 */
	public function handle(): void {
		$user_id = absint( $this->request( 'user' ) );
		check_admin_referer( self::nonce_action( $user_id ), self::NONCE_FIELD );
		if ( ! current_user_can( 'edit_users' ) || ! $this->approval->is_subject( $user_id ) ) {
			wp_die( esc_html__( 'You are not allowed to change this account.', 'linker-commerce' ), '', array( 'response' => 403 ) );
		}
		$action = sanitize_key( $this->request( 'linker_approval_action' ) );
		$status = ( self::actions()[ $action ] ?? null )['status'] ?? '';
		if ( '' === $status ) {
			wp_die( esc_html__( 'Choose approve, restrict or reject.', 'linker-commerce' ), '', array( 'response' => 400 ) );
		}
		$reason = sanitize_textarea_field( $this->request( 'linker_approval_reason' ) );
		if ( ! $this->approval->set( $user_id, $status, $reason ) ) {
			wp_die( esc_html__( 'A restriction or rejection needs a reason; the customer reads it in the email.', 'linker-commerce' ), '', array( 'response' => 400 ) );
		}
		wp_safe_redirect( $this->redirect_target( $user_id ) );
		exit;
	}

	/**
	 * A field of the current request (its GET part included: the list's
	 * one-click link is a GET request) as sanitized text. An array or a
	 * missing field reads as '', so a hand-built query cannot make a scalar
	 * read fail.
	 *
	 * @param string $field Request field.
	 */
	private function request( string $field ): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended, WordPress.Security.NonceVerification.Missing, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- handle() checks the per-user nonce before it writes anything and this helper is its only caller; the caller sanitizes each field for its own kind (absint, sanitize_key, sanitize_textarea_field).
		$value = wp_unslash( $_REQUEST[ $field ] ?? '' );
		return is_scalar( $value ) ? trim( (string) $value ) : '';
	}

	/**
	 * The address of one action, for the users list link.
	 *
	 * @param int    $user_id Customer.
	 * @param string $action  One of the three actions.
	 */
	private function action_url( int $user_id, string $action ): string {
		return wp_nonce_url(
			admin_url( 'admin-post.php?action=' . self::ACTION . '&user=' . $user_id . '&linker_approval_action=' . $action ),
			self::nonce_action( $user_id ),
			self::NONCE_FIELD
		);
	}

	/**
	 * Back to where the action came from: the users list or the profile.
	 *
	 * @param int $user_id Customer.
	 */
	private function redirect_target( int $user_id ): string {
		$referer = wp_get_referer();
		if ( is_string( $referer ) && '' !== $referer ) {
			return $referer;
		}
		return (string) get_edit_user_link( $user_id );
	}
}
