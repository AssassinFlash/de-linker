<?php
/**
 * Inquiries in the admin.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Inquiry;

/**
 * Staff see inquiries, not orders: the order screens take their headings from
 * the shop_order type's labels ("Inquiry #123 details", "Inquiries").
 */
final class OrderAdmin {

	/**
	 * Relabels the order type; runs on woocommerce_register_post_type_shop_order.
	 *
	 * @param array<string, mixed> $args Post type arguments.
	 * @return array<string, mixed>
	 */
	public function labels( array $args ): array {
		$labels = is_array( $args['labels'] ?? null ) ? $args['labels'] : array();

		$args['labels'] = array_merge(
			$labels,
			array(
				'name'                  => __( 'Inquiries', 'linker-commerce' ),
				'singular_name'         => __( 'Inquiry', 'linker-commerce' ),
				'menu_name'             => __( 'Inquiries', 'linker-commerce' ),
				'add_new'               => __( 'Add inquiry', 'linker-commerce' ),
				'add_new_item'          => __( 'Add new inquiry', 'linker-commerce' ),
				'edit_item'             => __( 'Edit inquiry', 'linker-commerce' ),
				'new_item'              => __( 'New inquiry', 'linker-commerce' ),
				'view_item'             => __( 'View inquiry', 'linker-commerce' ),
				'search_items'          => __( 'Search inquiries', 'linker-commerce' ),
				'not_found'             => __( 'No inquiries found', 'linker-commerce' ),
				'not_found_in_trash'    => __( 'No inquiries found in trash', 'linker-commerce' ),
				'filter_items_list'     => __( 'Filter inquiries', 'linker-commerce' ),
				'items_list_navigation' => __( 'Inquiries navigation', 'linker-commerce' ),
				'items_list'            => __( 'Inquiries list', 'linker-commerce' ),
			)
		);
		return $args;
	}
	/**
	 * Identifies both public doors in the existing Woo inquiry list.
	 *
	 * @param  array<string, string> $columns Native columns.
	 * @return array<string, string>
	 */
	public function columns( array $columns ): array {
		$columns['linker_source'] = __( 'Source', 'linker-commerce' );
		return $columns;
	}

	/**
	 * Works for both Woo order storage modes.
	 *
	 * @param string        $column  Column id.
	 * @param int|\WC_Order $subject Inquiry id or object.
	 */
	public function source( string $column, $subject ): void {
		if ( 'linker_source' !== $column ) {
			return;
		}
		$order = $subject instanceof \WC_Order ? $subject : wc_get_order( $subject );
		if ( ! $order instanceof \WC_Order ) {
			return;
		}
		$is_contact = 'contact' === $order->get_meta( '_linker_inquiry_source' );
		echo esc_html( $is_contact ? __( 'Contact form', 'linker-commerce' ) : __( 'Proforma request', 'linker-commerce' ) );
		if ( $is_contact ) {
			echo ' · ' . esc_html( \Linker\Commerce\Contact\Form::intent_label( (string) $order->get_meta( '_linker_inquiry_topic' ) ) );
		}
	}

	/**
	 * Adds the conversation summary box to both order screens (#244).
	 */
	public function register_summary_box(): void {
		$screen = get_current_screen();
		if ( ! $screen instanceof \WP_Screen ) {
			return;
		}
		if ( ! in_array( $screen->id, array( 'shop_order', 'woocommerce_page_wc-orders' ), true ) ) {
			return;
		}
		add_meta_box(
			'linker-genie-summary',
			__( 'Conversation with Genie', 'linker-commerce' ),
			array( $this, 'summary_box' ),
			$screen->id,
			'side',
			'default'
		);
	}

	/**
	 * Shows what the customer and Genie settled on, with the cause when the
	 * summary was assembled by rule instead of by the model.
	 *
	 * @param int|\WC_Order $post Inquiry.
	 */
	public function summary_box( $post ): void {
		$order = $post instanceof \WC_Order ? $post : wc_get_order( (int) $post );
		if ( ! $order instanceof \WC_Order ) {
			return;
		}
		$summary = $order->get_meta( Sender::SUMMARY_META );
		if ( ! is_array( $summary ) || '' === trim( (string) ( $summary['summary'] ?? '' ) ) ) {
			return;
		}
		?>
		<div class="linker-genie-summary">
			<p><?php echo nl2br( esc_html( (string) $summary['summary'] ) ); ?></p>
			<?php if ( array() !== (array) ( $summary['quantities'] ?? array() ) ) : ?>
				<p><strong><?php esc_html_e( 'Quantities', 'linker-commerce' ); ?></strong><br />
					<?php
					$lines = array();
					foreach ( (array) $summary['quantities'] as $line ) {
						$id = (int) ( $line['product_id'] ?? 0 );
						if ( $id > 0 ) {
							$lines[] = sprintf( '%1$s × %2$d', get_the_title( $id ), (int) ( $line['quantity'] ?? 0 ) );
						}
					}
					echo esc_html( implode( ', ', $lines ) );
					?>
				</p>
			<?php endif; ?>
			<?php if ( array() !== (array) ( $summary['conditions'] ?? array() ) ) : ?>
				<p><strong><?php esc_html_e( 'Conditions', 'linker-commerce' ); ?></strong><br />
					<?php echo esc_html( implode( ' · ', array_map( 'strval', (array) $summary['conditions'] ) ) ); ?>
				</p>
			<?php endif; ?>
			<?php if ( '' !== (string) ( $summary['note'] ?? '' ) ) : ?>
				<p><strong><?php esc_html_e( 'Latest message', 'linker-commerce' ); ?></strong><br />
					<?php echo esc_html( (string) $summary['note'] ); ?>
				</p>
			<?php endif; ?>
			<?php if ( 'rule' === ( $summary['source'] ?? '' ) ) : ?>
				<p><em>
					<?php
					printf(
						/* translators: %s: why the model summary was not used (a short cause). */
						esc_html__( 'Assembled from the customer\'s messages (%s).', 'linker-commerce' ),
						esc_html( (string) ( $summary['reason'] ?? '' ) )
					);
					?>
				</em></p>
			<?php endif; ?>
		</div>
		<?php
	}
}
