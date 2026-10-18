<?php
/**
 * The Genie part of the team mail of a contact message (#243): why Genie
 * offered the contact, the page, the customer's last messages, the link to
 * the whole conversation and the solution draft. #246's team mail
 * (linker-new-inquiry.php) includes it when the record carries a hand-off.
 *
 * A theme may override it as woocommerce/emails/linker-genie-handoff.php.
 *
 * @package Linker\Commerce
 *
 * @var array<string, mixed> $handoff The hand-off (Linker\Tools\Genie\ContactRequest::handoff()); its
 *                                    `reason_label` is in the site's language, labelled where the reasons are.
 */

defined( 'ABSPATH' ) || exit;

$linker_page         = is_array( $handoff['page'] ?? null ) ? $handoff['page'] : array();
$linker_conversation = is_array( $handoff['conversation'] ?? null ) ? $handoff['conversation'] : array();
$linker_summary      = is_array( $handoff['summary'] ?? null ) ? $handoff['summary'] : array();
$linker_draft        = is_array( $handoff['draft'] ?? null ) ? $handoff['draft'] : array();
$linker_page_url     = (string) ( $linker_page['url'] ?? '' );
$linker_page_title   = (string) ( $linker_page['title'] ?? '' );
?>
<h2><?php esc_html_e( 'Through Genie', 'linker-commerce' ); ?></h2>
<p><?php esc_html_e( 'Genie promised a reply within one business day.', 'linker-commerce' ); ?></p>
<table class="td" cellspacing="0" cellpadding="6" border="1" style="width: 100%;">
	<tr>
		<th class="td" scope="row" style="text-align: left;"><?php esc_html_e( 'Reason', 'linker-commerce' ); ?></th>
		<td class="td" style="text-align: left;"><?php echo esc_html( (string) ( $handoff['reason_label'] ?? '' ) ); ?></td>
	</tr>
	<tr>
		<th class="td" scope="row" style="text-align: left;"><?php esc_html_e( 'Page', 'linker-commerce' ); ?></th>
		<td class="td" style="text-align: left;">
			<?php if ( '' !== $linker_page_url ) : ?>
				<a href="<?php echo esc_url( $linker_page_url ); ?>"><?php echo esc_html( '' !== $linker_page_title ? $linker_page_title : $linker_page_url ); ?></a>
			<?php else : ?>
				<?php echo esc_html( '' !== $linker_page_title ? $linker_page_title : '—' ); ?>
			<?php endif; ?>
		</td>
	</tr>
</table>

<h3><?php esc_html_e( 'The customer\'s last messages, newest first', 'linker-commerce' ); ?></h3>
<?php if ( array() === $linker_summary ) : ?>
	<p>—</p>
<?php else : ?>
	<ol>
		<?php foreach ( $linker_summary as $linker_line ) : ?>
			<li><?php echo nl2br( esc_html( (string) $linker_line ) ); ?></li>
		<?php endforeach; ?>
	</ol>
<?php endif; ?>
<p><a href="<?php echo esc_url( (string) ( $linker_conversation['url'] ?? '' ) ); ?>"><?php esc_html_e( 'Open the conversation', 'linker-commerce' ); ?></a></p>

<h3><?php esc_html_e( 'Solution draft', 'linker-commerce' ); ?></h3>
<?php if ( array() === $linker_draft ) : ?>
	<p><?php esc_html_e( 'No products in the solution draft.', 'linker-commerce' ); ?></p>
<?php else : ?>
	<table class="td" cellspacing="0" cellpadding="6" border="1" style="width: 100%;">
		<thead>
			<tr>
				<th class="td" scope="col" style="text-align: left;"><?php esc_html_e( 'Product', 'linker-commerce' ); ?></th>
				<th class="td" scope="col" style="text-align: left;"><?php esc_html_e( 'Item number', 'linker-commerce' ); ?></th>
				<th class="td" scope="col" style="text-align: left;"><?php esc_html_e( 'Quantity', 'linker-commerce' ); ?></th>
			</tr>
		</thead>
		<tbody>
			<?php foreach ( $linker_draft as $linker_line ) : ?>
				<tr>
					<td class="td" style="text-align: left;"><?php echo esc_html( (string) ( $linker_line['name'] ?? '' ) ); ?></td>
					<td class="td" style="text-align: left;"><?php echo esc_html( '' !== (string) ( $linker_line['sku'] ?? '' ) ? (string) $linker_line['sku'] : '—' ); ?></td>
					<td class="td" style="text-align: left;"><?php echo esc_html( (string) (int) ( $linker_line['quantity'] ?? 0 ) ); ?></td>
				</tr>
			<?php endforeach; ?>
		</tbody>
	</table>
<?php endif; ?>
