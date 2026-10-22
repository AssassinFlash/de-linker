<?php
/** Research only: read the exact Woo fields behind an existing local feed. */
$input = $args[0] ?? '';
$feed = json_decode( file_get_contents( $input ), true, 512, JSON_THROW_ON_ERROR );
$rows = array();
foreach ( $feed['products'] as $product ) {
    $id = (int) $product['id'];
    $raw = get_post_meta( $id, \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY, true );
    if ( is_string( $raw ) ) {
        $raw = json_decode( $raw, true, 512, JSON_THROW_ON_ERROR );
    }
    $rows[] = array(
        'id' => $id,
        'model' => $product['model'],
        'language' => function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $id ) : null,
        'figures' => is_array( $raw ) ? (object) $raw : (object) array(),
    );
}
echo wp_json_encode( array( 'captured_at' => gmdate( 'c' ), 'products' => $rows ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
