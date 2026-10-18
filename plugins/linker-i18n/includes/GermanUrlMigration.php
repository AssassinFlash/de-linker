<?php
/**
 * Stored German addresses and their restorable migration.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/**
 * Changes German objects through native APIs; English is never a content target.
 *
 * @phpstan-type RouteRow array{id:int,type:string,old:string,new:string,url:string,target_url:string,source:int,before:array<string,string>,after:array<string,string>,seo_existed:bool,old_slugs:list<string>}
 */
final class GermanUrlMigration {

	/** First-run originals, retained across repeat applications. */
	public const BACKUP = 'linker_i18n_german_urls_backup';

	/** Runtime aliases are enabled only after applying the object data. */
	public const ACTIVE = 'linker_i18n_german_urls_active';

	/**
	 * Reviewed old/final paths keyed by English source identities.
	 *
	 * @return list<array{type:string,source:string,old:string,new:string,old_path:string,new_path:string}>
	 */
	private function manifest(): array {
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Checked-in local migration data.
		return json_decode( (string) file_get_contents( dirname( __DIR__ ) . '/content/german-urls.json' ), true, 512, JSON_THROW_ON_ERROR );
	}

	/**
	 * Previews field and URL changes in German, without writing.
	 *
	 * @return list<RouteRow>
	 */
	public function plan(): array {
		$languages = new Languages();
		$entered   = $languages->enter( 'de' );
		try {
			$rows   = $this->objects();
			$routes = new GermanRoutes();
			foreach ( $rows as &$row ) {
				foreach ( array( 'post_content', 'post_excerpt', 'description' ) as $field ) {
					if ( isset( $row['before'][ $field ] ) ) {
						$row['after'][ $field ] = $routes->rewrite_links( $row['before'][ $field ] );
					}
				}
				$row['after']  = array_diff_assoc( $row['after'], $row['before'] );
				$row['before'] = array_intersect_key( $row['before'], $row['after'] );
			}
			unset( $row );
			foreach ( get_posts(
				array(
					'post_type'   => 'nav_menu_item',
					'post_status' => 'any',
					'numberposts' => -1,
					'lang'        => '',
				)
			) as $item ) {
				$old = (string) get_post_meta( $item->ID, '_menu_item_url', true );
				$new = $routes->desired( $old );
				if ( $old !== $new ) {
					$rows[] = array(
						'id'          => $item->ID,
						'type'        => 'nav_menu_item',
						'old'         => '',
						'new'         => '',
						'url'         => '',
						'target_url'  => '',
						'source'      => 0,
						'before'      => array( 'meta:_menu_item_url' => $old ),
						'after'       => array( 'meta:_menu_item_url' => $new ),
						'seo_existed' => true,
						'old_slugs'   => array(),
					);
				}
			}
			return $rows;
		} finally {
			$languages->leave( $entered );
		}
	}

