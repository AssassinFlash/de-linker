<?php
/**
 * Reviewed German copy and data changes, with an explicit preview.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;

/**
 * Writes the German values of the pages reviewed for ticket #264 through the
 * native APIs. The manifest names the English source by slug, never an
 * environment-specific object ID; Plan, Apply, Verify and Rollback are the
 * same four steps as the German address migration, so the operator can read
 * every change before any write.
 *
 * @phpstan-type CopyRow array{id:int,type:string,source:int,before:array<string,string>,after:array<string,string>,existed:array<string,bool>}
 */
final class GermanCopyMigration {

	/**
	 * First-run originals, retained across repeat applications.
	 */
	public const BACKUP = 'linker_i18n_german_copy_backup';

	/**
	 * Native language access stays behind the shared Polylang door.
	 *
	 * @param Languages       $languages   Shared language and translation access.
	 * @param array|null      $manifest    Test seam; null reads the checked-in file.
	 * @param Translator|null $translator Records the reviewed German as the translation baseline.
	 * @phpstan-param list<array{type:string,source:string,set?:array<string,string>,replace?:array<string,list<array{old:string,new:string}>>}>|null $manifest
	 */
	public function __construct( private readonly Languages $languages = new Languages(), private readonly ?array $manifest = null, private readonly ?Translator $translator = null ) {}

	/**
	 * The reviewed German values keyed by English source slug.
	 *
	 * @return list<array{type:string,source:string,set?:array<string,string>,replace?:array<string,list<array{old:string,new:string}>>}>
	 */
	private function manifest(): array {
		if ( null !== $this->manifest ) {
			return $this->manifest;
		}
		// phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Checked-in reviewed copy data.
		return json_decode( (string) file_get_contents( dirname( __DIR__ ) . '/content/german-copy.json' ), true, 512, JSON_THROW_ON_ERROR );
	}

	/**
	 * Previews the reviewed German values without writing.
	 *
	 * @return list<CopyRow>
	 * @throws \RuntimeException A reviewed source or its German twin is missing, or a replacement no longer matches.
	 */
	public function plan(): array {
		$rows = array();
		foreach ( $this->manifest() as $entry ) {
			$source = $this->source( $entry['type'], $entry['source'] );
			$twin   = $this->twin( $source );
			$before = $this->read( $twin, $this->fields( $entry ) );
			$after  = $before;
			foreach ( $entry['set'] ?? array() as $field => $value ) {
				$after[ $field ] = $value;
			}
			foreach ( $entry['replace'] ?? array() as $field => $pairs ) {
				$value = $after[ $field ] ?? '';
				foreach ( $pairs as $pair ) {
					if ( ! str_contains( $value, $pair['old'] ) ) {
						// A repeat run has already replaced it; a value with
						// neither side is a drifted manifest and stops the run.
						if ( str_contains( $value, $pair['new'] ) ) {
							continue;
						}
						throw new \RuntimeException( esc_html( 'Reviewed text not found: ' . $entry['type'] . ':' . $entry['source'] . ' ' . $field ) );
					}
					$value = str_replace( $pair['old'], $pair['new'], $value );
				}
				$after[ $field ] = $value;
			}
			$changed = array_diff_assoc( $after, $before );
			if ( array() === $changed ) {
				continue;
			}
			$rows[] = array(
				'id'      => (int) $twin->ID,
				'type'    => $twin->post_type,
				'source'  => (int) $source->ID,
				'before'  => array_intersect_key( $before, $changed ),
				'after'   => $changed,
				'existed' => $this->existence( $twin, array_keys( $changed ) ),
			);
		}
		return $rows;
	}

