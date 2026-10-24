<?php
/**
 * CLI-only wrapper: adopt reviewed German inside the existing content transaction.
 *
 * @package Linker\Commerce
 */

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
	$pair = json_decode( base64_decode( '__REVIEWED_PAIR_PAYLOAD__' ), true, 512, JSON_THROW_ON_ERROR );
	if ( 2 !== count( $pair['changes'] ) ) {
		throw new RuntimeException( 'Exactly two explicit pages are required.' );
	}
	$en = (int) $pair['changes'][0]['id'];
	$de = (int) $pair['changes'][1]['id'];
	if ( $en === $de || 'en' !== pll_get_post_language( $en ) || 'de' !== pll_get_post_language( $de ) || (int) pll_get_post( $en, 'de' ) !== $de ) {
		throw new RuntimeException( 'Expected the explicit English/German page pair.' );
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
	$translator = new Translator( $languages, new Planner( new Segmenter( $tokenizer ), new Aligner() ), new Fields(), $state, $client, new Validator( $rules ), $twins, $links );
	if ( 'read' === $pair['mode'] ) {
		$pages = array();
		foreach ( array( $en, $de ) as $id ) {
			clean_post_cache( $id );
			$post = get_post( $id );
			if ( ! $post instanceof WP_Post || 'page' !== $post->post_type ) {
				throw new RuntimeException( 'The reviewed page no longer exists.' );
			}
			$pages[ $id ] = $post->post_content;
		}
		echo '@@reviewed-pair@@' . wp_json_encode(
			array(
				'home'     => home_url(),
				'pages'    => $pages,
				'metadata' => $read(),
				'current'  => $translator->current( State::POST, $en ),
			)
		);
		return;
	}
	if ( ! in_array( $pair['mode'], array( 'adopt', 'restore' ), true ) ) {
		throw new RuntimeException( 'Unknown reviewed pair operation.' );
	}
	foreach ( $pair['changes'] as $change ) {
		if ( $change['before'] === $change['after'] ) {
			throw new RuntimeException( 'A write requires both pages to change; inspect no-op pairs separately.' );
		}
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
	$lock           = static function ( int $id ) use ( $en, $de, $pair, $keys, &$locked, $wpdb ): void {
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
			$locked = true;
		}
	};
	$adopt          = static function ( int $id ) use ( $en, $de, $pair, $keys, $read, $translator, &$adopted, &$expected ): void {
		if ( $id !== $de ) {
			return;
		}
		foreach ( $pair['changes'] as $change ) {
			clean_post_cache( (int) $change['id'] );
			$post = get_post( (int) $change['id'] );
			if ( ! $post instanceof WP_Post || 'page' !== $post->post_type || $post->post_content !== $change['after'] ) {
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
	$verify         = static function ( string $query ) use ( $en, $pair, $read, $translator, &$locked, &$adopted, &$expected, $wpdb ): string {
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
		$valid = 'restore' === $pair['mode'] ? $read() === $pair['metadata_restore'] : $translator->current( State::POST, $en ) && $read() === $expected;
		if ( ! $locked || ! $adopted || ! $valid ) {
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
