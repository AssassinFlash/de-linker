<?php
/**
 * Search terms and additional product answers for the document library.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\DocumentLibrary;

/** Public index loaded when the reader searches or opens another answer page. */
final class LibraryIndexEndpoint {
	/** Register both language editions on one URL. */
	public static function register(): void {
		register_rest_route(
			'linker/v1',
			'/library-index',
			array(
				'methods'             => 'GET',
				'permission_callback' => '__return_true',
				'callback'            => array( self::class, 'response' ),
				'args'                => array(
					'lang' => array(
						'type'    => 'string',
						'default' => 'en',
						'enum'    => array( 'en', 'de' ),
					),
				),
			)
		);
	}

	/**
	 * Read the same published product rows as the SSR register.
	 *
	 * @param \WP_REST_Request $request Validated language.
	 */
	public static function response( \WP_REST_Request $request ): \WP_REST_Response {
		$lang    = 'de' === $request->get_param( 'lang' ) ? 'de' : 'en';
		$entries = ( new DocumentLibrary() )->entries( $lang );
		$skus    = array();
		foreach ( $entries['documents'] as $document ) {
			$terms                    = array_unique( array_merge( array_keys( $document['skus'] ), $document['covers'] ) );
			$skus[ $document['url'] ] = array_values( $terms );
		}
		$faqs  = array();
		$shown = array();
		foreach ( $entries['answers'] as $answer ) {
			$key           = 'linker-library-answers-' . sanitize_title( $answer['brand'] );
			$shown[ $key ] = ( $shown[ $key ] ?? 0 ) + 1;
			if ( $shown[ $key ] > LibraryPage::FAQ_SSR_PAGE_SIZE ) {
				unset( $answer['brand'] );
				$faqs[ $key ][] = $answer;
			}
		}
		$response = new \WP_REST_Response(
			array(
				'skus'      => (object) $skus,
				'extraFaqs' => (object) $faqs,
			)
		);
		$response->header( 'Cache-Control', 'public, max-age=3600, stale-while-revalidate=600' );
		$response->header( 'X-LiteSpeed-Cache-Control', 'public, max-age=3600' );
		$response->header( 'X-Robots-Tag', 'noindex, nofollow' );
		do_action( 'litespeed_tag_add', 'PT.product' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed purges the index with published products.
		return $response;
	}
}
