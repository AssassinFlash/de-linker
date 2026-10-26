<?php
/**
 * Manufacturer declarations in the normal Woo product editor.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

use Linker\Commerce\Products\Publication;

/** Uses the product's native documents, capabilities, nonce and Woo CRUD save. */
final class CompatibilityEditor {

	private const NONCE  = 'linker_compatibility_claims_nonce';
	private const ACTION = 'linker_compatibility_claims';
	private const NOTICE = '_linker_compatibility_editor_error';
	/** Guard native CRUD's nested save_post callback.
	 *
	 * @var bool
	 */
	private static bool $saving = false;

	/** Register ordinary product maintenance. */
	public function register(): void {
		add_action( 'add_meta_boxes', array( $this, 'box' ) );
		add_action( 'save_post_product', array( $this, 'save' ), 30 );
		add_action( 'admin_notices', array( $this, 'notice' ) );
	}

	/** Add to the existing standard Woo edit screen. */
	public function box(): void {
		add_meta_box( 'linker-compatibility-claims', __( 'Manufacturer compatibility declarations', 'linker-commerce' ), array( $this, 'render' ), 'product', 'normal', 'default' );
	}

	/**
	 * Native declaration data.
	 *
	 * @param \WP_Post $post Native product being edited.
	 */
	public function render( \WP_Post $post ): void {
		$id = Publication::canonical_id( $post->ID );
		if ( $id !== $post->ID ) {
			echo '<p>' . esc_html( __( 'Maintain these declarations on the English source product.', 'linker-commerce' ) ) . '</p>';
			return;
		}
		$stored = get_post_meta( $id, CompatibilityClaims::META_KEY, true );
		if ( '' !== $stored && array() !== $stored && ! CompatibilityClaims::shape( $stored ) ) {
			echo '<p>' . esc_html( __( 'The stored declarations have an unsupported format. They remain saved and unavailable for new releases.', 'linker-commerce' ) ) . '</p>';
			return;
		}
		$manifest = Publication::manifest();
		wp_nonce_field( self::ACTION, self::NONCE );
		echo '<p>' . esc_html( __( 'Choose Woo products and their associated hosted documents. Conditions remain in English and German. Confirm the evidence explicitly when changing a declaration or accepting a new document version.', 'linker-commerce' ) ) . '</p>';
		foreach ( array( 'pairs', 'requirements' ) as $kind ) {
			echo '<h3>' . esc_html( 'pairs' === $kind ? __( 'Battery pairings', 'linker-commerce' ) : __( 'Required components', 'linker-commerce' ) ) . '</h3>';
			$rows   = is_array( $stored ) ? $stored[ $kind ] : array();
			$rows[] = array( 'id' => wp_generate_uuid4() );
			foreach ( $rows as $index => $row ) {
				$this->row( $kind, $index, $row, $manifest );
			}
		}
		$this->input( 'linker_compatibility[complete]', '1', 'hidden' );
	}

