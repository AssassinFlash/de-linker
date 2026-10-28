<?php
/**
 * Shortcodes that feed the blog single template with its post data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use WP_Post;
use WP_Term;

/**
 * The two data fragments the blog single template renders: the article's
 * categories as links, and the related-articles grid.
 *
 * Both are the areas the closure round brought out of the template engine
 * (the live templates resolved them with Tangible loops): a loop cannot be
 * pinned by a test, and the related loop's `category="current"` fell back to
 * the newest articles when the article carried no category — the wrong-post
 * symptom on the live face. Here the selection is explicit and tested, and the
 * fragments carry semantic markup with class names only: the design lives in
 * content/livecanvas/blog_single.html and content/windpress/blog.css.
 */
final class BlogShortcodes {

	/**
	 * How many related articles the grid holds. The live face caps at three
	 * (`count="3"` on the template loop).
	 */
	public const RELATED_LIMIT = 3;

	/**
	 * The related card's date format, by language. The live face prints the
	 * English format in English and the German one in German (captures
	 * 2026-10-12/13: "May 29, 2026" against "29.05.2026"; the German twin was
	 * later re-written with the English format, so the German entry restores
	 * the captured face).
	 *
	 * @var array<string, string>
	 */
	private const DATE_FORMATS = array( 'de' => 'd.m.Y' );

	/**
	 * The date format of a language without its own entry.
	 */
	private const DEFAULT_DATE_FORMAT = 'M j, Y';

