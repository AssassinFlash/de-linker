<?php
/**
 * Email to the team: a new customer registered.
 *
 * A theme may override it as woocommerce/emails/linker-new-customer.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var WC_Email $email              The email.
 */

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\AccountsAdmin;
use Linker\Commerce\Registration\CustomerRole;
use Linker\Commerce\Registration\VatProfile;

defined( 'ABSPATH' ) || exit;

$linker_customer = new WC_Customer( $customer->ID );
$linker_rows     = array(
	__( 'Company', 'linker-commerce' )       => $linker_customer->get_billing_company(),
	__( 'Business type', 'linker-commerce' ) => CustomerRole::label( (string) $linker_customer->get_meta( CustomerRole::META ) ),
	__( 'Name', 'linker-commerce' )          => trim( $linker_customer->get_billing_first_name() . ' ' . $linker_customer->get_billing_last_name() ),
	__( 'Email', 'linker-commerce' )         => $linker_customer->get_email(),
	__( 'Address', 'linker-commerce' )       => wp_strip_all_tags( str_replace( '<br/>', ', ', WC()->countries->get_formatted_address( $linker_customer->get_billing() ) ) ),
	__( 'VAT ID', 'linker-commerce' )        => (string) $linker_customer->get_meta( VatProfile::VAT_META ),
	__( 'VAT check', 'linker-commerce' )     => VatProfile::label( (string) get_user_meta( $customer->ID, VatProfile::STATUS_META, true ) ),
	__( 'Approval', 'linker-commerce' )      => Approval::label( Approval::PENDING ),
);

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );
?>
<table class="td" cellspacing="0" cellpadding="6" border="1" style="width: 100%;">
	<?php foreach ( $linker_rows as $linker_label => $linker_value ) : ?>
		<tr>
			<th class="td" scope="row" style="text-align: left;"><?php echo esc_html( $linker_label ); ?></th>
			<td class="td" style="text-align: left;"><?php echo esc_html( '' !== $linker_value ? $linker_value : '—' ); ?></td>
		</tr>
	<?php endforeach; ?>
</table>
<p><a href="<?php echo esc_url( AccountsAdmin::url( $customer->ID ) ); ?>"><?php esc_html_e( 'Open the customer', 'linker-commerce' ); ?></a></p>
<?php
if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