	/**
	 * Native declaration data.
	 *
	 * @param string              $kind Declaration group.
	 * @param int                 $index Native repeated row index.
	 * @param array<string,mixed> $row Current declaration or blank row.
	 * @param array<string,mixed> $manifest Same current source shown by the editor.
	 */
	private function row( string $kind, int $index, array $row, array $manifest ): void {
		$name = 'linker_compatibility[' . $kind . '][' . $index . ']';
		echo '<details><summary>' . esc_html( (string) ( $row['id'] ?? '' ) ) . '</summary><p>';
		$this->input( $name . '[id]', (string) $row['id'], 'hidden' );
		if ( 'pairs' === $kind ) {
			$this->product( $name . '[battery_product_id]', (int) ( $row['battery_product_id'] ?? 0 ), $manifest['products'], __( 'Battery product', 'linker-commerce' ) );
			$this->select(
				$name . '[verdict]',
				(string) ( $row['verdict'] ?? '' ),
				array(
					''                        => __( 'Choose a verdict', 'linker-commerce' ),
					'released'                => __( 'Released', 'linker-commerce' ),
					'released_with_accessory' => __( 'Released with required accessory', 'linker-commerce' ),
					'not_released'            => __( 'No manufacturer release', 'linker-commerce' ),
				)
			);
			foreach ( array( 'min', 'max' ) as $bound ) {
				echo '<label>' . esc_html( 'min' === $bound ? __( 'Modules per stack: minimum', 'linker-commerce' ) : __( 'Modules per stack: maximum', 'linker-commerce' ) );
				$this->input( $name . '[modules][' . $bound . ']', (string) ( $row['modules'][ $bound ] ?? '' ), 'number' );
				echo '</label> ';
			}
		} else {
			$this->select(
				$name . '[kind]',
				(string) ( $row['kind'] ?? '' ),
				array(
					''                    => __( 'Choose a requirement', 'linker-commerce' ),
					'meter'               => __( 'Meter', 'linker-commerce' ),
					'backup'              => __( 'Backup', 'linker-commerce' ),
					'parallel_controller' => __( 'Parallel controller', 'linker-commerce' ),
				)
			);
			$this->select(
				$name . '[included]',
				isset( $row['included'] ) ? ( $row['included'] ? '1' : '0' ) : '',
				array(
					''  => __( 'Included status', 'linker-commerce' ),
					'1' => __( 'Included', 'linker-commerce' ),
					'0' => __( 'Separate required product', 'linker-commerce' ),
				)
			);
			foreach ( array( 'phase', 'max_units' ) as $field ) {
				echo '<label>' . esc_html( 'phase' === $field ? __( 'Phases (1 or 3)', 'linker-commerce' ) : __( 'Maximum converter units', 'linker-commerce' ) );
				$this->input( $name . '[' . $field . ']', (string) ( $row[ $field ] ?? '' ), 'number' );
				echo '</label> ';
			}
			echo '</p><p>';
			$this->scope_fields( $name, $row['applicability'] ?? array() );
		}
		echo '</p>';
		if ( ! empty( $row['unresolved'] ) ) {
			echo '<p>' . esc_html( implode( ' ', $row['unresolved'] ) ) . '</p>';
		}
		$conditions   = $row['conditions'] ?? array();
		$conditions[] = array();
		foreach ( $conditions as $i => $condition ) {
			foreach ( array( 'en', 'de' ) as $lang ) {
				echo '<p><label>' . esc_html( 'en' === $lang ? 'Condition (EN)' : 'Bedingung (DE)' ) . '<br><textarea class="large-text" rows="3" name="' . esc_attr( $name . '[conditions][' . $i . '][' . $lang . ']' ) . '">' . esc_textarea( (string) ( $condition[ $lang ] ?? '' ) ) . '</textarea></label></p>';
			}
		}
		$parts   = $row['accessories'] ?? array();
		$parts[] = array();
		foreach ( $parts as $i => $part ) {
			echo '<p>';
			$this->product( $name . '[accessories][' . $i . '][product_id]', (int) ( $part['product_id'] ?? 0 ), $manifest['products'], __( 'Accessory', 'linker-commerce' ) );
			$this->input( $name . '[accessories][' . $i . '][quantity]', (string) ( $part['quantity'] ?? '' ), 'number' );
			$this->select(
				$name . '[accessories][' . $i . '][per]',
				(string) ( $part['per'] ?? '' ),
				array(
					''       => __( 'Quantity basis', 'linker-commerce' ),
					'system' => __( 'Per system', 'linker-commerce' ),
					'stack'  => __( 'Per stack', 'linker-commerce' ),
					'unit'   => __( 'Per converter unit', 'linker-commerce' ),
				)
			);
			echo '</p>';
		}
		$documents   = $row['documents'] ?? array();
		$documents[] = array();
		$options     = array( '' => __( 'Choose associated document', 'linker-commerce' ) );
		foreach ( $manifest['documents'] as $doc ) {
			$options[ $doc['document_id'] ] = $doc['title'] . ' · ' . basename( $doc['url'] );
		}
		foreach ( $documents as $i => $doc ) {
			$id = $doc['document_id'] ?? ( ! empty( $doc['url'] ) ? DocumentFiles::id( $doc['url'] ) : '' );
			if ( '' !== $id && ! isset( $options[ $id ] ) ) {
				$options[ $id ] = __( 'Unavailable source', 'linker-commerce' ) . ' · ' . $id;
			}
			echo '<p>';
			$this->select( $name . '[documents][' . $i . '][document_id]', $id, $options );
			$this->input( $name . '[documents][' . $i . '][page]', (string) ( $doc['page'] ?? '' ), 'number' );
			echo '</p>';
		}
		echo '<p><label><input type="checkbox" name="' . esc_attr( $name . '[confirm]' ) . '" value="1"> ' . esc_html( __( 'I verified this declaration against the selected current document version.', 'linker-commerce' ) ) . '</label></p>';
		echo '<p><label><input type="checkbox" name="' . esc_attr( $name . '[remove]' ) . '" value="1"> ' . esc_html( __( 'Remove declaration', 'linker-commerce' ) ) . '</label></p></details>';
	}

