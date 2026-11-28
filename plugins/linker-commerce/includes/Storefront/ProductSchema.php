<?php
/**
 * The product page's structured data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;

/** Public product identity and search metadata use the same WooCommerce facts. */
final class ProductSchema {

	/** Use the caller's snapshot or the current request's authority.
	 *
	 * @param array<string,mixed>|null $manifest Published source data.
	 */
	public function __construct( private readonly ?array $manifest = null ) {}

	/**
	 * Adds the block to the head of a product page.
	 */
	public function register(): void {
		add_action( 'wp_head', array( $this, 'print_block' ) );
		add_filter( 'seopress_titles_title', array( $this, 'title' ), 45 );
		add_filter( 'seopress_titles_desc', array( $this, 'description' ), 45 );
		foreach ( array( 'seopress_social_og_title', 'seopress_social_twitter_card_title', 'seopress_social_og_desc', 'seopress_social_twitter_card_desc' ) as $filter ) {
			add_filter( $filter, array( $this, 'social' ), 45 );
		}
	}

	/**
	 * Prints the block, or nothing when this request is not a product page.
	 */
	public function print_block(): void {
		$product = $this->product();
		if ( ! $product instanceof \WC_Product ) {
			return;
		}
		$json = $this->encoded( $product );
		if ( '' === $json ) {
			return;
		}
		do_action( 'litespeed_tag_add', 'PT.product' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- Linked equipment and documents share the native product purge tag.
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- the payload is JSON, and encoded() is where its one dangerous character is handled.
		echo '<script type="application/ld+json">' . $json . "</script>\n";
		$group = ProductGroupIndex::current( $this->manifest )->schema( $product->get_id() );
		if ( $group ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON_HEX_TAG escapes script delimiters.
			echo '<script type="application/ld+json">' . wp_json_encode( $group, JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . "</script>\n";
		}
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
		$node = $this->data( $product );
		return ! $node ? '' : str_replace( '<', '\u003C', (string) wp_json_encode( $node, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
	}

	/**
	 * The Product node of one product.
	 *
	 * @param \WC_Product $product The product.
	 * @return array<string, mixed>
	 */
	public function data( \WC_Product $product ): array {
		$id       = $product->get_id();
		$manifest = $this->manifest ?? CompatibilityIndex::manifest();
		$source   = Publication::canonical_id( $id );
		$records  = array_column( $manifest['products'], null, 'product_id' );
		if ( ! Publication::published_in_manifest( $id, $manifest ) || ! empty( $records[ $source ]['engineering_role'] ) ) {
			return array();
		}
		$url   = (string) get_permalink( $id );
		$brand = $this->term_name( $id, 'pa_brand' );
		$model = $this->term_name( $id, 'pa_model' );

		$figures = Publication::figures_in_manifest( $source, $manifest );
		$facts   = SelectionFacts::from_figures( $source, $figures );
		$data    = array(
			'@context'         => 'https://schema.org',
			'@type'            => 'Product',
			'@id'              => $url . '#product',
			'mainEntityOfPage' => array( '@id' => $url . '#webpage' ),
			'inLanguage'       => Materials::locale(),
			'name'             => $this->text( $product->get_name() ),
			'url'              => $url,
			'description'      => $this->summary( $product ),
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

		$group = ProductGroupIndex::current( $manifest )->identity( $id );
		if ( '' !== $group ) {
			$data['inProductGroupWithID'] = $group;
			$data['isVariantOf']          = array( '@id' => $group );
		}
		$material = Materials::material_for_product( $source );
		$mpn      = $this->text( (string) ( $material['identity']['manufacturer_part_number'] ?? '' ) );
		if ( '' !== $mpn ) {
			$data['mpn'] = $mpn;
		}
		$downloads = ( new ProductView() )->downloads( $id, $manifest );
		foreach ( $downloads as $doc ) {
			$title = Materials::localized_document_title( $doc['title'], null, $doc['url'] );
			$node  = array(
				'@type'          => 'DigitalDocument',
				'name'           => $this->text( $title ),
				'url'            => $doc['url'],
				'encodingFormat' => 'application/pdf',
			);
			$lang  = strtolower( $doc['language'] );
			if ( in_array( $lang, array( 'en', 'de' ), true ) ) {
				$node['inLanguage'] = $lang;
			} elseif ( in_array( $lang, array( 'mul', 'de/en', 'en/de' ), true ) ) {
				$node['inLanguage'] = array( 'en', 'de' );
			}
			$data['subjectOf'][] = $node;
		}
		$properties = $this->properties( $source, $facts, $figures, $downloads );
		if ( $properties ) {
			$data['additionalProperty'] = $properties;
		}
		$links   = CompatibilityIndex::for_product( $id, $manifest );
		$related = array();
		foreach ( $links['compatible'] as $item ) {
			$related[] = $item;
			array_push( $related, ...$item['accessories'] );
		}
		foreach ( array(
			'isRelatedTo'               => $related,
			'isAccessoryOrSparePartFor' => $links['accessory_for'],
		) as $property => $items ) {
			$nodes = array();
			foreach ( $items as $item ) {
				$nodes[ $item['url'] ] = array(
					'@id'  => $item['url'] . '#product',
					'name' => $this->text( $item['name'] ),
					'url'  => $item['url'],
				);
			}
			if ( $nodes ) {
				$data[ $property ] = array_values( $nodes );
			}
		}
		return $data;
	}

	/** Localized public facts with numeric values kept numeric for consumers.
	 *
	 * @param int                               $id Canonical product ID.
	 * @param SelectionFactSet                  $f Verified public facts.
	 * @param array<string,array<string,mixed>> $figures Authorized technical figures.
	 * @param array<int,array<string,mixed>>    $downloads Published document links.
	 * @return list<array<string,mixed>> Schema.org PropertyValue nodes.
	 */
	private function properties( int $id, SelectionFactSet $f, array $figures, array $downloads ): array {
		$mppt   = $figures['n_mppt']['value'] ?? null;
		$mppt   = is_string( $mppt ) && ctype_digit( $mppt ) ? (int) $mppt : $mppt;
		$values = array(
			array( __( 'Rated AC output power', 'linker-commerce' ), $f->ac_power_kw, 'kW', 'KWT' ),
			array( __( 'Maximum PV input power', 'linker-commerce' ), $f->pv_input_kw, 'kW', 'KWT' ),
			array( __( 'Usable battery energy', 'linker-commerce' ), $f->usable_kwh, 'kWh', 'KWH' ),
			array( __( 'Nominal battery energy', 'linker-commerce' ), $f->nominal_kwh, 'kWh', 'KWH' ),
			array( __( 'MPPT trackers', 'linker-commerce' ), $mppt, '', '' ),
			array( __( 'Ingress protection', 'linker-commerce' ), $figures['ip_rating']['value'] ?? null, '', '' ),
			array( __( 'Battery voltage range', 'linker-commerce' ), Materials::de_number( (string) ( $figures['battery_voltage_range_v']['value'] ?? '' ) ), 'V', 'VLT' ),
			array( __( 'Grid compliance standards', 'linker-commerce' ), implode( ', ', CompatibilityIndex::grid_standards( $id, $downloads, $figures ) ), '', '' ),
		);
		if ( is_int( $f->phase ) ) {
			$values[] = array( __( 'Grid phases', 'linker-commerce' ), 1 === $f->phase ? __( 'Single-phase', 'linker-commerce' ) : __( 'Three-phase', 'linker-commerce' ), '', '' );
		}
		if ( null !== $f->kwh_range ) {
			$values[] = array( __( 'System energy range', 'linker-commerce' ), Materials::de_number( $f->kwh_range['min'] . '–' . $f->kwh_range['max'] ), 'kWh', 'KWH' );
		}
		if ( 'unknown' !== $f->application ) {
			$values[] = array( __( 'Application', 'linker-commerce' ), 'home' === $f->application ? __( 'Residential', 'linker-commerce' ) : __( 'Commercial & Industrial', 'linker-commerce' ), '', '' );
		}
		$result = array();
		foreach ( $values as list( $name, $value, $unit, $code ) ) {
			if ( ! is_scalar( $value ) || '' === $value || 'unknown' === $value ) {
				continue;
			}
			$node = array(
				'@type' => 'PropertyValue',
				'name'  => $name,
				'value' => $value,
			);
			if ( '' !== $unit ) {
				$node += array(
					'unitText' => $unit,
					'unitCode' => $code,
				);
			}
			$result[] = $node;
		}
		return $result;
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
		return $this->summary( $product );
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
		$id    = $product->get_id();
		$model = $this->term_name( $id, 'pa_model' );
		$brand = $this->term_name( $id, 'pa_brand' );
		$full  = str_starts_with( strtolower( $model ), strtolower( $brand ) ) ? $model : trim( $brand . ' ' . $model );
		if ( '' === $model || ( mb_strlen( trim( $existing ) ) <= 65 && ! in_array( $this->text( $product->get_name() ), array( $model, $full ), true ) ) ) {
			return $existing;
		}
		$rating = ProductGroupIndex::current( $this->manifest )->rating( $id );
		if ( ! $rating ) {
			return $existing;
		}
		list( $long, $short ) = ModelProfile::roles( $rating );
		foreach ( array( $full . ' – ' . $long, $full . ' – ' . $short, $model . ' – ' . $short ) as $candidate ) {
			$title = $candidate . ' | Linker';
			if ( mb_strlen( $title ) <= 65 ) {
				return $title;
			}
		}
		return $existing;
	}

	/**
	 * SEOPress filters both the source field and the completed HTML tag.
	 *
	 * @param string $existing Field or HTML tag.
	 */
	public function social( string $existing ): string {
		if ( ! str_starts_with( ltrim( $existing ), '<meta' ) ) {
			return $existing;
		}
		$product = $this->product();
		if ( ! $product ) {
			return $existing;
		}
		$filter = (string) current_filter();
		$field  = str_ends_with( $filter, 'title' ) ? 'title' : 'desc';
		$key    = '_seopress_social_' . ( str_contains( $filter, 'twitter' ) ? 'twitter_' : 'fb_' ) . $field;
		if ( '' !== trim( (string) get_post_meta( $product->get_id(), $key, true ) ) ) {
			return $existing;
		}
		if ( 'title' === $field && function_exists( 'seopress_titles_the_title' ) ) {
			$value = seopress_titles_the_title();
		} elseif ( 'desc' === $field && function_exists( 'seopress_titles_the_description_content' ) ) {
			$value = seopress_titles_the_description_content();
		} else {
			return $existing;
		}
		$tag = new \WP_HTML_Tag_Processor( $existing );
		$tag->next_tag( array( 'tag_name' => 'META' ) );
		$tag->set_attribute( 'content', html_entity_decode( $value, ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		return $tag->get_updated_html();
	}

	/**
	 * Build the model summary for the document head and social previews.
	 *
	 * @param \WC_Product $product Displayed product.
	 */
	private function summary( \WC_Product $product ): string {
		$id       = $product->get_id();
		$manifest = $this->manifest ?? CompatibilityIndex::manifest();
		$index    = ProductGroupIndex::current( $manifest );
		$rating   = $index->rating( $id );
		if ( ! $rating ) {
			return $this->text( $product->get_short_description() );
		}
		$position = (int) array_search( $id, $index->members_for( $id ), true );
		return ModelProfile::summary( $product, $rating, $position, $manifest );
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
