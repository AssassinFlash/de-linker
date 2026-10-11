<?php
/**
 * The audit rows of the stock pushes.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Stock;

/**
 * Keeps one row per accepted stock push, as a private post, so every write
 * an outside system made to the shop is on record with what it asked
 * for and what each SKU got (ticket #69). The persistence follows the mail
 * queue (Mail\JobStore): the payload lives in post meta, which no content
 * filter rewrites; the rows are not shown in any admin screen.
 */
final class BatchLog {

	/**
	 * Post type of the audit rows.
	 */
	public const POST_TYPE = 'linker_stock_batch';

	/**
	 * Post meta holding the row's payload.
	 */
	private const DATA_META = '_linker_stock_batch';

	/**
	 * Registers the post type; runs on init.
	 */
	public function register_post_type(): void {
		register_post_type(
			self::POST_TYPE,
			array(
				'label'           => __( 'Stock pushes', 'linker-commerce' ),
				'public'          => false,
				'show_ui'         => false,
				'rewrite'         => false,
				'query_var'       => false,
				'supports'        => array( 'title' ),
				'capability_type' => 'post',
			)
		);
	}

	/**
	 * Writes one audit row.
	 *
	 * @param array<string, mixed> $data The push: key, items, results, applied, unchanged, errors.
	 * @return int The row's post id, 0 when WordPress refused the write.
	 */
	public function record( array $data ): int {
		$applied   = (int) ( $data['applied'] ?? 0 );
		$unchanged = (int) ( $data['unchanged'] ?? 0 );
		$errors    = (int) ( $data['errors'] ?? 0 );
		$data      = array( 'received_at' => current_time( 'mysql', true ) ) + $data;
		$id        = wp_insert_post(
			array(
				'post_type'   => self::POST_TYPE,
				'post_status' => 'private',
				/* translators: 1: UTC time, 2: applied count, 3: unchanged count, 4: error count. */
				'post_title'  => sprintf( 'Stock push %1$s, %2$d applied, %3$d unchanged, %4$d errors', (string) $data['received_at'], $applied, $unchanged, $errors ),
			),
			true
		);
		if ( \is_wp_error( $id ) ) {
			return 0;
		}
		update_post_meta( $id, self::DATA_META, wp_slash( (string) wp_json_encode( $data ) ) );
		return (int) $id;
	}

	/**
	 * A stored row.
	 *
	 * @param int $id Row id.
	 * @return array<string, mixed>|null The payload, null when there is no such row.
	 */
	public function load( int $id ): ?array {
		if ( self::POST_TYPE !== get_post_type( $id ) ) {
			return null;
		}
		$data = json_decode( (string) get_post_meta( $id, self::DATA_META, true ), true );
		return \is_array( $data ) ? $data : null;
	}
}
