<?php
/**
 * The site's document register and its product answers, for the library page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Abilities\ProductText;
use Linker\Commerce\Gating\CommerceState;
use Linker\Commerce\Storefront\ProductView;

/**
 * What /faq-download/ lists (docs/specs/19-tool-pages.md): every document the
 * published products state, once per file, and their product answers. Both
 * come from the readings the product page already uses — the product's
 * document list (ProductView::downloads(), the `_linker_documents` field of
 * #8 once the migration writes it, the legacy entry until then) and the cited
 * FAQ field through Publication::faqs_for() — so
 * the library cannot disagree with the product pages it indexes.
 */
final class DocumentLibrary {

	/**
	 * Document types as the live register names them, in display order. The
	 * stored value is the product data's own word.
	 */
	public const TYPE_ORDER = array( 'datasheet', 'manual', 'certificate', 'compatibility', 'warranty', 'brochure', 'document' );

	/**
	 * The product view whose document and FAQ readings the library indexes.
	 *
	 * @var ProductView
	 */
	private readonly ProductView $view;

	/**
	 * Sets up the library.
	 *
	 * @param ProductView|null                    $view Document/FAQ reading; the default one otherwise.
	 * @param callable():array<string,mixed>|null $publication Current authority fixture; production reads Woo.
	 */
	public function __construct( ?ProductView $view = null, private mixed $publication = null ) {
		$this->view = $view ?? new ProductView( new CommerceState() );
	}

	/**
	 * Current permission is shared with every customer tool.
	 *
	 * @return array<string,mixed>
	 */
	private function current(): array {
		return is_callable( $this->publication ) ? ( $this->publication )() : Publication::library_read();
	}

	/**
	 * The product whose data the library reads for one of the page's
	 * products: the language layer answers the source-language twin through
	 * `linker_commerce_facts_product_id` (the same swap #7's facts read),
	 * because the document and FAQ fields live on the English product while a
	 * German product is its translated twin. Without a language layer the
	 * product answers itself.
	 *
	 * @param int $id Product ID as the page's language lists it.
	 */
	private static function source( int $id ): int {
		if ( function_exists( 'has_filter' ) && has_filter( 'linker_commerce_facts_product_id' ) ) {
			/**
			 * Filters the product the library's readings answer for: the
			 * language layer swaps in the source-language twin. Without a
			 * listener (no language layer, unit tests) the page's own product
			 * answers itself.
			 *
			 * @since 0.2.0
			 *
			 * @param int $id The product ID the page's language lists.
			 */
			return (int) apply_filters( 'linker_commerce_facts_product_id', $id );
		}

		return $id;
	}

	/**
	 * Every published product ID of the page's language, by title (A–Z) —
	 * the brands of the register read in that order.
	 *
	 * @param array<string,mixed> $manifest Current authority for this assembly.
	 * @return list<int>
	 */
	private function products( array $manifest ): array {
		$allowed = array();
		foreach ( $manifest['products'] as $product ) {
			foreach ( $product['published_locale_ids'] as $id ) {
				$allowed[ $id ] = true;
			}
		}
		return array_values(
			array_filter(
				array_map(
					'intval',
					get_posts(
						array(
							'post_type'      => 'product',
							'post_status'    => 'publish',
							'posts_per_page' => -1,
							'fields'         => 'ids',
							'orderby'        => 'title',
							'order'          => 'ASC',
							'cache_results'  => false,
						)
					)
				),
				static fn ( int $id ): bool => isset( $allowed[ $id ] )
			)
		);
	}

	/**
	 * The register: one row per file, in brand and title order, each carrying
	 * the products that state it.
	 *
	 * @return list<array{title: string, url: string, type: string, language: string, brand: string, covers: list<string>}>
	 */
	public function documents(): array {
		$manifest = $this->current();
		return $this->documents_in( $manifest, $this->products( $manifest ) );
	}

