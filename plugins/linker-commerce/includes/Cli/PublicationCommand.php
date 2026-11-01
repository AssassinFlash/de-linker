<?php
/**
 * Install/read back the native document gate and reconcile pending preparation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\PreparationJobs;

/** No original file is deleted; the emergency withdrawal block remains intact. */
final class PublicationCommand {
	/**
	 * Preview or apply the one-time Woo declaration migration; preview is default.
	 *
	 * ## OPTIONS
	 *
	 * [--input=<path>]
	 * : Retained compatibility JSON; defaults to the shipped one-time input.
	 * [--dry-run]
	 * : Return the complete before/after plan without writing.
	 * [--apply]
	 * : Apply only with the reviewed source hash and current publication revision.
	 * [--source-sha256=<sha256>]
	 * : Exact input-file hash returned by the preview.
	 * [--publication-revision=<sha256>]
	 * : Current source revision returned by the preview.
	 * [--rollback]
	 * : Preview restoration of untouched migration writes; add --apply to restore.
	 *
	 * @subcommand migrate-compatibility
	 * @param array<int,string>   $args Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 * @throws \RuntimeException Caught and reported through WP-CLI.
	 */
	public function migrate_compatibility( array $args, array $assoc_args ): void {
		unset( $args );
		try {
			$apply = isset( $assoc_args['apply'] ) && ! isset( $assoc_args['dry-run'] );
			if ( isset( $assoc_args['rollback'] ) ) {
				$result = \Linker\Commerce\Products\Publication\CompatibilityMigration::rollback( ! $apply );
			} else {
				$path  = isset( $assoc_args['input'] ) ? (string) $assoc_args['input'] : dirname( __DIR__, 2 ) . '/' . \Linker\Commerce\Products\EngineeringData::COMPATIBILITY_FILE;
				$input = \Linker\Commerce\Products\EngineeringData::json_from( $path );
				$hash  = is_readable( $path ) ? hash_file( 'sha256', $path ) : false; // phpcs:ignore WordPress.WP.AlternativeFunctions.file_system_operations_is_readable -- Explicit CLI migration input.
				if ( null === $input || false === $hash ) {
					throw new \RuntimeException( 'The retained migration input cannot be read.' );
				}
				$plan = \Linker\Commerce\Products\Publication\CompatibilityMigration::plan( $input, $hash );
				if ( $apply && ( ( $assoc_args['source-sha256'] ?? '' ) !== $hash || ( $assoc_args['publication-revision'] ?? '' ) !== $plan['publication_revision'] ) ) {
					throw new \RuntimeException( 'Apply requires the source hash and publication revision from the reviewed preview.' );
				}
				$result = $apply ? \Linker\Commerce\Products\Publication\CompatibilityMigration::apply( $plan ) : $plan;
			}
			\WP_CLI::log( (string) wp_json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
		} catch ( \RuntimeException $error ) {
			\WP_CLI::error( $error->getMessage() );
		}
	}

	/**
	 * Migrate the retained reference input into Woo once, or withdraw that record.
	 *
	 * ## OPTIONS
	 *
	 * [--dry-run]
	 * : Preview without creating or changing any product.
	 *
	 * [--withdraw=<product-id>]
	 * : Reversibly set the migrated reference record to draft; preserve all files/data.
	 *
	 * @subcommand migrate-reference
	 * @param array<int,string>   $args Positional arguments.
	 * @param array<string,mixed> $assoc_args Options.
	 * @throws \RuntimeException Caught here and reported by WP-CLI.
	 */
	public function migrate_reference( array $args, array $assoc_args ): void {
		unset( $args );
		try {
			$dry_run = isset( $assoc_args['dry-run'] );
			if ( isset( $assoc_args['withdraw'] ) ) {
				$result = \Linker\Commerce\Products\Publication\ReferenceMigration::withdraw( (int) $assoc_args['withdraw'], $dry_run );
			} else {
				$input = \Linker\Commerce\Products\EngineeringData::json( \Linker\Commerce\Products\EngineeringData::OVERLAY_FILE );
				if ( null === $input ) {
					throw new \RuntimeException( 'The one-time reference migration input is unavailable.' );
				}
				$result = \Linker\Commerce\Products\Publication\ReferenceMigration::run( $input, $dry_run );
			}
			\WP_CLI::log( (string) wp_json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
		} catch ( \RuntimeException $error ) {
			\WP_CLI::error( $error->getMessage() );
		}
	}

	/**
	 * Preview or adopt the two source-bound noncommercial cable references.
	 * Originals must already exist in uploads through normal media maintenance.
	 *
	 * ## OPTIONS
	 *
	 * [--input=<path>]
	 * : Reviewed one-time cable JSON, default data/cable-references.json.
	 * [--apply]
	 * : Adopt missing references only; existing Woo records are never overwritten.
	 * [--source-sha256=<sha256>]
	 * : Exact input-file hash issued by the preview.
	 * [--publication-revision=<sha256>]
	 * : Current publication revision issued by the preview.
	 * [--withdraw=<product-id>]
	 * : Preview withdrawing one adopted cable; add --apply to retain it as draft.
	 *
	 * @subcommand migrate-cable-references
	 * @param array<int,string>   $args Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 * @throws \RuntimeException Caught and reported through WP-CLI.
	 */
	public function migrate_cable_references( array $args, array $assoc_args ): void {
		unset( $args );
		try {
			$apply = isset( $assoc_args['apply'] );
			if ( isset( $assoc_args['withdraw'] ) ) {
				$id = filter_var( $assoc_args['withdraw'], FILTER_VALIDATE_INT, array( 'options' => array( 'min_range' => 1 ) ) );
				if ( false === $id || \Linker\Commerce\Products\EngineeringReference::CABLE !== \Linker\Commerce\Products\EngineeringReference::role( $id ) ) {
					throw new \RuntimeException( 'Withdraw requires one existing reference cable identity.' );
				}
				$result = \Linker\Commerce\Products\Publication\ReferenceMigration::withdraw( $id, ! $apply );
			} else {
				$path = isset( $assoc_args['input'] ) ? (string) $assoc_args['input'] : dirname( __DIR__, 2 ) . '/data/cable-references.json';
				// Decode and hash the very same bytes; a replacement between two
				// opens must never approve different content under the reviewed hash.
				// phpcs:ignore WordPress.WP.AlternativeFunctions -- Explicit administrator-selected local migration input.
				$bytes = is_readable( $path ) ? file_get_contents( $path ) : false;
				$input = is_string( $bytes ) ? json_decode( $bytes, true ) : null;
				$hash  = is_string( $bytes ) ? hash( 'sha256', $bytes ) : false;
				if ( ! is_array( $input ) || 1 !== ( $input['schema_version'] ?? null ) || ! is_array( $input['references'] ?? null ) || 2 !== count( $input['references'] ) ) {
					throw new \RuntimeException( 'The two reviewed cable references and their input hash are required.' );
				}
				$ids = array_column( $input['references'], 'id' );
				if ( 2 !== count( array_unique( $ids ) ) || array_filter( $input['references'], static fn( array $entry ): bool => 'cable' !== ( $entry['kind'] ?? null ) ) ) {
					throw new \RuntimeException( 'Distinct cable-only engineering identities are required.' );
				}
				$manifest = Publication::manifest();
				$result   = array(
					'source_sha256'        => $hash,
					'publication_revision' => $manifest['source_revision'],
					'references'           => array(),
				);
				foreach ( $input['references'] as $entry ) {
					$result['references'][] = \Linker\Commerce\Products\Publication\ReferenceMigration::run( array( 'overlay' => array( $entry ) ), true );
				}
				if ( $apply ) {
					if ( ( $assoc_args['source-sha256'] ?? null ) !== $hash || ( $assoc_args['publication-revision'] ?? null ) !== $manifest['source_revision'] ) {
						throw new \RuntimeException( 'Apply requires the exact reviewed input hash and publication revision.' );
					}
					$created = array();
					$locked  = \Linker\Commerce\Inquiry\Assessment\Lock::run(
						'cable-reference-adoption',
						static function () use ( $input, $manifest, &$created ): void {
							if ( Publication::manifest()['source_revision'] !== $manifest['source_revision'] ) {
								throw new \RuntimeException( 'Woo changed after the cable preview; no adoption started.' );
							}
							try {
								foreach ( $input['references'] as $entry ) {
									$created[] = \Linker\Commerce\Products\Publication\ReferenceMigration::run( array( 'overlay' => array( $entry ) ), false );
								}
							} catch ( \Throwable $error ) {
								// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI-only diagnostic preserves exact recovery IDs.
								throw new \RuntimeException( 'Cable adoption stopped. Retain completed reference records: ' . wp_json_encode( $created ) . '. ' . $error->getMessage(), 0, $error );
							}
						}
					);
					if ( ! $locked ) {
						throw new \RuntimeException( 'Another cable adoption owns the native maintenance lock.' );
					}
					$result['references'] = $created;
				}
				$fresh = Publication::manifest();
				foreach ( $result['references'] as &$reference ) {
					$reference['ready'] = $reference['product_id'] > 0 && Publication::is_published( $reference['product_id'] ) && null !== \Linker\Commerce\Products\Publication\CableFacts::projection( $reference['product_id'], $fresh );
				}
				unset( $reference );
				if ( $apply ) {
					$unready = array_values( array_filter( $result['references'], static fn( array $reference ): bool => ! $reference['ready'] ) );
					if ( array() !== $unready ) {
						// phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- CLI recovery record, not rendered public content.
						throw new \RuntimeException( 'Cable adoption is incomplete. Preserve and inspect these Woo reference IDs; rerunning never republishes a draft: ' . wp_json_encode( array_column( $unready, 'product_id' ) ) . '. Withdraw only newly adopted records to leave the current feed; do not delete originals or overwrite existing Woo maintenance.' );
					}
				}
			}
			\WP_CLI::log( (string) wp_json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
		} catch ( \RuntimeException $error ) {
			\WP_CLI::error( $error->getMessage() );
		}
	}

	/** Print the current public manifest. */
	public function manifest(): void {
		\WP_CLI::log( (string) wp_json_encode( Publication::manifest(), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
	}

	/** Reconcile current preparation jobs. */
	public function reconcile(): void {
		( new PreparationJobs() )->reconcile();
		\WP_CLI::success( 'Current preparation jobs reconciled.' );
	}

	/**
	 * Preview or abandon one confirmed interrupted knowledge lease.
	 *
	 * ## OPTIONS
	 *
	 * --job-id=<sha256>
	 * : Exact observed knowledge job identity.
	 * --source-revision=<sha256>
	 * : Exact observed and current Woo source revision.
	 * --recipe-revision=<sha256>
	 * : Exact observed compiler identity.
	 * --activation-epoch=<epoch>
	 * : Exact observed positive activation epoch.
	 * --worker-id=<worker>
	 * : Exact worker independently verified to have stopped.
	 * [--confirm-worker-stopped]
	 * : Required with --apply; confirm the exact worker no longer runs.
	 * [--apply]
	 * : Apply the previewed cancellation; otherwise do not write.
	 *
	 * @subcommand abandon-interrupted-knowledge
	 * @param array<int,string>   $args       Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 */
	public function abandon_interrupted_knowledge( array $args, array $assoc_args ): void {
		unset( $args );
		$epoch = $assoc_args['activation-epoch'] ?? '';
		if ( ! is_string( $epoch ) || ! ctype_digit( $epoch ) || (int) $epoch < 1 || (string) (int) $epoch !== $epoch ) {
			\WP_CLI::error( 'The activation epoch must be the exact observed positive integer.' );
		}
		$result = ( new PreparationJobs() )->abandon_interrupted_knowledge(
			(string) ( $assoc_args['job-id'] ?? '' ),
			(string) ( $assoc_args['source-revision'] ?? '' ),
			(string) ( $assoc_args['recipe-revision'] ?? '' ),
			(int) $epoch,
			(string) ( $assoc_args['worker-id'] ?? '' ),
			true === ( $assoc_args['confirm-worker-stopped'] ?? false ),
			true === ( $assoc_args['apply'] ?? false )
		);
		if ( $result instanceof \WP_Error ) {
			\WP_CLI::error( $result->get_error_code() . ': ' . $result->get_error_message() );
		}
		\WP_CLI::log( (string) wp_json_encode( $result, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
	}

	/**
	 * Bind the current existing published Woo facts once, preserving later stale bindings.
	 *
	 * @subcommand bind-figures
	 */
	public function bind_figures(): void {
		foreach ( Publication::manifest()['products'] as $product ) {
			\Linker\Commerce\Products\Publication\EvidenceBindings::capture( $product['product_id'], true );
			\Linker\Commerce\Products\Publication\EvidenceBindings::capture_faqs( $product['product_id'], true );
		}
		( new PreparationJobs() )->changed();
		\WP_CLI::success( 'Existing published Woo figure sources bound; existing bindings preserved.' );
	}

	/**
	 * Install and read back the native PDF gate.
	 *
	 * @subcommand install-gate
	 */
	public function install_gate(): void {
		require_once ABSPATH . 'wp-admin/includes/misc.php';
		require_once ABSPATH . 'wp-admin/includes/file.php';
		if ( ! save_mod_rewrite_rules() ) {
			\WP_CLI::error( 'Cannot install native WordPress rewrite rules.' );
		}
		$file     = get_home_path() . '.htaccess';
		$rules    = file_get_contents( $file ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- read back the installed rewrite block.
		$gate     = is_string( $rules ) ? strpos( $rules, 'linker_public_document=' ) : false;
		$shortcut = is_string( $rules ) ? strpos( $rules, 'REQUEST_FILENAME' ) : false;
		if ( false === $gate || ( false !== $shortcut && $gate > $shortcut ) ) {
			\WP_CLI::error( 'Document gate does not precede the static-file shortcut.' );
		}
		( new PreparationJobs() )->changed();
		\WP_CLI::success( 'Installed and read back the document gate; existing out-of-block rules retained.' );
	}
}
