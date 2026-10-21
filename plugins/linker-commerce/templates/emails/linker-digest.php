<?php
/**
 * Email to the team: the daily digest.
 *
 * A theme may override it as woocommerce/emails/linker-digest.php.
 * Presentation rules live in DigestEmail::presentation_css() and are inlined
 * by WooCommerce when the message is sent. The strings are the reviewed copy.
 *
 * @package Linker\Commerce
 *
 * @var string   $email_heading      Heading.
 * @var string   $additional_content Closing paragraph from the email settings.
 * @var bool     $sent_to_admin      True.
 * @var bool     $plain_text         False.
 * @var WC_Email $email              The email.
 * @var list<Linker\Commerce\Digest\Block> $blocks The blocks of the digest, in order.
 */

defined( 'ABSPATH' ) || exit;

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_header', $email_heading, $email );

$rendered = array();
foreach ( $blocks as $block ) {
	$rendered[] = array(
		'block'   => $block,
		'entries' => $block->entries(),
	);
}

$date = '';
if ( isset( $email->placeholders['{date}'] ) && is_string( $email->placeholders['{date}'] ) ) {
	$date = $email->placeholders['{date}'];
}
if ( '' !== $date ) {
	echo '<p class="linker-digest-date">' . esc_html( $date ) . '</p>' . "\n";
}

$open  = array();
$clear = array();
foreach ( $rendered as $item ) {
	if ( array() === $item['entries'] ) {
		$clear[] = $item;
		continue;
	}
	$open[] = $item;
}

foreach ( $open as $item ) {
	$block   = $item['block'];
	$entries = $item['entries'];
	echo '<table class="linker-digest-card" role="presentation" width="100%" cellpadding="0" cellspacing="0">' . "\n";
	echo '<tr><td class="linker-digest-num">' . esc_html( (string) count( $entries ) ) . '</td>';
	echo '<td class="linker-digest-title">' . esc_html( $block->title() ) . '</td></tr>' . "\n";
	echo '<tr><td class="linker-digest-body" colspan="2">';
	echo '<table class="linker-digest-rows" role="presentation" width="100%" cellpadding="0" cellspacing="0">' . "\n";
	foreach ( $entries as $entry ) {
		echo '<tr><td class="linker-digest-main">' . esc_html( $entry['label'] );
		if ( '' !== $entry['detail'] ) {
			echo '<br><span class="linker-digest-detail">' . esc_html( $entry['detail'] ) . '</span>';
		}
		if ( '' !== $entry['url'] && '' !== $entry['link_text'] ) {
			echo '<br><a class="linker-digest-link" href="' . esc_url( $entry['url'] ) . '">' . esc_html( $entry['link_text'] ) . '</a>';
		}
		echo '</td></tr>' . "\n";
	}
	echo '</table></td></tr></table>' . "\n";
}

if ( array() !== $clear ) {
	echo '<table class="linker-digest-quiet" role="presentation" width="100%" cellpadding="0" cellspacing="0">' . "\n";
	foreach ( $clear as $item ) {
		echo '<tr><td class="linker-digest-empty"><strong>' . esc_html( $item['block']->title() ) . '</strong><br>' . esc_html( $item['block']->empty_text() ) . '</td></tr>' . "\n";
	}
	echo '</table>' . "\n";
}

if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