	/**
	 * Native declaration data.
	 *
	 * @param int $post_id Native saved product ID.
	 * @throws \RuntimeException Caught to preserve the complete prior metadata.
	 */
	public function save( int $post_id ): void {
		$id = Publication::canonical_id( $post_id );
		if ( self::$saving || ! isset( $_POST[ self::NONCE ], $_POST['linker_compatibility'] ) || ! wp_verify_nonce( sanitize_text_field( wp_unslash( $_POST[ self::NONCE ] ) ), self::ACTION ) || ! current_user_can( 'edit_post', $post_id ) || ! current_user_can( 'edit_post', $id ) || $id !== $post_id || wp_is_post_revision( $id ) || wp_is_post_autosave( $id ) ) {
			return;
		}
		try {
			$draft  = wp_unslash( $_POST['linker_compatibility'] ); // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Each typed declaration field is parsed below; no raw input reaches a writer.
			$before = get_post_meta( $id, CompatibilityClaims::META_KEY, true );
			$after  = self::prepare( $id, $draft, $before, Publication::manifest() );
			if ( $after === $before || ( array() === $after['pairs'] && array() === $after['requirements'] && '' === $before ) ) {
				return;
			}
			$product = wc_get_product( $id );
			if ( ! $product ) {
				throw new \RuntimeException( 'The canonical Woo product is unavailable.' );
			}
			$product->update_meta_data( CompatibilityClaims::META_KEY, $after );
			self::$saving = true;
			try {
				$product->save();
			} finally {
				self::$saving = false;
			}
		} catch ( \RuntimeException $error ) {
			update_user_meta( get_current_user_id(), self::NOTICE, __( 'Compatibility declarations were preserved: ', 'linker-commerce' ) . $error->getMessage() );
		}
	}

	/**
	 * Preserve unchanged document bindings; bind only an explicitly confirmed row.
	 *
	 * @param int                 $owner Canonical product.
	 * @param mixed               $draft Native repeated form fields.
	 * @param mixed               $before Current metadata.
	 * @param array<string,mixed> $manifest Current authority.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When any row is invalid; the complete prior value stays.
	 */
	public static function prepare( int $owner, mixed $draft, mixed $before, array $manifest ): array {
		if ( ! is_array( $draft ) || '1' !== ( $draft['complete'] ?? null ) || ( '' !== $before && array() !== $before && ! CompatibilityClaims::shape( $before ) ) ) {
			throw new \RuntimeException( 'Unsupported declaration format.' );
		}
		$result = array(
			'schema_version' => 1,
			'pairs'          => array(),
			'requirements'   => array(),
		);
		foreach ( array( 'pairs', 'requirements' ) as $kind ) {
			$previous = is_array( $before ) ? array_column( $before[ $kind ], null, 'id' ) : array();
			$seen     = array();
			foreach ( (array) ( $draft[ $kind ] ?? array() ) as $raw ) {
				if ( ! is_array( $raw ) ) {
					throw new \RuntimeException( 'A declaration row must be structured.' );
				}
				$id = (string) ( $raw['id'] ?? '' );
				if ( isset( $seen[ $id ] ) ) {
					throw new \RuntimeException( 'Declaration identities must be unique.' );
				}
				$seen[ $id ] = true;
				if ( ! empty( $raw['remove'] ) ) {
					continue;
				}
				if ( 'pairs' === $kind ? empty( $raw['battery_product_id'] ) : empty( $raw['kind'] ) ) {
					if ( isset( $previous[ (string) ( $raw['id'] ?? '' ) ] ) ) {
						throw new \RuntimeException( 'Use Remove declaration to remove an existing row.' );
					}
					continue;
				}
				$row = self::parse( $raw, $kind );
				$old = $previous[ $row['id'] ] ?? null;
				if ( is_array( $old ) && Publication::revision( self::editable( $old ) ) === Publication::revision( self::editable( $row ) ) && empty( $raw['confirm'] ) ) {
					$result[ $kind ][] = $old;
					continue;
				}
				if ( '1' !== ( $raw['confirm'] ?? null ) ) {
					throw new \RuntimeException( 'Confirm each new or changed declaration against its current evidence.' );
				}
				$result[ $kind ][] = CompatibilityClaims::bind_row( $owner, $row, $kind, $manifest, true );
			}
			if ( array() !== array_diff_key( $previous, $seen ) ) {
				throw new \RuntimeException( 'The submitted form is incomplete; all declarations were preserved.' );
			}
		}
		return $result;
	}

