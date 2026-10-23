<?php
/**
 * Two real HTTP worker publication-race harness, local fixtures only.
 *
 * @package Linker\Commerce
 */

if ( 'local' !== wp_get_environment_type() ) {
	return;
}
add_action(
	'rest_api_init',
	static function (): void {
		register_rest_route(
			'linker-fixture/v1',
			'/publication-race',
			array(
				'methods'             => 'POST',
				'permission_callback' => '__return_true',
				'callback'            => static function ( WP_REST_Request $request ): array {
					$state = get_option( 'linker_publication_fixture', array() );
					$id = $state['ids'][0];
					$mode = $request->get_param( 'mode' );
					$signal = get_temp_dir() . '/linker-publication-race-' . md5( home_url() );
					if ( 'describe' === $mode ) {
						return array( 'signal' => $signal );
					}
					if ( 'hold' === $mode ) {
						$manifest = \Linker\Commerce\Products\Publication::manifest();
						$products = array_column( $manifest['products'], null, 'product_id' );
						$dependencies = array(
							'products'  => array(
								array(
									'product_id'       => $id,
									'product_revision' => $products[ $id ]['product_revision'],
								),
							),
							'documents' => array(),
						);
						// Prime the same process's native post and metadata caches too.
						get_post_status( $id );
						get_post_meta( $id, '_linker_documents', true );
						file_put_contents( $signal, 'waiting' );
						$deadline = microtime( true ) + 20;
						while ( microtime( true ) < $deadline && 'changed' !== file_get_contents( $signal ) ) {
							usleep( 10000 );
						}
						$result = \Linker\Commerce\Products\Publication::validate( $dependencies );
						unlink( $signal );
						return array(
							'valid_after_external_change' => $result['valid'],
							'invalid'                     => $result['invalid'],
							'worker'                      => getmypid(),
						);
					}
					if ( 'waiting' === $mode ) {
						return array( 'waiting' => is_file( $signal ) && 'waiting' === file_get_contents( $signal ) );
					}
					if ( 'document' === $mode ) {
						update_post_meta( $id, '_linker_documents', array() );
					} elseif ( 'product' === $mode ) {
						wp_update_post(
							array(
								'ID'          => $id,
								'post_status' => 'draft',
							)
						);
					} elseif ( 'restore' === $mode ) {
						wp_update_post(
							array(
								'ID'          => $id,
								'post_status' => 'publish',
							)
						);
						wp_update_post(
							array(
								'ID'          => $state['ids'][1],
								'post_status' => 'publish',
							)
						);
						pll_save_post_translations(
							array(
								'en' => $id,
								'de' => $state['ids'][1],
							)
						);
						update_post_meta(
							$id,
							'_linker_documents',
							array(
								array(
									'url'     => $state['urls']['shared'],
									'title'   => 'Fixture manual',
									'type'    => 'manual',
									'lang'    => 'en',
									'aliases' => array( $state['urls']['alias'] ),
								),
							)
						);
					} elseif ( 'mirror' === $mode ) {
						wp_update_post(
							array(
								'ID'          => $id,
								'post_status' => 'draft',
							)
						);
						wp_update_post(
							array(
								'ID'          => $state['ids'][1],
								'post_status' => 'publish',
							)
						);
					}
					if ( is_file( $signal ) ) {
						file_put_contents( $signal, 'changed' );
					}
					return array(
						'changed' => true,
						'worker'  => getmypid(),
					);
				},
			)
		);
	}
);