	/**
	 * Reads native objects and builds the desired German fields.
	 *
	 * @return list<RouteRow>
	 * @throws \RuntimeException Native objects cannot be read.
	 */
	private function objects(): array {
		$rows   = array();
		$titles = new GermanTitles();
		$routes = new GermanRoutes();
		$front  = (int) pll_get_post( (int) get_option( 'page_on_front' ), 'en' );
		foreach ( get_posts(
			array(
				'post_type'   => array( 'page', 'post', 'product' ),
				'post_status' => 'publish',
				'numberposts' => -1,
				'lang'        => 'de',
				'orderby'     => 'ID',
				'order'       => 'ASC',
			)
		) as $post ) {
			$source              = (int) pll_get_post( $post->ID, 'en' );
			$url                 = $source === $front ? ( new Languages() )->home_url( 'de' ) : (string) get_permalink( $post );
			$title               = $titles->post_title( $post );
			$before              = array(
				'post_name'                   => $post->post_name,
				'post_title'                  => $post->post_title,
				'post_content'                => $post->post_content,
				'post_excerpt'                => $post->post_excerpt,
				'meta:_seopress_titles_title' => (string) get_post_meta( $post->ID, '_seopress_titles_title', true ),
			);
			$after               = $before;
			$after['post_name']  = GermanSlugs::translated( $post->post_name );
			$after['post_title'] = $title;
			if ( $title !== $post->post_title ) {
				$after['meta:_seopress_titles_title'] = $title . ' | ' . get_bloginfo( 'name' );
			}
			$rows[] = array(
				'id'          => $post->ID,
				'type'        => $post->post_type,
				'old'         => $post->post_name,
				'new'         => $after['post_name'],
				'url'         => $url,
				'target_url'  => $routes->desired( $url ),
				'source'      => $source,
				'before'      => $before,
				'after'       => $after,
				'seo_existed' => metadata_exists( 'post', $post->ID, '_seopress_titles_title' ),
				'old_slugs'   => array_values( array_filter( get_post_meta( $post->ID, '_wp_old_slug', false ), 'is_string' ) ),
			);
		}
		$terms = get_terms(
			array(
				'taxonomy'   => array( 'category', 'product_cat' ),
				'lang'       => 'de',
				'hide_empty' => false,
			)
		);
		if ( is_wp_error( $terms ) ) {
			throw new \RuntimeException( esc_html( $terms->get_error_message() ) );
		}
		foreach ( $terms as $term ) {
			$url = get_term_link( $term );
			if ( is_wp_error( $url ) ) {
				throw new \RuntimeException( esc_html( $url->get_error_message() ) );
			}
			$before        = array(
				'slug'        => $term->slug,
				'name'        => $term->name,
				'description' => $term->description,
			);
			$after         = $before;
			$after['slug'] = GermanSlugs::translated( $term->slug );
			$after['name'] = $titles->term_title( $term );
			$rows[]        = array(
				'id'          => $term->term_id,
				'type'        => $term->taxonomy,
				'old'         => $term->slug,
				'new'         => $after['slug'],
				'url'         => $url,
				'target_url'  => $routes->desired( $url ),
				'source'      => (int) pll_get_term( $term->term_id, 'en' ),
				'before'      => $before,
				'after'       => $after,
				'seo_existed' => false,
				'old_slugs'   => array(),
			);
		}
		return $rows;
	}

	/**
	 * Applies a fully preflighted plan, preserving the first originals.
	 *
	 * @return int Changed objects.
	 * @throws \RuntimeException If a conflict or native write failure occurs.
	 */
	public function apply(): int {
		$rows   = array_values( array_filter( $this->preview(), static fn( array $row ): bool => array() !== $row['after'] ) );
		$backup = $this->backup();
		$this->check_originals( $backup );
		foreach ( $rows as $row ) {
			$this->preflight( $row );
			$key = $row['type'] . ':' . $row['id'];
			if ( ! isset( $backup[ $key ] ) ) {
				$backup[ $key ] = $row;
			}
		}
		if ( array() !== $rows ) {
			update_option(
				self::BACKUP,
				array(
					'version' => 1,
					'objects' => $backup,
				),
				false
			);
		}
		$notices = get_option( 'seopress_can_post_redirect', null );
		try {
			foreach ( $rows as $row ) {
				$this->write( $row, $row['after'] );
			}
		} finally {
			$this->restore_notices( $notices );
		}
		update_option( self::ACTIVE, true, false );
		$this->refresh_routes();
		return count( $rows );
	}

	/**
	 * Validates the entire preview before any migration write.
	 *
	 * @param bool $rollback Preview restoration instead of application.
	 * @return list<RouteRow>
	 * @throws \RuntimeException Source, target or original data conflicts.
	 */
	public function preview( bool $rollback = false ): array {
		$this->check_originals( $this->backup() );
		if ( ! $rollback ) {
			$this->reviewed_pairs();
		}
		$rows    = $rollback ? array_values( $this->backup() ) : $this->plan();
		$targets = array();
		foreach ( $rows as &$row ) {
			$this->identity( $row );
			if ( $rollback ) {
				$field = in_array( $row['type'], array( 'category', 'product_cat' ), true ) ? 'slug' : 'post_name';
				if ( isset( $row['before'][ $field ] ) ) {
					$current        = $this->read( $row, array( $field ) );
					$restore        = $row;
					$restore['old'] = $current[ $field ];
					$restore['new'] = $row['before'][ $field ];
					$this->preflight( $restore );
				}
				$current           = $this->read( $row, array_keys( $row['before'] ) );
				$row['before']     = array_diff_assoc( $row['before'], $current );
				$original_url      = $row['url'];
				$row['url']        = $row['target_url'];
				$row['target_url'] = $original_url;
			} else {
				$this->preflight( $row );
				if ( 'nav_menu_item' !== $row['type'] ) {
					if ( isset( $targets[ $row['target_url'] ] ) ) {
						throw new \RuntimeException( esc_html( 'Planned target collision: ' . $row['target_url'] ) );
					}
					$targets[ $row['target_url'] ] = true;
				}
			}
		}
		unset( $row );
		return $rows;
	}

