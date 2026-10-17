<?php
/**
 * A QualityStore that records instead of writing post meta.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\QualityStore;

/**
 * Records what the route handed in; takes every record for conversation 812.
 */
final class RecordingQualityStore extends QualityStore {

	/**
	 * Records handed in.
	 *
	 * @var list<array<string, mixed>>
	 */
	public array $records = array();

	/**
	 * Status reports handed in.
	 *
	 * @var list<array<string, mixed>>
	 */
	public array $statuses = array();

	/**
	 * Takes every record that names conversation 812.
	 *
	 * @param array<string, mixed> $raw Record.
	 */
	public function store( array $raw ): bool {
		$this->records[] = $raw;
		return 812 === ( $raw['conversation_id'] ?? null );
	}

	/**
	 * Records the report.
	 *
	 * @param array<string, mixed> $status Report.
	 */
	public function store_status( array $status ): void {
		$this->statuses[] = $status;
	}
}
