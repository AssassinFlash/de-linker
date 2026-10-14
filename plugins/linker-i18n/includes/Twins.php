<?php
/**
 * Writes German versions of English posts and terms.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\Fields;
use Linker\I18n\Woo\Projection;

/**
 * Creates and updates the German version of an English object: a post or
 * term of its own, in Polylang's translation group, with the English
 * object's structure (parent, order, template, image, categories,
 * attributes, LiveCanvas settings) and the German text it is given.
 *
 * A new German object gets its slug in a second step, once it has its
 * language, so a slug shared with the English object is allowed
 * (docs/research/2026-10-09/i18n-opensource-replication.md §5.3). Content is
 * written without WordPress's HTML filter: it is the English content's
 * markup, which an editor allowed to post unfiltered HTML wrote, and
 * background jobs run without a user, for whom kses would strip the
 * LiveCanvas scripts and styles.
 */
final class Twins {

	/**
	 * Meta copied from the English post as it is: the page template, the
	 * featured image (media is not translated), LiveCanvas's switch and
	 * template choice (`_lc_livecanvas_enabled`, `lc_use_template_of_slug`;
	 * LiveCanvas 4.9.3 livecanvas-plugin-index.php:233, modules/templating.php:110).
	 */
	private const COPIED_META = array( '_wp_page_template', '_thumbnail_id', '_lc_livecanvas_enabled', 'lc_use_template_of_slug' );

	/**
	 * Term meta copied from the English term as it is: WooCommerce's
	 * category order, display type and image (media is not translated).
	 */
	private const COPIED_TERM_META = array( 'order', 'display_type', 'thumbnail_id' );

	/**
	 * Post types whose `is_*` meta says where LiveCanvas uses them
	 * (is_header, is_single_product, …). The German copy needs it too: on a
	 * German page Polylang shows LiveCanvas only German partials and
	 * templates (LiveCanvas 4.9.3 modules/templating.php:149).
	 */
	private const LIVECANVAS_TYPES = array( 'lc_partial', 'lc_dynamic_template' );

	/**
	 * Whether this class is writing (its own saves are not edits by a person).
	 *
	 * @var bool
	 */
	private bool $writing = false;

	/**
	 * Sets up the writer.
	 *
	 * @param Languages     $languages  The site's languages.
	 * @param LinkLocalizer $links      Rewrites links to German pages.
	 * @param Projection    $projection Copies a product's commerce fields.
	 */
	public function __construct(
		private readonly Languages $languages,
		private readonly LinkLocalizer $links,
		private readonly Projection $projection
	) {}

	/**
	 * Whether this class is writing right now.
	 */
	public function writing(): bool {
		return $this->writing;
	}

	/**
	 * Creates or updates the German version of an English post.
	 *
	 * @param int                   $source_id English post ID.
	 * @param array<string, string> $values    German values: post_title, post_excerpt, post_content, meta:<key>.
	 * @param string|null           $slug      Slug of a new German post; the English slug for products, the German title's otherwise.
	 * @return int German post ID.
	 * @throws \RuntimeException When WordPress refuses the post.
	 */
	public function post( int $source_id, array $values, ?string $slug = null ): int {
		$source = get_post( $source_id );
		if ( ! $source instanceof \WP_Post ) {
			throw new \RuntimeException( esc_html( sprintf( 'No post %d.', $source_id ) ) );
		}
		$twin          = $this->languages->post_translation( $source_id, Languages::TARGET );
		$postarr       = array(
			'post_type'      => $source->post_type,
			'post_status'    => $source->post_status,
			'post_author'    => $source->post_author,
			'post_parent'    => $this->parent( $source ),
			'menu_order'     => $source->menu_order,
			'comment_status' => $source->comment_status,
			'ping_status'    => $source->ping_status,
			'post_password'  => $source->post_password,
			'post_title'     => $values['post_title'] ?? '',
			'post_excerpt'   => $this->links->localize( $values['post_excerpt'] ?? '' ),
			'post_content'   => $this->links->localize( $values['post_content'] ?? '' ),
		);
		$this->writing = true;
		$kses          = $this->suspend_kses();
		$defaulting    = $this->suspend_default_category();
		try {
			if ( null === $twin ) {
				$postarr['post_date']     = $source->post_date;
				$postarr['post_date_gmt'] = $source->post_date_gmt;
				$twin                     = $this->insert( $postarr );
				$this->ensure_post_pair( $source_id, $twin );
				$this->update(
					array(
						'ID'        => $twin,
						'post_name' => $slug ?? ( 'product' === $source->post_type ? $source->post_name : sanitize_title( $postarr['post_title'] ) ),
					)
				);
			} else {
				$update = array( 'ID' => $twin ) + $postarr;
				if ( null !== $slug ) {
					// An adopt() that names a slug renames the German version:
					// the migration is the authority for it (a re-run after a
					// slug correction must take, or the first run's slug stays
					// forever). translate() passes none and keeps the slug.
					$update['post_name'] = $slug;
				}
				$this->ensure_post_pair( $source_id, $twin );
				$this->update( $update );
			}
			$this->meta( $source, $twin, $values );
			$this->terms( $source, $twin );
			if ( is_post_type_hierarchical( $source->post_type ) ) {
				$this->adopt_children( $source_id, $twin );
			}
		} finally {
			$this->restore_kses( $kses );
			$this->restore_default_category( $defaulting );
			$this->writing = false;
		}
		if ( 'product' === $source->post_type ) {
			$this->projection->project( $source_id );
		}
		return $twin;
	}

