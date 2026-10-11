<?php
/**
 * Email to the team: the daily digest.
 *
 * A theme may override it as woocommerce/emails/linker-digest.php.
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

foreach ( $blocks as $block ) {
	echo '<h2>' . esc_html( $block->title() ) . '</h2>' . "\n";
	$entries = $block->entries();
	if ( array() === $entries ) {
		echo '<p>' . esc_html( $block->empty_text() ) . '</p>' . "\n";
		continue;
	}
	echo '<ul>' . "\n";
	foreach ( $entries as $entry ) {
		echo '<li>' . esc_html( $entry['label'] );
		if ( '' !== $entry['detail'] ) {
			echo '<br>' . esc_html( $entry['detail'] );
		}
		if ( '' !== $entry['url'] && '' !== $entry['link_text'] ) {
			echo '<br><a href="' . esc_url( $entry['url'] ) . '">' . esc_html( $entry['link_text'] ) . '</a>';
		}
		echo '</li>' . "\n";
	}
	echo '</ul>' . "\n";
}

if ( $additional_content ) {
	echo wp_kses_post( wpautop( wptexturize( $additional_content ) ) );
}

/** This action is documented in woocommerce/templates/emails/customer-on-hold-order.php */
do_action( 'woocommerce_email_footer', $email );
