<?php
/**
 * Frozen project context follows native Woo lines into an inquiry.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Planning;

use Linker\Commerce\Products\Publication;
use WC_Order;
use WC_Order_Item_Product;
use WP_Error;

/** A copied cart field is only a reference to server-owned session context. */
final class Context {
	public const META            = '_linker_planning_projects';
	public const NOTES_META      = '_linker_planning_notes';
	public const INCLUDE_FIELD   = 'linker_include_project_notes';
	public const PRESENT_FIELD   = 'linker_project_notes_present';
	public const REVISIONS_FIELD = 'linker_project_note_revisions';
	/** HPOS orders_meta.meta_value is TEXT: wpdb reports a 65,535-byte limit. */
	private const MAX_META_BYTES = 65535;
	/** Matches Submission::MAX_MESSAGE. */
	private const MAX_NOTE_LENGTH = 5000;

	/**
	 * Active inquiry form submission fields, scoped to the current request.
	 *
	 * @var array<string,mixed>|null
	 */
	private static ?array $submission_post = null;

	/**
	 * Exact note revisions consumed by the most recent committed inquiry.
	 *
	 * @var array<string,string>|null
	 */
	private static ?array $consumed_revisions = null;

	/**
	 * Bind posted inquiry form fields around preflight and order creation.
	 *
	 * @template T
	 * @param array<string,mixed> $post     Unslashed POST fields.
	 * @param callable():T        $callback Scoped operation.
	 * @return T
	 */
	public static function with_submission( array $post, callable $callback ): mixed {
		$previous              = self::$submission_post;
		self::$submission_post = $post;
		try {
			return $callback();
		} finally {
			self::$submission_post = $previous;
		}
	}

	/**
	 * Normalize posted project-note inclusion state for Business payload hashing.
	 *
	 * @param array<string,mixed> $post Unslashed POST fields.
	 * @return array<string,mixed>
	 */
	public static function submission_fingerprint( array $post ): array {
		$included  = '1' === ( $post[ self::INCLUDE_FIELD ] ?? '' );
		$revisions = array();
		if ( is_array( $post[ self::REVISIONS_FIELD ] ?? null ) ) {
			foreach ( $post[ self::REVISIONS_FIELD ] as $id => $rev ) {
				if ( is_string( $id ) && is_string( $rev ) ) {
					$revisions[ $id ] = $rev;
				}
			}
			ksort( $revisions );
		}
		return array(
			'included'  => $included,
			'revisions' => $revisions,
		);
	}

	/**
	 * Resolve only contexts referenced by live native Woo lines.
	 *
	 * @return array<string,array<string,mixed>>
	 */
	public static function active(): array {
		$result = array();
		$stored = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		foreach ( WC()->cart->get_cart() as $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( is_string( $id ) && ! isset( $result[ $id ] ) && isset( $stored[ $id ] ) && self::valid( $stored[ $id ], $id ) ) {
				$result[ $id ] = $stored[ $id ];
			}
		}
		return $result;
	}

	/**
	 * Reports attached to the native draft independently of cart items.
	 *
	 * @return array<string,array<string,mixed>>
	 */
	public static function report_only_contexts(): array {
		$stored = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		return array_filter(
			$stored,
			static fn ( $handoff, $id ): bool => is_string( $id ) && self::valid( $handoff, $id ) && DraftTransfer::report_only( $handoff['snapshot'] ),
			ARRAY_FILTER_USE_BOTH
		);
	}