	/**
	 * Suspends WooCommerce's default-category forcing while the German
	 * product's terms mirror the English ones: an empty list is the English
	 * product having none, and the forced default is an English term - its
	 * assignment would make Polylang's term sync create the German default
	 * term, a category the site's German has no use for (the ones language
	 * creation makes are removed by Setup::drop_default_terms()).
	 *
	 * @return bool Whether the hook was there.
	 */
	private function suspend_default_category(): bool {
		return remove_action( 'set_object_terms', array( \WC_Post_Data::class, 'force_default_term' ), 10 );
	}

	/**
	 * Puts the suspended hook back.
	 *
	 * @param bool $suspended What suspend_default_category() returned.
	 */
	private function restore_default_category( bool $suspended ): void {
		if ( $suspended ) {
			add_action( 'set_object_terms', array( \WC_Post_Data::class, 'force_default_term' ), 10, 5 );
		}
	}

	/**
	 * Creates or updates the German version of an English term.
	 *
	 * @param int                   $term_id English term ID.
	 * @param array<string, string> $values  German values: name, description.
	 * @param string|null           $slug    Slug of a new German term; the German name's by default.
	 * @return int German term ID.
	 * @throws \RuntimeException When WordPress refuses the term.
	 */
	public function term( int $term_id, array $values, ?string $slug = null ): int {
		$source = get_term( $term_id );
		if ( ! $source instanceof \WP_Term ) {
			throw new \RuntimeException( esc_html( sprintf( 'No term %d.', $term_id ) ) );
		}
		$twin          = $this->languages->term_translation( $term_id, Languages::TARGET );
		$parent        = 0 === $source->parent ? 0 : absint( $this->languages->term_translation( $source->parent, Languages::TARGET ) );
		$args          = array(
			'name'        => $values['name'] ?? $source->name,
			'description' => $this->links->localize( $values['description'] ?? '' ),
			'parent'      => $parent,
		);
		$this->writing = true;
		$kses          = $this->suspend_kses();
		$defaulting    = $this->suspend_default_category();
		try {
			if ( null === $twin ) {
				// A placeholder slug first: the German slug may equal the English one,
				// which is allowed only once the term has its language (SameSlug\TermSlugs).
				$created = wp_insert_term( wp_slash( $args['name'] ), $source->taxonomy, wp_slash( array( 'slug' => 'linker-i18n-' . wp_generate_uuid4() ) + $args ) );
				if ( is_wp_error( $created ) ) {
					throw new \RuntimeException( esc_html( $created->get_error_message() ) );
				}
				$twin = (int) $created['term_id'];
				$this->ensure_term_pair( $term_id, $twin );
				$args['slug'] = $slug ?? sanitize_title( $args['name'] );
			} else {
				$this->ensure_term_pair( $term_id, $twin );
				if ( null !== $slug ) {
					// An adopt() that names a slug renames the German term:
					// the migration is the authority for it (a re-run after a
					// slug correction must take, or the first run's slug stays
					// forever). translate() passes none and keeps the slug.
					$args['slug'] = $slug;
				}
			}
			$updated = wp_update_term( $twin, $source->taxonomy, wp_slash( $args ) );
			if ( is_wp_error( $updated ) ) {
				throw new \RuntimeException( esc_html( $updated->get_error_message() ) );
			}
			foreach ( self::COPIED_TERM_META as $key ) {
				$value = get_term_meta( $term_id, $key, true );
				if ( '' !== $value ) {
					update_term_meta( $twin, $key, $value );
				}
			}
			// Every write, not only the first: the German term may already
			// exist when the English posts get their categories (the
			// migration creates the term before the posts), and a later
			// adopt() must put the posts back. Polylang's term sync runs on
			// set_object_terms while writing is still true, so it does not
			// treat this as a person's edit.
			$this->assign_term( $source, $twin );
		} finally {
			$this->restore_kses( $kses );
			$this->restore_default_category( $defaulting );
			$this->writing = false;
		}
		return $twin;
	}