	/**
	 * Requires the reviewed source pairs and accepts only their old or final slug.
	 *
	 * The manifest contains source slugs, never environment-specific object IDs.
	 *
	 * @throws \RuntimeException When reviewed data or a language pair has drifted.
	 */
	private function reviewed_pairs(): void {
		foreach ( $this->manifest() as $entry ) {
			$is_term = in_array( $entry['type'], array( 'category', 'product_cat' ), true );
			if ( $is_term ) {
				$matches = get_terms(
					array(
						'taxonomy'   => $entry['type'],
						'slug'       => $entry['source'],
						'lang'       => 'en',
						'hide_empty' => false,
					)
				);
				if ( is_wp_error( $matches ) || 1 !== count( $matches ) ) {
					throw new \RuntimeException( esc_html( 'Missing reviewed English term: ' . $entry['source'] ) );
				}
				$de   = get_term( (int) pll_get_term( $matches[0]->term_id, 'de' ), $entry['type'] );
				$slug = $de instanceof \WP_Term ? $de->slug : '';
			} else {
				$matches = get_posts(
					array(
						'post_type'     => $entry['type'],
						'post_status'   => 'publish',
						'post_name__in' => array( $entry['source'] ),
						'lang'          => 'en',
						'numberposts'   => 2,
					)
				);
				if ( 1 !== count( $matches ) ) {
					throw new \RuntimeException( esc_html( 'Missing reviewed English post: ' . $entry['source'] ) );
				}
				$de   = get_post( (int) pll_get_post( $matches[0]->ID, 'de' ) );
				$slug = $de instanceof \WP_Post ? $de->post_name : '';
			}
			if ( ! in_array( $slug, array( $entry['old'], $entry['new'] ), true ) ) {
				throw new \RuntimeException( esc_html( 'Unexpected German slug or missing pair: ' . $entry['type'] . ':' . $entry['source'] . ' (' . $slug . ')' ) );
			}
		}
	}

	/**
	 * Verifies stored migration state; HTTP acceptance separately checks rendered consumers.
	 *
	 * @throws \RuntimeException Migration is inactive or incomplete.
	 */
	public function verify(): void {
		$rows = $this->preview();
		if ( ! get_option( self::ACTIVE ) ) {
			throw new \RuntimeException( 'German URL migration is not active.' );
		}
		foreach ( $rows as $row ) {
			if ( array() !== $row['after'] ) {
				throw new \RuntimeException( esc_html( 'Pending German fields: ' . $row['type'] . ':' . $row['id'] . ' ' . implode( ', ', array_keys( $row['after'] ) ) ) );
			}
		}
		$written = get_option( 'rewrite_rules', array() );
		foreach ( ( new GermanRoutes() )->rules( array() ) as $rule => $target ) {
			if ( ! is_array( $written ) || ( $written[ $rule ] ?? null ) !== $target ) {
				throw new \RuntimeException( esc_html( 'German rewrite rule missing: ' . $rule ) );
			}
		}
	}

	/**
	 * Rebuilds native rules after removing a stale autoloaded option-cache copy.
	 *
	 * A cached old rules array alongside the already-updated database makes
	 * update_option return early, leaving new routes at 404. These are this
	 * WordPress site's option keys; no Redis database or other instance is flushed.
	 */
	private function refresh_routes(): void {
		wp_cache_delete( 'alloptions', 'options' );
		wp_cache_delete( 'rewrite_rules', 'options' );
		flush_rewrite_rules( false );
	}

