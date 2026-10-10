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
 * question without a document and page is refused, the previous row stays,
 * and the row is named in a notice on the next admin screen.
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
	 * The user meta that carries the refused rows to the next admin screen,
	 * the same channel FiguresMetaBox rides: the new product form saves
	 * through REST and never runs the classic redirect a notice could ride
	 * along on.
	 */
	private const REFUSED_META = 'linker_commerce_faqs_refused';

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
	 * Saves the FAQ list; runs on save_post_product. Rows beyond those the box
	 * sent are kept: another writer may have appended rows after this box was
	 * rendered, and the box did not see them. A row with a question but no
	 * citation is refused — the previous item at that index stays and the row
	 * waits in the user's meta for the notice on the next admin screen.
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
		$items   = array();
		$refused = array();
		foreach ( $rows as $index => $row ) {
			$question = $row['question'];
			if ( '' === $question ) {
				continue;
			}
			$citable = in_array( $row['document'], $document_urls, true ) && ctype_digit( $row['page'] ) && (int) $row['page'] >= 1;
			if ( ! $citable ) {
				$refused[] = (string) ( $index + 1 );
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
		$last_sent = 0 === count( $rows ) ? -1 : max( array_keys( $rows ) );
		$items     = array_merge( $items, array_slice( $previous, $last_sent + 1 ) );
		$json      = Faqs::encode( $items );
		update_post_meta( $post_id, Faqs::META_KEY, wp_slash( $json ) );
		Faqs::mirror_to_twin( $post_id, $json );
		if ( array() !== $refused ) {
			// The new product form saves through REST and never runs the
			// classic redirect, so the rows wait for the next admin screen
			// of this user.
			update_user_meta( get_current_user_id(), self::REFUSED_META, implode( ',', $refused ) );
		}
	}

	/**
	 * Prints the refused-rows notice on the next admin screen: the save left
	 * the refused rows in the user's meta, the channel FiguresMetaBox rides.
	 * Registered once at Plugin's hooks; silent when no rows wait. The row
	 * numbers count the box's rows from 1.
	 */
	public function notice_refused(): void {
		$rows = (string) get_user_meta( get_current_user_id(), self::REFUSED_META, true );
		if ( '' === $rows ) {
			return;
		}
		delete_user_meta( get_current_user_id(), self::REFUSED_META );
		printf(
			'<div class="notice notice-error is-dismissible"><p>%s</p></div>',
			esc_html(
				sprintf(
					/* translators: %s: list of row numbers. */
					__( 'FAQ rows %s kept their previous content: an answer needs the document and the page it is printed on.', 'linker-commerce' ),
					$rows
				)
			)
		);
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
