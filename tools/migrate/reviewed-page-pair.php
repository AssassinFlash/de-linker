<?php
/**
 * CLI-only wrapper: adopt reviewed German inside the existing content transaction.
 *
 * @package Linker\Commerce
 */

use Linker\Commerce\Mail\NativeTransaction;
use Linker\I18n\Languages;
use Linker\I18n\LinkLocalizer;
use Linker\I18n\Twins;
use Linker\I18n\Translation\Aligner;
use Linker\I18n\Translation\Client;
use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\HtmlTokenizer;
use Linker\I18n\Translation\Planner;
use Linker\I18n\Translation\Rules;
use Linker\I18n\Translation\Segmenter;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;
use Linker\I18n\Translation\Validator;
use Linker\I18n\Woo\Projection;

( static function (): void {
	global $wpdb;
	if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
		throw new RuntimeException( 'Reviewed paired saving is CLI-only.' );
	}
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- JSON transport only, never executable data.
	$pair      = json_decode( base64_decode( '__REVIEWED_PAIR_PAYLOAD__' ), true, 512, JSON_THROW_ON_ERROR );
	$post_type = $pair['post_type'] ?? 'page';
	if ( ! in_array( $post_type, array( 'page', 'post' ), true ) || 2 !== count( $pair['changes'] ) ) {
		throw new RuntimeException( 'Exactly two explicit pages or two explicit blog posts are required.' );
	}
	$en = (int) $pair['changes'][0]['id'];
	$de = (int) $pair['changes'][1]['id'];
	if ( $en === $de || 'en' !== pll_get_post_language( $en ) || 'de' !== pll_get_post_language( $de ) || (int) pll_get_post( $en, 'de' ) !== $de ) {
		throw new RuntimeException( 'Expected the explicit English/German pair.' );
	}
	$posts    = array();
	$pages    = array();
	$excerpts = array();
	foreach ( array( $en, $de ) as $id ) {
		clean_post_cache( $id );
		$post = get_post( $id );
		if ( ! $post instanceof WP_Post || $post_type !== $post->post_type ) {
			throw new RuntimeException( 'The reviewed object does not have the expected post type.' );
		}
		$posts[ $id ]    = $post;
		$pages[ $id ]    = $post->post_content;
		$excerpts[ $id ] = $post->post_excerpt;
	}
	if ( 'InnoDB' !== $wpdb->get_var( $wpdb->prepare( 'SELECT ENGINE FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s', $wpdb->postmeta ) ) ) {
		throw new RuntimeException( 'Transactional translation metadata is required.' );
	}
	$keys       = array(
		$en => array( State::STATUS, State::NOTE ),
		$de => array( State::SOURCE_HASH, State::UNITS ),
	);
	$read       = static function () use ( $keys ): array {
		$out = array();
		foreach ( $keys as $id => $names ) {
			wp_cache_delete( $id, 'post_meta' );
			foreach ( $names as $name ) {
				$out[ $id ][ $name ] = get_post_meta( $id, $name, false );
			}
		}
		return $out;
	};
	$client     = new class() implements Client {
		/** This reviewed operation has no machine translator. */
		public function available(): bool {
			return false;
		}
		/**
		 * Reject any accidental use of the native machine-translation path.
		 *
		 * @param array<int, string> $texts Unused interface input.
		 * @param string             $feedback Unused interface feedback.
		 * @throws RuntimeException Always: reviewed copy cannot call a model.
		 */
		public function translate( array $texts, string $feedback = '' ): array { // phpcs:ignore Generic.CodeAnalysis.UnusedFunctionParameter -- Native Client contract; calls always fail.
			throw new RuntimeException( 'Reviewed copy must never call a model.' );
		}
	};
	$languages  = new Languages();
	$tokenizer  = new HtmlTokenizer();
	$state      = new State();
	$links      = new LinkLocalizer( $languages, $tokenizer );
	$twins      = new Twins( $languages, $links, new Projection( $languages ) );
	$rules      = Rules::load( WP_PLUGIN_DIR . '/linker-i18n/data' );
	$fields     = new Fields();
	$planner    = new Planner( new Segmenter( $tokenizer ), new Aligner() );
	$translator = new Translator( $languages, $planner, $fields, $state, $client, new Validator( $rules ), $twins, $links );
	if ( in_array( $pair['mode'], array( 'read_descriptions', 'save_descriptions' ), true ) ) {
		$read_descriptions = static function () use ( $pair ): array {
			$result = array();
			foreach ( $pair['changes'] as $change ) {
				$id = (int) $change['id'];
				wp_cache_delete( $id, 'post_meta' );
				foreach ( $change['keys'] as $key ) {
					if ( ! in_array( $key, array( '_seopress_titles_title', '_seopress_titles_desc', '_seopress_social_fb_desc', '_seopress_social_twitter_desc' ), true ) ) {
						throw new RuntimeException( 'Expected a reviewed SEOPress title or description.' );
					}
					$values = get_post_meta( $id, $key, false );
					if ( 1 !== count( $values ) ) {
						throw new RuntimeException( esc_html( sprintf( 'Expected one published value for %d %s.', $id, $key ) ) );
					}
					$result[ $id ][ $key ] = $values[0];
				}
			}
			return $result;
		};
		if ( 'read_descriptions' === $pair['mode'] ) {
			$snapshot = array(
				'home'     => home_url(),
				'values'   => $read_descriptions(),
				'metadata' => $read(),
				'current'  => $translator->current( State::POST, $en ),
			);
			echo '@@reviewed-pair@@' . wp_json_encode( $snapshot );
			return;
		}
		$write = static function () use ( $wpdb, $en, $de, $pair, $read_descriptions, $read, $translator ): void {
			if ( false === $wpdb->query( $wpdb->prepare( 'SELECT ID FROM %i WHERE ID IN (%d,%d) FOR UPDATE', $wpdb->posts, $en, $de ) )
				|| false === $wpdb->query( $wpdb->prepare( 'SELECT meta_id FROM %i WHERE post_id IN (%d,%d) ORDER BY post_id, meta_id FOR UPDATE', $wpdb->postmeta, $en, $de ) ) ) {
				throw new RuntimeException( 'Cannot lock the reviewed page pair.' );
			}
			if ( $read_descriptions() !== $pair['before'] || $read() !== $pair['metadata_before'] || $translator->current( State::POST, $en ) !== ( $pair['require_current'] ?? true ) ) {
				throw new RuntimeException( 'The published descriptions or their translation baseline changed.' );
			}
			foreach ( $pair['after'] as $id => $values ) {
				foreach ( $values as $key => $value ) {
					if ( ! isset( $pair['before'][ $id ][ $key ] ) ) {
						throw new RuntimeException( 'Description is outside the reviewed fields.' );
					}
					update_post_meta( (int) $id, $key, wp_slash( $value ) );
				}
			}
			if ( $pair['require_current'] ?? true ) {
				foreach ( array( State::SOURCE_HASH, State::UNITS ) as $key ) {
					$expected = $pair['expected_metadata'][ $de ][ $key ];
					if ( 1 !== count( $expected ) ) {
						throw new RuntimeException( 'Expected the existing bilingual description baseline.' );
					}
					update_post_meta( $de, $key, wp_slash( $expected[0] ) );
				}
			}
			if ( $read_descriptions() !== $pair['after'] || $read() !== $pair['expected_metadata'] || $translator->current( State::POST, $en ) !== ( $pair['require_current'] ?? true ) ) {
				throw new RuntimeException( 'The reviewed descriptions or translation failed readback.' );
			}
		};
		try {
			NativeTransaction::run( $write );
		} finally {
			foreach ( array( $en, $de ) as $id ) {
				wp_cache_delete( $id, 'post_meta' );
			}
		}
		echo '@@reviewed-pair@@{}';
		return;
	}
	if ( 'read' === $pair['mode'] ) {
		$snapshot = array(
			'home'     => home_url(),
			'pages'    => $pages,
			'metadata' => $read(),
			'current'  => $translator->current( State::POST, $en ),
		);
		if ( 'post' === $post_type ) {
			$snapshot['excerpts'] = $excerpts;
		}
		echo '@@reviewed-pair@@' . wp_json_encode( $snapshot );
		return;
	}
	if ( 'preview_page_adoption' === $pair['mode'] ) {
		if ( 'page' !== $post_type ) {
			throw new RuntimeException( 'Expected a page pair for adoption preview.' );
		}
		$texts = array();
		foreach ( $pair['changes'] as $change ) {
			$post               = clone $posts[ (int) $change['id'] ];
			$post->post_content = $change['after'] ?? $post->post_content;
			$values             = $fields->of_post( $post, $de === $post->ID );
			foreach ( $change['descriptions'] ?? array() as $key => $description ) {
				$values[ Fields::META . $key ] = array( $description, false );
			}
			$texts[] = $values;
		}
		list( $source, $german ) = $texts;
		$descriptions            = $pair['changes'][0]['descriptions'] ?? array();
		$units                   = $descriptions ? json_decode( get_post_meta( $de, State::UNITS, true ), true, 512, JSON_THROW_ON_ERROR ) : array();
		$parts                   = array();
		foreach ( $source as $field => list( $value, $html ) ) {
			$parts[] = $field . "\0" . $value;
			if ( $descriptions && ! isset( $descriptions[ substr( $field, strlen( Fields::META ) ) ] ) ) {
				continue;
			}
			$translated      = $german[ $field ][0] ?? '';
			$units[ $field ] = array(
				'src'      => $planner->split( $value, $html )->hashes(),
				'out'      => $planner->split( $translated, $html )->hashes(),
				'conflict' => false,
			);
		}
		// The paired writer checks this preview against native adopt_current() before COMMIT.
		/**
		 * Native metadata keyed by post ID and translation field.
		 *
		 * @var array<int,array<string,array<int,mixed>>> $expected
		 */
		$expected = $read();
		$updates  = array(
			array( $de, State::SOURCE_HASH, sha1( implode( "\1", $parts ) ) ),
			array( $de, State::UNITS, wp_json_encode( $units ) ),
		);
		if ( ! $descriptions ) {
			$updates[]                      = array( $en, State::STATUS, State::SYNCED );
			$expected[ $en ][ State::NOTE ] = array();
		}
		foreach ( $updates as list( $id, $key, $value ) ) {
			$expected[ $id ][ $key ] = array_fill( 0, max( 1, count( $expected[ $id ][ $key ] ) ), $value );
		}
		echo '@@reviewed-pair@@' . wp_json_encode( array( 'expected_metadata' => $expected ) );
		return;
	}
	if ( ! in_array( $pair['mode'], array( 'adopt', 'restore' ), true ) ) {
		throw new RuntimeException( 'Unknown reviewed pair operation.' );
	}
	$changed    = static fn( array $change ): bool => $change['before'] !== $change['after'] || ( $change['before_excerpt'] ?? null ) !== ( $change['after_excerpt'] ?? null );
	$en_changed = $changed( $pair['changes'][0] );
	$de_changed = $changed( $pair['changes'][1] );
	if ( ! $en_changed && ! $de_changed ) {
		throw new RuntimeException( 'A write requires at least one reviewed page to change.' );
	}
	$locked         = false;
	$adopted        = false;
	$expected       = $pair['metadata_before'];
	$observe_update = static function ( mixed $check, int $id, string $key, mixed $value ) use ( $keys, &$expected ): mixed {
		if ( isset( $keys[ $id ] ) && in_array( $key, $keys[ $id ], true ) ) {
			// Native metadata filters receive the unslashed requested value,
			// even when another filter rejects it. Reuse native segment hashing.
			$expected[ $id ][ $key ] = array_fill( 0, max( 1, count( $expected[ $id ][ $key ] ) ), $value );
		}
		return $check;
	};
	$observe_delete = static function ( mixed $check, int $id, string $key ) use ( $keys, &$expected ): mixed {
		if ( isset( $keys[ $id ] ) && in_array( $key, $keys[ $id ], true ) ) {
			$expected[ $id ][ $key ] = array();
		}
		return $check;
	};
	$lock           = static function ( int $id ) use ( $en, $de, $pair, $keys, $translator, &$locked, $wpdb ): void {
		if ( $id !== $en && $id !== $de ) {
			return;
		}
		if ( ! $locked ) {
			// The content writer already holds both post locks on this connection.
			// Lock their metadata before native pre-save baseline priming runs.
			$rows    = $wpdb->get_results( $wpdb->prepare( 'SELECT post_id, meta_key, meta_value FROM %i WHERE post_id IN (%d, %d) ORDER BY post_id, meta_id FOR UPDATE', $wpdb->postmeta, $en, $de ) );
			$current = array();
			foreach ( $keys as $post_id => $names ) {
				wp_cache_delete( $post_id, 'post_meta' );
				foreach ( $names as $name ) {
					$current[ $post_id ][ $name ] = array();
				}
			}
			foreach ( $rows as $row ) {
				$post_id = (int) $row->post_id;
				if ( isset( $current[ $post_id ] ) && array_key_exists( $row->meta_key, $current[ $post_id ] ) ) {
					$current[ $post_id ][ $row->meta_key ][] = maybe_unserialize( $row->meta_value );
				}
			}
			if ( $current !== $pair['metadata_before'] ) {
				throw new RuntimeException( 'Translation metadata changed since backup.' );
			}
			// A partial copy edit cannot review all differences in a stale English source.
			if ( ( 'adopt' === $pair['mode'] || ! empty( $pair['require_current'] ) ) && ! $translator->current( State::POST, $en ) ) {
				throw new RuntimeException( 'Translation baseline is stale before reviewed copy adoption.' );
			}
			$locked = true;
		}
	};
	$adopt          = static function ( int $id ) use ( $en, $de, $post_type, $pair, $keys, $read, $translator, &$adopted, &$expected ): void {
		if ( $id !== $de ) {
			return;
		}
		foreach ( $pair['changes'] as $change ) {
			clean_post_cache( (int) $change['id'] );
			$post = get_post( (int) $change['id'] );
			if ( ! $post instanceof WP_Post || $post_type !== $post->post_type || $post->post_content !== $change['after'] || ( isset( $change['after_excerpt'] ) && $post->post_excerpt !== $change['after_excerpt'] ) ) {
				throw new RuntimeException( 'Both reviewed texts must precede baseline adoption.' );
			}
		}
		if ( 'restore' === $pair['mode'] ) {
			foreach ( $keys as $post_id => $names ) {
				foreach ( $names as $name ) {
					delete_post_meta( $post_id, $name );
					foreach ( $pair['metadata_restore'][ $post_id ][ $name ] as $value ) {
						add_post_meta( $post_id, $name, wp_slash( $value ) );
					}
				}
			}
			if ( $read() !== $pair['metadata_restore'] ) {
				throw new RuntimeException( 'Original translation values were not restored.' );
			}
		} else {
			$expected = $read();
			if ( State::SYNCED !== $translator->adopt_current( State::POST, $en ) || ! $translator->current( State::POST, $en ) || $read() !== $expected ) {
				throw new RuntimeException( 'Reviewed baseline differs from native requested values.' );
			}
		}
		$adopted = true;
	};
	$verify         = static function ( string $query ) use ( $en, $de, $de_changed, $pair, $read, $translator, $adopt, &$locked, &$adopted, &$expected, $wpdb ): string {
		if ( 'START TRANSACTION' === $query ) {
			// Limit this to the next transaction, after the writer's preflight.
			// Native reads must see current locked values and protect absent keys;
			// session and global isolation defaults remain unchanged.
			if ( false === $wpdb->query( 'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE' ) ) {
				throw new RuntimeException( 'Could not protect the reviewed baseline transaction.' );
			}
			return $query;
		}
		if ( 'COMMIT' !== $query ) {
			return $query;
		}
		if ( $locked && ! $adopted && ! $de_changed ) {
			// An unchanged German page has no post_updated event. The same
			// adoption guard verifies both after texts before recording the baseline.
			$adopt( $de );
		}
		$valid = 'restore' === $pair['mode'] ? $read() === $pair['metadata_restore'] : $translator->current( State::POST, $en ) && $read() === $expected;
		if ( ! $locked || ! $adopted || ! $valid || ( isset( $pair['expected_metadata'] ) && $pair['expected_metadata'] !== $expected ) ) {
			throw new RuntimeException( 'Cannot commit an unadopted reviewed pair.' );
		}
		return $query;
	};
	add_action( 'pre_post_update', $lock, -PHP_INT_MAX );
	add_action( 'post_updated', $adopt, PHP_INT_MAX );
	add_filter( 'update_post_metadata', $observe_update, PHP_INT_MAX, 4 );
	add_filter( 'delete_post_metadata', $observe_delete, PHP_INT_MAX, 3 );
	add_filter( 'query', $verify, PHP_INT_MAX - 1 );
	try { // phpcs:ignore Generic.CodeAnalysis.EmptyStatement.DetectedTry -- Trusted writer source replaces this template marker before CLI execution.
		// Replaced only with the trusted, unchanged repository writer source.
		/* __REVIEWED_PAIR_CONTENT_WRITER__ */
	} finally {
		remove_action( 'pre_post_update', $lock, -PHP_INT_MAX );
		remove_action( 'post_updated', $adopt, PHP_INT_MAX );
		remove_filter( 'update_post_metadata', $observe_update, PHP_INT_MAX );
		remove_filter( 'delete_post_metadata', $observe_delete, PHP_INT_MAX );
		remove_filter( 'query', $verify, PHP_INT_MAX - 1 );
	}
	echo PHP_EOL . '@@reviewed-pair@@' . wp_json_encode( array( 'expected_metadata' => 'restore' === $pair['mode'] ? $pair['metadata_restore'] : $expected ) );
} )();
