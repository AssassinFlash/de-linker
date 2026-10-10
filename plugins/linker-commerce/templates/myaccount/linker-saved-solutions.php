<?php
/**
 * Account page "Saved solutions": the solutions the customer saved.
 *
 * A theme may override it as woocommerce/myaccount/linker-saved-solutions.php.
 *
 * @package Linker\Commerce
 *
 * @var list<WP_Post>                          $solutions The customer's saved solutions, newest first.
 * @var Linker\Commerce\Account\SavedSolutions $saved     The store of saved solutions.
 */

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\SavedSolutions;

defined( 'ABSPATH' ) || exit;

if ( array() === $solutions ) : ?>
	<p class="linker-empty"><?php esc_html_e( 'Solutions you save in the Solution Configurator appear here, with their design report.', 'linker-commerce' ); ?></p>
	<?php
	return;
endif;
?>
<table class="woocommerce-orders-table shop_table shop_table_responsive my_account_orders linker-saved-solutions">
	<thead>
		<tr>
			<th scope="col"><?php esc_html_e( 'Solution', 'linker-commerce' ); ?></th>
			<th scope="col"><?php esc_html_e( 'Saved on', 'linker-commerce' ); ?></th>
			<th scope="col"><?php esc_html_e( 'Products', 'linker-commerce' ); ?></th>
			<th scope="col"><span class="screen-reader-text"><?php esc_html_e( 'Actions', 'linker-commerce' ); ?></span></th>
		</tr>
	</thead>
	<tbody>
		<?php
		foreach ( $solutions as $linker_solution ) :
			$linker_items = $saved->items( $linker_solution->ID );
			?>
			<tr id="<?php echo esc_attr( 'linker-solution-' . $linker_solution->ID ); ?>">
				<th scope="row" data-title="<?php esc_attr_e( 'Solution', 'linker-commerce' ); ?>"><?php echo esc_html( $linker_solution->post_title ); ?></th>
				<td data-title="<?php esc_attr_e( 'Saved on', 'linker-commerce' ); ?>"><?php echo esc_html( wp_date( Linker\Commerce\Vocabulary\LocaleFormat::date_format(), (int) get_post_timestamp( $linker_solution ) ) ); ?></td>
				<td data-title="<?php esc_attr_e( 'Products', 'linker-commerce' ); ?>">
					<?php
					foreach ( $linker_items as $linker_item ) {
						$linker_product = wc_get_product( $linker_item['product_id'] );
						if ( $linker_product ) {
							printf( '%1$d × %2$s<br>', (int) $linker_item['quantity'], esc_html( $linker_product->get_name() ) );
						}
					}
					?>
				</td>
				<td>
					<form method="post" class="linker-solution-to-draft">
						<?php wp_nonce_field( SavedSolutions::ADD_ACTION . '_' . $linker_solution->ID ); ?>
						<button type="submit" class="woocommerce-button button" name="<?php echo esc_attr( SavedSolutions::ADD_ACTION ); ?>" value="<?php echo esc_attr( (string) $linker_solution->ID ); ?>"><?php esc_html_e( 'Add to solution draft', 'linker-commerce' ); ?></button>
					</form>
					<?php if ( '' !== $saved->report_path( $linker_solution->ID ) ) : ?>
						<a class="woocommerce-button button linker-report" href="<?php echo esc_url( DocumentDownload::report_url( $linker_solution->ID ) ); ?>"><?php esc_html_e( 'Design report (PDF)', 'linker-commerce' ); ?></a>
					<?php endif; ?>
				</td>
			</tr>
		<?php endforeach; ?>
	</tbody>
</table>
