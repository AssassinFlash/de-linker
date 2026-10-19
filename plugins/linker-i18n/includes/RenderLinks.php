<?php
/**
 * Stored content keeps the request's language, without waiting for a job.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Runs the link localizer over rendered post content. German posts and pages
 * were copied from English with their English links and no translation job
 * runs on every request; without this fallback a German legal page links to
 * the English legal pages and a German post to the English categories
 * (docs/research/2026-10-17-i18n-audit/AUDIT.md, H3, M2, S1).
 *
 * The write-time localization remains the source of truth; this is the
 * render-time safety net. The stored content is never changed here.
 */
final class RenderLinks {

	/**
	 * Sets up the filter.
	 *
	 * @param LinkLocalizer $links     The link localizer.
	 * @param Languages     $languages The site's languages.
	 */
	public function __construct( private readonly LinkLocalizer $links, private readonly Languages $languages ) {}

	/**
	 * The content with its internal links in the request's language; runs on
	 * the_content, the_excerpt and widget_text_content.
	 *
	 * @param string $html Rendered content.
	 */
	public function content( string $html ): string {
		if ( '' === $html || is_admin() || ( defined( 'REST_REQUEST' ) && REST_REQUEST ) || ! $this->languages->ready() ) {
			return $html;
		}
		return $this->links->localize( $html, $this->languages->current() );
	}
}
