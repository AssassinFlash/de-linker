<?php
/**
 * Model comparisons at common grid-connection limits.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\Publication;

/** Electrical values describe the individual unit at the grid terminals. */
final class GridThresholdPairs {
	/** Model, maximum grid kVA, maximum line current at 400 V, battery or backup rating, counterpart SKU, selection note and threshold comparison. */
	private const MODELS = array(
		'DLK-GOODWE-GW9999KETAG20'  => array( 'GW9.999K-ETA-G20', '9.999', '14.5', '10 kVA', 'DLK-GOODWE-GW10KETAG20', 'ten', '−0.001 kVA' ),
		'DLK-GOODWE-GW10KETAG20'    => array( 'GW10K-ETA-G20', '10', '14.5', '10 kVA', 'DLK-GOODWE-GW9999KETAG20', 'ten', '0 kVA' ),
		'DLK-GOODWE-GW29999KETAG20' => array( 'GW29.999K-ETA-G20', '29.999', '43.5', '30 kVA', 'DLK-GOODWE-GW30KETAG20', 'thirty', '−0.001 kVA' ),
		'DLK-GOODWE-GW30KETAG20'    => array( 'GW30K-ETA-G20', '30', '43.5', '30 kVA', 'DLK-GOODWE-GW29999KETAG20', 'thirty', '0 kVA' ),
		'DLK-SAJ-H230KT3DE'         => array( 'H2-30K-T3-DE', '29.999', '43.4', '45 kVA / 3 s', 'DLK-SAJ-H225KT3', 'h2', '−0.001 kVA' ),
		'DLK-SAJ-H225KT3'           => array( 'H2-25K-T3', '27.5', '39.9', '37.5 kVA / 3 s', 'DLK-SAJ-H230KT3DE', 'h2', '−2.5 kVA' ),
		'DLK-SAJ-CHS2299KT4X'       => array( 'CHS2-29.9K-T4-X', '29.999', '43.3', '29.999 kVA', 'DLK-SAJ-CHS230KT4X', 'chs2', '−0.001 kVA' ),
		'DLK-SAJ-CHS230KT4X'        => array( 'CHS2-30K-T4-X', '33', '47.9', '45 kVA / 5 s', 'DLK-SAJ-CHS2299KT4X', 'chs2', '+3 kVA' ),
		'DLK-GOODWE-GW9999KETG10'   => array( 'GW99.99K-ET-G10', '99.99', '144.4', '99.99 kW', 'DLK-GOODWE-GW100KETG10', 'hundred', '99.99 kW' ),
		'DLK-GOODWE-GW100KETG10'    => array( 'GW100K-ET-G10', '110', '158.8', '110 kW', 'DLK-GOODWE-GW9999KETG10', 'hundred', '100 kW' ),
		'DLK-GOODWE-GW9999KETRG10'  => array( 'GW99.99K-ETR-G10', '99.99', '144.4', '99.99 kW', 'DLK-GOODWE-GW100KETRG10', 'hundred', '99.99 kW' ),
		'DLK-GOODWE-GW100KETRG10'   => array( 'GW100K-ETR-G10', '110', '158.8', '110 kW', 'DLK-GOODWE-GW9999KETRG10', 'hundred', '100 kW' ),
		'DLK-GOODWE-GW12499KETRG10' => array( 'GW124.99K-ETR-G10', '124.99', '180.5', '124.99 kW', 'DLK-GOODWE-ETR125', 'etr', '124.99 kW' ),
		'DLK-GOODWE-ETR125'         => array( 'GW125K-ETR-G10', '137.5', '198.5', '137.5 kW', 'DLK-GOODWE-GW12499KETRG10', 'etr', '137.5 kW' ),
	);

