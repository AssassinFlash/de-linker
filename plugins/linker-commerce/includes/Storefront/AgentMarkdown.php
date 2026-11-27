<?php
/**
 * Public page and engineering representations for SEOPress.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Products\Publication;

/** Integrate structured content with the native Markdown negotiation and discovery endpoints. */
final class AgentMarkdown {
	/** Register SEOPress PRO public filters. */
	public function register(): void {
		add_filter( 'seopress_agent_ready_markdown_post_types', array( $this, 'markdown_post_types' ) );
		add_filter( 'seopress_agent_ready_html_to_markdown', array( $this, 'html_to_markdown' ), 10, 2 );
		add_filter( 'seopress_agent_ready_markdown_body', array( $this, 'markdown_body' ), 20, 2 );
		add_filter( 'seopress_agent_ready_home_markdown_body', array( $this, 'home_markdown_body' ), 20 );
		add_filter( 'seopress_agent_ready_a2a_agent_card', array( $this, 'clean_well_known_card' ), 20 );
		add_filter( 'seopress_agent_ready_mcp_card', array( $this, 'mcp_card' ), 20 );
		add_filter( 'seopress_agent_ready_agent_skills', array( $this, 'clean_well_known_card' ), 20 );
	}

	/**
	 * Enable the representation for publicly supplied products.
	 *
	 * @param string[] $types Existing SEOPress post types.
	 * @return string[]
	 */
	public function markdown_post_types( array $types ): array {
		if ( is_singular( 'page' ) && ( new PageIndexing() )->transaction() ) {
			return array_values( array_diff( $types, array( 'page' ) ) );
		}
		if ( is_singular( 'product' ) && ! Publication::published_ids( array( (int) get_queried_object_id() ), true ) ) {
			return array_values( array_diff( $types, array( 'product' ) ) );
		}
		return array_values( array_unique( array_merge( $types, array( 'product' ) ) ) );
	}

	/**
	 * Convert the rendered page body, including server-rendered engineering tables.
	 *
	 * @param string|null $short Existing replacement.
	 * @param string      $html Rendered HTML.
	 */
	public function html_to_markdown( ?string $short, string $html ): string {
		if ( null !== $short ) {
			return $short;
		}
		$doc = new \DOMDocument();
		$doc->loadHTML( '<meta charset="utf-8"><body>' . $html . '</body>', LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING );
		return self::clean( self::node( $doc ) );
	}

	// phpcs:disable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase -- PHP DOM uses native camelCase properties.

	/**
	 * Render visible content in document order.
	 *
	 * @param \DOMNode $node HTML node.
	 */
	private static function node( \DOMNode $node ): string {
		if ( $node instanceof \DOMText ) {
			return (string) preg_replace( '/\s+/u', ' ', $node->textContent );
		}
		if ( $node instanceof \DOMElement ) {
			if ( $node->hasAttribute( 'hidden' ) || 'true' === $node->getAttribute( 'aria-hidden' ) || in_array( $node->tagName, array( 'script', 'style', 'svg', 'noscript', 'dialog', 'template', 'form', 'button' ), true ) ) {
				return '';
			}
			if ( 'table' === $node->tagName ) {
				return self::table( $node );
			}
			if ( 'pre' === $node->tagName ) {
				return "\n\n```\n" . rtrim( $node->textContent ) . "\n```\n\n";
			}
		}
		$body = '';
		foreach ( $node->childNodes as $child ) {
			$body .= self::node( $child );
		}
		$value = trim( $body );
		return match ( $node->nodeName ) {
			'h1', 'h2', 'h3', 'h4', 'h5', 'h6' => "\n\n" . str_repeat( '#', (int) substr( $node->nodeName, 1 ) ) . ' ' . $value . "\n\n",
			'a' => $node instanceof \DOMElement && '' !== esc_url_raw( $node->getAttribute( 'href' ) ) && '' !== $value ? '[' . $value . '](' . esc_url_raw( $node->getAttribute( 'href' ) ) . ')' : $body,
			'strong', 'b' => '**' . $value . '**',
			'em', 'i' => '*' . $value . '*',
			'code' => '`' . $body . '`',
			'dt' => "\n- **" . $value . '**: ',
			'dd' => $value . "\n",
			'li' => "\n- " . $value . "\n",
			'hr' => "\n\n---\n\n",
			'br' => "\n",
			'p', 'section', 'div', 'aside', 'article', 'details', 'summary', 'header', 'footer' => '' === $value ? '' : "\n" . $value . "\n",
			default => $body,
		};
	}

