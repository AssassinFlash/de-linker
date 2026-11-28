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
		$response->header( 'X-Robots-Tag', 'noindex, nofollow' );
		self::cache_policy( $request, $response, $lang );
		return $response;
	}

	/**
	 * Only the public index URL requested by the library opts into the shared origin cache.
	 *
	 * @param \WP_REST_Request  $request  REST request.
	 * @param \WP_REST_Response $response Index response.
	 * @param string            $lang     Index language.
	 */
	private static function cache_policy( \WP_REST_Request $request, \WP_REST_Response $response, string $lang ): void {
		// phpcs:disable WordPress.Security.ValidatedSanitizedInput.InputNotSanitized -- Compare the literal external GET and its only allowed query parameter.
		$uri    = wp_unslash( $_SERVER['REQUEST_URI'] ?? '' );
		$method = wp_unslash( $_SERVER['REQUEST_METHOD'] ?? '' );
		// phpcs:enable
		$cookies   = (string) $request->get_header( 'cookie' );
		$private   = preg_match( '/(?:^|;\s*)(?:wordpress_(?:logged_in_[^=;]+|sec_[^=;]+|[a-f0-9]{32})|wp-postpass_[^=;]+|wp_woocommerce_session_[^=;]+|woocommerce_(?:items_in_cart|cart_hash))=/', $cookies );
		$canonical = wp_parse_url( rest_url( 'linker/v1/library-index' ), PHP_URL_PATH ) . '?lang=' . $lang;
		if ( $uri !== $canonical || 'GET' !== $method || is_user_logged_in() || $private || $request->get_header( 'authorization' ) || $request->get_header( 'x-wp-nonce' ) || isset( $_SERVER['PHP_AUTH_USER'] ) || ! empty( $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ) ) {
			$response->header( 'Cache-Control', 'private, no-store, max-age=0' );
			$response->header( 'X-LiteSpeed-Cache-Control', 'no-cache' );
			return;
		}

		$response->header( 'Cache-Control', 'public, max-age=3600, stale-while-revalidate=600' );
		$response->header( 'X-LiteSpeed-Cache-Control', 'public, max-age=3600' );
		// phpcs:disable WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed finalizes the origin policy after the REST response.
		do_action( 'litespeed_tag_add', 'PT.product' );
		do_action( 'litespeed_control_force_public', 'Public library index' );
		do_action( 'litespeed_control_set_ttl', HOUR_IN_SECONDS );
		// phpcs:enable
	}
}