	private const NOTES = array(
		'ten'     => array(
			'Both units accept 20 kW of PV across four trackers. Where the connection agreement specifies strictly less than 10 kVA, only the 9.999 kVA model meets that limit on its own.',
			'Beide Geräte nehmen 20 kW PV-Leistung über vier Tracker auf. Verlangt der Netzanschlussvertrag ausdrücklich weniger als 10 kVA, erfüllt nur das 9,999-kVA-Modell diese Grenze als Einzelgerät.',
		),
		'thirty'  => array(
			'Under VDE-AR-N 4105, central grid protection applies above 30 kVA summed across the inverters at the connection. Both units reach 43.5 A at 400 V. For metering, compare the continuous current at the meter with the local limits, including any 44 A limit for direct measurement.',
			'Nach VDE-AR-N 4105 ist bei mehr als 30 kVA Summenscheinleistung am Netzanschluss ein zentraler NA-Schutz erforderlich. Beide Geräte erreichen 43,5 A bei 400 V. Für die Messung zählt der Dauerstrom am Zählerplatz nach örtlichen Anschlussbedingungen, etwa bei einer Direktmessgrenze von 44 A.',
		),
		'h2'      => array(
			'The 25 kW model leaves 2.5 kVA below the 30 kVA total for central grid protection under VDE-AR-N 4105. At a meter with a 44 A continuous-current limit, check the contribution of existing equipment alongside the inverter.',
			'Beim 25-kW-Modell verbleiben 2,5 kVA bis zur 30-kVA-Summengrenze für den zentralen NA-Schutz nach VDE-AR-N 4105. Gilt am Zähler eine Dauerstromgrenze von 44 A, berücksichtigen Sie auch die vorhandenen Geräte.',
		),
		'chs2'    => array(
			'The 33 kVA cabinet alone exceeds the 30 kVA total for central grid protection under VDE-AR-N 4105. Its 47.9 A maximum also warrants a metering check where the local direct-meter limit is 44 A continuous.',
			'Der Schrank mit 33 kVA überschreitet bereits allein die 30-kVA-Summengrenze für zentralen NA-Schutz nach VDE-AR-N 4105. Bei maximal 47,9 A ist auch der Dauerstrom am Zählerplatz relevant, wenn die örtlichen Anschlussbedingungen Direktmessung bis 44 A zulassen.',
		),
		'hundred' => array(
			'For German EEG remuneration and direct marketing, compare the installed PV capacity with the 100 kW threshold in § 21 EEG. Under § 13a EnWG, redispatch covers plants rated at least 100 kW and units the grid operator can control remotely.',
			'Für EEG-Vergütung und Direktvermarktung ist die installierte PV-Leistung an der 100-kW-Grenze des § 21 EEG maßgeblich. Redispatch nach § 13a EnWG erfasst Anlagen ab 100 kW Nennleistung sowie durch den Netzbetreiber jederzeit fernsteuerbare Anlagen.',
		),
		'etr'     => array(
			'For a German medium-voltage connection, assess the 135 kW boundary using active power, including existing generation at the connection. The certification route under VDE-AR-N 4110 and NELEV also depends on total installed capacity and agreed export power.',
			'Für den Anschluss an die Mittelspannung zählt an der 135-kW-Grenze die Wirkleistung einschließlich vorhandener Erzeugungsanlagen am Anschluss. Das Nachweisverfahren nach VDE-AR-N 4110 und NELEV richtet sich auch nach der installierten Gesamtleistung und der vereinbarten Einspeiseleistung.',
		),
	);

	/**
	 * Maximum apparent power of one listed unit feeding the grid.
	 *
	 * @param string $sku Woo product SKU.
	 * @param string $lang Page language.
	 */
	public static function badge( string $sku, string $lang ): string {
		if ( ! isset( self::MODELS[ $sku ] ) ) {
			return '';
		}
		$value = self::MODELS[ $sku ][1];
		return 'de' === $lang ? str_replace( '.', ',', $value ) . ' kVA maximal' : $value . ' kVA maximum';
	}