	/**
	 * Native declaration data.
	 *
	 * @param array<string,mixed> $raw Form row.
	 * @param string              $kind Group.
	 * @return array<string,mixed>
	 * @throws \RuntimeException When a numeric declaration field is invalid.
	 */
	private static function parse( array $raw, string $kind ): array {
		$row = array(
			'id'          => sanitize_text_field( (string) ( $raw['id'] ?? '' ) ),
			'conditions'  => array(),
			'documents'   => array(),
			'accessories' => array(),
		);
		if ( 'pairs' === $kind ) {
			$row['battery_product_id'] = self::integer( $raw['battery_product_id'] );
			$row['verdict']            = (string) ( $raw['verdict'] ?? '' );
			if ( '' !== ( $raw['modules']['min'] ?? '' ) || '' !== ( $raw['modules']['max'] ?? '' ) ) {
				$row['modules'] = array(
					'min' => self::integer( $raw['modules']['min'] ?? '' ),
					'max' => self::integer( $raw['modules']['max'] ?? '' ),
				);
			}
		} else {
			$row['kind']     = (string) $raw['kind'];
			$row['included'] = '1' === ( $raw['included'] ?? '' ) ? true : ( '0' === ( $raw['included'] ?? '' ) ? false : null );
			foreach ( array( 'phase', 'max_units' ) as $key ) {
				if ( '' !== ( $raw[ $key ] ?? '' ) ) {
					$row[ $key ] = self::integer( $raw[ $key ] );
				}
			}
			$scope = array_filter( (array) ( $raw['applicability'] ?? array() ), static fn( mixed $value ): bool => '' !== $value );
			if ( array() !== $scope ) {
				$row['applicability'] = $scope;
			}
		}
		foreach ( (array) ( $raw['conditions'] ?? array() ) as $condition ) {
			$en = sanitize_textarea_field( (string) ( $condition['en'] ?? '' ) );
			$de = sanitize_textarea_field( (string) ( $condition['de'] ?? '' ) );
			if ( '' !== $en || '' !== $de ) {
				$row['conditions'][] = array(
					'en' => $en,
					'de' => $de,
				);
			}
		}
		foreach ( (array) ( $raw['accessories'] ?? array() ) as $part ) {
			if ( ! empty( $part['product_id'] ) ) {
				$row['accessories'][] = array(
					'product_id' => self::integer( $part['product_id'] ),
					'quantity'   => self::integer( $part['quantity'] ?? '' ),
					'per'        => (string) ( $part['per'] ?? '' ),
				);
			}
		}
		foreach ( (array) ( $raw['documents'] ?? array() ) as $doc ) {
			if ( ! empty( $doc['document_id'] ) ) {
				$reference = array( 'document_id' => (string) $doc['document_id'] );
				if ( '' !== ( $doc['page'] ?? '' ) ) {
					$reference['page'] = self::integer( $doc['page'] );
				}
				$row['documents'][] = $reference;
			}
		}
		return $row;
	}

