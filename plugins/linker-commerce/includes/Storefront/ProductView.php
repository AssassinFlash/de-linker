<?php
/**
 * The single product's fields for the storefront template.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Gating\CommerceState;

use Linker\Commerce\Catalog\SelectionFactSet;
use Linker\Commerce\Catalog\SelectionFacts;

/**
 * What the product page shows, in the order the template prints it
 * (docs/specs/12-site-chrome.md item 6): the gallery and the words come
 * from the WooCommerce product's own fields — a maintainer's edit in the
 * standard editor is what the page shows the moment it is saved — the key
 * numbers come from the selection facts (#7), the technical table from
 * `linker_specs` once #8 writes it (the legacy ACF JSON until then), the
 * documents from the product's download entries and the questions from the
 * FAQ entries (#15's fields take them over).
 */
final class ProductView {

	/**
	 * Sets up the view.
	 *
	 * @param CommerceState $state #11's price rule: whether this visitor sees
	 *                             this product's price (the single authority;
	 *                             this view never derives it).
	 */
	public function __construct( private readonly CommerceState $state = new CommerceState() ) {}

	/**
	 * The fields of a product, keyed as the template prints them.
	 *
	 * @param int $product_id The English or German product ID.
	 * @return array<string, mixed>
	 */
	public function fields( int $product_id ): array {
		$product = wc_get_product( $product_id );
		if ( ! $product instanceof \WC_Product ) {
			return array();
		}
		$facts = SelectionFacts::for_product( $product_id );
		$brand = $this->term_name( $product_id, 'pa_brand' );
		$model = $this->term_name( $product_id, 'pa_model' );

		return array(
			'id'           => $product_id,
			'title'        => $product->get_name(),
			'model'        => '' !== $model ? $model : $product->get_name(),
			'designation'  => $this->designation( $product->get_name(), $brand, $model ),
			'brand'        => $brand,
			'brand_slug'   => $this->term_slug( $product_id, 'pa_brand' ),
			'brand_logo'   => $this->brand_logo( $product_id ),
			'sku'          => $product->get_sku(),
			'gallery'      => $this->gallery( $product ),
			'stats'        => $this->key_numbers( $facts ),
			'price'        => $this->price( $product ),
			'availability' => $product->is_in_stock() ? __( 'In stock', 'linker-commerce' ) : __( 'Currently unavailable', 'linker-commerce' ),
			'cta_label'    => $this->state->visitor_sees_prices()
				? __( 'Add to solution draft', 'linker-commerce' )
				: __( 'Sign in for partner pricing', 'linker-commerce' ),
			'cta_url'      => $this->cta_url( $product ),
			'ask_url'      => $this->ask_url( $product ),
			'intro'        => '' !== $product->get_short_description() ? $product->get_short_description() : $this->legacy_field( $product_id, 'product_short_intro' ),
			'body'         => $product->get_description(),
			'series'       => $this->legacy_field( $product_id, 'product_series' ),
			'spec_groups'  => $this->spec_groups( $product_id ),
			'attributes'   => $this->attributes( $product ),
			'figures'      => $this->figures( $product_id ),
			'features'     => $this->features( $product_id ),
			'downloads'    => $this->downloads( $product_id ),
			'faqs'         => $this->faqs( $product_id ),
			'pairings'     => $this->pairings( $product_id ),
			'crumbs'       => $this->crumbs( $product_id ),
		);
	}

	/**
	 * One term's name of the product, '' when the product has none.
	 *
	 * @param int    $product_id The product.
	 * @param string $taxonomy   The attribute taxonomy.
	 */
	private function term_name( int $product_id, string $taxonomy ): string {
		$terms = get_the_terms( $product_id, $taxonomy );
		return ( \is_array( $terms ) && ! empty( $terms ) ) ? (string) reset( $terms )->name : '';
	}

