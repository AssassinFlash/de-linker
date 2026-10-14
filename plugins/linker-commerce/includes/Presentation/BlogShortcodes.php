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
		add_shortcode( 'linker_blog_post_categories', array( $this, 'post_categories' ) );
		add_shortcode( 'linker_blog_related_posts', array( $this, 'related_posts' ) );
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
		$html     .= '<h3 class="tv-blog-single-related-card-title">' . esc_html( get_the_title( $post ) ) . '</h3>';
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
		$alt    = (string) get_post_meta( $image_id, '_wp_attachment_image_alt', true );
		$html   = '<img src="' . esc_url( $src ) . '"';
		if ( \is_string( $srcset ) && '' !== $srcset ) {
			$html .= ' srcset="' . esc_attr( $srcset ) . '"';
		}
		$html .= ' sizes="' . esc_attr( self::CARD_IMAGE_SIZES ) . '" loading="lazy" alt="' . esc_attr( $alt ) . '">';
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
