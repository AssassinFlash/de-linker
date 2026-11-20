<?php
/**
 * Fixed customer acknowledgement of a saved inquiry.
 *
 * @package Linker\Commerce
 *
 * @var WC_Order $order         The received inquiry.
 * @var string   $email_heading The WooCommerce email heading.
 * @var WC_Email $email         The customer email.
 */

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php. */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
/* translators: %s: inquiry number. */
printf( esc_html__( 'Inquiry #%s', 'linker-commerce' ), esc_html( $order->get_order_number() ) );
?>
</p>
<p><?php esc_html_e( 'We reply within one business day.', 'linker-commerce' ); ?></p>
<?php if ( 0 === $order->get_customer_id() ) : ?>
	<p><a href="<?php echo esc_url( \Linker\Commerce\Inquiry\AccountLink::url( $order ) ); ?>"><?php esc_html_e( 'Create an account with this email', 'linker-commerce' ); ?></a></p>
<?php else : ?>
	<p><a href="<?php echo esc_url( $order->get_view_order_url() ); ?>"><?php esc_html_e( 'View inquiry', 'linker-commerce' ); ?></a></p>
<?php endif; ?>
<?php
/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php. */
do_action( 'woocommerce_email_footer', $email );
