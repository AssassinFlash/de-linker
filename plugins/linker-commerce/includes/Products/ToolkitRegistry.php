<?php
/**
 * Bilingual engineering toolkit files and their public metadata.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Products;

use Linker\Commerce\Presentation\PageUrls;

/** Frozen bilingual editions grouped into four engineering tools. */
final class ToolkitRegistry {
	public const ROUTE_PREFIX = 'downloads/engineering-toolkit/';
	public const REVISION     = '2026-11';

	private const FILES = array(
		'linker-b2b-storage-inverter-comparison-2026-en.pdf' => array(
			'suite'       => 'comparison',
			'lang'        => 'en',
			'doc_code'    => 'DLK-REF-COMP-2026-11-EN',
			'unit_count'  => 4,
			'sha256'      => '45edccfcc550a00652d716b0b17000059c3d5bf681fc292187fa8e8237cf2ce4',
			'bytes'       => 1856569,
			'title'       => 'C&I & Residential Storage Comparison 2026',
			'description' => 'Side-by-side power, topology, STS backup switching, VDE 4105/4110, and CN 2026 / ADR matrix from 5 kW to 261 kWh.',
		),
		'linker-gewerbe-heimspeicher-vergleich-2026-de.pdf' => array(
			'suite'       => 'comparison',
			'lang'        => 'de',
			'doc_code'    => 'DLK-REF-COMP-2026-11-DE',
			'unit_count'  => 4,
			'sha256'      => 'c9b5761fe8fc06c8b0acf95333d4aedc23d3cb85d570baae4d1e2d7985bced8c',
			'bytes'       => 1860444,
			'title'       => 'Gewerbe- & Heimspeicher Vergleich 2026',
			'description' => 'Systematischer Leistungs-, Topologie-, STS-Ersatzstrom-, VDE-4105/4110- und CN-2026/ADR-Vergleich von 5 kW bis 261 kWh.',
		),
		'linker-inverter-battery-compatibility-list-2026-11-en.pdf' => array(
			'suite'       => 'compatibility',
			'lang'        => 'en',
			'doc_code'    => 'DLK-REF-COMPAT-2026-11-EN',
			'unit_count'  => 3,
			'sha256'      => 'a60abc4c091c9326ad2f8ec3e4ae72cc3c2d392345861d5682e136241dfb7fc9',
			'bytes'       => 362635,
			'title'       => 'Inverter × HV Battery Compatibility & ZEREZ List',
			'description' => 'Manufacturer-released pairings, mandatory meters/EMS, firmware notes, and ZEREZ-ID certificate audit.',
		),
		'linker-speicher-freigabeliste-kompatibilitaet-2026-11-de.pdf' => array(
			'suite'       => 'compatibility',
			'lang'        => 'de',
			'doc_code'    => 'DLK-REF-COMPAT-2026-11-DE',
			'unit_count'  => 3,
			'sha256'      => 'dcad7e2a35c3a41ebdd4881dd7d72c8221279f3cd7cd285a0df15348ac57080f',
			'bytes'       => 367300,
			'title'       => 'Wechselrichter × HV-Batterie Freigabeliste & ZEREZ',
			'description' => 'Herstellerfreigegebene Kombinationen, Pflicht-Zähler/EMS, Firmware-Hinweise und ZEREZ-ID-Zertifikatsprüfung.',
		),
		'linker-ci-storage-project-intake-sheet-en.pdf' => array(
			'suite'       => 'intake',
			'lang'        => 'en',
			'doc_code'    => 'DLK-FORM-CI-2026-11-EN',
			'unit_count'  => 2,
			'sha256'      => '4631d8ec3b9388c465275c6663f358ee4aa2d2a04b94c1cff6216293e8b5b0d7',
			'bytes'       => 326737,
			'title'       => 'C&I Storage Project Intake Sheet',
			'description' => 'Structured two-page field checklist for grid connection point, transformer, metering, peak shaving, and site logistics.',
		),
		'linker-projekterfassungsbogen-gewerbespeicher-de.pdf' => array(
			'suite'       => 'intake',
			'lang'        => 'de',
			'doc_code'    => 'DLK-FORM-CI-2026-11-DE',
			'unit_count'  => 2,
			'sha256'      => '2d61b49c0908fe0b122ccaff4c8290bcb205065d569b06a4d99f492b223581d3',
			'bytes'       => 334050,
			'title'       => 'Projekterfassungsbogen Gewerbespeicher',
			'description' => 'Strukturierte zweiseitige Checkliste für Netzanschlusspunkt, Transformator, Messkonzept, Peak Shaving und Aufstellungsort.',
		),
		'linker-load-profile-template-15min-en.csv'     => array(
			'suite'       => 'load-profile',
			'lang'        => 'en',
			'doc_code'    => '',
			'unit_count'  => 96,
			'sha256'      => 'ab90f6dd1d70da533780906d91cdfb01360a87a02fae05c37aa8700e3fe21d4b',
			'bytes'       => 5067,
			'title'       => '15-Minute Load Profile Template (CSV)',
			'description' => 'Ready-to-fill 15-minute RLM interval structure with 24-hour example and kWh-to-kW conversion notes.',
		),
		'linker-vorlage-lastgang-15min-de.csv'          => array(
			'suite'       => 'load-profile',
			'lang'        => 'de',
			'doc_code'    => '',
			'unit_count'  => 96,
			'sha256'      => '67fd9931c1890004c1cacf602ce7f587dafb59dc36e2a2abeec54b342314f29c',
			'bytes'       => 5226,
			'title'       => 'Vorlage 15-Minuten-Lastgang (CSV)',
			'description' => 'Excel-kompatible 15-Minuten-RLM-Vorlage (Semikolon, UTF-8 BOM) mit 24-Stunden-Beispiel und kWh-zu-kW-Hinweis.',
		),
	);

