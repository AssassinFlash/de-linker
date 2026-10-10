<?php
/**
 * The Proforma invoice, rendered to PDF.
 *
 * A theme may override it as woocommerce/proforma/proforma.php.
 *
 * @package Linker\Commerce
 *
 * @var array{
 *     number: string,
 *     inquiry: string,
 *     issued: string,
 *     valid_until: string,
 *     seller: array{name: string, vat_id: string, address: list<string>, email: string},
 *     bank: array{holder: string, name: string, iban: string, bic: string},
 *     buyer: array{company: string, name: string, address: list<string>, vat_id: string, email: string},
 *     lines: list<array{position: int, name: string, sku: string, quantity: int, unit: string, total: string}>,
 *     fees: list<array{name: string, total: string}>,
 *     subtotal: string,
 *     taxes: list<array{label: string, amount: string}>,
 *     total: string
 * } $proforma Document data.
 */

defined( 'ABSPATH' ) || exit;

$linker_seller = $proforma['seller'];
$linker_bank   = $proforma['bank'];
$linker_buyer  = $proforma['buyer'];
?>
<!DOCTYPE html>
<html lang="<?php echo esc_attr( str_replace( '_', '-', determine_locale() ) ); ?>">
<head>
<meta charset="utf-8">
<title><?php echo esc_html( $proforma['number'] ); ?></title>
<style>
	@page { margin: 15mm 16mm 20mm 16mm; }
	body { font-family: 'DejaVu Sans', sans-serif; font-size: 9pt; color: #1d1d1b; line-height: 1.35; }
	h1 { font-size: 16pt; margin: 0 0 4mm 0; }
	table { border-collapse: collapse; width: 100%; }
	.head td { vertical-align: top; }
	.seller { text-align: right; font-size: 8.5pt; }
	.seller strong { font-size: 10pt; }
	.meta td { padding: 1mm 0; }
	.meta td.label { color: #5b5b5b; width: 32mm; padding-right: 3mm; }
	.buyer { margin: 5mm 0; }
	.lines th { text-align: left; border-bottom: 0.6pt solid #1d1d1b; padding: 1.5mm 1mm; font-size: 8.5pt; }
	.lines td { border-bottom: 0.3pt solid #c8c8c8; padding: 1.5mm 1mm; vertical-align: top; }
	.lines .num { text-align: right; white-space: nowrap; }
	.sku { color: #5b5b5b; font-size: 8pt; }
	.totals { width: 75mm; margin-left: auto; margin-top: 3mm; }
	.totals td { padding: 1mm; }
	.totals td.num { text-align: right; white-space: nowrap; }
	.totals tr.grand td { border-top: 0.6pt solid #1d1d1b; font-weight: bold; }
	.box { margin-top: 4mm; border: 0.6pt solid #1d1d1b; padding: 3mm 4mm; }
	.box h2 { font-size: 10pt; margin: 0 0 2mm 0; }
	.box td { padding: 0.6mm 0; }
	/* Wide enough for the longest German label, "Verwendungszweck". */
	.box td.label { color: #5b5b5b; width: 38mm; padding-right: 3mm; }
	.note { margin-top: 5mm; font-size: 8.5pt; }
	.footer { position: fixed; bottom: -12mm; left: 0; right: 0; font-size: 7.5pt; color: #5b5b5b; text-align: center; }
</style>
</head>
<body>
<div class="footer">
	<?php echo esc_html( implode( ' · ', array_filter( array_merge( array( $linker_seller['name'] ), $linker_seller['address'], array( $linker_seller['email'] ) ) ) ) ); ?>
</div>

<table class="head">
	<tr>
		<td>
			<h1><?php esc_html_e( 'Proforma invoice', 'linker-commerce' ); ?></h1>
			<table class="meta">
				<tr><td class="label"><?php esc_html_e( 'Proforma no.', 'linker-commerce' ); ?></td><td><strong><?php echo esc_html( $proforma['number'] ); ?></strong></td></tr>
				<tr><td class="label"><?php esc_html_e( 'Inquiry no.', 'linker-commerce' ); ?></td><td><?php echo esc_html( $proforma['inquiry'] ); ?></td></tr>
				<tr><td class="label"><?php esc_html_e( 'Date', 'linker-commerce' ); ?></td><td><?php echo esc_html( $proforma['issued'] ); ?></td></tr>
				<tr><td class="label"><?php esc_html_e( 'Valid until', 'linker-commerce' ); ?></td><td><?php echo esc_html( $proforma['valid_until'] ); ?></td></tr>
			</table>
		</td>
		<td class="seller">
			<strong><?php echo esc_html( $linker_seller['name'] ); ?></strong><br>
			<?php foreach ( $linker_seller['address'] as $linker_line ) : ?>
				<?php echo esc_html( $linker_line ); ?><br>
			<?php endforeach; ?>
			<?php echo esc_html( $linker_seller['email'] ); ?>
			<?php if ( '' !== $linker_seller['vat_id'] ) : ?>
				<br><?php esc_html_e( 'VAT ID', 'linker-commerce' ); ?>: <?php echo esc_html( $linker_seller['vat_id'] ); ?>
			<?php endif; ?>
		</td>
	</tr>
</table>

<div class="buyer">
	<?php if ( '' !== $linker_buyer['company'] ) : ?>
		<strong><?php echo esc_html( $linker_buyer['company'] ); ?></strong><br>
	<?php endif; ?>
	<?php echo esc_html( $linker_buyer['name'] ); ?><br>
	<?php foreach ( $linker_buyer['address'] as $linker_line ) : ?>
		<?php echo esc_html( wp_strip_all_tags( $linker_line ) ); ?><br>
	<?php endforeach; ?>
	<?php if ( '' !== $linker_buyer['vat_id'] ) : ?>
		<?php esc_html_e( 'VAT ID', 'linker-commerce' ); ?>: <?php echo esc_html( $linker_buyer['vat_id'] ); ?><br>
	<?php endif; ?>
	<?php echo esc_html( $linker_buyer['email'] ); ?>
</div>

<table class="lines">
	<thead>
		<tr>
			<th><?php esc_html_e( 'Pos.', 'linker-commerce' ); ?></th>
			<th><?php esc_html_e( 'Product', 'linker-commerce' ); ?></th>
			<th class="num"><?php esc_html_e( 'Qty', 'linker-commerce' ); ?></th>
			<th class="num"><?php esc_html_e( 'Unit price (net)', 'linker-commerce' ); ?></th>
			<th class="num"><?php esc_html_e( 'Amount (net)', 'linker-commerce' ); ?></th>
		</tr>
	</thead>
	<tbody>
		<?php foreach ( $proforma['lines'] as $linker_line ) : ?>
			<tr>
				<td><?php echo esc_html( (string) $linker_line['position'] ); ?></td>
				<td>
					<?php echo esc_html( $linker_line['name'] ); ?>
					<?php if ( '' !== $linker_line['sku'] ) : ?>
						<br><span class="sku"><?php esc_html_e( 'Product no.', 'linker-commerce' ); ?> <?php echo esc_html( $linker_line['sku'] ); ?></span>
					<?php endif; ?>
				</td>
				<td class="num"><?php echo esc_html( (string) $linker_line['quantity'] ); ?></td>
				<td class="num"><?php echo wp_kses_post( $linker_line['unit'] ); ?></td>
				<td class="num"><?php echo wp_kses_post( $linker_line['total'] ); ?></td>
			</tr>
		<?php endforeach; ?>
		<?php foreach ( $proforma['fees'] as $linker_fee ) : ?>
			<tr>
				<td></td>
				<td><?php echo esc_html( $linker_fee['name'] ); ?></td>
				<td class="num"></td>
				<td class="num"></td>
				<td class="num"><?php echo wp_kses_post( $linker_fee['total'] ); ?></td>
			</tr>
		<?php endforeach; ?>
	</tbody>
</table>

<table class="totals">
	<tr><td><?php esc_html_e( 'Subtotal (net)', 'linker-commerce' ); ?></td><td class="num"><?php echo wp_kses_post( $proforma['subtotal'] ); ?></td></tr>
	<?php foreach ( $proforma['taxes'] as $linker_tax ) : ?>
		<tr><td><?php echo esc_html( $linker_tax['label'] ); ?></td><td class="num"><?php echo wp_kses_post( $linker_tax['amount'] ); ?></td></tr>
	<?php endforeach; ?>
	<tr class="grand"><td><?php esc_html_e( 'Total', 'linker-commerce' ); ?></td><td class="num"><?php echo wp_kses_post( $proforma['total'] ); ?></td></tr>
</table>

<p class="note">
	<?php
	/* translators: %s: last day of validity. */
	printf( esc_html__( 'This Proforma invoice is valid until %s.', 'linker-commerce' ), esc_html( $proforma['valid_until'] ) );
	?>
	<?php esc_html_e( 'This document is not an invoice within the meaning of Section 14 of the German VAT Act (UStG). The invoice will be issued separately.', 'linker-commerce' ); ?>
</p>

<div class="box">
	<h2><?php esc_html_e( 'Bank transfer', 'linker-commerce' ); ?></h2>
	<p>
		<?php
		/* translators: %s: Proforma number. */
		printf( esc_html__( 'Please transfer the total to the account below and give %s as the reference.', 'linker-commerce' ), '<strong>' . esc_html( $proforma['number'] ) . '</strong>' );
		?>
	</p>
	<table>
		<tr><td class="label"><?php esc_html_e( 'Account holder', 'linker-commerce' ); ?></td><td><?php echo esc_html( '' !== $linker_bank['holder'] ? $linker_bank['holder'] : $linker_seller['name'] ); ?></td></tr>
		<?php if ( '' !== $linker_bank['name'] ) : ?>
			<tr><td class="label"><?php esc_html_e( 'Bank', 'linker-commerce' ); ?></td><td><?php echo esc_html( $linker_bank['name'] ); ?></td></tr>
		<?php endif; ?>
		<tr><td class="label"><?php esc_html_e( 'IBAN', 'linker-commerce' ); ?></td><td><?php echo esc_html( trim( chunk_split( $linker_bank['iban'], 4, ' ' ) ) ); ?></td></tr>
		<?php if ( '' !== $linker_bank['bic'] ) : ?>
			<tr><td class="label"><?php esc_html_e( 'BIC', 'linker-commerce' ); ?></td><td><?php echo esc_html( $linker_bank['bic'] ); ?></td></tr>
		<?php endif; ?>
		<tr><td class="label"><?php esc_html_e( 'Reference', 'linker-commerce' ); ?></td><td><?php echo esc_html( $proforma['number'] ); ?></td></tr>
	</table>
</div>

</body>
</html>
