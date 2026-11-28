<?php
/**
 * Public responses for RSS feeds and media attachment pages.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\Publication;

/** Keep editorial feeds readable and point media pages at their published owner. */
final class CrawlHygiene {
	/**
	 * Whether SEOPress has prepared an empty IndexNow batch in this request.
	 *
	 * @var bool
	 */
	private bool $skip_next_indexnow = false;

	/** Resolve after the site's retired aliases and before core attachment handling. */
	public function register(): void {
		add_filter( 'the_content', array( $this, 'content_links' ), 8 );
		add_filter( 'robots_txt', array( $this, 'robots_txt' ), 99, 2 );
		add_filter( 'wp_headers', array( $this, 'headers' ) );
		add_action( 'template_redirect', array( $this, 'respond' ), 2 );
		add_action( 'init', array( $this, 'register_instant_indexing' ), 20 );
		add_filter( 'seopress_instant_indexing_post_request_args', array( $this, 'indexnow_args' ) );
		add_filter( 'pre_http_request', array( $this, 'skip_empty_indexnow' ), 10, 3 );
	}

	/**
	 * Mark utility links in the original LiveCanvas page and journal content.
	 *
	 * @param string $content Stored markup before shortcode expansion.
	 */
	public function content_links( string $content ): string {
		if ( ! str_contains( $content, 'href' ) || is_admin() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
			return $content;
		}
		$root = PageUrls::root();
		$html = new \WP_HTML_Tag_Processor( $content );
		while ( $html->next_tag( array( 'tag_name' => 'A' ) ) ) {
			$href = $html->get_attribute( 'href' );
			if ( ! is_string( $href ) ) {
				continue;
			}
			$path = str_starts_with( $href, $root ) ? '/' . substr( $href, strlen( $root ) ) : $href;
			if ( ! self::nofollow_path( $path ) ) {
				continue;
			}
			$rel = (string) $html->get_attribute( 'rel' );
			if ( ! in_array( 'nofollow', explode( ' ', strtolower( $rel ) ), true ) ) {
				$html->set_attribute( 'rel', trim( $rel . ' nofollow' ) );
			}
		}
		return $html->get_updated_html();
	}

	/**
	 * Private account, inquiry and configurator state links.
	 *
	 * @param string $path Root-relative href or unmodified external URL.
	 */
	public static function nofollow_path( string $path ): bool {
		return (bool) preg_match( '~^/(?:my-account|de/mein-konto|cart|de/loesungsentwurf|(?:de/)?genie)(?:/|$)|^/(?:contact|de/kontakt)/\?(?:[^#]*&)?(?:intent|linker_contact_selection)=|^/(?:solution-configurator|de/loesungskonfigurator)/\?(?:[^#]*&)?(?:step|scope|compare|projects|view)=~', $path );
	}

	/**
	 * Extend the site's first wildcard group without changing named crawler groups.
	 *
	 * @param string $text WordPress or SEOPress virtual robots.txt.
	 * @param bool   $visible Site visibility.
	 */
	public function robots_txt( string $text, bool $visible ): string {
		if ( ! $visible ) {
			return $text;
		}
		$lines = explode( "\n", $text );
		$at    = null;
		foreach ( $lines as $i => $line ) {
			if ( 0 === strcasecmp( trim( $line ), 'User-agent: *' ) ) {
				$at = $i + 1;
				break;
			}
		}
		if ( null === $at ) {
			$lines[] = 'User-agent: *';
			$at      = count( $lines );
		}
		$existing = array();
		foreach ( array_slice( $lines, $at ) as $line ) {
			if ( str_starts_with( strtolower( ltrim( $line ) ), 'user-agent:' ) ) {
				break;
			}
			$existing[] = trim( $line );
		}
		$rules = array();
		foreach ( array( 'redirect_to', 'intent', 'linker_contact_selection', 'wc-ajax' ) as $key ) {
			$rules[] = 'Disallow: /*?' . $key . '=';
			$rules[] = 'Disallow: /*?*' . $key . '=';
		}
		array_splice( $lines, $at, 0, array_diff( $rules, $existing ) );
		return implode( "\n", $lines );
	}