	/**
	 * One term's slug of the product, '' when the product has none.
	 *
	 * @param int    $product_id The product.
	 * @param string $taxonomy   The attribute taxonomy.
	 */
	private function term_slug( int $product_id, string $taxonomy ): string {
		$terms = get_the_terms( $product_id, $taxonomy );
		return ( \is_array( $terms ) && ! empty( $terms ) ) ? (string) reset( $terms )->slug : '';
	}

	/**
	 * The line under the model: what the product name says besides the brand
	 * and the model ("ESA (10 kW single-phase power module)").
	 *
	 * @param string $title The product name.
	 * @param string $brand The brand name.
	 * @param string $model The model name.
	 */
	private function designation( string $title, string $brand, string $model ): string {
		$rest = $title;
		foreach ( array( $brand, $model ) as $token ) {
			if ( '' !== $token ) {
				$rest = trim( (string) preg_replace( '/\b' . preg_quote( $token, '/' ) . '\b/u', ' ', $rest ) );
			}
		}
		return trim( $rest, " \t-" );
	}

	/**
	 * The brand's light logo from the media library (our-brand-<slug>-mono-
	 * light), as the product page shows it; null when the library holds none.
	 *
	 * @param int $product_id The product.
	 * @return array{src: string, srcset: string, alt: string}|null
	 */
	private function brand_logo( int $product_id ): ?array {
		static $logos = array();
		$brand        = $this->term_slug( $product_id, 'pa_brand' );
		if ( '' === $brand ) {
			return null;
		}
		if ( ! \array_key_exists( $brand, $logos ) ) {
			$attachment      = get_posts(
				array(
					'post_type'      => 'attachment',
					'posts_per_page' => 1,
					'fields'         => 'ids',
					'no_found_rows'  => true,
					'post_status'    => 'inherit',
					'meta_key'       => '_wp_attached_file', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key
					's'              => 'our-brand-' . $brand . '-mono-light',
				)
			);
			$id              = array() !== $attachment ? (int) reset( $attachment ) : 0;
			$source          = $id ? wp_get_attachment_image_src( $id, 'full' ) : false;
			$logos[ $brand ] = \is_array( $source )
				? array(
					'src'    => (string) $source[0],
					'srcset' => (string) wp_get_attachment_image_srcset( $id, 'full' ),
					'alt'    => $this->term_name( $product_id, 'pa_brand' ),
				)
				: null;
		}
		return $logos[ $brand ];
	}

	/**
	 * The product's images: the featured one first, then the gallery's, as
	 * the product data holds them (the standard editor's order).
	 *
	 * @param \WC_Product $product The product.
	 * @return int[] Attachment IDs.
	 */
	private function gallery( \WC_Product $product ): array {
		$ids      = array();
		$featured = (int) $product->get_image_id();
		if ( 0 !== $featured ) {
			$ids[] = $featured;
		}
		foreach ( $product->get_gallery_image_ids() as $id ) {
			$ids[] = (int) $id;
		}
		return array_values( array_unique( $ids ) );
	}

	/**
	 * The numbers the purchase panel shows, from the selection facts (#7's
	 * contract is the one reader of what a product is).
	 *
	 * @param SelectionFactSet $facts The product's facts.
	 * @return list<array{label: string, value: string}> The stats, unknown ones left out.
	 */
	private function key_numbers( SelectionFactSet $facts ): array {
		$stats   = array(
			array(
				'label' => __( 'Application', 'linker-commerce' ),
				'value' => 'home' === $facts->application ? __( 'Home', 'linker-commerce' ) : ( 'commercial' === $facts->application ? __( 'Commercial', 'linker-commerce' ) : $facts->application ),
			),
			array(
				'label' => __( 'Grid phases', 'linker-commerce' ),
				'value' => \is_int( $facts->phase ) ? (string) $facts->phase : $facts->phase,
			),
			array(
				'label' => __( 'AC power', 'linker-commerce' ),
				'value' => \is_float( $facts->ac_power_kw ) ? self::number( $facts->ac_power_kw, 'kW' ) : $facts->ac_power_kw,
			),
		);
		$energy  = \is_float( $facts->nominal_kwh ) ? $facts->nominal_kwh : $facts->usable_kwh;
		$stats[] = array(
			'label' => __( 'Energy capacity', 'linker-commerce' ),
			'value' => \is_float( $energy ) ? self::number( $energy, 'kWh' ) : (string) $energy,
		);
		return array_values(
			array_filter(
				$stats,
				static fn( array $stat ): bool => SelectionFactSet::UNKNOWN !== $stat['value']
			)
		);
	}

