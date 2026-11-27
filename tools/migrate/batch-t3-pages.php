<?php
/**
 * Publish the marketing page styles in WindPress and the intrinsic dimensions in HTML.
 *
 * @package Linker\Commerce
 */

namespace Linker\Commerce\Migrate\T3Pages;

use Linker\Commerce\Mail\NativeTransaction;
use Linker\I18n\Translation\Fields;
use Linker\I18n\Translation\State;
use Linker\I18n\Translation\Translator;
use RuntimeException;
use WP_HTML_Tag_Processor;

const PAIRS = array(
	13   => 6913,
	862  => 6865,
	2748 => 6700,
	746  => 6871,
	749  => 6923,
	792  => 6921,
	1755 => 6917,
	826  => 6869,
	842  => 6867,
);

const SHARED = array( 'home-journal.css', 'capability-cards.css', 'app-details.css', 'reference-photo-scenes.css' );

/**
 * Capture the exact original page body and the reviewed translation fields.
 *
 * @return array<int,array{content:string,fields:array<string,string>,meta:array<string,array<mixed>>}>
 * @throws RuntimeException When the expected published language pair is missing.
 */
function snapshot(): array {
	$rows   = array();
	$fields = new Fields();
	foreach ( PAIRS as $en => $de ) {
		if ( (int) pll_get_post( $en, 'de' ) !== $de || 'en' !== pll_get_post_language( $en ) ) {
			throw new RuntimeException( 'The marketing page translation pairing has changed.' );
		}
		foreach ( array( $en, $de ) as $id ) {
			$post = get_post( $id );
			if ( ! $post instanceof \WP_Post || 'publish' !== $post->post_status || 'page' !== $post->post_type ) {
				throw new RuntimeException( 'A published marketing page is missing.' );
			}
			$meta = array();
			foreach ( $en === $id ? array( State::STATUS, State::NOTE ) : array( State::SOURCE_HASH, State::UNITS ) as $key ) {
				$meta[ $key ] = get_post_meta( $id, $key, false );
			}
			$text = $fields->of_post( $post, $de === $id );
			unset( $text['post_content'] );
			$rows[ $id ] = array(
				'fields'  => array_map( static fn ( array $field ): string => $field[0], $text ),
				'content' => $post->post_content,
				'meta'    => $meta,
			);
		}
	}
	return $rows;
}

/**
 * Check the other translation inputs before writing page bodies or their translation state.
 *
 * @param array<int,array{content:string,fields:array<string,string>,meta:array<string,array<mixed>>}> $before Original page snapshot.
 * @return array<int,array{content:string,fields:array<string,string>,meta:array<string,array<mixed>>}>
 * @throws RuntimeException When a title, excerpt or SEO text changed.
 */
function checked_snapshot( array $before ): array {
	$current = snapshot();
	foreach ( $current as $id => $row ) {
		if ( $row['fields'] !== $before[ $id ]['fields'] ) {
			throw new RuntimeException( 'Translation fields changed since snapshot: ' . esc_html( (string) $id ) );
		}
	}
	return $current;
}

/**
 * Read the stylesheet shipped in the installed volume.
 *
 * @param string $file Owned stylesheet basename.
 * @throws RuntimeException When the deployed volume has no matching file.
 */
function stylesheet( string $file ): string {
	$path = WP_PLUGIN_DIR . '/linker-commerce/content/windpress/' . $file;
	$css  = file_get_contents( $path ); // phpcs:ignore WordPress.WP.AlternativeFunctions.file_get_contents_file_get_contents -- Compare the installed local stylesheet bytes before retiring the inline source.
	if ( false === $css ) {
		throw new RuntimeException( 'Missing marketing stylesheet ' . esc_html( $file ) );
	}
	return $css;
}

/**
 * Reconstruct the exact inline variant from the shared stylesheet. The Home cards
 * and About scene use different heading levels for the same visual treatment.
 *
 * @param string $file Owned stylesheet basename.
 * @param bool   $home Home page in either language.
 */
function inline_variant( string $file, bool $home ): string {
	$css = stylesheet( $file );
	if ( 'app-details.css' === $file && ! $home ) {
		return str_replace( '#home-a [data-capability-card] h2{', '#home-a [data-capability-card] h4{', $css );
	}
	if ( 'reference-photo-scenes.css' === $file ) {
		$tag = $home ? 'h3' : 'h4';
		$css = str_replace( '#home-a .scene-card-body h3,#about-journal .scene-card-body h4{', ':is(#home-a,#about-journal) .scene-card-body ' . $tag . '{', $css );
		if ( ! $home ) {
			$css = str_replace( '#home-a .scene-card-body h3{', '#home-a .scene-card-body h4{', $css );
		}
	}
	if ( 'home-sections.css' === $file ) {
		foreach ( array(
			'backdrop-filter' => 'blur(10px)',
			'appearance'      => 'none',
		) as $property => $value ) {
			$css = str_replace( "    -webkit-$property: $value;\n    $property: $value;", "    $property: $value;\n    -webkit-$property: $value;", $css );
		}
	}
	return $css;
}

