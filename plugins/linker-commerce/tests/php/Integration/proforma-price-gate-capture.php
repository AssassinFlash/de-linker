<?php
/**
 * Test doubles for the Proforma download's header() and readfile().
 *
 * DocumentDownload::serve() calls those functions unqualified. While this
 * file is loaded they resolve inside Linker\Commerce\Account, so the price-gate
 * test records the PDF instead of sending it and exiting.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Account;

use Linker\Commerce\Tests\Integration\ProformaPriceGateTest;

/**
 * Stands in for header() while the price-gate test is loaded.
 *
 * @param string $header        Header line.
 * @param bool   $replace       Replaces a previous header of the same name.
 * @param int    $response_code HTTP status.
 */
function header( string $header, bool $replace = true, int $response_code = 0 ): void {
	ProformaPriceGateTest::keep_header( $header, $replace, $response_code );
}

// The throw is the return: serve() would exit the process.
// phpcs:disable Squiz.Commenting.FunctionComment.InvalidNoReturn
/**
 * Stands in for readfile() while the price-gate test is loaded.
 *
 * The real call streams the PDF and serve() then exits. Recording the file
 * and throwing returns those bytes to the test. The signature matches the
 * call in DocumentDownload::serve().
 *
 * @param string $filename Private PDF.
 * @return int|false Byte count. This stand-in throws instead.
 * @throws \RuntimeException Always, so the process does not exit.
 */
function readfile( string $filename ): int|false {
	ProformaPriceGateTest::keep_pdf( $filename );
	throw new \RuntimeException( 'proforma-bytes' );
}
// phpcs:enable Squiz.Commenting.FunctionComment.InvalidNoReturn
