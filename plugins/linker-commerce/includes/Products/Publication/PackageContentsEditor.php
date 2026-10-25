<?php
/**
 * Package contents maintained on the ordinary Woo product edit screen.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;

/**
 * Uses native capabilities, metadata, document associations and Woo CRUD.
 */
final class PackageContentsEditor {


	private const NONCE  = 'linker_package_contents_nonce';
	private const NOTICE = '_linker_package_contents_error';
	/** Guard Woo CRUD's nested save_post callback.
	 *
	 * @var bool
	 */
	private static bool $saving = false;

	/**
	 * Register native maintenance.
	 */
	public function register(): void {
		add_action( 'add_meta_boxes', array( $this, 'box' ) );
		add_action( 'save_post_product', array( $this, 'save' ), 30 );
		add_action( 'admin_notices', array( $this, 'notice' ) );
	}

	/**
	 * Native Woo product editor.
	 */
	public function box(): void {
		add_meta_box( 'linker-package-contents', __( 'Manufacturer package contents', 'linker-commerce' ), array( $this, 'render' ), 'product', 'normal', 'default' );
	}

	/**
	 * The quantities are per sales unit, with no independent product identities.
	 *
	 * @param \WP_Post $post Current native product.
	 */
	public function render( \WP_Post $post ): void {
		if ( Publication::canonical_id( $post->ID ) !== $post->ID ) {
			echo '<p>' . esc_html__( 'Maintain these declarations on the English source product.', 'linker-commerce' ) . '</p>';
			return;
		}
		$raw = get_post_meta( $post->ID, PackageContents::META_KEY, true );
		if ( '' !== $raw && array() !== $raw && ( ! is_array( $raw ) || 1 !== ( $raw['schema_version'] ?? null ) || ! is_array( $raw['items'] ?? null ) ) ) {
			echo '<p>' . esc_html__( 'The stored declarations have an unsupported format. They remain saved and unavailable for new releases.', 'linker-commerce' ) . '</p>';
			return;
		}
		$manifest = Publication::manifest();
		$docs     = array_filter( $manifest['documents'], static fn ( array $d ): bool => in_array( $post->ID, $d['product_ids'], true ) );
		$items    = is_array( $raw ) ? $raw['items'] : array();
		foreach ( $items as $item ) {
			if ( ! is_array( $item ) || ! is_string( $item['id'] ?? null ) || ! is_array( $item['label'] ?? null ) || ! is_string( $item['label']['en'] ?? null ) || ! is_string( $item['label']['de'] ?? null ) || ! is_array( $item['source'] ?? null ) || ! is_string( $item['source']['document_id'] ?? null ) || ! is_int( $item['source']['page'] ?? null ) || ( ! is_int( $item['quantity'] ?? null ) && ! is_float( $item['quantity'] ?? null ) ) || ! is_string( $item['unit'] ?? null ) || ! is_string( $item['role'] ?? null ) ) {
				echo '<p>' . esc_html__( 'The stored declarations have an unsupported format. They remain saved and unavailable for new releases.', 'linker-commerce' ) . '</p>';
				return;
			}
		}
		$items[] = array( 'id' => wp_generate_uuid4() );
		wp_nonce_field( PackageContents::META_KEY, self::NONCE );
		echo '<p>' . esc_html__( 'List only additional components supplied with one Woo sales unit. Each quantity needs a current associated document and its PDF page. Site cable runs and installation quantities are separate.', 'linker-commerce' ) . '</p>';
		foreach ( $items as $i => $item ) {
			$name = 'linker_package_contents[items][' . $i . ']';
			echo '<fieldset><legend>' . esc_html( $item['label']['en'] ?? __( 'New supplied component', 'linker-commerce' ) ) . '</legend>';
			$this->input( $name . '[id]', (string) $item['id'], 'hidden' );
			foreach ( array( 'en', 'de' ) as $lang ) {
				echo '<p><label>' . esc_html( 'en' === $lang ? __( 'Component name (EN)', 'linker-commerce' ) : __( 'Component name (DE)', 'linker-commerce' ) );
				$this->input( $name . '[label][' . $lang . ']', (string) ( $item['label'][ $lang ] ?? '' ), 'text' );
				echo '</label></p>';
			}
			echo '<p><label>' . esc_html__( 'Quantity per sales unit', 'linker-commerce' );
			$quantity = isset( $item['quantity'] ) ? self::decimal( (string) wp_json_encode( $item['quantity'] ) ) : '';
			$this->input( $name . '[quantity]', $quantity, 'text' );
			echo '</label> <label>' . esc_html__( 'Unit', 'linker-commerce' );
			$this->select(
				$name . '[unit]',
				(string) ( $item['unit'] ?? '' ),
				array(
					''      => __( 'Choose unit', 'linker-commerce' ),
					'piece' => __( 'Pieces', 'linker-commerce' ),
					'pair'  => __( 'Pairs', 'linker-commerce' ),
					'm'     => 'm',
				)
			);
			echo '</label></p><p><label>' . esc_html__( 'Component function', 'linker-commerce' );
			$this->select(
				$name . '[role]',
				(string) ( $item['role'] ?? 'other' ),
				array(
					'other'               => __( 'Other supplied component', 'linker-commerce' ),
					'meter'               => __( 'Meter', 'linker-commerce' ),
					'backup'              => __( 'Backup', 'linker-commerce' ),
					'parallel_controller' => __( 'Parallel controller', 'linker-commerce' ),
				)
			);
			echo '</label></p><p><label>' . esc_html__( 'Source document', 'linker-commerce' );
			$options = array( '' => __( 'Choose associated document', 'linker-commerce' ) );
			foreach ( $docs as $doc ) {
				$options[ $doc['document_id'] ] = $doc['title'] . ' · ' . basename( $doc['url'] );
			}
			$id = (string) ( $item['source']['document_id'] ?? '' );
			if ( '' !== $id && ! isset( $options[ $id ] ) ) {
				$options[ $id ] = __( 'Unavailable source', 'linker-commerce' ) . ' · ' . $id;
			}
			$this->select( $name . '[document_id]', $id, $options );
			echo '</label> <label>' . esc_html__( 'PDF page', 'linker-commerce' );
			$this->input( $name . '[page]', (string) ( $item['source']['page'] ?? '' ), 'text' );
			echo '</label></p><p><label><input type="checkbox" name="' . esc_attr( $name . '[confirm]' ) . '" value="1"> ' . esc_html__( 'I verified this declaration against the selected current document version.', 'linker-commerce' ) . '</label></p>';
			echo '<p><label><input type="checkbox" name="' . esc_attr( $name . '[remove]' ) . '" value="1"> ' . esc_html__( 'Remove component', 'linker-commerce' ) . '</label></p></fieldset>';
		}
		$this->input( 'linker_package_contents[complete]', '1', 'hidden' );
	}

