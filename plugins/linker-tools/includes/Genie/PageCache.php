<?php
/**
 * Tells Genie to drop a page it has cached, when that page is saved.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Post;

/**
 * Genie reads a page as an anonymous visitor and keeps the text in its own
 * process (`PageReader`, ten minutes). A save, an update, or the German
 * auto-translation (`wp_update_post` in linker-i18n) does not reach that
 * copy, so the next question was still answered from the old text until the
 * process restarted (#405).
 *
 * This hooks the save and POSTs the public path, and the path of each
 * language twin, to the service (`POST /pages/invalidate`, the same shared
 * token as every other call). Pages that were not saved stay cached. The
 * ten minutes remain the backstop when the service cannot be reached, and
 * for a page this save does not name (a listing that only embeds the
 * product, a filtered query).
 *
 * WordPress's object cache is not that copy. A normal save already drops
 * the post's own object-cache keys, and the next anonymous GET renders
 * again. A full-page cache in front of the site is a different copy.
 * Production has none active: the LiteSpeed Cache plugin is not in use, and
 * anonymous HTML is not served with an `x-litespeed-cache` hit
 * (docs/research/2026-10-09/i18n-audit.md,
 * docs/acceptance/2026-10-14/17). If one is turned on later, Genie's GET can
 * still receive the proxy's HTML after this call, until that cache is
 * purged. This hook does not send `X-LiteSpeed-Purge`.
 *
 * The service runs as one process (`linker-genie.service`, no worker
 * fan-out), so this POST reaches the process that holds the cache. A later
 * multi-worker deploy would need the call to reach every worker; the ten
 * minutes would still bound a miss.
 */
final class PageCache {

	/**
	 * The service route (linker_genie.app.invalidate_pages).
	 */
	public const ROUTE = '/pages/invalidate';

	/**
	 * Paths one request carries. The same number as `page.INVALIDATE_LIMIT`:
	 * past it, this sends another request.
	 */
	public const MAX_PATHS = 256;

	/**
	 * Seconds the save will wait for the service. The service is on this
	 * machine; a longer wait would hold the editor's request for a Genie
	 * that is not answering. The ten-minute cache is the backstop.
	 */
	public const TIMEOUT = 2.0;

	/**
	 * Paths to drop, gathered during this request and sent once on shutdown.
	 *
	 * @var array<string, true>
	 */
	private array $paths = array();

	/**
	 * Whether the shutdown send is already scheduled.
	 *
	 * @var bool
	 */
	private bool $armed = false;

	/**
	 * Whether a send is in progress, so a save during the send adds paths
	 * instead of starting a second send.
	 *
	 * @var bool
	 */
	private bool $sending = false;

	/**
	 * The shared service token; '' when the site has none.
	 *
	 * @var string
	 */
	private readonly string $token;

	/**
	 * Sets up the notifier.
	 *
	 * @param callable( string, array<string, mixed>, array<string, string> ): (int|string|\WP_Error)|null $fetch Optional HTTP client for tests (URL, body, headers): an int status, a body string (200), or WP_Error.
	 * @param string|null                                                                                  $token The shared service token; read from Proxy::TOKEN_CONSTANT when null.
	 */
	public function __construct( private $fetch = null, ?string $token = null ) {
		$this->token = $token ?? ( defined( Proxy::TOKEN_CONSTANT ) ? (string) constant( Proxy::TOKEN_CONSTANT ) : '' );
	}

	/**
	 * Adds the hooks. `wp_after_insert_post` covers a staff save and the
	 * translator's `wp_update_post`. `edited_term` covers a category or tag
	 * whose archive is the page.
	 */
	public function register(): void {
		add_action( 'pre_post_update', array( $this, 'before_post_saved' ) );
		add_action( 'wp_after_insert_post', array( $this, 'post_saved' ), 10, 4 );
		add_action( 'edit_terms', array( $this, 'before_term_saved' ), 10, 2 );
		add_action( 'edited_term', array( $this, 'term_saved' ), 10, 3 );
	}

	/**
	 * The public address before the update, so a renamed page drops the old path.
	 *
	 * @param int $post_id Post ID.
	 */
	public function before_post_saved( int $post_id ): void {
		$post = get_post( $post_id );
		if ( $post instanceof WP_Post && $this->is_public_post( $post ) ) {
			$this->note_post( $post->ID );
		}
	}

	/**
	 * A post was inserted or updated. A published page, product or post drops
	 * its cache and its twins'; so does a page that just stopped being public.
	 *
	 * @param int          $post_id Post ID.
	 * @param WP_Post      $post    The post as saved.
	 * @param bool         $update  Whether this was an update.
	 * @param WP_Post|null $before  The post before the update; null on insert.
	 */
	public function post_saved( int $post_id, WP_Post $post, bool $update = false, ?WP_Post $before = null ): void {
		unset( $update );
		$was = $before instanceof WP_Post && $this->is_public_post( $before );
		if ( ! $was && ! $this->is_public_post( $post ) ) {
			return;
		}
		$this->note_post( $post_id );
	}

	/**
	 * The term's public address before the update.
	 *
	 * @param int    $term_id  Term ID.
	 * @param string $taxonomy Taxonomy.
	 */
	public function before_term_saved( int $term_id, string $taxonomy ): void {
		$this->note_term( $term_id, $taxonomy );
	}

	/**
	 * A term was edited. Its archive, and each language twin's archive, is dropped.
	 *
	 * @param int    $term_id  Term ID.
	 * @param int    $tt_id    Term taxonomy ID.
	 * @param string $taxonomy Taxonomy.
	 */
	public function term_saved( int $term_id, int $tt_id, string $taxonomy ): void {
		unset( $tt_id );
		$this->note_term( $term_id, $taxonomy );
	}

	/**
	 * POSTs the gathered paths. Runs on shutdown, or immediately when the save
	 * itself happens during shutdown. A failure is logged and never fatal to
	 * the save: the cache still expires on its own.
	 */
	public function send(): void {
		if ( $this->sending ) {
			return;
		}
		$this->sending = true;
		try {
			while ( array() !== $this->paths ) {
				$paths       = array_keys( $this->paths );
				$this->paths = array();
				$this->deliver( $paths );
			}
		} finally {
			$this->sending = false;
			$this->armed   = false;
		}
	}

	/**
	 * Whether the post is a public page an anonymous visitor can be shown.
	 *
	 * A revision, an autosave, a draft and a non-public type (a conversation)
	 * are not pages Genie caches.
	 *
	 * @param WP_Post $post Post.
	 */
	private function is_public_post( WP_Post $post ): bool {
		if ( wp_is_post_revision( $post->ID ) || wp_is_post_autosave( $post->ID ) ) {
			return false;
		}
		if ( 'publish' !== $post->post_status ) {
			return false;
		}
		return is_post_type_viewable( $post->post_type );
	}

	/**
	 * Notes the post's path and each language twin's path.
	 *
	 * @param int $post_id Post ID.
	 */
	private function note_post( int $post_id ): void {
		$ids = array( $post_id );
		if ( function_exists( 'pll_get_post_translations' ) ) {
			$translations = pll_get_post_translations( $post_id );
			if ( is_array( $translations ) ) {
				foreach ( $translations as $id ) {
					$ids[] = (int) $id;
				}
			}
		}
		foreach ( array_unique( $ids ) as $id ) {
			if ( $id <= 0 ) {
				continue;
			}
			$link = get_permalink( $id );
			if ( is_string( $link ) ) {
				$this->note( $this->path_of( $link ) );
			}
		}
	}

	/**
	 * Notes a viewable term's archive and each language twin's archive.
	 *
	 * @param int    $term_id  Term ID.
	 * @param string $taxonomy Taxonomy.
	 */
	private function note_term( int $term_id, string $taxonomy ): void {
		if ( ! is_taxonomy_viewable( $taxonomy ) ) {
			return;
		}
		$ids = array( $term_id );
		if ( function_exists( 'pll_get_term_translations' ) ) {
			$translations = pll_get_term_translations( $term_id );
			if ( is_array( $translations ) ) {
				foreach ( $translations as $id ) {
					$ids[] = (int) $id;
				}
			}
		}
		foreach ( array_unique( $ids ) as $id ) {
			if ( $id <= 0 ) {
				continue;
			}
			$link = get_term_link( $id, $taxonomy );
			if ( is_string( $link ) ) {
				$this->note( $this->path_of( $link ) );
			}
		}
	}

	/**
	 * The path of a permalink, query included. Empty when it is not a path.
	 *
	 * @param string $url Absolute permalink.
	 */
	private function path_of( string $url ): string {
		$parts = wp_parse_url( $url );
		if ( ! is_array( $parts ) ) {
			return '';
		}
		$path = (string) ( $parts['path'] ?? '' );
		if ( '' === $path || ! str_starts_with( $path, '/' ) || str_starts_with( $path, '//' ) ) {
			return '';
		}
		$query = isset( $parts['query'] ) && '' !== $parts['query'] ? '?' . $parts['query'] : '';
		return $path . $query;
	}

	/**
	 * Remembers one path and makes sure it will be sent.
	 *
	 * @param string $path Site path, leading slash.
	 */
	private function note( string $path ): void {
		if ( '' === $path ) {
			return;
		}
		$this->paths[ $path ] = true;
		if ( did_action( 'shutdown' ) ) {
			$this->send();
			return;
		}
		if ( ! $this->armed ) {
			$this->armed = true;
			add_action( 'shutdown', array( $this, 'send' ) );
		}
	}

	/**
	 * POSTs the paths, in batches of MAX_PATHS. No address means Genie is not
	 * configured, and a save stays quiet. A missing token, or a call that
	 * fails, is logged: the pages would otherwise stay stale for ten minutes.
	 *
	 * @param string[] $paths Paths.
	 */
	private function deliver( array $paths ): void {
		$base = rtrim( (string) get_option( Proxy::OPTION, '' ), '/' );
		if ( '' === $base ) {
			return;
		}
		if ( '' === $this->token ) {
			$this->failed( 503, count( $paths ) );
			return;
		}
		foreach ( array_chunk( $paths, self::MAX_PATHS ) as $chunk ) {
			$code = $this->post( $base . self::ROUTE, array( 'paths' => $chunk ) );
			if ( $code >= 400 ) {
				$this->failed( $code, count( $chunk ) );
			}
		}
	}

	/**
	 * Logs that the cached pages were not dropped. The save has already succeeded.
	 *
	 * @param int $code  Status code, or 503 when Genie is not configured.
	 * @param int $count How many paths this attempt carried.
	 */
	private function failed( int $code, int $count ): void {
		if ( ! function_exists( 'wc_get_logger' ) ) {
			return;
		}
		wc_get_logger()->error(
			sprintf( 'Genie: %d cached page(s) were not dropped (status %d). The pages expire on their own within ten minutes.', $count, $code ),
			array( 'source' => 'linker-genie' )
		);
	}

	/**
	 * POST JSON to the service; returns the status code, 502 when it cannot be reached.
	 *
	 * @param string               $url  Service URL.
	 * @param array<string, mixed> $body Request body.
	 */
	private function post( string $url, array $body ): int {
		if ( is_callable( $this->fetch ) ) {
			$answer = ( $this->fetch )( $url, $body, array( Proxy::TOKEN_HEADER => $this->token ) );
			if ( is_wp_error( $answer ) ) {
				return 502;
			}
			return is_int( $answer ) ? $answer : 200;
		}
		$response = wp_remote_post(
			$url,
			array(
				'headers' => array(
					'Content-Type'      => 'application/json',
					Proxy::TOKEN_HEADER => $this->token,
				),
				'body'    => (string) wp_json_encode( $body ),
				'timeout' => self::TIMEOUT,
			)
		);
		if ( is_wp_error( $response ) ) {
			return 502;
		}
		return (int) wp_remote_retrieve_response_code( $response );
	}
}
