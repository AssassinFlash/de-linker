<?php
/**
 * Email to a guest: confirm the address before a Genie conversation is sent.
 *
 * A theme may override it as woocommerce/emails/linker-genie-confirm-address.php.
 * Fixed words and the link only: nothing of the conversation.
 *
 * @package Linker\Commerce
 *
 * @var string   $link               The one-time link.
 * @var int      $hours              How many hours it works.
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
/* translators: %s: the site's domain, e.g. de-linker.com. */
printf( esc_html__( "On %s, a conversation with Genie, Linker's AI assistant, was requested for this email address.", 'linker-commerce' ), esc_html( (string) wp_parse_url( home_url(), PHP_URL_HOST ) ) );
?>
</p>
<p><a href="<?php echo esc_url( $link ); ?>" style="color: #0c7f73; font-weight: 600;"><?php esc_html_e( 'Send me the conversation', 'linker-commerce' ); ?></a></p>
<p>
<?php
/* translators: %d: how many hours the link works. */
printf( esc_html( _n( 'The link works once and expires after %d hour.', 'The link works once and expires after %d hours.', $hours, 'linker-commerce' ) ), (int) $hours );
?>
</p>
<p><?php esc_html_e( 'The conversation is sent only once the link is opened. If you did not ask for it, you can ignore this email.', 'linker-commerce' ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
 */
do_action( 'woocommerce_email_footer', $email );
