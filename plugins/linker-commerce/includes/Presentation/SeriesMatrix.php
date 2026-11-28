<?php
/**
 * Server-rendered series comparisons.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;
use Linker\Commerce\Storefront\GridThresholdPairs;
use Linker\Commerce\Storefront\ModelProfile;
use Linker\Commerce\Storefront\ProductGroupIndex;

/** Product details and archive navigation use the same series roster as JSON-LD. */
final class SeriesMatrix {
	/**
	 * Compare every model in the displayed series.
	 *
	 * @param int $id Current model.
	 */
	public static function product( int $id ): string {
		$index   = ProductGroupIndex::current();
		$members = $index->members_for( $id );
		if ( count( $members ) < 2 ) {
			return '';
		}
		$rows    = array();
		$columns = array();
		foreach ( $members as $member ) {
			$rating          = $index->rating( $member );
			$cells           = ModelProfile::cells( $member, $rating, CompatibilityIndex::manifest() );
			$columns        += $cells;
			$rows[ $member ] = $cells;
		}
		$de   = Materials::is_de();
		$html = '';
		foreach ( $rows as $member => $cells ) {
			$current = $member === $id;
			$model   = esc_html( $index->rating( $member )['model'] );
			$html   .= '<tr' . ( $current ? ' class="is-current" aria-current="page"' : '' ) . '><th scope="row">' . ( $current ? $model : '<a href="' . esc_url( (string) get_permalink( $member ) ) . '">' . $model . '</a>' ) . '</th>';
			foreach ( array_keys( $columns ) as $column ) {
				$html .= '<td>' . esc_html( $cells[ $column ] ?? '—' ) . '</td>';
			}
			$html .= '</tr>';
		}
		return self::table( $de ? 'Modelle dieser Serie im Vergleich' : 'Compare models in this series', array_merge( array( $de ? 'Modell' : 'Model' ), array_keys( $columns ) ), $html );
	}

	/** Series and representative models in the current term archive. */
	public static function archive(): string {
		$groups = ProductGroupIndex::archive_groups();
		if ( ! $groups ) {
			return '';
		}
		$index = ProductGroupIndex::current();
		$de    = Materials::is_de();
		$html  = '';
		foreach ( $groups as $group ) {
			$members = $index->members_for( $group );
			$ranges  = array();
			$phases  = array();
			$voltage = array();
			$links   = array();
			foreach ( $members as $pos => $id ) {
				$r = $index->rating( $id );
				foreach ( array(
					'ac_power_kw' => 'kW',
					'nominal_kwh' => 'kWh',
				) as $key => $unit ) {
					if ( is_numeric( $r[ $key ] ) ) {
						$ranges[ $unit ][] = $r[ $key ];
					}
				}
				if ( is_int( $r['phase'] ) ) {
					$phases[ $r['phase'] ] = $r['phase'] . ( $de ? '-phasig' : '-phase' );
				}
				$band = $r['figures']['battery_voltage_range_v']['value'] ?? $r['figures']['system_operating_voltage_range_v']['value'] ?? null;
				if ( is_scalar( $band ) && '' !== (string) $band ) {
					$voltage[ (string) $band ] = Materials::de_number( str_replace( '~', '–', (string) $band ) ) . ' V';
				}
				if ( 0 === $pos || '' !== GridThresholdPairs::badge( (string) get_post_meta( $r['product_id'], '_sku', true ), Materials::locale() ) ) {
					$links[] = '<a href="' . esc_url( (string) get_permalink( $id ) ) . '">' . esc_html( $r['model'] ) . '</a>';
				}
			}
			$span = array();
			foreach ( $ranges as $unit => $values ) {
				$span[] = Materials::de_number( implode( '–', array_unique( array( min( $values ), max( $values ) ) ) ) ) . ' ' . $unit;
			}
			$html .= '<tr><th scope="row">' . esc_html( $index->rating( $group )['series'] ) . '</th><td>' . count( $members ) . '</td><td>' . esc_html( $span || $phases || $voltage ? implode( ' · ', array_merge( $span, array_values( $phases ), array_values( $voltage ) ) ) : '—' ) . '</td><td>' . implode( ', ', $links ) . '</td></tr>';
		}
		return self::table( $de ? 'Modellserien im Vergleich' : 'Compare model series', $de ? array( 'Serie', 'Anzahl', 'Auslegung', 'Modelle' ) : array( 'Series', 'Count', 'Ratings', 'Models' ), $html );
	}

	/**
	 * Render a scrollable table with accessible headings.
	 *
	 * @param string   $title Section title.
	 * @param string[] $labels Column headings.
	 * @param string   $rows Escaped table rows.
	 */
	private static function table( string $title, array $labels, string $rows ): string {
		$html = '<section class="lk-series-matrix pdp-block sf-container"><h2 class="pdp-section-title">' . esc_html( $title ) . '</h2><div class="lk-series-matrix-scroll" tabindex="0" role="region" aria-label="' . esc_attr( $title ) . '"><table class="lk-series-matrix-table"><thead><tr>';
		foreach ( $labels as $label ) {
			$html .= '<th scope="col">' . esc_html( $label ) . '</th>';
		}
		return $html . '</tr></thead><tbody>' . $rows . '</tbody></table></div></section>';
	}

	/**
	 * Highlight the displayed model’s key selection facts.
	 *
	 * @param int $id Displayed product.
	 */
	public static function intro( int $id ): string {
		$index  = ProductGroupIndex::current();
		$rating = $index->rating( $id );
		if ( ! $rating ) {
			return '';
		}
		$cells = ModelProfile::cells( $id, $rating, CompatibilityIndex::manifest() );
		if ( ! $cells ) {
			return '';
		}
		$de   = Materials::is_de();
		$keys = $de ? array( 'AC-Grenzwert', 'AC-Nennleistung', 'Max. PV-Leistung', 'Nutzbare Energie', 'Nennenergie', 'MPPT', 'Batteriespannung', 'Passende Wechselrichter', 'Passende Batterien', 'Netznorm' ) : array( 'AC limit', 'Rated AC output', 'Max PV input', 'Usable energy', 'Nominal energy', 'MPPT', 'Battery voltage', 'Matched inverters', 'Matched batteries', 'Grid standard' );
		if ( in_array( $rating['device_class'], array( 'home-storage', 'battery-systems' ), true ) ) {
			$members  = $index->members_for( $id );
			$position = array_search( $id, $members, true );
			$label    = $de ? 'Position in der Serie' : 'Position in series';
			if ( false !== $position && count( $members ) > 1 ) {
				$cells[ $label ] = sprintf( $de ? '%1$d von %2$d · %3$s' : '%1$d of %2$d · %3$s', $position + 1, count( $members ), $rating['series'] );
			}
			$keys = $de
				? array( 'Nutzbare Energie', 'Batteriespannung', 'Schutzart', 'Passende Wechselrichter', 'Zuordnungen in der Matrix', $label, 'Nennenergie' )
				: array( 'Usable energy', 'Battery voltage', 'Protection', 'Matched inverters', 'Pairings in the matrix', $label, 'Nominal energy' );
		}
		$html = '<dl class="pdp-intro-facts" aria-label="' . ( $de ? 'Modell-Eckdaten' : 'Key model figures' ) . '">';
		foreach ( array_slice( array_intersect_key( array_flip( $keys ), $cells ) + $cells, 0, 5, true ) as $key => $_ ) {
			$html .= '<div class="pdp-intro-fact"><dt>' . esc_html( $key ) . '</dt><dd>' . esc_html( $cells[ $key ] ) . '</dd></div>';
		}
		return $html . '</dl>';
	}
}