	/** All approved editions in suite order.
	 *
	 * @return list<array<string,mixed>>
	 */
	public static function all(): array {
		$items = array();
		foreach ( array_keys( self::FILES ) as $filename ) {
			$items[] = self::item( $filename );
		}
		return $items;
	}

	/** PDF editions included in the public document sitemap.
	 *
	 * @return list<array<string,mixed>>
	 */
	public static function pdfs(): array {
		return array_values( array_filter( self::all(), static fn( array $item ): bool => 'pdf' === $item['format'] ) );
	}

	/** Primary language download and its counterpart for each suite.
	 *
	 * @param string $lang Language of the download centre.
	 * @return list<array<string,mixed>>
	 */
	public static function cards_for_locale( string $lang ): array {
		$groups = array();
		foreach ( self::all() as $asset ) {
			$groups[ $asset['suite'] ][ $asset['lang'] ] = $asset;
		}
		$cards = array();
		foreach ( $groups as $editions ) {
			$primary = $editions[ 'de' === $lang ? 'de' : 'en' ];
			$alt     = $editions[ 'de' === $lang ? 'en' : 'de' ];
			$cards[] = $primary + array(
				'alt_url'      => $alt['url'],
				'alt_lang'     => $alt['lang'],
				'alt_filename' => $alt['filename'],
			);
		}
		return $cards;
	}

	/** Resolve an exact approved public filename.
	 *
	 * @param string $filename Requested basename.
	 * @return array<string,mixed>|null
	 */
	public static function find_by_filename( string $filename ): ?array {
		return isset( self::FILES[ $filename ] ) ? self::item( $filename ) : null;
	}

	/** Complete the edition record from the installed file and canonical site URL.
	 *
	 * @param string $filename Approved filename.
	 * @phpstan-param key-of<self::FILES> $filename
	 * @return array<string,mixed>
	 */
	private static function item( string $filename ): array {
		$edition = self::FILES[ $filename ];
		$path    = dirname( __DIR__, 2 ) . '/data/engineering-toolkit/' . $filename;
		$mtime   = is_file( $path ) ? filemtime( $path ) : false;
		$pdf     = str_ends_with( $filename, '.pdf' );
		return $edition + array(
			'filename'         => $filename,
			'path'             => $path,
			'url'              => PageUrls::root() . self::ROUTE_PREFIX . $filename,
			'lastmod'          => false !== $mtime ? gmdate( DATE_ATOM, $mtime ) : '2026-11-28T11:29:00+00:00',
			'format'           => $pdf ? 'pdf' : 'csv',
			'mime'             => $pdf ? 'application/pdf' : 'text/csv; charset=utf-8',
			'content_language' => 'de' === $edition['lang'] ? 'de-DE' : 'en',
			'revision'         => self::REVISION,
		);
	}
}
