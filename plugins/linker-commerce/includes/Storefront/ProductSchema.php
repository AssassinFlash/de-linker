<?php
/**
 * The product page's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/**
 * Emits the one Product JSON-LD block a product page carries.
 *
 * WHY HERE AND NOT IN THE RETAINED SEO PLUGIN. The site runs SEOPress (its
 * licence stays), and its schema editor does emit a Product node for products —
 * from a stored template row that says, for every product of every brand,
 * `"brand": "Linker"` and `"category": "Energy storage system"`, and that
 * carries no sku, no model, no image and no availability. Nothing in this
 * repository can test that row, and the product's real facts would not survive
 * the switch: the previous emitter (custom code in a plugin this switch
 * deletes) is where they live today. The product page's facts are this
 * plugin's (docs/specs/12-site-chrome.md item 6: the words come from
 * WooCommerce's own fields, the numbers from #7's contract), so the page's
 * structured data is built next to ProductView, which reads the same fields.
 *
 * WHAT IT MUST NOT SAY. No price, no priceCurrency, no offers.price: the block
 * is emitted into pages that LiteSpeed's cache serves to anonymous visitors,
 * and net prices are visible only to approved partners (#11's gate is the one
 * authority on that). `url` and `availability` are the public facts. The brand
 * is the product's own `pa_brand` term — the manufacturer's name, never this
 * company's.
 */
final class ProductSchema {

	/**
	 * The schema.org term for WooCommerce's stock status.
	 *
	 * WooCommerce's own stock state is the authority; the previous tree's
	 * mirror of it is gone. An unknown status is left out rather than guessed:
	 * an absent availability claim is recoverable, a wrong one is not.
	 *
	 * @var array<string, string>
	 */
	private const AVAILABILITY = array(
		'instock'     => 'https://schema.org/InStock',
		'outofstock'  => 'https://schema.org/OutOfStock',
		'onbackorder' => 'https://schema.org/BackOrder',
	);

	/**
	 * Adds the block to the head of a product page.
	 */
	public function register(): void {
		add_action( 'wp_head', array( $this, 'print_block' ) );
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
			'description' => $this->text( wp_strip_all_tags( $this->intro( $product ) ) ),
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

		$availability   = self::AVAILABILITY[ $product->get_stock_status() ] ?? '';
		$data['offers'] = array_filter(
			array(
				'@type'        => 'Offer',
				'url'          => $url,
				'availability' => $availability,
			),
			static fn( string $value ): bool => '' !== $value
		);

		return $data;
	}

	/**
	 * The product's own introduction: its short description, or its long one
	 * when it has no short one (the same choice the page's own text makes).
	 *
	 * @param \WC_Product $product The product.
	 */
	private function intro( \WC_Product $product ): string {
		$short = (string) $product->get_short_description();
		return '' !== $short ? $short : (string) $product->get_description();
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
