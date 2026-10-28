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