	/**
	 * The price per #11's rule: CommerceState decides whether this visitor
	 * sees this product's price (a partner or RFQ exception); the view only
	 * renders the verdict (#11's Gating module owns the rule).
	 *
	 * @param \WC_Product $product The product.
	 * @return array{html: string, url: string} The price HTML and the sign-in URL for a visitor.
	 */
	private function price( \WC_Product $product ): array {
		if ( $this->state->shows_price( $product ) ) {
			return array(
				'html' => $product->get_price_html(),
				'url'  => '',
			);
		}
		return array(
			'html' => __( 'Net price after partner sign-in', 'linker-commerce' ),
			'url'  => $this->login_url( (string) $product->get_permalink() ),
		);
	}

	/**
	 * Where the primary button leads: a partner adds the product to the
	 * solution draft (Woo's cart until #11 renames and reshapes it), a
	 * visitor signs in first.
	 *
	 * @param \WC_Product $product The product.
	 * @return string The URL.
	 */
	private function cta_url( \WC_Product $product ): string {
		if ( $this->state->visitor_sees_prices() ) {
			return esc_url_raw( add_query_arg( 'add-to-cart', (string) $product->get_id(), wc_get_checkout_url() ) );
		}
		return $this->login_url( (string) $product->get_permalink() );
	}

	/**
	 * The sign-in URL that returns to a page.
	 *
	 * @param string $back Where to return.
	 */
	private function login_url( string $back ): string {
		return esc_url_raw(
			add_query_arg( 'redirect_to', rawurlencode( $back ), wc_get_page_permalink( 'myaccount' ) )
		);
	}

	/**
	 * The "Ask about this product" contact URL, as the live page links it.
	 *
	 * @param \WC_Product $product The product.
	 */
	private function ask_url( \WC_Product $product ): string {
		return esc_url_raw(
			add_query_arg(
				array(
					'intent' => 'product',
					'kind'   => 'product',
					'title'  => rawurlencode( $product->get_name() ),
				),
				home_url( '/contact/' )
			)
		);
	}

	/**
	 * The technical table's groups: `linker_specs` once #8 writes it, the
	 * legacy ACF JSON's spec_groups until then — the table keeps its look
	 * across the handover, and only its source changes.
	 *
	 * @param int $product_id The product.
	 * @return list<array{title: string, rows: list<array{label: string, value: string, unit: string, note: string, highlight: bool}>}>
	 */
	public function spec_groups( int $product_id ): array {
		$specs  = get_post_meta( $product_id, 'linker_specs', true );
		$groups = \is_string( $specs ) && '' !== $specs
			? json_decode( $specs, true )
			: $this->legacy( $product_id, 'spec_groups' );
		if ( ! \is_array( $groups ) ) {
			return array();
		}
		$parsed = array();
		foreach ( $groups as $group ) {
			if ( ! \is_array( $group ) || ! isset( $group['spec_rows'] ) ) {
				continue;
			}
			$rows = array();
			foreach ( $group['spec_rows'] as $row ) {
				if ( ! \is_array( $row ) || ! isset( $row['spec_label'] ) ) {
					continue;
				}
				$rows[] = array(
					'label'     => (string) $row['spec_label'],
					'value'     => (string) ( $row['spec_value'] ?? '' ),
					'unit'      => (string) ( $row['spec_unit'] ?? '' ),
					'note'      => (string) ( $row['spec_note'] ?? '' ),
					'highlight' => ! empty( $row['spec_is_highlight'] ),
				);
			}
			$parsed[] = array(
				'title' => (string) ( $group['spec_group_title'] ?? '' ),
				'rows'  => $rows,
			);
		}
		return $parsed;
	}