	/**
	 * Preserve cell boundaries and links in a GFM table.
	 *
	 * @param \DOMElement $table Rendered table.
	 */
	private static function table( \DOMElement $table ): string {
		$rows = array();
		foreach ( $table->getElementsByTagName( 'tr' ) as $row ) {
			$cells = array();
			foreach ( $row->childNodes as $cell ) {
				if ( in_array( $cell->nodeName, array( 'th', 'td' ), true ) ) {
					$cells[] = self::node( $cell );
				}
			}
			if ( $cells ) {
				$rows[] = self::row( $cells );
				if ( 1 === count( $rows ) ) {
					$rows[] = self::row( array_fill( 0, count( $cells ), '---' ) );
				}
			}
		}
		return "\n\n" . implode( "\n", $rows ) . "\n\n";
	}

	// phpcs:enable WordPress.NamingConventions.ValidVariableName.UsedPropertyNotSnakeCase

	/**
	 * A single GFM row from visible text or formatted links.
	 *
	 * @param string[] $cells Cell content.
	 */
	public static function row( array $cells ): string {
		$cells = array_map( static fn( string $cell ): string => str_replace( '|', '\\|', trim( (string) preg_replace( '/\s+/u', ' ', $cell ) ) ), $cells );
		return '| ' . implode( ' | ', $cells ) . ' |';
	}

	/**
	 * Remove unresolved LiveCanvas shortcodes from SEOPress excerpts and bodies.
	 *
	 * @param string $text Markdown.
	 */
	private static function clean( string $text ): string {
		$text = (string) preg_replace( '/\[\/?(?:linker|lc)_[a-z0-9_]+[^\]]*\]/i', '', strip_shortcodes( $text ) );
		return trim( (string) preg_replace( "/\n[ \t]*\n(?:[ \t]*\n)+/", "\n\n", $text ) );
	}

	/**
	 * Headers for the alternate representation.
	 *
	 * @param string $url Canonical HTML permalink.
	 */
	private static function headers( string $url ): void {
		if ( ! headers_sent() ) {
			header( 'X-Robots-Tag: noindex, follow' );
			if ( '' !== $url ) {
				header( 'Link: <' . esc_url_raw( $url ) . '>; rel="canonical"', false );
			}
		}
	}

	/**
	 * Clean the posts index when SEOPress handles a non-static homepage.
	 *
	 * @param string $markdown Native representation.
	 */
	public function home_markdown_body( string $markdown ): string {
		self::headers( PageUrls::home() );
		return self::clean( $markdown ) . "\n";
	}