/**
 * Remove the approved inline blocks only when their bytes match this publication.
 *
 * @param string $content Original raw page.
 * @param int    $id Marketing page ID.
 * @throws RuntimeException When an inline stylesheet has changed independently.
 */
function without_styles( string $content, int $id ): string {
	$home = in_array( $id, array( 13, 6913 ), true );
	// The Home and About templates have no conflicting page-specific rules.
	$keep_position = ! $home && ! in_array( $id, array( 862, 6865 ), true );
	$composition   = array();
	$body          = preg_replace_callback(
		'~<style\b([^>]*)>(.*?)</style>~is',
		static function ( array $block ) use ( $home, $keep_position, &$composition ): string {
			if ( $home && '' === trim( $block[1] ) ) {
				$composition[] = $block[2];
				return '';
			}
			if ( ! preg_match( '/^\s+data-site-css="([^"]+)"\s*$/', $block[1], $name ) || ! in_array( $name[1], SHARED, true ) ) {
				return $block[0];
			}
			if ( inline_variant( $name[1], $home ) !== $block[2] ) {
				throw new RuntimeException( 'Inline stylesheet differs from the volume: ' . esc_html( $name[1] ) );
			}
			return $keep_position ? '[linker_marketing_style name="' . basename( $name[1], '.css' ) . '"]' : '';
		},
		$content
	);
	if ( null === $body || ( $composition && implode( "\n", $composition ) !== inline_variant( 'home-sections.css', true ) ) ) {
		throw new RuntimeException( 'Home composition differs from the deployed volume.' );
	}
	return $body;
}

/**
 * The two embedded Utility illustrations specify their intrinsic size in the SVG root.
 *
 * @param string $src Image URL.
 * @param string $base Public uploads URL path, with trailing slash.
 * @param string $dir Local uploads directory.
 * @return array{int,int}|null
 * @throws RuntimeException When an owned image has no readable dimensions.
 */
function dimensions( string $src, string $base, string $dir ): ?array {
	if ( str_starts_with( $src, 'data:image/svg+xml;base64,' ) ) {
		$svg = base64_decode( substr( $src, strlen( 'data:image/svg+xml;base64,' ) ), true ); // phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Read the intrinsic dimensions of the authored data URI.
		$tag = new WP_HTML_Tag_Processor( false === $svg ? '' : $svg );
		if ( $tag->next_tag( array( 'tag_name' => 'svg' ) ) ) {
			$w = (int) $tag->get_attribute( 'width' );
			$h = (int) $tag->get_attribute( 'height' );
			if ( $w > 0 && $h > 0 ) {
				return array( $w, $h );
			}
		}
		throw new RuntimeException( 'Missing dimensions on the embedded marketing illustration.' );
	}
	$url = wp_parse_url( $src );
	if ( ! is_array( $url ) || ! isset( $url['path'] ) || ( isset( $url['host'] ) && wp_parse_url( (string) get_option( 'home' ), PHP_URL_HOST ) !== $url['host'] ) || ! str_starts_with( $url['path'], $base ) ) {
		return null;
	}
	$path = realpath( $dir . '/' . rawurldecode( substr( $url['path'], strlen( $base ) ) ) );
	$size = false !== $path && str_starts_with( $path, trailingslashit( $dir ) ) ? wp_getimagesize( $path ) : false;
	if ( ! $size || $size[0] <= 0 || $size[1] <= 0 ) {
		throw new RuntimeException( 'Missing marketing image dimensions for ' . esc_html( $src ) );
	}
	return array( $size[0], $size[1] );
}

/**
 * Keep all unrelated attributes and WordPress content bytes intact.
 *
 * @param int    $id Page ID.
 * @param string $original Snapshotted page body.
 */
function revised( int $id, string $original ): string {
	$tags    = new WP_HTML_Tag_Processor( without_styles( $original, $id ) );
	$uploads = wp_get_upload_dir();
	$base    = trailingslashit( (string) wp_parse_url( $uploads['baseurl'], PHP_URL_PATH ) );
	$dir     = realpath( $uploads['basedir'] );
	while ( $tags->next_tag( array( 'tag_name' => 'img' ) ) ) {
		$width  = $tags->get_attribute( 'width' );
		$height = $tags->get_attribute( 'height' );
		$src    = $tags->get_attribute( 'src' );
		if ( ( null !== $width && null !== $height ) || ! is_string( $src ) || false === $dir ) {
			continue;
		}
		$size = dimensions( $src, $base, $dir );
		if ( $size ) {
			if ( null === $width ) {
				$tags->set_attribute( 'width', (string) $size[0] );
			}
			if ( null === $height ) {
				$tags->set_attribute( 'height', (string) $size[1] );
			}
		}
	}
	return $tags->get_updated_html();
}