	/**
	 * Native declaration data.
	 *
	 * @param array<string,mixed> $row Bound or editable row.
	 * @return array<string,mixed>
	 */
	private static function editable( array $row ): array {
		unset( $row['migration_source'], $row['unresolved'] );
		$row['documents'] = array_map(
			static fn( array $doc ): array => array_filter(
				array(
					'document_id' => $doc['document_id'] ?? DocumentFiles::id( (string) ( $doc['url'] ?? '' ) ),
					'page'        => $doc['page'] ?? null,
				),
				static fn( mixed $value ): bool => null !== $value
			),
			$row['documents']
		);
		return $row;
	}

	/**
	 * Native declaration data.
	 *
	 * @param mixed $value Native form integer; decimals never truncate into facts.
	 * @throws \RuntimeException When the input is not a positive whole number.
	 */
	private static function integer( mixed $value ): int {
		if ( ( ! is_string( $value ) && ! is_int( $value ) ) || 1 !== preg_match( '/^[1-9][0-9]*$/D', (string) $value ) || strlen( (string) $value ) > 16 || (int) $value > 9007199254740991 ) {
			throw new \RuntimeException( 'A positive whole number is required.' );
		}
		return (int) $value;
	}

	/**
	 * Source applicability uses native controls, with empty fields kept unknown.
	 *
	 * @param string              $name Row field prefix.
	 * @param array<string,mixed> $scope Current maintained scope.
	 */
	private function scope_fields( string $name, array $scope ): void {
		$options = array(
			'operating_mode'  => array(
				''               => __( 'Operating mode not specified', 'linker-commerce' ),
				'grid_connected' => __( 'Grid-connected', 'linker-commerce' ),
				'backup'         => __( 'Backup', 'linker-commerce' ),
			),
			'topology'        => array(
				''                 => __( 'Topology not specified', 'linker-commerce' ),
				'single_converter' => __( 'Single converter', 'linker-commerce' ),
				'parallel_group'   => __( 'Parallel group', 'linker-commerce' ),
			),
			'control_network' => array(
				''      => __( 'No network restriction declared', 'linker-commerce' ),
				'lan'   => 'LAN',
				'rs485' => 'RS485',
			),
		);
		foreach ( $options as $key => $choices ) {
			$this->select( $name . '[applicability][' . $key . ']', (string) ( $scope[ $key ] ?? '' ), $choices );
		}
	}

	/** Show a native, user-scoped save refusal. */
	public function notice(): void {
		$error = get_user_meta( get_current_user_id(), self::NOTICE, true );
		if ( is_string( $error ) && '' !== $error ) {
			delete_user_meta( get_current_user_id(), self::NOTICE );
			echo '<div class="notice notice-error"><p>' . esc_html( $error ) . '</p></div>';
		}
	}

	/**
	 * Native declaration data.
	 *
	 * @param string $name Native input name.
	 * @param string $value Stored value.
	 * @param string $type Native input type.
	 */
	private function input( string $name, string $value, string $type ): void {
		echo '<input type="' . esc_attr( $type ) . '" name="' . esc_attr( $name ) . '" value="' . esc_attr( $value ) . '"' . ( 'number' === $type ? ' min="1" step="1"' : '' ) . '>';
	}

	/**
	 * Native declaration data.
	 *
	 * @param string                   $name Field.
	 * @param string                   $value Current selection.
	 * @param array<string|int,string> $options Options.
	 */
	private function select( string $name, string $value, array $options ): void {
		echo '<select name="' . esc_attr( $name ) . '">';
		foreach ( $options as $key => $label ) {
			echo '<option value="' . esc_attr( (string) $key ) . '"' . selected( (string) $key, $value, false ) . '>' . esc_html( $label ) . '</option>';
		}
		echo '</select> ';
	}

	/**
	 * Native declaration data.
	 *
	 * @param string                    $name Field.
	 * @param int                       $id Canonical selection.
	 * @param list<array<string,mixed>> $products Current Woo products.
	 * @param string                    $label Native label.
	 */
	private function product( string $name, int $id, array $products, string $label ): void {
		$options = array( '' => $label );
		foreach ( $products as $product ) {
			$options[ $product['product_id'] ] = $product['model'] . ' · #' . $product['product_id'];
		}
		if ( $id > 0 && ! isset( $options[ $id ] ) ) {
			$options[ $id ] = __( 'Unavailable product', 'linker-commerce' ) . ' · #' . $id;
		}
		$this->select( $name, (string) $id, $options );
	}
}