	/**
	 * The two published models in the page language.
	 *
	 * @param string $sku Current product SKU.
	 * @param string $lang Page language.
	 */
	public static function render( string $sku, string $lang ): string {
		$current = self::MODELS[ $sku ] ?? null;
		if ( null === $current ) {
			return '';
		}
		$id = (int) wc_get_product_id_by_sku( $current[4] );
		$id = $id && function_exists( 'pll_get_post' ) ? (int) pll_get_post( $id, $lang ) : $id;
		if ( ! $id || ! Publication::published_ids( array( $id ) ) ) {
			return '';
		}
		$url = get_permalink( $id );
		if ( ! $url ) {
			return '';
		}

		$de    = 'de' === $lang;
		$twin  = self::MODELS[ $current[4] ];
		$topic = $current[5];
		$limit = match ( $topic ) {
			'ten', 'thirty' => $de ? 'Ersatzstrom-Nennleistung' : 'Rated backup output',
			'h2', 'chs2'    => $de ? 'Ersatzstrom-Spitzenleistung' : 'Peak backup output',
			default         => $de ? 'Max. Lade- und Entladeleistung' : 'Maximum charge and discharge power',
		};
		$fit = match ( $topic ) {
			'ten'     => $de ? 'Abstand zu 10 kVA (Einzelgerät)' : 'Difference from 10 kVA (one unit)',
			'hundred' => $de ? 'AC-Nennwirkleistung' : 'Rated AC active power',
			'etr'     => $de ? 'Max. netzparallele Wirkleistung' : 'Maximum on-grid active power',
			default   => $de ? 'Abstand zu 30 kVA (Einzelgerät)' : 'Difference from 30 kVA (one unit)',
		};
		$rows = array(
			array( $de ? 'Max. Scheinleistung am Netz' : 'Maximum apparent power to grid', $current[1] . ' kVA', $twin[1] . ' kVA' ),
			array( $de ? 'Max. Netzstrom bei 400 V' : 'Maximum grid current at 400 V', $current[2] . ' A', $twin[2] . ' A' ),
			array( $limit, $current[3], $twin[3] ),
			array( $fit, $current[6], $twin[6] ),
		);
		$html = '<section class="lk-grid-threshold sf-container" aria-labelledby="lk-gt-heading"><p class="pdp-kicker">'
			. ( $de ? 'Modellvergleich' : 'Model comparison' ) . '</p><h2 id="lk-gt-heading" class="pdp-section-title">'
			. ( $de ? 'Netzanschluss-Schwellenwert im Vergleich' : 'Grid-Threshold Selection Note' ) . '</h2><p>' . esc_html( self::NOTES[ $topic ][ (int) $de ] )
			. '</p><div class="lk-grid-threshold-scroll"><table class="lk-grid-threshold-table"><thead><tr><th scope="col">'
			. ( $de ? 'Datenblattwert' : 'Datasheet rating' ) . '</th><th scope="col"><small>' . ( $de ? 'Dieses Modell' : 'Current model' ) . '</small>'
			. esc_html( $current[0] ) . '</th><th scope="col">' . esc_html( $twin[0] ) . '</th></tr></thead><tbody>';
		foreach ( $rows as list( $label, $a, $b ) ) {
			$html .= '<tr><th scope="row">' . esc_html( $label ) . '</th><td>' . esc_html( $de ? str_replace( '.', ',', $a ) : $a )
				. '</td><td>' . esc_html( $de ? str_replace( '.', ',', $b ) : $b ) . '</td></tr>';
		}
		$detail = $twin[0] . ' (' . self::badge( $current[4], $lang ) . ')';
		return $html . '</tbody></table></div><a class="lk-grid-threshold-link" href="' . esc_url( $url ) . '">'
			. esc_html( $de ? 'Mit ' . $detail . ' vergleichen' : 'Compare ' . $detail ) . ' →</a></section>';
	}
}
