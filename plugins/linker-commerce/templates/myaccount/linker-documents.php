<?php
/**
 * Account page "Documents": Proforma invoices and design reports.
 *
 * A theme may override it as woocommerce/myaccount/linker-documents.php.
 *
 * @package Linker\Commerce
 *
 * @var list<array{title: string, date: int, url: string}> $documents The customer's documents, newest first.
 */

defined( 'ABSPATH' ) || exit;

if ( array() === $documents ) : ?>
	<p class="linker-empty"><?php esc_html_e( 'Your Proforma invoices and the design reports of your saved solutions will appear here.', 'linker-commerce' ); ?></p>
	<?php
	return;
endif;
?>
<table class="woocommerce-orders-table shop_table shop_table_responsive my_account_orders linker-documents">
	<thead>
		<tr>
			<th scope="col"><?php esc_html_e( 'Document', 'linker-commerce' ); ?></th>
			<th scope="col"><?php esc_html_e( 'Date', 'linker-commerce' ); ?></th>
			<th scope="col"><span class="screen-reader-text"><?php esc_html_e( 'Download', 'linker-commerce' ); ?></span></th>
		</tr>
	</thead>
	<tbody>
		<?php foreach ( $documents as $linker_document ) : ?>
			<tr>
				<th scope="row" data-title="<?php esc_attr_e( 'Document', 'linker-commerce' ); ?>"><?php echo esc_html( $linker_document['title'] ); ?></th>
				<td data-title="<?php esc_attr_e( 'Date', 'linker-commerce' ); ?>"><?php echo esc_html( wp_date( Linker\Commerce\Vocabulary\LocaleFormat::date_format(), $linker_document['date'] ) ); ?></td>
				<td><a class="woocommerce-button button" href="<?php echo esc_url( $linker_document['url'] ); ?>"><?php esc_html_e( 'Download (PDF)', 'linker-commerce' ); ?></a></td>
			</tr>
		<?php endforeach; ?>
	</tbody>
</table>
