<?php
/**
 * Repeatable German-address migration, with an explicit preview.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Cli;

use Linker\I18n\GermanUrlMigration;
use WP_CLI;

/** Public migration entry point; previews are read-only. */
final class GermanUrlsCommand {

	/**
	 * Previews the German page, post, product and category addresses.
	 *
	 * ## OPTIONS
	 *
	 * [--dry-run]
	 * : Preview the migration (the default).
	 *
	 * [--apply]
	 * : Apply the preflighted migration.
	 *
	 * [--rollback]
	 * : Restore the saved originals (with --apply).
	 *
	 * [--verify]
	 * : Fail unless the stored migration is complete and consistent.
	 *
	 * [--format=<format>]
	 * : Output the preview as table or json. Default: table.
	 *
	 * @param array<int, string>  $args Positional arguments.
	 * @param array<string,mixed> $options Options.
	 */
	public function __invoke( array $args, array $options ): void {
		unset( $args );
		if ( ! current_user_can( 'manage_options' ) ) {
			WP_CLI::error( 'Run as an administrator.' );
		}
		if ( ( isset( $options['apply'], $options['dry-run'] ) ) || ( isset( $options['verify'] ) && ( isset( $options['apply'] ) || isset( $options['rollback'] ) || isset( $options['dry-run'] ) ) ) ) {
			WP_CLI::error( 'Choose one of --dry-run, --apply or --verify; --rollback supports dry-run or apply.' );
		}
		if ( ! in_array( $options['format'] ?? 'table', array( 'table', 'json' ), true ) ) {
			WP_CLI::error( 'Format must be table or json.' );
		}
		$migration = new GermanUrlMigration();
		if ( isset( $options['verify'] ) ) {
			try {
				$migration->verify();
				WP_CLI::success( 'Verified German URL migration state.' );
			} catch ( \RuntimeException $error ) {
				WP_CLI::error( $error->getMessage() );
			}
			return;
		}
		if ( isset( $options['apply'] ) && ! isset( $options['dry-run'] ) ) {
			try {
				$changed = isset( $options['rollback'] ) ? $migration->rollback() : $migration->apply();
				WP_CLI::success( $changed . ' changes.' );
			} catch ( \RuntimeException $error ) {
				WP_CLI::error( $error->getMessage() );
			}
			return;
		}
		try {
			$rows = $migration->preview( isset( $options['rollback'] ) );
			if ( 'json' === ( $options['format'] ?? 'table' ) ) {
				WP_CLI::log(
					(string) wp_json_encode(
						array(
							'backup_objects' => count( $migration->backup() ),
							'rollback'       => isset( $options['rollback'] ),
							'objects'        => $rows,
						),
						JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
					)
				);
				return;
			}
			foreach ( $rows as $row ) {
				$changes = isset( $options['rollback'] ) ? $row['before'] : $row['after'];
				WP_CLI::log( $row['type'] . ':' . $row['id'] . ' ' . $row['url'] . ' -> ' . $row['target_url'] . ' ' . ( array() === $changes ? 'complete' : implode( ', ', array_keys( $changes ) ) ) );
			}
			WP_CLI::log( 'Backup: ' . count( $migration->backup() ) . ' original objects retained.' );
		} catch ( \RuntimeException $error ) {
			WP_CLI::error( $error->getMessage() );
		}
		WP_CLI::success( 'Dry run; no migration data written.' );
	}
}