	/**
	 * Gives the German post the status of the English one, when it has a
	 * German post: an English page taken offline takes its German page with it.
	 *
	 * @param int $source_id English post ID.
	 */
	public function follow_status( int $source_id ): void {
		$source = get_post( $source_id );
		$twin   = $this->languages->post_translation( $source_id, Languages::TARGET );
		if ( ! $source instanceof \WP_Post || null === $twin || get_post_status( $twin ) === $source->post_status ) {
			return;
		}
		$this->writing = true;
		try {
			if ( 'trash' === $source->post_status ) {
				wp_trash_post( $twin );
			} else {
				$this->update(
					array(
						'ID'          => $twin,
						'post_status' => $source->post_status,
					)
				);
			}
		} finally {
			$this->writing = false;
		}
	}

	/**
	 * Makes an English post and its German version a proper Polylang pair:
	 * both carry their language and the translation group names them.
	 *
	 * A source without a language is the snapshot's LiveCanvas partial
	 * (a header or footer arrives languageless); Polylang's
	 * pll_save_post_translations() silently skips a languageless member,
	 * which left the German partial unpaired and LiveCanvas's ID-ordered
	 * partial lookup grabbing it for every language. The source is English,
	 * so it says so before pairing, and an update of an already-written pair
	 * repairs the languages the same way.
	 *
	 * @param int $source_id English post ID.
	 * @param int $twin      German post ID.
	 */
	private function ensure_post_pair( int $source_id, int $twin ): void {
		if ( Languages::SOURCE !== $this->languages->of_post( $source_id ) ) {
			$this->languages->set_post_language( $source_id, Languages::SOURCE );
		}
		if ( Languages::TARGET !== $this->languages->of_post( $twin ) ) {
			$this->languages->set_post_language( $twin, Languages::TARGET );
		}
		if ( null === $this->languages->post_translation( $source_id, Languages::TARGET ) ) {
			$this->languages->pair_posts( $source_id, $twin );
		}
	}

	/**
	 * The terms' counterpart of ensure_post_pair().
	 *
	 * @param int $term_id English term ID.
	 * @param int $twin    German term ID.
	 */
	private function ensure_term_pair( int $term_id, int $twin ): void {
		if ( Languages::SOURCE !== $this->languages->of_term( $term_id ) ) {
			$this->languages->set_term_language( $term_id, Languages::SOURCE );
		}
		if ( Languages::TARGET !== $this->languages->of_term( $twin ) ) {
			$this->languages->set_term_language( $twin, Languages::TARGET );
		}
		if ( null === $this->languages->term_translation( $term_id, Languages::TARGET ) ) {
			$this->languages->pair_terms( $term_id, $twin );
		}
	}

	/**
	 * Inserts a post.
	 *
	 * @param array<string, mixed> $postarr Post fields.
	 * @throws \RuntimeException When WordPress refuses it.
	 */
	private function insert( array $postarr ): int {
		$id = wp_insert_post( wp_slash( $postarr ), true );
		if ( is_wp_error( $id ) ) {
			throw new \RuntimeException( esc_html( $id->get_error_message() ) );
		}
		return $id;
	}

	/**
	 * Updates a post.
	 *
	 * @param array<string, mixed> $postarr Post fields with ID.
	 * @throws \RuntimeException When WordPress refuses it.
	 */
	private function update( array $postarr ): void {
		$id = wp_update_post( wp_slash( $postarr ), true );
		if ( is_wp_error( $id ) ) {
			throw new \RuntimeException( esc_html( $id->get_error_message() ) );
		}
	}

	/**
	 * The German parent of a post: the German version of its English parent.
	 *
	 * @param \WP_Post $source English post.
	 */
	private function parent( \WP_Post $source ): int {
		if ( 0 === $source->post_parent ) {
			return 0;
		}
		return $this->languages->post_translation( $source->post_parent, Languages::TARGET ) ?? 0;
	}