	/**
	 * Resolve valid project notes in the current Woo session, including notes
	 * whose product lines were subsequently removed from the cart.
	 *
	 * @return array<string,array{handoff_id:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	public static function session_notes(): array {
		// WC()->session is null outside a request that loaded the native cart.
		if ( ! function_exists( 'WC' ) || null === WC()->session ) {
			return array();
		}
		$stored     = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		$by_project = array();
		foreach ( $stored as $id => $handoff ) {
			if ( ! is_string( $id ) || ! self::valid( $handoff, $id ) ) {
				continue;
			}
			$snapshot    = $handoff['snapshot'];
			$note        = self::project_note( $snapshot );
			$report_only = DraftTransfer::report_only( $snapshot );
			if ( '' === $note && ! $report_only ) {
				continue;
			}
			$project_id                = (string) $snapshot['project_id'];
			$by_project[ $project_id ] = array(
				'handoff_id'    => $id,
				'project_id'    => $project_id,
				'title'         => (string) $snapshot['title'],
				'revision'      => (int) $snapshot['revision'],
				'note_revision' => self::note_revision( $handoff ),
				'text'          => $note,
				...( $report_only ? array( 'report_only' => true ) : array() ),
			);
		}
		$result = array();
		foreach ( $by_project as $entry ) {
			$result[ $entry['handoff_id'] ] = $entry;
		}
		return $result;
	}

	/**
	 * Whether the current inquiry submission includes at least one project note.
	 */
	public static function has_included_notes(): bool {
		return array() !== self::included_notes();
	}

