<?php
/**
 * Independent German document titles and account endpoint metadata.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/** Titles describe the German page being viewed, including Woo endpoints. */
final class GermanTitles {

	/**
	 * Native language access stays behind the shared Polylang door.
	 *
	 * @param Languages $languages Shared language and translation access.
	 */
	public function __construct( private readonly Languages $languages = new Languages() ) {}

	/**
	 * Reviewed title data shared by runtime and migration.
	 *
	 * @return list<array{type:string,source:string,before:array<string,string>,after:array<string,string>}>
	 */
	public function manifest(): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Checked-in reviewed title data.
		return json_decode( (string) file_get_contents( dirname( __DIR__ ) . '/content/german-titles.json' ), true, 512, JSON_THROW_ON_ERROR );
	}

	/**
	 * Use the native canonical opt-in for changed, nonpaged German categories.
	 *
	 * @param bool $allow Existing canonical-on-noindex policy.
	 */
	public function category_canonical( bool $allow ): bool {
		return $allow || ( get_option( GermanUrlMigration::ACTIVE ) && 'de' === $this->languages->current() && is_category() && ! is_paged() );
	}

	/**
	 * The German title after either SEOPress or WordPress has built its title.
	 *
	 * @param string $title Existing title, preserved outside German pages.
	 */
	public function title( string $title ): string {
		if ( ! get_option( GermanUrlMigration::ACTIVE ) || 'de' !== $this->languages->current() || is_404() ) {
			return $title;
		}
		$page  = max( (int) get_query_var( 'paged' ), (int) get_query_var( 'page' ), is_wc_endpoint_url( 'orders' ) ? (int) get_query_var( 'orders' ) : 0 );
		$label = '';
		if ( is_wc_endpoint_url( 'order-received' ) ) {
			/* translators: %s: inquiry number. */
			$label = sprintf( __( 'Inquiry received – %s', 'linker-i18n' ), (string) get_query_var( 'order-received' ) );
		} elseif ( is_account_page() ) {
			$endpoint = WC()->query->get_current_endpoint();
			$label    = $this->account_title( $endpoint );
		} elseif ( is_shop() ) {
			$label = __( 'Inverters, storage and systems', 'linker-i18n' );
		} elseif ( is_tax( 'product_cat' ) ) {
			/* translators: %s: German product category name. */
			$label = sprintf( __( 'Products: %s', 'linker-i18n' ), single_term_title( '', false ) );
		} elseif ( is_category() ) {
			/* translators: %s: German post category name. */
			$label = sprintf( __( 'Posts: %s', 'linker-i18n' ), single_term_title( '', false ) );
		} elseif ( is_search() ) {
			/* translators: %s: search query. */
			$label = sprintf( __( 'Search results for “%s”', 'linker-i18n' ), get_search_query( false ) );
		} else {
			$id   = get_queried_object_id();
			$post = get_post( $id );
			if ( $post instanceof \WP_Post && 'de' === $this->languages->of_post( $id ) ) {
				// Existing independent German SEO copy remains the native authority.
				$native = '' !== trim( $title ) ? $title : $this->post_title( $post ) . ' | ' . get_bloginfo( 'name' );
				if ( $page < 2 ) {
					return $native;
				}
				$brand = ' | ' . get_bloginfo( 'name' );
				$label = str_ends_with( $native, $brand ) ? substr( $native, 0, -strlen( $brand ) ) : $native;
			}
		}
		if ( '' === $label ) {
			return $title;
		}
		if ( $page > 1 ) {
			/* translators: %d: page number. */
			$label .= ' – ' . sprintf( __( 'Page %d', 'linker-i18n' ), $page );
		}
		return wp_strip_all_tags( $label ) . ' | ' . get_bloginfo( 'name' );
	}

	/**
	 * German page headings for the approved route changes; existing German otherwise.
	 *
	 * @param \WP_Post $post German post.
	 */
	public function post_title( \WP_Post $post ): string {
		$source = get_post( (int) $this->languages->post_translation( $post->ID, 'en' ) );
		$slug   = $source instanceof \WP_Post ? $source->post_name : '';
		foreach ( $this->manifest() as $entry ) {
			if ( $entry['type'] === $post->post_type && $entry['source'] === $slug ) {
				return $entry['after']['post_title'] ?? $post->post_title;
			}
		}
		return $post->post_title;
	}

	/**
	 * German category names for the two descriptive route changes.
	 *
	 * @param \WP_Term $term German category.
	 */
	public function term_title( \WP_Term $term ): string {
		$source = get_term( (int) $this->languages->term_translation( $term->term_id, 'en' ), $term->taxonomy );
		foreach ( $this->manifest() as $entry ) {
			if ( $source instanceof \WP_Term && $entry['type'] === $term->taxonomy && $entry['source'] === $source->slug ) {
				return $entry['after']['name'] ?? $term->name;
			}
		}
		return $term->name;
	}

	/**
	 * Native Woo endpoint identity supplies the title, even before sign-in.
	 *
	 * @param string $endpoint Internal endpoint key.
	 */
	private function account_title( string $endpoint ): string {
		return match ( $endpoint ) {
			'register' => __( 'Create a partner account', 'linker-i18n' ),
			'lost-password' => __( 'Reset your password', 'linker-i18n' ),
			'orders' => __( 'Inquiries', 'linker-i18n' ),
			/* translators: %s: inquiry number. */
			'view-order' => sprintf( __( 'Inquiry %s', 'linker-i18n' ), (string) get_query_var( 'view-order' ) ),
			'saved-solutions' => __( 'Saved solutions', 'linker-i18n' ),
			'documents' => __( 'Documents', 'linker-i18n' ),
			'edit-address' => match ( wc_edit_address_i18n( (string) get_query_var( 'edit-address' ), true ) ) {
				'billing' => 'Rechnungsadresse',
				'shipping' => 'Lieferadresse',
				default => __( 'Company details', 'linker-i18n' ),
			},
			'edit-account' => __( 'Account details', 'linker-i18n' ),
			'customer-logout' => __( 'Sign out', 'linker-i18n' ),
			default => is_user_logged_in() ? __( 'Your partner account', 'linker-i18n' ) : __( 'Sign in to your partner account', 'linker-i18n' ),
		};
	}

	/**
	 * Account forms retain the site's noindex policy and canonicalise to themselves.
	 *
	 * SEOPress passes complete canonical/Open Graph tags through both filters.
	 * Keep their markup and update the URL with WordPress's native HTML processor.
	 *
	 * @param string $tag Existing metadata tag.
	 */
	public function canonical( string $tag ): string {
		if ( ! get_option( GermanUrlMigration::ACTIVE ) || 'de' !== $this->languages->current() || ( ! is_account_page() && ! is_wc_endpoint_url( 'order-received' ) ) ) {
			return $tag;
		}
		$key  = WC()->query->get_current_endpoint();
		$base = 'order-received' === $key ? 'checkout' : 'myaccount';
		if ( '' === $key ) {
			return $tag;
		}
		$html = new \WP_HTML_Tag_Processor( $tag );
		if ( ! $html->next_tag() || ! in_array( $html->get_tag(), array( 'LINK', 'META' ), true ) ) {
			return $tag;
		}
		$html->set_attribute( 'LINK' === $html->get_tag() ? 'href' : 'content', wc_get_endpoint_url( $key, (string) get_query_var( $key ), wc_get_page_permalink( $base ) ) );
		return $html->get_updated_html();
	}
}