	/**
	 * Both panels share one fresh authority assembly and product list.
	 *
	 * Nothing is retained on this object: another call reads Woo and document
	 * cited bytes again. Independent answers()/documents() callers stay fresh too.
	 *
	 * @param 'en'|'de' $lang Language of the answer rows.
	 * @return array{answers: list<array{question: string, answer: string, product: string, brand: string, url: string, source: string, source_url: string}>, documents: list<array{title: string, url: string, type: string, language: string, brand: string, covers: list<string>}>}
	 */
	public function entries( string $lang = 'en' ): array {
		$manifest = $this->current();
		$products = $this->products( $manifest );

		return array(
			'answers'   => $this->answers_in( $lang, $manifest, $products ),
			'documents' => $this->documents_in( $manifest, $products ),
		);
	}

	/**
	 * Assemble file rows within the caller's current read.
	 *
	 * @param array<string,mixed> $manifest Current authority for this assembly.
	 * @param int[]               $products Native locale product IDs.
	 * @return list<array{title: string, url: string, type: string, language: string, brand: string, covers: list<string>}>
	 */
	private function documents_in( array $manifest, array $products ): array {
		$files = array();
		foreach ( $products as $id ) {
			$title = wp_specialchars_decode( get_the_title( $id ), ENT_QUOTES );
			$brand = self::brand( self::source( $id ) );
			foreach ( $this->view->downloads( self::source( $id ), $manifest ) as $document ) {
				if ( '' === $document['url'] ) {
					continue;
				}
				$key = (string) $document['url'];
				if ( ! isset( $files[ $key ] ) ) {
					$files[ $key ] = array(
						'title'    => Materials::localized_document_title( '' !== trim( $document['title'] ) ? $document['title'] : __( 'Document', 'linker-commerce' ) ),
						'url'      => (string) $document['url'],
						'type'     => self::type( (string) $document['type'], (string) $document['role'] ),
						'language' => self::language( (string) $document['language'] ),
						'brand'    => $brand,
						'covers'   => array(),
					);
				}
				if ( ! in_array( $title, $files[ $key ]['covers'], true ) ) {
					$files[ $key ]['covers'][] = $title;
				}
			}
		}
		$documents = array_values( $files );
		usort(
			$documents,
			static function ( array $a, array $b ): int {
				$order = self::rank( $a['type'] ) <=> self::rank( $b['type'] );

				return 0 !== $order ? $order : strcasecmp( $a['title'], $b['title'] );
			}
		);

		return $documents;
	}

	/**
	 * A type's position in the register's display order.
	 *
	 * @param string $type A type from self::TYPE_ORDER.
	 */
	private static function rank( string $type ): int {
		$at = array_search( $type, self::TYPE_ORDER, true );

		return is_int( $at ) ? $at : count( self::TYPE_ORDER );
	}

	/**
	 * The product answers of every published product, in product order: the
	 * #15 FAQ field where it is filled, the legacy product FAQ until then.
	 *
	 * Each row names its product's brand (the pa_brand term, the first word of
	 * the name without one), so the register can file an answer under the
	 * brand its product states — the same reading documents() files by.
	 *
	 * @param 'en'|'de' $lang Language of question and answer.
	 * @return list<array{question: string, answer: string, product: string, brand: string, url: string, source: string, source_url: string}>
	 */
	public function answers( string $lang = 'en' ): array {
		$manifest = $this->current();
		return $this->answers_in( $lang, $manifest, $this->products( $manifest ) );
	}