	/**
	 * The product's attributes for the technical data table.
	 *
	 * @param \WC_Product $product The product.
	 * @return list<array{label: string, value: string}> Visible attributes with a value.
	 */
	private function attributes( \WC_Product $product ): array {
		$rows = array();
		foreach ( $product->get_attributes() as $attribute ) {
			if ( ! $attribute instanceof \WC_Product_Attribute || ! $attribute->get_visible() ) {
				continue;
			}
			$formatted = (string) $product->get_attribute( $attribute->get_name() );
			if ( '' === $formatted ) {
				continue;
			}
			$rows[] = array(
				'label' => wc_attribute_label( $attribute->get_name(), $product ),
				'value' => $formatted,
			);
		}
		return $rows;
	}

	/**
	 * The figures meta as table rows, the citation attached to the value.
	 *
	 * @param int $product_id The product.
	 * @return list<array{label: string, value: string}> One row per figure.
	 */
	public function figures( int $product_id ): array {
		$raw     = (string) get_post_meta( $product_id, '_tv_b2b_figures', true );
		$decoded = json_decode( $raw, true );
		if ( ! \is_array( $decoded ) ) {
			return array();
		}
		$rows = array();
		foreach ( $decoded as $key => $figure ) {
			if ( ! \is_array( $figure ) || ! isset( $figure['value'] ) ) {
				continue;
			}
			$rows[] = array(
				'label' => (string) $key,
				'value' => trim( (string) $figure['value'] . ' ' . (string) ( $figure['unit'] ?? '' ) ),
			);
		}
		return $rows;
	}

	/**
	 * The feature cards: what #8 will write into `linker_specs`' feature
	 * branch, the legacy ACF JSON's feature_cards until then.
	 *
	 * @param int $product_id The product.
	 * @return list<array{title: string, body: string, priority: bool}> The cards.
	 */
	private function features( int $product_id ): array {
		$cards  = $this->legacy( $product_id, 'feature_cards' );
		$parsed = array();
		foreach ( $cards as $card ) {
			if ( ! \is_array( $card ) || ! isset( $card['feature_title'] ) ) {
				continue;
			}
			$parsed[] = array(
				'title'    => (string) $card['feature_title'],
				'body'     => (string) ( $card['feature_body'] ?? '' ),
				'priority' => ! empty( $card['feature_priority'] ),
			);
		}
		return $parsed;
	}

	/**
	 * One branch of the legacy ACF JSON, as the page shows it until #8's
	 * migration writes it into the product's own fields.
	 *
	 * @param int    $product_id The product.
	 * @param string $branch     The JSON branch: spec_groups, feature_cards, faqs.
	 * @return mixed[] The branch's items.
	 */
	private function legacy( int $product_id, string $branch ): array {
		$decoded = json_decode( (string) get_post_meta( $product_id, '_tv_legacy_acf_json', true ), true );
		if ( ! \is_array( $decoded ) || ! isset( $decoded[ $branch ] ) || ! \is_array( $decoded[ $branch ] ) ) {
			return array();
		}
		/** The branch's items.
		 *
		 * @var mixed[] $items
		 */
		$items = $decoded[ $branch ];
		return $items;
	}

	/**
	 * One plain field of the legacy ACF JSON.
	 *
	 * @param int    $product_id The product.
	 * @param string $field      The field name.
	 */
	private function legacy_field( int $product_id, string $field ): string {
		$decoded = json_decode( (string) get_post_meta( $product_id, '_tv_legacy_acf_json', true ), true );
		return \is_array( $decoded ) && isset( $decoded[ $field ] ) && \is_string( $decoded[ $field ] ) ? $decoded[ $field ] : '';
	}

