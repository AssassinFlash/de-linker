<?php
/**
 * The document meta box of the product edit screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Admin;

use Linker\Commerce\Catalog\EngineeringData;

/**
 * One row per document of the product's `_linker_documents` — the list the
 * product page, the engineering feed and the Genie abilities read. The rows
 * are the maintenance entry: title, URL, type and language, with the shape
 * `{url, title, type, lang}` the migration wrote (tools/migrate/8-engineering.py).
 *
 * Every document is a file of our own media library (owner ruling 2026-09-02,
 * docs/specs/8-engineering-data.md): the URL of a document is the address the
 * site serves, never a link to a third-party source. Changing what a document
 * SAYS stays with the owner, item by item (ticket #68); this box is the entry
 * that makes the list maintainable in the standard editor.
 */
final class DocumentsMetaBox {


	/**
	 * The document types the list uses, from the migrated data.
	 */
	private const TYPES = array( 'datasheet', 'manual', 'warranty', 'document' );

	/**
	 * Empty rows offered below the stored ones, so an editor can add a
	 * document without JavaScript.
	 */
	private const SPARE_ROWS = 2;

	/**
	 * The nonce action and field of the box.
	 */
	private const NONCE_ACTION = 'linker_commerce_documents';
	private const NONCE_FIELD  = 'linker_commerce_documents_nonce';

	/**
	 * Adds the box; runs on add_meta_boxes.
	 */
	public function register(): void {
		add_meta_box(
			'linker-commerce-documents',
			__( 'Documents', 'linker-commerce' ),
			static fn( $post ) => ( new self() )->render( (int) $post->ID ),
			'product',
			'normal',
			'default'
		);
	}