	/**
	 * Native save; preserve the complete previous value on any refusal.
	 *
	 * @param int $id Product being saved.
	 */
	public function save( int $id ): void {
		if ( self::$saving || ! isset( $_POST[ self::NONCE ], $_POST['linker_package_contents'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST[ self::NONCE ] ) ), PackageContents::META_KEY ) || ! current_user_can( 'edit_post', $id ) || Publication::canonical_id( $id ) !== $id || wp_is_post_revision( $id ) || wp_is_post_autosave( $id ) ) {
			return;
		}
		try {
			$before = get_post_meta( $id, PackageContents::META_KEY, true );
			$after  = self::prepare( $id, wp_unslash( $_POST['linker_package_contents'] ), $before, Publication::manifest() ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- prepare validates every scalar and binds current evidence before persistence.
			if ( $after === $before || ( array() === $after['items'] && ( '' === $before || array() === $before ) ) ) {
				return;
			}
			$product = wc_get_product( $id );
			if ( ! $product instanceof \WC_Product ) {
				return;
			}
			if ( array() === $after['items'] ) {
				$product->delete_meta_data( PackageContents::META_KEY );
			} else {
				$product->update_meta_data( PackageContents::META_KEY, $after );
			}
			self::$saving = true;
			try {
				$product->save();
			} finally {
				self::$saving = false;
			}
		} catch ( \RuntimeException $error ) {
			update_user_meta( get_current_user_id(), self::NOTICE, __( 'Package contents were preserved: ', 'linker-commerce' ) . $error->getMessage() );
		}
	}

