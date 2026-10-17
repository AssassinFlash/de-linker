<?php
/**
 * Email to the customer: the partner registration was received and is under review.
 *
 * A theme may override it as woocommerce/emails/linker-registration-received.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var string   $reason             Not used; a registration carries no team reason yet.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var bool     $sent_to_admin      False.
 * @var bool     $plain_text         False.
 * @var WC_Email $email              The email.
 */

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p><?php esc_html_e( 'We received your partner registration.', 'linker-commerce' ); ?></p>
<p><?php esc_html_e( 'We are reviewing your partner account and will email you when it is approved. You can send inquiries now; approval opens net prices.', 'linker-commerce' ); ?></p>
<?php
// The address is the message's own placeholder so the gate can link the same
// sentence; in the email it stays the plain address the reader saw before.
printf(
	'<p>%s</p>',
	sprintf(
		/* translators: %s: the team's email address. */
		esc_html__( 'Until then, browse the products and write to %s with any question.', 'linker-commerce' ),
		esc_html( 'sales@de-linker.com' )
	)
);
?>
<p>
	<a class="link" href="<?php echo esc_url( (string) get_permalink( (int) wc_get_page_id( 'shop' ) ) ); ?>"><?php esc_html_e( 'Browse products', 'linker-commerce' ); ?></a>
</p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
