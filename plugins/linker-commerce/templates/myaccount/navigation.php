<?php
/**
 * The account navigation.
 *
 * The active theme still ships this template as the markup WooCommerce
 * carried in 2.6 (a list-group of bare anchors) and with it lost the
 * current-page state WooCommerce's own template prints today. This copy is
 * that same theme markup — every class the account card menu styles — with
 * the state restored: "is-active" and aria-current="page" on the current
 * endpoint, the two signals wc_get_account_menu_item_classes() and
 * wc_is_current_account_menu_item() define. Menu reaches it through the
 * woocommerce_locate_template filter.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

/**
 * This action is documented in woocommerce/templates/myaccount/navigation.php.
 */
do_action( 'woocommerce_before_account_navigation' );
?>
<nav class="woocommerce-MyAccount-navigation" role="navigation">
	<div class="list-group">
		<?php foreach ( wc_get_account_menu_items() as $endpoint => $label ) : ?>
			<?php $is_current = wc_is_current_account_menu_item( $endpoint ); ?>
			<a
				href="<?php echo esc_url( wc_get_account_endpoint_url( $endpoint ) ); ?>"
				class="list-group-item list-group-item-action<?php echo $is_current ? ' is-active' : ''; ?>"
				<?php echo $is_current ? 'aria-current="page"' : ''; ?>
			><?php echo esc_html( $label ); ?></a>
		<?php endforeach; ?>
	</div>
</nav>
<?php
/**
 * This action is documented in woocommerce/templates/myaccount/navigation.php.
 */
do_action( 'woocommerce_after_account_navigation' );
