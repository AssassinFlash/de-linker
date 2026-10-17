<?php
/**
 * Email to the visitor: a Genie conversation they asked to receive.
 *
 * A theme may override it as woocommerce/emails/linker-genie-conversation.php.
 *
 * @package Linker\Commerce
 *
 * @var Linker\Commerce\Genie\Conversation $conversation       The conversation.
 *
 * The colours are the receipt email's (linker-contact-receipt.php): the
 * site's teal for Genie's side, a quiet line for the customer's, the deep ink
 * for text; a product's model in the muted ink (--proto-ink-muted-deep,
 * content/windpress/tokens.css). Emails carry inline styles: mail clients
 * read no stylesheet.
 * @var string                             $email_heading      Heading.
 * @var string                             $additional_content Closing paragraph from the email settings.
 * @var bool                               $sent_to_admin      False.
 * @var bool                               $plain_text         False.
 * @var WC_Email                           $email              The email.
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
printf( esc_html__( "As requested on %s, here is your conversation with Genie, Linker's AI assistant.", 'linker-commerce' ), esc_html( (string) wp_parse_url( home_url(), PHP_URL_HOST ) ) );
?>
</p>
<?php foreach ( $conversation->messages as $message ) : ?>
<p style="margin: 16px 0 4px;"><strong><?php echo 'assistant' === $message['role'] ? esc_html__( 'Genie', 'linker-commerce' ) : esc_html__( 'You', 'linker-commerce' ); ?></strong></p>
<blockquote style="margin: 0 0 8px; padding: 8px 16px; border-left: 3px solid <?php echo 'assistant' === $message['role'] ? '#0c7f73' : '#c8d3cf'; ?>; color: #15372f;">
	<?php echo nl2br( esc_html( $message['content'] ) ); ?>
	<?php if ( array() !== $message['products'] ) : ?>
	<ul style="margin: 8px 0 0; padding-left: 18px;">
		<?php foreach ( $message['products'] as $product ) : ?>
		<li style="margin: 4px 0;">
			<a href="<?php echo esc_url( $product['url'] ); ?>" style="color: #0c7f73;"><?php echo esc_html( $product['title'] ); ?></a>
			<?php if ( '' !== $product['model'] ) : ?>
			<br /><span style="color: #596e67;"><?php echo esc_html__( 'Model', 'linker-commerce' ) . ' ' . esc_html( $product['model'] ); ?></span>
			<?php endif; ?>
		</li>
		<?php endforeach; ?>
	</ul>
	<?php endif; ?>
</blockquote>
<?php endforeach; ?>
<p style="margin-top: 24px;"><?php esc_html_e( "Genie is an AI system, and its answers can contain mistakes. Where an answer differs from the product's datasheet, the datasheet applies.", 'linker-commerce' ); ?></p>
<p><?php esc_html_e( 'Replies to this email go to the Linker team.', 'linker-commerce' ); ?></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/**
 * This action is documented in woocommerce/templates/emails/customer-on-hold-order.php
 */
do_action( 'woocommerce_email_footer', $email );
