<?php
/**
 * The FAQ meta box of the product edit screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Admin;

use Linker\Commerce\Catalog\EngineeringData;
use Linker\Commerce\Catalog\Faqs;

/**
 * One row per FAQ of the product's `_linker_faqs`: the English question and
 * answer, the German pair, and the citation — a document of this product and
 * the page (docs/specs/15-faq.md). A row without a question is dropped; a
 * question without a document and page is refused and the previous row stays.
 */
final class FaqsMetaBox {

	/**
	 * Empty rows offered below the stored ones, so an editor can add an item
	 * without JavaScript.
	 */
	private const SPARE_ROWS = 2;

	/**
	 * The nonce action and field of the box.
	 */
	private const NONCE_ACTION = 'linker_commerce_faqs';
	private const NONCE_FIELD  = 'linker_commerce_faqs_nonce';

	/**
	 * Adds the box; runs on add_meta_boxes.
	 */
	public function register(): void {
		add_meta_box(
			'linker-commerce-faqs',
			__( 'FAQ', 'linker-commerce' ),
			static fn( $post ) => ( new self() )->render( (int) $post->ID ),
			'product',
			'normal',
			'default'
		);
	}

	/**
	 * The box: one row per stored item and spare empty rows.
	 *
	 * @param int $post_id Product ID.
	 */
	public function render( int $post_id ): void {
		wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD );
		$items     = Faqs::of( $post_id );
		$documents = $this->documents( $post_id );
		echo '<p>' . esc_html__( 'Each answer needs the document and the page it is printed on. A row without a question is dropped.', 'linker-commerce' ) . '</p>';
		echo '<table class="widefat striped"><thead><tr>'
			. '<th style="width:18%">' . esc_html__( 'Question', 'linker-commerce' ) . '</th>'
			. '<th style="width:22%">' . esc_html__( 'Answer', 'linker-commerce' ) . '</th>'
			. '<th style="width:18%">' . esc_html__( 'Question (German)', 'linker-commerce' ) . '</th>'
			. '<th style="width:22%">' . esc_html__( 'Answer (German)', 'linker-commerce' ) . '</th>'
			. '<th style="width:14%">' . esc_html__( 'Document', 'linker-commerce' ) . '</th>'
			. '<th style="width:6%">' . esc_html__( 'Page', 'linker-commerce' ) . '</th>'
			. '</tr></thead><tbody>';
		$count = count( $items ) + self::SPARE_ROWS;
		for ( $index = 0; $index < $count; $index++ ) {
			$this->row( $index, $items[ $index ] ?? array(), $documents );
		}
		echo '</tbody></table>';
	}

	/**
	 * Saves the FAQ list; runs on save_post_product. Rows the box did not send
	 * are left as they are (another writer saved). A question without a
	 * citation is refused and the previous item at that index stays.
	 *
	 * @param int $post_id Product ID.
	 */
	public function save( int $post_id ): void {
		if ( ! isset( $_POST[ self::NONCE_FIELD ] )
			|| ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST[ self::NONCE_FIELD ] ) ), self::NONCE_ACTION )
			|| ! current_user_can( 'edit_post', $post_id )
			|| wp_is_post_revision( $post_id )
			|| wp_is_post_autosave( $post_id )
		) {
			return;
		}
		$rows = $this->posted_rows();
		if ( null === $rows ) {
			return;
		}
			$previous      = Faqs::of( $post_id );
			$catalogue     = $this->documents( $post_id );
			$document_urls = array();
		foreach ( $catalogue as $document ) {
			if ( is_string( $document['url'] ?? null ) ) {
				$document_urls[] = $document['url'];
			}
		}
		$items = array();
		foreach ( $rows as $index => $row ) {
			$question = $row['question'];
			if ( '' === $question ) {
				continue;
			}
			$citable = in_array( $row['document'], $document_urls, true ) && ctype_digit( $row['page'] ) && (int) $row['page'] >= 1;
			if ( ! $citable ) {
				if ( isset( $previous[ $index ] ) ) {
					$items[] = $previous[ $index ];
				}
				continue;
			}
			$item  = array(
				'question'    => $question,
				'answer'      => $row['answer'],
				'question_de' => $row['question_de'],
				'answer_de'   => $row['answer_de'],
				'citation'    => array(
					'url'  => $row['document'],
					'page' => (int) $row['page'],
				),
			);
			$title = $this->title_of( $row['document'], $catalogue );
			if ( '' !== $title ) {
				$item['citation']['title'] = $title;
			}
			$items[] = $item;
		}
		$json = Faqs::encode( $items );
		update_post_meta( $post_id, Faqs::META_KEY, wp_slash( $json ) );
		$this->mirror( $post_id, $json );
	}

	/**
	 * Copies the same JSON onto the German product when Polylang has a twin
	 * (docs/specs/15-faq.md: the German object follows #9).
	 *
	 * @param int    $post_id English or German product ID.
	 * @param string $json    Encoded list.
	 */
	private function mirror( int $post_id, string $json ): void {
		if ( ! function_exists( 'pll_get_post_language' ) || ! function_exists( 'pll_get_post' ) ) {
			return;
		}
		$language = pll_get_post_language( $post_id );
		$twin_of  = 'en' === $language ? 'de' : ( 'de' === $language ? 'en' : '' );
		if ( '' === $twin_of ) {
			return;
		}
		$twin = pll_get_post( $post_id, $twin_of );
		if ( $twin > 0 && (int) $twin !== $post_id ) {
			update_post_meta( (int) $twin, Faqs::META_KEY, wp_slash( $json ) );
		}
	}

	/**
	 * The title of a document URL in the product's list.
	 *
	 * @param string                     $url       Document URL.
	 * @param list<array<string, mixed>> $documents The product's documents.
	 */
	private function title_of( string $url, array $documents ): string {
		foreach ( $documents as $document ) {
			if ( ( $document['url'] ?? '' ) === $url ) {
				return (string) ( $document['title'] ?? '' );
			}
		}

		return '';
	}

	/**
	 * One row of the box.
	 *
	 * @param int                        $index     Row index.
	 * @param array<string, mixed>       $item      Stored item or empty.
	 * @param list<array<string, mixed>> $documents The product's documents.
	 */
	private function row( int $index, array $item, array $documents ): void {
		$citation = is_array( $item['citation'] ?? null ) ? $item['citation'] : array();
		echo '<tr>';
		printf(
			'<td><textarea rows="3" style="width:100%%" name="%1$s">%2$s</textarea></td>',
			esc_attr( $this->field( $index, 'question' ) ),
			esc_textarea( (string) ( $item['question'] ?? '' ) )
		);
		printf(
			'<td><textarea rows="3" style="width:100%%" name="%1$s">%2$s</textarea></td>',
			esc_attr( $this->field( $index, 'answer' ) ),
			esc_textarea( (string) ( $item['answer'] ?? '' ) )
		);
		printf(
			'<td><textarea rows="3" style="width:100%%" name="%1$s">%2$s</textarea></td>',
			esc_attr( $this->field( $index, 'question_de' ) ),
			esc_textarea( (string) ( $item['question_de'] ?? '' ) )
		);
		printf(
			'<td><textarea rows="3" style="width:100%%" name="%1$s">%2$s</textarea></td>',
			esc_attr( $this->field( $index, 'answer_de' ) ),
			esc_textarea( (string) ( $item['answer_de'] ?? '' ) )
		);
		echo '<td><select style="width:100%" name="' . esc_attr( $this->field( $index, 'document' ) ) . '">';
		printf( '<option value="">%s</option>', esc_html__( '— none —', 'linker-commerce' ) );
		foreach ( $documents as $document ) {
			$url = (string) ( $document['url'] ?? '' );
			if ( '' === $url ) {
				continue;
			}
			printf(
				'<option value="%1$s"%2$s>%3$s</option>',
				esc_attr( $url ),
				selected( $url, (string) ( $citation['url'] ?? '' ), false ),
				esc_html( (string) ( $document['title'] ?? $url ) )
			);
		}
		echo '</select></td>';
		printf(
			'<td><input type="number" min="1" step="1" style="width:100%%" name="%1$s" value="%2$s" /></td></tr>',
			esc_attr( $this->field( $index, 'page' ) ),
			esc_attr( (string) ( $citation['page'] ?? '' ) )
		);
	}

	/**
	 * The rows the box sent: index => fields. Null when the request carries
	 * none of the box's fields.
	 *
	 * Save() has verified the box's nonce before this runs.
	 *
	 * @return array<int, array{question: string, answer: string, question_de: string, answer_de: string, document: string, page: string}>|null
	 */
	private function posted_rows(): ?array {
		$rows = null;
		// phpcs:ignore WordPress.Security.NonceVerification.Missing -- save() verified the box's nonce before calling this.
		foreach ( $_POST as $name => $value ) {
			if ( ! is_string( $name )
				|| 1 !== preg_match( '/^linker_faqs\[(\d+)\]\[(question|answer|question_de|answer_de|document|page)\]$/', $name, $match )
			) {
				continue;
			}
			$index                       = (int) $match[1];
			$rows                        = $rows ?? array();
			$rows[ $index ]            ??= array(
				'question'    => '',
				'answer'      => '',
				'question_de' => '',
				'answer_de'   => '',
				'document'    => '',
				'page'        => '',
			);
			$text                        = is_array( $value ) ? '' : $value;
			$rows[ $index ][ $match[2] ] = 'answer' === $match[2] || 'answer_de' === $match[2]
				? sanitize_textarea_field( wp_unslash( $text ) )
				: sanitize_text_field( wp_unslash( $text ) );
		}
		if ( null !== $rows ) {
			ksort( $rows );
		}

		return $rows;
	}

	/**
	 * The name of a row field in the form.
	 *
	 * @param int    $index Row index.
	 * @param string $field The row field.
	 */
	private function field( int $index, string $field ): string {
		return 'linker_faqs[' . $index . '][' . $field . ']';
	}

	/**
	 * The product's documents, the same list the figures box uses.
	 *
	 * @param int $post_id Product ID.
	 * @return list<array<string, mixed>>
	 */
	private function documents( int $post_id ): array {
		$documents = get_post_meta( $post_id, EngineeringData::DOCUMENTS_META_KEY, true );
		if ( is_string( $documents ) ) {
			$documents = json_decode( $documents, true );
		}

		return is_array( $documents ) ? array_values( $documents ) : array();
	}
}
