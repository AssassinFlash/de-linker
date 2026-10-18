<?php
/**
 * Email to the team: a new inquiry.
 *
 * A theme may override it as woocommerce/emails/linker-new-inquiry.php.
 *
 * @package Linker\Commerce
 *
 * @var WC_Order $order              The inquiry.
 * @var string   $sender_label       Company, name, or real reply email.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var bool     $sent_to_admin      True.
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
	printf(
		/* translators: 1: inquiry number, 2: company or reply email when no name was given. */
		esc_html__( 'New inquiry %1$s from %2$s.', 'linker-commerce' ),
		esc_html( '#' . $order->get_order_number() ),
		esc_html( $sender_label )
	);
} else {
	printf(
		/* translators: 1: inquiry number, 2: company, 3: customer's full name. */
		esc_html__( 'New inquiry %1$s from %2$s (%3$s).', 'linker-commerce' ),
		esc_html( '#' . $order->get_order_number() ),
		esc_html( $sender_label ),
		esc_html( $order->get_formatted_billing_full_name() )
	);
}
?>
</p>
<p><a href="<?php echo esc_url( $order->get_edit_order_url() ); ?>"><?php esc_html_e( 'Open the inquiry', 'linker-commerce' ); ?></a></p>
<?php
// A contact message through Genie (#243) names its own door below, with its hand-off.
$linker_handoff = $order->get_meta( \Linker\Commerce\Genie\Module::HANDOFF_META );
if ( 'contact' === $order->get_meta( '_linker_inquiry_source' ) && ! is_array( $linker_handoff ) ) :
	?>
<p><?php esc_html_e( 'Contact form', 'linker-commerce' ); ?><br />
	<?php
	printf(
	/* translators: %s: topic selected in the contact form. */
		esc_html__( 'This is about: %s', 'linker-commerce' ),
		esc_html( \Linker\Commerce\Contact\Form::intent_label( (string) $order->get_meta( '_linker_inquiry_topic' ) ) )
	);
	?>
</p>
<?php endif; ?>
<?php
if ( is_array( $linker_handoff ) ) {
	// A contact message through Genie (#243): its hand-off.
	wc_get_template( 'emails/linker-genie-handoff.php', array( 'handoff' => $linker_handoff ), '', $email->template_base );
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
