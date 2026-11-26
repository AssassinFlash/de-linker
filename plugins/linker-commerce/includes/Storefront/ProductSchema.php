<?php
/**
 * The product page's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\SelectionFacts;

/** Public product identity and search metadata use the same WooCommerce facts. */
final class ProductSchema {

	/**
	 * Adds the block to the head of a product page.
	 */
	public function register(): void {
		add_action( 'wp_head', array( $this, 'print_block' ) );
		add_filter( 'seopress_titles_title', array( $this, 'title' ), 45 );
		add_filter( 'seopress_titles_desc', array( $this, 'description' ), 45 );
	}

	/**
	 * Prints the block, or nothing when this request is not a product page.
	 */
	public function print_block(): void {
		$product = $this->product();
		if ( ! $product instanceof \WC_Product ) {
			return;
		}
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the payload is JSON, and encoded() is where its one dangerous character is handled.
		echo '<script type="application/ld+json">' . $this->encoded( $product ) . "</script>\n";
	}

	/**
	 * The block's JSON for one product.
	 *
	 * Public so the product page's own test can assert the block's content
	 * without an output buffer around a hook.
	 *
	 * @param \WC_Product $product The product the page shows.
	 */
	public function encoded( \WC_Product $product ): string {
		// A `<` inside a product name would otherwise end the script element,
		// and the block would leave the page as text. JSON decodes `\u003C`
		// back to the character, so an escaping pass over the encoded string
		// is the one place that keeps the payload out of HTML's way.
		return str_replace( '<', '\u003C', (string) wp_json_encode( $this->data( $product ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
	}

	/**
	 * The Product node of one product.
	 *
	 * @param \WC_Product $product The product.
	 * @return array<string, mixed>
	 */
	public function data( \WC_Product $product ): array {
		$id    = $product->get_id();
		$url   = (string) get_permalink( $id );
		$brand = $this->term_name( $id, 'pa_brand' );
		$model = $this->term_name( $id, 'pa_model' );

		$data = array(
			'@context'    => 'https://schema.org',
			'@type'       => 'Product',
			'name'        => $this->text( $product->get_name() ),
			'url'         => $url,
			'description' => $this->summary( $product, $brand, $model ),
		);

		$sku = $this->text( $product->get_sku() );
		if ( '' !== $sku ) {
			$data['sku'] = $sku;
		}
		if ( '' !== $brand ) {
			$data['brand']        = array(
				'@type' => 'Brand',
				'name'  => $brand,
			);
			$data['manufacturer'] = array(
				'@type' => 'Organization',
				'name'  => $brand,
			);
		}
		if ( '' !== $model ) {
			$data['model'] = $model;
		}
		$category = $this->term_name( $id, 'product_cat' );
		if ( '' !== $category ) {
			$data['category'] = $category;
		}
		$image = $this->image( $product );
		if ( '' !== $image ) {
			$data['image'] = $image;
		}

		return $data;
	}

	/**
	 * SEOPress also uses the SEO description for its social cards.
	 *
	 * @param string $existing Existing description after native template expansion.
	 */
	public function description( string $existing ): string {
		$product = $this->product();
		if ( ! $product || '' !== trim( (string) get_post_meta( $product->get_id(), '_seopress_titles_desc', true ) ) ) {
			return $existing;
		}
		return $this->summary( $product, $this->term_name( $product->get_id(), 'pa_brand' ), $this->term_name( $product->get_id(), 'pa_model' ) );
	}

	/**
	 * Give published model-only names a useful localized search title.
	 *
	 * @param string $existing Title after SEOPress expands its template.
	 */
	public function title( string $existing ): string {
		$product = $this->product();
		if ( ! $product || '' !== trim( (string) get_post_meta( $product->get_id(), '_seopress_titles_title', true ) ) ) {
			return $existing;
		}
		$name    = $this->text( $product->get_name() );
		$details = $this->model_details( $product, $name, $this->term_name( $product->get_id(), 'pa_brand' ), $this->term_name( $product->get_id(), 'pa_model' ) );
		while ( $details ) {
			$title = $name . ' – ' . implode( ', ', $details ) . ' | Linker';
			if ( mb_strlen( $title ) <= 65 ) {
				return $title;
			}
			array_pop( $details );
		}
		return $existing;
	}

	/**
	 * Ratings and translated category of a model whose name has no description.
	 *
	 * @param \WC_Product $product Localized product.
	 * @param string      $name Published product name.
	 * @param string      $brand Brand term.
	 * @param string      $model Model term.
	 * @return list<string>
	 */
	private function model_details( \WC_Product $product, string $name, string $brand, string $model ): array {
		if ( '' === $model || ( $name !== trim( $brand . ' ' . $model ) && $name !== $model ) ) {
			return array();
		}
		$facts    = SelectionFacts::for_product( $product->get_id() );
		$category = $this->term_name( $product->get_id(), 'product_cat' );
		$details  = '' !== $category ? array( $category ) : array();
		if ( is_float( $facts->ac_power_kw ) ) {
			$details[] = wc_format_localized_decimal( (string) $facts->ac_power_kw ) . ' kW';
		} elseif ( is_float( $facts->nominal_kwh ) ) {
			$details[] = wc_format_localized_decimal( (string) $facts->nominal_kwh ) . ' kWh';
		}
		if ( is_int( $facts->phase ) ) {
			$details[] = 1 === $facts->phase ? __( 'single-phase', 'linker-commerce' ) : __( 'three-phase', 'linker-commerce' );
		}
		return $details;
	}

	/**
	 * Add the category and published rating when the Woo title is only a model.
	 *
	 * @param \WC_Product $product Localized product.
	 * @param string      $brand   Manufacturer name.
	 * @param string      $model   Model designation.
	 */
	private function summary( \WC_Product $product, string $brand, string $model ): string {
		$name    = $this->text( $product->get_name() );
		$details = $this->model_details( $product, $name, $brand, $model );
		if ( $details ) {
			$name .= ' – ' . implode( ', ', $details );
		}
		$endings = array(
			__( 'Use the manufacturer’s documents to check the technical details, then request a quotation from Linker for your installation.', 'linker-commerce' ),
			__( 'Check the technical details in the manufacturer’s documents and request a quotation from Linker for your project.', 'linker-commerce' ),
			__( 'Check the manufacturer’s documents and ask Linker for a quotation for your installation.', 'linker-commerce' ),
			__( 'See the manufacturer’s documents and request a project quotation from Linker.', 'linker-commerce' ),
			__( 'Check the manufacturer’s documents and request a quotation.', 'linker-commerce' ),
		);
		foreach ( $endings as $ending ) {
			$description = $name . '. ' . $ending;
			if ( mb_strlen( $description ) <= 155 ) {
				return $description;
			}
		}
		return $name . '. ' . end( $endings );
	}

	/**
	 * The product this request shows, or null when it does not show one.
	 */
	private function product(): ?\WC_Product {
		if ( ! function_exists( 'is_singular' ) || ! is_singular( 'product' ) ) {
			return null;
		}
		if ( ! function_exists( 'wc_get_product' ) || ! function_exists( 'get_the_ID' ) ) {
			return null;
		}
		$product = wc_get_product( (int) get_the_ID() );
		return $product instanceof \WC_Product ? $product : null;
	}

	/**
	 * One term's name of the product, '' when it has none.
	 *
	 * @param int    $product_id The product.
	 * @param string $taxonomy   The taxonomy.
	 */
	private function term_name( int $product_id, string $taxonomy ): string {
		if ( ! function_exists( 'get_the_terms' ) ) {
			return '';
		}
		$terms = get_the_terms( $product_id, $taxonomy );
		if ( ! \is_array( $terms ) || array() === $terms ) {
			return '';
		}
		$first = reset( $terms );
		return $this->text( (string) $first->name );
	}

	/**
	 * The featured image at full size, '' when the product has none.
	 *
	 * @param \WC_Product $product The product.
	 */
	private function image( \WC_Product $product ): string {
		$id = (int) $product->get_image_id();
		if ( 0 === $id || ! function_exists( 'wp_get_attachment_image_url' ) ) {
			return '';
		}
		return (string) wp_get_attachment_image_url( $id, 'full' );
	}

	/**
	 * A value as it goes into JSON: HTML entities decoded, tags gone.
	 *
	 * The name the page prints is the decoded one ('C&I', not 'C&amp;I'); the
	 * encoder escapes for itself, so decoding first is what makes the block
	 * agree with the heading above it.
	 *
	 * @param string $value The raw value.
	 */
	private function text( string $value ): string {
		return trim( html_entity_decode( wp_strip_all_tags( $value ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
	}
}
