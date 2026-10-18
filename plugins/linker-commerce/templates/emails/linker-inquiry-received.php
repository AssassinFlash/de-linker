<?php
/**
 * Email to the customer: the inquiry was received.
 *
 * A theme may override it as woocommerce/emails/linker-inquiry-received.php.
 *
 * @package Linker\Commerce
 *
 * @var WC_Order $order              The inquiry.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var bool     $sent_to_admin      False.
 * @var bool     $plain_text         False.
 * @var WC_Email $email              The email.
 */

defined( 'ABSPATH' ) || exit;

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
if ( '' === trim( $order->get_formatted_billing_full_name() ) ) {
	esc_html_e( 'Hello,', 'linker-commerce' );
} else {
	/* translators: %s: the customer's full name. */
	printf( esc_html__( 'Hello %s,', 'linker-commerce' ), esc_html( $order->get_formatted_billing_full_name() ) );
}
?>
</p>
<p>
<?php
/* translators: %s: inquiry number. The sentence follows the salutation "Hello %s,". */
printf( esc_html__( 'Thank you for your inquiry %s.', 'linker-commerce' ), esc_html( '#' . $order->get_order_number() ) );
?>
</p>
<p><?php esc_html_e( 'We reply within one business day.', 'linker-commerce' ); ?> <?php esc_html_e( 'The Linker team will reply to the email address you provided.', 'linker-commerce' ); ?></p>
<?php
if ( 0 === $order->get_customer_id() ) {
	printf( '<p><a href="%s">%s</a></p>', esc_url( \Linker\Commerce\Inquiry\AccountLink::url( $order ) ), esc_html__( 'Create an account with this email to see net prices after approval and track your inquiry.', 'linker-commerce' ) );
}
/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_order_details', $order, $sent_to_admin, $plain_text, $email );
/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_order_meta', $order, $sent_to_admin, $plain_text, $email );
/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_customer_details', $order, $sent_to_admin, $plain_text, $email );

if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_footer', $email );
