<?php
/**
 * Native LC assignment metadata for existing public product taxonomies.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** Keeps the existing product-archive template reachable when its loop is empty. */
final class ArchiveAssignments {

	/**
	 * Generic keys exposed by LC for the site's registered public product taxa.
	 *
	 * @return list<string>
	 */
	public function keys(): array {
		$keys = array();
		foreach ( get_object_taxonomies( 'product', 'objects' ) as $taxonomy ) {
			if ( $taxonomy->public && $taxonomy->publicly_queryable && in_array( 'product', $taxonomy->object_type, true ) ) {
				$keys[] = 'is_archive_for_tax_' . $taxonomy->name;
			}
		}
		sort( $keys );
		return $keys;
	}

	/**
	 * Reports missing native assignments and existing ownership conflicts.
	 *
	 * @param array<string, int> $targets Language => existing template ID.
	 * @return list<array{surface: string, target: string, detail: string}>
	 */
	public function drift( array $targets ): array {
		$keys = $this->keys();
		$rows = $this->conflicts( $targets, $keys );
		foreach ( $targets as $language => $id ) {
			foreach ( $keys as $key ) {
				if ( ! in_array( '1', $this->values( $id, $key ), true ) ) {
					$rows[] = $this->row( $key, $language, $id, 'native generic assignment is missing' );
				}
			}
		}
		return $rows;
	}

