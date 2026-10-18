<?php
/**
 * The contact form of the /contact/ page.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

/**
 * The contact page's form (ticket #68, GAP-8): the shortcode that renders it,
 * the handler that takes its submission, and the shared inquiry sender. Inquiry status emails notify the team and
 * acknowledge the visitor through the same Outbox pipeline. The site's previous contact form is not carried over: its
 * workspace, project bindings and receipts have no successor, the message
 * itself does.
 *
 * The mount is the page's own region: `[linker_contact_form]` stands inside
 * the `[data-linker-contact-mount]` of the /contact/ pages (EN and DE), where
 * the previous runtime rendered its form (tools/migrate/68-contact-form.py).
 * A deployed page whose content still carries the old fallback is mounted at
 * render time: the cutover list does not run that migration, and the live
 * pages measured 2026-10-14 still print the fallback with no form.
 */
final class Module {


	/**
	 * Adds the public form and handler; inquiry status hooks own the emails.
	 */
	public function register(): void {
		( new Form() )->register();
		( new Handler() )->register();
		// Before do_shortcode (priority 11 on the_content, WordPress default):
		// the replacement has to be a shortcode by the time that filter runs.
		add_filter( 'the_content', array( $this, 'mount_form' ), 9 );
	}

	/**
	 * Replaces the contact page's old fallback mount with the form shortcode.
	 *
	 * The pages ship their markup in post content (page template `empty`,
	 * measured on the deployed /contact/ and /de/kontakt/ on 2026-10-14).
	 * That content still holds the previous runtime's mount — a visible
	 * fallback and a noscript line — because the migration that swaps them
	 * for `[linker_contact_form]` is not in the cutover list. The swap
	 * happens here, on the way out, so a deploy renders the form without a
	 * content write. A page that already carries the shortcode keeps it —
	 * only the fallback line left beside it goes. Any other page is left
	 * alone: the mount marker belongs to these two pages.
	 *
	 * The fallback line stays in the page and is shown only when this
	 * shortcode is not registered — the form really cannot render. While
	 * the shortcode exists, the line is removed with the noscript note of
	 * the previous runtime.
	 *
	 * @param string $content The page content.
	 */
	public function mount_form( string $content ): string {
		if ( ! $this->is_contact_page() || ! str_contains( $content, 'data-linker-contact-mount' ) ) {
			return $content;
		}
		// Either branch: the fallback stays while the shortcode cannot
		// render. A page that already names the shortcode is not a reason
		// to drop the line — an unregistered tag would then leave nothing.
		if ( ! shortcode_exists( Form::SHORTCODE ) ) {
			return $content;
		}
		if ( str_contains( $content, '[' . Form::SHORTCODE ) ) {
			return $this->without_previous_fallback( $content );
		}
		$mounted = preg_replace(
			'/(<div\b[^>]*\bdata-linker-contact-mount\b[^>]*>)\s*<div\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/div>\s*(<\/div>)/s',
			'$1[' . Form::SHORTCODE . ']$2',
			$content,
			1,
			$count
		);
		// A PCRE failure returns null. Casting that to a string would blank
		// the page; the visitor keeps the content they already had.
		if ( ! is_string( $mounted ) || 1 !== $count ) {
			return $content;
		}
		return $this->without_previous_fallback( $mounted );
	}

	/**
	 * Whether the request is one of the two contact pages.
	 *
	 * English is the page at `contact`. German is its Polylang twin
	 * (`pll_get_post`), which is `/de/kontakt/` on the deployed site — not
	 * a slug this code invents.
	 */
	private function is_contact_page(): bool {
		$page = $this->rendered_page();
		if ( ! $page instanceof \WP_Post || 'page' !== $page->post_type ) {
			return false;
		}
		$english = get_page_by_path( 'contact' );
		if ( ! $english instanceof \WP_Post ) {
			return false;
		}
		if ( (int) $english->ID === (int) $page->ID ) {
			return true;
		}
		if ( ! function_exists( 'pll_get_post' ) ) {
			return false;
		}
		// 0 is "not translated" (Polylang 3.4+); it is not a page id.
		return pll_get_post( (int) $english->ID, 'de' ) === (int) $page->ID;
	}

	/**
	 * The contact page of this request, when the content being filtered is
	 * that page's own.
	 *
	 * The empty template prints the page through `the_content()`, so the
	 * post in the loop is the page. A widget or another loop on the same
	 * request is a different post: its content is not this form, even if
	 * it happens to carry the mount marker. Outside a loop the queried
	 * page is what is rendering.
	 */
	private function rendered_page(): ?\WP_Post {
		$queried = get_queried_object();
		if ( ! $queried instanceof \WP_Post || 'page' !== $queried->post_type ) {
			return null;
		}
		$loop = get_post();
		if ( $loop instanceof \WP_Post && (int) $loop->ID !== (int) $queried->ID ) {
			return null;
		}
		return $queried;
	}

	/**
	 * Drops the previous runtime's fallback line and its noscript note.
	 *
	 * Both describe a JavaScript form that is no longer what renders. The
	 * visible line is the one the 2026-10-14 recheck found in place of the
	 * form ("If the form is unavailable…" / "Falls das Formular nicht
	 * verfügbar ist…").
	 *
	 * The line survives in two stored shapes. The deployed pages and the
	 * stored snapshot content wrap it in `<noscript>` (de-linker.com
	 * /contact/ and /de/kontakt/ fetched 2026-10-14; plugins/linker-i18n/
	 * tests/fixtures/live/pages.json, entry `contact`). The bare paragraph
	 * is what a re-save of the contactform instance left on posts 10 and 11,
	 * 2026-10-14 13:26–13:33 UTC: `<script>`, `<style>` and `<noscript>`
	 * dropped with their text kept — the shape a kses-filtered save leaves.
	 * The loader did not do that: it calls `kses_remove_filters()` before it
	 * inserts (plugins/linker-i18n/tests/fixtures/seed.php:78), and t110's
	 * snapshot-loaded pages keep `<script>`/`<style>` (post 6917, whose
	 * fallback line the migration has already replaced with the shortcode).
	 * Which process ran the stripping save is not recorded; the lane README
	 * (docs/acceptance/2026-10-14/contact-form/) carries the reads and the
	 * open question.
	 *
	 * Both shapes are this line, so both are matched.
	 *
	 * @param string $content Page content that already mounts the form.
	 */
	private function without_previous_fallback( string $content ): string {
		$without_line = preg_replace(
			'/\s*(?:<noscript>\s*)?<p\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/p>\s*(?:<\/noscript>)?/s',
			'',
			$content,
			1
		);
		if ( ! is_string( $without_line ) ) {
			return $content;
		}
		$without_fallback = preg_replace(
			'/\s*<div\b[^>]*\bcp-contact-fallback\b[^>]*>.*?<\/div>/s',
			'',
			$without_line,
			1
		);
		return is_string( $without_fallback ) ? $without_fallback : $content;
	}
}