/**
 * Save raw HTML without WordPress interpreting quotes or backslashes.
 *
 * @param int    $id Page ID.
 * @param string $content Target raw page.
 * @throws RuntimeException When WordPress fails to persist the page.
 */
function write_body( int $id, string $content ): void {
	$result = wp_update_post(
		wp_slash(
			array(
				'ID'           => $id,
				'post_content' => $content,
			)
		),
		true
	);
	if ( is_wp_error( $result ) || get_post_field( 'post_content', $id, 'raw' ) !== $content ) {
		throw new RuntimeException( 'Cannot update marketing page ' . esc_html( (string) $id ) );
	}
}

/**
 * Publish a pair together and adopt the reviewed German body.
 *
 * @param array<int,array{content:string,fields:array<string,string>,meta:array<string,array<mixed>>}> $before Original page snapshot.
 * @param Translator                                                                                   $translator Reviewed translation writer.
 * @throws RuntimeException When a marketing page changed independently.
 */
function apply( array $before, Translator $translator ): int {
	$count   = 0;
	$current = checked_snapshot( $before );
	foreach ( PAIRS as $en => $de ) {
		$writes = array();
		foreach ( array( $en, $de ) as $id ) {
			$body = revised( $id, $before[ $id ]['content'] );
			if ( $current[ $id ]['content'] === $body ) {
				continue;
			}
			if ( $current[ $id ]['content'] !== $before[ $id ]['content'] ) {
				throw new RuntimeException( 'Marketing page changed since snapshot: ' . esc_html( (string) $id ) );
			}
			$writes[ $id ] = $body;
		}
		if ( ! $writes ) {
			continue;
		}
		if ( $current[ $en ]['meta'] !== $before[ $en ]['meta'] || $current[ $de ]['meta'] !== $before[ $de ]['meta'] ) {
			throw new RuntimeException( 'Translation state changed since snapshot: ' . esc_html( (string) $en ) );
		}
		$synced = array( State::SYNCED ) === $before[ $en ]['meta'][ State::STATUS ];
		NativeTransaction::run(
			static function () use ( $writes, $en, $translator, $synced ): void {
				foreach ( $writes as $id => $body ) {
					write_body( $id, $body );
				}
				if ( $synced && ( State::SYNCED !== $translator->adopt_current( State::POST, $en ) || ! $translator->current( State::POST, $en ) ) ) {
					throw new RuntimeException( 'Cannot adopt the reviewed marketing page translation.' );
				}
			}
		);
		$count += count( $writes );
	}
	return $count;
}

/**
 * Restore both original bodies and their recorded translation metadata.
 *
 * @param array<int,array{content:string,fields:array<string,string>,meta:array<string,array<mixed>>}> $before Original page snapshot.
 * @throws RuntimeException When subsequent edits need to be preserved.
 */
function restore( array $before ): int {
	$count   = 0;
	$current = checked_snapshot( $before );
	foreach ( PAIRS as $en => $de ) {
		if ( $current[ $en ]['content'] === $before[ $en ]['content'] && $current[ $de ]['content'] === $before[ $de ]['content'] ) {
			continue;
		}
		foreach ( array( $en, $de ) as $id ) {
			if ( $current[ $id ]['content'] !== $before[ $id ]['content'] && revised( $id, $before[ $id ]['content'] ) !== $current[ $id ]['content'] ) {
				throw new RuntimeException( 'Marketing page changed after publication: ' . esc_html( (string) $id ) );
			}
		}
		$synced = array( State::SYNCED ) === $before[ $en ]['meta'][ State::STATUS ];
		if ( $synced && $current[ $en ]['meta'] !== $before[ $en ]['meta'] ) {
			throw new RuntimeException( 'Translation status changed after publication: ' . esc_html( (string) $en ) );
		}
		NativeTransaction::run(
			static function () use ( $before, $current, $en, $de, $synced, &$count ): void {
				foreach ( array( $en, $de ) as $id ) {
					if ( $current[ $id ]['content'] !== $before[ $id ]['content'] ) {
						write_body( $id, $before[ $id ]['content'] );
					}
					++$count;
					if ( ! $synced || $de !== $id ) {
						continue;
					}
					foreach ( $before[ $id ]['meta'] as $key => $values ) {
						delete_post_meta( $id, $key );
						foreach ( $values as $value ) {
							add_post_meta( $id, $key, wp_slash( $value ) );
						}
					}
				}
			}
		);
	}
	return $count;
}