	/**
	 * Applies a fully preflighted plan, preserving the first originals.
	 *
	 * @return int Changed objects.
	 * @throws \RuntimeException A conflict or native write failure occurs.
	 */
	public function apply(): int {
		$rows = $this->plan();
		if ( array() !== $rows ) {
			$backup = $this->backup();
			$this->check_originals( $backup );
			foreach ( $rows as $row ) {
				$key = $row['type'] . ':' . $row['id'];
				if ( ! isset( $backup[ $key ] ) ) {
					$backup[ $key ] = $row;
				}
			}
			update_option(
				self::BACKUP,
				array(
					'version' => 1,
					'objects' => $backup,
				),
				false
			);
			foreach ( $rows as $row ) {
				$this->write( $row, $row['after'], $row['existed'] );
			}
		}
		if ( null !== $this->translator ) {
			// The German in place is the reviewed source of truth; record it as
			// the translation baseline, also on a repeat run where no content
			// changed, so the next translation run keeps it and only fills
			// fields that have no German yet.
			foreach ( $this->manifest() as $entry ) {
				$source = $this->source( $entry['type'], $entry['source'] );
				$this->translator->adopt_current( State::POST, (int) $source->ID );
			}
		}
		return count( $rows );
	}

	/**
	 * Fails unless every reviewed value is in place.
	 *
	 * @throws \RuntimeException The migration is incomplete.
	 */
	public function verify(): void {
		$rows = $this->plan();
		if ( array() !== $rows ) {
			throw new \RuntimeException( esc_html( 'Pending German copy: ' . implode( ', ', array_map( static fn( array $row ): string => $row['type'] . ':' . $row['id'], $rows ) ) ) );
		}
	}

	/**
	 * Restores the saved originals and keeps the backup for a re-apply.
	 *
	 * @return int Restored objects.
	 */
	public function rollback(): int {
		$changed = 0;
		foreach ( $this->backup() as $row ) {
			$current = $this->read( (int) $row['id'], array_keys( $row['before'] ) );
			if ( $current === $row['before'] ) {
				continue;
			}
			$this->check_originals( array( $row['type'] . ':' . $row['id'] => $row ) );
			$this->write( $row, $row['before'], $row['existed'] );
			++$changed;
		}
		return $changed;
	}

	/**
	 * The saved originals; an unknown format is never overwritten.
	 *
	 * @return array<string,CopyRow>
	 * @throws \RuntimeException The saved format is unknown.
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
	 * The English object the manifest names.
	 *
	 * @param string $type Post type.
	 * @param string $slug English slug.
	 * @throws \RuntimeException The source is missing or not unique.
	 */
	private function source( string $type, string $slug ): \WP_Post {
		$posts = get_posts(
			array(
				'post_type'     => $type,
				'post_status'   => 'publish',
				'post_name__in' => array( $slug ),
				'lang'          => 'en',
				'numberposts'   => 2,
			)
		);
		if ( 1 !== count( $posts ) ) {
			throw new \RuntimeException( esc_html( 'Missing reviewed English source: ' . $type . ':' . $slug ) );
		}
		return $posts[0];
	}

	/**
	 * The German twin of the English source.
	 *
	 * @param \WP_Post $source English object.
	 * @throws \RuntimeException The twin is missing.
	 */
	private function twin( \WP_Post $source ): \WP_Post {
		$id   = (int) $this->languages->post_translation( $source->ID, 'de' );
		$post = $id > 0 ? get_post( $id ) : null;
		if ( ! $post instanceof \WP_Post || 'de' !== $this->languages->of_post( $id ) ) {
			throw new \RuntimeException( esc_html( 'Missing German twin: ' . $source->post_type . ':' . $source->post_name ) );
		}
		return $post;
	}

	/**
	 * The field names a manifest entry owns.
	 *
	 * @param array{set?:array<string,string>,replace?:array<string,list<array{old:string,new:string}>>} $entry Manifest entry.
	 * @return list<string>
	 */
	private function fields( array $entry ): array {
		return array_values( array_unique( array_merge( array_keys( $entry['set'] ?? array() ), array_keys( $entry['replace'] ?? array() ) ) ) );
	}

