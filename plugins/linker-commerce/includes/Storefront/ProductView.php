<?php
/**
 * The single product's fields for the storefront template.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Gating\PriceDisplay;
use Linker\Commerce\Presentation\PageUrls;

use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\SelectionFactSet;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\Publication;

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
	 * @param CommerceState                                                                                   $state #11's price rule: whether this visitor sees
	 *                                                                                                               this product's price (the single authority;
	 *                                                                                                               this view never derives it).
	 * @param \Closure(int):list<array{title:string,url:string,type:string,role:string,language:string}>|null $document_reader Current-document reader; presentation fixtures may supply an immutable source.
	 */
	public function __construct( private readonly CommerceState $state = new CommerceState(), private readonly ?\Closure $document_reader = null ) {}

	/**
	 * The fields of a product, keyed as the template prints them.
	 *
	 * @param int $product_id The English or German product ID.
	 * @return array<string, mixed>
	 */
	public function fields( int $product_id ): array {
		$fields  = $this->card_fields( $product_id );
		$product = wc_get_product( $product_id );
		if ( array() === $fields || ! $product instanceof \WC_Product ) {
			return array();
		}
		return array_merge(
			$fields,
			array(
				'designation' => Materials::apply_terms( $this->designation( $product->get_name(), $fields['brand'], $this->term_name( $product_id, 'pa_model' ) ) ),
				'brand_logo'  => $this->brand_logo( $product_id ),
				'cta_label'   => $this->cta_label(),
				'cta_url'     => $this->cta_url( $product ),
				'ask_url'     => $this->ask_url( $product ),
				'intro'       => Materials::apply_terms( '' !== $product->get_short_description() ? $product->get_short_description() : $this->legacy_field( $product_id, 'product_short_intro' ) ),
				'body'        => Materials::apply_terms( $product->get_description() ),
				'spec_groups' => $this->spec_groups( $product_id ),
				'attributes'  => $this->attributes( $product ),
				'figures'     => $this->figures( $product_id ),
				'features'    => $this->features( $product_id ),
				'benefits'    => $this->benefits( $product_id ),
				'stats_claim' => $this->stats_claim( $product_id ),
				'scenarios'   => $this->scenarios( $product_id ),
				'downloads'   => $this->downloads( $product_id ),
				'faqs'        => $this->faqs( $product_id ),
				'pairings'    => $this->pairings( $product_id ),
				'crumbs'      => $this->crumbs( $product_id ),
			)
		);
	}

	/**
	 * Catalogue cards and their model pickers do not display technical documents.
	 *
	 * @param int $product_id The English or German product ID.
	 * @return array<string, mixed>
	 */
	public function card_fields( int $product_id ): array {
		$product = wc_get_product( $product_id );
		if ( ! $product instanceof \WC_Product ) {
			return array();
		}
		$facts = SelectionFacts::for_product( $product_id );
		$model = $this->term_name( $product_id, 'pa_model' );

		return array(
			'id'           => $product_id,
			'title'        => Materials::apply_terms( $product->get_name() ),
			'model'        => '' !== $model ? $model : $product->get_name(),
			'brand'        => $this->term_name( $product_id, 'pa_brand' ),
			'brand_slug'   => $this->term_slug( $product_id, 'pa_brand' ),
			'sku'          => $product->get_sku(),
			'gallery'      => $this->gallery( $product ),
			'stats'        => $this->key_numbers( $facts ),
			'price'        => $this->price( $product ),
			'availability' => $product->is_in_stock() ? __( 'In stock', 'linker-commerce' ) : __( 'Currently unavailable', 'linker-commerce' ),
			'series'       => self::series_label( $this->legacy_field( $product_id, 'product_series' ), Materials::is_de() ),
		);
	}

	/**
	 * The product's series label in the page's language (AGENTS.md §2
	 * 2026-10-05: Produkt / Modell / Serie; ticket #264 M4). The stored
	 * `product_series` values are the manufacturers' English labels ("ET
	 * Series", "ESA Series", "EcoFlow OCEAN 2 (Three-Phase)"); the German
	 * page prints the German compound ("ET-Serie", "ESA-Serie") and the
	 * German phase word. Values without an English suffix stay byte for byte,
	 * and an already German label ("ET-Serie") is left alone.
	 *
	 * @param string $series The stored series label.
	 * @param bool   $german Whether the page is German.
	 */
	public static function series_label( string $series, bool $german ): string {
		if ( ! $german || '' === $series ) {
			return $series;
		}
		$series = (string) \preg_replace( '/\b([A-Za-z0-9]+) Series\b/u', '$1-Serie', $series );
		return \str_replace(
			array( '(Three-Phase)', '(Single-Phase)' ),
			array( '(dreiphasig)', '(einphasig)' ),
			$series
		);
	}

	/**
	 * The application scenarios: the legacy ACF JSON's application_scenarios
	 * branch (#16 GAP-2: the live product page has the section, the new
	 * template had no reader for it). Two record shapes exist in the data:
	 * a rich one (situation, fit, verdict, checklist) and a plain one
	 * (body, link). Both come back with the fields they carry.
	 *
	 * @param int $product_id The product.
	 * @return list<array{kind: string, title: string, situation: string, fit: string, verdict: string, checklist: list<string>, image: int, url: string}> The scenarios.
	 */
	public function scenarios( int $product_id ): array {
		$parsed = array();
		foreach ( $this->legacy( $product_id, 'application_scenarios' ) as $scenario ) {
			if ( ! \is_array( $scenario ) || ! isset( $scenario['scenario_title'] ) ) {
				continue;
			}
			$link     = \is_array( $scenario['scenario_link'] ?? null ) ? (string) ( $scenario['scenario_link']['url'] ?? '' ) : '';
			$checks   = \array_values(
				\array_filter(
					\array_map(
						static fn( $row ): string => \is_array( $row ) ? \trim( (string) ( $row['check_text'] ?? '' ) ) : \trim( (string) $row ),
						\is_array( $scenario['scenario_checklist'] ?? null ) ? $scenario['scenario_checklist'] : array()
					)
				)
			);
			$parsed[] = array(
				'kind'      => (string) ( $scenario['scenario_kind'] ?? '' ),
				'title'     => (string) $scenario['scenario_title'],
				'situation' => (string) ( $scenario['scenario_situation'] ?? $scenario['scenario_body'] ?? '' ),
				'fit'       => (string) ( $scenario['scenario_fit'] ?? '' ),
				'verdict'   => (string) ( $scenario['scenario_verdict'] ?? '' ),
				'checklist' => $checks,
				'image'     => (int) ( $scenario['scenario_image'] ?? 0 ),
				'url'       => $link,
			);
		}
		return $parsed;
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
		$rest = trim( $rest, " \t-" );
		// The name's own brackets are dropped: the live page reads "ESA battery
		// module, 5.12 kWh" where the name says "(ESA battery module, 5.12
		// kWh)" (measured 2026-10-12, EN and DE).
		if ( \str_starts_with( $rest, '(' ) && \str_ends_with( $rest, ')' ) ) {
			$rest = trim( \substr( $rest, 1, -1 ) );
		}
		return $rest;
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
		return array(
			'html' => $this->price_html( $product ),
			'url'  => CommerceState::LOGIN === $this->state->reason( $product, CommerceState::PAGE )
				? esc_url_raw( add_query_arg( 'redirect_to', rawurlencode( (string) $product->get_permalink() ), wc_get_page_permalink( 'myaccount' ) ) )
				: '',
		);
	}

	/**
	 * The product page's price line: the price, or the sentence in its place.
	 * The comparison page prints the same line, and Genie's card reads the
	 * same CommerceState::reason() on its PAGE surface (#242).
	 *
	 * @param \WC_Product $product The product.
	 */
	public function price_html( \WC_Product $product ): string {
		$reason = $this->state->reason( $product, CommerceState::PAGE );
		if ( null === $reason || CommerceState::UNPRICED === $reason ) {
			// WooCommerce's own price, or its empty-price text ("Price on
			// request", Gating\PriceDisplay).
			return $product->get_price_html();
		}
		if ( CommerceState::PROJECT === $reason ) {
			// An approved account on a product quoted per project (live 1957):
			// the account is not what hides the price (#242).
			return __( 'Quoted per project', 'linker-commerce' );
		}
		if ( in_array( $reason, array( CommerceState::APPROVAL, CommerceState::UNAVAILABLE ), true ) ) {
			return ( new PriceDisplay( $this->state ) )->reason_text( $reason );
		}
		return __( 'Net price after partner sign-in', 'linker-commerce' );
	}

	/**
	 * Anyone can add a product for an inquiry; approval controls only prices (#246).
	 *
	 * @return string The label.
	 */
	private function cta_label(): string {
		return __( 'Add to solution draft', 'linker-commerce' );
	}

	/**
	 * Woo adds the product to the session draft and opens the public request.
	 *
	 * @param \WC_Product $product The product.
	 * @return string The URL.
	 */
	private function cta_url( \WC_Product $product ): string {
		return esc_url_raw( add_query_arg( 'add-to-cart', (string) $product->get_id(), wc_get_checkout_url() ) );
	}

	/**
	 * The "Ask about this product" contact URL, in the product page's own
	 * language: a German page opens the German contact form, whose receipt
	 * then speaks German (AUDIT.md H1).
	 *
	 * @param \WC_Product $product The product.
	 */
	private function ask_url( \WC_Product $product ): string {
		return esc_url_raw(
			add_query_arg(
				array(
					'intent'     => 'product',
					'kind'       => 'product',
					'title'      => rawurlencode( $product->get_name() ),
					'source_id'  => $product->get_id(),
					'product_id' => $product->get_id(),
					'source'     => $product->get_permalink(),
				),
				PageUrls::page( 'contact' )
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
				'image'    => (int) ( $card['feature_image'] ?? 0 ),
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
		$decoded = Materials::acf( $product_id );
		if ( ! isset( $decoded[ $branch ] ) || ! \is_array( $decoded[ $branch ] ) ) {
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
		$decoded = Materials::acf( $product_id );
		return isset( $decoded[ $field ] ) && \is_string( $decoded[ $field ] ) ? $decoded[ $field ] : '';
	}

	/**
	 * The description panel's benefit bullets: the legacy `value_prop`
	 * branch's `benefit_bullets`, in order (the live page's two cards).
	 *
	 * @param int $product_id The product.
	 * @return list<string> The bullets.
	 */
	public function benefits( int $product_id ): array {
		$prop = $this->legacy( $product_id, 'value_prop' );
		$out  = array();
		foreach ( \is_array( $prop['benefit_bullets'] ?? null ) ? $prop['benefit_bullets'] : array() as $bullet ) {
			$line = \trim( (string) $bullet );
			if ( '' !== $line ) {
				$out[] = $line;
			}
		}
		return $out;
	}

	/**
	 * The technical-data summary of the live page: the legacy `stats_claim`
	 * branch (a kicker label, a headline and a reading body) that sits beside
	 * the specification deck. array() when the product carries none.
	 *
	 * @param int $product_id The product.
	 * @return array{label?: string, title?: string, body?: string, cards?: list<array{label: string, value: string}>}
	 */
	public function stats_claim( int $product_id ): array {
		$claim = $this->legacy( $product_id, 'stats_claim' );
		if ( ! isset( $claim['label'] ) && ! isset( $claim['title'] ) ) {
			return array();
		}
		$cards = array();
		foreach ( \is_array( $claim['cards'] ?? null ) ? $claim['cards'] : array() as $card ) {
			if ( \is_array( $card ) && '' !== trim( (string) ( $card['label'] ?? '' ) ) ) {
				$cards[] = array(
					'label' => (string) $card['label'],
					'value' => trim( (string) ( $card['value'] ?? '' ) ),
				);
			}
		}
		return array(
			'label' => (string) ( $claim['label'] ?? '' ),
			'title' => (string) ( $claim['title'] ?? '' ),
			'body'  => (string) ( $claim['body'] ?? '' ),
			'cards' => $cards,
		);
	}

	/**
	 * Current published Woo document relations for the product template.
	 *
	 * @param int                      $product_id Product ID.
	 * @param array<string,mixed>|null $manifest Optional current assembly snapshot.
	 * @return list<array{title:string,url:string,type:string,role:string,language:string}>
	 */
	public function downloads( int $product_id, ?array $manifest = null ): array {
		if ( null !== $this->document_reader ) {
			return ( $this->document_reader )( $product_id );
		}
		if ( ! Publication::is_published( $product_id ) ) {
			return array();
		}
		// Download links consume current listing metadata, not product revisions
		// or preparation state. The original PDF gate still authorizes its bytes.
		$id         = Publication::canonical_id( $product_id );
		$documents  = array();
		$manifest ??= Publication::library_read();
		foreach ( $manifest['documents'] as $document ) {
			if ( ! in_array( $id, $document['product_ids'], true ) ) {
				continue;
			}
			$documents[] = array(
				'title'    => $document['title'],
				'url'      => $document['url'],
				'type'     => $document['type'],
				'role'     => $document['role'] ?? '',
				'language' => $document['lang'],
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
