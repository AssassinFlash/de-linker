<?php
/**
 * The WordPress side of tools/faq/export.py and import.py: reads existing
 * questions from the legacy ACF JSON, or writes `_linker_faqs`.
 *
 * The Python scripts hand this file to `wp eval-file -` with the request
 * (JSON, base64) in place of the placeholder at the end. Evaluated code
 * cannot start with a strict_types declaration.
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

	$acf_faqs = static function ( string $raw, string $question_key ): array {
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
			$question = trim( (string) ( $item[ $question_key ] ?? $item['faq_question'] ?? '' ) );
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
			$en_faqs   = $acf_faqs( $en_raw, 'faq_question' );
			$de_faqs   = $acf_faqs( $de_raw, 'faq_question' );
			$questions = array();
			foreach ( $en_faqs as $i => $en ) {
				$questions[] = array(
					'index'       => $en['index'],
					'category'    => $en['category'],
					'question_en' => $en['question'],
					'question_de' => $de_faqs[ $i ]['question'] ?? '',
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

	if ( 'import' !== $action ) {
		throw new RuntimeException( 'Unknown FAQ WP-CLI action.' );
	}

	$normalize = static function ( array $items ): array {
		$out = array();
		foreach ( $items as $item ) {
			if ( ! is_array( $item ) ) {
				continue;
			}
			$question = trim( (string) ( $item['question'] ?? '' ) );
			$citation = is_array( $item['citation'] ?? null ) ? $item['citation'] : array();
			$url      = trim( (string) ( $citation['url'] ?? '' ) );
			$page     = $citation['page'] ?? 0;
			$page     = is_numeric( $page ) ? (int) $page : 0;
			if ( '' === $question || '' === $url || $page < 1 ) {
				continue;
			}
			$row   = array(
				'question'    => $question,
				'answer'      => (string) ( $item['answer'] ?? '' ),
				'question_de' => (string) ( $item['question_de'] ?? '' ),
				'answer_de'   => (string) ( $item['answer_de'] ?? '' ),
				'citation'    => array(
					'url'  => $url,
					'page' => $page,
				),
			);
			$title = trim( (string) ( $citation['title'] ?? '' ) );
			if ( '' !== $title ) {
				$row['citation']['title'] = $title;
			}
			$out[] = $row;
		}
		return $out;
	};

	$written = array();
	foreach ( $request['products'] as $row ) {
		$product_id = (int) ( $row['id'] ?? 0 );
		$product    = wc_get_product( $product_id );
		if ( ! $product instanceof WC_Product ) {
			throw new RuntimeException( esc_html( "No product {$product_id}." ) );
		}
		$items = $normalize( is_array( $row['items'] ?? null ) ? $row['items'] : array() );
		$json  = (string) wp_json_encode( $items, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
		update_post_meta( $product_id, '_linker_faqs', wp_slash( $json ) );
		if ( function_exists( 'pll_get_post_language' ) && function_exists( 'pll_get_post' ) ) {
			$language = pll_get_post_language( $product_id );
			$twin_of  = 'en' === $language ? 'de' : ( 'de' === $language ? 'en' : '' );
			if ( '' !== $twin_of ) {
				$twin = pll_get_post( $product_id, $twin_of );
				if ( $twin > 0 && (int) $twin !== $product_id ) {
					update_post_meta( (int) $twin, '_linker_faqs', wp_slash( $json ) );
				}
			}
		}
		$read      = (string) get_post_meta( $product_id, '_linker_faqs', true );
		$written[] = array(
			'id'    => $product_id,
			'slug'  => $product->get_slug(),
			'count' => count( $items ),
			'done'  => $read === $json,
		);
	}
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for tools/faq/import.py on the command line, not HTML.
	echo $marker . wp_json_encode( array( 'written' => $written ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "\n";
} )( '15-faq-payload' );