	/**
	 * Reads only the fields the migration owns.
	 *
	 * @param \WP_Post|int      $post   German object.
	 * @param array<int,string> $fields Field names.
	 * @return array<string,string>
	 * @throws \RuntimeException The object or a field is missing.
	 */
	private function read( $post, array $fields ): array {
		$object = $post instanceof \WP_Post ? $post : get_post( (int) $post );
		if ( ! $object instanceof \WP_Post ) {
			throw new \RuntimeException( 'German copy target no longer exists.' );
		}
		$values = array();
		foreach ( $fields as $field ) {
			if ( str_starts_with( $field, 'meta:' ) ) {
				$values[ $field ] = (string) get_post_meta( $object->ID, substr( $field, 5 ), true );
				continue;
			}
			$values[ $field ] = match ( $field ) {
				'post_title' => $object->post_title,
				'post_content' => $object->post_content,
				'post_excerpt' => $object->post_excerpt,
				default => throw new \RuntimeException( esc_html( 'Unknown migration field: ' . $field ) ),
			};
		}
		return $values;
	}

	/**
	 * Whether each meta key existed before the first run; rollback removes the
	 * ones the migration created.
	 *
	 * @param \WP_Post          $post   German object.
	 * @param array<int,string> $fields Field names.
	 * @return array<string,bool>
	 */
	private function existence( \WP_Post $post, array $fields ): array {
		$exists = array();
		foreach ( $fields as $field ) {
			if ( str_starts_with( $field, 'meta:' ) ) {
				$exists[ substr( $field, 5 ) ] = metadata_exists( 'post', $post->ID, substr( $field, 5 ) );
			}
		}
		return $exists;
	}

	/**
	 * Checks every saved field before any new write or rollback.
	 *
	 * @param array<string,CopyRow> $backup First originals.
	 * @throws \RuntimeException A field changed outside the migration.
	 */
	private function check_originals( array $backup ): void {
		foreach ( $backup as $row ) {
			$current = $this->read( (int) $row['id'], array_keys( $row['before'] ) );
			if ( $current !== $row['before'] && $current !== $row['after'] ) {
				throw new \RuntimeException( esc_html( 'Changed outside migration: ' . $row['type'] . ':' . $row['id'] ) );
			}
		}
	}

	/**
	 * Writes through the native APIs and checks the actual resulting values.
	 *
	 * @param array{id:int,type:string,source:int,before:array<string,string>,after:array<string,string>,existed:array<string,bool>} $row Object identity and originals.
	 * @param array<string,string>                                                                                                   $fields Desired native fields.
	 * @param array<string,bool>                                                                                                     $exists Meta keys' pre-migration existence.
	 * @throws \RuntimeException A native write fails or its readback disagrees.
	 */
	private function write( array $row, array $fields, array $exists ): void {
		$postarr = array( 'ID' => (int) $row['id'] );
		foreach ( $fields as $field => $value ) {
			if ( str_starts_with( $field, 'meta:' ) ) {
				$key = substr( $field, 5 );
				if ( '' === $value && ! ( $exists[ $key ] ?? true ) ) {
					delete_post_meta( (int) $row['id'], $key );
					continue;
				}
				update_post_meta( (int) $row['id'], $key, wp_slash( $value ) );
				continue;
			}
			match ( $field ) {
				'post_title' => $postarr['post_title']     = $value,
				'post_content' => $postarr['post_content'] = $value,
				'post_excerpt' => $postarr['post_excerpt'] = $value,
				default => throw new \RuntimeException( esc_html( 'Unknown migration field: ' . $field ) ),
			};
		}
		if ( count( $postarr ) > 1 ) {
			$result = wp_update_post( wp_slash( $postarr ), true );
			if ( is_wp_error( $result ) ) {
				throw new \RuntimeException( esc_html( $result->get_error_message() ) );
			}
		}
		if ( $this->read( (int) $row['id'], array_keys( $fields ) ) !== $fields ) {
			throw new \RuntimeException( esc_html( 'Native readback mismatch: ' . $row['type'] . ':' . $row['id'] ) );
		}
	}
}
