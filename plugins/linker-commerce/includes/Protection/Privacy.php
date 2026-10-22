<?php
/**
 * Native WordPress privacy lifecycle for subject-linked admission payloads.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Protection;

/** The framework owns requester verification; callbacks do no external lookup. */
final class Privacy {
	/** Use the native verified-email export/removal path. */
	public function register(): void {
		add_filter( 'wp_privacy_personal_data_exporters', array( $this, 'exporters' ) );
		add_filter( 'wp_privacy_personal_data_erasers', array( $this, 'erasers' ) );
	}

	/**
	 * Register a bounded single-page exporter on WordPress's own surface.
	 *
	 * @param array<string,mixed> $exporters Native registered exporters.
	 * @return array<string,mixed>
	 */
	public function exporters( array $exporters ): array {
		$exporters['linker-public-protection'] = array(
			'exporter_friendly_name' => __( 'Public request protection', 'linker-commerce' ),
			'callback'               => array( $this, 'export' ),
		);
		return $exporters;
	}

	/**
	 * Register the corresponding approved erasure callback.
	 *
	 * @param array<string,mixed> $erasers Native registered erasers.
	 * @return array<string,mixed>
	 */
	public function erasers( array $erasers ): array {
		$erasers['linker-public-protection'] = array(
			'eraser_friendly_name' => __( 'Public request protection', 'linker-commerce' ),
			'callback'             => array( $this, 'erase' ),
		);
		return $erasers;
	}

	/**
	 * Export only receipts linked to the native verified address/account.
	 *
	 * @param string $email Verified requester address.
	 * @param int    $page Framework page.
	 * @return array<string,mixed> Native exporter response.
	 * @throws \RuntimeException A busy or failed read must not claim no data exists.
	 */
	public function export( string $email, int $page = 1 ): array {
		if ( $page > 1 ) {
			return array(
				'data' => array(),
				'done' => true,
			);
		}
		$result = ( new Ledger() )->privacy( self::owners( $email ), false );
		if ( is_wp_error( $result ) ) {
			throw new \RuntimeException( 'public_admission_export_unavailable' );
		}
		$review = IntakeStore::privacy( self::owners( $email ), false );
		if ( is_wp_error( $review ) ) {
			throw new \RuntimeException( 'public_review_export_unavailable' );
		}
		$data = array();
		foreach ( $review['data'] as $record ) {
			$data[] = array(
				'group_id'    => 'linker-public-protection',
				'group_label' => __( 'Public request protection', 'linker-commerce' ),
				'item_id'     => 'review-capacity-' . $record['id'],
				'data'        => array(
					array(
						'name'  => __( 'Public request review', 'linker-commerce' ),
						'value' => (string) wp_json_encode( $record, JSON_UNESCAPED_UNICODE ),
					),
				),
			);
		}
		foreach ( $result['data'] as $record ) {
			$data[] = array(
				'group_id'    => 'linker-public-protection',
				'group_label' => __( 'Public request protection', 'linker-commerce' ),
				'item_id'     => 'admission-' . $record['id'],
				'data'        => array(
					array(
						'name'  => __( 'Request processing record', 'linker-commerce' ),
						'value' => (string) wp_json_encode( $record, JSON_UNESCAPED_UNICODE ),
					),
				),
			);
		}
		foreach ( $result['buckets'] as $id => $bucket ) {
			$data[] = array(
				'group_id'    => 'linker-public-protection',
				'group_label' => __( 'Public request protection', 'linker-commerce' ),
				'item_id'     => 'admission-counter-' . $id,
				'data'        => array(
					array(
						'name'  => __( 'Request allowance counter', 'linker-commerce' ),
						'value' => (string) wp_json_encode( $bucket ),
					),
				),
			);
		}
		return array(
			'data' => $data,
			'done' => true,
		);
	}

	/**
	 * Strip linked payload atomically with admission/recovery/late completion.
	 *
	 * @param string $email Verified requester address.
	 * @param int    $page Framework page.
	 * @return array<string,mixed> Explicit removal and minimal-retention status.
	 * @throws \RuntimeException Storage failure cannot be reported as completed erasure.
	 */
	public function erase( string $email, int $page = 1 ): array {
		if ( $page > 1 ) {
			return array(
				'items_removed'  => false,
				'items_retained' => false,
				'messages'       => array(),
				'done'           => true,
			);
		}
		$result = ( new Ledger() )->privacy( self::owners( $email ), true );
		if ( is_wp_error( $result ) ) {
			throw new \RuntimeException( 'public_admission_erasure_unavailable' );
		}
		$review = IntakeStore::privacy( self::owners( $email ), true );
		if ( is_wp_error( $review ) ) {
			throw new \RuntimeException( 'public_review_erasure_unavailable' );
		}
		$removed = $result['removed'] > 0 || $review['removed'] > 0;

		return array(
			'items_removed'  => $removed,
			'items_retained' => $removed,
			'messages'       => $review['removed'] > 0 ? array( __( 'Linked request data was removed. Minimal review-capacity markers remain until the saved request is resolved or its native data is erased.', 'linker-commerce' ) ) : ( $removed ? array( __( 'Linked request data was removed. Minimal duplicate-request markers remain until their original retry window ends.', 'linker-commerce' ) ) : array() ),
			'done'           => true,
		);
	}

	/**
	 * A guest without a supplied address has no email-linked record to resolve.
	 *
	 * @param string $email Verified requester address.
	 * @return list<string> Private subject owner hashes.
	 */
	private static function owners( string $email ): array {
		$owners = array( Allowance::owner_for( Identity::recipient( $email ) ) );
		$user   = get_user_by( 'email', $email );
		if ( $user instanceof \WP_User ) {
			$owners[] = Allowance::owner_for( Identity::account( $user->ID ) );
		}
		return $owners;
	}
}
