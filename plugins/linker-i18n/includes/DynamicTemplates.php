<?php
/**
 * LiveCanvas dynamic templates on a German request.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Lets a German WooCommerce page render through the English LiveCanvas
 * dynamic template when it has no German one of its own.
 *
 * LiveCanvas picks a dynamic template with get_posts()
 * (livecanvas 4.9.3, modules/templating.php, lc_get_template_id()), and
 * Polylang narrows that query to the request's language (its parse_query at
 * priority 6, frontend.php). This plugin tells Polylang to translate
 * lc_dynamic_template, so on /de/ the lookup sees only German templates. The
 * shop, cart, checkout and account templates are structural — shortcodes, no
 * words of their own — and an instance can hold them in English only. The
 * German page then matches no template and falls through to the theme's
 * page.php, which prints its own title above the page.
 *
 * LiveCanvas's own last word on the choice is the lc_modify_template_id
 * filter (modules/templating.php), which runs after every one of its cases,
 * including a template a page names for itself. A page that already resolved
 * to a template is left as it is. Only a German request that resolved to none,
 * and that is one of the four WooCommerce page types, is answered with the
 * English template of that type — the language the missing German one is
 * written in. The lookup is LiveCanvas's own, run while Polylang's current
 * language is the source language, so it finds exactly the template the
 * English page renders through.
 */
final class DynamicTemplates {

	/**
	 * LiveCanvas's post type of a dynamic template.
	 */
	private const POST_TYPE = 'lc_dynamic_template';

	/**
	 * The WooCommerce page type a request is, and the meta key LiveCanvas
	 * stores that assignment under (modules/templating.php, the
	 * `is_<type>_page` cases). Order is the order LiveCanvas itself tests
	 * them in, so a request that is somehow two of them resolves as it does.
	 */
	private const PAGE_TYPES = array(
		'is_shop'         => 'is_shop_page',
		'is_cart'         => 'is_cart_page',
		'is_checkout'     => 'is_checkout_page',
		'is_account_page' => 'is_account_page',
	);

	/**
	 * Sets up the resolver.
	 *
	 * The page-type test is WooCommerce's own conditional (`is_cart()` and
	 * the three beside it). A test passes its own, because those functions
	 * belong to WooCommerce and a unit test does not load it.
	 *
	/**
	 * Whether the request is a WooCommerce page type, by the name of its
	 * conditional. The constructor closes over WooCommerce's own functions; a
	 * test passes its own.
	 *
	 * @var callable(string): bool
	 */
	private $is_page;

	/**
	 * Sets up the resolver.
	 *
	 * @param Languages                     $languages The site's languages.
	 * @param (callable(string): bool)|null $is_page   Whether the request is a WooCommerce page type, by the name of its conditional.
	 */
	public function __construct( private readonly Languages $languages, ?callable $is_page = null ) {
		$this->is_page = $is_page ?? static fn( string $conditional ): bool => function_exists( $conditional ) && $conditional();
	}

	/**
	 * The template a request renders through (filter `lc_modify_template_id`).
	 *
	 * A resolved template, a request in the source language and a request that
	 * is not one of the four page types pass through unchanged.
	 *
	 * @param int|false $template_id The template LiveCanvas resolved, or false.
	 */
	public function template( int|false $template_id ): int|false {
		if ( $template_id || Languages::SOURCE === $this->languages->current() || ! $this->languages->ready() ) {
			return $template_id;
		}
		$key = $this->page_type();
		if ( null === $key ) {
			return $template_id;
		}
		$english = $this->english_template( $key );

		return null === $english ? $template_id : $english;
	}

	/**
	 * The meta key of the WooCommerce page type this request is, or null.
	 */
	private function page_type(): ?string {
		foreach ( self::PAGE_TYPES as $conditional => $key ) {
			if ( ( $this->is_page )( $conditional ) ) {
				return $key;
			}
		}

		return null;
	}

	/**
	 * The English template carrying a LiveCanvas assignment, as LiveCanvas's
	 * own lookup finds it once the request's language no longer hides it.
	 *
	 * @param string $key LiveCanvas assignment meta key.
	 */
	private function english_template( string $key ): ?int {
		// Only Polylang's current language scopes the lookup (its parse_query
		// reads PLL()->curlang). The locale and the string translations stay:
		// the template is markup and shortcodes, and switching them would
		// change the language of everything rendered after this filter.
		$polylang          = PLL();
		$previous          = $polylang->curlang;
		$polylang->curlang = $polylang->model->get_language( Languages::SOURCE );
		$found             = get_posts(
			array(
				'post_type'        => self::POST_TYPE,
				'meta_key'         => $key, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- LiveCanvas's own lookup key (modules/templating.php, lc_get_template_id()).
				'orderby'          => 'menu_order',
				'numberposts'      => 1,
				'post_status'      => 'publish',
				'suppress_filters' => false,
			)
		);
		$polylang->curlang = $previous;
		if ( ! isset( $found[0]->ID ) ) {
			return null;
		}

		return (int) $found[0]->ID;
	}
}
