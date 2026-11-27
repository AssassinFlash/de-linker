<?php
/** LiteSpeed Cache configuration API used by the WP-CLI migration; static analysis only. */
// phpcs:ignoreFile -- Installed plugin method signatures.
namespace LiteSpeed;
class Conf {
	/** @return self */
	public static function cls() {}
	/** @param array<string,mixed> $the_matrix */
	public function update_confs( $the_matrix = array() ) {}
}
