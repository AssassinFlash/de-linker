<?php
/**
 * Email to the customer: the partner account was rejected.
 *
 * A theme may override it as woocommerce/emails/linker-approval-rejected.php.
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

use Linker\Commerce\Settings\Options;

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p><?php esc_html_e( 'Your Linker partner account was not approved. You cannot sign in with this account.', 'linker-commerce' ); ?></p>
<?php if ( '' !== $reason ) : ?>
	<p><strong><?php esc_html_e( 'Our reason:', 'linker-commerce' ); ?></strong><br /><?php echo esc_html( $reason ); ?></p>
<?php endif; ?>
<p><?php /* translators: %s: public team email address. */ echo esc_html( sprintf( __( 'If you have questions, write to %s.', 'linker-commerce' ), ( new Options() )->team_mailbox() ) ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
