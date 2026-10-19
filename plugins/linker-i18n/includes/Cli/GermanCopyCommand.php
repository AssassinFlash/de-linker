<?php
/**
 * Repeatable German copy migration, with an explicit preview.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Cli;

use Linker\I18n\GermanCopyMigration;
use Linker\I18n\Translation\Translator;
use WP_CLI;

/** Public migration entry point; previews are read-only. */
final class GermanCopyCommand {

	/**
	 * Sets up the command.
	 *
	 * @param Translator $translator Records the reviewed German as the translation baseline.
	 */
	public function __construct( private readonly Translator $translator ) {}

	/**
	 * Previews the reviewed German copy values.
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
	 * : Fail unless the stored migration is complete.
	 *
	 * [--format=<format>]
	 * : Output the preview as table or json. Default: table.
	 *
	 * @param array<int, string>  $args    Positional arguments.
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
		$migration = new GermanCopyMigration( new \Linker\I18n\Languages(), null, $this->translator );
		if ( isset( $options['verify'] ) ) {
			try {
				$migration->verify();
				WP_CLI::success( 'Verified German copy migration state.' );
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
			$rollback = isset( $options['rollback'] );
			$rows     = $rollback ? array_values( $migration->backup() ) : $migration->plan();
			if ( 'json' === ( $options['format'] ?? 'table' ) ) {
				WP_CLI::log(
					(string) wp_json_encode(
						array(
							'backup_objects' => count( $migration->backup() ),
							'rollback'       => $rollback,
							'objects'        => $rows,
						),
						JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
					)
				);
				return;
			}
			foreach ( $rows as $row ) {
				WP_CLI::log( $row['type'] . ':' . $row['id'] . ' source ' . $row['source'] );
				$from = $rollback ? $row['after'] : $row['before'];
				$to   = $rollback ? $row['before'] : $row['after'];
				foreach ( $to as $field => $value ) {
					$before = (string) ( $from[ $field ] ?? '' );
					WP_CLI::log( '  ' . $field . ': ' . wp_json_encode( $this->excerpt( $before, $value ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) . ' -> ' . wp_json_encode( $this->excerpt( $value, $before ), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES ) );
				}
			}
			WP_CLI::log( 'Backup: ' . count( $migration->backup() ) . ' original objects retained.' );
		} catch ( \RuntimeException $error ) {
			WP_CLI::error( $error->getMessage() );
		}
		WP_CLI::success( 'Dry run; no migration data written.' );
	}

	/**
	 * A readable window around the first change for the table preview; the
	 * JSON preview keeps the complete values for a diff.
	 *
	 * @param string $value Field value.
	 * @param string $other The value it is compared with.
	 */
	private function excerpt( string $value, string $other ): string {
		// Short values are their own preview. Longer ones (a page body) show
		// the first difference with 40 bytes of context on each side; 160 is
		// the readable width of one preview row in a standard terminal.
		if ( \strlen( $value ) <= 160 ) {
			return $value;
		}
		$limit  = min( \strlen( $value ), \strlen( $other ) );
		$offset = 0;
		while ( $offset < $limit && $value[ $offset ] === $other[ $offset ] ) {
			++$offset;
		}
		$start = max( 0, $offset - 40 );
		return '…' . \mb_strcut( $value, $start, 200 ) . '…';
	}
}
