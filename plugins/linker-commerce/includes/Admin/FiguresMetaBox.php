<?php
/**
 * The figure-citation meta box of the product edit screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Admin;

use Linker\Commerce\Catalog\EngineeringData;
use Linker\Commerce\Catalog\SelectionFacts;

/**
 * One row per figure of the product's _tv_b2b_figures: the key (read-only),
 * the value, the unit, and the citation — a document of this product and the
 * page (docs/specs/8-engineering-data.md). Changing a value or a unit asks
 * for the citation to be filled again: a changed entry without a document and
 * page is refused with a notice and keeps its previous value.
 */
final class FiguresMetaBox {

	/**
	 * The units the box offers, with the free-text fallback.
	 */
	private const UNITS = array( '', 'V', 'A', 'W', 'kW', 'Wp', 'kWp', 'kWh', 'Wh', 'VA', 'Hz', '°C', '%', 'mm', 'kg', 'ms', 'cycles', 'modules', 'packs' );

	/**
	 * The nonce action and field of the box.
	 */
	private const NONCE_ACTION = 'linker_commerce_figures';
	private const NONCE_FIELD  = 'linker_commerce_figures_nonce';

	/**
	 * The user meta that carries the refused keys to the next admin screen:
	 * the new product form saves through REST and never runs the classic
	 * redirect a notice could ride along on.
	 */
	private const REFUSED_META = 'linker_commerce_figures_refused';

	/**
	 * Adds the box; runs on add_meta_boxes.
	 */
	public function register(): void {
		add_meta_box(
			'linker-commerce-figures',
			__( 'Figures and citations', 'linker-commerce' ),
			// The box needs the product's ID, not the post object itself.
			static fn( $post ) => ( new self() )->render( (int) $post->ID ),
			'product',
			'normal',
			'default'
		);
	}

	/**
	 * The box: one row per figure entry, the citation from the product's
	 * documents (docs/specs/8-engineering-data.md). Prints nothing when the
	 * product states no figures.
	 *
	 * @param int $post_id Product ID.
	 */
	public function render( int $post_id ): void {
		wp_nonce_field( self::NONCE_ACTION, self::NONCE_FIELD );
		$figures   = $this->figures( $post_id );
		$documents = $this->documents( $post_id );
		if ( array() === $figures ) {
			echo '<p>' . esc_html__( 'This product states no figures.', 'linker-commerce' ) . '</p>';

			return;
		}
		echo '<p>' . esc_html__( 'Changing a value or a unit requires the citation to be given again: the document and the page it is printed on.', 'linker-commerce' ) . '</p>';
		echo '<table class="widefat striped"><thead><tr>'
			. '<th style="width:22%">' . esc_html__( 'Key', 'linker-commerce' ) . '</th>'
			. '<th style="width:20%">' . esc_html__( 'Value', 'linker-commerce' ) . '</th>'
			. '<th style="width:10%">' . esc_html__( 'Unit', 'linker-commerce' ) . '</th>'
			. '<th style="width:34%">' . esc_html__( 'Document', 'linker-commerce' ) . '</th>'
			. '<th style="width:7%">' . esc_html__( 'Page', 'linker-commerce' ) . '</th>'
			. '<th style="width:7%"></th>'
			. '</tr></thead><tbody>';
		foreach ( $figures as $key => $entry ) {
			$this->row( (string) $key, $entry, $documents );
		}
		echo '</tbody></table>';
	}

