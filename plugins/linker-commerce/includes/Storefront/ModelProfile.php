<?php
/**
 * Model ratings used in selection tables and search previews.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Products\CompatibilityIndex;
use Linker\Commerce\Products\Materials;

/** Format one model's published facts without promoting missing values to ratings. */
final class ModelProfile {
	/**
	 * Format an authorized selection or figure value.
	 *
	 * @param mixed  $value Published value.
	 * @param string $unit Display unit.
	 */
	private static function value( mixed $value, string $unit = '' ): string {
		if ( ! is_scalar( $value ) || '' === $value || 'unknown' === $value ) {
			return '';
		}
		return trim( Materials::de_number( str_replace( '~', '–', (string) $value ) ) . ' ' . $unit );
	}

	/**
	 * Table and intro values. Keys serve as localized table headers.
	 *
	 * @param int                 $id Localized product ID.
	 * @param array<string,mixed> $r Published rating.
	 * @param array<string,mixed> $manifest Published documents and declarations.
	 * @return array<string,string>
	 */
	public static function cells( int $id, array $r, array $manifest ): array {
		$de      = Materials::is_de();
		$figures = $r['figures'];
		$voltage = $figures['battery_voltage_range_v']['value'] ?? $figures['system_operating_voltage_range_v']['value'] ?? null;
		$cells   = array(
			( $de ? 'AC-Nennleistung' : 'Rated AC output' ) => self::value( $r['ac_power_kw'], 'kW' ),
			( $de ? 'Max. PV-Leistung' : 'Max PV input' )  => self::value( $r['pv_input_kw'], 'kWp' ),
			( $de ? 'Phasen' : 'Phases' )                  => self::value( $r['phase'] ),
			'MPPT'                                         => self::value( $figures['n_mppt']['value'] ?? null ),
			( $de ? 'Nutzbare Energie' : 'Usable energy' ) => self::value( $r['usable_kwh'], 'kWh' ),
			( $de ? 'Nennenergie' : 'Nominal energy' )     => self::value( $r['nominal_kwh'], 'kWh' ),
			( $de ? 'Batteriespannung' : 'Battery voltage' ) => self::value( $voltage, 'V' ),
			( $de ? 'Schutzart' : 'Protection' )           => self::value( $figures['ip_rating']['value'] ?? null ),
		);
		$cells[ $de ? 'Modulspannung' : 'Module voltage' ] = self::value( $figures['module_voltage_range_v']['value'] ?? null, 'V' );
		$packs = $figures['modules_per_stack_min']['value'] ?? null;
		if ( is_numeric( $packs ) && ( $figures['modules_per_stack_max']['value'] ?? null ) === $packs ) {
			$cells[ $de ? 'Module je Stapel' : 'Modules per stack' ] = (string) $packs;
		}
		foreach ( array(
			'rated_current_a'  => array( $de ? 'Nennstrom' : 'Rated current', 'A' ),
			'max_current_a'    => array( $de ? 'Strombereich' : 'Current rating', '' ),
			'output_interface' => array( $de ? 'Schnittstelle' : 'Interface', '' ),
			'protocol'         => array( $de ? 'Protokoll' : 'Protocol', '' ),
			'power_supply'     => array( $de ? 'Versorgung' : 'Supply', '' ),
		) as $key => list( $label, $unit ) ) {
			$entry = $figures[ $key ] ?? array();
			$value = $de ? ( $entry['value_de'] ?? $entry['value'] ?? '' ) : ( $entry['value'] ?? '' );
			if ( 'max_current_a' === $key && is_numeric( $value ) ) {
				$unit = 'A';
			}
			$cells[ $label ] = self::value( $value, $unit );
		}
		if ( ! empty( $r['kwh_range'] ) ) {
			$cells[ $de ? 'Ausbaubereich' : 'System capacity range' ] = self::value( $r['kwh_range']['min'] . '–' . $r['kwh_range']['max'], 'kWh' );
		}
		$links = CompatibilityIndex::for_product( $id, $manifest );
		if ( $links['compatible'] ) {
			$is_battery = 'inverter' === $links['compatible'][0]['role'];
			$label      = $is_battery ? ( $de ? 'Passende Wechselrichter' : 'Matched inverters' ) : ( $de ? 'Passende Batterien' : 'Matched batteries' );
			if ( in_array( 'released_with_accessory', array_column( $links['compatible'], 'verdict' ), true ) ) {
				$label = $de ? 'Zuordnungen in der Matrix' : 'Pairings in the matrix';
			}
			$cells[ $label ] = (string) count( $links['compatible'] );
		}
		$sku   = (string) get_post_meta( $r['product_id'], '_sku', true );
		$badge = GridThresholdPairs::badge( $sku, Materials::locale() );
		if ( '' !== $badge ) {
			$cells[ $de ? 'AC-Grenzwert' : 'AC limit' ] = $badge;
		} elseif ( 'inverters' === $r['device_class'] ) {
			$standards = CompatibilityIndex::grid_standards( $r['product_id'], ( new ProductView() )->downloads( $id, $manifest ), $figures );
			if ( $standards ) {
				$cells[ $de ? 'Netznorm' : 'Grid standard' ] = $standards[0];
			}
		}
		$cells = array_filter( $cells, static fn( string $value ): bool => '' !== $value );
		if ( count( $cells ) < 4 ) {
			foreach ( ( new ProductView() )->spec_groups( $id ) as $group ) {
				foreach ( $group['rows'] as $row ) {
					$label = wp_strip_all_tags( $row['label'] );
					$value = trim( wp_strip_all_tags( $row['value'] . ' ' . $row['unit'] ) );
					if ( '' !== $label && '' !== $value && mb_strlen( $value ) <= 55 && ! in_array( $value, $cells, true ) && 0 !== strcasecmp( $value, $r['model'] ) && ! in_array( strtolower( $label ), array( 'model', 'modell', 'brand', 'marke', 'manufacturer', 'hersteller' ), true ) ) {
						$cells[ $label ] ??= $value;
					}
					if ( count( $cells ) >= 4 ) {
						break 2;
					}
				}
			}
		}
		return $cells;
	}

