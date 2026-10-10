<?php
/**
 * The German column of the page, post and product lists.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Admin;

use Linker\I18n\Jobs;
use Linker\I18n\Languages;
use Linker\I18n\Translation\State;

/**
 * Shows, for each English page, post and product, whether its German version
 * is synced, waits for a review, is pending or missing, and lets an editor
 * translate it again. The plugin has no other admin screen.
 */
final class StatusColumn {

	/**
	 * The column key.
	 */
	public const COLUMN = 'linker_i18n';

	/**
	 * The admin-post action of the "Retranslate" link.
	 */
	public const ACTION = 'linker_i18n_retranslate';

	/**
	 * The lists that get the column.
	 */
	public const POST_TYPES = array( 'page', 'post', 'product' );

	/**
	 * Sets up the column.
	 *
	 * @param Languages $languages The site's languages.
	 * @param State     $state     Translation state.
	 * @param Jobs      $jobs      The translation queue.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly State $state,
		private readonly Jobs $jobs
	) {}

	/**
	 * Adds the column (filters `manage_{page,post,product}_posts_columns`).
	 *
	 * @param array<string, string> $columns Columns.
	 * @return array<string, string>
	 */
	public function columns( array $columns ): array {
		$columns[ self::COLUMN ] = __( 'German', 'linker-i18n' );
		return $columns;
	}

	/**
	 * Prints the cell of an English post (actions
	 * `manage_{page,post,product}_posts_custom_column`).
	 *
	 * @param string     $column  Column key.
	 * @param int|string $post_id Post ID.
	 */
	public function cell( string $column, $post_id ): void {
		$post_id = (int) $post_id;
		if ( self::COLUMN !== $column || Languages::SOURCE !== $this->languages->of_post( $post_id ) ) {
			return;
		}
		$twin  = $this->languages->post_translation( $post_id, Languages::TARGET );
		$label = $this->label( null !== $twin, $this->state->status( State::POST, $post_id ) );
		$note  = $this->state->note( State::POST, $post_id );
		$link  = null === $twin ? '' : get_edit_post_link( $twin );
		if ( is_string( $link ) && '' !== $link ) {
			printf( '<a href="%1$s" title="%2$s">%3$s</a>', esc_url( $link ), esc_attr( $note ), esc_html( $label ) );
			return;
		}
		printf( '<span title="%1$s">%2$s</span>', esc_attr( $note ), esc_html( $label ) );
	}

	/**
	 * The words for a state.
	 *
	 * @param bool   $exists Whether the German version exists.
	 * @param string $status The English object's status.
	 */
	public function label( bool $exists, string $status ): string {
		if ( ! $exists ) {
			return State::PENDING === $status ? __( 'Missing, translation pending', 'linker-i18n' ) : __( 'Missing', 'linker-i18n' );
		}
		if ( State::NEEDS_REVIEW === $status ) {
			return __( 'Needs review', 'linker-i18n' );
		}
		return State::PENDING === $status ? __( 'Translation pending', 'linker-i18n' ) : __( 'Synced', 'linker-i18n' );
	}

	/**
	 * Adds "Retranslate" to an English post's row (filters `page_row_actions`
	 * and `post_row_actions`).
	 *
	 * @param array<string, string> $actions Row actions.
	 * @param \WP_Post              $post    Post.
	 * @return array<string, string>
	 */
	public function row_actions( array $actions, \WP_Post $post ): array {
		if ( ! in_array( $post->post_type, self::POST_TYPES, true ) || Languages::SOURCE !== $this->languages->of_post( $post->ID ) || ! current_user_can( 'edit_post', $post->ID ) ) {
			return $actions;
		}
		$url                     = wp_nonce_url( admin_url( 'admin-post.php?action=' . self::ACTION . '&post=' . $post->ID ), self::ACTION . '_' . $post->ID );
		$actions[ self::ACTION ] = sprintf( '<a href="%1$s">%2$s</a>', esc_url( $url ), esc_html__( 'Retranslate', 'linker-i18n' ) );
		return $actions;
	}

	/**
	 * Queues a full new translation and goes back to the list (action
	 * `admin_post_linker_i18n_retranslate`).
	 */
	public function retranslate(): void {
		$post_id = isset( $_GET['post'] ) ? absint( $_GET['post'] ) : 0; // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- checked on the next line.
		check_admin_referer( self::ACTION . '_' . $post_id );
		if ( ! current_user_can( 'edit_post', $post_id ) ) {
			wp_die( esc_html__( 'You may not translate this.', 'linker-i18n' ), '', array( 'response' => 403 ) );
		}
		$this->jobs->queue( State::POST, $post_id, true );
		$back = wp_get_referer();
		wp_safe_redirect( add_query_arg( 'linker_i18n_queued', '1', false === $back ? admin_url( 'edit.php' ) : $back ) );
		exit;
	}

	/**
	 * Confirms the queued translation (action `admin_notices`).
	 */
	public function notice(): void {
		if ( ! isset( $_GET['linker_i18n_queued'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended -- a display flag set by retranslate().
			return;
		}
		printf( '<div class="notice notice-success is-dismissible"><p>%s</p></div>', esc_html__( 'The German version will be translated again.', 'linker-i18n' ) );
	}
}
