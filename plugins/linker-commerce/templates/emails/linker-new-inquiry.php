<?php
/**
 * Email to the team: a new inquiry.
 *
 * A theme may override it as woocommerce/emails/linker-new-inquiry.php.
 *
 * @package Linker\Commerce
 *
 * @var WC_Order $order              The inquiry.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var bool     $sent_to_admin      True.
 * @var bool     $plain_text         False.
 * @var WC_Email $email              The email.
 */

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
printf(
	/* translators: 1: inquiry number, 2: company, 3: customer's full name. */
	esc_html__( 'New inquiry %1$s from %2$s (%3$s).', 'linker-commerce' ),
	esc_html( '#' . $order->get_order_number() ),
	esc_html( $order->get_billing_company() ),
	esc_html( $order->get_formatted_billing_full_name() )
);
?>
</p>
<p><a href="<?php echo esc_url( $order->get_edit_order_url() ); ?>"><?php esc_html_e( 'Open the inquiry', 'linker-commerce' ); ?></a></p>
<?php
/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_order_details', $order, $sent_to_admin, $plain_text, $email );
/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_order_meta', $order, $sent_to_admin, $plain_text, $email );
/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_customer_details', $order, $sent_to_admin, $plain_text, $email );

if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
