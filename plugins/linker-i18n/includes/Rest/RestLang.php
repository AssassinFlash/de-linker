<?php
/**
 * REST lists in one language.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n\Rest;

use Linker\I18n\Languages;

/**
 * Makes every REST answer one language's: lists hold the objects of the
 * language named by `?lang=`, else of the page making an internal request,
 * else English (`?lang=all` lists both), and the answer's texts (stock,
 * buttons, prices) are in that language's locale.
 *
 * Polylang's free edition only sets the current language from `?lang=` and
 * leaves lists unfiltered, so wp/v2, wc/v3 and the Store API would list
 * every product twice (docs/research/2026-10-09/i18n-opensource-replication.md
 * §2.2, §6.1). The language is a query parameter, never a header or cookie:
 * LiteSpeed caches REST answers by URL (§6.3).
 */
final class RestLang {

	/**
	 * The query parameter naming the language.
	 */
	public const PARAM = 'lang';

	/**
	 * The parameter value that lists every language.
	 */
	public const ALL = 'all';

	/**
	 * The REST requests whose callbacks are running, innermost last: the
	 * language they list (null for every language) and what entering that
	 * language changed.
	 *
	 * @var list<array{language: string|null, entered: array{bool, mixed, string}|null}>
	 */
	private array $running = array();

	/**
	 * Sets up the filters.
	 *
	 * @param Languages $languages The site's languages.
	 */
	public function __construct( private readonly Languages $languages ) {}

	/**
	 * Enters a request (filter `rest_request_before_callbacks`).
	 *
	 * @param mixed                $response Response so far.
	 * @param array<string, mixed> $handler  Route handler.
	 * @param \WP_REST_Request     $request  Request.
	 * @return mixed
	 *
	 * @phpstan-param \WP_REST_Request<array<string, mixed>> $request
	 */
	public function enter( $response, array $handler, \WP_REST_Request $request ) {
		unset( $handler );
		$language        = $this->language_of( $request );
		$this->running[] = array(
			'language' => $language,
			'entered'  => null === $language ? null : $this->languages->enter( $language ),
		);
		return $response;
	}

	/**
	 * Leaves a request (filter `rest_request_after_callbacks`).
	 *
	 * @param mixed $response Response.
	 * @return mixed
	 */
	public function leave( $response ) {
		$request = array_pop( $this->running );
		if ( null !== $request && null !== $request['entered'] ) {
			$this->languages->leave( $request['entered'] );
		}
		return $response;
	}

	/**
	 * The language a request lists, null for every language.
	 *
	 * @param \WP_REST_Request $request Request.
	 *
	 * @phpstan-param \WP_REST_Request<array<string, mixed>> $request
	 */
	public function language_of( \WP_REST_Request $request ): ?string {
		$requested = $request->get_param( self::PARAM );
		if ( self::ALL === $requested ) {
			return null;
		}
		if ( is_string( $requested ) && $this->languages->exists( $requested ) ) {
			return $requested;
		}
		return $this->languages->current();
	}

	/**
	 * Narrows a post query run by a REST callback to the request's language
	 * (action `pre_get_posts`). Queries by ID and queries that name a
	 * language are left alone.
	 *
	 * @param \WP_Query $query The query.
	 */
	public function posts( \WP_Query $query ): void {
		// Only server-built authority queries carry this marker. REST query
		// parameters are never copied here; customer lists keep their language.
		if ( true === $query->get( 'linker_publication_internal' ) ) {
			return;
		}
		$language = $this->language();
		if ( null === $language || '' !== (string) $query->get( self::PARAM ) ) {
			return;
		}
		foreach ( array( 'p', 'page_id', 'post__in' ) as $by_id ) {
			if ( ! empty( $query->get( $by_id ) ) ) {
				return;
			}
		}
		$post_types = $query->get( 'post_type' );
		$post_types = empty( $post_types ) ? array( 'post' ) : (array) $post_types;
		if ( in_array( 'any', $post_types, true ) || array() !== array_filter( $post_types, array( $this->languages, 'translates_post_type' ) ) ) {
			$query->set( self::PARAM, $language );
		}
	}

	/**
	 * Narrows a term query run by a REST callback to the request's language
	 * (filter `get_terms_args`). The terms of a given object and queries by ID
	 * or by language are left alone.
	 *
	 * @param array<string, mixed> $args       Term query arguments.
	 * @param array<int, string>   $taxonomies Taxonomies queried.
	 * @return array<string, mixed>
	 */
	public function terms( array $args, array $taxonomies ): array {
		$language = $this->language();
		if ( null === $language || isset( $args['lang'] ) || ! empty( $args['object_ids'] ) || ! empty( $args['include'] ) ) {
			return $args;
		}
		if ( array() !== array_filter( $taxonomies, array( $this->languages, 'translates_taxonomy' ) ) ) {
			$args['lang'] = $language;
		}
		return $args;
	}

	/**
	 * The language of the innermost running request; null outside REST or
	 * when it lists every language.
	 */
	private function language(): ?string {
		return array() === $this->running ? null : $this->running[ array_key_last( $this->running ) ]['language'];
	}
}
