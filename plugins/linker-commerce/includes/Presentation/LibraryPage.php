<?php
/**
 * The document register and the product answers of /faq-download/.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Catalog\DocumentLibrary;

/**
 * The library page's two fragments (docs/specs/19-tool-pages.md): the
 * documents the catalogue states, and the products' own answers. The page
 * around them — its words, its sections, its order — is the LiveCanvas
 * dynamic template assigned to the page; these shortcodes print lists and
 * nothing else, no script and no inline style, so the page is complete
 * without JavaScript (the old page's workbench was a script, and its removal
 * left a shell).
 */
final class LibraryPage {

	/**
	 * The register the fragments list.
	 *
	 * @var DocumentLibrary
	 */
	private readonly DocumentLibrary $library;

	/**
	 * Sets up the page.
	 *
	 * @param DocumentLibrary|null $library Register override (tests).
	 */
	public function __construct( ?DocumentLibrary $library = null ) {
		$this->library = $library ?? new DocumentLibrary();
	}

	/**
	 * Adds the fragments' shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_document_register', array( $this, 'register_documents' ) );
		add_shortcode( 'linker_product_answers', array( $this, 'product_answers' ) );
	}

	/**
	 * The document register, grouped by brand.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function register_documents( $atts = array() ): string {
		unset( $atts );
		$groups = array();
		foreach ( $this->library->documents() as $document ) {
			$groups[ $document['brand'] ][] = $document;
		}
		$html = '<div id="linker-documents" class="linker-documents flex flex-col gap-6">';
		foreach ( $groups as $brand => $documents ) {
			$html .= '<section class="linker-documents-group" data-brand="' . esc_attr( sanitize_title( (string) $brand ) ) . '">';
			$html .= '<h3 class="linker-documents-brand mb-3 text-lg font-semibold text-(--proto-navy-deep)">' . esc_html( (string) $brand ) . ' <span class="linker-documents-count text-sm font-normal text-neutral-500">' . esc_html(
				sprintf(
					/* translators: %d: number of documents of the brand. */
					_n( '%d document', '%d documents', count( $documents ), 'linker-commerce' ),
					count( $documents )
				)
			) . '</span></h3>';
			$html .= '<ul class="linker-documents-list border-t border-neutral-200">';
			foreach ( $documents as $document ) {
				$html .= $this->document( $document );
			}
			$html .= '</ul></section>';
		}

		return $html . '</div>';
	}

	/**
	 * The products' answers, grouped by brand.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes, unused.
	 */
	public function product_answers( $atts = array() ): string {
		unset( $atts );
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$groups = array();
		foreach ( $this->library->answers( $german ? 'de' : 'en' ) as $answer ) {
			$groups[ strtok( $answer['product'], ' ' ) ][] = $answer;
		}
		$html = '<div id="linker-answers" class="linker-answers flex flex-col gap-8">';
		foreach ( $groups as $brand => $answers ) {
			$html .= '<section class="linker-answers-group" data-brand="' . esc_attr( sanitize_title( (string) $brand ) ) . '">';
			$html .= '<h3 class="linker-answers-brand mb-3 text-lg font-semibold text-(--proto-navy-deep)">' . esc_html( (string) $brand ) . ' <span class="linker-answers-count text-sm font-normal text-neutral-500">' . esc_html(
				sprintf(
					/* translators: %d: number of answers of the brand. */
					_n( '%d answer', '%d answers', count( $answers ), 'linker-commerce' ),
					count( $answers )
				)
			) . '</span></h3>';
			foreach ( $answers as $answer ) {
				$html .= '<details class="linker-answer border-b border-neutral-200 py-3">';
				$html .= '<summary class="linker-answer-question cursor-pointer font-semibold text-(--proto-navy-deep)">' . esc_html( $answer['question'] ) . '</summary>';
				$html .= '<div class="linker-answer-body mt-2 leading-relaxed text-neutral-700">' . wp_kses_post( wpautop( $answer['answer'] ) );
				$html .= '<p class="linker-answer-product mt-2 text-sm text-neutral-500"><a href="' . esc_url( $answer['url'] ) . '">' . esc_html( $answer['product'] ) . '</a>';
				if ( '' !== $answer['source'] ) {
					$html .= ' — <a href="' . esc_url( $answer['source_url'] ) . '">' . esc_html( $answer['source'] ) . '</a>';
				}
				$html .= '</p>';
				$html .= '</div></details>';
			}
			$html .= '</section>';
		}

		return $html . '</div>';
	}

	/**
	 * One document of the register.
	 *
	 * @param array{title: string, url: string, type: string, language: string, brand: string, covers: list<string>} $document Document.
	 */
	private function document( array $document ): string {
		$html  = '<li class="linker-document grid gap-1 border-b border-neutral-200 py-3 md:grid-cols-[9rem_1fr_11rem_9rem_7rem] md:items-baseline md:gap-4" data-type="' . esc_attr( $document['type'] ) . '" data-language="' . esc_attr( $document['language'] ) . '">';
		$html .= '<p class="linker-document-type text-xs font-semibold uppercase text-neutral-500">' . esc_html( self::type_label( $document['type'] ) ) . '</p>';
		$html .= '<p class="linker-document-title font-semibold text-(--proto-navy-deep)">' . esc_html( $document['title'] ) . '</p>';
		$html .= '<p class="linker-document-covers text-sm text-neutral-500">' . esc_html( self::covers( $document['covers'] ) ) . '</p>';
		$html .= '<p class="linker-document-language text-sm text-neutral-500">' . esc_html( self::language_label( $document['language'] ) ) . '</p>';
		$html .= '<p class="linker-document-download"><a class="text-(--proto-accent) underline" href="' . esc_url( $document['url'] ) . '">' . esc_html__( 'Download', 'linker-commerce' ) . '</a></p>';

		return $html . '</li>';
	}

	/**
	 * What a document covers: the products whose pages state it.
	 *
	 * @param string[] $covers Product names.
	 * @return string The sentence.
	 */
	private static function covers( array $covers ): string {
		if ( 1 === count( $covers ) ) {
			/* translators: %s: product name. */
			return sprintf( __( 'covers %s', 'linker-commerce' ), $covers[0] );
		}

		return sprintf(
			/* translators: %d: number of products. */
			_n( 'covers %d product', 'covers %d products', count( $covers ), 'linker-commerce' ),
			count( $covers )
		);
	}

	/**
	 * A document type's display name.
	 *
	 * @param string $type Stored type key.
	 */
	private static function type_label( string $type ): string {
		$labels = array(
			'datasheet'     => __( 'Datasheet', 'linker-commerce' ),
			'manual'        => __( 'Manual', 'linker-commerce' ),
			'certificate'   => __( 'Certificate', 'linker-commerce' ),
			'compatibility' => __( 'Compatibility', 'linker-commerce' ),
			'warranty'      => __( 'Warranty', 'linker-commerce' ),
			'brochure'      => __( 'Brochure', 'linker-commerce' ),
			'document'      => __( 'Document', 'linker-commerce' ),
		);

		return $labels[ $type ] ?? $labels['document'];
	}

	/**
	 * A document language's display name; the combined forms read as stored.
	 *
	 * @param string $language Stored language.
	 */
	private static function language_label( string $language ): string {
		$labels = array(
			'EN'  => __( 'English', 'linker-commerce' ),
			'DE'  => __( 'German', 'linker-commerce' ),
			'MUL' => __( 'Multilingual', 'linker-commerce' ),
		);

		return $labels[ $language ] ?? $language;
	}
}
