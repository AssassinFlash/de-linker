<?php
/**
 * Email to the team: the VAT check of a customer changed.
 *
 * A theme may override it as woocommerce/emails/linker-vat-review.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var string   $previous           Verdict before.
 * @var string   $current            Verdict now.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var WC_Email $email              The email.
 */

use Linker\Commerce\Registration\VatProfile;

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<p>
<?php
printf(
	/* translators: 1: company, 2: VAT ID. */
	esc_html__( 'The VAT check of %1$s (VAT ID %2$s) changed.', 'linker-commerce' ),
	esc_html( (string) get_user_meta( $customer->ID, 'billing_company', true ) ),
	esc_html( (string) get_user_meta( $customer->ID, VatProfile::VAT_META, true ) )
);
?>
</p>
<p>
<?php
printf(
	/* translators: 1: verdict before, 2: verdict now. */
	esc_html__( 'Before: %1$s. Now: %2$s.', 'linker-commerce' ),
	esc_html( VatProfile::label( $previous ) ),
	esc_html( VatProfile::label( $current ) )
);
?>
</p>
<p><a href="<?php echo esc_url( get_edit_user_link( $customer->ID ) ); ?>"><?php esc_html_e( 'Open the customer', 'linker-commerce' ); ?></a></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
