<?php
/**
 * Isolated requests using the real managed-file resolver and a test option.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products\Publication;

/**
 * Count actual file hashes without changing their result.
 *
 * @param string $algorithm Digest algorithm.
 * @param string $filename Managed file.
 */
function hash_file( string $algorithm, string $filename ): string|false {
	++$GLOBALS['linker_commerce_hash_calls'];
	$result = \hash_file( $algorithm, $filename );
	if ( is_string( $GLOBALS['linker_commerce_hash_change'] ) ) {
		$mtime = filemtime( $filename );
		file_put_contents( $filename, $GLOBALS['linker_commerce_hash_change'] );
		if ( false !== $mtime ) {
			touch( $filename, $mtime );
		}
		$GLOBALS['linker_commerce_hash_change'] = null;
	}
	return $result;
}

/**
 * Read this test process's simulated option.
 *
 * @param string $name Option name.
 * @param mixed  $fallback Default value.
 */
function get_option( string $name, mixed $fallback = false ): mixed {
	unset( $name, $fallback );
	return $GLOBALS['linker_commerce_hash_option'];
}

/**
 * Save the test option for transfer to the next isolated process.
 *
 * @param string $name Option name.
 * @param mixed  $value Option value.
 * @param mixed  $autoload Autoload choice.
 */
function update_option( string $name, mixed $value, mixed $autoload = null ): bool {
	unset( $name, $autoload );
	++$GLOBALS['linker_commerce_hash_writes'];
	$GLOBALS['linker_commerce_hash_option'] = $value;
	return true;
}

/** Return the test host. */
function home_url(): string {
	return 'http://linker.test';
}

/**
 * Return the isolated test uploads root.
 *
 * @return array{basedir:string,baseurl:string}
 * @throws \RuntimeException When the test root is missing.
 */
function wp_upload_dir(): array {
	if ( ! is_string( $GLOBALS['linker_commerce_hash_uploads'] ) ) {
		throw new \RuntimeException( 'Missing test uploads root.' );
	}
	return array(
		'basedir' => $GLOBALS['linker_commerce_hash_uploads'],
		'baseurl' => 'http://linker.test/wp-content/uploads',
	);
}

/**
 * Use PHP's native URL parser for the test host.
 *
 * @param string $url URL to parse.
 * @param int    $component Optional component.
 */
function wp_parse_url( string $url, int $component = -1 ): mixed {
	return parse_url( $url, $component );
}

$linker_commerce_hash_input              = json_decode( (string) stream_get_contents( STDIN ), true, 512, JSON_THROW_ON_ERROR );
$GLOBALS['linker_commerce_hash_calls']   = 0;
$GLOBALS['linker_commerce_hash_writes']  = 0;
$GLOBALS['linker_commerce_hash_option']  = $linker_commerce_hash_input['cache'];
$GLOBALS['linker_commerce_hash_uploads'] = $linker_commerce_hash_input['uploads'];
$GLOBALS['linker_commerce_hash_change']  = $linker_commerce_hash_input['after_hash'];
require dirname( __DIR__, 2 ) . '/includes/Products/Publication/DocumentFiles.php';
DocumentFiles::begin_read( $linker_commerce_hash_input['manifest'] );
$linker_commerce_hash_file = DocumentFiles::resolve( 'http://linker.test/wp-content/uploads/2026/manual.pdf' );
DocumentFiles::end_read();
echo json_encode(
	array(
		'sha'        => $linker_commerce_hash_file['blob_sha256'] ?? null,
		'hash_calls' => $GLOBALS['linker_commerce_hash_calls'],
		'writes'     => $GLOBALS['linker_commerce_hash_writes'],
		'cache'      => $GLOBALS['linker_commerce_hash_option'],
	),
	JSON_THROW_ON_ERROR
);
