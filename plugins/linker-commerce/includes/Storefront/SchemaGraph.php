<?php
/**
 * One structured-data graph from the site's head publishers.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;

/** Collect the filtered output from SEOPress, the child theme and the storefront. */
final class SchemaGraph {
	/**
	 * Whether this head opened an output buffer.
	 *
	 * @var bool
	 */
	private bool $buffering = false;

	/** Register on either side of the existing head callbacks. */
	public function register(): void {
		add_filter( 'seopress_schemas_graph_enabled', '__return_false', 99 );
		add_action( 'wp_head', array( $this, 'start_buffer' ), -1000 );
		add_action( 'wp_head', array( $this, 'flush_buffer' ), 9999 );
	}

	/** Start collecting the public HTML head. */
	public function start_buffer(): void {
		if ( ! is_admin() && ! wp_doing_ajax() && ! ( defined( 'REST_REQUEST' ) && REST_REQUEST ) ) {
			$this->buffering = ob_start();
		}
	}

	/** Return the original head markup and its unified JSON-LD script. */
	public function flush_buffer(): void {
		if ( ! $this->buffering ) {
			return;
		}
		$this->buffering = false;
		$html            = ob_get_clean();
		if ( is_string( $html ) ) {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Existing wp_head HTML; the new script is JSON encoded below.
			echo $this->consolidate( $html, is_front_page() );
		}
	}

	/**
	 * Move the valid JSON-LD nodes to one graph, preserving other head markup.
	 *
	 * @param string $html Head HTML printed by the native hooks.
	 * @param bool   $front Whether this is a localized front page.
	 */
	public function consolidate( string $html, bool $front ): string {
		$entries = array();
		$head    = preg_replace_callback(
			'~<!--.*?-->(*SKIP)(*F)|<script\b([^>]*)>(.*?)</script\s*>~is',
			static function ( array $script ) use ( &$entries ): string {
				if ( ! preg_match( '~(?:"[^"]*"|\'[^\']*\')(*SKIP)(*F)|\stype\s*=\s*(?:"application/ld\+json"|\'application/ld\+json\'|application/ld\+json)(?=\s|$)~i', $script[1] ) ) {
					return $script[0];
				}
				$data = json_decode( trim( $script[2] ), true );
				if ( ! is_array( $data ) ) {
					return $script[0];
				}
				if ( is_array( $data['@graph'] ?? null ) ) {
					array_push( $entries, ...$data['@graph'] );
				} elseif ( array_is_list( $data ) ) {
					array_push( $entries, ...$data );
				} else {
					$entries[] = $data;
				}
				return '';
			},
			$html
		);
		if ( null === $head ) {
			return $html;
		}

		$nodes     = array();
		$positions = array();
		foreach ( $entries as $node ) {
			if ( ! is_array( $node ) || empty( $node['@type'] ) ) {
				continue;
			}
			unset( $node['@context'] );
			$types = (array) $node['@type'];
			$id    = $node['@id'] ?? '';
			$org   = in_array( 'Organization', $types, true ) && ! array_intersect( array( 'WebPage', 'AboutPage', 'ContactPage' ), $types );
			if ( ! $front && in_array( 'WebSite', $types, true ) ) {
				continue;
			}
			if ( ! $front && $org && ( PageUrls::root() . '#organization' === $id || 'Linker Technology GmbH' === ( $node['legalName'] ?? '' ) || 'Linker' === ( $node['name'] ?? '' ) ) ) {
				continue;
			}
			if ( is_string( $id ) && '' !== $id ) {
				if ( isset( $positions[ $id ] ) ) {
					$position = $positions[ $id ];
					if ( $front && $org && ! empty( $node['legalName'] ) && empty( $nodes[ $position ]['legalName'] ) ) {
						$nodes[ $position ] = $node;
					}
					continue;
				}
				$positions[ $id ] = count( $nodes );
			} elseif ( in_array( $node, $nodes, true ) ) {
				continue;
			}
			$nodes[] = $node;
		}

		if ( ! $nodes ) {
			return $head;
		}
		$json = wp_json_encode(
			array(
				'@context' => 'https://schema.org',
				'@graph'   => $nodes,
			),
			JSON_HEX_TAG | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
		);
		return $head . '<script id="linker-schema-graph" type="application/ld+json">' . $json . "</script>\n";
	}
}
