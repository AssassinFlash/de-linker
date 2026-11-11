<?php
/**
 * Install/read back the native document gate and reconcile pending preparation.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Cli;

use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\EngineLoadedState;
use Linker\Commerce\Products\Publication\GenieLoadedState;
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
	 * Acknowledge the generation this instance's own engine actually loaded.
	 *
	 * A pulled instance rewrites every upload address, so renewing the evidence
	 * bindings changes every product revision; the receipts a production worker
	 * left behind then name a generation that no longer exists, and no local
	 * process acknowledges the new one. Planning rejects every selection on such
	 * an instance (`product_evidence_changed`) until someone does.
	 *
	 * The engine loaded the current feed from this site, and its authenticated
	 * readback is the same evidence the production preparation worker
	 * acknowledges with — a local engine's loaded state grants this instance's
	 * readiness under that same trust. Only the products the engine reports as
	 * loaded are acknowledged; the native ACK still verifies every revision
	 * against the current source and refuses anything else.
	 *
	 * ## OPTIONS
	 *
	 * --engine=<url>
	 * : Base URL of the engine that loaded this instance's feed, e.g. http://127.0.0.1:8890.
	 *
	 * [--consumer=<consumer>]
	 * : Only engineering is supported: knowledge readiness needs a recipe-aware
	 *   index generation (recipe_revision, index_version, model identity) that an
	 *   engine readback cannot supply.
	 *
	 * @subcommand ack-engineering
	 * @param array<int,string>   $args       Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 */
	public function ack_engineering( array $args, array $assoc_args ): void {
		unset( $args );
		$consumer = (string) ( $assoc_args['consumer'] ?? 'engineering' );
		if ( 'engineering' !== $consumer ) {
			\WP_CLI::error(
				sprintf(
					'unsupported_consumer: an engine readback can only acknowledge engineering; %s readiness is acknowledged from the index Genie itself opened, with `publication ack-knowledge --genie=<url>`.',
					$consumer
				)
			);
		}
		$engine = $assoc_args['engine'] ?? '';
		if ( ! is_string( $engine ) || '' === $engine ) {
			\WP_CLI::error( 'invalid_engine_url: --engine=<url> is required, e.g. http://127.0.0.1:8890.' );
		}
		$loaded = EngineLoadedState::read( $engine );
		if ( $loaded instanceof \WP_Error ) {
			\WP_CLI::error( $loaded->get_error_code() . ': ' . $loaded->get_error_message() );
		}
		$manifest = Publication::manifest();
		$report   = array(
			'engine'                        => rtrim( $engine, '/' ),
			'engine_version'                => $loaded['version'],
			'consumer'                      => $consumer,
			'claim'                         => 'none',
			'source_revision'               => $manifest['source_revision'],
			'loaded_source_revision'        => $loaded['source_revision'],
			'compatibility_revision'        => $manifest['compatibility_revision'],
			'loaded_compatibility_revision' => $loaded['compatibility_revision'],
			'products'                      => $this->loaded_products_difference( $manifest, $loaded['products'] ),
		);
		if ( $loaded['source_revision'] !== $manifest['source_revision'] ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error(
				sprintf(
					'engine_source_mismatch: the engine loaded %s, this site publishes %s; nothing was acknowledged.',
					$loaded['source_revision'],
					$manifest['source_revision']
				)
			);
		}
		$jobs  = new PreparationJobs();
		$claim = $jobs->claim( $consumer, 'cli-ack-' . getmypid(), 120 );
		if ( $claim instanceof \WP_Error ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error( 'claim_failed: ' . $claim->get_error_code() . ': ' . $claim->get_error_message() );
		}
		$job = $claim['job'] ?? null;
		if ( null === $job ) {
			// An earlier ACK already covers this source, or another worker holds
			// the live lease; neither is this invocation's to change.
			$state                  = get_option( PreparationJobs::OPTION, array() );
			$current                = is_array( $state ) ? ( $state['engineering'] ?? array() ) : array();
			$report['claim']        = 'not_claimed';
			$report['acknowledged'] = $this->acknowledged( $manifest );
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			if ( 'ready' === ( $current['status'] ?? '' ) ) {
				\WP_CLI::success(
					sprintf(
						'engineering is already acknowledged for this source: %d of %d products ready.',
						$report['acknowledged'],
						$report['products']['expected']
					)
				);
				return;
			}
			\WP_CLI::error(
				sprintf(
					'job_not_claimable: the engineering job is %s with a lease until %d; nothing was acknowledged.',
					(string) ( $current['status'] ?? 'unknown' ),
					(int) ( $current['lease_expires_at'] ?? 0 )
				)
			);
		}
		$ack = $jobs->acknowledge(
			array(
				'job_id'            => $job['job_id'],
				'lease_token'       => $job['lease_token'],
				'source_revision'   => $job['source_revision'],
				'loaded_revision'   => $loaded['source_revision'],
				'prepared_products' => $loaded['products'],
				'status'            => 'ready',
			)
		);
		if ( $ack instanceof \WP_Error ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error( 'ack_rejected: ' . $ack->get_error_code() . ': ' . $ack->get_error_message() );
		}
		$report['claim']        = 'acknowledged';
		$report['ack']          = $ack;
		$report['acknowledged'] = $this->acknowledged( $manifest );
		\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
		if ( true !== ( $ack['complete'] ?? false ) ) {
			\WP_CLI::error(
				sprintf(
					'acknowledgement_incomplete: the engine loaded %d of %d current products; the receipt is recorded but readiness stays below the source.',
					$report['products']['loaded'],
					$report['products']['expected']
				)
			);
		}
		\WP_CLI::success(
			sprintf(
				'engineering ready for %d of %d current products from the generation the engine loaded.',
				$report['acknowledged'],
				$report['products']['expected']
			)
		);
	}

	/**
	 * How the engine's loaded products differ from the current source.
	 *
	 * @param array<string,mixed>                                 $manifest Current source.
	 * @param list<array{product_id:int,product_revision:string}> $loaded Engine readback.
	 * @return array{expected:int,loaded:int,matching:int,stale:list<int>,missing:list<int>,unknown:list<int>}
	 */
	private function loaded_products_difference( array $manifest, array $loaded ): array {
		$expected = array_column( $manifest['products'], 'product_revision', 'product_id' );
		$matching = 0;
		$stale    = array();
		$unknown  = array();
		$seen     = array();
		foreach ( $loaded as $product ) {
			$id     = $product['product_id'];
			$seen[] = $id;
			if ( ! isset( $expected[ $id ] ) ) {
				$unknown[] = $id;
			} elseif ( $expected[ $id ] === $product['product_revision'] ) {
				++$matching;
			} else {
				$stale[] = $id;
			}
		}
		return array(
			'expected' => count( $expected ),
			'loaded'   => count( $loaded ),
			'matching' => $matching,
			'stale'    => $stale,
			'missing'  => array_values( array_map( 'intval', array_diff( array_keys( $expected ), $seen ) ) ),
			'unknown'  => $unknown,
		);
	}

	/**
	 * Acknowledge the knowledge generation this instance's own Genie actually opened.
	 *
	 * Knowledge readiness is recipe-aware: its receipt names the compiler
	 * (`recipe_revision`), the index generation (`index_version`), the serving
	 * rules the process runs and the native model identity. An engine's feed
	 * readback carries none of them, so the only local evidence is Genie's own
	 * authenticated `/knowledge/loaded`, which reports exactly the index that
	 * process has open — the same readback the production preparation worker
	 * acknowledges from.
	 *
	 * A build from another source, another model identity or another set of
	 * serving rules is refused here, before any claim; `acknowledge()` then
	 * verifies every field and every product revision against the current source.
	 *
	 * A locally prebuilt index is not compiled inside a preparation lease, so the
	 * receipt names the claimed lease's activation epoch, not the epoch recorded
	 * in the index. The index's own epoch is reported for the operator and never
	 * sent as the receipt's.
	 *
	 * ## OPTIONS
	 *
	 * --genie=<url>
	 * : Base URL of the Genie process that opened this index, e.g. http://127.0.0.1:8891.
	 *
	 * [--worker-id=<id>]
	 * : Claim owner recorded on the lease; defaults to this invocation.
	 *
	 * @subcommand ack-knowledge
	 * @param array<int,string>   $args       Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 */
	public function ack_knowledge( array $args, array $assoc_args ): void {
		unset( $args );
		$genie = $assoc_args['genie'] ?? '';
		if ( ! is_string( $genie ) || '' === $genie ) {
			\WP_CLI::error( 'invalid_genie_url: --genie=<url> is required, e.g. http://127.0.0.1:8891.' );
		}
		$loaded = GenieLoadedState::read( $genie );
		if ( $loaded instanceof \WP_Error ) {
			\WP_CLI::error( $loaded->get_error_code() . ': ' . $loaded->get_error_message() );
		}
		$manifest = Publication::manifest();
		$report   = array(
			'genie'                          => rtrim( $genie, '/' ),
			'consumer'                       => 'knowledge',
			'claim'                          => 'none',
			'source_revision'                => $manifest['source_revision'],
			'loaded_source_revision'         => $loaded['source_revision'],
			'model_identity_revision'        => $manifest['model_identity_revision'],
			'loaded_model_identity_revision' => $loaded['model_identity_revision'],
			'recipe_revision'                => $loaded['recipe_revision'],
			'index_version'                  => $loaded['index_version'],
			'expected_serving_revision'      => $loaded['expected_serving_revision'],
			'serving_revision'               => $loaded['serving_revision'],
			'index_activation_epoch'         => $loaded['activation_epoch'],
			'materialization_complete'       => $loaded['materialization_complete'],
			'preparation_complete'           => $loaded['preparation_complete'],
			'unprepared_documents'           => count( $loaded['unprepared_documents'] ),
			'products'                       => $this->knowledge_products_difference( $manifest, $loaded['products'] ),
		);
		$expected = $this->knowledge_expected_products( $manifest );
		if ( $loaded['source_revision'] !== $manifest['source_revision'] ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error(
				sprintf(
					'genie_source_mismatch: Genie loaded %s, this site publishes %s; the index was built from another source, so nothing was acknowledged.',
					$loaded['source_revision'],
					$manifest['source_revision']
				)
			);
		}
		if ( $loaded['model_identity_revision'] !== $manifest['model_identity_revision'] ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error(
				sprintf(
					'genie_identity_mismatch: Genie loaded model identity %s, this site publishes %s; nothing was acknowledged.',
					$loaded['model_identity_revision'],
					$manifest['model_identity_revision']
				)
			);
		}
		if ( array() !== $report['products']['stale'] || array() !== $report['products']['unknown'] ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error(
				sprintf(
					'genie_products_stale: the index carries %d stale and %d unknown product revisions; rebuild it from this site\'s current manifest. Nothing was acknowledged.',
					count( $report['products']['stale'] ),
					count( $report['products']['unknown'] )
				)
			);
		}
		$jobs = new PreparationJobs();
		if ( $this->knowledge_receipt_names_loaded( $manifest, $loaded, $expected ) ) {
			$report['claim']        = 'not_claimed';
			$report['acknowledged'] = $this->knowledge_acknowledged( $manifest );
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::success(
				sprintf(
					'knowledge is already acknowledged for this generation: %d of %d products ready.',
					$report['acknowledged'],
					$report['products']['expected']
				)
			);
			return;
		}
		$worker = (string) ( $assoc_args['worker-id'] ?? 'cli-knowledge-' . getmypid() );
		$claim  = $jobs->claim( 'knowledge', $worker, 120, $loaded['recipe_revision'], $loaded );
		if ( $claim instanceof \WP_Error ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error( 'claim_failed: ' . $claim->get_error_code() . ': ' . $claim->get_error_message() );
		}
		$job = $claim['job'] ?? null;
		if ( null === $job ) {
			$state                  = get_option( PreparationJobs::OPTION, array() );
			$current                = is_array( $state ) ? ( $state['knowledge'] ?? array() ) : array();
			$report['claim']        = 'not_claimed';
			$report['acknowledged'] = $this->knowledge_acknowledged( $manifest );
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error(
				sprintf(
					'job_not_claimable: the knowledge job is %s with a lease until %d; nothing was acknowledged.',
					(string) ( $current['status'] ?? 'unknown' ),
					(int) ( $current['lease_expires_at'] ?? 0 )
				)
			);
		}
		$ack = $jobs->acknowledge(
			array(
				'job_id'                         => $job['job_id'],
				'lease_token'                    => $job['lease_token'],
				'source_revision'                => $job['source_revision'],
				'loaded_revision'                => $loaded['source_revision'],
				'loaded_model_identity_revision' => $loaded['model_identity_revision'],
				'model_identity_revision'        => $loaded['model_identity_revision'],
				'prepared_products'              => $loaded['products'],
				'status'                         => 'ready',
				'error'                          => $loaded['preparation_complete'] && array() === $loaded['unprepared_documents'] && array() === $report['products']['missing']
					? ''
					: 'Some current document associations still lack proven passages.',
				'preparation_complete'           => $loaded['preparation_complete'],
				'materialization_complete'       => $loaded['materialization_complete'],
				'unprepared_documents'           => $loaded['unprepared_documents'],
				'recipe_revision'                => $loaded['recipe_revision'],
				'loaded_recipe_revision'         => $loaded['recipe_revision'],
				'index_version'                  => $loaded['index_version'],
				'expected_serving_revision'      => $loaded['expected_serving_revision'],
				'serving_revision'               => $loaded['serving_revision'],
				'activation_epoch'               => (int) ( $job['activation_epoch'] ?? 0 ),
			)
		);
		if ( $ack instanceof \WP_Error ) {
			\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
			\WP_CLI::error( 'ack_rejected: ' . $ack->get_error_code() . ': ' . $ack->get_error_message() );
		}
		$report['claim']        = 'acknowledged';
		$report['ack']          = $ack;
		$report['acknowledged'] = $this->knowledge_acknowledged( $manifest );
		\WP_CLI::log( (string) wp_json_encode( $report, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES ) );
		if ( true !== ( $ack['complete'] ?? false ) ) {
			\WP_CLI::error(
				sprintf(
					'acknowledgement_incomplete: Genie loaded %d of %d knowledge products; the receipt is recorded but readiness stays below the source.',
					$report['products']['loaded'],
					$report['products']['expected']
				)
			);
		}
		\WP_CLI::success(
			sprintf(
				'knowledge ready for %d of %d current products from the generation Genie loaded (%s).',
				$report['acknowledged'],
				$report['products']['expected'],
				$loaded['index_version']
			)
		);
	}

	/**
	 * Whether the recorded knowledge receipt already names the loaded generation.
	 *
	 * The activation epoch is a lease fence for a worker's own build, not a
	 * generation identity: a locally built index was never compiled inside one.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 * @param array<string,mixed> $loaded Genie readback.
	 * @param array<int,string>   $expected Current knowledge product revisions.
	 */
	private function knowledge_receipt_names_loaded( array $manifest, array $loaded, array $expected ): bool {
		$state = get_option( PreparationJobs::OPTION, array() );
		$job   = is_array( $state ) ? ( $state['knowledge'] ?? array() ) : array();
		return 'ready' === ( $job['status'] ?? '' )
			&& ( $job['source_revision'] ?? '' ) === $manifest['source_revision']
			&& ( $job['loaded_revision'] ?? '' ) === $loaded['source_revision']
			&& ( $job['loaded_recipe_revision'] ?? '' ) === $loaded['recipe_revision']
			&& ( $job['index_version'] ?? '' ) === $loaded['index_version']
			&& ( $job['serving_revision'] ?? '' ) === $loaded['serving_revision']
			&& ( $job['loaded_model_identity_revision'] ?? '' ) === $manifest['model_identity_revision']
			&& $this->knowledge_acknowledged( $manifest ) === count( $expected );
	}

	/**
	 * Products whose knowledge receipt matches the current source and identity.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 */
	private function knowledge_acknowledged( array $manifest ): int {
		$count = 0;
		foreach ( $this->knowledge_expected_products( $manifest ) as $id => $revision ) {
			if ( PreparationJobs::readiness( $id, $revision, (string) $manifest['model_identity_revision'] )['knowledge'] ) {
				++$count;
			}
		}
		return $count;
	}

	/**
	 * Current product revisions a knowledge index must carry, excluding references.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 * @return array<int,string>
	 */
	private function knowledge_expected_products( array $manifest ): array {
		$expected = array();
		foreach ( $manifest['products'] as $product ) {
			if ( ! in_array( $product['engineering_role'] ?? '', \Linker\Commerce\Products\EngineeringReference::ROLES, true ) ) {
				$expected[ (int) $product['product_id'] ] = (string) $product['product_revision'];
			}
		}
		return $expected;
	}

	/**
	 * How the index's products differ from the current knowledge source.
	 *
	 * @param array<string,mixed>                                 $manifest Current source.
	 * @param list<array{product_id:int,product_revision:string}> $loaded Genie readback.
	 * @return array{expected:int,loaded:int,matching:int,stale:list<int>,missing:list<int>,unknown:list<int>}
	 */
	private function knowledge_products_difference( array $manifest, array $loaded ): array {
		$expected = $this->knowledge_expected_products( $manifest );
		$matching = 0;
		$stale    = array();
		$unknown  = array();
		$seen     = array();
		foreach ( $loaded as $product ) {
			$id     = $product['product_id'];
			$seen[] = $id;
			if ( ! isset( $expected[ $id ] ) ) {
				$unknown[] = $id;
			} elseif ( $expected[ $id ] === $product['product_revision'] ) {
				++$matching;
			} else {
				$stale[] = $id;
			}
		}
		return array(
			'expected' => count( $expected ),
			'loaded'   => count( $loaded ),
			'matching' => $matching,
			'stale'    => $stale,
			'missing'  => array_values( array_map( 'intval', array_diff( array_keys( $expected ), $seen ) ) ),
			'unknown'  => $unknown,
		);
	}

	/**
	 * Products whose engineering receipt matches the current source.
	 *
	 * @param array<string,mixed> $manifest Current source.
	 */
	private function acknowledged( array $manifest ): int {
		$count = 0;
		foreach ( $manifest['products'] as $product ) {
			if ( PreparationJobs::readiness( (int) $product['product_id'], (string) $product['product_revision'] )['engineering'] ) {
				++$count;
			}
		}
		return $count;
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
	 * Renew recorded evidence versions whose cited bytes did not change.
	 *
	 * `bind-figures` preserves every recorded binding, and a declaration holds
	 * the document version an editor confirmed. Both then keep a version that a
	 * pulled instance's URL rewrite moved, so the fact drops out of the
	 * engineering feed and every declaration reads as unconfirmed even though it
	 * cites the same bytes. This renews only those: the recorded document
	 * identity and blob must equal the current ones, so no value ever adopts a
	 * replaced file.
	 *
	 * ## OPTIONS
	 *
	 * [--dry-run]
	 * : Count the renewable entries without writing.
	 *
	 * @subcommand repair-bindings
	 * @param array<int,string>   $args Positional arguments.
	 * @param array<string,mixed> $assoc_args Native CLI options.
	 */
	public function repair_bindings( array $args, array $assoc_args ): void {
		unset( $args );
		$dry_run  = isset( $assoc_args['dry-run'] );
		$manifest = Publication::manifest();
		$figures  = array();
		$claims   = array();
		foreach ( $manifest['products'] as $product ) {
			$id    = (int) $product['product_id'];
			$count = \Linker\Commerce\Products\Publication\EvidenceBindings::repair_unchanged( $id, $dry_run );
			if ( $count > 0 ) {
				$figures[ $id ] = $count;
			}
			$count = \Linker\Commerce\Products\Publication\CompatibilityClaims::renew_unchanged( $id, $manifest, $dry_run );
			if ( $count > 0 ) {
				$claims[ $id ] = $count;
			}
		}
		$total = array_sum( $figures ) + array_sum( $claims );
		$count = (string) wp_json_encode(
			array(
				'figures'      => $figures,
				'declarations' => $claims,
			),
			JSON_PRETTY_PRINT
		);
		if ( $dry_run ) {
			\WP_CLI::log( $count );
			\WP_CLI::success(
				sprintf(
					'%d figure binding(s) and %d declaration(s) cite unchanged bytes and can be renewed.',
					array_sum( $figures ),
					array_sum( $claims )
				)
			);
			return;
		}
		if ( $total > 0 ) {
			( new PreparationJobs() )->changed();
		}
		\WP_CLI::log( $count );
		\WP_CLI::success(
			sprintf(
				'%d figure binding(s) and %d declaration(s) renewed; replaced files remain unbound.',
				array_sum( $figures ),
				array_sum( $claims )
			)
		);
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