	/**
	 * Copies the structural meta and writes the translated meta.
	 *
	 * @param \WP_Post              $source English post.
	 * @param int                   $twin   German post ID.
	 * @param array<string, string> $values German values.
	 */
	private function meta( \WP_Post $source, int $twin, array $values ): void {
		$all = get_post_meta( $source->ID );
		foreach ( $all as $key => $meta ) {
			$key    = (string) $key;
			$copied = in_array( $key, self::COPIED_META, true ) || ( in_array( $source->post_type, self::LIVECANVAS_TYPES, true ) && str_starts_with( $key, 'is_' ) );
			if ( $copied && isset( $meta[0] ) ) {
				update_post_meta( $twin, $key, wp_slash( maybe_unserialize( $meta[0] ) ) );
			}
		}
		foreach ( $values as $field => $value ) {
			if ( ! str_starts_with( $field, Fields::META ) ) {
				continue;
			}
			$key = substr( $field, strlen( Fields::META ) );
			if ( '' === $value ) {
				delete_post_meta( $twin, $key );
			} else {
				update_post_meta( $twin, $key, wp_slash( $value ) );
			}
		}
	}

	/**
	 * Gives the German post the English post's terms: the German term of a
	 * translated taxonomy (when there is one), the same term otherwise.
	 *
	 * @param \WP_Post $source English post.
	 * @param int      $twin   German post ID.
	 */
	private function terms( \WP_Post $source, int $twin ): void {
		foreach ( get_object_taxonomies( $source->post_type ) as $taxonomy ) {
			if ( in_array( $taxonomy, array( 'language', 'post_translations' ), true ) ) {
				continue;
			}
			$ids = wp_get_object_terms( $source->ID, $taxonomy, array( 'fields' => 'ids' ) );
			if ( ! is_array( $ids ) ) {
				continue;
			}
			$ids = array_map( 'intval', $ids );
			if ( $this->languages->translates_taxonomy( $taxonomy ) ) {
				$ids = array_values( array_filter( array_map( fn( int $id ): ?int => $this->languages->term_translation( $id, Languages::TARGET ), $ids ) ) );
			}
			wp_set_object_terms( $twin, $ids, $taxonomy );
		}
	}

	/**
	 * Gives the German term to the English posts that have the English term,
	 * and to their German versions (Polylang does this only for a user who may
	 * assign terms, never in a background job).
	 *
	 * Both sides: the English relationship is the source the archive and the
	 * single page read, and the German version needs its own term of the same
	 * taxonomy. A post that has no German version yet is covered when the post
	 * itself is written (terms()).
	 *
	 * @param \WP_Term $source English term.
	 * @param int      $twin   German term ID.
	 */
	private function assign_term( \WP_Term $source, int $twin ): void {
		$posts = get_objects_in_term( $source->term_id, $source->taxonomy );
		if ( ! is_array( $posts ) ) {
			return;
		}
		foreach ( $posts as $post_id ) {
			$post_id = (int) $post_id;
			wp_set_object_terms( $post_id, array( $source->term_id ), $source->taxonomy, true );
			$german = $this->languages->post_translation( $post_id, Languages::TARGET );
			if ( null !== $german ) {
				wp_set_object_terms( $german, array( $twin ), $source->taxonomy, true );
			}
		}
	}

	/**
	 * Hangs the German versions of the English children under the new German parent.
	 *
	 * @param int $source_id English parent ID.
	 * @param int $twin      German parent ID.
	 */
	private function adopt_children( int $source_id, int $twin ): void {
		foreach ( get_children(
			array(
				'post_parent' => $source_id,
				'post_type'   => get_post_type( $source_id ),
			)
		) as $child ) {
			$german = $this->languages->post_translation( $child->ID, Languages::TARGET );
			if ( null !== $german && wp_get_post_parent_id( $german ) !== $twin ) {
				$this->update(
					array(
						'ID'          => $german,
						'post_parent' => $twin,
					)
				);
			}
		}
	}

	/**
	 * Takes WordPress's HTML filter off for this write.
	 *
	 * @return bool Whether it was on.
	 */
	private function suspend_kses(): bool {
		$on = false !== has_filter( 'content_save_pre', 'wp_filter_post_kses' );
		if ( $on ) {
			kses_remove_filters();
		}
		return $on;
	}

	/**
	 * Puts WordPress's HTML filter back when it was on.
	 *
	 * @param bool $was_on What suspend_kses() returned.
	 */
	private function restore_kses( bool $was_on ): void {
		if ( $was_on ) {
			kses_init_filters();
		}
	}
}
