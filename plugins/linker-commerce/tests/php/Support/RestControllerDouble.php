<?php
/**
 * WordPress's REST controller base class, as far as the unit tests need it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

/**
 * Stands in for WP_REST_Controller in the unit tests, which do not load
 * WordPress (tests/php/bootstrap.php aliases it): the properties
 * SelectionFactsController sets and the schema method WordPress's OPTIONS
 * answer calls. On a real site WordPress's own class is the parent.
 */
abstract class RestControllerDouble {

	/**
	 * REST namespace.
	 *
	 * @var string
	 */
	protected $namespace;

	/**
	 * Route within the namespace.
	 *
	 * @var string
	 */
	protected $rest_base;

	/**
	 * Cached schema.
	 *
	 * @var array<string, mixed>|null
	 */
	protected $schema;

	/**
	 * The schema WordPress shows for OPTIONS; WordPress also strips arg_options.
	 *
	 * @return array<string, mixed>
	 */
	public function get_public_item_schema(): array {
		return $this->get_item_schema();
	}

	/**
	 * The item schema.
	 *
	 * @return array<string, mixed>
	 */
	abstract public function get_item_schema(): array;
}
