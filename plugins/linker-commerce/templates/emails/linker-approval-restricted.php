<?php
/**
 * Email to the customer: the partner account is restricted.
 *
 * A theme may override it as woocommerce/emails/linker-approval-restricted.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var string   $reason             The reason the team gave.
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
<p><?php esc_html_e( 'Your partner account has been limited for now.', 'linker-commerce' ); ?></p>
<p><?php esc_html_e( 'You can keep browsing the products, and you can reach us any time at sales@de-linker.com. Net prices and the Proforma request are paused while the account is limited.', 'linker-commerce' ); ?></p>
<?php if ( '' !== $reason ) : ?>
	<p><strong><?php esc_html_e( 'Our reason:', 'linker-commerce' ); ?></strong><br /><?php echo esc_html( $reason ); ?></p>
<?php endif; ?>
<p><?php esc_html_e( 'Write to us and we will look at your account again.', 'linker-commerce' ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