	/**
	 * Localized roles with full and compact ratings.
	 *
	 * @param array<string,mixed> $r Model rating.
	 * @return array{string,string}
	 */
	public static function roles( array $r ): array {
		$de     = Materials::is_de();
		$model  = $r['model'];
		$ac     = self::value( $r['ac_power_kw'], 'kW' );
		$energy = self::value( is_numeric( $r['nominal_kwh'] ) ? $r['nominal_kwh'] : $r['usable_kwh'], 'kWh' );
		$roles  = match ( $r['device_class'] ) {
			'inverters' => ( str_ends_with( $model, '-HT' ) ? array( 'String Inverter', 'Stringwechselrichter' ) : array( 'Hybrid Inverter', 'Hybridwechselrichter' ) ),
			'all-in-one-systems' => array( 'All-in-One ESS', 'Komplettspeicher' ),
			'battery-systems' => array( 'C&I Battery', 'Gewerbespeicher' ),
			'home-storage' => ( str_starts_with( $model, 'BC2-' ) ? array( 'Battery Controller', 'Batteriesteuerung' ) : array( 'LFP Battery', 'LFP-Speicher' ) ),
			'ev-chargers' => array( 'EV Charger', 'Wallbox' ),
			'ems-monitoring' => ( str_contains( $model, 'AIO3' ) ? array( 'Data Logger', 'Datenlogger' ) : array( 'Energy Manager', 'Energiemanager' ) ),
			'accessories' => ( preg_match( '/STS|ATS/i', $model ) ? array( 'Transfer Switch', 'Umschalteinheit' ) : array( 'Energy Meter', 'Energiezähler' ) ),
			default => array( 'System Component', 'Systemkomponente' ),
		};
		$compact = $roles[ (int) $de ];
		$rating  = match ( $r['device_class'] ) {
			'all-in-one-systems' => implode( ' / ', array_filter( array( $ac, $energy ) ) ),
			'home-storage', 'battery-systems' => $energy,
			default => $ac,
		};
		return array( trim( $rating . ' ' . $compact ), $compact );
	}

