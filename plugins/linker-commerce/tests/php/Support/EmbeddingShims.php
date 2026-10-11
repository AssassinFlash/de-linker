<?php
/**
 * Namespace-local shims so the embedding tests can observe getenv, error_log
 * and usleep without touching the process for real. The knobs live in the
 * QueryEmbeddingTestShims class, loaded from EmbeddingShimsKnobs.php.
 *
 * @package Linker\Commerce
 */

declare( strict_types=1 );

namespace Linker\Commerce\Abilities;

/**
 * Getenv with a test override for the provider switch.
 *
 * @param string $name Variable name.
 * @return string|false
 */
function getenv( string $name ) {
	if ( 'LINKER_EMBEDDING_PROVIDER' === $name && null !== QueryEmbeddingTestShims::$provider ) {
		return QueryEmbeddingTestShims::$provider;
	}
	return \getenv( $name );
}

/**
 * Error_log that records instead of writing.
 *
 * @param string $message Line to record.
 * @return bool
 */
function error_log( string $message ) {
	QueryEmbeddingTestShims::$logged[] = $message;
	return true;
}

/**
 * Usleep that returns instantly.
 *
 * @param int $microseconds Ignored.
 * @return void
 */
function usleep( int $microseconds ) {}
