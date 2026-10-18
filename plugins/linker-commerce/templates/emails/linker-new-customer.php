<?php
/**
 * Email to the team: a new customer registered.
 *
 * A theme may override it as woocommerce/emails/linker-new-customer.php.
 *
 * @package Linker\Commerce
 *
 * @var WP_User  $customer           The customer.
 * @var list<array{key: string, label: string, value: string, website: bool}> $registration_rows The same rows the accounts page reads.
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var WC_Email $email              The email.
 */

use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Registration\AccountsAdmin;
use Linker\Commerce\Registration\VatProfile;

defined( 'ABSPATH' ) || exit;

// One reader for the notification and the staff accounts page (ticket #225):
// RegistrationInformation reads the field definitions, so the website added to
// the form appears in both without a second list. The VAT verdict and the
// approval state are not registration fields; they follow the fields.
$linker_rows = array();
foreach ( $registration_rows as $linker_row ) {
	$linker_rows[ $linker_row['label'] ] = $linker_row['value'];
}
$linker_rows[ __( 'VAT check', 'linker-commerce' ) ] = VatProfile::label( (string) get_user_meta( $customer->ID, VatProfile::STATUS_META, true ) );
$linker_rows[ __( 'Approval', 'linker-commerce' ) ]  = Approval::label( Approval::PENDING );

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