	/**
	 * Restores owned fields and native slug history without consuming the backup.
	 *
	 * @return int Restored objects.
	 */
	public function rollback(): int {
		$backup = $this->backup();
		$this->preview( true );
		$changed = 0;
		$notices = get_option( 'seopress_can_post_redirect', null );
		try {
			foreach ( $backup as $row ) {
				if ( $this->read( $row, array_keys( $row['before'] ) ) !== $row['before'] ) {
					$this->write( $row, $row['before'], true );
					++$changed;
				}
			}
		} finally {
			$this->restore_notices( $notices );
		}
		delete_option( self::ACTIVE );
		$this->refresh_routes();
		return $changed;
	}

	/**
	 * Returns the first originals; unknown formats cannot be silently overwritten.
	 *
	 * @return array<string,RouteRow>
	 * @throws \RuntimeException The saved backup format is unknown.
	 */
	public function backup(): array {
		$value = get_option( self::BACKUP, null );
		if ( null === $value ) {
			return array();
		}
		if ( ! is_array( $value ) || 1 !== ( $value['version'] ?? null ) || ! is_array( $value['objects'] ?? null ) ) {
			throw new \RuntimeException( 'Unrecognised migration backup; original data retained.' );
		}
		return $value['objects'];
	}

	/**
	 * Checks every saved field before any new write or rollback.
	 *
	 * @param array<string,RouteRow> $backup First originals.
	 * @throws \RuntimeException An owned field changed outside the migration.
	 */
	private function check_originals( array $backup ): void {
		foreach ( $backup as $row ) {
			$this->identity( $row );
			foreach ( $this->read( $row, array_keys( $row['before'] ) ) as $field => $value ) {
				if ( $value !== $row['before'][ $field ] && $value !== $row['after'][ $field ] ) {
					throw new \RuntimeException( esc_html( 'Changed outside migration: ' . $row['type'] . ':' . $row['id'] . ' ' . $field ) );
				}
			}
		}
	}

	/**
	 * Requires the same language pair, never just a reused numeric ID.
	 *
	 * @param array $row Object identity.
	 * @throws \RuntimeException The language pair no longer exists.
	 * @phpstan-param RouteRow $row
	 */
	private function identity( array $row ): void {
		if ( 'nav_menu_item' === $row['type'] ) {
			$valid = 'nav_menu_item' === get_post_type( $row['id'] );
		} elseif ( in_array( $row['type'], array( 'category', 'product_cat' ), true ) ) {
			$term  = get_term( $row['id'], $row['type'] );
			$valid = $term instanceof \WP_Term && 'de' === pll_get_term_language( $row['id'] ) && 0 < $row['source'] && (int) pll_get_term( $row['id'], 'en' ) === $row['source'];
		} else {
			$valid = get_post_type( $row['id'] ) === $row['type'] && 'de' === pll_get_post_language( $row['id'] ) && 0 < $row['source'] && (int) pll_get_post( $row['id'], 'en' ) === $row['source'];
		}
		if ( ! $valid ) {
			throw new \RuntimeException( esc_html( 'Missing or changed language pair: ' . $row['type'] . ':' . $row['id'] ) );
		}
	}

	/**
	 * Rejects occupied slugs before saving any original or changing any object.
	 *
	 * @param array $row Planned object.
	 * @throws \RuntimeException The target slug is occupied or missing.
	 * @phpstan-param RouteRow $row
	 */
	private function preflight( array $row ): void {
		$this->identity( $row );
		if ( $row['old'] === $row['new'] ) {
			return;
		}
		if ( in_array( $row['type'], array( 'category', 'product_cat' ), true ) ) {
			$holders = get_terms(
				array(
					'taxonomy'   => $row['type'],
					'lang'       => 'de',
					'slug'       => $row['new'],
					'hide_empty' => false,
					'exclude'    => array( $row['id'] ),
				)
			);
		} else {
			$parent = wp_get_post_parent_id( $row['id'] );
			if ( false === $parent ) {
				throw new \RuntimeException( 'Migration target no longer exists.' );
			}
			$holders = get_posts(
				array(
					'post_type'     => $row['type'],
					'post_status'   => 'any',
					'numberposts'   => -1,
					'lang'          => 'de',
					'post_name__in' => array( $row['new'] ),
					'post_parent'   => $parent,
					'post__not_in'  => array( $row['id'] ),
				)
			);
		}
		if ( is_wp_error( $holders ) || array() !== $holders ) {
			throw new \RuntimeException( esc_html( 'Target slug occupied: ' . $row['new'] ) );
		}
	}

