<?php
/**
 * Public product-selection context, independent of the customer's message.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Contact;

use Linker\I18n\Languages;
use WP_Post;
use WP_Term;

/** Source URLs identify public objects; they do not grant access or execute requests. */
final class SelectionContext {
	public const FIELD         = 'linker_contact_selection';
	public const INCLUDE_FIELD = 'linker_contact_selection_include';
	public const META          = '_linker_contact_selection';

	/**
	 * Resolve current public data again, never accepting a browser-supplied title.
	 *
	 * @param mixed $value Public source URL and selected navigation fields.
	 * @return array<string,mixed>
	 */
	public static function normalize( mixed $value ): array {
		if ( ! is_array( $value ) || ! is_string( $value['source'] ?? null ) ) {
			return array();
		}
		$url = $value['source'];
		if ( '' === $url || ! self::same_origin( $url ) ) {
			return array();
		}
		$path     = (string) wp_parse_url( $url, PHP_URL_PATH );
		$homepage = self::home_page( $path );
		$source   = null;
		$id       = null === $homepage ? url_to_postid( $url ) : $homepage['id'];
		// Woo serves the shop as an archive, so native url_to_postid may return zero.
		if ( null === $homepage && $id < 1 && function_exists( 'wc_get_page_id' ) ) {
			$shop = (int) wc_get_page_id( 'shop' );
			if ( $shop > 0 && self::same_path( $path, (string) get_permalink( $shop ) ) ) {
				$id = $shop;
			}
		}
		$post = $id > 0 ? get_post( $id ) : null;
		if ( $post instanceof WP_Post && 'publish' === $post->post_status && '' === $post->post_password && in_array( $post->post_type, array( 'product', 'page', 'post' ), true ) ) {
			$canonical = null === $homepage ? (string) get_permalink( $post ) : $homepage['source'];
			if ( null === $homepage && ! self::same_path( $path, $canonical ) ) {
				// Native product lookup can return the other language's same-slug twin.
				$twin = self::translation_at_path( $post, $path );
				if ( null !== $twin ) {
					$post      = $twin;
					$id        = $twin->ID;
					$canonical = (string) get_permalink( $twin );
				}
			}
			if ( self::same_path( $path, $canonical ) && ( null === $homepage || 'page' === $post->post_type ) ) {
				$source = array(
					'type'   => $post->post_type,
					'id'     => $id,
					'title'  => get_the_title( $post ),
					'source' => $canonical,
				);
			}
		}
		// A missing or restricted static front page must not become a language term.
		if ( null !== $homepage && null === $source ) {
			return array();
		}
		if ( null === $source ) {
			$slug = rawurldecode( basename( rtrim( $path, '/' ) ) );
			foreach ( get_object_taxonomies( 'product', 'names' ) as $taxonomy ) {
				if ( ! is_taxonomy_viewable( $taxonomy ) ) {
					continue;
				}
				$term = get_term_by( 'slug', $slug, $taxonomy );
				if ( ! $term instanceof WP_Term ) {
					continue;
				}
				$link = get_term_link( $term );
				if ( is_string( $link ) && self::same_path( $path, $link ) ) {
					$source = array(
						'type'     => 'term',
						'id'       => $term->term_id,
						'taxonomy' => $term->taxonomy,
						'title'    => $term->name,
						'source'   => $link,
					);
					break;
				}
			}
		}
		if ( null === $source ) {
			return array();
		}
		$selection = self::selection( is_array( $value['selection'] ?? null ) ? $value['selection'] : array() );
		// Match the existing native FormRecovery field limit without silently truncating a selected search.
		$transport = wp_json_encode(
			array(
				'source'    => $source['source'],
				'selection' => $selection,
			)
		);
		if ( ! is_string( $transport ) || mb_strlen( $transport ) > Submission::MAX_MESSAGE ) {
			return array();
		}
		return array_merge(
			$source,
			array(
				'selection' => $selection,
				'url'       => add_query_arg( array_map( static fn( $item ): string => rawurlencode( (string) $item ), $selection ), $source['source'] ),
			)
		);
	}