	/**
	 * The image size the related card's thumbnail is drawn at, and the sizes
	 * hint the live card carries (measured off the live HTML, 2026-10-14).
	 */
	private const CARD_IMAGE_SIZE  = 'medium_large';
	private const CARD_IMAGE_SIZES = '(max-width: 300px) 100vw, 300px';

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_action( 'init', array( JournalTitles::class, 'register' ) );
		add_filter( 'pre_get_document_title', array( $this, 'empty_search_title' ), 60 );
		add_shortcode( 'linker_blog_post_categories', array( $this, 'post_categories' ) );
		add_shortcode( 'linker_blog_related_posts', array( $this, 'related_posts' ) );
		add_shortcode( 'linker_blog_share', array( $this, 'share' ) );
	}

	/**
	 * Name the cleared journal search after SEOPress and the German title filter
	 * have composed the browser title. Keep its site suffix and other searches.
	 *
	 * @param string $title The composed browser title.
	 */
	public function empty_search_title( string $title ): string {
		if ( ! is_search() || 'post' !== get_query_var( 'post_type' ) || '' !== get_search_query( false ) ) {
			return $title;
		}
		$heading = __( 'All posts', 'linker-commerce' );
		$suffix  = strstr( $title, '|' );
		return $heading . ( false === $suffix ? '' : ' ' . $suffix );
	}

	/**
	 * The article's share row in the request's language.
	 *
	 * LiveCanvas's own sharing shortcode carries English titles ("Share on
	 * Facebook") and the plugin ships no German pack; the German template
	 * therefore composes the same four networks itself (#264 M1). The markup
	 * and icon set mirror what LiveCanvas printed on the live face, so the
	 * reader workspace's stylesheet draws both rows the same way. The label
	 * text is the link's accessible name and travels into title/aria-label;
	 * the German template's script keeps the server-provided values.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function share( $atts = array() ): string {
		$attributes = shortcode_atts( array( 'class' => 'reader-share-links' ), (array) $atts );
		$id         = (int) get_queried_object_id();
		$url        = (string) get_permalink( $id );
		if ( '' === $url ) {
			return '';
		}
		$title    = (string) get_the_title( $id );
		$networks = array(
			'facebook' => array( 'Facebook', 'https://www.facebook.com/sharer.php?u=' . rawurlencode( $url ) ),
			'whatsapp' => array( 'WhatsApp', 'https://api.whatsapp.com/send?text=' . rawurlencode( $url ) ),
			'telegram' => array( 'Telegram', 'https://telegram.me/share/url?url=' . rawurlencode( $url ) . '&text=' ),
			'twitter'  => array( 'Twitter', 'https://twitter.com/share?url=' . rawurlencode( $url ) . '&text=' . rawurlencode( $title ) . '&via=' ),
		);
		$html     = '<div class="lc-sharing-buttons ' . esc_attr( (string) $attributes['class'] ) . '">';
		foreach ( $networks as $network => list( $label, $href ) ) {
			/* translators: %s: social network name. */
			$text  = sprintf( __( 'Share on %s', 'linker-commerce' ), $label );
			$html .= '<a class="btn btn-outline-dark btn-sm btn-' . esc_attr( $network ) . '" href="' . esc_url( $href ) . '" target="_blank" rel="nofollow noopener" title="' . esc_attr( $text ) . '" aria-label="' . esc_attr( $text ) . '">' . $this->share_icon( $network ) . '<span class="d-none d-lg-inline"> ' . esc_html( $label ) . '</span></a>';
		}
		return $html . '</div>';
	}

	/**
	 * The network's icon, the set LiveCanvas printed on the live face (the
	 * brand glyphs are data; the stylesheet sizes them).
	 *
	 * @param string $network Network key.
	 */
	private function share_icon( string $network ): string {
		$paths = array(
			'facebook' => 'M279.14 288l14.22-92.66h-88.91v-60.13c0-25.35 12.42-50.06 52.24-50.06h40.42V6.26S260.43 0 225.36 0c-73.22 0-121.08 44.38-121.08 124.72v70.62H22.89V288h81.39v224h100.17V288z',
			'whatsapp' => 'M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 39.1 10.2 77.3 29.6 111L0 480l117.7-30.9c32.4 17.7 68.9 27 106.1 27h.1c122.3 0 224.1-99.6 224.1-222 0-59.3-25.2-115-67.1-157zm-157 341.6c-33.2 0-65.7-8.9-94-25.7l-6.7-4-69.8 18.3L72 359.2l-4.4-7c-18.5-29.4-28.2-63.3-28.2-98.2 0-101.7 82.8-184.5 184.6-184.5 49.3 0 95.6 19.2 130.4 54.1 34.8 34.9 56.2 81.2 56.1 130.5 0 101.8-84.9 184.6-186.6 184.6zm101.2-138.2c-5.5-2.8-32.8-16.2-37.9-18-5.1-1.9-8.8-2.8-12.5 2.8-3.7 5.6-14.3 18-17.6 21.8-3.2 3.7-6.5 4.2-12 1.4-32.6-16.3-54-29.1-75.5-66-5.7-9.8 5.7-9.1 16.3-30.3 1.8-3.7.9-6.9-.5-9.7-1.4-2.8-12.5-30.1-17.1-41.2-4.5-10.8-9.1-9.3-12.5-9.5-3.2-.2-6.9-.2-10.6-.2-3.7 0-9.7 1.4-14.8 6.9-5.1 5.6-19.4 19-19.4 46.3 0 27.3 19.9 53.7 22.6 57.4 2.8 3.7 39.1 59.7 94.8 83.8 35.2 15.2 49 16.5 66.6 13.9 10.7-1.6 32.8-13.4 37.4-26.4 4.6-13 4.6-24.1 3.2-26.4-1.3-2.5-5-3.9-10.5-6.6z',
			'telegram' => 'M446.7 98.6l-67.6 318.8c-5.1 22.5-18.4 28.1-37.3 17.5l-103-75.9-49.7 47.8c-5.5 5.5-10.1 10.1-20.7 10.1l7.4-104.9 190.9-172.5c8.3-7.4-1.8-11.5-12.9-4.1L117.8 284 16.2 252.2c-22.1-6.9-22.5-22.1 4.6-32.7L418.2 66.4c18.4-6.9 34.5 4.1 28.5 32.2z',
			'twitter'  => 'M459.37 151.716c.325 4.548.325 9.097.325 13.645 0 138.72-105.583 298.558-298.558 298.558-59.452 0-114.68-17.219-161.137-47.106 8.447.974 16.568 1.299 25.34 1.299 49.055 0 94.213-16.568 130.274-44.832-46.132-.975-84.792-31.188-98.112-72.772 6.498.974 12.995 1.624 19.818 1.624 9.421 0 18.843-1.3 27.614-3.573-48.081-9.747-84.143-51.98-84.143-102.985v-1.299c13.969 7.797 30.214 12.67 47.431 13.319-28.264-18.843-46.781-51.005-46.781-87.391 0-19.492 5.197-37.36 14.294-52.954 51.655 63.675 129.3 105.258 216.365 109.807-1.624-7.797-2.599-15.918-2.599-24.04 0-57.828 46.782-104.934 104.934-104.934 30.213 0 57.502 12.67 76.67 33.137 23.715-4.548 46.456-13.32 66.599-25.34-7.798 24.366-24.366 44.833-46.132 57.827 21.117-2.273 41.584-8.122 60.426-16.243-14.292 20.791-32.161 39.308-52.628 54.253z',
		);
		$path  = $paths[ $network ] ?? '';
		return '' === $path ? '' : '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' . ( 'facebook' === $network ? '320' : ( 'twitter' === $network ? '512' : '448' ) ) . ' 512" width="1.4em" height="1.4em" aria-hidden="true" focusable="false" fill="currentColor"><path d="' . $path . '"></path></svg>';
	}

	/**
	 * The article's categories as links to their archives.
	 *
	 * The link is the term's own URL, so an English article links
	 * `/category/<slug>/` and its German twin `/de/category/<slug>/`. A term
	 * the request's language does not carry resolves to its twin in that
	 * language; a term without a twin prints nothing, because a German page
	 * must not link an English archive.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function post_categories( $atts = array() ): string {
		unset( $atts );
		$html = '';
		foreach ( $this->current_terms() as $term ) {
			$url = get_term_link( $term );
			if ( ! \is_string( $url ) ) {
				continue;
			}
			$html .= '<a href="' . esc_url( $url ) . '">' . esc_html( $term->name ) . '</a>';
		}
		return $html;
	}

	/**
	 * The related articles: the posts that share a category with the article
	 * on display, newest first, at most RELATED_LIMIT.
	 *
	 * An article without a category has nothing to share and prints no grid —
	 * not a fallback to the newest articles, which is what the live face's
	 * loop did while the article-to-category relations were missing.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function related_posts( $atts = array() ): string {
		unset( $atts );
		$id = (int) get_the_ID();
		if ( $id <= 0 ) {
			return '';
		}
		$categories = array();
		foreach ( $this->current_terms() as $term ) {
			$categories[] = (int) $term->term_id;
		}
		if ( array() === $categories ) {
			return '';
		}
		$posts = get_posts(
			array(
				'post_type'           => 'post',
				'post_status'         => 'publish',
				'category__in'        => $categories,
				'post__not_in'        => array( $id ),
				'posts_per_page'      => self::RELATED_LIMIT,
				'orderby'             => 'date',
				'order'               => 'DESC',
				'ignore_sticky_posts' => true,
				'no_found_rows'       => true,
			)
		);
		$html  = '';
		foreach ( $posts as $post ) {
			$html .= $this->card( $post );
		}
		return $html;
	}

	/**
	 * One related card: the live card's own anatomy, class names and image
	 * attributes, so the stylesheet reaches it unchanged.
	 *
	 * The live card's meta line is the date and a separator; the empty category
	 * slot it carried (the template's category field resolved to nothing) is
	 * not printed — the face shows no category there.
	 *
	 * @param WP_Post $post The related article.
	 */
	private function card( WP_Post $post ): string {
		$permalink = (string) get_permalink( $post );
		$html      = '<article class="lc-block">';
		$html     .= '<a href="' . esc_url( $permalink ) . '" class="tv-blog-single-related-card">';
		$html     .= '<div class="tv-blog-single-related-img">';
		$html     .= $this->card_image( $post );
		$html     .= '</div>';
		$html     .= '<div class="tv-blog-single-related-body">';
		$html     .= '<div class="tv-blog-single-related-meta">';
		$html     .= '<time datetime="' . esc_attr( (string) get_the_date( 'c', $post ) ) . '">' . esc_html( $this->card_date( $post ) ) . '</time>';
		$html     .= '<span aria-hidden="true">&middot;</span>';
		$html     .= '</div>';
		$html     .= '<h3 class="tv-blog-single-related-card-title">' . esc_html( JournalTitles::label( $post ) ) . '</h3>';
		$html     .= '<div class="tv-blog-single-related-excerpt">' . esc_html( get_the_excerpt( $post ) ) . '</div>';
		$html     .= '<span class="tv-blog-single-related-arrow">' . esc_html__( 'Read article', 'linker-commerce' );
		$html     .= '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">';
		$html     .= '<path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14m-6-6 6 6-6 6" />';
		$html     .= '</svg></span>';
		$html     .= '</div></a></article>';
		return $html;
	}

	/**
	 * The card's thumbnail, or the live card's fallback figure when the
	 * article has none.
	 *
	 * @param WP_Post $post The related article.
	 */
	private function card_image( WP_Post $post ): string {
		$image_id = (int) get_post_thumbnail_id( $post );
		$src      = $image_id > 0 ? wp_get_attachment_image_url( $image_id, self::CARD_IMAGE_SIZE ) : false;
		if ( ! \is_string( $src ) || '' === $src ) {
			return '<div class="tv-blog-single-img-fallback">'
				. '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">'
				. '<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />'
				. '</svg></div>';
		}
		$srcset = wp_get_attachment_image_srcset( $image_id, self::CARD_IMAGE_SIZE );
		$html   = '<img src="' . esc_url( $src ) . '"';
		if ( \is_string( $srcset ) && '' !== $srcset ) {
			$html .= ' srcset="' . esc_attr( $srcset ) . '"';
		}
		// The linked card already names the article in its heading; the thumbnail is decorative.
		$html .= ' sizes="' . esc_attr( self::CARD_IMAGE_SIZES ) . '" loading="lazy" alt="">';
		return $html;
	}

	/**
	 * The card's date, in the page's language.
	 *
	 * @param WP_Post $post The related article.
	 */
	private function card_date( WP_Post $post ): string {
		$language = $this->request_language();
		$format   = self::DATE_FORMATS[ $language ] ?? self::DEFAULT_DATE_FORMAT;
		return (string) get_the_date( $format, $post );
	}

	/**
	 * The current article's categories, in the request's language.
	 *
	 * @return list<WP_Term>
	 */
	private function current_terms(): array {
		$id = (int) get_the_ID();
		if ( $id <= 0 ) {
			return array();
		}
		$terms = get_the_terms( $id, 'category' );
		if ( ! \is_array( $terms ) ) {
			return array();
		}
		$in_language = array();
		foreach ( $terms as $term ) {
			$resolved = $this->in_request_language( $term );
			if ( null !== $resolved ) {
				$in_language[] = $resolved;
			}
		}
		return $in_language;
	}

	/**
	 * A term as the request's language carries it: itself when it already is
	 * that language's, its twin when it has one, nothing when it has not.
	 *
	 * @param WP_Term $term The term the article carries.
	 */
	private function in_request_language( WP_Term $term ): ?WP_Term {
		$language = $this->request_language();
		if ( '' === $language || ! function_exists( 'pll_get_term' ) || ! function_exists( 'pll_get_term_language' ) ) {
			return $term;
		}
		if ( pll_get_term_language( $term->term_id ) === $language ) {
			return $term;
		}
		$twin = (int) pll_get_term( $term->term_id, $language );
		if ( $twin <= 0 ) {
			return null;
		}
		$twin_term = get_term( $twin, 'category' );
		return $twin_term instanceof WP_Term ? $twin_term : null;
	}

	/**
	 * The request's language, or an empty string without a language layer.
	 */
	private function request_language(): string {
		if ( ! function_exists( 'pll_current_language' ) ) {
			return '';
		}
		$language = pll_current_language();
		return \is_string( $language ) ? $language : '';
	}
}
