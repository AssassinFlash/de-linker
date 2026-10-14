<?php
/**
 * The shape WordPress's HTTP layer answers with.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Tests\Doubles;

/**
 * Core's `Requests_Utility_CaseInsensitiveDictionary`, as the tests need it: a
 * dictionary whose headers are private and read through `getAll()`. Casting it
 * to an array exposes one mangled key (`"\0*\0data"`) and nothing else — the
 * shape that hid the pdf content type until 2026-10-15.
 */
final class HeaderDictionary {

	/**
	 * The headers; private, as core's dictionary stores them.
	 *
	 * @var array<string, string>
	 */
	private array $headers = array(
		'Content-Type'   => 'application/pdf',
		'Content-Length' => '48835',
	);

	/**
	 * Core's own accessor.
	 *
	 * @return array<string, string>
	 */
	public function getAll(): array { // phpcs:ignore WordPress.NamingConventions.ValidFunctionName.MethodNameInvalid -- core's own method name.
		return $this->headers;
	}
}
