<?php
/**
 * Email to the team: a message from the contact form.
 *
 * A theme may override it as woocommerce/emails/linker-contact-team.php.
 *
 * @package Linker\Commerce
 *
 * @var Linker\Commerce\Contact\Submission $submission        The visitor's message.
 * @var string                             $email_heading     Heading.
 * @var string                             $additional_content Closing paragraph from the email settings.
 * @var bool                               $sent_to_admin     True.
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
printf(
	/* translators: 1: the visitor's name, 2: the visitor's company, empty when not given. */
	esc_html__( '%1$s (%2$s) sent a message through the contact form.', 'linker-commerce' ),
	esc_html( $submission->name ),
	esc_html( '' !== $submission->company ? $submission->company : __( 'no company given', 'linker-commerce' ) )
);
?>
</p>
<p>
<?php
/* translators: %s: the visitor's email address. */
printf( esc_html__( 'Reply address: %s', 'linker-commerce' ), esc_html( $submission->email ) );
?>
<br />
<?php
printf(
	/* translators: %s: the topic the visitor picked, for example "A question". */
	esc_html__( 'This is about: %s', 'linker-commerce' ),
	esc_html( \Linker\Commerce\Contact\Form::intent_label( $submission->intent ) )
);
?>
<br />
<?php
printf(
	/* translators: %s: EN or DE, the language the visitor wrote in. */
	esc_html__( 'Written in: %s', 'linker-commerce' ),
	esc_html( $submission->is_german() ? 'DE' : 'EN' )
);
?>
</p>
<p><strong><?php esc_html_e( 'Message:', 'linker-commerce' ); ?></strong></p>
<blockquote style="margin: 0 0 16px; padding: 12px 16px; border-left: 3px solid #0c7f73; color: #15372f;">
<?php echo nl2br( esc_html( $submission->message ) ); ?>
</blockquote>
<p><?php esc_html_e( 'Answer this email to reply to the visitor directly.', 'linker-commerce' ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
*/
do_action( 'woocommerce_email_footer', $email );