	/**
	 * Reads only fields the migration owns on this object.
	 *
	 * @param array $row Object identity.
	 * @param array $fields Field names.
	 * @return array<string,string>
	 * @throws \RuntimeException A field or object no longer exists.
	 * @phpstan-param RouteRow $row
	 * @phpstan-param list<string> $fields
	 */
	private function read( array $row, array $fields ): array {
		$term   = in_array( $row['type'], array( 'category', 'product_cat' ), true ) ? get_term( $row['id'], $row['type'] ) : null;
		$values = array();
		foreach ( $fields as $field ) {
			if ( str_starts_with( $field, 'meta:' ) ) {
				$values[ $field ] = (string) get_post_meta( $row['id'], substr( $field, 5 ), true );
			} elseif ( $term instanceof \WP_Term ) {
				$values[ $field ] = match ( $field ) {
					'slug' => $term->slug,
					'name' => $term->name,
					'description' => $term->description,
					default => throw new \RuntimeException( 'Unknown migration term field.' ),
				};
			} else {
				$post = get_post( $row['id'] );
				if ( ! $post instanceof \WP_Post ) {
					throw new \RuntimeException( 'Migration post no longer exists.' );
				}
				$values[ $field ] = match ( $field ) {
					'post_name' => $post->post_name,
					'post_title' => $post->post_title,
					'post_content' => $post->post_content,
					'post_excerpt' => $post->post_excerpt,
					default => throw new \RuntimeException( 'Unknown migration post field.' ),
				};
			}
		}
		return $values;
	}

	/**
	 * Writes through native APIs and checks the actual resulting values.
	 *
	 * @param array                $row Object identity and originals.
	 * @param array<string,string> $fields Desired native fields.
	 * @param bool                 $restore Restore metadata presence and native history too.
	 * @throws \RuntimeException A native write fails or its readback disagrees.
	 * @phpstan-param RouteRow $row
	 */
	private function write( array $row, array $fields, bool $restore = false ): void {
		$data = array();
		foreach ( $fields as $field => $value ) {
			if ( str_starts_with( $field, 'meta:' ) ) {
				$key = substr( $field, 5 );
				if ( $restore && '_seopress_titles_title' === $key && ! $row['seo_existed'] ) {
					delete_post_meta( $row['id'], $key );
				} else {
					update_post_meta( $row['id'], $key, wp_slash( $value ) );
				}
			} else {
				$data[ $field ] = $value;
			}
		}
		if ( array() !== $data ) {
			if ( in_array( $row['type'], array( 'category', 'product_cat' ), true ) ) {
				$term_data = array();
				if ( isset( $data['slug'] ) ) {
					$term_data['slug'] = wp_slash( $data['slug'] );
				}
				if ( isset( $data['name'] ) ) {
					$term_data['name'] = wp_slash( $data['name'] );
				}
				if ( isset( $data['description'] ) ) {
					$term_data['description'] = wp_slash( $data['description'] );
				}
				$result = wp_update_term( $row['id'], $row['type'], $term_data );
			} else {
				$post_data = array( 'ID' => $row['id'] );
				if ( isset( $data['post_name'] ) ) {
					$post_data['post_name'] = wp_slash( $data['post_name'] );
				}
				if ( isset( $data['post_title'] ) ) {
					$post_data['post_title'] = wp_slash( $data['post_title'] );
				}
				if ( isset( $data['post_content'] ) ) {
					$post_data['post_content'] = wp_slash( $data['post_content'] );
				}
				if ( isset( $data['post_excerpt'] ) ) {
					$post_data['post_excerpt'] = wp_slash( $data['post_excerpt'] );
				}
				$result = wp_update_post( $post_data, true );
			}
			if ( is_wp_error( $result ) ) {
				throw new \RuntimeException( esc_html( $result->get_error_message() ) );
			}
		}
		if ( $restore && isset( $fields['post_name'] ) ) {
			delete_post_meta( $row['id'], '_wp_old_slug' );
			foreach ( $row['old_slugs'] as $slug ) {
				add_post_meta( $row['id'], '_wp_old_slug', $slug );
			}
		}
		if ( $this->read( $row, array_keys( $fields ) ) !== $fields ) {
			throw new \RuntimeException( esc_html( 'Native readback mismatch: ' . $row['type'] . ':' . $row['id'] ) );
		}
	}

