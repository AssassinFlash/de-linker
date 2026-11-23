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
	public const PROJECT_FIELD   = 'linker_preliminary_project';
	public const PROJECT_META    = '_linker_preliminary_project';
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

	/** Exact preliminary note verified before the native write.
	 *
	 * @var array{project_id:string,title:string,revision:int,note_revision:string,text:string,inputs?:array<string,mixed>}|null
	 */
	private static ?array $reviewed_note = null;

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
		$previous_note         = self::$reviewed_note;
		self::$submission_post = $post;
		self::$reviewed_note   = null;
		try {
			return $callback();
		} finally {
			self::$submission_post = $previous;
			self::$reviewed_note   = $previous_note;
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
	 * @param array<string,mixed>|null $proposed Optional replacement project shown before a confirmed transfer.
	 * @return array<string,array{handoff_id:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	public static function session_notes( ?array $proposed = null ): array {
		// WC()->session is null outside a request that loaded the native cart.
		if ( ! function_exists( 'WC' ) || null === WC()->session ) {
			return array();
		}
		$stored     = null === $proposed
			? (array) WC()->session->get( DraftTransfer::CONTEXTS, array() )
			: array( $proposed['id'] => DraftTransfer::native_context( $proposed ) );
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
		return isset( self::$reviewed_note['inputs'] ) || array() !== self::included_notes();
	}

	/**
	 * Recheck the exact reviewed draft and project-note revisions before Woo writes.
	 *
	 * @param array<string,mixed>|null $proposed Reviewed replacement handoff.
	 */
	public static function preflight( ?array $proposed = null ): ?WP_Error {
		if ( null === $proposed ) {
			$active = self::active();
			foreach ( WC()->cart->get_cart() as $line ) {
				$id = $line[ DraftTransfer::LINE_META ] ?? null;
				if ( null !== $id && ( ! is_string( $id ) || ! isset( $active[ $id ] ) ) ) {
					return new WP_Error( 'planning_context_unavailable', __( 'Your solution draft changed. Please review it and send your inquiry again.', 'linker-commerce' ), array( 'status' => 409 ) );
				}
			}
		}
		foreach ( self::submitted_handoffs( $proposed ) as $handoff ) {
			$error = DraftTransfer::publication_error( $handoff['snapshot'] );
			if ( $error instanceof WP_Error ) {
				return $error;
			}
		}
		return self::preflight_notes( $proposed );
	}

	/**
	 * Render the inquiry form's project-notes review and inclusion section.
	 *
	 * @param array<string,mixed>      $previous Consumed flash fields after a failed POST.
	 * @param array<string,mixed>|null $proposed Handoff included in the projected inquiry.
	 * @param array<string,mixed>|null $note Current owner-verified project note.
	 * @param bool                     $show_project Whether this form contains the project summary.
	 */
	public static function inquiry_notes_section( array $previous = array(), ?array $proposed = null, ?array $note = null, bool $show_project = true ): string {
		$notes   = self::session_notes( $proposed );
		$project = '';
		if ( $show_project && isset( $note['inputs'] ) ) {
			$summary = self::project_summary( $note, isset( $previous[ self::PROJECT_FIELD ] ) );
			$project = '' === $summary ? '' : '<div class="linker-inquiry-project">' . nl2br( esc_html( $summary ) ) . '</div>';
		}
		if ( null !== $note && ( ! isset( $note['inputs'] ) || '' !== trim( $note['text'] ) ) ) {
			$notes[ 'project_' . $note['project_id'] ] = $note;
		}
		if ( array() === $notes ) {
			return $project;
		}
		$included      = ! ( isset( $previous[ self::PRESENT_FIELD ] ) && '1' === $previous[ self::PRESENT_FIELD ] && '1' !== ( $previous[ self::INCLUDE_FIELD ] ?? '' ) );
		$has_report    = array() !== array_filter( $notes, static fn ( array $note ): bool => ! empty( $note['report_only'] ) );
		$html          = '<fieldset class="linker-inquiry-project-notes">';
		$html         .= '<legend>' . ( $has_report ? esc_html__( 'Planning report', 'linker-commerce' ) : esc_html__( 'Your project note', 'linker-commerce' ) ) . '</legend>';
		$html         .= '<input type="hidden" name="' . esc_attr( self::PRESENT_FIELD ) . '" value="1" />';
		$html         .= '<label class="linker-form-consent"><input type="checkbox" name="' . esc_attr( self::INCLUDE_FIELD ) . '" value="1"' . ( $included ? ' checked' : '' ) . ' /><span>' . ( $has_report ? esc_html__( 'Include planning reports and project notes with this inquiry', 'linker-commerce' ) : esc_html__( 'Include project notes with this inquiry', 'linker-commerce' ) ) . '</span></label>';
		$has_note_text = false;
		foreach ( $notes as $id => $note ) {
			$html .= '<input type="hidden" name="' . esc_attr( self::REVISIONS_FIELD . '[' . $id . ']' ) . '" value="' . esc_attr( $note['note_revision'] ) . '" />';
			if ( ! isset( $note['text'] ) ) {
				continue; // Failed lookup on retry: retain the option to exclude, never display stale text.
			}
			$has_note_text = $has_note_text || '' !== $note['text'];
			$html         .= '<div class="linker-inquiry-project-note"><p><strong>' . esc_html( self::label( $note ) ) . '</strong></p><p>' . nl2br( esc_html( $note['text'] ) ) . '</p></div>';
		}
		if ( $has_note_text ) {
			$html .= '<p class="linker-form-note">' . esc_html__( 'This note is not used in the calculation.', 'linker-commerce' ) . '</p>';
		}
		$html .= '</fieldset>';
		return $project . $html;
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
		$transfer = InquiryTransfer::read( self::$submission_post[ InquiryTransfer::FIELD ] ?? null );
		if ( null !== $transfer ) {
			$order->update_meta_data( InquiryTransfer::ORDER_META, $transfer->handoff );
		}
		if ( isset( self::$reviewed_note['inputs'] ) ) {
			$project = self::$reviewed_note;
			// Woo's native customer note remains readable by previous releases.
			$message = $order->get_customer_note();
			$summary = self::project_summary( $project );
			if ( isset( self::included_notes()[ 'project_' . $project['project_id'] ] ) ) {
				$summary .= "\n\n" . __( 'Project note from the customer', 'linker-commerce' ) . ': ' . $project['text'];
			}
			$order->set_customer_note( $summary . ( '' === $message ? '' : "\n\n" . $message ) );
			$order->update_meta_data( self::PROJECT_META, $project['project_id'] . ':' . $project['revision'] );
		}
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
		// Preliminary notes are already frozen in the native note, including for older readers.
		if ( isset( self::$reviewed_note['inputs'] ) ) {
			unset( $notes[ 'project_' . self::$reviewed_note['project_id'] ] );
		}
		$note_texts = array_filter( $notes, static fn ( array $note ): bool => '' !== $note['text'] );
		if ( array() !== $note_texts ) {
			$encoded_notes = wp_json_encode( $note_texts, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
			if ( ! is_string( $encoded_notes ) || strlen( $encoded_notes ) > self::MAX_META_BYTES ) {
				throw new \RuntimeException( 'planning_inquiry_context_unavailable' );
			}
			$order->update_meta_data( self::NOTES_META, $encoded_notes );
		}
		if ( null === $transfer ) {
			self::$consumed_revisions = array_map( static fn ( array $note ): string => $note['note_revision'], $notes );
		}
	}

	/** A definite refusal before Woo writes the inquiry. */
	public static function admission_unavailable(): WP_Error {
		return new WP_Error( 'planning_admission_unavailable', __( 'The solution could not be checked. Please try again.', 'linker-commerce' ), array( 'status' => 503 ) );
	}

	/** Frozen handoffs the current inquiry will submit, keyed by handoff ID.
	 *
	 * @param array<string,mixed>|null $proposed Reviewed replacement handoff.
	 * @return array<string,array<string,mixed>>
	 */
	public static function submitted_handoffs( ?array $proposed = null ): array {
		if ( null !== $proposed ) {
			if ( DraftTransfer::report_only( $proposed['snapshot'] ) && ! isset( self::included_notes( $proposed )[ $proposed['id'] ] ) ) {
				return array();
			}
			return array( $proposed['id'] => DraftTransfer::native_context( $proposed ) );
		}
		return self::active() + array_intersect_key( self::report_only_contexts(), self::included_notes() );
	}

	/**
	 * Admit the submitted draft and hold its project locks through Woo's commit.
	 *
	 * @param callable(array<string,array<string,mixed>>,array<int,string>):(WC_Order|WP_Error) $submit Native order writer.
	 * @param array<string,mixed>|null                                                          $proposed Reviewed replacement handoff.
	 */
	public static function submit_inquiry( callable $submit, ?array $proposed = null ): WC_Order|WP_Error {
		$handoffs = self::submitted_handoffs( $proposed );
		$project  = isset( self::$reviewed_note['inputs'] ) ? self::$reviewed_note : null;
		if ( array() === $handoffs && null === $project ) {
			return $submit( array(), array() );
		}
		$retry = self::admission_unavailable();
		if ( \Linker\Commerce\Mail\Capacity::transaction_active() ) {
			return $retry;
		}
		$references = array_map( self::reference( ... ), $handoffs );
		$admissions = $references;
		if ( null !== $project ) {
			$admissions[] = array(
				'project_id' => $project['project_id'],
				'revision'   => $project['revision'],
			);
		}
		$projects = array_unique( array_column( $admissions, 'project_id' ) );
		sort( $projects, SORT_STRING );
		$result = $retry;
		$work   = static function () use ( $admissions, $projects, $references, $submit, &$result ): void {
			foreach ( $admissions as $reference ) {
				/**
				 * Admit the server-stored handoff before commit.
				 *
				 * @since 0.3.0
				 */
				$admitted = apply_filters( 'linker_tools_planning_admit_inquiry', null, $reference ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Private linker-tools transport seam.
				if ( true === $admitted ) {
					continue;
				}
				if ( ! isset( $reference['handoff_id'] ) ) {
					if ( $admitted instanceof WP_Error ) {
						$result = self::preliminary_refusal( $admitted );
					}
					return;
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
			$result = $submit( $references, $projects );
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
		if ( isset( self::$reviewed_note['inputs'] ) && $order->get_meta( self::PROJECT_META ) !== self::$reviewed_note['project_id'] . ':' . self::$reviewed_note['revision'] ) {
			return false;
		}
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
	 * @return array<string,array{handoff_id?:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	public static function stored_notes( WC_Order $order ): array {
		$raw    = $order->get_meta( self::NOTES_META );
		$raw    = is_string( $raw ) ? json_decode( $raw, true ) : $raw;
		$result = array();
		if ( is_array( $raw ) ) {
			foreach ( $raw as $id => $entry ) {
				if (
					is_string( $id )
					&& is_array( $entry )
					&& is_string( $entry['project_id'] ?? null )
					&& 1 === preg_match( '/\A[a-f0-9]{32}\z/', $entry['project_id'] )
					&& is_string( $entry['title'] ?? null )
					&& is_int( $entry['revision'] ?? null )
					&& $entry['revision'] >= 1
					&& is_string( $entry['note_revision'] ?? null )
					&& (
						( 'project_' . $entry['project_id'] === $id && ! isset( $entry['handoff_id'] ) && $entry['note_revision'] === (string) $entry['revision'] )
						|| ( ( $entry['handoff_id'] ?? null ) === $id && 1 === preg_match( '/\A[a-f0-9]{32}\z/', $id ) && 1 === preg_match( '/\A[a-f0-9]{64}\z/', $entry['note_revision'] ) )
					)
					&& is_string( $entry['text'] ?? null )
					&& '' !== trim( $entry['text'] )
					&& mb_strlen( $entry['text'], 'UTF-8' ) <= self::MAX_NOTE_LENGTH
				) {
					$result[ $id ] = array(
						...( isset( $entry['handoff_id'] ) ? array( 'handoff_id' => $id ) : array() ),
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
	 * Read hardware phase conflicts from the frozen report, including older reports.
	 *
	 * @param array<string,mixed> $snapshot Frozen handoff snapshot.
	 * @return list<array{unit:string|null,actual:1|3,required:1|3}>
	 */
	public static function phase_conflicts( array $snapshot ): array {
		$report    = $snapshot['report'] ?? array();
		$conflicts = array();
		if ( array_key_exists( 'phase_conflicts', $report ) ) {
			foreach ( $report['phase_conflicts'] as $check ) {
				$unit     = $check['unit'] ?? null;
				$actual   = $check['actual'] ?? null;
				$required = $check['required'] ?? null;
				if ( ( null === $unit || ( is_string( $unit ) && '' !== trim( $unit ) ) )
					&& ( 1 === $actual || 3 === $actual )
					&& ( 1 === $required || 3 === $required )
					&& $actual !== $required ) {
					$conflicts[] = array(
						'unit'     => $unit,
						'actual'   => $actual,
						'required' => $required,
					);
				}
			}
			return $conflicts;
		}

		foreach ( $report['sections'] ?? array() as $section ) {
			if ( ! preg_match( '/\Acheck-[0-9]+\z/', $section['id'] ?? '' ) ) {
				continue;
			}
			$title     = $section['title'] ?? '';
			$separator = strrpos( $title, ' · ' );
			$unit      = false === $separator ? null : substr( $title, 0, $separator );
			$check     = false === $separator ? $title : substr( $title, $separator + strlen( ' · ' ) );
			$labels    = match ( $check ) {
				'Grid phases' => array( 'Assessment status', 'Requirements not met', 'Result', 'Requirement' ),
				'Netzphasen'  => array( 'Prüfstatus', 'Anforderungen nicht erfüllt', 'Ergebnis', 'Anforderung' ),
				default       => null,
			};
			if ( null === $labels || ( null !== $unit && '' === trim( $unit ) ) ) {
				continue;
			}
			$rows     = array_column( $section['rows'] ?? array(), 'value', 'label' );
			$actual   = $rows[ $labels[2] ] ?? null;
			$required = $rows[ $labels[3] ] ?? null;
			if ( ( $rows[ $labels[0] ] ?? null ) === $labels[1]
				&& ( '1' === $actual || '3' === $actual )
				&& ( '1' === $required || '3' === $required )
				&& $actual !== $required ) {
				$conflicts[] = array(
					'unit'     => $unit,
					'actual'   => '1' === $actual ? 1 : 3,
					'required' => '1' === $required ? 1 : 3,
				);
			}
		}
		return $conflicts;
	}

	/** Show each active project's hardware conflicts in the native Woo cart. */
	public function cart_phase_notices(): void {
		foreach ( self::active() as $handoff ) {
			$snapshot = $handoff['snapshot'];
			foreach ( self::phase_conflicts( $snapshot ) as $conflict ) {
				$unit = null === $conflict['unit'] ? '' : esc_html( $conflict['unit'] ) . ': ';
				wc_print_notice(
					esc_html( $snapshot['title'] ) . ': ' . $unit . sprintf(
						/* translators: 1: inverter phase count, 2: required grid phase count. */
						esc_html__( 'Grid phase mismatch. Selected inverter: %1$d. Project requirement: %2$d. You can send an inquiry to discuss the configuration.', 'linker-commerce' ),
						$conflict['actual'],
						$conflict['required']
					),
					'notice'
				);
			}
		}
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
	private static function notes_changed(): WP_Error {
		return new WP_Error( 'linker_project_notes_changed', __( 'The project notes have changed. Your other entries are still here.', 'linker-commerce' ), array( 'status' => 409 ) );
	}

	/** Only an owned-revision lookup can distinguish a missing project from a missing service route.
	 *
	 * @param WP_Error $error Private planner refusal.
	 */
	private static function preliminary_refusal( WP_Error $error ): WP_Error {
		return 'linker_planner_project_revision_not_found' === $error->get_error_code() && 404 === ( $error->get_error_data()['status'] ?? null )
			? new WP_Error( 'planning_preliminary_unavailable', __( 'This project is unavailable. Your contact details and message are still here.', 'linker-commerce' ), array( 'status' => 409 ) )
			: self::admission_unavailable();
	}

	/** Read a project under the native submitter's ownership.
	 *
	 * @param string   $id Selected project ID.
	 * @param int|null $revision Reviewed revision; legacy note-only forms read the current revision.
	 * @return array{project_id:string,title:string,revision:int,note_revision:string,text:string,inputs?:array<string,mixed>}|WP_Error|null
	 */
	public static function read_selected_note( string $id, ?int $revision = null ): array|WP_Error|null {
		/** Read the selected project with the native submitter’s identity.
		 *
		 * @since 0.3.0
		 */
		$note = apply_filters( 'linker_tools_planning_inquiry_note', null, $id, ...( null === $revision ? array() : array( $revision ) ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- Private linker-tools transport seam.
		if ( $note instanceof WP_Error ) {
			if ( null !== $revision ) {
				return self::preliminary_refusal( $note );
			}
			return in_array( $note->get_error_data()['status'] ?? null, array( 401, 403, 404 ), true ) ? self::notes_changed() : self::admission_unavailable();
		}
		return $note;
	}

	/** Read a project's immutable inputs using the current submitter's identity.
	 *
	 * @param mixed $reference Reviewed project and revision from the form.
	 * @return array{project_id:string,title:string,revision:int,note_revision:string,text:string,inputs:array<string,mixed>}|WP_Error
	 */
	public static function read_preliminary_project( mixed $reference ): array|WP_Error {
		if ( ! is_string( $reference ) || ! preg_match( '/\A([a-f0-9]{32}):([1-9][0-9]*)\z/', $reference, $match ) ) {
			return self::notes_changed();
		}
		$project = self::read_selected_note( $match[1], (int) $match[2] );
		if ( $project instanceof WP_Error ) {
			return $project;
		}
		if ( ! is_array( $project['inputs'] ?? null ) || $project['project_id'] !== $match[1] || (string) $project['revision'] !== $match[2] ) {
			return self::notes_changed();
		}
		return $project;
	}

	/**
	 * Check every reviewed revision before the first Woo write.
	 *
	 * @param array<string,mixed>|null $proposed Reviewed replacement handoff.
	 */
	private static function preflight_notes( ?array $proposed ): ?WP_Error {
		if ( null === self::$submission_post ) {
			return null;
		}
		$post                = self::$submission_post;
		self::$reviewed_note = null;
		if ( isset( $post[ self::PROJECT_FIELD ] ) ) {
			$project = self::read_preliminary_project( $post[ self::PROJECT_FIELD ] );
			if ( $project instanceof WP_Error ) {
				return $project;
			}
			self::$reviewed_note = $project;
		}
		$present = '1' === ( $post[ self::PRESENT_FIELD ] ?? '' );
		if ( $present && '1' !== ( $post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			return null;
		}
		$current = self::session_notes( $proposed );
		if ( ! $present && ! isset( $post[ self::REVISIONS_FIELD ] ) ) {
			return null;
		}
		$posted = is_array( $post[ self::REVISIONS_FIELD ] ?? null ) ? $post[ self::REVISIONS_FIELD ] : array();
		foreach ( array_keys( $posted ) as $key ) {
			if ( ! is_string( $key ) || ! preg_match( '/\Aproject_([a-f0-9]{32})\z/', $key, $match ) ) {
				continue;
			}
			if ( ! $present || ( null !== self::$reviewed_note && ( ! isset( self::$reviewed_note['inputs'] ) || self::$reviewed_note['project_id'] !== $match[1] ) ) ) {
				return self::notes_changed();
			}
			$note = self::$reviewed_note ?? self::read_selected_note( $match[1] );
			if ( $note instanceof WP_Error ) {
				return $note;
			}
			if ( null === $note || $note['note_revision'] !== $posted[ $key ] ) {
				return self::notes_changed();
			}
			self::$reviewed_note = $note;
			$current[ $key ]     = $note;
		}
		if ( isset( self::$reviewed_note['inputs'] ) && '' !== trim( self::$reviewed_note['text'] ) ) {
			$current[ 'project_' . self::$reviewed_note['project_id'] ] = self::$reviewed_note;
		}
		if ( count( $posted ) !== count( $current ) ) {
			return self::notes_changed();
		}
		foreach ( $current as $id => $note ) {
			if ( ! isset( $posted[ $id ] ) || ! is_string( $posted[ $id ] ) || ! hash_equals( $note['note_revision'], $posted[ $id ] ) ) {
				return self::notes_changed();
			}
		}
		return null;
	}

	/**
	 * Resolve the project notes included by the current submission.
	 *
	 * @param array<string,mixed>|null $proposed Reviewed replacement handoff.
	 * @return array<string,array{handoff_id?:string,project_id:string,title:string,revision:int,note_revision:string,text:string,report_only?:true}>
	 */
	private static function included_notes( ?array $proposed = null ): array {
		if ( null !== self::$submission_post && '1' === ( self::$submission_post[ self::PRESENT_FIELD ] ?? '' ) && '1' !== ( self::$submission_post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			return array();
		}
		$notes = self::session_notes( $proposed );
		if ( '1' === ( self::$submission_post[ self::PRESENT_FIELD ] ?? '' ) && '1' === ( self::$submission_post[ self::INCLUDE_FIELD ] ?? '' ) ) {
			if ( null !== self::$reviewed_note && '' !== trim( self::$reviewed_note['text'] ) ) {
				$note = self::$reviewed_note;
				unset( $note['inputs'] );
				$notes[ 'project_' . $note['project_id'] ] = $note;
			}
			return $notes;
		}
		return array_filter( $notes, static fn ( array $note ): bool => ! isset( $note['report_only'] ) );
	}

	/** Sales and the customer see the same facts from the selected input revision.
	 *
	 * @param array<string,mixed> $project Owned planner project.
	 * @param bool                $include_direction Include the direction unless the planner already displays it.
	 * @throws \UnexpectedValueException The project has no supported preliminary direction.
	 */
	private static function project_summary( array $project, bool $include_direction = true ): string {
		$lines = $include_direction ? array( self::label( $project ) ) : array();
		foreach ( self::project_facts( $project, $include_direction ) as $label => $value ) {
			$lines[] = $label . ': ' . $value;
		}
		return implode( "\n", $lines );
	}

	/**
	 * Facts attached to the reviewed project revision, in the active language.
	 *
	 * @param array<string,mixed> $project Owned planner project.
	 * @param bool                $include_direction Include the planned system.
	 * @param bool                $for_planner Add panel inputs and use the selection labels from the planner.
	 * @return array<string,string>
	 * @throws \UnexpectedValueException The project has no supported preliminary direction.
	 */
	private static function project_facts( array $project, bool $include_direction, bool $for_planner = false ): array {
		$inputs  = $project['inputs'];
		$brief   = $inputs['brief'] ?? array();
		$site    = $brief['site'] ?? array();
		$number  = static fn ( $value ): string => $for_planner ? wc_format_localized_decimal( (string) $value ) : (string) $value;
		$country = $site['country_code'] ?? '';
		if ( $for_planner && '' !== $country ) {
			$country = WC()->countries->get_countries()[ $country ] ?? $country;
		}
		// phpcs:disable WordPress.WP.I18n.TextDomainMismatch -- Use the configurator's existing EN/DE field labels.
		$scope = match ( $brief['system_scope'] ?? null ) {
			null               => '',
			'new_pv_storage'   => __( 'Solar and storage', 'linker-tools' ),
			'storage_addition' => __( 'Storage for existing PV', 'linker-tools' ),
			'storage_only'     => __( 'Storage', 'linker-tools' ),
			'pv_only'          => __( 'Solar', 'linker-tools' ),
			default            => throw new \UnexpectedValueException( 'unknown_preliminary_direction' ),
		};
		$use = match ( $brief['project_use'] ?? null ) {
			'residential' => __( 'Residential', 'linker-tools' ),
			'commercial'  => __( 'Commercial', 'linker-tools' ),
			'industrial'  => __( 'Industrial', 'linker-tools' ),
			default       => '',
		};
		$scenario = $inputs['energy_scenario'] ?? array();
		$modes    = array_column( $scenario['schedule'] ?? array(), 'mode' );
		$purpose  = match ( true ) {
			isset( $inputs['backup_demand'] ) || in_array( 'outage', $modes, true ) => __( 'Backup supply', 'linker-tools' ),
			'peak_shaving_with_reserve_v1' === ( $scenario['controller'] ?? '' )   => __( 'Reduce peak demand', 'linker-tools' ),
			in_array( 'connected', $modes, true )                                   => __( 'Use more solar on site', 'linker-tools' ),
			default                                                                 => '',
		};
		$equipment = $inputs['equipment_plant_setup']['requirements'] ?? $inputs['equipment_plant']['requirements'] ?? $inputs['equipment_setup'] ?? $inputs['equipment_requirements'] ?? array();
		$reference = $inputs['pvgis_reference_setup'] ?? $inputs['pvgis_reference'] ?? array();
		$pv_kwp    = $equipment['pv_dc_kw'] ?? null;
		$arrays    = 'pvgis_5_3_known_ac_reference_v1' === ( $reference['model'] ?? '' ) ? ( $reference['arrays'] ?? array() ) : array();
		if ( $arrays ) {
			$sizes  = array_column( $arrays, 'peak_power_kwp' );
			$pv_kwp = count( $sizes ) === count( $arrays ) && ! in_array( null, $sizes, true ) ? array_sum( $sizes ) : null;
		}
		$basis = match ( $brief['annual_load']['basis'] ?? null ) {
			'bill_total'     => $for_planner ? __( 'Electricity bill', 'linker-tools' ) : __( 'Electricity bills', 'linker-tools' ),
			'user_estimate'  => $for_planner ? __( 'Estimate', 'linker-tools' ) : __( 'Project estimate', 'linker-tools' ),
			default          => '',
		};
		$limits = array();
		if ( 'peak_shaving_with_reserve_v1' === ( $scenario['controller'] ?? '' ) ) {
			foreach ( $scenario['schedule'] ?? array() as $period ) {
				if ( 'connected' === $period['mode'] && 'limited' === ( $period['import_policy'] ?? '' ) && isset( $period['import_cap_kw'] ) ) {
					$limits[] = $number( $period['import_cap_kw'] ) . ' kW';
				}
			}
		}
		$phase = $equipment['grid_phase'] ?? ( '' === $purpose ? '' : __( 'To confirm', 'linker-tools' ) );
		if ( $for_planner ) {
			$phase = match ( $phase ) {
				1       => __( 'Single phase', 'linker-tools' ),
				3       => __( 'Three phase', 'linker-tools' ),
				default => $phase,
			};
		}
		$inverter = '';
		if ( ! $for_planner && 'storage_addition' === ( $brief['system_scope'] ?? null ) && isset( $inputs['existing_system']['keep_inverter'] ) ) {
			$inverter = $inputs['existing_system']['keep_inverter'] ? __( 'Keep the existing inverter', 'linker-tools' ) : __( 'Consider a replacement inverter', 'linker-tools' );
		}
		$facts = array(
			__( 'Planned system', 'linker-tools' )         => $include_direction ? $scope : '',
			__( 'Location', 'linker-tools' )               => implode( ', ', array_filter( array( $site['location_label'] ?? '', $site['postal_code'] ?? '', $country ), static fn ( $part ): bool => '' !== $part ) ),
			__( 'Latitude', 'linker-tools' )               => isset( $site['latitude'] ) ? $number( $site['latitude'] ) : '',
			__( 'Longitude', 'linker-tools' )              => isset( $site['longitude'] ) ? $number( $site['longitude'] ) : '',
			__( 'Time zone', 'linker-tools' )              => $site['timezone'] ?? '',
			__( 'Project type', 'linker-tools' )           => $use,
			__( 'Annual electricity use', 'linker-tools' ) => isset( $brief['annual_load']['kwh'] ) ? $number( $brief['annual_load']['kwh'] ) . ' kWh' : '',
			__( 'Basis for the annual figure', 'linker-tools' ) => $basis,
			__( 'Source note', 'linker-tools' )            => $brief['annual_load']['source_note'] ?? '',
			__( 'Main purpose', 'linker-tools' )           => $purpose,
			__( 'Target grid import limit', 'linker-tools' ) => implode( ', ', array_unique( $limits ) ),
			__( 'Grid phases', 'linker-tools' )            => $phase,
			__( 'Existing inverter (retrofit)', 'linker-tools' ) => $inverter,
			__( 'PV array size', 'linker-tools' )          => null !== $pv_kwp ? $number( $pv_kwp ) . ' kWp' : '',
			__( 'Continuous discharge power', 'linker-tools' ) => isset( $equipment['required_discharge_ac_kw'] ) ? $number( $equipment['required_discharge_ac_kw'] ) . ' kW' : '',
			__( 'Usable storage capacity', 'linker-tools' ) => isset( $equipment['required_usable_kwh'] ) ? $number( $equipment['required_usable_kwh'] ) . ' kWh' : '',
			__( 'Backup load', 'linker-tools' )            => isset( $inputs['backup_demand']['load_kw'] ) ? $number( $inputs['backup_demand']['load_kw'] ) . ' kW' : '',
			__( 'Required duration', 'linker-tools' )      => isset( $inputs['backup_demand']['duration_hours'] ) ? $number( $inputs['backup_demand']['duration_hours'] ) . ' h' : '',
			__( 'Solution draft', 'linker-commerce' )      => $inputs['saved_solution_reference']['title'] ?? '',
		);
		if ( $for_planner ) {
			if ( $arrays && isset( $equipment['pv_dc_kw'] ) ) {
				$facts[ __( 'PV input power', 'linker-tools' ) ] = $number( $equipment['pv_dc_kw'] ) . ' kWp';
			}
			$panels = $inputs['known_panel_details'] ?? array();
			if ( isset( $panels['count'] ) ) {
				$facts[ __( 'Number of modules', 'linker-tools' ) ] = $number( $panels['count'] );
			}
			if ( isset( $panels['power_w'] ) ) {
				$facts[ __( 'Power per panel', 'linker-tools' ) ] = $number( $panels['power_w'] ) . ' Wp';
			}
			// The Solar capacity control also populates the first reference array.
			if ( isset( $panels['system_kwp'] ) && ! ( 1 === count( $arrays ) && isset( $arrays[0]['peak_power_kwp'] ) && (float) $arrays[0]['peak_power_kwp'] === (float) $panels['system_kwp'] ) ) {
				$facts[ __( 'Solar capacity', 'linker-tools' ) ] = $number( $panels['system_kwp'] ) . ' kWp';
			}
		}
		// phpcs:enable WordPress.WP.I18n.TextDomainMismatch
		return array_map( 'strval', array_filter( $facts, static fn ( $value ): bool => '' !== $value ) );
	}

	/**
	 * Details displayed alongside the native contact form in the planner.
	 *
	 * @param array<string,mixed> $project Owned planner project.
	 * @return list<array{label:string,value:string}>
	 */
	public static function review_facts( array $project ): array {
		if ( ! isset( $project['inputs'] ) ) {
			return array();
		}
		$rows = array();
		foreach ( self::project_facts( $project, false, for_planner: true ) as $label => $value ) {
			$rows[] = array(
				'label' => $label,
				'value' => $value,
			);
		}
		return $rows;
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
