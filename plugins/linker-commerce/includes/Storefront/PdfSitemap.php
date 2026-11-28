<?php
/**
 * Public PDF sitemap for the engineering toolkit and current product documents.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Presentation\PageUrls;
use Linker\Commerce\Products\EngineeringReference;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\Publication\DocumentCache;
use Linker\Commerce\Products\Publication\DocumentFiles;
use Linker\Commerce\Products\ToolkitRegistry;

/** Enumerate primary document URLs currently associated with sale products. */
final class PdfSitemap {
	public const NAME = 'pdf-sitemap1.xml';

	/** Register before the native sitemap rewrite and main query. */
	public function register(): void {
		add_filter( 'do_parse_request', array( $this, 'serve' ), 1 );
	}

	/** Toolkit editions first, then unique OEM URLs in canonical order.
	 *
	 * @return list<array{loc:string,lastmod:string}>
	 */
	public function entries(): array {
		$manifest = Publication::library_read();
		$allowed  = array();
		foreach ( $manifest['products'] as $product ) {
			if ( empty( $product['published_locale_ids'] ) || EngineeringReference::is_reference( $product['product_id'] ) ) {
				continue;
			}
			foreach ( $product['documents'] as $id ) {
				$allowed[ $id ] = true;
			}
		}
		$entries = array();
		foreach ( ToolkitRegistry::pdfs() as $asset ) {
			$entries[] = array(
				'loc'     => $asset['url'],
				'lastmod' => $asset['lastmod'],
			);
		}
		$oem = array();
		DocumentFiles::begin_read( true, true );
		try {
			foreach ( $manifest['documents'] as $document ) {
				if ( ! isset( $allowed[ $document['document_id'] ] ) ) {
					continue;
				}
				$file = DocumentFiles::resolve( $document['url'] );
				if ( null === $file ) {
					continue;
				}
				$id                  = attachment_url_to_postid( $file['url'] );
				$date                = $id ? get_post_datetime( $id, 'modified', 'gmt' ) : false;
				$oem[ $file['url'] ] = array(
					'loc'     => $file['url'],
					'lastmod' => gmdate( DATE_ATOM, $date ? $date->getTimestamp() : (int) filemtime( $file['path'] ) ),
				);
			}
		} finally {
			DocumentFiles::end_read();
		}
		ksort( $oem, SORT_STRING );
		return array_merge( $entries, array_values( $oem ) );
	}

	/** Modification date of the most recent listed document. */
	public function latest_lastmod(): string {
		$dates = array_column( $this->entries(), 'lastmod' );
		return $dates ? max( $dates ) : '';
	}

	/** Render the same public inventory consumed by the sitemap index. */
	public function render_xml(): string {
		$xml = '<?xml version="1.0" encoding="UTF-8"?>' . "\n"
			. '<?xml-stylesheet type="text/xsl" href="' . esc_xml( PageUrls::root() . 'sitemaps_xsl.xsl' ) . '"?>' . "\n"
			. '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . "\n";
		foreach ( $this->entries() as $row ) {
			$xml .= '<url><loc>' . esc_xml( $row['loc'] ) . '</loc><lastmod>' . esc_xml( $row['lastmod'] ) . "</lastmod></url>\n";
		}
		return $xml . "</urlset>\n";
	}

	/**
	 * Serve the public XML resource without a page template.
	 *
	 * @param bool $parse Whether WordPress should parse the request.
	 */
	public function serve( bool $parse ): bool {
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Exact public path match only.
		if ( ! $parse || wp_parse_url( wp_unslash( $_SERVER['REQUEST_URI'] ?? '' ), PHP_URL_PATH ) !== wp_parse_url( PageUrls::root() . self::NAME, PHP_URL_PATH ) ) {
			return $parse;
		}
		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput -- Strict comparison to the supported public methods.
		$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
		if ( ! in_array( $method, array( 'GET', 'HEAD' ), true ) ) {
			status_header( 405 );
			DocumentCache::forbid( true );
			header( 'Allow: GET, HEAD' );
			exit;
		}
		$xml = $this->render_xml();
		status_header( 200 );
		header( 'Content-Type: application/xml; charset=UTF-8' );
		header( 'X-Robots-Tag: noindex, follow' );
		header( 'Cache-Control: public, max-age=900, stale-while-revalidate=300' );
		DocumentCache::allow( array( 'LK.pdf.sitemap', 'LK.pdf', 'LK.toolkit', 'PT.product' ), 15 * MINUTE_IN_SECONDS );
		if ( 'GET' === $method ) {
			echo $xml; // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- Document URLs and dates are XML-escaped when assembled.
		}
		exit;
	}
}