	/**
	 * Explicit compatibility already covers renamed URLs; preserve existing notices.
	 *
	 * @param mixed $notices The pre-operation SEOPress notice state.
	 */
	private function restore_notices( $notices ): void {
		if ( null === $notices ) {
			delete_option( 'seopress_can_post_redirect' );
		} else {
			update_option( 'seopress_can_post_redirect', $notices );
		}
	}

	/**
	 * Native product history must not select another language's post.
	 *
	 * @param int $id Candidate from WordPress's old-slug lookup.
	 */
	public function old_post( int $id ): int {
		if ( 'de' !== pll_current_language() || 0 === $id || 'de' === pll_get_post_language( $id ) ) {
			return $id;
		}
		// Core's first historical match can belong to English. Query the same
		// native history metadata in German before accepting a destination.
		$type = get_post_type( $id );
		if ( false === $type ) {
			return 0;
		}
		$posts = get_posts(
			array(
				'post_type'   => $type,
				'post_status' => 'publish',
				'lang'        => 'de',
				'numberposts' => 1,
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_key -- WordPress's native historical slug lookup, constrained to the requested language.
				'meta_key'    => '_wp_old_slug',
				// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_value -- Same native lookup, never a new redirect store.
				'meta_value'  => (string) get_query_var( 'name' ),
			)
		);
		return isset( $posts[0] ) ? $posts[0]->ID : 0;
	}

	/**
	 * Preserves opaque query values on native history redirects.
	 *
	 * @param string $url Native destination.
	 */
	public function old_url( string $url ): string {
		if ( 'de' !== pll_current_language() ) {
			return $url;
		}
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- opaque query, appended verbatim to a server-selected local URL.
		$query = isset( $_SERVER['QUERY_STRING'] ) ? wp_unslash( $_SERVER['QUERY_STRING'] ) : '';
		return '' === $query ? $url : $url . '?' . $query;
	}

	/**
	 * Supplies page and term history to the existing redirect dispatcher.
	 *
	 * @param string|null $target Earlier destination.
	 * @param string      $path Requested full path.
	 */
	public function retired_url( ?string $target, string $path ): ?string {
		if ( null !== $target || ! get_option( self::ACTIVE ) || ! str_starts_with( $path, '/de/' ) ) {
			return $target;
		}
		$routes = new GermanRoutes();
		foreach ( $this->backup() as $row ) {
			$old_path = wp_parse_url( $row['url'], PHP_URL_PATH );
			if ( in_array( $row['type'], array( 'product', 'nav_menu_item' ), true ) || ! is_string( $old_path ) || ! str_starts_with( $path, $old_path ) ) {
				continue;
			}
			$url = in_array( $row['type'], array( 'category', 'product_cat' ), true ) ? get_term_link( $row['id'], $row['type'] ) : get_permalink( $row['id'] );
			if ( is_string( $url ) && wp_parse_url( $url, PHP_URL_PATH ) !== $old_path ) {
				$url = $routes->link( $url . substr( $path, strlen( $old_path ) ) );
				return $this->old_url( $url );
			}
		}
		foreach ( $this->manifest() as $entry ) {
			if ( 'product' !== $entry['type'] && str_starts_with( $path, $entry['old_path'] ) ) {
				$url = untrailingslashit( ( new Languages() )->home_url( 'en' ) ) . $entry['new_path'] . substr( $path, strlen( $entry['old_path'] ) );
				return $this->old_url( $routes->link( $url ) );
			}
		}
		return $routes->category_history( $path ) ?? $routes->endpoint_history( $path );
	}
}
