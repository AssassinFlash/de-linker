<?php
/**
 * The live products of the #7 fixture.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Support;

use RuntimeException;

/**
 * The 89 published inverters and batteries of de-linker.com as read on
 * 2026-10-09, and the draft 4124 that the migration corrects
 * (tests/fixtures/live-products-2026-10-09.json, see its "source"), optionally
 * with the data changes of tools/migrate/7-facts.json applied.
 */
final class LiveCatalogue {

	private const FIXTURE = __DIR__ . '/../../fixtures/live-products-2026-10-09.json';

	private const MIGRATION = __DIR__ . '/../../../../../tools/migrate/7-facts.json';

	private const RESEARCH_CSV = __DIR__ . '/../../fixtures/live-catalogue-facts.csv';

	/**
	 * The published products of the fixture, by ID.
	 *
	 * @param bool $migrated Whether to apply tools/migrate/7-facts.json.
	 * @return array<int, array{name: string, status: string, categories: array<int, string>, attributes: array<string, string[]>, figures: string}>
	 */
	public static function published( bool $migrated = false ): array {
		return array_filter( self::products( $migrated ), static fn ( array $product ): bool => 'publish' === $product['status'] );
	}

	/**
	 * All products of the fixture by ID: status, category slug by term ID,
	 * attribute term slugs by taxonomy, and the figures meta as stored.
	 *
	 * @param bool $migrated Whether to apply tools/migrate/7-facts.json.
	 * @return array<int, array{name: string, status: string, categories: array<int, string>, attributes: array<string, string[]>, figures: string}>
	 */
	public static function products( bool $migrated = false ): array {
		$fixture       = self::read( self::FIXTURE );
		$category_ids  = array();
		$products      = array();
		$product_rows  = $fixture['products'];
		$category_rows = $fixture['product_categories'];
		foreach ( $category_rows as $category ) {
			$category_ids[ $category['slug'] ] = $category['id'];
		}
		foreach ( $product_rows as $row ) {
			$attributes = array();
			foreach ( $row['attributes'] as $attribute ) {
				$attributes[ $attribute['taxonomy'] ] = $attribute['terms'];
			}
			$categories = array();
			foreach ( $row['categories'] as $slug ) {
				$categories[ $category_ids[ $slug ] ] = $slug;
			}
			$products[ $row['id'] ] = array(
				'name'       => $row['name'],
				'status'     => $row['status'],
				'categories' => $categories,
				'attributes' => $attributes,
				'figures'    => $row['meta']['_tv_b2b_figures'],
			);
		}

		return $migrated ? self::migrate( $products ) : $products;
	}

	/**
	 * The rows of the research CSV (docs/research/2026-10-09/old-repo-live-catalogue-facts.md),
	 * column => cell, by product ID.
	 *
	 * @return array<int, array<string, string>>
	 * @throws RuntimeException When the file cannot be read.
	 */
	public static function research_csv(): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fopen -- a local fixture; WordPress is not loaded in unit tests.
		$handle = fopen( self::RESEARCH_CSV, 'r' );
		if ( false === $handle ) {
			throw new RuntimeException( 'Cannot read the research CSV.' );
		}
		$header = (array) fgetcsv( $handle, null, ',', '"', '' );
		$rows   = array();
		while ( false !== ( $cells = fgetcsv( $handle, null, ',', '"', '' ) ) ) { // phpcs:ignore Generic.CodeAnalysis.AssignmentInCondition.FoundInWhileCondition -- the usual fgetcsv loop.
			$row                      = array_combine( array_map( 'strval', $header ), array_map( 'strval', $cells ) );
			$rows[ (int) $row['id'] ] = $row;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_fclose -- see fopen above.
		fclose( $handle );

		return $rows;
	}

	/**
	 * Applies the "to" side of every change in tools/migrate/7-facts.json.
	 *
	 * @param array<int, array{name: string, status: string, categories: array<int, string>, attributes: array<string, string[]>, figures: string}> $products Products by ID.
	 * @return array<int, array{name: string, status: string, categories: array<int, string>, attributes: array<string, string[]>, figures: string}>
	 * @throws RuntimeException When the migration names a product the fixture does not have.
	 */
	private static function migrate( array $products ): array {
		$plan = self::read( self::MIGRATION );
		foreach ( $plan['attributes'] as $change ) {
			$product = $products[ $change['product'] ] ?? throw new RuntimeException( 'The migration names a product the fixture does not have.' );

			$product['attributes'][ $change['taxonomy'] ] = $change['to'];
			$products[ $change['product'] ]               = $product;
		}
		foreach ( $plan['figures'] as $change ) {
			$product                   = $products[ $change['product'] ] ?? throw new RuntimeException( 'The migration names a product the fixture does not have.' );
			$figures                   = json_decode( $product['figures'], true, 512, JSON_THROW_ON_ERROR );
			$figures[ $change['key'] ] = $change['to'];
			// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- WordPress is not loaded in unit tests.
			$product['figures']             = (string) json_encode( $figures, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES );
			$products[ $change['product'] ] = $product;
		}

		return $products;
	}

	/**
	 * Reads a JSON file.
	 *
	 * @param string $path File path.
	 * @return array<string, mixed>
	 * @throws RuntimeException When the file cannot be read.
	 */
	private static function read( string $path ): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- a local fixture; WordPress is not loaded in unit tests.
		$json = file_get_contents( $path );
		if ( false === $json ) {
			throw new RuntimeException( 'Cannot read a test fixture.' );
		}

		return json_decode( $json, true, 512, JSON_THROW_ON_ERROR );
	}
}
