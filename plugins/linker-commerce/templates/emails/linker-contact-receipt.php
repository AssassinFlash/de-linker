<?php
/**
 * Email to the visitor: the contact form message arrived.
 *
 * A theme may override it as woocommerce/emails/linker-contact-receipt.php.
 *
 * @package Linker\Commerce
 *
 * @var Linker\Commerce\Contact\Submission $submission        The visitor's message.
 * @var string                             $email_heading     Heading.
 * @var string                             $additional_content Closing paragraph from the email settings.
 * @var bool                               $sent_to_admin     False.
 * @var bool                               $plain_text        False.
 * @var WC_Email                           $email             The email.
 */

defined( 'ABSPATH' ) || exit;

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
/* translators: %s: the visitor's name. */
printf( esc_html__( 'Hello %s,', 'linker-commerce' ), esc_html( $submission->name ) );
?>
</p>
<p><?php esc_html_e( 'Thank you for your message. The Linker team will reply to this address.', 'linker-commerce' ); ?></p>
<p><strong><?php esc_html_e( 'Your message:', 'linker-commerce' ); ?></strong></p>
<blockquote style="margin: 0 0 16px; padding: 12px 16px; border-left: 3px solid #0c7f73; color: #15372f;">
<?php echo nl2br( esc_html( $submission->message ) ); ?>
</blockquote>
<p><?php esc_html_e( 'If anything is missing, reply to this email and it reaches the same team.', 'linker-commerce' ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_footer', $email );
