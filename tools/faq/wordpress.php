<?php
/**
 * The WordPress side of the tools/faq scripts: they hand this file to
 * `wp eval-file -` with the request (JSON, base64) in place of the
 * placeholder at the end. Evaluated code cannot start with a strict_types
 * declaration.
 *
 * Three actions, one per caller:
 *
 * - `export` (export.py): every published product's existing questions, read
 *   out of the legacy ACF JSON, with the German question paired by position
 *   when the two lists are the same length.
 * - `import` (import.py): writes `_linker_faqs` through the plugin's own
 *   Faqs::encode()/mirror_to_twin(), after checking the record still names the
 *   product it was written for.
 * - `documents` (thumbs.py): the document register's own reading
 *   (DocumentLibrary::documents()) — the URLs and types the thumbnail
 *   pipeline downloads and renders, so the pipeline sees exactly the files
 *   the page lists.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets any request JSON sit in the single-quoted literal the Python scripts write into this file.
	$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
	$action  = $request['action'] ?? '';
	$marker  = $request['marker'] ?? '';
	if ( '' === $marker ) {
		throw new RuntimeException( 'FAQ WP-CLI request has no marker.' );
	}

	$acf_faqs = static function ( string $raw ): array {
		if ( '' === $raw ) {
			return array();
		}
		$decoded = json_decode( $raw, true );
		$faqs    = is_array( $decoded ) ? ( $decoded['faqs'] ?? null ) : null;
		if ( ! is_array( $faqs ) ) {
			return array();
		}
		$out = array();
		foreach ( $faqs as $index => $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$question = trim( (string) ( $item['faq_question'] ?? '' ) );
			if ( '' === $question ) {
				continue;
			}
			$out[] = array(
				'index'    => (int) $index,
				'category' => (string) ( $item['faq_category'] ?? '' ),
				'question' => $question,
			);
		}
		return $out;
	};

	$attribute = static function ( WC_Product $product, string $name ): string {
		return $product->get_attribute( $name );
	};

	if ( 'export' === $action ) {
		$query    = new WP_Query(
			array(
				'post_type'      => 'product',
				'post_status'    => 'publish',
				'posts_per_page' => -1,
				'orderby'        => 'ID',
				'order'          => 'ASC',
				'fields'         => 'ids',
			)
		);
		$products = array();
		$ids      = is_array( $query->posts ) ? $query->posts : array();
		foreach ( $ids as $product_id ) {
			if ( ! is_int( $product_id ) ) {
				continue;
			}
			$product = wc_get_product( $product_id );
			if ( ! $product instanceof WC_Product ) {
				continue;
			}
			$en_raw    = (string) get_post_meta( $product_id, '_tv_legacy_acf_json', true );
			$de_raw    = (string) get_post_meta( $product_id, '_linker_de_acf_json', true );
			$en_faqs   = $acf_faqs( $en_raw );
			$de_faqs   = $acf_faqs( $de_raw );
			$questions = array();
			// The legacy ACF rows share no key across languages, so the German
			// question can only follow the English position — and only while
			// both lists ran through the same editor. Lists of different
			// length do not pair; exporting the English question alone beats
			// pairing a German question onto the wrong topic.
			$paired = count( $en_faqs ) === count( $de_faqs );
			foreach ( $en_faqs as $i => $en ) {
				$questions[] = array(
					'index'       => $en['index'],
					'category'    => $en['category'],
					'question_en' => $en['question'],
					'question_de' => $paired ? ( $de_faqs[ $i ]['question'] ?? '' ) : '',
				);
			}
			$series  = '';
			$decoded = json_decode( $en_raw, true );
			if ( is_array( $decoded ) ) {
				$series = (string) ( $decoded['product_series'] ?? '' );
			}
			$products[] = array(
				'id'        => $product_id,
				'slug'      => $product->get_slug(),
				'sku'       => $product->get_sku(),
				'title'     => $product->get_name(),
				'brand'     => $attribute( $product, 'pa_brand' ),
				'model'     => $attribute( $product, 'pa_model' ),
				'series'    => $series,
				'questions' => $questions,
			);
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for tools/faq/export.py on the command line, not HTML.
		echo $marker . wp_json_encode( array( 'products' => $products ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
		return;
	}

	if ( 'documents' === $action ) {
		if ( ! class_exists( \Linker\Commerce\Products\DocumentLibrary::class ) ) {
			// The register's URLs are the plugin's own reading; without the
			// plugin the eval'd script would drift from it.
			throw new RuntimeException( 'linker-commerce must be active on the thumbnails target.' );
		}
		$register = array();
		foreach ( ( new \Linker\Commerce\Products\DocumentLibrary() )->documents() as $document ) {
			$register[] = array(
				'url'  => (string) $document['url'],
				'type' => (string) $document['type'],
			);
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for tools/faq/thumbs.py on the command line, not HTML.
		echo $marker . wp_json_encode( array( 'documents' => $register ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
		return;
	}

	if ( 'import' !== $action ) {
		throw new RuntimeException( 'Unknown FAQ WP-CLI action.' );
	}
	if ( ! class_exists( \Linker\Commerce\Products\Faqs::class ) ) {
		// The shape the import writes is the plugin's rule; without the
		// plugin the eval'd script would drift from it.
		throw new RuntimeException( 'linker-commerce must be active on the import target.' );
	}

	$written = array();
	foreach ( $request['products'] as $row ) {
		$product_id = (int) ( $row['id'] ?? 0 );
		$product    = wc_get_product( $product_id );
		if ( ! $product instanceof WC_Product ) {
			throw new RuntimeException( esc_html( "No product {$product_id}." ) );
		}
		// The record names the product it was written for: an id that now
		// belongs to another slug would put the answers on the wrong product.
		$expected = (string) ( $row['slug'] ?? '' );
		if ( '' !== $expected && $product->get_slug() !== $expected ) {
			throw new RuntimeException(
				esc_html( "Slug mismatch for {$product_id}: the record says '{$expected}', the product is '" . $product->get_slug() . "'." )
			);
		}
		$items = is_array( $row['items'] ?? null ) ? $row['items'] : array();
		$json  = \Linker\Commerce\Products\Faqs::encode( $items );
		update_post_meta( $product_id, \Linker\Commerce\Products\Faqs::META_KEY, wp_slash( $json ) );
		\Linker\Commerce\Products\Faqs::mirror_to_twin( $product_id, $json );
		$read      = (string) get_post_meta( $product_id, \Linker\Commerce\Products\Faqs::META_KEY, true );
		$written[] = array(
			'id'    => $product_id,
			'slug'  => $product->get_slug(),
			'count' => count( \Linker\Commerce\Products\Faqs::normalize( $items ) ),
			'done'  => $read === $json,
		);
	}
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for tools/faq/import.py on the command line, not HTML.
	echo $marker . wp_json_encode( array( 'written' => $written ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
} )( '15-faq-payload' );