	/**
	 * Only a current public native twin at the exact requested path can replace a lookup.
	 *
	 * @param WP_Post $post Public native lookup result.
	 * @param string  $path Requested canonical path.
	 */
	private static function translation_at_path( WP_Post $post, string $path ): ?WP_Post {
		if ( ! function_exists( 'pll_get_post_translations' ) ) {
			return null;
		}
		foreach ( pll_get_post_translations( $post->ID ) as $id ) {
			if ( $id === $post->ID ) {
				continue;
			}
			$twin = get_post( $id );
			if ( $twin instanceof WP_Post && $twin->post_type === $post->post_type && 'publish' === $twin->post_status && '' === $twin->post_password && self::same_path( $path, (string) get_permalink( $twin ) ) ) {
				return $twin;
			}
		}
		return null;
	}

	/**
	 * Current transport values, including the older public contact-link shape.
	 *
	 * @param array<string,mixed> $query Unslashed read-only URL query.
	 * @return array<string,mixed>
	 */
	public static function query( array $query ): array {
		if ( isset( $query[ self::FIELD ] ) && is_string( $query[ self::FIELD ] ) ) {
			return self::normalize( json_decode( $query[ self::FIELD ], true ) );
		}
		$selection = is_array( $query['filters'] ?? null ) ? $query['filters'] : array();
		if ( is_string( $query['search'] ?? null ) ) {
			$selection['q'] = $query['search'];
		}
		if ( is_string( $query['sort'] ?? null ) ) {
			$selection['sort'] = $query['sort'];
		}
		foreach ( array( 'platform', 'document' ) as $key ) {
			if ( is_string( $query[ $key ] ?? null ) ) {
				$selection[ $key ] = $query[ $key ];
			}
		}
		return self::normalize(
			array(
				'source'    => $query['source'] ?? '',
				'selection' => $selection,
			)
		);
	}

