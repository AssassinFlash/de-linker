<?php
/**
 * Recoverable removal of a customer's saved solution.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Registration\Approval;
use WP_Error;
use WP_Post;

/** Native post trash, account notices and owner-bound form actions. */
final class SavedSolutionRemoval {

	/** Owner-bound form actions and nonce prefixes. */
	public const REMOVE = 'linker_solution_remove';
	public const UNDO   = 'linker_solution_restore';

	/**
	 * Uses the existing report store and account decision.
	 *
	 * @param PrivateFiles $reports The existing per-solution report storage.
	 * @param Approval     $approval Current account access.
	 */
	public function __construct(
		private readonly PrivateFiles $reports = new PrivateFiles( SavedSolutions::REPORTS_DIRECTORY ),
		private readonly Approval $approval = new Approval()
	) {}

	/** Registers the account action and the native permanent-deletion cleanup. */
	public function register(): void {
		add_action( 'wp_loaded', array( $this, 'request' ), 30 );
		add_action( 'deleted_post', array( $this, 'deleted' ), 10, 2 );
	}

	/** Handles a confirmed POST or Woo-style nonce-bound Undo, then redirects. */
	public function request(): void {
		// phpcs:disable WordPress.Security.NonceVerification -- remove()/restore() verify the action nonce before any write.
		$remove = isset( $_POST[ self::REMOVE ] ) ? absint( $_POST[ self::REMOVE ] ) : 0;
		$undo   = isset( $_GET[ self::UNDO ] ) ? absint( $_GET[ self::UNDO ] ) : 0;
		$nonce  = isset( $_POST['_wpnonce'] ) && $remove > 0 ? sanitize_text_field( wp_unslash( $_POST['_wpnonce'] ) ) : '';
		if ( $remove <= 0 && $undo > 0 ) {
			$nonce = isset( $_GET['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ) : '';
		}
		// phpcs:enable WordPress.Security.NonceVerification
		if ( $remove <= 0 && $undo <= 0 ) {
			return;
		}
		$result = $remove > 0 ? $this->remove( $remove, $nonce ) : $this->restore( $undo, $nonce );
		if ( $result instanceof WP_Error ) {
			wc_add_notice( $result->get_error_message(), 'error' );
		} elseif ( $remove > 0 ) {
			$url = wp_nonce_url( add_query_arg( self::UNDO, $remove, wc_get_account_endpoint_url( 'saved-solutions' ) ), self::UNDO . '_' . $remove );
			wc_add_notice( esc_html__( 'Saved solution removed.', 'linker-commerce' ) . ' <a class="linker-account-undo" href="' . esc_url( $url ) . '">' . esc_html__( 'Undo', 'linker-commerce' ) . '</a>' );
		} else {
			wc_add_notice( __( 'Saved solution restored.', 'linker-commerce' ) );
		}
		wp_safe_redirect( wc_get_account_endpoint_url( 'saved-solutions' ) );
		exit;
	}

	/**
	 * Moves only an authenticated owner's private solution to native trash.
	 *
	 * @param int    $id Solution ID.
	 * @param string $nonce Form nonce.
	 * @return true|WP_Error
	 */
	public function remove( int $id, string $nonce ): true|WP_Error {
		$post = $this->owned( $id, $nonce, self::REMOVE );
		if ( $post instanceof WP_Error ) {
			return $post;
		}
		if ( 'trash' === $post->post_status ) {
			return true;
		}
		// Core deletes permanently when trash is disabled. Keep the solution instead
		// of offering an Undo that cannot restore it (wp-includes/post.php).
		if ( ! EMPTY_TRASH_DAYS || ! wp_trash_post( $id ) ) {
			return $this->failed();
		}
		return true;
	}

	/**
	 * Restores the same private record, with its original data and report.
	 *
	 * @param int    $id Solution ID.
	 * @param string $nonce Undo nonce.
	 * @return true|WP_Error
	 */
	public function restore( int $id, string $nonce ): true|WP_Error {
		$post = $this->owned( $id, $nonce, self::UNDO );
		if ( $post instanceof WP_Error ) {
			return $post;
		}
		if ( 'private' === $post->post_status ) {
			return true;
		}
		// Core otherwise restores a custom post as draft. Scope the native filter
		// to this solution so a recovered report stays in the private account.
		$private = static fn ( string $status, int $post_id ): string => $id === $post_id ? 'private' : $status;
		add_filter( 'wp_untrash_post_status', $private, 10, 2 );
		try {
			$restored = wp_untrash_post( $id );
		} finally {
			remove_filter( 'wp_untrash_post_status', $private, 10 );
		}
		return $restored && 'private' === get_post_status( $id ) ? true : $this->failed();
	}

	/**
	 * Permanent core trash cleanup also reclaims only this solution's report folder.
	 *
	 * @param int     $id Deleted post ID.
	 * @param WP_Post $post Deleted post, supplied by WordPress after successful deletion.
	 */
	public function deleted( int $id, WP_Post $post ): void {
		if ( SavedSolutions::POST_TYPE === $post->post_type ) {
			$this->reports->delete_owner( $id );
		}
	}

	/**
	 * Verifies the session before looking up the private record.
	 *
	 * @param int    $id Solution ID.
	 * @param string $nonce Action nonce.
	 * @param string $action Remove or Undo.
	 * @return WP_Post|WP_Error
	 */
	private function owned( int $id, string $nonce, string $action ): WP_Post|WP_Error {
		$user = get_current_user_id();
		if ( $id <= 0 || $user <= 0 || Approval::REJECTED === $this->approval->status( $user ) || ! wp_verify_nonce( $nonce, $action . '_' . $id ) ) {
			return $this->unavailable();
		}
		$post = get_post( $id );
		if ( ! $post instanceof WP_Post || SavedSolutions::POST_TYPE !== $post->post_type || (int) $post->post_author !== $user || ! in_array( $post->post_status, array( 'private', 'trash' ), true ) ) {
			return $this->unavailable();
		}
		return $post;
	}

	/** Same result for an unavailable record, owner, account or nonce. */
	private function unavailable(): WP_Error {
		return new WP_Error( 'saved_solution_unavailable', __( 'This saved solution is not available.', 'linker-commerce' ) );
	}

	/** A recoverable write failure; no optimistic success notice. */
	private function failed(): WP_Error {
		return new WP_Error( 'saved_solution_update_failed', __( 'The saved solution could not be updated. Please try again.', 'linker-commerce' ) );
	}
}
