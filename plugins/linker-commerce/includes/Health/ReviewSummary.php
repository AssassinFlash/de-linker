<?php
/** Narrow read boundary for saved inquiries awaiting staff review.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Health;

use Closure;
use WP_Error;

/** Admission owns the rows; health consumers read only count, age and an admin link. */
final class ReviewSummary {
	/**
	 * Use the intake aggregate, or an isolated native fixture.
	 *
	 * @param Closure|null $read Test-owned summary reader.
	 */
	public function __construct( private readonly ?Closure $read = null ) {}
	/**
	 * Read a complete aggregate; failure never masquerades as an empty queue.
	 *
	 * @return array{count: int, oldest: int, url: string}|WP_Error
	 */
	public function get(): array|WP_Error {
		/**
		 * Admission supplies only saved pending count, oldest Unix time and the native staff URL.
		 * Null means the producer is absent; consumers must not call that an empty queue.
		 *
		 * @since 0.2.0
		 */
		$result = null !== $this->read ? ( $this->read )() : apply_filters( 'linker_commerce_pending_review_summary', null );
		if ( is_wp_error( $result ) ) {
			return $result;
		}
		if ( ! is_array( $result ) || ! is_int( $result['count'] ?? null ) || $result['count'] < 0 || ! is_int( $result['oldest'] ?? null ) || ( $result['count'] > 0 && $result['oldest'] <= 0 ) || ! is_string( $result['url'] ?? null ) || ! str_starts_with( $result['url'], admin_url() ) ) {
			return new WP_Error( 'review_summary_invalid', 'Pending inquiry counts could not be verified.' );
		}
		return array(
			'count'  => $result['count'],
			'oldest' => $result['oldest'],
			'url'    => $result['url'],
		);
	}
}
