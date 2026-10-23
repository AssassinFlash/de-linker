<?php
/**
 * Guarded historical staff disposition; run only through native wp eval-file --user=STAFF.
 *
 * Usage: wp --user=STAFF eval-file tools/security/568-disposition.php MODE MANIFEST UUID SHA256
 * MODE is preflight (default), apply, or rollback. Manifest and output stay private.
 * Each entry commits independently. An unconfirmed entry stops the batch; never report all done.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

use Linker\Commerce\Protection\BusinessDisposition;
use Linker\Commerce\Protection\Campaign;
use Linker\Commerce\Inquiry\Assessment\CurrentSource;
use Linker\Commerce\Inquiry\Assessment\Reviews;
use Linker\Commerce\Protection\Intake;

if ( ! defined( 'WP_CLI' ) || ! WP_CLI || ! current_user_can( 'manage_woocommerce' ) ) {
	throw new RuntimeException( 'Staff WP-CLI context required.' );
}
$linker_commerce_disposition_args      = isset( $args ) && is_array( $args ) ? $args : array();
$linker_commerce_disposition_mode      = $linker_commerce_disposition_args[0] ?? 'preflight';
$linker_commerce_disposition_path      = $linker_commerce_disposition_args[1] ?? '';
$linker_commerce_disposition_operation = $linker_commerce_disposition_args[2] ?? '';
$linker_commerce_disposition_sha       = $linker_commerce_disposition_args[3] ?? '';
// Approved immutable incident evidence. The current detector must independently
// match every native body; a newer detector version never rewrites this manifest.
$linker_commerce_disposition_approved = '451978ea1d1be0901d37e8a4302c00e1cbb973d7092c012b7b348ebc29977eee';
if ( ! in_array( $linker_commerce_disposition_mode, array( 'preflight', 'apply', 'rollback' ), true ) || ! wp_is_uuid( $linker_commerce_disposition_operation, 4 ) || ! is_file( $linker_commerce_disposition_path ) || ! hash_equals( $linker_commerce_disposition_approved, $linker_commerce_disposition_sha ) || ! hash_equals( $linker_commerce_disposition_sha, (string) hash_file( 'sha256', $linker_commerce_disposition_path ) ) ) {
	WP_CLI::error( 'Invalid mode, private manifest, operation UUID or approved SHA256.' );
}
$linker_commerce_disposition_manifest = json_decode( (string) file_get_contents( $linker_commerce_disposition_path ), true ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Approved SHA-bound private local manifest, never remote HTTP.
if ( ! is_array( $linker_commerce_disposition_manifest ) || 1 !== ( $linker_commerce_disposition_manifest['schema'] ?? null ) || BusinessDisposition::EXCLUDED_CONTROL !== ( $linker_commerce_disposition_manifest['excluded_control'] ?? null ) || 'transfer-fredmer-20261022-v1' !== ( $linker_commerce_disposition_manifest['rule'] ?? null ) || 'd449cea25020922f412eeadeae2e13fa3bd83c3bd9295905c4eb61ea0a94e55c' !== ( $linker_commerce_disposition_manifest['snapshot_sha256'] ?? null ) || ! is_array( $linker_commerce_disposition_manifest['entries'] ?? null ) || BusinessDisposition::MAXIMUM !== count( $linker_commerce_disposition_manifest['entries'] ) ) {
	WP_CLI::error( 'Expected the independently verified fixed 87-entry incident manifest.' );
}
$linker_commerce_disposition_seen = array();
foreach ( $linker_commerce_disposition_manifest['entries'] as $linker_commerce_disposition_entry ) {
	$linker_commerce_disposition_id    = is_array( $linker_commerce_disposition_entry ) ? ( $linker_commerce_disposition_entry['order'] ?? 0 ) : 0;
	$linker_commerce_disposition_order = is_int( $linker_commerce_disposition_id ) ? CurrentSource::order( $linker_commerce_disposition_id ) : null;
	if ( ! $linker_commerce_disposition_order instanceof WC_Order || BusinessDisposition::EXCLUDED_CONTROL === $linker_commerce_disposition_id || isset( $linker_commerce_disposition_seen[ $linker_commerce_disposition_id ] ) || ! is_string( $linker_commerce_disposition_entry['message_sha256'] ?? null ) || ! hash_equals( $linker_commerce_disposition_entry['message_sha256'], hash( 'sha256', BusinessDisposition::body( $linker_commerce_disposition_order ) ) ) || ! hash_equals( $linker_commerce_disposition_entry['customer_note_sha256'], hash( 'sha256', $linker_commerce_disposition_order->get_customer_note() ) ) || $linker_commerce_disposition_entry['source'] !== $linker_commerce_disposition_order->get_meta( '_linker_inquiry_source' ) || ! $linker_commerce_disposition_order->has_status( $linker_commerce_disposition_entry['status'] ) || $linker_commerce_disposition_order->get_meta( Intake::META ) || $linker_commerce_disposition_order->get_meta( Reviews::ERASED ) || ! Campaign::matches( BusinessDisposition::body( $linker_commerce_disposition_order ) ) ) {
		WP_CLI::error( 'Preflight source changed; no batch writes were attempted.' );
	}
	$linker_commerce_disposition_seen[ $linker_commerce_disposition_id ] = true;
}
WP_CLI::log(
	(string) wp_json_encode(
		array(
			'mode'             => $linker_commerce_disposition_mode,
			'operation'        => $linker_commerce_disposition_operation,
			'manifest_sha256'  => $linker_commerce_disposition_sha,
			'historical_rule'  => $linker_commerce_disposition_manifest['rule'],
			'current_rule'     => Campaign::VERSION,
			'verified'         => count( $linker_commerce_disposition_seen ),
			'actor'            => get_current_user_id(),
			'excluded_control' => BusinessDisposition::EXCLUDED_CONTROL,
		)
	)
);
if ( 'preflight' === $linker_commerce_disposition_mode ) {
	return;
}
$linker_commerce_disposition_done = 0;
foreach ( $linker_commerce_disposition_manifest['entries'] as $linker_commerce_disposition_entry ) {
	$linker_commerce_disposition_result = BusinessDisposition::run( $linker_commerce_disposition_entry['order'], $linker_commerce_disposition_entry['message_sha256'], $linker_commerce_disposition_operation, 'rollback' === $linker_commerce_disposition_mode );
	if ( $linker_commerce_disposition_result instanceof WP_Error ) {
		WP_CLI::error(
			(string) wp_json_encode(
				array(
					'operation'         => $linker_commerce_disposition_operation,
					'confirmed_entries' => $linker_commerce_disposition_done,
					'unconfirmed_order' => $linker_commerce_disposition_entry['order'],
					'code'              => $linker_commerce_disposition_result->get_error_code(),
					'detail'            => $linker_commerce_disposition_result->get_error_message(),
				)
			)
		);
	}
	++$linker_commerce_disposition_done;
	WP_CLI::log( (string) wp_json_encode( $linker_commerce_disposition_result ) );
}
WP_CLI::success(
	(string) wp_json_encode(
		array(
			'operation'         => $linker_commerce_disposition_operation,
			'confirmed_entries' => $linker_commerce_disposition_done,
			'mode'              => $linker_commerce_disposition_mode,
		)
	)
);
