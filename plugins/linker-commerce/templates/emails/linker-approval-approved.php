<?php
/**
 * Email to the customer: the partner account is approved.
 *
 * A theme may override it as woocommerce/emails/linker-approval-approved.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var string   $reason             Not used by this template; an approval carries no reason.
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
<p><?php esc_html_e( 'Your Linker partner account is approved.', 'linker-commerce' ); ?></p>
<p><?php esc_html_e( 'Net prices are now shown with every product. Add the systems you need to your solution draft, and request the Proforma when the draft is ready.', 'linker-commerce' ); ?></p>
<p>
	<a class="link" href="<?php echo esc_url( (string) wc_get_page_permalink( 'shop' ) ); ?>"><?php esc_html_e( 'Browse products', 'linker-commerce' ); ?></a>
	&nbsp;&bull;&nbsp;
	<a class="link" href="<?php echo esc_url( (string) wc_get_page_permalink( 'myaccount' ) ); ?>"><?php esc_html_e( 'Your account', 'linker-commerce' ); ?></a>
</p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
