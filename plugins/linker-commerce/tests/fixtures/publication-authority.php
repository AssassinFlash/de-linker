<?php
/**
 * Real WordPress/Woo publication fixture; run only on a disposable local site.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Products\EngineeringData;
use Linker\Commerce\Products\EngineeringFeed;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentAccess;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\Publication\PreparationJobs;

if ( 'local' !== wp_get_environment_type() ) {
	throw new RuntimeException( 'Publication fixture requires a local environment.' );
}
$linker_publication_mode = $args[0] ?? 'verify';
$linker_publication_state = get_option( 'linker_publication_fixture', array() );
if ( 'withdraw' === $linker_publication_mode ) {
	foreach ( $linker_publication_state['ids'] as $linker_publication_id ) {
		wp_update_post( array( 'ID' => $linker_publication_id, 'post_status' => 'draft' ) );
	}
	echo wp_json_encode( array( 'withdrawn' => true, 'state' => $linker_publication_state ) );
	return;
}
if ( 'cleanup' === $linker_publication_mode ) {
	foreach ( $linker_publication_state['ids'] ?? array() as $linker_publication_id ) {
		wp_delete_post( $linker_publication_id, true );
	}
	foreach ( $linker_publication_state['files'] ?? array() as $linker_publication_file ) {
		wp_delete_file( $linker_publication_file );
	}
	delete_option( 'linker_publication_fixture' );
	delete_option( PreparationJobs::OPTION );
	echo wp_json_encode( array( 'cleaned' => true ) );
	return;
}
if ( array() !== $linker_publication_state ) {
	throw new RuntimeException( 'Clean the previous publication fixture first.' );
}
$linker_publication_checks = array();
$linker_publication_check = static function ( bool $condition, string $name ) use ( &$linker_publication_checks ): void {
	if ( ! $condition ) {
		throw new RuntimeException( 'FAIL: ' . $name );
	}
	$linker_publication_checks[] = $name;
};
$linker_publication_create = static function ( string $model, string $status, string $lang = 'en' ): int {
	$product = new WC_Product_Simple();
	$product->set_name( 'Publication fixture ' . $model );
	$product->set_status( $status );
	$id = $product->save();
	pll_set_post_language( $id, $lang );
	wp_set_object_terms( $id, $model, 'pa_model' );
	return $id;
};
if ( ! taxonomy_exists( 'pa_model' ) ) {
	wc_create_attribute( array( 'name' => 'Model', 'slug' => 'model' ) );
	register_taxonomy( 'pa_model', 'product', array( 'public' => true ) );
}
$linker_publication_a = $linker_publication_create( 'Fixture-A', 'publish' );
$linker_publication_de = $linker_publication_create( 'Fixture-A', 'publish', 'de' );
pll_save_post_translations( array( 'en' => $linker_publication_a, 'de' => $linker_publication_de ) );
$linker_publication_b = $linker_publication_create( 'Fixture-B', 'draft' );
$linker_publication_c = $linker_publication_create( 'Fixture-C', 'publish' );
$linker_publication_uploads = wp_upload_dir();
$linker_publication_directory = $linker_publication_uploads['basedir'] . '/publication-614';
wp_mkdir_p( $linker_publication_directory );
$linker_publication_bytes = "%PDF-1.4\nPublication fixture\n%%EOF\n";
$linker_publication_files = array();
$linker_publication_urls = array();
foreach ( array( 'shared', 'alias', 'unassociated', 'legacy', 'figure' ) as $linker_publication_name ) {
	$linker_publication_path = $linker_publication_directory . '/' . $linker_publication_name . '.pdf';
	file_put_contents( $linker_publication_path, $linker_publication_bytes );
	$linker_publication_files[] = $linker_publication_path;
	$linker_publication_urls[ $linker_publication_name ] = $linker_publication_uploads['baseurl'] . '/publication-614/' . $linker_publication_name . '.pdf';
}
$linker_publication_state = array( 'ids' => array( $linker_publication_a, $linker_publication_de, $linker_publication_b, $linker_publication_c ), 'files' => $linker_publication_files, 'urls' => $linker_publication_urls );
update_option( 'linker_publication_fixture', $linker_publication_state, false );
$linker_publication_row = array( 'url' => $linker_publication_urls['shared'], 'title' => 'Fixture manual', 'type' => 'manual', 'lang' => 'en', 'aliases' => array( $linker_publication_urls['alias'] ) );
update_post_meta( $linker_publication_a, EngineeringData::DOCUMENTS_META_KEY, array( $linker_publication_row ) );
update_post_meta( $linker_publication_b, EngineeringData::DOCUMENTS_META_KEY, array( $linker_publication_row ) );
update_post_meta( $linker_publication_c, '_delinker_datasheet_url', $linker_publication_urls['legacy'] );
update_post_meta( $linker_publication_c, \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY, array( 'rated_ac_power_kw' => array( 'value' => 10, 'unit' => 'kW', 'citation' => array( 'url' => $linker_publication_urls['figure'], 'page' => 1 ) ) ) );
$linker_publication_manifest = Publication::manifest();
$linker_publication_products = array_column( $linker_publication_manifest['products'], null, 'product_id' );
$linker_publication_documents = array_column( $linker_publication_manifest['documents'], null, 'document_id' );
$linker_publication_doc_id = DocumentFiles::id( $linker_publication_urls['shared'] );
$linker_publication_doc = $linker_publication_documents[ $linker_publication_doc_id ];
$linker_publication_a_revision = $linker_publication_products[ $linker_publication_a ]['product_revision'];
$linker_publication_dependencies = array( 'products' => array( array( 'product_id' => $linker_publication_a, 'product_revision' => $linker_publication_a_revision ) ), 'documents' => array( array( 'document_id' => $linker_publication_doc_id, 'document_revision' => $linker_publication_doc['document_revision'], 'product_id' => $linker_publication_a ) ), 'compatibility_revision' => $linker_publication_manifest['compatibility_revision'] );
$linker_publication_check( Publication::validate( $linker_publication_dependencies )['valid'], 'current dependency set validates' );
$linker_publication_check( ! isset( $linker_publication_products[ $linker_publication_b ] ), 'draft model absent from public manifest' );
$linker_publication_check( $linker_publication_doc['product_ids'] === array( $linker_publication_a ), 'shared manual grants only published A' );
$linker_publication_check( Publication::canonical_id( $linker_publication_de ) === $linker_publication_a, 'German mirror resolves canonical source' );
$linker_publication_check( 2 === count( $linker_publication_products[ $linker_publication_c ]['documents'] ), 'legacy datasheet and figure citations remain explicit Woo associations' );
$linker_publication_check( Publication::manifest()['source_revision'] === $linker_publication_manifest['source_revision'], 'source revision excludes generated time and readiness' );
$linker_publication_check( ! Publication::validate( array() )['valid'] && Publication::validate( array( 'products' => array(), 'documents' => array() ) )['valid'], 'missing scope rejects; explicit empty scope represents zero objects' );
$linker_publication_check( ! Publication::validate( array( 'products' => array( array( 'product_id' => array(), 'product_revision' => '' ) ), 'documents' => array() ) )['valid'], 'malformed public dependency fails closed' );
$linker_publication_access = new DocumentAccess();
$linker_publication_file = DocumentFiles::resolve( $linker_publication_urls['shared'] );
if ( null === $linker_publication_file ) {
	throw new RuntimeException( 'Fixture PDF cannot be resolved.' );
}
$linker_publication_check( 200 === $linker_publication_access->response( $linker_publication_file, 'GET' )['status'] && 200 === $linker_publication_access->response( $linker_publication_file, 'HEAD' )['status'], 'GET and HEAD authorize current document' );
$linker_publication_check( 206 === $linker_publication_access->response( $linker_publication_file, 'GET', 'bytes=0-4' )['status'] && 416 === $linker_publication_access->response( $linker_publication_file, 'GET', 'bytes=999999-' )['status'], 'single byte range supported and invalid range rejected' );
$linker_publication_check( 200 === $linker_publication_access->response( DocumentFiles::resolve( $linker_publication_urls['alias'] ), 'GET' )['status'], 'explicit same-content alias is authorized' );
$linker_publication_check( 410 === $linker_publication_access->response( DocumentFiles::resolve( $linker_publication_urls['unassociated'] ), 'GET' )['status'], 'same SHA unassociated alias receives no permission' );
$linker_publication_check( null === DocumentFiles::resolve( $linker_publication_uploads['baseurl'] . '/publication-614/../publication-614/shared.pdf' ) && null === DocumentFiles::resolve( 'https://example.com/shared.pdf' ), 'traversal and foreign hosts cannot resolve local files' );
wp_update_post( array( 'ID' => $linker_publication_b, 'post_status' => 'publish' ) );
$linker_publication_after = Publication::manifest();
$linker_publication_check( Publication::validate( $linker_publication_dependencies )['valid'], 'another product sharing unchanged PDF does not invalidate A' );
wp_update_post( array( 'ID' => $linker_publication_b, 'post_status' => 'draft' ) );
$linker_publication_check( Publication::validate( $linker_publication_dependencies )['valid'], 'withdrawing shared B preserves valid A dependencies' );
$linker_publication_jobs = new PreparationJobs();
$linker_publication_claim = $linker_publication_jobs->claim( 'knowledge', 'fixture-worker', 300 );
$linker_publication_check( ! is_wp_error( $linker_publication_claim ) && is_array( $linker_publication_claim['job'] ), 'current source automatically produces a persistent preparation lease' );
if ( is_wp_error( $linker_publication_claim ) ) {
	throw new RuntimeException( $linker_publication_claim->get_error_message() );
}
$linker_publication_job = $linker_publication_claim['job'];
$linker_publication_ack = array( 'job_id' => $linker_publication_job['job_id'], 'lease_token' => $linker_publication_job['lease_token'], 'source_revision' => $linker_publication_job['source_revision'], 'loaded_revision' => 'fixture-actually-loaded', 'status' => 'ready' );
$linker_publication_second_claim = $linker_publication_jobs->claim( 'knowledge', 'another-worker', 300 );
$linker_publication_check( ! is_wp_error( $linker_publication_second_claim ) && null === $linker_publication_second_claim['job'], 'live preparation lease prevents double claim' );
wp_update_post( array( 'ID' => $linker_publication_a, 'post_status' => 'draft' ) );
$linker_publication_check( ! Publication::is_published( $linker_publication_de ) && ! Publication::validate( $linker_publication_dependencies )['valid'], 'canonical withdrawal immediately blocks German mirror and old dependencies without a job' );
$linker_publication_check( 410 === $linker_publication_access->response( $linker_publication_file, 'GET' )['status'], 'last live relation withdrawal denies original bytes immediately' );
$linker_publication_check( is_wp_error( $linker_publication_jobs->acknowledge( $linker_publication_ack ) ), 'late preparation acknowledgement cannot restore withdrawn source' );
wp_update_post( array( 'ID' => $linker_publication_a, 'post_status' => 'publish' ) );
$linker_publication_current = Publication::manifest();
$linker_publication_before_bytes = array_column( $linker_publication_current['documents'], null, 'document_id' )[ $linker_publication_doc_id ]['document_revision'];
file_put_contents( $linker_publication_file['path'], $linker_publication_bytes . 'replacement' );
$linker_publication_changed = array_column( Publication::manifest()['documents'], null, 'document_id' )[ $linker_publication_doc_id ];
$linker_publication_check( $linker_publication_changed['document_revision'] !== $linker_publication_before_bytes && $linker_publication_changed['blob_sha256'] !== $linker_publication_doc['blob_sha256'], 'same URL changed bytes produces a new content revision' );
file_put_contents( $linker_publication_file['path'], $linker_publication_bytes );
$linker_publication_attachment = wp_insert_attachment( array( 'post_title' => 'Fixture manual', 'post_mime_type' => 'application/pdf', 'post_status' => 'inherit' ), $linker_publication_file['path'] );
update_attached_file( $linker_publication_attachment, $linker_publication_file['path'] );
update_post_meta( $linker_publication_attachment, '_linker_document_public', '0' );
$linker_publication_check( 410 === $linker_publication_access->response( $linker_publication_file, 'GET' )['status'], 'media withdrawal blocks every active relation' );
update_post_meta( $linker_publication_attachment, '_linker_document_public', '1' );
$linker_publication_state['ids'][] = $linker_publication_attachment;
update_option( 'linker_publication_fixture', $linker_publication_state, false );
$linker_publication_check( 10.0 === EngineeringFeed::item( $linker_publication_c )['ac_power_kw'], 'current numeric fact uses its bound document bytes' );
file_put_contents( $linker_publication_files[4], $linker_publication_bytes . 'updated figure PDF' );
$linker_publication_check( 'unknown' === EngineeringFeed::item( $linker_publication_c )['ac_power_kw'], 'same URL replacement cannot reauthorize old scalar figure values' );
update_post_meta( $linker_publication_c, \Linker\Commerce\Products\SelectionFacts::FIGURES_META_KEY, array( 'rated_ac_power_kw' => array( 'value' => 11, 'unit' => 'kW', 'citation' => array( 'url' => $linker_publication_urls['figure'], 'page' => 1 ) ) ) );
$linker_publication_check( 11.0 === EngineeringFeed::item( $linker_publication_c )['ac_power_kw'], 'normal Woo fact correction binds the newly edited fact to current bytes' );
$linker_publication_feed = EngineeringFeed::feed();
$linker_publication_feed_ids = array_column( $linker_publication_feed['products'], 'id' );
$linker_publication_check( in_array( $linker_publication_a, $linker_publication_feed_ids, true ) && ! in_array( $linker_publication_b, $linker_publication_feed_ids, true ) && ! in_array( $linker_publication_de, $linker_publication_feed_ids, true ), 'engineering feed emits one canonical published product and current document versions' );
$linker_publication_current_claim = $linker_publication_jobs->claim( 'knowledge', 'fixture-worker', 300 );
if ( is_wp_error( $linker_publication_current_claim ) ) {
	throw new RuntimeException( $linker_publication_current_claim->get_error_message() );
}
$linker_publication_current_job = $linker_publication_current_claim['job'];
$linker_publication_ready = $linker_publication_jobs->acknowledge( array( 'job_id' => $linker_publication_current_job['job_id'], 'lease_token' => $linker_publication_current_job['lease_token'], 'source_revision' => $linker_publication_current_job['source_revision'], 'loaded_revision' => 'fixture-current-loaded', 'status' => 'ready', 'prepared_products' => $linker_publication_current_job['manifest']['products'] ) );
$linker_publication_check( ! is_wp_error( $linker_publication_ready ) && ( Publication::product( $linker_publication_a )['ready']['knowledge'] ?? false ), 'current loaded receipt enables matching preparation state without changing permission' );
echo wp_json_encode( array( 'checks' => $linker_publication_checks, 'count' => count( $linker_publication_checks ), 'state' => $linker_publication_state, 'manifest' => Publication::manifest() ), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );
