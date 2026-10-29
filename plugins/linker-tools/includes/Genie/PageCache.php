<?php
/**
 * Tells Genie to drop a page it has cached, when that page is saved.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

use WP_Post;
use WP_Term;

/**
 * Genie reads a page as an anonymous visitor and keeps the text in its own
 * process (`PageReader`, ten minutes). A save, an update, or the German
 * auto-translation (`wp_update_post` in linker-i18n) does not reach that
 * copy, so the next question was still answered from the old text until the
 * process restarted (#405).
 *
 * This hooks the save and POSTs the public path, the path of each language
 * twin, and the listings that show the object, to the service
 * (`POST /pages/invalidate`, the same shared token as every other call).
 * A post names the blog index, its categories and its tags. A product names
 * the shop and its product categories. A page names neither the blog index
 * nor the shop. A category move is recorded on `set_object_terms`: WooCommerce
 * assigns terms after `wp_update_post`, and a category-only save never calls
 * `wp_update_post`. The old archive and the new one are both named. The service
 * also drops every cached solution draft on that call (`page.py`): the body is
 * paths, not which draft holds the product.
 * The ten minutes remain the backstop when the service cannot be reached,
 * and for a filtered, searched, or paginated listing this save does not name.
 * A single page that was not saved, and that is not one of those listings,
 * stays cached.
 *
 * WordPress's object cache is not that copy. A normal save already drops
 * the post's own object-cache keys, and the next anonymous GET renders
 * again. A full-page cache in front of the site is a different copy.
 * Production LiteSpeed serves anonymous HTML from that copy. This hook does
 * not send `X-LiteSpeed-Purge`; a deploy still has to purge that cache.
 * The workspace, configurator and public forms are kept out by Cache\DynamicHtml.
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
	 * Paths one request carries. The same number as `schema.CACHE_SIZE`
	 * (services/genie/src/linker_genie/schema.py): the page cache holds that
	 * many entries, so one invalidation need not name more paths than the
	 * process can hold. Past it, this sends another request. PHP cannot
	 * import the Python constant; services/genie/tests/test_page.py reads
	 * this line and pins the two.
	 */
	public const MAX_PATHS = 256;

	/**
	 * Seconds the save will wait for the service.
	 *
	 * Production Genie is not in the WordPress host. The site on Hostinger
	 * calls nginx on the VPS, port 8443, `location /genie/`, which proxies
	 * to `linker-genie.service` on 127.0.0.1:8902
	 * (services/genie/src/linker_genie/gate.py, docs/specs/17-cutover.md, the
	 * §5 run-face note). Locally `just serve` writes `linker_genie_url` to
	 * loopback. Either way the save waits on one hop. Two seconds sits far
	 * under the shell's turn budget (`Proxy::TURN_BUDGET`, 60): a Genie that
	 * is not answering must not hold the editor's save. The ten-minute cache
	 * is the backstop.
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
	 * translator's `wp_update_post`. `edited_term` covers a renamed category or
	 * tag. `set_object_terms` covers the assignment itself: WooCommerce writes
	 * it in `update_terms()` after `wp_update_post`, and skips `wp_update_post`
	 * when only the category changed. The block editor's `handle_terms()` also
	 * runs after `wp_update_post`.
	 */
	public function register(): void {
		add_action( 'pre_post_update', array( $this, 'before_post_saved' ) );
		add_action( 'wp_after_insert_post', array( $this, 'post_saved' ), 10, 4 );
		add_action( 'edit_terms', array( $this, 'before_term_saved' ), 10, 2 );
		add_action( 'edited_term', array( $this, 'term_saved' ), 10, 3 );
		add_action( 'set_object_terms', array( $this, 'object_terms_set' ), 10, 6 );
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
	 * Terms were assigned. The new archives and the ones just replaced are dropped.
	 *
	 * WordPress 7.1 `wp_set_object_terms()` (`wp-includes/taxonomy.php`) fires
	 * this after the relationships are written and the relationship cache is
	 * deleted:
	 * `do_action( 'set_object_terms', $object_id, $terms, $tt_ids, $taxonomy, $append, $old_tt_ids )`.
	 * `$terms` is the caller's list, IDs or slugs, and is not a term-id list.
	 * `$tt_ids` are the requested term_taxonomy_ids (`term_exists()` values;
	 * WooCommerce passes them as strings). `$old_tt_ids` is the previous
	 * term_taxonomy_ids from `wp_get_object_terms( ..., array( 'fields' => 'tt_ids' ) )`
	 * when the assignment replaces; an append passes an empty array. Those
	 * field values are integers. Neither array is a list of term IDs.
	 *
	 * @param int          $object_id  Object ID.
	 * @param array<mixed> $terms      Caller term IDs or slugs. Unused.
	 * @param array<mixed> $tt_ids     Requested term_taxonomy_ids.
	 * @param string       $taxonomy   Taxonomy slug.
	 * @param bool         $append     Whether the terms were appended.
	 * @param array<mixed> $old_tt_ids Previous term_taxonomy_ids, empty when appending.
	 */
	public function object_terms_set( int $object_id, array $terms, array $tt_ids, string $taxonomy, bool $append, array $old_tt_ids ): void {
		unset( $terms, $append );
		$post = get_post( $object_id );
		if ( ! $post instanceof WP_Post || ! $this->is_public_post( $post ) ) {
			return;
		}
		// The relationship cache is already gone, so this sees the new assignment.
		// The requested ids are still resolved below: a stale cache must not hide them.
		$this->note_post( $object_id );
		$this->note_term_taxonomy_ids( $tt_ids, $taxonomy );
		$this->note_term_taxonomy_ids( $old_tt_ids, $taxonomy );
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
	 * Notes the post's path, each language twin's path, and the listings that
	 * show them. Called before the save, after it, and when terms are assigned,
	 * so a renamed slug and a category move each drop both addresses.
	 *
	 * @param int $post_id Post ID.
	 */
	private function note_post( int $post_id ): void {
		foreach ( $this->post_ids( $post_id ) as $id ) {
			$link = get_permalink( $id );
			if ( is_string( $link ) ) {
				$this->note( $this->path_of( $link ) );
			}
			$post = get_post( $id );
			if ( $post instanceof WP_Post ) {
				$this->note_listings( $post );
			}
		}
	}

	/**
	 * The post and each language twin. Zeros are dropped.
	 *
	 * @param int $post_id Post ID.
	 * @return list<int>
	 */
	private function post_ids( int $post_id ): array {
		$ids = array( $post_id );
		if ( function_exists( 'pll_get_post_translations' ) ) {
			$translations = pll_get_post_translations( $post_id );
			if ( is_array( $translations ) ) {
				foreach ( $translations as $id ) {
					$ids[] = (int) $id;
				}
			}
		}
		return $this->positive_ids( $ids );
	}

	/**
	 * Listings whose HTML embeds this object.
	 *
	 * A post: the blog index, its categories, its tags. A product: the shop,
	 * its product categories. A page: nothing else. Filtered queries, search
	 * and pagination are not named; they expire with the ten-minute TTL.
	 *
	 * @param WP_Post $post Post.
	 */
	private function note_listings( WP_Post $post ): void {
		if ( 'post' === $post->post_type ) {
			$this->note_posts_index();
			$this->note_assigned_terms( $post->ID, 'category' );
			$this->note_assigned_terms( $post->ID, 'post_tag' );
			return;
		}
		if ( 'product' === $post->post_type ) {
			$this->note_shop();
			$this->note_assigned_terms( $post->ID, 'product_cat' );
		}
	}

	/**
	 * The blog index. The posts page and its language twins when the site has
	 * one; otherwise the front page in each language when that front page is
	 * the post list; otherwise the post type archive link when WordPress has one.
	 */
	private function note_posts_index(): void {
		$page = (int) get_option( 'page_for_posts' );
		if ( $page > 0 ) {
			$this->note_post_paths( $page );
			return;
		}
		if ( 'posts' === (string) get_option( 'show_on_front' ) ) {
			$this->note_homes();
			return;
		}
		$this->note_archive( 'post' );
	}

	/**
	 * The shop. The shop page and its language twins when WooCommerce has one;
	 * otherwise the product archive link.
	 */
	private function note_shop(): void {
		$shop = function_exists( 'wc_get_page_id' ) ? (int) wc_get_page_id( 'shop' ) : 0;
		if ( $shop > 0 ) {
			$this->note_post_paths( $shop );
			return;
		}
		$this->note_archive( 'product' );
	}

	/**
	 * Paths of a page and its language twins, without that page's own listings.
	 *
	 * The shop page and the posts page are pages. Noting them must not walk
	 * back into the shop or the blog index.
	 *
	 * @param int $post_id Post ID.
	 */
	private function note_post_paths( int $post_id ): void {
		foreach ( $this->post_ids( $post_id ) as $id ) {
			$link = get_permalink( $id );
			if ( is_string( $link ) ) {
				$this->note( $this->path_of( $link ) );
			}
		}
	}

	/**
	 * Each language's home, the blog index when the front page lists posts.
	 */
	private function note_homes(): void {
		if ( function_exists( 'pll_languages_list' ) && function_exists( 'pll_home_url' ) ) {
			$languages = pll_languages_list();
			if ( is_array( $languages ) && array() !== $languages ) {
				foreach ( $languages as $language ) {
					if ( ! is_string( $language ) || '' === $language ) {
						continue;
					}
					$link = pll_home_url( $language );
					if ( is_string( $link ) ) {
						$this->note( $this->path_of( $link ) );
					}
				}
				return;
			}
		}
		// No language layer: the front page is the only blog index. home_url()
		// is the host; the path is the root.
		$home = $this->path_of( home_url() );
		$this->note( '' === $home ? '/' : $home );
	}

	/**
	 * A post type archive link, when WordPress has one.
	 *
	 * @param string $post_type Post type.
	 */
	private function note_archive( string $post_type ): void {
		$link = get_post_type_archive_link( $post_type );
		if ( is_string( $link ) ) {
			$this->note( $this->path_of( $link ) );
		}
	}

	/**
	 * The terms assigned to the post, and each term's language twin.
	 *
	 * @param int    $post_id  Post ID.
	 * @param string $taxonomy Taxonomy.
	 */
	private function note_assigned_terms( int $post_id, string $taxonomy ): void {
		if ( ! taxonomy_exists( $taxonomy ) ) {
			return;
		}
		$terms = wp_get_object_terms( $post_id, $taxonomy, array( 'fields' => 'ids' ) );
		if ( is_wp_error( $terms ) ) {
			return;
		}
		foreach ( $terms as $term_id ) {
			$this->note_term( (int) $term_id, $taxonomy );
		}
	}

	/**
	 * Positive IDs, once each, in first-seen order.
	 *
	 * @param int[] $ids IDs.
	 * @return list<int>
	 */
	private function positive_ids( array $ids ): array {
		$unique = array();
		foreach ( $ids as $id ) {
			if ( $id > 0 ) {
				$unique[ $id ] = true;
			}
		}
		$found = array();
		foreach ( array_keys( $unique ) as $id ) {
			$found[] = (int) $id;
		}
		return $found;
	}

	/**
	 * Resolves term_taxonomy_ids to archives. `get_term_by( 'term_taxonomy_id' )`
	 * does not treat the id as a term_id (`wp-includes/taxonomy.php`).
	 *
	 * @param array<mixed> $tt_ids   Term_taxonomy_ids, integers or numeric strings.
	 * @param string       $taxonomy Taxonomy the assignment used.
	 */
	private function note_term_taxonomy_ids( array $tt_ids, string $taxonomy ): void {
		if ( ! is_taxonomy_viewable( $taxonomy ) ) {
			return;
		}
		foreach ( $tt_ids as $tt_id ) {
			$id = $this->term_taxonomy_id( $tt_id );
			if ( $id <= 0 ) {
				continue;
			}
			$term = get_term_by( 'term_taxonomy_id', $id, $taxonomy );
			if ( ! $term instanceof WP_Term ) {
				continue;
			}
			$found = (string) $term->taxonomy;
			$this->note_term( (int) $term->term_id, '' !== $found ? $found : $taxonomy );
		}
	}

	/**
	 * A term_taxonomy_id from the `set_object_terms` action. Zero when it is not one.
	 *
	 * @param mixed $value Action argument. WooCommerce passes strings for the new ids and integers for the old ones.
	 */
	private function term_taxonomy_id( mixed $value ): int {
		if ( is_int( $value ) ) {
			return $value;
		}
		if ( is_string( $value ) && ctype_digit( $value ) ) {
			return (int) $value;
		}
		return 0;
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
		foreach ( $this->positive_ids( $ids ) as $id ) {
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
