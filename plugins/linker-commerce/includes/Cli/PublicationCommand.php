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
