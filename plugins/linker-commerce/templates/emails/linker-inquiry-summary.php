<?php
/**
 * Email to the team: the conversation summary an inquiry carries (#244).
 *
 * A theme may override it as woocommerce/emails/linker-inquiry-summary.php.
 *
 * @package Linker\Commerce
 *
 * @var array<string, mixed> $summary Linker\Tools\Genie\InquirySummary's answer.
 */

defined( 'ABSPATH' ) || exit;

$linker_summary = isset( $summary['summary'] ) ? (string) $summary['summary'] : '';
if ( '' === trim( $linker_summary ) ) {
	return;
}
?>
<h2><?php esc_html_e( 'Conversation with Genie', 'linker-commerce' ); ?></h2>
<p><?php echo esc_html( $linker_summary ); ?></p>
<?php if ( array() !== (array) ( $summary['quantities'] ?? array() ) ) : ?>
<p><strong><?php esc_html_e( 'Quantities from the conversation', 'linker-commerce' ); ?></strong><br />
	<?php
	$linker_lines = array();
	foreach ( (array) $summary['quantities'] as $linker_line ) {
		$linker_id = (int) ( $linker_line['product_id'] ?? 0 );
		if ( $linker_id < 1 ) {
			continue;
		}
		$linker_lines[] = sprintf(
			'%1$s × %2$d',
			get_the_title( $linker_id ),
			(int) ( $linker_line['quantity'] ?? 0 )
		);
	}
	echo esc_html( implode( ', ', $linker_lines ) );
	?>
</p>
<?php endif; ?>
<?php if ( array() !== (array) ( $summary['conditions'] ?? array() ) ) : ?>
<p><strong><?php esc_html_e( 'Conditions from the conversation', 'linker-commerce' ); ?></strong><br />
	<?php echo esc_html( implode( ' · ', array_map( 'strval', (array) $summary['conditions'] ) ) ); ?>
</p>
<?php endif; ?>
<?php if ( '' !== (string) ( $summary['note'] ?? '' ) ) : ?>
<p><strong><?php esc_html_e( 'Latest message', 'linker-commerce' ); ?></strong><br />
	<?php echo esc_html( (string) $summary['note'] ); ?>
</p>
<?php endif; ?>
<?php if ( 'rule' === ( $summary['source'] ?? '' ) ) : ?>
<p><em>
	<?php
	printf(
		/* translators: %s: why the model summary was not used (a short cause). */
		esc_html__( 'Assembled from the customer\'s messages (%s).', 'linker-commerce' ),
		esc_html( (string) ( $summary['reason'] ?? '' ) )
	);
	?>
</em></p>
<?php endif; ?>
