<?php
/**
 * The knobs the embedding shims read; the test class is the only writer.
 *
 * @package Linker\Commerce
 */

declare( strict_types=1 );

namespace Linker\Commerce\Abilities;

/**
 * Test knobs for the embedding shims.
 */
final class QueryEmbeddingTestShims {

	/**
	 * When set, getenv( 'LINKER_EMBEDDING_PROVIDER' ) answers this.
	 *
	 * @var string|null
	 */
	public static ?string $provider = null;

	/**
	 * Lines error_log received.
	 *
	 * @var list<string>
	 */
	public static array $logged = array();
}