	/**
	 * The box: one row per stored document and spare empty rows.
	 *
	 * @param int $post_id Product ID.
	 */
	public function render( int $post_id ): void {
		wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD );
		$documents = $this->documents( $post_id );
		echo '<p>' . esc_html__( 'The documents shown on the product page and used as citations: datasheets, manuals and warranty terms of our own media library.', 'linker-commerce' ) . '</p>';
		echo '<p>' . esc_html__( 'The file itself is uploaded to the media library; the address here is the media file\'s URL. What a document may state is decided item by item — do not change a value or a claim without that confirmation.', 'linker-commerce' ) . '</p>';
		echo '<table class="widefat striped"><thead><tr>'
		. '<th style="width:36%">' . esc_html__( 'Title', 'linker-commerce' ) . '</th>'
		. '<th style="width:38%">' . esc_html__( 'URL', 'linker-commerce' ) . '</th>'
		. '<th style="width:12%">' . esc_html__( 'Type', 'linker-commerce' ) . '</th>'
		. '<th style="width:8%">' . esc_html__( 'Language', 'linker-commerce' ) . '</th>'
		. '<th style="width:6%">' . esc_html__( 'Remove', 'linker-commerce' ) . '</th>'
		. '</tr></thead><tbody>';
		$index = 0;
		foreach ( $documents as $document ) {
			$this->row( $index, $document, false );
			++$index;
		}
		for ( $spare = 0; $spare < self::SPARE_ROWS; $spare++ ) {
			$this->row( $index + $spare, array(), true );
		}
		echo '</tbody></table>';
	}

	/**
	 * One row of the box.
	 *
	 * @param int                  $index    Row index.
	 * @param array<string, mixed> $document The stored document, empty for a spare row.
	 * @param bool                 $spare    Whether the row is an empty spare.
	 */
	private function row( int $index, array $document, bool $spare ): void {
		$field = static fn( string $key ): string => sprintf( 'linker_documents[%d][%s]', $index, $key );
		$title = (string) ( $document['title'] ?? '' );
		$url   = (string) ( $document['url'] ?? '' );
		$type  = (string) ( $document['type'] ?? '' );
		$lang  = (string) ( $document['lang'] ?? '' );
		echo '<tr>';
		printf(
			'<td><input type="text" style="width:100%%" name="%1$s" value="%2$s" aria-label="%3$s" /></td>',
			esc_attr( $field( 'title' ) ),
			esc_attr( $title ),
			esc_attr__( 'Title', 'linker-commerce' )
		);
		printf(
			'<td><input type="url" style="width:100%%" name="%1$s" value="%2$s" aria-label="%3$s" /></td>',
			esc_attr( $field( 'url' ) ),
			esc_attr( $url ),
			esc_attr__( 'URL', 'linker-commerce' )
		);
		echo '<td><select style="width:100%" name="' . esc_attr( $field( 'type' ) ) . '" aria-label="' . esc_attr__( 'Type', 'linker-commerce' ) . '"><option value=""></option>';
		foreach ( array_unique( array_merge( self::TYPES, '' === $type ? array() : array( $type ) ) ) as $option ) {
			printf(
				'<option value="%1$s"%2$s>%1$s</option>',
				esc_attr( $option ),
				selected( $option, $type, false )
			);
		}
		echo '</select></td>';
		echo '<td><select style="width:100%" name="' . esc_attr( $field( 'lang' ) ) . '" aria-label="' . esc_attr__( 'Language', 'linker-commerce' ) . '">';
		foreach ( array(
			''   => '—',
			'en' => 'EN',
			'de' => 'DE',
		) as $value => $label ) {
			printf(
				'<option value="%1$s"%2$s>%3$s</option>',
				esc_attr( (string) $value ),
				selected( (string) $value, $lang, false ),
				esc_html( $label )
			);
		}
		echo '</select></td>';
		printf(
			'<td><input type="checkbox" name="%1$s" value="1" aria-label="%2$s"%3$s /></td>',
			esc_attr( $field( 'remove' ) ),
			esc_attr__( 'Remove', 'linker-commerce' ),
			$spare ? ' disabled' : ''
		);
		echo '</tr>';
	}

	/**
	 * Saves the document list; runs on save_post_product. Rows beyond those
	 * the box sent are kept: another writer may have appended rows after this
	 * box was rendered, and the box did not see them. A row that is removed
	 * or has no URL is dropped; a row with an address that is not a URL of
	 * this site keeps its previous entry.
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
		$previous  = $this->documents( $post_id );
		$documents = array();
		foreach ( $rows as $index => $row ) {
			if ( $row['remove'] ) {
				continue;
			}
			$url = $this->hosted_url( $row['url'] );
			if ( '' !== $row['url'] && '' === $url ) {
				// An address that is not one of ours: the previous entry stays.
				if ( isset( $previous[ $index ] ) ) {
					$documents[] = $previous[ $index ];
				}
				continue;
			}
			if ( '' === $url ) {
				// No address, no document: the row is dropped (removing it is
				// what clearing the address means).
				continue;
			}
			$document    = array(
				'url'   => $url,
				'title' => $row['title'],
				'type'  => $row['type'],
				'lang'  => $row['lang'],
			);
			$documents[] = $document;
		}
		// Rows beyond the ones the box sent are kept: another writer may have
		// appended them after this box was rendered, and the box speaks only
		// for the rows it carried. FaqsMetaBox merges its list the same way.
		$last_sent = 0 === count( $rows ) ? -1 : max( array_keys( $rows ) );
		$documents = array_merge( $documents, array_slice( $previous, $last_sent + 1 ) );
		update_post_meta( $post_id, EngineeringData::DOCUMENTS_META_KEY, $documents );
	}

	/**
	 * The rows the box posted, ordered by their index, or null when the box
	 * sent nothing.
	 *
	 * @return array<int, array{title: string, url: string, type: string, lang: string, remove: bool}>|null
	 */
	private function posted_rows(): ?array {
		// The box posts linker_documents[index][field]; PHP parses that into a
		// nested array.
		// phpcs:ignore WordPress.Security.NonceVerification.Missing, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized, WordPress.Security.ValidatedSanitizedInput.MissingUnslash -- save() verified the box's nonce; each field is sanitized below, and the row list is unslashed once.
		$posted = isset( $_POST['linker_documents'] ) && is_array( $_POST['linker_documents'] ) ? wp_unslash( $_POST['linker_documents'] ) : array();
		$rows   = array();
		foreach ( $posted as $index => $fields ) {
			if ( ! is_array( $fields ) ) {
				continue;
			}
			$row = array(
				'title'  => '',
				'url'    => '',
				'type'   => '',
				'lang'   => '',
				'remove' => false,
			);
			foreach ( array( 'title', 'type', 'lang' ) as $field ) {
				$value         = $fields[ $field ] ?? '';
				$row[ $field ] = sanitize_text_field( is_scalar( $value ) ? (string) $value : '' );
			}
			$url                  = $fields['url'] ?? '';
			$row['url']           = esc_url_raw( is_scalar( $url ) ? (string) $url : '' );
			$remove               = $fields['remove'] ?? '';
			$row['remove']        = '1' === ( is_scalar( $remove ) ? (string) $remove : '' );
			$rows[ (int) $index ] = $row;
		}
		if ( array() === $rows ) {
			return null;
		}
		ksort( $rows );
		return $rows;
	}

	/**
	 * An URL of this site's media library, '' for anything else.
	 *
	 * @param string $url The posted address.
	 */
	private function hosted_url( string $url ): string {
		if ( '' === $url ) {
			return '';
		}
		$host = (string) wp_parse_url( $url, PHP_URL_HOST );
		if ( '' !== $host && strtolower( $host ) !== strtolower( (string) wp_parse_url( home_url(), PHP_URL_HOST ) ) ) {
			return '';
		}
		return $url;
	}

	/**
	 * The product's documents, the same list the figures box and the feed read.
	 *
	 * @param  int $post_id Product ID.
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
