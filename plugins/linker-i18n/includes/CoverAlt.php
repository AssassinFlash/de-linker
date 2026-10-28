<?php
/**
 * Translation lifecycle and display value for blog cover alternatives.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;

/** The attachment owns English; the German post owns its translated value. */
final class CoverAlt {
	public const DISPLAY = '_linker_i18n_cover_alt_display';

	/**
	 * Sources captured before an attachment is deleted.
	 *
	 * @var array<int, list<int>>
	 */
	private array $deleting = array();

	/**
	 * Sets up the cover field and its translation lifecycle.
	 *
	 * @param Languages  $languages Site languages.
	 * @param Translator $translator Translation and baseline writer.
	 * @param Jobs       $jobs Background translation queue.
	 * @param Twins      $twins German writer.
	 * @param State      $state Translation fingerprints.
	 * @param Segmenter  $segmenter Fingerprints plain text.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly Translator $translator,
		private readonly Jobs $jobs,
		private readonly Twins $twins,
		private readonly State $state,
		private readonly Segmenter $segmenter
	) {}

	/**
	 * A virtual post meta field for LiveCanvas. Never show a stale translation:
	 * both its recorded source and output must still match, and the German
	 * post must show the same attachment as the source. Otherwise the actual
	 * displayed image's current attachment alt is the honest fallback.
	 *
	 * @param mixed  $value Earlier metadata filter result.
	 * @param int    $post_id Post ID.
	 * @param string $key Meta key.
	 * @return mixed
	 */
	public function display( mixed $value, int $post_id, string $key ): mixed {
		if ( null !== $value || self::DISPLAY !== $key ) {
			return $value;
		}
		$post = get_post( $post_id );
		if ( ! $post instanceof \WP_Post || 'post' !== $post->post_type ) {
			return $value;
		}
		$image    = (int) get_post_thumbnail_id( $post_id );
		$fallback = $image ? (string) get_post_meta( $image, '_wp_attachment_image_alt', true ) : '';
		$source   = Languages::TARGET === $this->languages->of_post( $post_id ) ? $this->languages->source_post( $post_id ) : null;
		if ( null === $source || ! $image || (int) get_post_thumbnail_id( $source ) !== $image || '' === trim( $fallback ) ) {
			return array( $fallback );
		}
		$field = Fields::META . Fields::COVER_ALT;
		$unit  = $this->state->units( State::POST, $post_id )[ $field ] ?? null;
		$alt   = (string) get_post_meta( $post_id, Fields::COVER_ALT, true );
		if ( null === $unit || $unit['conflict'] || '' === trim( $alt ) || $unit['src'] !== $this->segmenter->text( $fallback )->hashes() || $unit['out'] !== $this->segmenter->text( $alt )->hashes() ) {
			return array( $fallback );
		}
		return array( $alt );
	}

	/**
	 * Capture an existing German baseline before metadata changes.
	 *
	 * @param mixed  $check Earlier filter result.
	 * @param int    $id Post or attachment ID.
	 * @param string $key Metadata key.
	 * @return mixed
	 */
	public function before_meta( mixed $check, int $id, string $key ): mixed {
		if ( null === $check && ! $this->twins->writing() ) {
			foreach ( $this->sources( $id, $key ) as $source ) {
				$this->translator->prime( State::POST, $source );
			}
		}
		return $check;
	}

	/**
	 * Queue only after a metadata mutation really succeeded.
	 *
	 * @param mixed  $meta_id Metadata ID or IDs.
	 * @param int    $id Post or attachment ID.
	 * @param string $key Metadata key.
	 */
	public function after_meta( mixed $meta_id, int $id, string $key ): void {
		unset( $meta_id );
		if ( ! $this->twins->writing() ) {
			foreach ( $this->sources( $id, $key ) as $source ) {
				$this->jobs->queue( State::POST, $source );
			}
		}
	}

	/**
	 * Capture consumers before WordPress bulk-deletes their thumbnail meta.
	 *
	 * @param int $id Attachment ID.
	 */
	public function before_attachment_delete( int $id ): void {
		$this->deleting[ $id ] = $this->sources( $id, '_wp_attachment_image_alt' );
		foreach ( $this->deleting[ $id ] as $source ) {
			$this->translator->prime( State::POST, $source );
		}
	}

	/**
	 * Queue after successful deletion, when the thumbnail metadata is gone.
	 *
	 * @param int $id Deleted post ID.
	 */
	public function after_post_delete( int $id ): void {
		foreach ( $this->deleting[ $id ] ?? array() as $source ) {
			$this->jobs->queue( State::POST, $source );
		}
		unset( $this->deleting[ $id ] );
	}

	/**
	 * Find live English blog posts affected by this metadata.
	 *
	 * @param int    $id Post or attachment ID.
	 * @param string $key Metadata key.
	 * @return list<int>
	 */
	private function sources( int $id, string $key ): array {
		if ( $id < 1 || ! in_array( $key, array( '_thumbnail_id', '_wp_attachment_image_alt' ), true ) ) {
			return array();
		}
		$post = get_post( $id );
		if ( ! $post instanceof \WP_Post ) {
			return array();
		}
		if ( '_thumbnail_id' === $key && 'post' === $post->post_type ) {
			$ids = array( $id );
		} elseif ( '_wp_attachment_image_alt' === $key && 'attachment' === $post->post_type ) {
			$ids = get_posts(
				array(
					'post_type'        => 'post',
					'post_status'      => array( 'publish', 'future', 'private' ),
					'posts_per_page'   => -1,
					'fields'           => 'ids',
					'lang'             => '',
					'meta_key'         => '_thumbnail_id', // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- Find every post sharing this attachment.
					'meta_value'       => (string) $id, // phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Match the changed attachment only.
					'suppress_filters' => true,
				)
			);
		} else {
			return array();
		}
		return array_values(
			array_filter(
				array_map( 'intval', $ids ),
				fn( int $source ): bool => Languages::SOURCE === $this->languages->of_post( $source ) && in_array( get_post_status( $source ), array( 'publish', 'future', 'private' ), true )
			)
		);
	}
}