	/**
	 * Supply the reviewed description or the published product data.
	 *
	 * @param string   $markdown Native page representation.
	 * @param \WP_Post $post Current public post.
	 */
	public function markdown_body( string $markdown, \WP_Post $post ): string {
		$url = (string) get_permalink( $post );
		self::headers( $url );
		if ( 'product' === $post->post_type ) {
			if ( ! Publication::published_ids( array( $post->ID ), true ) ) {
				return '';
			}
			$product = wc_get_product( $post->ID );
			return $product instanceof \WC_Product ? $this->product_markdown( $product ) : '';
		}
		$description = (string) get_post_meta( $post->ID, '_seopress_titles_desc', true );
		if ( '' === trim( $description ) ) {
			$description = has_excerpt( $post ) ? get_the_excerpt( $post ) : wp_trim_words( wp_strip_all_tags( self::clean( $post->post_content ) ), 40 );
		}
		$description = self::clean( html_entity_decode( wp_strip_all_tags( $description, true ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
		$markdown    = (string) preg_replace_callback( '/^> .*?\n(?=> URL:)/ms', static fn(): string => '> ' . $description . "\n", $markdown, 1 );
		return self::clean( $markdown ) . "\n";
	}

	/**
	 * Human-readable specifications, release conditions and authorized document links.
	 *
	 * @param \WC_Product $product Public product.
	 */
	private function product_markdown( \WC_Product $product ): string {
		$id   = $product->get_id();
		$data = ( new ProductSchema() )->data( $product );
		$view = new ProductView();
		$out  = array( '# ' . $data['name'], '', '> ' . $data['description'], '> URL: ' . $data['url'], '> Last modified: ' . get_post_modified_time( 'c', true, $id ), '' );
		$meta = array(
			__( 'Brand', 'linker-commerce' )    => $data['brand']['name'] ?? '',
			__( 'Model', 'linker-commerce' )    => $data['model'] ?? '',
			'SKU'                               => $data['sku'] ?? '',
			'MPN'                               => $data['mpn'] ?? '',
			__( 'Category', 'linker-commerce' ) => $data['category'] ?? '',
		);
		foreach ( $meta as $label => $value ) {
			if ( '' !== $value ) {
				$out[] = '- **' . $label . '**: ' . $value;
			}
		}
		$out[]  = "\n## " . __( 'Technical specifications', 'linker-commerce' );
		$groups = $view->spec_groups( $id );
		foreach ( $groups as $group ) {
			$out[] = "\n### " . $group['title'] . "\n";
			$out[] = self::row( array( __( 'Specification', 'linker-commerce' ), __( 'Value', 'linker-commerce' ) ) );
			$out[] = '| --- | --- |';
			foreach ( $group['rows'] as $row ) {
				$out[] = self::row( array( $row['label'], $row['value'] . ' ' . $row['unit'] . ' ' . $row['note'] ) );
			}
		}
		if ( ! empty( $data['additionalProperty'] ) ) {
			$out[] = '';
			$out[] = self::row( array( __( 'Engineering data', 'linker-commerce' ), __( 'Value', 'linker-commerce' ) ) );
			$out[] = '| --- | --- |';
			foreach ( $data['additionalProperty'] as $fact ) {
				$out[] = self::row( array( $fact['name'], (string) $fact['value'] . ' ' . ( $fact['unitText'] ?? '' ) ) );
			}
		}
		$pairs = CompatibilityIndex::for_product( $id )['compatible'];
		if ( $pairs ) {
			$out[] = "\n## " . __( 'Verified compatibility', 'linker-commerce' ) . "\n";
			$out[] = self::row( array( __( 'Model', 'linker-commerce' ), __( 'Release status', 'linker-commerce' ), __( 'Required accessory', 'linker-commerce' ), __( 'Conditions', 'linker-commerce' ) ) );
			$out[] = '| --- | --- | --- | --- |';
			foreach ( $pairs as $pair ) {
				$accessories = array_map( self::product_link( ... ), $pair['accessories'] );
				$out[]       = self::row( array( self::product_link( $pair ), 'released_with_accessory' === $pair['verdict'] ? __( 'Released with accessory', 'linker-commerce' ) : __( 'Released', 'linker-commerce' ), implode( ', ', $accessories ), implode( ' ', $pair['conditions'] ) ) );
			}
		}
		$documents = $view->downloads( $id );
		if ( $documents ) {
			$out[] = "\n## " . __( 'Manufacturer documentation', 'linker-commerce' ) . "\n";
			foreach ( $documents as $doc ) {
				$out[] = '- [' . Materials::localized_document_title( $doc['title'], null, $doc['url'] ) . '](' . $doc['url'] . ') · ' . trim( Materials::document_kind_label( Materials::document_kind( $doc['role'], $doc['type'] ) ) . ' ' . strtoupper( $doc['language'] ) );
			}
		}
		$out[] = "\n## " . __( 'Support & quotation', 'linker-commerce' ) . "\n";
		foreach ( array( 'contact', 'solution-configurator', 'inverter-battery-compatibility' ) as $slug ) {
			$url = PageUrls::translated( $slug );
			if ( '' !== $url ) {
				$out[] = '- [' . get_the_title( url_to_postid( $url ) ) . '](' . $url . ')';
			}
		}
		return implode( "\n", $out ) . "\n";
	}

	/**
	 * Link to a published localized product.
	 *
	 * @param array<string,mixed> $item Release row.
	 */
	private static function product_link( array $item ): string {
		return '[' . $item['name'] . '](' . $item['url'] . ')';
	}

	/**
	 * Decode HTML transport entities for JSON clients.
	 *
	 * @param array<string,mixed> $card Native discovery card.
	 * @return array<string,mixed>
	 */
	public function clean_well_known_card( array $card ): array {
		foreach ( array( 'name', 'description' ) as $key ) {
			if ( isset( $card[ $key ] ) ) {
				$card[ $key ] = html_entity_decode( $card[ $key ], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
			}
		}
		if ( isset( $card['serverInfo']['name'] ) ) {
			$card['serverInfo']['name'] = html_entity_decode( $card['serverInfo']['name'], ENT_QUOTES | ENT_HTML5, 'UTF-8' );
		}
		return $card;
	}

	/**
	 * Register the site's two public engineering resources.
	 *
	 * @param array<string,mixed> $card Native MCP card.
	 * @return array<string,mixed>
	 */
	public function mcp_card( array $card ): array {
		$card = $this->clean_well_known_card( $card );
		$seen = array_column( $card['resources'], 'uri' );
		foreach ( array( array( 'llms-full', PageUrls::root() . 'llms-full.txt', 'text/plain' ), array( 'engineering-feed', rest_url( 'linker/v1/engineering-feed' ), 'application/json' ) ) as list( $name, $uri, $mime ) ) {
			if ( ! in_array( $uri, $seen, true ) ) {
				$card['resources'][] = array(
					'name'     => $name,
					'uri'      => $uri,
					'mimeType' => $mime,
				);
			}
		}
		return $card;
	}
}