	/**
	 * Keep all feeds out of the search index.
	 *
	 * @param array<string,string|false> $headers Native HTTP headers.
	 * @return array<string,string|false>
	 */
	public function headers( array $headers ): array {
		// WP::send_headers() can end a conditional feed request with 304 before template_redirect.
		$trap = $this->retired_query();
		if ( $trap || $this->retired_product_id() || $this->retired_feed() ) {
			status_header( 410 );
			header( $trap ? 'X-Robots-Tag: noindex' : 'X-Robots-Tag: noindex, follow' );
			header( 'Content-Type: text/plain; charset=utf-8' );
			header( 'Cache-Control: public, max-age=3600' );
			echo 'Gone';
			exit;
		}
		if ( is_feed() ) {
			$headers['X-Robots-Tag'] = 'noindex, follow';
		}
		return $headers;
	}

	/** Retired search, placeholder and malformed catalogue URLs on public reads. */
	private function retired_query(): bool {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Classify public read-only requests; inputs are never rendered.
		if ( empty( $_GET ) || ! in_array( $_SERVER['REQUEST_METHOD'] ?? 'GET', array( 'GET', 'HEAD' ), true ) || is_admin() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
			return false;
		}
		// Woo marks even this unexpanded template placeholder as DOING_AJAX on init.
		if ( '%%endpoint%%' === ( $_GET['wc-ajax'] ?? null ) ) {
			return true;
		}
		if ( wp_doing_ajax() ) {
			return false;
		}
		if ( array_key_exists( 's', $_GET ) && 'product' === ( $_GET['post_type'] ?? null ) ) {
			return true;
		}
		foreach ( array( 'phase', 'power', 'brand', 'application' ) as $facet ) {
			$value = $_GET[ $facet ] ?? '';
			if ( ! is_string( $value ) || ! str_contains( $value, ',' ) ) {
				continue;
			}
			$tokens = array_diff( array_map( 'trim', explode( ',', $value ) ), array( '' ) );
			if ( count( $tokens ) !== count( array_unique( $tokens ) ) ) {
				return is_shop() || is_product_taxonomy();
			}
		}
		// phpcs:enable
		return false;
	}

	/** Public shortlinks for missing or unpublished Woo products. */
	private function retired_product_id(): bool {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended, WordPress.Security.ValidatedSanitizedInput -- Classify a read-only permalink query.
		if ( 'product' !== ( $_GET['post_type'] ?? null ) || ! array_key_exists( 'p', $_GET ) || ! in_array( $_SERVER['REQUEST_METHOD'] ?? 'GET', array( 'GET', 'HEAD' ), true )
			|| is_admin() || wp_doing_ajax() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
			return false;
		}
		// phpcs:ignore WordPress.WP.Capabilities.Unknown -- WooCommerce registers edit_products for its product post type.
		if ( is_user_logged_in() && ( isset( $_GET['preview'] ) || current_user_can( 'edit_products' ) ) ) {
			return false;
		}
		$id = is_scalar( $_GET['p'] ) && ctype_digit( (string) $_GET['p'] ) ? (int) $_GET['p'] : 0;
		// phpcs:enable
		$post = $id > 0 ? get_post( $id ) : null;
		return ! $post instanceof \WP_Post || 'product' !== $post->post_type || 'publish' !== $post->post_status || '' !== $post->post_password || ! self::listed_product( $post->ID );
	}

	/**
	 * Publication covers both translations; the Woo visibility term controls catalog inclusion.
	 *
	 * @param int $id Product ID.
	 */
	private static function listed_product( int $id ): bool {
		return (bool) Publication::published_ids( array( $id ), true ) && ! has_term( 'exclude-from-catalog', 'product_visibility', $id );
	}

	/** Preserve SEOPress's publishing callback for eligible pages. */
	public function register_instant_indexing(): void {
		if ( remove_action( 'transition_post_status', 'seopress_instant_indexing_on_post_publish', 10 ) ) {
			add_action( 'transition_post_status', array( $this, 'guard_instant_indexing' ), 10, 3 );
		}
	}