	/**
	 * The downloads list: the legacy download entries as our media library
	 * links (every file is ours and under our URL, ADR-0023), the #8/#15
	 * document fields take them over.
	 *
	 * @param int $product_id The product.
	 * @return list<array{title: string, url: string|null, type: string, language: string}> The documents.
	 */
	public function downloads( int $product_id ): array {
		$documents = array();
		foreach ( $this->legacy( $product_id, 'downloads' ) as $download ) {
			if ( ! \is_array( $download ) ) {
				continue;
			}
			$attachment = (int) ( $download['download_file'] ?? 0 );
			$url        = $attachment ? wp_get_attachment_url( $attachment ) : null;
			if ( ! \is_string( $url ) ) {
				continue;
			}
			$documents[] = array(
				'title'    => (string) ( $download['download_title'] ?? '' ),
				'url'      => $url,
				'type'     => (string) ( $download['download_type'] ?? '' ),
				'language' => (string) ( $download['download_language'] ?? '' ),
			);
		}
		return $documents;
	}

	/**
	 * The FAQ entries as the page's accordions hold them.
	 *
	 * @param int $product_id The product.
	 * @return list<array{question: string, answer: string}> The questions.
	 */
	public function faqs( int $product_id ): array {
		$parsed = array();
		foreach ( $this->legacy( $product_id, 'faqs' ) as $faq ) {
			if ( ! \is_array( $faq ) || ! isset( $faq['faq_question'] ) ) {
				continue;
			}
			$parsed[] = array(
				'question' => (string) $faq['faq_question'],
				'answer'   => (string) ( $faq['faq_answer'] ?? '' ),
			);
		}
		return $parsed;
	}

	/**
	 * The paired products of the compatibility matrices (#7's documented
	 * pairs; the ACF relationship leaves with the old plugin's data).
	 *
	 * @param int $product_id The product.
	 * @return list<array{title: string, url: string, image: string}> The pairings.
	 */
	private function pairings( int $product_id ): array {
		$related = $this->legacy( $product_id, 'related_products' );
		$pairs   = array();
		foreach ( $related as $id ) {
			$post = get_post( (int) $id );
			if ( ! $post instanceof \WP_Post || 'product' !== $post->post_type || 'publish' !== $post->post_status ) {
				continue;
			}
			$image   = wp_get_attachment_image_url( (int) get_post_meta( $post->ID, '_thumbnail_id', true ), 'medium_large' );
			$pairs[] = array(
				'title' => get_the_title( $post ),
				'url'   => (string) get_permalink( $post ),
				'image' => \is_string( $image ) ? $image : '',
			);
		}
		return $pairs;
	}

	/**
	 * The breadcrumb: the shop, the brand's category, this product.
	 *
	 * @param int $product_id The product.
	 * @return list<array{label: string, url: string|null}> The crumbs.
	 */
	private function crumbs( int $product_id ): array {
		$crumbs = array(
			array(
				'label' => __( 'Products', 'linker-commerce' ),
				'url'   => (string) wc_get_page_permalink( 'shop' ),
			),
		);
		$terms  = get_the_terms( $product_id, 'product_cat' );
		if ( \is_array( $terms ) && ! empty( $terms ) ) {
			$term     = reset( $terms );
			$crumbs[] = array(
				'label' => $term->name,
				'url'   => \is_string( get_term_link( $term ) ) ? (string) get_term_link( $term ) : null,
			);
		}
		$crumbs[] = array(
			'label' => get_the_title( $product_id ),
			'url'   => null,
		);
		return $crumbs;
	}

	/**
	 * A number with its unit for the stats: whole numbers without decimals.
	 *
	 * @param float  $value The number.
	 * @param string $unit  The unit.
	 * @return string The printed value.
	 */
	private static function number( float $value, string $unit ): string {
		$printed = round( $value, 2 );
		$printed = fmod( $printed, 1.0 ) === 0.0 ? (string) (int) $printed : (string) $printed;
		return $printed . ' ' . $unit;
	}
}
