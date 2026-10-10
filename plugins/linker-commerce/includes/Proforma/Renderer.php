<?php
/**
 * HTML to PDF.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Proforma;

use Dompdf\Dompdf;
use Dompdf\Options as DompdfOptions;

/**
 * Renders the Proforma template to PDF with dompdf (dompdf/dompdf 3.1,
 * LGPL-2.1; its php-font-lib LGPL-2.1-or-later and php-svg-lib
 * LGPL-3.0-or-later, html5 and php-css-parser MIT). The template is filled by
 * WooCommerce's template loader, so a theme may override it as
 * woocommerce/proforma/proforma.php.
 */
final class Renderer {

	/**
	 * Sets up the renderer.
	 *
	 * @param string $plugin_file Absolute path of the main plugin file.
	 */
	public function __construct( private readonly string $plugin_file ) {}

	/**
	 * The filled template as HTML.
	 *
	 * @param array<string, mixed> $data Document data (Document::data()).
	 */
	public function html( array $data ): string {
		return wc_get_template_html( 'proforma/proforma.php', array( 'proforma' => $data ), '', plugin_dir_path( $this->plugin_file ) . 'templates/' );
	}

	/**
	 * The PDF of an HTML document, on A4 paper (ISO 216, the business paper size in Germany).
	 *
	 * @param string $html HTML.
	 */
	public function pdf( string $html ): string {
		$options = new DompdfOptions();
		// Nothing is fetched while rendering: the template is self-contained.
		$options->setIsRemoteEnabled( false );
		$options->setChroot( array( plugin_dir_path( $this->plugin_file ) ) );
		// DejaVu Sans ships with dompdf and covers €, umlauts and ß.
		$options->setDefaultFont( 'DejaVu Sans' );
		$options->setTempDir( get_temp_dir() );
		$options->setFontCache( get_temp_dir() );

		$dompdf = new Dompdf( $options );
		$dompdf->loadHtml( $html, 'UTF-8' );
		$dompdf->setPaper( 'A4' );
		$dompdf->render();
		return (string) $dompdf->output();
	}
}