	/**
	 * Verified public context follows the native language link; arbitrary JSON does not.
	 *
	 * @param array<string,mixed> $query Unslashed read-only navigation query.
	 * @param string              $language Target language slug.
	 * @return array<string,string> Unencoded values for the language URL writer.
	 */
	public static function language_query( array $query, string $language ): array {
		$result = array();
		$intent = $query['intent'] ?? null;
		if ( is_string( $intent ) && in_array( $intent, Form::INTENTS, true ) ) {
			$result['intent'] = $intent;
		}
		$context = self::query( $query );
		if ( array() === $context ) {
			return $result;
		}
		$source    = (string) $context['source'];
		$id        = (int) $context['id'];
		$homepage  = self::home_page( (string) wp_parse_url( $source, PHP_URL_PATH ) );
		$languages = class_exists( Languages::class ) ? new Languages() : null;
		if ( null !== $homepage && null !== $languages && $languages->exists( $language ) ) {
			$source = $languages->home_url( $language );
		} elseif ( 'term' === $context['type'] ) {
			$twin = function_exists( 'pll_get_term' ) ? (int) pll_get_term( $id, $language ) : 0;
			$link = $twin > 0 ? get_term_link( $twin ) : $source;
			if ( is_string( $link ) ) {
				$source = $link;
			}
			// Shared, untranslated product taxonomies keep the native language base.
			if ( 0 === $twin && function_exists( 'PLL' ) ) {
				$target = PLL()->model->get_language( $language );
				if ( $target instanceof \PLL_Language ) {
					$source = (string) PLL()->links_model->switch_language_in_link( $source, $target );
				}
			}
		} elseif ( function_exists( 'pll_get_post' ) ) {
			$twin = (int) pll_get_post( $id, $language );
			$link = $twin > 0 ? get_permalink( $twin ) : false;
			if ( is_string( $link ) ) {
				$source = $link;
			}
		}
		/**
		 * Apply the site's native localized product and shared-taxonomy bases.
		 *
		 * @since 0.2.0
		 *
		 * @param string $source Validated public object's native language permalink.
		 * @param string $language Target language slug.
		 */
		$source = (string) apply_filters( 'pll_translation_url', $source, $language ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound -- existing native language URL seam.
		if ( self::same_origin( $source ) ) {
			$result[ self::FIELD ] = (string) wp_json_encode(
				array(
					'source'    => $source,
					'selection' => $context['selection'],
				)
			);
		}
		return $result;
	}

	/**
	 * Native static front pages have language home URLs even outside a front-end request.
	 * Resolve them before url_to_postid, which can return zero for the German root.
	 *
	 * @param string $path Proposed source path.
	 * @return array{id:int,source:string}|null A recognized home path, including a missing twin.
	 */
	private static function home_page( string $path ): ?array {
		if ( 'page' !== get_option( 'show_on_front' ) ) {
			return null;
		}
		$front     = (int) get_option( 'page_on_front' );
		$languages = class_exists( Languages::class ) ? new Languages() : null;
		if ( null !== $languages && $languages->ready() ) {
			foreach ( array( Languages::SOURCE, Languages::TARGET ) as $language ) {
				$url = $languages->home_url( $language );
				if ( self::same_path( $path, $url ) ) {
					return array(
						'id'     => $front > 0 ? (int) pll_get_post( $front, $language ) : 0,
						'source' => $url,
					);
				}
			}
			return null;
		}
		$url = home_url();
		return self::same_path( $path, $url ) ? array(
			'id'     => $front,
			'source' => $url,
		) : null;
	}

	/**
	 * JSON strings retain bytes in both Woo data stores; legacy array values remain readable.
	 *
	 * @param mixed $stored Native order metadata.
	 * @return array<string,mixed>
	 */
	public static function stored( mixed $stored ): array {
		$value = is_string( $stored ) ? json_decode( $stored, true ) : $stored;
		return is_array( $value ) ? $value : array();
	}

	/**
	 * Only known navigation values survive; no transport credentials or arbitrary URL parameters.
	 *
	 * @param array<string,mixed> $input Public selected filters.
	 * @return array<string,string|float>
	 */
	private static function selection( array $input ): array {
		$result = array();
		foreach ( array( 'application', 'brand', 'phase', 'power' ) as $key ) {
			$value = is_string( $input[ $key ] ?? null ) ? sanitize_key( $input[ $key ] ) : '';
			if ( '' !== $value ) {
				$result[ $key ] = $value;
			}
		}
		foreach ( array( 'kw_min', 'kw_max', 'kwh_min', 'kwh_max' ) as $key ) {
			$value = $input[ $key ] ?? null;
			if ( ! is_string( $value ) && ! is_int( $value ) && ! is_float( $value ) ) {
				continue;
			}
			$number = str_replace( ',', '.', (string) $value );
			if ( is_numeric( $number ) && is_finite( (float) $number ) && (float) $number > 0 ) {
				$result[ $key ] = (float) $number;
			}
		}
		// These are customer request labels, like search text, never product authority.
		foreach ( array( 'q', 'platform', 'document' ) as $key ) {
			if ( ! is_string( $input[ $key ] ?? null ) ) {
				continue;
			}
			$text = sanitize_text_field( $input[ $key ] );
			if ( '' !== $text ) {
				$result[ $key ] = $text;
			}
		}
		if ( is_string( $input['sort'] ?? null ) && in_array( $input['sort'], array( 'recommended', 'newest', 'name', 'power-desc', 'power-asc' ), true ) ) {
			$result['sort'] = $input['sort'];
		}
		return $result;
	}

	/**
	 * No remote requests, foreign hosts, alternate ports, userinfo or executable schemes.
	 *
	 * @param string $url Proposed public source.
	 */
	private static function same_origin( string $url ): bool {
		$parts = wp_parse_url( $url );
		$home  = wp_parse_url( home_url() );
		return is_array( $parts ) && is_array( $home ) && ! isset( $parts['user'] ) && ! isset( $parts['pass'] )
			&& in_array( $parts['scheme'] ?? '', array( 'http', 'https' ), true )
			&& strtolower( $parts['scheme'] ) === strtolower( (string) ( $home['scheme'] ?? '' ) )
			&& strtolower( (string) ( $parts['host'] ?? '' ) ) === strtolower( (string) ( $home['host'] ?? '' ) )
			&& ( $parts['port'] ?? null ) === ( $home['port'] ?? null );
	}

	/**
	 * The resolved object's own URL must match the supplied source path.
	 *
	 * @param string $path Supplied source path.
	 * @param string $url Current canonical public URL.
	 */
	private static function same_path( string $path, string $url ): bool {
		return self::same_origin( $url ) && rtrim( $path, '/' ) === rtrim( (string) wp_parse_url( $url, PHP_URL_PATH ), '/' );
	}
}
