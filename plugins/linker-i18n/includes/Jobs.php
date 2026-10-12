<?php
/**
 * Translation on save, through WooCommerce's Action Scheduler.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\State;
use Linker\I18n\Translation\TranslationFailed;
use Linker\I18n\Translation\Translator;

/**
 * Queues a translation when an English page, post, product, LiveCanvas
 * partial or template, category or attribute term is saved, and runs it in
 * the background: an editor's save never waits for the translator.
 *
 * A failure for a passing reason (network, rate limit, an empty answer) is
 * tried again later; without DEEPSEEK_API_KEY the object stays pending until
 * someone translates it again ("Retranslate" in the list, or
 * `wp linker-i18n translate`).
 */
final class Jobs {

	/**
	 * The Action Scheduler hook.
	 */
	public const HOOK = 'linker_i18n_translate';

	/**
	 * The Action Scheduler group.
	 */
	public const GROUP = 'linker-i18n';

	/**
	 * Attempts for a translation that failed for a passing reason.
	 */
	private const ATTEMPTS = 3;

	/**
	 * Minutes before the next attempt: long enough for a rate limit or an
	 * outage to pass, short enough that an edit is German the same hour.
	 */
	private const RETRY_MINUTES = 15;

		/**
		 * Post statuses whose German version is translated; any other status is
		 * only passed on to the German version.
		 */
	private const LIVE = array( 'publish', 'future', 'private' );

		/**
		 * English LiveCanvas partial slugs whose German twin is a curated export,
		 * not a machine translation. `present` writes both files itself
		 * (header.html and de/header.html). Queuing the English save would
		 * translate over the German file. The German slug is kopfzeile — Twins
		 * derives it from the German title — so the exemption is the English
		 * slug plus its Polylang twin, not a same-slug pair.
		 */
	private const CURATED_PARTIALS = array( 'header' );

	/**
	 * Sets up the jobs.
	 *
	 * @param Languages  $languages  The site's languages.
	 * @param Translator $translator Makes the German versions.
	 * @param Twins      $twins      Writes German objects.
	 * @param State      $state      Translation state.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly Translator $translator,
		private readonly Twins $twins,
		private readonly State $state
	) {}

	/**
	 * A post was saved (action `wp_after_insert_post`): an English one is
	 * queued, or its status passed on; a German one saved by a person is an
	 * edit to keep.
	 *
	 * @param int      $post_id Post ID.
	 * @param \WP_Post $post    Post.
	 */
	public function post_saved( int $post_id, \WP_Post $post ): void {
		if ( $this->twins->writing() || wp_is_post_revision( $post_id ) || wp_is_post_autosave( $post_id ) || ! $this->languages->translates_post_type( $post->post_type ) ) {
			return;
		}
		if ( $this->curated_partial( $post_id, $post ) ) {
			return;
		}
		$language = $this->languages->of_post( $post_id );
		if ( Languages::TARGET === $language ) {
			if ( $this->translator->record_edit( State::POST, $post_id ) ) {
				$source = $this->languages->post_translation( $post_id, Languages::SOURCE );
				if ( null !== $source ) {
					$this->queue( State::POST, $source );
				}
			}
			return;
		}
		if ( Languages::SOURCE !== $language ) {
			return;
		}
		if ( in_array( $post->post_status, self::LIVE, true ) ) {
			$this->queue( State::POST, $post_id );
		} else {
			$this->twins->follow_status( $post_id );
		}
	}

	/**
	 * A term was saved (actions `created_term` and `edited_term`).
	 *
	 * @param int    $term_id  Term ID.
	 * @param int    $tt_id    Term taxonomy ID.
	 * @param string $taxonomy Taxonomy.
	 */
	public function term_saved( int $term_id, int $tt_id, string $taxonomy ): void {
		unset( $tt_id );
		if ( $this->twins->writing() || ! $this->languages->translates_taxonomy( $taxonomy ) ) {
			return;
		}
		$language = $this->languages->of_term( $term_id );
		if ( Languages::TARGET === $language ) {
			if ( $this->translator->record_edit( State::TERM, $term_id ) ) {
				$source = $this->languages->term_translation( $term_id, Languages::SOURCE );
				if ( null !== $source ) {
					$this->queue( State::TERM, $source );
				}
			}
			return;
		}
		if ( Languages::SOURCE === $language ) {
			$this->queue( State::TERM, $term_id );
		}
	}

		/**
		 * Whether this save is the curated header partial or its German twin.
		 *
		 * The English partial is named `header`. Its twin is whatever
		 * Polylang pairs with it (kopfzeile on the live instances). Saving
		 * either side must not queue a translation: the German export is the
		 * curated file, and a machine translation of the English save would
		 * replace it.
		 *
		 * @param int      $post_id Post ID.
		 * @param \WP_Post $post    Post.
		 */
	private function curated_partial( int $post_id, \WP_Post $post ): bool {
		if ( 'lc_partial' !== $post->post_type ) {
			return false;
		}
		if ( in_array( $post->post_name, self::CURATED_PARTIALS, true ) ) {
			return true;
		}
		$english = $this->languages->post_translation( $post_id, Languages::SOURCE );
		if ( null === $english ) {
			return false;
		}
		$source = get_post( $english );
		return $source instanceof \WP_Post && in_array( $source->post_name, self::CURATED_PARTIALS, true );
	}

		/**
		 * Queues the translation of an English object.
		 *
		 * @param string $kind  State::POST or State::TERM.
		 * @param int    $id    English object ID.
		 * @param bool   $force Translate every segment again, discarding edits.
		 */
	public function queue( string $kind, int $id, bool $force = false ): void {
		$this->state->set_status( $kind, $id, State::PENDING, 'queued' );
		as_enqueue_async_action( self::HOOK, array( $kind, $id, $force, 1 ), self::GROUP, true );
	}

	/**
	 * Runs a queued translation (action `linker_i18n_translate`).
	 *
	 * @param string $kind    State::POST or State::TERM.
	 * @param int    $id      English object ID.
	 * @param bool   $force   Translate every segment again.
	 * @param int    $attempt Which attempt this is.
	 */
	public function run( string $kind, int $id, bool $force = false, int $attempt = 1 ): void {
		try {
			$status = State::POST === $kind ? $this->translator->post( $id, $force ) : $this->translator->term( $id, $force );
		} catch ( TranslationFailed $failure ) {
			$this->state->set_status( $kind, $id, State::PENDING, $failure->getMessage() );
			if ( $failure->transient && $attempt < self::ATTEMPTS ) {
				as_schedule_single_action( time() + self::RETRY_MINUTES * MINUTE_IN_SECONDS, self::HOOK, array( $kind, $id, $force, $attempt + 1 ), self::GROUP );
			}
			return;
		}
		// Saved again while this run translated: the queue refused a second job then.
		if ( State::SYNCED === $status && ! $this->translator->current( $kind, $id ) ) {
			$this->queue( $kind, $id );
		}
	}
}