	/** Recheck current source permission and project-note revision consistency before consuming an inquiry attempt. */
	public static function preflight(): ?WP_Error {
		$active = self::active();
		foreach ( WC()->cart->get_cart() as $line ) {
			$id = $line[ DraftTransfer::LINE_META ] ?? null;
			if ( null !== $id && ( ! is_string( $id ) || ! isset( $active[ $id ] ) ) ) {
				return new WP_Error( 'planning_context_unavailable', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ), array( 'status' => 409 ) );
			}
		}
		foreach ( array_intersect_key( self::report_only_contexts(), self::included_notes() ) + $active as $handoff ) {
			$error = DraftTransfer::publication_error( $handoff['snapshot'] );
			if ( $error instanceof WP_Error ) {
				return $error;
			}
		}
		$note_error = self::preflight_notes();
		if ( $note_error instanceof WP_Error ) {
			return $note_error;
		}
		return null;
	}

	/**
	 * Render the inquiry form's project-notes review and inclusion section.
	 *
	 * @param array<string,mixed> $previous Consumed flash fields after a failed POST.
	 */
	public static function inquiry_notes_section( array $previous = array() ): string {
		$notes = self::session_notes();
		if ( array() === $notes ) {
			return '';
		}
		$included      = ! ( isset( $previous[ self::PRESENT_FIELD ] ) && '1' === $previous[ self::PRESENT_FIELD ] && '1' !== ( $previous[ self::INCLUDE_FIELD ] ?? '' ) );
		$has_report    = array() !== array_filter( $notes, static fn ( array $note ): bool => ! empty( $note['report_only'] ) );
		$html          = '<fieldset class="linker-inquiry-project-notes">';
		$html         .= '<legend>' . ( $has_report ? esc_html__( 'Planning report', 'linker-commerce' ) : esc_html__( 'Your project note', 'linker-commerce' ) ) . '</legend>';
		$html         .= '<input type="hidden" name="' . esc_attr( self::PRESENT_FIELD ) . '" value="1" />';
		$html         .= '<label class="linker-form-consent"><input type="checkbox" name="' . esc_attr( self::INCLUDE_FIELD ) . '" value="1"' . ( $included ? ' checked' : '' ) . ' /><span>' . ( $has_report ? esc_html__( 'Include planning reports and project notes with this inquiry', 'linker-commerce' ) : esc_html__( 'Include project notes with this inquiry', 'linker-commerce' ) ) . '</span></label>';
		$has_note_text = false;
		foreach ( $notes as $id => $note ) {
			$has_note_text = $has_note_text || '' !== $note['text'];
			$html         .= '<input type="hidden" name="' . esc_attr( self::REVISIONS_FIELD . '[' . $id . ']' ) . '" value="' . esc_attr( $note['note_revision'] ) . '" />';
			$html         .= '<div class="linker-inquiry-project-note"><p><strong>' . esc_html( self::label( $note ) ) . '</strong></p><p>' . nl2br( esc_html( $note['text'] ) ) . '</p></div>';
		}
		if ( $has_note_text ) {
			$html .= '<p class="linker-form-note">' . esc_html__( 'This note is not used in the calculation.', 'linker-commerce' ) . '</p>';
		}
		$html .= '</fieldset>';
		return $html;
	}

	/**
	 * Preserve the reference through native cart-to-order line creation.
	 *
	 * @param WC_Order_Item_Product $item Native order line.
	 * @param string                $key Native cart key.
	 * @param array<string,mixed>   $values Native cart line.
	 */
	public function line( WC_Order_Item_Product $item, string $key, array $values ): void {
		unset( $key );
		$id     = $values[ DraftTransfer::LINE_META ] ?? null;
		$active = is_string( $id ) ? self::session_context( $id ) : null;
		if ( null !== $active ) {
			$item->add_meta_data( DraftTransfer::LINE_META, $id, true );
		}
	}

	/**
	 * Persist original planning quantities and reviewed project notes alongside the inquiry.
	 *
	 * @param WC_Order $order Native inquiry, before assessment/mail preparation.
	 * @throws \RuntimeException Frozen native context cannot be encoded.
	 */
	public function capture( WC_Order $order ): void {
		$active = array();
		foreach ( $order->get_items() as $item ) {
			if ( ! $item instanceof WC_Order_Item_Product ) {
				continue;
			}
			$id = $item->get_meta( DraftTransfer::LINE_META );
			if ( '' === $id ) {
				continue;
			}
			$handoff = is_string( $id ) ? self::session_context( $id ) : null;
			if ( null === $handoff ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$active[ $id ] = $handoff;
		}
		$contexts = array();
		foreach ( $active as $id => $handoff ) {
			$actual = array();
			foreach ( $order->get_items() as $item ) {
				if ( $item instanceof WC_Order_Item_Product && $item->get_meta( DraftTransfer::LINE_META ) === $id ) {
					$product            = Publication::canonical_id( $item->get_product_id() );
					$actual[ $product ] = ( $actual[ $product ] ?? 0 ) + $item->get_quantity();
				}
			}
			if ( array() === $actual ) {
				continue;
			}
			$planned = array();
			foreach ( $handoff['snapshot']['items'] as $item ) {
				$planned[ $item['product_id'] ] = ( $planned[ $item['product_id'] ] ?? 0 ) + $item['quantity'];
			}
			$contexts[ $id ] = array(
				'reference'          => self::reference( $handoff ),
				'included_items'     => $actual,
				'quantities_changed' => Publication::revision( $planned ) !== Publication::revision( $actual ),
			);
		}
		$notes = self::included_notes();
		foreach ( array_intersect_key( self::report_only_contexts(), $notes ) as $id => $handoff ) {
			$contexts[ $id ] = array(
				'reference'          => self::reference( $handoff ),
				'included_items'     => array(),
				'quantities_changed' => false,
			);
		}
		if ( array() !== $contexts ) {
			// A compact reference fits HPOS TEXT. The full report/proof remains
			// in its immutable planner record; strings also avoid CPT array slashing.
			$encoded = wp_json_encode( $contexts, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
			if ( ! is_string( $encoded ) || strlen( $encoded ) > self::MAX_META_BYTES ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$order->update_meta_data( self::META, $encoded );
		}
		$note_texts = array_filter( $notes, static fn ( array $note ): bool => '' !== $note['text'] );
		if ( array() !== $note_texts ) {
			$encoded_notes = wp_json_encode( $note_texts, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
			if ( ! is_string( $encoded_notes ) || strlen( $encoded_notes ) > self::MAX_META_BYTES ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$order->update_meta_data( self::NOTES_META, $encoded_notes );
		}
		self::$consumed_revisions = array_column( $notes, 'note_revision', 'handoff_id' );
	}

	/** A definite refusal before Woo writes the inquiry. */
	public static function admission_unavailable(): WP_Error {
		return new WP_Error( 'planning_admission_unavailable', __( 'The solution could not be checked. Please try again.', 'linker-commerce' ), array( 'status' => 503 ) );
	}

	/**
	 * Admit the submitted draft and hold its project locks through Woo's commit.
	 *
	 * @param callable(array<string,array<string,mixed>>):(WC_Order|WP_Error) $submit Native order writer.
	 */
	public static function submit_inquiry( callable $submit ): WC_Order|WP_Error {
		$handoffs = self::active() + array_intersect_key( self::report_only_contexts(), self::included_notes() );
		if ( array() === $handoffs ) {
			return $submit( array() );
		}
		$retry = self::admission_unavailable();
		if ( \Linker\Commerce\Mail\Capacity::transaction_active() ) {
			return $retry;
		}
		$references = array_map( self::reference( ... ), $handoffs );
		$projects   = array_unique( array_column( $references, 'project_id' ) );
		sort( $projects, SORT_STRING );
		$result = $retry;
		$work   = static function () use ( $references, $submit, &$result ): void {
			foreach ( $references as $reference ) {
				/**
				 * Admit the server-stored handoff before commit.
				 *
				 * @since 0.3.0
				 */
				$admitted = apply_filters( 'linker_tools_planning_admit_inquiry', null, $reference ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Private linker-tools transport seam.
				if ( true === $admitted ) {
					continue;
				}
				if ( $admitted instanceof WP_Error && 'linker_planner_handoff_not_found' === $admitted->get_error_code() && 404 === ( $admitted->get_error_data()['status'] ?? null ) ) {
					$message = ! empty( $reference['report_only'] )
						/* translators: %s: planning project title. */
						? __( 'The planning project “%s” is no longer accessible. Clear the “Include planning reports and project notes with this inquiry” checkbox, then send your inquiry again.', 'linker-commerce' )
						/* translators: %s: planning project title. */
						: __( 'The planning project “%s” is no longer accessible. Remove its products from your solution draft, then send your inquiry again.', 'linker-commerce' );
					$result = new WP_Error( 'planning_project_deleted', sprintf( $message, $reference['title'] ), array( 'status' => 409 ) );
				}
				return;
			}
			$result = $submit( $references );
		};
		foreach ( array_reverse( $projects ) as $project_id ) {
			$work = static function () use ( $project_id, $work ): void {
				ProjectReferences::with_lock( $project_id, $work );
			};
		}
		$work();
		return $result;
	}

	/**
	 * Require the saved order to carry exactly the admitted draft's references.
	 *
	 * @param WC_Order                          $order Persisted native order.
	 * @param array<string,array<string,mixed>> $references Admitted handoffs by ID.
	 */
	public static function matches_admission( WC_Order $order, array $references ): bool {
		$raw = $order->get_meta( self::META );
		if ( '' === $raw ) {
			return array() === $references;
		}
		$entries  = self::stored( $order );
		$captured = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		return array() !== $entries && $entries === $captured && array_map( static fn ( array $entry ) => $entry['reference'], $entries ) === $references;
	}

	/**
	 * Remove only the exact consumed note revisions after an inquiry commits,
	 * preserving any newer note written by another tab.
	 *
	 * @param WC_Order $order Committed native inquiry.
	 */
	public static function consume_captured_notes( WC_Order $order ): void {
		// WC()->session is null outside a request that loaded the native cart.
		if ( ! function_exists( 'WC' ) || null === WC()->session ) {
			return;
		}
		$consumed = self::$consumed_revisions ?? array();
		foreach ( self::stored_notes( $order ) as $id => $note ) {
			$consumed[ $id ] = $note['note_revision'];
		}
		self::$consumed_revisions = $consumed;
		$stored                   = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		$retained                 = array();
		foreach ( $stored as $id => $handoff ) {
			if ( ! is_string( $id ) || ! self::valid( $handoff, $id ) ) {
				continue;
			}
			$note = self::project_note( $handoff['snapshot'] );
			if ( '' === $note && ! DraftTransfer::report_only( $handoff['snapshot'] ) ) {
				continue;
			}
			$current_revision = self::note_revision( $handoff );
			if ( isset( $consumed[ $id ] ) && hash_equals( $consumed[ $id ], $current_revision ) ) {
				continue;
			}
			$retained[ $id ] = $handoff;
		}
		WC()->session->set( DraftTransfer::CONTEXTS, $retained );
	}

	/**
	 * Native orders retain an immutable pointer and commercial quantities, not
	 * another report/product registry. Private reads resolve and match it again.
	 *
	 * @param array<string,mixed> $handoff Verified full planner handoff.
	 * @return array<string,mixed>
	 */
	public static function reference( array $handoff ): array {
		$snapshot  = $handoff['snapshot'];
		$reference = array(
			'schema_version'  => 1,
			'kind'            => 'planning_inquiry_reference_v1',
			'handoff_id'      => $handoff['id'],
			'snapshot_sha256' => $handoff['snapshot_sha256'],
		);
		foreach ( array( 'project_id', 'title', 'revision', 'input_sha256', 'report_run_id', 'report_source_sha256', 'report_sha256', 'pdf', 'items' ) as $field ) {
			$reference[ $field ] = $snapshot[ $field ];
		}
		if ( DraftTransfer::report_only( $snapshot ) ) {
			$reference['report_only'] = true;
		}
		$reference['reference_sha256'] = Publication::revision( $reference );
		return $reference;
	}

	/**
	 * Historical inquiry context is independent of subsequent publication changes.
	 *
	 * @param WC_Order $order Authorised native inquiry.
	 * @return array<string,array<string,mixed>>
	 */
	public static function stored( WC_Order $order ): array {
		$raw    = $order->get_meta( self::META );
		$raw    = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$result = array();
		if ( is_array( $raw ) ) {
			foreach ( $raw as $id => $entry ) {
				if ( ! is_string( $id ) || ! is_array( $entry ) ) {
					continue;
				}
				if ( ! array_key_exists( 'reference', $entry ) && self::valid( $entry['handoff'] ?? null, $id ) ) {
					$snapshot = $entry['handoff']['snapshot'];
					if ( ! isset( $snapshot['title'], $snapshot['input_sha256'], $snapshot['report_source_sha256'], $snapshot['report_sha256'], $snapshot['pdf'], $snapshot['items'] ) ) {
						continue;
					}
					$entry['reference'] = self::reference( $entry['handoff'] );
					unset( $entry['handoff'] );
				}
				if ( self::valid_reference( $entry['reference'] ?? null, $id ) ) {
					$result[ $id ] = $entry;
				}
			}
		}
		return $result;
	}

	/**
	 * Historical project notes included with an authorised native inquiry.
	 *
	 * @param WC_Order $order Authorised native inquiry.
	 * @return array<string,array{handoff_id:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	public static function stored_notes( WC_Order $order ): array {
		$raw    = $order->get_meta( self::NOTES_META );
		$raw    = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$result = array();
		if ( is_array( $raw ) ) {
			foreach ( $raw as $id => $entry ) {
				if (
					is_string( $id )
					&& 1 === preg_match( '/\A[a-f0-9]{32}\z/', $id )
					&& is_array( $entry )
					&& ( $entry['handoff_id'] ?? null ) === $id
					&& is_string( $entry['project_id'] ?? null )
					&& 1 === preg_match( '/\A[a-f0-9]{32}\z/', $entry['project_id'] )
					&& is_string( $entry['title'] ?? null )
					&& is_int( $entry['revision'] ?? null )
					&& $entry['revision'] >= 1
					&& is_string( $entry['note_revision'] ?? null )
					&& 1 === preg_match( '/\A[a-f0-9]{64}\z/', $entry['note_revision'] )
					&& is_string( $entry['text'] ?? null )
					&& '' !== trim( $entry['text'] )
					&& mb_strlen( $entry['text'], 'UTF-8' ) <= self::MAX_NOTE_LENGTH
				) {
					$result[ $id ] = array(
						'handoff_id'    => $id,
						'project_id'    => $entry['project_id'],
						'title'         => $entry['title'],
						'revision'      => $entry['revision'],
						'note_revision' => $entry['note_revision'],
						'text'          => $entry['text'],
					);
				}
			}
		}
		return $result;
	}

	/**
	 * Extract the customer's verbatim project note from an engine handoff snapshot.
	 *
	 * The frozen report is the only authority: its site section carries the note
	 * under the report's own label. Row order is not consulted, because a value
	 * read by position could silently report another row as the customer's words.
	 *
	 * @param array<string,mixed> $snapshot Frozen handoff snapshot.
	 */
	public static function project_note( array $snapshot ): string {
		$note = '';
		if ( is_array( $snapshot['report']['sections'] ?? null ) ) {
			foreach ( $snapshot['report']['sections'] as $section ) {
				if ( ! is_array( $section ) || 'site' !== ( $section['id'] ?? null ) || ! is_array( $section['rows'] ?? null ) ) {
					continue;
				}
				foreach ( $section['rows'] as $row ) {
					if ( ! is_array( $row ) || ! is_string( $row['value'] ?? null ) ) {
						continue;
					}
					$label = (string) ( $row['label'] ?? '' );
					if ( 'Project note' === $label || 'Projektnotiz' === $label ) {
						$note = $row['value'];
						break 2;
					}
				}
			}
		}
		if ( '—' === $note || '' === trim( $note ) || mb_strlen( $note, 'UTF-8' ) > self::MAX_NOTE_LENGTH ) {
			return '';
		}
		return $note;
	}

	/**
	 * Deterministic revision hash for a handoff's project note.
	 *
	 * @param array<string,mixed> $handoff Verified planner handoff.
	 */
	public static function note_revision( array $handoff ): string {
		$snapshot = $handoff['snapshot'];
		if ( DraftTransfer::report_only( $snapshot ) ) {
			return $handoff['snapshot_sha256'];
		}
		return hash(
			'sha256',
			(string) $handoff['id'] . '|' . (string) $snapshot['project_id'] . '|' . (string) $snapshot['revision'] . '|' . self::project_note( $snapshot )
		);
	}

	/**
	 * Show the reference and project note in the native draft item-data surface.
	 *
	 * @param array<array<string,mixed>> $data Native item descriptions.
	 * @param array<string,mixed>        $line Native cart line.
	 * @return array<array<string,mixed>>
	 */
	public function item_data( array $data, array $line ): array {
		$id     = $line[ DraftTransfer::LINE_META ] ?? null;
		$active = is_string( $id ) ? self::session_context( $id ) : null;
		if ( null !== $active ) {
			$snapshot = $active['snapshot'];
			$data[]   = array(
				'key'   => __( 'Planning project', 'linker-commerce' ),
				'value' => self::label( $snapshot ),
			);
			$note     = self::project_note( $snapshot );
			if ( '' !== $note ) {
				$data[] = array(
					'key'   => __( 'Project note', 'linker-commerce' ),
					'value' => $note,
				);
			}
		}
		return $data;
	}

	/**
	 * Semantic data fragments inherit the native Woo/LC surface and tokens.
	 *
	 * @param WC_Order $order Authorised native inquiry.
	 */
	public function render( WC_Order $order ): void {
		$this->output( $order, false );
	}

	/**
	 * Keep HTML and plain inquiry emails faithful to the same frozen context.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param bool     $admin Team copy.
	 * @param bool     $plain Plain-text template.
	 */
	public function email( WC_Order $order, bool $admin, bool $plain ): void {
		unset( $admin );
		$this->output( $order, $plain );
	}

	/** Retain receipts for uncertain retries; release consumed contexts when Woo empties. */
	public function emptied(): void {
		if ( null !== self::$consumed_revisions ) {
			$stored   = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
			$retained = array();
			foreach ( $stored as $id => $handoff ) {
				if ( ! is_string( $id ) || ! self::valid( $handoff, $id ) ) {
					continue;
				}
				$note = self::project_note( $handoff['snapshot'] );
				if ( '' !== $note || DraftTransfer::report_only( $handoff['snapshot'] ) ) {
					$rev = self::note_revision( $handoff );
					if ( ! isset( self::$consumed_revisions[ $id ] ) || ! hash_equals( self::$consumed_revisions[ $id ], $rev ) ) {
						$retained[ $id ] = $handoff;
					}
				}
			}
			self::$consumed_revisions = null;
			WC()->session->set( DraftTransfer::CONTEXTS, $retained );
			return;
		}
		WC()->session->set( DraftTransfer::CONTEXTS, array() );
	}

	/**
	 * Private download follows the native inquiry's own access checks.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param string   $id Frozen handoff identity.
	 */
	public static function report_url( WC_Order $order, string $id ): string {
		return add_query_arg( 'key', $order->get_order_key(), rest_url( 'linker/v1/inquiries/' . $order->get_id() . '/planning-report/' . $id ) );
	}

	/**
	 * Validate submitted project-note revisions against current session notes.
	 */
	private static function preflight_notes(): ?WP_Error {
		if ( null === self::$submission_post ) {
			return null;
		}
		$post    = self::$submission_post;
		$present = '1' === ( $post[ self::PRESENT_FIELD ] ?? '' );
		if ( $present && '1' !== ( $post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			return null;
		}
		$current = self::session_notes();
		if ( ! $present && ! isset( $post[ self::REVISIONS_FIELD ] ) ) {
			return null;
		}
		$posted = is_array( $post[ self::REVISIONS_FIELD ] ?? null ) ? $post[ self::REVISIONS_FIELD ] : array();
		if ( count( $posted ) !== count( $current ) ) {
			return new WP_Error( 'linker_project_notes_changed', __( 'The project notes have changed. Your other entries are still here.', 'linker-commerce' ), array( 'status' => 409 ) );
		}
		foreach ( $current as $id => $note ) {
			if ( ! isset( $posted[ $id ] ) || ! is_string( $posted[ $id ] ) || ! hash_equals( $note['note_revision'], $posted[ $id ] ) ) {
				return new WP_Error( 'linker_project_notes_changed', __( 'The project notes have changed. Your other entries are still here.', 'linker-commerce' ), array( 'status' => 409 ) );
			}
		}
		return null;
	}

	/**
	 * Resolve the project notes included by the current submission.
	 *
	 * @return array<string,array{handoff_id:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	private static function included_notes(): array {
		if ( null !== self::$submission_post && '1' === ( self::$submission_post[ self::PRESENT_FIELD ] ?? '' ) && '1' !== ( self::$submission_post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			return array();
		}
		$notes = self::session_notes();
		if ( '1' === ( self::$submission_post[ self::PRESENT_FIELD ] ?? '' ) && '1' === ( self::$submission_post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			return $notes;
		}
		return array_filter( $notes, static fn ( array $note ): bool => ! isset( $note['report_only'] ) );
	}

	/**
	 * Format the saved project reference through the native locale.
	 *
	 * @param array<string,mixed> $snapshot Frozen report context.
	 */
	private static function label( array $snapshot ): string {
		/* translators: 1: project title, 2: saved input revision. */
		return sprintf( __( '%1$s · input revision %2$d', 'linker-commerce' ), $snapshot['title'], $snapshot['revision'] );
	}

	/**
	 * Render only the native data attached to this authorised inquiry.
	 *
	 * @param WC_Order $order Native inquiry.
	 * @param bool     $plain Plain output.
	 */
	private function output( WC_Order $order, bool $plain ): void {
		foreach ( self::stored( $order ) as $id => $entry ) {
			$label   = self::label( $entry['reference'] );
			$url     = self::report_url( $order, $id );
			$changed = ! empty( $entry['quantities_changed'] ) ? __( 'Quantities differ from the planning report.', 'linker-commerce' ) : '';
			if ( $plain ) {
				echo esc_html( __( 'Planning project', 'linker-commerce' ) . ': ' . $label . "\n" . $changed . "\n" . __( 'Planning report', 'linker-commerce' ) . ': ' . $url . "\n" );
			} else {
				echo '<dl><dt>' . esc_html__( 'Planning project', 'linker-commerce' ) . '</dt><dd>' . esc_html( $label ) . '</dd>';
				if ( '' !== $changed ) {
					echo '<dd>' . esc_html( $changed ) . '</dd>';
				}
				echo '<dt>' . esc_html__( 'Planning report', 'linker-commerce' ) . '</dt><dd><a href="' . esc_url( $url ) . '">' . esc_html__( 'Download PDF', 'linker-commerce' ) . '</a></dd></dl>';
			}
		}
		foreach ( self::stored_notes( $order ) as $note ) {
			$label = self::label( $note );
			$scope = __( 'This note is not used in the calculation.', 'linker-commerce' );
			if ( $plain ) {
				echo esc_html( __( 'Project note from the customer', 'linker-commerce' ) . ' (' . $label . '): ' . $note['text'] . "\n" . $scope . "\n" );
			} else {
				echo '<dl class="linker-planning-note"><dt>' . esc_html__( 'Project note from the customer', 'linker-commerce' ) . '</dt><dd>' . esc_html( $label ) . '</dd><dd>' . nl2br( esc_html( $note['text'] ) ) . '</dd><dd>' . esc_html( $scope ) . '</dd></dl>';
			}
		}
	}

	/**
	 * Resolve one line without re-scanning every native cart line.
	 *
	 * @param string $id Native handoff reference.
	 * @return array<string,mixed>|null
	 */
	private static function session_context( string $id ): ?array {
		$stored = (array) WC()->session->get( DraftTransfer::CONTEXTS, array() );
		return isset( $stored[ $id ] ) && self::valid( $stored[ $id ], $id ) ? $stored[ $id ] : null;
	}

	/**
	 * Only the immutable server-created envelope can be copied into native records.
	 *
	 * @param mixed  $value Stored context.
	 * @param string $id Native line reference.
	 */
	private static function valid( mixed $value, string $id ): bool {
		return DraftTransfer::native_context_valid( $value, $id );
	}

	/**
	 * Check the compact native reference before displaying or resolving it.
	 *
	 * @param mixed  $value Native order metadata.
	 * @param string $id Referenced handoff identity.
	 */
	private static function valid_reference( mixed $value, string $id ): bool {
		if ( ! is_array( $value ) || 1 !== ( $value['schema_version'] ?? null ) || 'planning_inquiry_reference_v1' !== ( $value['kind'] ?? null ) || ( $value['handoff_id'] ?? null ) !== $id || ! is_string( $value['title'] ?? null ) || ! is_int( $value['revision'] ?? null ) || $value['revision'] < 1 || ! is_array( $value['items'] ?? null ) || ! is_array( $value['pdf'] ?? null ) ) {
			return false;
		}
		foreach ( array( 'handoff_id', 'project_id', 'report_run_id' ) as $field ) {
			if ( ! is_string( $value[ $field ] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $value[ $field ] ) ) {
				return false;
			}
		}
		foreach ( array( 'snapshot_sha256', 'input_sha256', 'report_source_sha256', 'report_sha256', 'reference_sha256' ) as $field ) {
			if ( ! is_string( $value[ $field ] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $value[ $field ] ) ) {
				return false;
			}
		}
		$pdf = $value['pdf'];
		if ( ! is_string( $pdf['asset_id'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{32}\z/', $pdf['asset_id'] ) || ! is_string( $pdf['sha256'] ?? null ) || 1 !== preg_match( '/\A[a-f0-9]{64}\z/', $pdf['sha256'] ) || 'application/pdf' !== ( $pdf['media_type'] ?? null ) || ! array_is_list( $value['items'] ) || ( array() === $value['items'] ) !== ( true === ( $value['report_only'] ?? false ) ) ) {
			return false;
		}
		foreach ( $value['items'] as $item ) {
			if ( ! is_array( $item ) || ! is_int( $item['product_id'] ?? null ) || $item['product_id'] < 1 || ! is_int( $item['quantity'] ?? null ) || $item['quantity'] < 1 || ! is_string( $item['label'] ?? null ) || '' === $item['label'] ) {
				return false;
			}
		}
		$sha = $value['reference_sha256'];
		unset( $value['reference_sha256'] );
		return hash_equals( $sha, Publication::revision( $value ) );
	}
}
