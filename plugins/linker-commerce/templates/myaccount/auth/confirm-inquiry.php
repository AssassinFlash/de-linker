<?php
/**
 * Confirm a guest inquiry's transfer to the current account.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

$order = \Linker\Commerce\Inquiry\AccountLink::awaiting_confirmation();
if ( ! $order ) {
	return;
}
?>
<form method="post">
	<p><?php /* translators: %s: inquiry number. */ printf( esc_html__( 'Add inquiry #%s to your account?', 'linker-commerce' ), esc_html( $order->get_order_number() ) ); ?></p>
	<?php wp_nonce_field( 'linker_claim_' . $order->get_id(), 'linker_claim_nonce' ); ?>
	<button class="button" type="submit"><?php esc_html_e( 'Link inquiry to my account', 'linker-commerce' ); ?></button>
</form>