	/**
	 * Refuses explicit generic ownership before the batch changes any metadata.
	 *
	 * @param array<string, int> $targets Language => existing template ID.
	 * @throws \RuntimeException On a same-language or unclassified owner.
	 */
	public function preflight( array $targets ): void {
		$rows = $this->conflicts( $targets, $this->keys() );
		if ( array() !== $rows ) {
			throw new \RuntimeException( $rows[0]['surface'] . ': ' . $rows[0]['target'] . ': ' . $rows[0]['detail'] ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator diagnostics, not HTML.
		}
	}

	/**
	 * Installs only missing assignments, with readback and batch-local recovery.
	 * Native hook throwables are rethrown unchanged after successful restoration.
	 *
	 * @param array<string, int> $targets Language => existing template ID.
	 * @return int Changed assignment keys, not changed HTML templates.
	 * @throws \RuntimeException On conflict, failed readback or failed local restoration.
	 */
	public function sync( array $targets ): int {
		$this->preflight( $targets );
		$before  = $this->snapshot( $targets );
		$changed = 0;
		try {
			foreach ( $before as $id => $keys ) {
				foreach ( $keys as $key => $values ) {
					if ( in_array( '1', $values, true ) ) {
						continue;
					}
					update_post_meta( $id, $key, '1' );
					if ( ! in_array( '1', $this->values( $id, $key ), true ) ) {
						throw new \RuntimeException( sprintf( 'Native archive assignment %s on template %d failed readback.', $key, $id ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator diagnostics.
					}
					++$changed;
				}
			}
		} catch ( \Throwable $error ) {
			try {
				$this->restore( $before );
			} catch ( \Throwable $rollback ) {
				throw new \RuntimeException( $error->getMessage() . ' Local assignment rollback also failed: ' . $rollback->getMessage(), 0, $error ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator diagnostics.
			}
			throw $error;
		}
		return $changed;
	}

	/**
	 * Exact pre-write key values, including [] for absent metadata.
	 *
	 * @param array<string, int> $targets Language => existing template ID.
	 * @return array<int, array<string, list<mixed>>>
	 */
	public function snapshot( array $targets ): array {
		$snapshot = array();
		$keys     = $this->keys();
		foreach ( array_unique( array_values( $targets ) ) as $id ) {
			foreach ( $keys as $key ) {
				$snapshot[ $id ][ $key ] = $this->values( $id, $key );
			}
		}
		return $snapshot;
	}

	/**
	 * Restores only the saved template/key set, preserving all values and slashes.
	 *
	 * The saved keys, not today's taxonomy registry, define rollback scope.
	 *
	 * @param array<int, array<string, list<mixed>>> $snapshot Exact pre-run values.
	 * @throws \RuntimeException When restoration does not read back exactly.
	 */
	public function restore( array $snapshot ): void {
		foreach ( $snapshot as $id => $keys ) {
			foreach ( $keys as $key => $values ) {
				if ( $id <= 0 || ! str_starts_with( $key, 'is_archive_for_tax_' ) || str_contains( $key, '__' ) ) {
					throw new \RuntimeException( 'Invalid native archive assignment backup scope.' );
				}
				if ( $this->values( $id, $key ) === $values ) {
					continue;
				}
				delete_post_meta( $id, $key );
				foreach ( $values as $value ) {
					add_post_meta( $id, $key, wp_slash( $value ) );
				}
				if ( $this->values( $id, $key ) !== $values ) {
					throw new \RuntimeException( sprintf( 'Native archive assignment rollback %s on template %d failed readback; the backup must be kept.', $key, $id ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator diagnostics.
				}
			}
		}
	}

	/**
	 * One primed template scan avoids an N-taxonomy meta-query JOIN graph.
	 * LC's native matcher selects published templates by meta existence, not 1.
	 *
	 * @param array<string, int> $targets Language => intended existing owner.
	 * @param array<int, string> $keys Generic keys only; per-term keys are untouched.
	 * @return list<array{surface: string, target: string, detail: string}>
	 */
	private function conflicts( array $targets, array $keys ): array {
		if ( array() === $targets || array() === $keys ) {
			return array();
		}
		$rows = array();
		foreach ( get_posts(
			array(
				'post_type'              => Templates::POST_TYPE,
				'post_status'            => 'publish',
				'posts_per_page'         => -1,
				'lang'                   => '',
				'orderby'                => 'ID',
				'order'                  => 'ASC',
				'update_post_meta_cache' => true,
			)
		) as $post ) {
			$owner_language = function_exists( 'pll_get_post_language' ) ? pll_get_post_language( $post->ID ) : false;
			foreach ( $targets as $language => $id ) {
				if ( (int) $post->ID === $id || ( is_string( $owner_language ) && $owner_language !== $language ) ) {
					continue;
				}
				foreach ( $keys as $key ) {
					if ( array() !== $this->values( (int) $post->ID, $key ) ) {
						$rows[] = $this->row( $key, $language, $id, sprintf( 'native generic assignment already belongs to template %d (%s)', $post->ID, $owner_language ? $owner_language : 'language unknown' ) );
					}
				}
			}
		}
		return $rows;
	}

	/**
	 * All native values preserve absent versus empty and multi-row assignments.
	 *
	 * @param int    $id Template ID.
	 * @param string $key Generic assignment key.
	 * @return list<mixed>
	 * @throws \RuntimeException On an unreadable native metadata list.
	 */
	private function values( int $id, string $key ): array {
		$values = get_post_meta( $id, $key, false );
		if ( ! is_array( $values ) ) {
			throw new \RuntimeException( sprintf( 'Native archive assignment %s on template %d cannot be read.', $key, $id ) ); // phpcs:ignore WordPress.Security.EscapeOutput.ExceptionNotEscaped -- operator diagnostics.
		}
		return array_values( $values );
	}

	/**
	 * One operator-facing drift row, in Templates::drift()'s existing format.
	 *
	 * @param string $key Native generic key.
	 * @param string $language Native language.
	 * @param int    $id Target template.
	 * @param string $detail Missing value or conflict.
	 * @return array{surface: string, target: string, detail: string}
	 */
	private function row( string $key, string $language, int $id, string $detail ): array {
		return array(
			'surface' => 'archive assignment ' . $key,
			'target'  => $language . ' template ' . $id,
			'detail'  => $detail,
		);
	}
}