	/**
	 * One row of the box.
	 *
	 * @param string                     $key       Figure key.
	 * @param array<string, mixed>       $entry     The stored entry.
	 * @param list<array<string, mixed>> $documents The product's documents.
	 */
	private function row( string $key, array $entry, array $documents ): void {
		$citation = is_array( $entry['citation'] ?? null ) ? $entry['citation'] : array();
		$locked   = ! isset( $citation['url'] ) || ! isset( $citation['page'] );
		printf(
			'<tr data-key="%1$s"><td><code>%1$s</code></td>',
			esc_attr( $key )
		);
		echo '<td><input type="text" style="width:100%" name="' . esc_attr( $this->field( $key, 'value' ) ) . '" value="' . esc_attr( (string) ( $entry['value'] ?? '' ) ) . '" /></td>';
		echo '<td><select style="width:100%" name="' . esc_attr( $this->field( $key, 'unit' ) ) . '">';
		$unit = (string) ( $entry['unit'] ?? '' );
		foreach ( array_unique( array_merge( self::UNITS, array( $unit ) ) ) as $option ) {
			printf(
				'<option value="%1$s"%2$s>%1$s</option>',
				esc_attr( $option ),
				selected( $option, $unit, false )
			);
		}
		echo '</select></td>';
		echo '<td><select style="width:100%" name="' . esc_attr( $this->field( $key, 'document' ) ) . '">';
		printf(
			'<option value="">%s</option>',
			esc_html__( '— none —', 'linker-commerce' )
		);
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
			'<td><input type="number" min="1" step="1" style="width:100%%" name="%1$s" value="%2$s" /></td>',
			esc_attr( $this->field( $key, 'page' ) ),
			esc_attr( (string) ( $citation['page'] ?? '' ) )
		);
		// The locked marker: the entry had no citation before, so the row is
		// marked until one is given (the save refuses a change without it).
		printf(
			'<td>%s</td></tr>',
			$locked ? '<span class="dashicons dashicons-warning" title="' . esc_attr__( 'No citation', 'linker-commerce' ) . '"></span>' : ''
		);
	}

	/**
	 * Saves the figures; runs on save_post_product, after WooCommerce's own
	 * save. Only the rows the box sent are touched; a changed value or unit
	 * without a document and page is refused and keeps its previous entry.
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
		$figures = $this->figures( $post_id );
		if ( array() === $figures ) {
			return;
		}
		$documents = array();
		foreach ( $this->documents( $post_id ) as $document ) {
			if ( is_string( $document['url'] ?? null ) ) {
				$documents[] = $document['url'];
			}
		}
		$refused = array();
		foreach ( $rows as $key => $row ) {
			if ( ! array_key_exists( $key, $figures ) || ! is_array( $figures[ $key ] ) ) {
				continue; // the box edits the entries that exist; it does not add or rename keys.
			}
			$old            = $figures[ $key ];
			$entry          = $old;
			$entry['value'] = $row['value'];
			$entry['unit']  = $row['unit'];
			// A citation names one of this product's documents and a page of it; anything else is no citation.
			$citable = in_array( $row['document'], $documents, true ) && ctype_digit( $row['page'] ) && (int) $row['page'] >= 1;
			if ( ! $citable ) {
				if ( (string) ( $old['value'] ?? '' ) === $row['value'] && (string) ( $old['unit'] ?? '' ) === $row['unit'] ) {
					// Nothing changed: the old citation, or its absence, stays.
					continue;
				}
				$refused[] = $key;
				continue;
			}
			$entry['citation'] = array(
				'url'  => $row['document'],
				'page' => (int) $row['page'],
			);
			if ( $entry === $old ) {
				continue;
			}
			$figures[ $key ] = $entry;
		}
		if ( array() !== $refused ) {
			// The new product form saves through REST and never runs the classic
			// redirect, so the keys wait for the next admin screen of this user.
			update_user_meta( get_current_user_id(), self::REFUSED_META, implode( ',', $refused ) );
		}
		// The entries are stored with unescaped Unicode and slashes, as the migration writes them.
		update_post_meta(
			$post_id,
			SelectionFacts::FIGURES_META_KEY,
			wp_slash( (string) wp_json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) )
		);
	}

	/**
	 * Prints the refused-rows notice on the next admin screen: the save left
	 * the refused keys in the user's meta (the new product form saves through
	 * REST, with no classic redirect to ride along on). Registered once at
	 * register(); silent when no keys wait.
	 */
	public function notice_refused(): void {
		$keys = (string) get_user_meta( get_current_user_id(), self::REFUSED_META, true );
		if ( '' === $keys ) {
			return;
		}
		delete_user_meta( get_current_user_id(), self::REFUSED_META );
		printf(
			'<div class="notice notice-error is-dismissible"><p>%s</p></div>',
			esc_html(
				sprintf(
					/* translators: %s: list of figure keys. */
					__( 'Figures %s kept their previous value: a changed value needs the document and the page it is printed on.', 'linker-commerce' ),
					$keys
				)
			)
		);
	}

	/**
	 * The rows the box sent: key => {value, unit, document, page}. Null when
	 * the request carries none of the box's fields (another writer saved).
	 *
	 * Save() has verified the box's nonce before this runs.
	 *
	 * @return array<string, array{value: string, unit: string, document: string, page: string}>|null
	 */
	private function posted_rows(): ?array {
		// The box posts linker_figures[key][field]; PHP parses that into a
		// nested array (the flat "linker_figures[key][field]" keys a naive
		// reader looks for never occur in a browser post).
		// phpcs:ignore WordPress.Security.NonceVerification.Missing, WordPress.Security.ValidatedSanitizedInput.InputNotSanitized, WordPress.Security.ValidatedSanitizedInput.MissingUnslash -- save() verified the box's nonce; each field is sanitized below, and the row list is unslashed once.
		$posted = isset( $_POST['linker_figures'] ) && is_array( $_POST['linker_figures'] ) ? wp_unslash( $_POST['linker_figures'] ) : array();
		$rows   = array();
		foreach ( $posted as $key => $fields ) {
			if ( ! is_string( $key ) || ! is_array( $fields ) ) {
				continue;
			}
			$row = array(
				'value'    => '',
				'unit'     => '',
				'document' => '',
				'page'     => '',
			);
			foreach ( array_keys( $row ) as $field ) {
				$value         = $fields[ $field ] ?? '';
				$row[ $field ] = sanitize_text_field( is_scalar( $value ) ? (string) $value : '' );
			}
			$rows[ $key ] = $row;
		}

		return array() === $rows ? null : $rows;
	}

	/**
	 * The name of a row field in the form.
	 *
	 * @param string $key   Figure key.
	 * @param string $field The row field: value, unit, document or page.
	 */
	private function field( string $key, string $field ): string {
		return 'linker_figures[' . $key . '][' . $field . ']';
	}

	/**
	 * The product's figures, decoded, in stored order.
	 *
	 * @param int $post_id Product ID.
	 * @return array<string, mixed>
	 */
	private function figures( int $post_id ): array {
		$figures = get_post_meta( $post_id, SelectionFacts::FIGURES_META_KEY, true );
		if ( is_string( $figures ) ) {
			$figures = json_decode( $figures, true );
		}

		return is_array( $figures ) ? $figures : array();
	}

	/**
	 * The product's documents, the same list the feed carries.
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