	/**
	 * Parse only complete native submissions; document changes require confirmation.
	 *
	 * @param  int                 $owner    Canonical product.
	 * @param  mixed               $draft    Posted native form.
	 * @param  mixed               $before   Current raw metadata.
	 * @param  array<string,mixed> $manifest Current authority assembly.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When inputs are incomplete or unconfirmed.
	 */
	public static function prepare( int $owner, mixed $draft, mixed $before, array $manifest ): array {
		if ( ! is_array( $draft ) || '1' !== ( $draft['complete'] ?? null ) || ! is_array( $draft['items'] ?? null ) || ( '' !== $before && array() !== $before && ( ! is_array( $before ) || 1 !== ( $before['schema_version'] ?? null ) || ! is_array( $before['items'] ?? null ) ) ) ) {
			throw new \RuntimeException( __( 'The submitted package contents are incomplete.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		$previous = is_array( $before ) ? array_column( $before['items'], null, 'id' ) : array();
		$seen     = array();
		$items    = array();
		foreach ( $draft['items'] as $raw ) {
			if ( ! is_array( $raw ) || ! is_string( $raw['id'] ?? null ) || '' === trim( $raw['id'] ) || isset( $seen[ $raw['id'] ] ) ) {
				throw new \RuntimeException( __( 'Package item identities must be distinct.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
			}
			$id          = $raw['id'];
			$seen[ $id ] = true;
			if ( ! empty( $raw['remove'] ) ) {
				continue;
			}
			$en = sanitize_text_field( (string) ( $raw['label']['en'] ?? '' ) );
			$de = sanitize_text_field( (string) ( $raw['label']['de'] ?? '' ) );
			if ( '' === $en && '' === $de && '' === ( $raw['quantity'] ?? '' ) && ! isset( $previous[ $id ] ) ) {
				continue;
			}
			if ( ! is_string( $raw['quantity'] ?? null ) || 1 !== preg_match( '/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/D', $raw['quantity'] ) || ! is_string( $raw['page'] ?? null ) || 1 !== preg_match( '/^[1-9][0-9]*$/D', $raw['page'] ) || strlen( $raw['page'] ) > 16 ) {
				throw new \RuntimeException( __( 'Use a decimal point for quantities. Enter the PDF page number as a positive whole number.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
			}
			$row = array(
				'id'       => $id,
				'label'    => array(
					'en' => $en,
					'de' => $de,
				),
				'quantity' => self::quantity( $raw['quantity'], (string) ( $raw['unit'] ?? '' ) ),
				'unit'     => (string) ( $raw['unit'] ?? '' ),
				'role'     => (string) ( $raw['role'] ?? 'other' ),
				'source'   => array(
					'document_id' => (string) ( $raw['document_id'] ?? '' ),
					'page'        => (int) $raw['page'],
				),
			);
			$old = $previous[ $id ] ?? null;
			if ( is_array( $old ) ) {
				$editable           = $old;
				$editable['source'] = array(
					'document_id' => $old['source']['document_id'],
					'page'        => $old['source']['page'],
				);
				if ( Publication::revision( $editable ) === Publication::revision( $row ) && empty( $raw['confirm'] ) ) {
					$items[] = $old;
					continue;
				}
			}
			if ( '1' !== ( $raw['confirm'] ?? null ) ) {
				throw new \RuntimeException( __( 'Confirm each new or changed component against its current source.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
			}
			$items[] = PackageContents::bind( $owner, $row, $manifest, true );
		}
		if ( array() !== array_diff_key( $previous, $seen ) ) {
			throw new \RuntimeException( __( 'The submitted package contents are incomplete.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		return array(
			'schema_version' => 1,
			'items'          => $items,
		);
	}

	/**
	 * Native user-scoped save error.
	 */
	public function notice(): void {
		$error = get_user_meta( get_current_user_id(), self::NOTICE, true );
		if ( is_string( $error ) && '' !== $error ) {
			delete_user_meta( get_current_user_id(), self::NOTICE );
			echo '<div class="notice notice-error"><p>' . esc_html( $error ) . '</p></div>';
		}
	}

	/**
	 * Native control only.
	 *
	 * @param string $name  Name.
	 * @param string $value Value.
	 * @param string $type  HTML input type.
	 */
	private function input( string $name, string $value, string $type ): void {
		echo '<input type="' . esc_attr( $type ) . '" name="' . esc_attr( $name ) . '" value="' . esc_attr( $value ) . '">';
	}

	/**
	 * Native control only.
	 *
	 * @param string               $name    Name.
	 * @param string               $value   Value.
	 * @param array<string,string> $options Choices.
	 */
	private function select( string $name, string $value, array $options ): void {
		echo '<select name="' . esc_attr( $name ) . '">';
		foreach ( $options as $key => $label ) {
			echo '<option value="' . esc_attr( $key ) . '"' . selected( $value, $key, false ) . '>' . esc_html( $label ) . '</option>';
		}
		echo '</select>';
	}

	/**
	 * Validate the original decimal before IEEE-754 conversion can round it.
	 *
	 * @param string $raw Already syntax-checked decimal candidate.
	 * @param string $unit Declared physical unit.
	 * @return int|float
	 * @throws \RuntimeException When the original value violates the count/transport boundary.
	 */
	private static function quantity( string $raw, string $unit ): int|float {
		$parts    = explode( '.', $raw, 2 );
		$whole    = $parts[0];
		$fraction = rtrim( $parts[1] ?? '', '0' );
		// Shared exact-integer browser boundary, compared before conversion.
		$maximum = '9007199254740991';
		if ( strlen( $whole ) > strlen( $maximum ) || ( strlen( $whole ) === strlen( $maximum ) && strcmp( $whole, $maximum ) > 0 ) || ( $whole === $maximum && '' !== $fraction ) || ( 'm' !== $unit && '' !== $fraction ) ) {
			throw new \RuntimeException( __( 'Package quantities need a positive value, an explicit unit and a whole count for pieces or pairs.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		if ( 'm' !== $unit ) {
			return (int) $whole;
		}
		$value = (float) $raw;
		if ( ! is_finite( $value ) || $value <= 0 || self::decimal( $raw ) !== self::decimal( (string) wp_json_encode( $value ) ) ) {
			throw new \RuntimeException( __( 'The quantity cannot be represented without rounding. Check the value and unit.', 'linker-commerce' ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- Plain errors are escaped by the native notice renderer.
		}
		return $value;
	}

	/**
	 * Normalize raw and JSON positive decimals for exact round-trip comparison.
	 *
	 * @param string $value Decimal or native JSON float spelling.
	 * @return string
	 */
	private static function decimal( string $value ): string {
		$exponent = explode( 'e', strtolower( $value ), 2 );
		$parts    = explode( '.', $exponent[0], 2 );
		$digits   = $parts[0] . ( $parts[1] ?? '' );
		$point    = strlen( $parts[0] ) + (int) ( $exponent[1] ?? 0 );
		if ( $point <= 0 ) {
			$expanded = '0.' . str_repeat( '0', -$point ) . $digits;
		} elseif ( $point >= strlen( $digits ) ) {
			$expanded = $digits . str_repeat( '0', $point - strlen( $digits ) );
		} else {
			$expanded = substr( $digits, 0, $point ) . '.' . substr( $digits, $point );
		}
		return str_contains( $expanded, '.' ) ? rtrim( rtrim( $expanded, '0' ), '.' ) : $expanded;
	}
}