	/**
	 * Assemble cited answers within the caller's current read.
	 *
	 * @param 'en'|'de'           $lang Answer language.
	 * @param array<string,mixed> $manifest Current authority for this assembly.
	 * @param int[]               $products Native locale product IDs.
	 * @return list<array{question: string, answer: string, product: string, brand: string, url: string, source: string, source_url: string}>
	 */
	private function answers_in( string $lang, array $manifest, array $products ): array {
		$german  = 'de' === ProductText::lang( $lang );
		$answers = array();
		foreach ( $products as $id ) {
			$product = wp_specialchars_decode( get_the_title( $id ), ENT_QUOTES );
			$url     = (string) get_permalink( $id );
			$brand   = self::brand( self::source( $id ) );
			foreach ( $this->faq_items( self::source( $id ), $german, $manifest ) as $item ) {
				$answers[] = array(
					'question'   => $item['question'],
					'answer'     => $item['answer'],
					'product'    => $product,
					'brand'      => $brand,
					'url'        => $url,
					'source'     => $item['source'],
					'source_url' => $item['source_url'],
				);
			}
		}

		return $answers;
	}

	/**
	 * Current cited FAQ items in the page's language. Unbound editorial records
	 * remain stored but cannot supply a current technical answer.
	 *
	 * @param int                 $id     Product ID.
	 * @param bool                $german German page.
	 * @param array<string,mixed> $manifest Current authority for this assembly.
	 * @return list<array{question: string, answer: string, source: string, source_url: string}>
	 */
	private function faq_items( int $id, bool $german, array $manifest ): array {
		$items = array();
		foreach ( Publication::faqs_for( $id, $manifest ) as $faq ) {
			$question = $german && '' !== $faq['question_de'] ? $faq['question_de'] : $faq['question'];
			$answer   = $german && '' !== $faq['answer_de'] ? $faq['answer_de'] : $faq['answer'];
			if ( '' === trim( $question ) ) {
				continue;
			}
			$page    = (int) $faq['citation']['page'];
			$title   = Materials::localized_document_title( (string) ( $faq['citation']['title'] ?? '' ), $german );
			$items[] = array(
				'question'   => $question,
				'answer'     => $answer,
				'source'     => '' !== $title
					? sprintf(
						/* translators: 1: document title, 2: page number. */
						__( '%1$s, p. %2$d', 'linker-commerce' ),
						$title,
						$page
					)
					: sprintf(
						/* translators: %d: page number. */
						__( 'p. %d', 'linker-commerce' ),
						$page
					),
				'source_url' => $faq['citation']['url'] . '#page=' . $page,
			);
		}
		return $items;
	}

	/**
	 * A document type as the register names it.
	 *
	 * A known maintained type is authoritative. The retained role only fills
	 * a missing, generic or unknown type; German aliases share the same mapping.
	 *
	 * @param string $stored Stored type.
	 * @param string $role   Stored role, '' when the row states none.
	 */
	public static function type( string $stored, string $role = '' ): string {
		$kind = Materials::document_kind( '', $stored );
		if ( 'document' === $kind || ! in_array( $kind, self::TYPE_ORDER, true ) ) {
			$kind = Materials::document_kind( $role, $stored );
		}

		return in_array( $kind, self::TYPE_ORDER, true ) ? $kind : 'document';
	}

	/**
	 * A document language as stored: `DE`, `EN`, `MUL` (multilingual) or the
	 * combined `DE/EN` / `EN/DE`; a product that states none reads `EN`.
	 *
	 * @param string $stored Stored language.
	 */
	public static function language( string $stored ): string {
		$value = strtoupper( trim( $stored ) );
		$value = match ( $value ) {
			'MULTI', 'MULTILINGUAL' => 'MUL',
			''                      => 'EN',
			default                 => $value,
		};

		return $value;
	}

	/**
	 * The brand of a product: the pa_brand term where it has one, otherwise
	 * the first word of its name (the live register's own fallback).
	 *
	 * @param int $id Product ID.
	 */
	private static function brand( int $id ): string {
		$brand = ProductText::term_name( $id, 'pa_brand' );
		if ( null !== $brand ) {
			return $brand;
		}
		$name = wp_specialchars_decode( get_the_title( $id ), ENT_QUOTES );

		return (string) strtok( $name, ' ' );
	}
}
