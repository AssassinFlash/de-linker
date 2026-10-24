<?php
/**
 * Explicit current FAQ evidence for presentation fixtures.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Products\Publication;

/** Only caller-supplied answers and one specified current document are bound. */
trait BoundFaqFixture {
	/**
	 * A prepared binding for the fixture's deliberately authorized answer set.
	 *
	 * @param array<int|string,mixed> $answers Explicit prepared FAQ rows.
	 * @param string                  $document_id Current fixture document.
	 * @param string                  $sha Current fixture bytes.
	 * @return array<string,array{document_id:string,blob_sha256:string,figure_revision:string}>
	 */
	private static function bound_faqs( array $answers, string $document_id, string $sha ): array {
		$bindings = array();
		foreach ( Faqs::normalize( $answers ) as $answer ) {
			$revision              = Publication::revision( $answer );
			$bindings[ $revision ] = array(
				'document_id'     => $document_id,
				'blob_sha256'     => $sha,
				'figure_revision' => $revision,
			);
		}
		return $bindings;
	}
}
