<?php
/**
 * Memory substrate for VAT rule/template unit tests; native protection is tested separately.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Fixtures;

use Linker\Commerce\Registration\VatNotice;
use Linker\Commerce\Registration\VatProfile;

/** Follows the existing overridable native-service seam used by VIES and Genie tests. */
final class VatNoticeMemory extends VatNotice {
	/**
	 * The unit's user meta is owned by its WP_Mock fixture.
	 *
	 * @param int $id Synthetic account.
	 */
	public function version( int $id ): string {
		return '';
	}

	/**
	 * Preserve the rule test's original native write projection, without a DB.
	 *
	 * @param int                                $id Synthetic account.
	 * @param string                             $number Normalized VAT input.
	 * @param array{status:string,detail:string} $result Simulated real VIES result.
	 * @param bool                               $notify Native policy.
	 * @param string                             $witness Unused memory token.
	 * @return array<string,mixed>
	 */
	public function persist( int $id, string $number, array $result, bool $notify, string $witness ): array {
		$previous = (string) get_user_meta( $id, VatProfile::STATUS_META, true );
		update_user_meta( $id, VatProfile::STATUS_META, $result['status'] );
		update_user_meta( $id, VatProfile::DETAIL_META, $result['detail'] );
		update_user_meta( $id, VatProfile::NUMBER_META, $number );
		update_user_meta( $id, VatProfile::CHECKED_META, time() );
		return array(
			'previous' => $previous,
			'current'  => $result['status'],
			'job'      => $notify && '' !== $previous && $previous !== $result['status'] ? 0 : -1,
		);
	}

	/**
	 * A template unit renders a known native change; no job or transport is claimed.
	 *
	 * @param int      $id Synthetic account.
	 * @param callable $capture Native template seam.
	 * @phpstan-param callable(array<string,mixed>):?\Linker\Commerce\Mail\Message $capture
	 */
	public function deliver( int $id, callable $capture ): void {
		$capture(
			array(
				'previous' => VatProfile::INVALID,
				'current'  => VatProfile::VALID,
			)
		);
	}
}
