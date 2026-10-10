<?php
/**
 * Email to the customer: the Proforma invoice is ready.
 *
 * A theme may override it as woocommerce/emails/linker-proforma-issued.php.
 *
 * @package Linker\Commerce
 *
 * @var WC_Order $order              The inquiry.
 * @var string   $proforma_number    Proforma number.
 * @var string   $valid_until        Last day of validity.
 * @var string   $download_url       Link to the PDF (account login needed).
 * @var string   $inquiry_url        Link to the inquiry in the account.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var WC_Email $email              The email.
 */

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
/* translators: %s: the customer's full name. */
printf( esc_html__( 'Hello %s,', 'linker-commerce' ), esc_html( $order->get_formatted_billing_full_name() ) );
?>
</p>
<p>
<?php
printf(
	/* translators: 1: Proforma number, 2: inquiry number, 3: last day of validity. The sentence follows the salutation "Hello %s,". */
	esc_html__( 'Your Proforma invoice %1$s for inquiry %2$s is ready and valid until %3$s.', 'linker-commerce' ),
	'<strong>' . esc_html( $proforma_number ) . '</strong>',
	esc_html( '#' . $order->get_order_number() ),
	esc_html( $valid_until )
);
?>
</p>
<p><a class="button" href="<?php echo esc_url( $download_url ); ?>"><?php esc_html_e( 'Download the Proforma invoice (PDF)', 'linker-commerce' ); ?></a></p>
<p>
<?php
printf(
	/* translators: %s: link to the inquiry in the account. */
	esc_html__( 'You need to be logged in to open it. You can also find it in your account under %s.', 'linker-commerce' ),
	'<a href="' . esc_url( $inquiry_url ) . '">' . esc_html__( 'Inquiries', 'linker-commerce' ) . '</a>'
);
?>
</p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