	/**
	 * Model-specific search summary from verified ratings and the localized Woo introduction.
	 *
	 * @param \WC_Product         $product Localized model.
	 * @param array<string,mixed> $r Published rating.
	 * @param int                 $pos Sorted series position.
	 * @param array<string,mixed> $manifest Authority snapshot.
	 */
	public static function summary( \WC_Product $product, array $r, int $pos, array $manifest ): string {
		$de        = Materials::is_de();
		$model     = $r['model'];
		$name      = str_starts_with( strtolower( $model ), strtolower( $r['brand'] ) ) ? $model : trim( $r['brand'] . ' ' . $model );
		$role      = self::roles( $r )[1];
		$ac        = self::value( $r['ac_power_kw'], 'kW' );
		$capacity  = self::value( $r['usable_kwh'], 'kWh' );
		$nominal   = self::value( $r['nominal_kwh'], 'kWh' );
		$pv        = self::value( $r['pv_input_kw'], 'kWp' );
		$phase     = is_int( $r['phase'] ) ? ( $de ? $r['phase'] . '-phasig' : $r['phase'] . '-phase' ) : '';
		$badge     = GridThresholdPairs::badge( $product->get_sku(), Materials::locale() );
		$figures   = $r['figures'];
		$mppt      = self::value( $figures['n_mppt']['value'] ?? null );
		$voltage   = self::value( $figures['battery_voltage_range_v']['value'] ?? $figures['system_operating_voltage_range_v']['value'] ?? null, 'V' );
		$ip        = self::value( $figures['ip_rating']['value'] ?? null );
		$sentences = array();

		if ( '' !== $badge ) {
			$frames = $de ? array(
				'%1$s am Netz. Für den %2$s sind %3$s PV-Leistung und %4$s MPP-Tracker angegeben.',
				'%1$s für die Netzeinspeisung. Der %2$s nimmt bis zu %3$s PV-Leistung an %4$s Trackern auf.',
				'%1$s am Netz. Auf der DC-Seite des %2$s stehen %4$s MPP-Tracker für bis zu %3$s PV-Leistung bereit.',
				'%1$s am AC-Ausgang des %2$s. Die PV-Seite ist auf %3$s an %4$s MPP-Trackern ausgelegt.',
				'%1$s am Netzanschluss des %2$s. Bis zu %3$s PV-Leistung verteilen sich auf %4$s MPP-Tracker.',
				'%1$s erreicht der %2$s auf der AC-Seite. Der PV-Generator darf bis zu %3$s leisten, verteilt auf %4$s MPP-Tracker.',
			) : array(
				'%1$s at the grid. The %2$s accepts up to %3$s of PV across %4$s trackers.',
				'%1$s grid export. The %2$s pairs a %3$s PV array limit with %4$s independent MPPT inputs.',
				'%1$s on the AC side of the %2$s. Its %4$s trackers can take up to %3$s from the PV array.',
				'%1$s at the AC terminals of the %2$s. Its %4$s MPPT channels handle a PV array of up to %3$s.',
				'%1$s at the grid terminals of the %2$s. Plan the PV strings for %4$s MPPT inputs and up to %3$s of array power.',
				'%1$s for grid export with the %2$s. A PV generator rated up to %3$s can feed its %4$s tracking channels.',
			);
			$slot   = $pos % 8;
			$lead   = $pv && $mppt ? sprintf( $frames[ $slot % count( $frames ) ], $badge, $name, $pv, $mppt ) : $badge . ' · ' . $name;
			$angles = array();

		} elseif ( str_contains( $model, '-STS-' ) && $ac && isset( $figures['rated_current_a']['value'], $figures['max_current_a']['value'] ) ) {
			$rated  = self::value( $figures['rated_current_a']['value'], 'A' );
			$max    = self::value( $figures['max_current_a']['value'], 'A' );
			$frames = $de ? array(
				'%1$s schaltet den Netz- und Ersatzstrompfad bei %2$s. Für die Auslegung der Umschalteinheit gelten %3$s Nennstrom und bis zu %4$s.',
				'Bei %1$s ist der Leistungspfad auf %2$s ausgelegt. Der Nennstrom beträgt %3$s. Netz- und Ersatzstromanschluss unterstützen bis zu %4$s.',
			) : array(
				'%1$s switches the backup path at %2$s. Allow for a rated current of %3$s when sizing the transfer circuit, with a maximum of %4$s.',
				'At %2$s, the %1$s carries %3$s nominal current. Its grid and backup connections support up to %4$s during a transfer.',
			);
			$lead   = sprintf( $frames[ $pos % 2 ], $name, $ac, $rated, $max );
			$angles = array();
		} elseif ( 'ev-chargers' === $r['device_class'] && in_array( $model, array( 'GW7K-HCA-20', 'GW11K-HCA-20', 'GW22K-HCA-20' ), true ) ) {
			$amps         = 11.0 === $r['ac_power_kw'] ? 16 : 32;
			$descriptions = $de ? array(
				'%s lädt einphasig mit %s bei %d A. Das feste Typ-2-Kabel reicht 7,5 m. Über SEMS lässt sich PV-Überschuss für das Fahrzeug nutzen.',
				'%s nutzt drei Phasen für %s bei %d A. Das 7,5 m lange Typ-2-Kabel bleibt an der Wallbox. SEMS unterstützt das Laden mit PV-Überschuss.',
				'%s: Die dreiphasige Wallbox liefert %s bei %d A. Für den Stellplatz stehen ein festes 7,5-m-Kabel mit Typ-2-Stecker und PV-Laden per SEMS bereit.',
			) : array(
				'%s delivers %s on one phase at %d A. Its fixed 7.5 m Type 2 cable reaches the parking space, and SEMS can route surplus PV to the vehicle.',
				'%s splits %s across three phases at %d A. A tethered 7.5 m Type 2 lead serves the charging bay with PV surplus control through SEMS.',
				'%s supplies %s at %d A on a three-phase circuit. Charge from surplus solar with SEMS and a fixed 7.5 m cable with an IEC Type 2 plug.',
			);
			$lead         = sprintf( $descriptions[ array_search( $model, array( 'GW7K-HCA-20', 'GW11K-HCA-20', 'GW22K-HCA-20' ), true ) ], $name, $ac, $amps );
			$angles       = array();
		} elseif ( 'all-in-one-systems' === $r['device_class'] && '' === $pv && $ac && $nominal ) {
			$lead   = $de ? sprintf( '%s verbindet %s AC-Leistung mit einer Nennenergie von %s im Speicherschrank.', $name, $ac, $nominal )
				: sprintf( '%s combines %s of AC output with %s of nominal storage capacity in one cabinet.', $name, $ac, $nominal );
			$angles = $de ? array( 'Die Einbindung erfolgt auf der AC-Seite.' ) : array( 'The cabinet connects on the AC side.' );
		} elseif ( in_array( $r['device_class'], array( 'inverters', 'all-in-one-systems' ), true ) && '' !== $ac ) {
			$leads  = $de ? array(
				'%1$s liefert %2$s AC-Nennleistung.',
				'Für eine AC-Leistung von %2$s steht der %1$s zur Wahl.',
				'%1$s eignet sich für einen Anschluss mit %2$s Nennleistung.',
				'%1$s ist die Variante mit %2$s AC-Nennleistung.',
				'%1$s erreicht im Netzbetrieb eine Nennleistung von %2$s.',
				'%2$s am AC-Ausgang bilden den Auslegungspunkt des %1$s.',
				'%1$s ist für %2$s AC im Dauerbetrieb ausgelegt.',
				'Bei der AC-Auslegung des %1$s gelten %2$s als Nennwert.',
				'Das Modell %1$s stellt auf der AC-Seite %2$s bereit.',
				'%2$s Nennleistung kennzeichnen den %1$s innerhalb der Baureihe.',
				'Der %1$s speist mit einer AC-Nennleistung von %2$s ein.',
				'%1$s: Die AC-Seite ist auf %2$s bemessen.',
			) : array(
				'%1$s supplies %2$s of rated AC output.',
				'Plan around %2$s on the AC side with the %1$s.',
				'%1$s is rated at %2$s for grid-connected operation.',
				'The %2$s power step in this range is the %1$s.',
				'%1$s delivers a nominal %2$s at the grid connection.',
				'For a design calling for %2$s AC, compare the %1$s.',
				'%1$s sets the AC design point at %2$s.',
				'The AC stage of the %1$s carries a %2$s nominal rating.',
				'Allow for %2$s at the output of the %1$s.',
				'%1$s provides the %2$s option for this installation.',
				'At a rated output of %2$s, the %1$s serves this power band.',
				'%1$s has a continuous AC rating of %2$s.',
			);
			$lead   = sprintf( $leads[ $pos % 12 ], $name, $ac );
			$angles = $de ? array( 'Vergleichen Sie die PV-Eingänge für die Stringplanung.', 'Die Leistungsstufe bestimmt die Auslegung auf der AC-Seite.', 'Für das Projekt zählt die verfügbare Leistung am Netzanschluss.', 'Die Tabelle zeigt die Leistungsstufen der Serie im Vergleich.' )
				: array( 'Compare the PV inputs for your string layout.', 'Use the output rating to size the AC side.', 'Match the power step to the grid connection.', 'The series table compares adjacent AC ratings.' );
		} elseif ( '' !== $capacity || '' !== $nominal ) {
			$energy = '' !== $capacity ? $capacity . ( $de ? ' nutzbar' : ' usable' ) : $nominal . ( ' nominal' );
			$leads  = $de ? array(
				'%1$s stellt %2$s bereit.',
				'Für die Speicherplanung mit %1$s gelten %2$s.',
				'Das Speichersystem %1$s bietet %2$s.',
				'Für den %1$s weist das Datenblatt %2$s aus.',
				'%2$s stehen mit dem Batteriespeicher %1$s zur Verfügung.',
				'Die Auslegung des %1$s basiert auf %2$s.',
				'%1$s erweitert die Auswahl um eine Speicherstufe mit %2$s.',
			) : array(
				'%1$s provides %2$s for the storage system.',
				'Plan a battery system around the %1$s with %2$s.',
				'The %1$s storage unit delivers %2$s.',
				'%1$s stores %2$s for subsequent discharge.',
				'With the %1$s, storage sizing starts at %2$s.',
				'Size the storage bank with %2$s from the %1$s.',
				'The %1$s brings %2$s to the battery installation.',
			);
			$lead   = sprintf( $leads[ $pos % 7 ], $name, $energy );
			$angles = $de ? array( 'Die nutzbare Energiemenge ist für die Lastdeckung entscheidend.', 'Vergleichen Sie die Speicherstufen bei gleichem Lastprofil.', 'Die Kapazität bestimmt die mögliche Versorgung über Nacht.', 'Prüfen Sie die Auslegung für den vorgesehenen Verbrauch.' )
				: array( 'Use the energy rating to plan load coverage.', 'Compare nearby capacities for the same load profile.', 'Match storage capacity to overnight consumption.', 'Use the model comparison to size the battery system.' );
		} else {
			$intro = trim( html_entity_decode( wp_strip_all_tags( $product->get_short_description() ), ENT_QUOTES | ENT_HTML5, 'UTF-8' ) );
			$parts = preg_split( '/(?<=[.!?])\s+(?=[\p{Lu}])/u', $intro );
			$first = $parts[0] ?? '';
			$lead  = $name . ' · ' . $role . '.';
			if ( '' !== $first && mb_strlen( $first ) <= 158 ) {
				$lead = $first;
			}
			foreach ( self::cells( $product->get_id(), $r, $manifest ) as $key => $value ) {
				if ( ! str_contains( strtolower( $lead ), strtolower( $value ) ) ) {
					$sentences[] = $key . ': ' . $value;
				}
			}
			foreach ( ( new ProductView() )->spec_groups( $product->get_id() ) as $group ) {
				foreach ( $group['rows'] as $row ) {
					$value = trim( wp_strip_all_tags( $row['value'] . ' ' . $row['unit'] ) );
					if ( '' !== $value && ! str_contains( strtolower( $lead ), strtolower( $value ) ) && mb_strlen( $row['label'] . $value ) <= 35 ) {
						$sentences[] = wp_strip_all_tags( $row['label'] ) . ': ' . $value;
					}
				}
			}

			$angles = $de ? array( 'Technische Angaben für den Systemanschluss.', 'Details für die Anlagenplanung vergleichen.', 'Schnittstellen für die Einbindung prüfen.', 'Passende Systeme und Einbaudaten prüfen.' )
				: array( 'Review the model connections for site planning.', 'Compare the details for system integration.', 'Check the interfaces for your installation.', 'Review equipment and mounting requirements.' );
		}
		if ( '' !== $badge || in_array( $r['device_class'], array( 'inverters', 'all-in-one-systems' ), true ) ) {
			$sentences[] = $pv && '' === $badge ? ( $de ? 'PV-Eingang bis ' . $pv : 'PV input up to ' . $pv ) : '';
			$sentences[] = $mppt && '' === $badge ? $mppt . ( $de ? ' MPP-Tracker' : ' MPPT trackers' ) : '';
			if ( $pv || $phase ) {
				if ( preg_match( '/-(?:EHA|ETA)-G20$/', $model ) ) {
					$role = $de ? 'ESA-Leistungsmodul' : 'ESA power module';
				}
				$sentences[] = $phase ? $role . ' · ' . $phase : $role;
			}
			$current = $figures['mppt_max_current_a']['value'] ?? null;
			if ( is_numeric( $current ) ) {
				$sentences[] = self::value( $current, 'A' ) . ( $de ? ' je MPP-Tracker' : ' per MPPT input' );
			}
			if ( is_numeric( $r['ac_power_kw'] ) && '' === $badge ) {
				$upper = match ( true ) {
					$r['ac_power_kw'] <= 6 => 6,
					$r['ac_power_kw'] <= 12 => 12,
					$r['ac_power_kw'] <= 25 => 25,
					$r['ac_power_kw'] <= 35 => 35,
					$r['ac_power_kw'] <= 85 => 85,
					default => 0,
				};
				$angles[] = $upper ? ( $de ? 'Auswahlklasse bis ' : 'Series tier up to ' ) . $upper . ' kW' : ( $de ? 'Leistungsklasse oberhalb von 85 kW' : 'Output class above 85 kW' );
			}
		}
		$sentences[] = $voltage ? ( $de ? 'Batteriebus ' : 'Battery bus ' ) . $voltage : '';
		$sentences[] = $nominal && ! str_contains( $lead, $nominal ) ? ( $de ? 'Nennenergie ' : 'Nominal capacity ' ) . $nominal : '';
		$sentences[] = isset( $figures['module_voltage_range_v']['value'] ) ? ( $de ? 'Modulspannung ' : 'Module voltage ' ) . self::value( $figures['module_voltage_range_v']['value'], 'V' ) : '';
		$sentences[] = $ip ? ( $de ? 'Schutzart ' : 'Enclosure rating ' ) . $ip : '';
		$modules     = $figures['modules_per_stack_min']['value'] ?? null;
		if ( is_numeric( $modules ) && ( $figures['modules_per_stack_max']['value'] ?? null ) === $modules ) {
			$sentences[] = $modules . ' ' . ( $de ? ( 1 === (int) $modules ? 'Modul je Stapel' : 'Module je Stapel' ) : ( 1 === (int) $modules ? 'module per stack' : 'modules per stack' ) );
		}
		$matches = CompatibilityIndex::for_product( $product->get_id(), $manifest )['compatible'];
		$count   = count( $matches );
		if ( in_array( 'released_with_accessory', array_column( $matches, 'verdict' ), true ) ) {
			$sentences[] = $count . ( $de ? ' Zuordnungen in der Matrix' : ' pairings listed in the matrix' );
		} elseif ( $count ) {
			$inverters   = 'inverter' === $matches[0]['role'];
			$sentences[] = $count . ' ' . ( $de
				? ( $inverters ? ( 1 === $count ? 'passender Wechselrichter' : 'passende Wechselrichter' ) : ( 1 === $count ? 'passende Batterie' : 'passende Batterien' ) )
				: ( $inverters ? ( 1 === $count ? 'matched inverter' : 'matched inverters' ) : ( 1 === $count ? 'matched battery' : 'matched batteries' ) ) );
		}
		$sentences = array_values( array_filter( $sentences ) );
		if ( $sentences ) {
			$offset    = $pos % count( $sentences );
			$sentences = array_merge( array_slice( $sentences, $offset ), array_slice( $sentences, 0, $offset ) );
		}
		$sentences = array_unique( $sentences );
		if ( $angles ) {
			$offset = $pos % count( $angles );
			array_push( $sentences, ...array_slice( $angles, $offset ), ...array_slice( $angles, 0, $offset ) );
		}
		if ( is_numeric( $r['usable_kwh'] ) ) {
			$limit = match ( true ) {
				$r['usable_kwh'] <= 6.5 => 6.5,
				$r['usable_kwh'] <= 12 => 12,
				$r['usable_kwh'] <= 26 => 26,
				$r['usable_kwh'] <= 110 => 110,
				default => 0,
			};
			$sentences[] = $limit ? ( $de ? 'Speicherklasse bis ' : 'Capacity band up to ' ) . Materials::de_number( (string) $limit ) . ' kWh' : ( $de ? 'Kapazitätsklasse über 110 kWh' : 'Capacity class above 110 kWh' );
		}
		$sentences[] = $de ? 'Details für die Auslegung.' : 'Model selection details.';
		return self::fit( $lead, $sentences );
	}

	/**
	 * Fit complete spec phrases, preferring a complete authored sentence when available.
	 *
	 * @param string   $lead Model introduction.
	 * @param string[] $phrases Ordered model facts and planning details.
	 */
	private static function fit( string $lead, array $phrases ): string {
		$lead = trim( (string) preg_replace( '/\s+/u', ' ', $lead ) );
		if ( mb_strlen( $lead ) > 157 ) {
			$lead = (string) preg_replace( '/\s+\S*$/u', '', mb_substr( $lead, 0, 158 ) );
			if ( strrpos( $lead, '(' ) > strrpos( $lead, ')' ) ) {
				$lead = substr( $lead, 0, (int) strrpos( $lead, '(' ) );
			}
		}
		$lead = rtrim( $lead, " \t\n\r\0\x0B.,;:-" );
		$lead = (string) preg_replace( '/[\s–—]+$/u', '', $lead ) . '.';
		foreach ( $phrases as $phrase ) {
			if ( mb_strlen( $lead ) >= 120 ) {
				break;
			}
			$sentence = rtrim( $phrase, '.' ) . '.';
			if ( mb_strlen( $lead . ' ' . $sentence ) <= 158 ) {
				$lead .= ' ' . $sentence;
			}
		}
		return $lead;
	}
}