	/**
	 * Forward only public, indexable posts with a pretty permalink.
	 *
	 * @param string   $new_status New status.
	 * @param string   $old_status Previous status.
	 * @param \WP_Post $post Changed post.
	 */
	public function guard_instant_indexing( string $new_status, string $old_status, \WP_Post $post ): void {
		if ( 'publish' !== $new_status || '' !== $post->post_password || 'yes' === get_post_meta( $post->ID, '_seopress_robots_index', true )
			|| ( 'product' === $post->post_type && ! self::listed_product( $post->ID ) ) ) {
			return;
		}
		$url = get_permalink( $post );
		if ( $url && ! str_contains( $url, '?' ) && ! self::retired_submission( $url ) && function_exists( 'seopress_instant_indexing_on_post_publish' ) ) {
			seopress_instant_indexing_on_post_publish( $new_status, $old_status, $post );
		}
	}

	/**
	 * Query shortlinks and trash permalinks must never enter an IndexNow batch.
	 *
	 * @param string $url URL from SEOPress.
	 */
	private static function retired_submission( string $url ): bool {
		return (bool) preg_match( '~[?&](?:post_type|p|page_id)=|__trashed~i', $url );
	}

	/**
	 * Remove retired URLs from SEOPress's final JSON, including manual submissions.
	 *
	 * @param array<string,mixed> $args Arguments for the IndexNow POST.
	 * @return array<string,mixed>
	 */
	public function indexnow_args( array $args ): array {
		$payload                  = json_decode( $args['body'], true );
		$valid                    = array_values( array_filter( $payload['urlList'], static fn( string $url ): bool => ! self::retired_submission( $url ) ) );
		$this->skip_next_indexnow = ! $valid;
		if ( $payload['urlList'] !== $valid ) {
			$payload['urlList'] = $valid;
			$args['body']       = wp_json_encode( $payload );
		}
		return $args;
	}

	/**
	 * Complete an empty SEOPress batch without opening an HTTP connection.
	 *
	 * @param mixed               $response Existing WordPress HTTP preemption.
	 * @param array<string,mixed> $args HTTP arguments.
	 * @param string              $url Destination.
	 * @return mixed
	 * @phpstan-impure Consumes the pending SEOPress batch.
	 */
	public function skip_empty_indexnow( mixed $response, array $args, string $url ): mixed {
		if ( ! $this->skip_next_indexnow || 'https://api.indexnow.org/indexnow/' !== $url || 'POST' !== $args['method'] ) {
			return $response;
		}
		$this->skip_next_indexnow = false;
		return false !== $response ? $response : array(
			'headers'  => array(),
			'body'     => '',
			'response' => array(
				'code'    => 200,
				'message' => 'OK',
			),
			'cookies'  => array(),
			'filename' => null,
		);
	}

	/** Whether this request is for a retired commerce or comments feed. */
	private function retired_feed(): bool {
		return is_feed() && ( is_comment_feed() || is_post_type_archive( 'product' ) || is_tax( array( 'product_cat', 'product_brand' ) ) || is_singular( 'product' ) );
	}

	/**
	 * Resolve an attachment's published and publicly queryable owner.
	 *
	 * @param \WP_Post $attachment Queried media item.
	 */
	public function attachment_parent( \WP_Post $attachment ): ?string {
		if ( ! $attachment->post_parent ) {
			return null;
		}
		$parent = get_post( $attachment->post_parent );
		if ( ! $parent instanceof \WP_Post || 'publish' !== $parent->post_status || ! is_post_publicly_viewable( $parent ) ) {
			return null;
		}
		$url = get_permalink( $parent );
		return $url ? trailingslashit( $url ) : null;
	}

	/** Media pages without a public parent render the site's 404. */
	public function respond(): void {
		if ( ! is_attachment() ) {
			return;
		}
		$post   = get_queried_object();
		$target = $post instanceof \WP_Post ? $this->attachment_parent( $post ) : null;
		if ( null !== $target && wp_safe_redirect( $target, 301 ) ) {
			exit;
		}
		global $wp_query;
		$wp_query->set_404();
		remove_action( 'template_redirect', 'redirect_canonical' );
		status_header( 404 );
		nocache_headers();
	}
}
