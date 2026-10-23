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
 * #8 once the migration writes it, the legacy entry until then) and the FAQ
 * field of #15 (Products\Faqs, the legacy FAQ until the field is filled) — so
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
		return is_callable( $this->publication ) ? ( $this->publication )() : Publication::manifest();
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
		$files    = array();
		$manifest = $this->current();
		foreach ( $this->products( $manifest ) as $id ) {
			$title = wp_specialchars_decode( get_the_title( $id ), ENT_QUOTES );
			$brand = self::brand( self::source( $id ) );
			foreach ( $this->view->downloads( self::source( $id ), $manifest ) as $document ) {
				if ( '' === $document['url'] ) {
					continue;
				}
				$key = (string) $document['url'];
				if ( ! isset( $files[ $key ] ) ) {
					$files[ $key ] = array(
						'title'    => Materials::document_title_display( '' !== trim( $document['title'] ) ? $document['title'] : __( 'Document', 'linker-commerce' ) ),
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
		$german   = 'de' === ProductText::lang( $lang );
		$answers  = array();
		$manifest = $this->current();
		foreach ( $this->products( $manifest ) as $id ) {
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
	 * The FAQ items of a product in the page's language: `_linker_faqs` (#15),
	 * the legacy product FAQ where that field is still empty.
	 *
	 * @param int                 $id     Product ID.
	 * @param bool                $german German page.
	 * @param array<string,mixed> $manifest Current authority for this assembly.
	 * @return list<array{question: string, answer: string, source: string, source_url: string}>
	 */
	private function faq_items( int $id, bool $german, array $manifest ): array {
		$items        = array();
		$faqs         = Faqs::of( $id );
		$allowed_urls = array();
		foreach ( $manifest['documents'] as $document ) {
			if ( in_array( $id, $document['product_ids'], true ) ) {
				$allowed_urls = array_merge( $allowed_urls, $document['aliases'] );
			}
		}
		foreach ( Publication::faqs_for( $id, $manifest ) as $faq ) {
			if ( ! in_array( strtok( (string) $faq['citation']['url'], '#' ), $allowed_urls, true ) ) {
				continue;
			}
			$question = $german && '' !== $faq['question_de'] ? $faq['question_de'] : $faq['question'];
			$answer   = $german && '' !== $faq['answer_de'] ? $faq['answer_de'] : $faq['answer'];
			if ( '' === trim( $question ) ) {
				continue;
			}
			$page    = (int) $faq['citation']['page'];
			$title   = (string) ( $faq['citation']['title'] ?? '' );
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
		if ( array() !== $faqs ) {
			return $items;
		}
		foreach ( $this->view->faqs( $id ) as $faq ) {
			if ( '' === trim( $faq['question'] ) ) {
				continue;
			}
			$items[] = array(
				'question'   => $faq['question'],
				'answer'     => $faq['answer'],
				'source'     => '',
				'source_url' => '',
			);
		}

		return $items;
	}

	/**
	 * A document type as the register names it.
	 *
	 * The row's role and type go through the one mapping the product page's
	 * document cards use (Materials::document_kind), so a German row reads
	 * like its English twin (`Datenblatt` and `datasheet` are both
	 * `datasheet`) — the German table stores German type words, and the
	 * register read them all as `Document` until 2026-10-16. The result is
	 * then closed on the register's own vocabulary: a word the register does
	 * not know still reads `Document`.
	 *
	 * @param string $stored Stored type.
	 * @param string $role   Stored role, '' when the row states none.
	 */
	public static function type( string $stored, string $role = '' ): string {
		$kind = Materials::document_kind( $role, $stored );

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
