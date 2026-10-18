<?php
/**
 * Reviewed German route vocabulary for the owner's German-address ruling.
 *
 * @package Linker\I18n
 */

declare( strict_types = 1 );

namespace Linker\I18n;

/** German descriptions change; manufacturer names, models and figures remain. */
final class GermanSlugs {

	/** Exact page and term changes approved in ticket #254. */
	private const EXACT = array(
		'warenkorb'                                     => 'loesungsentwurf',
		'faq-download'                                  => 'faq-dokumente',
		'compare-products'                              => 'produkte-vergleichen',
		'service-support'                               => 'kundendienst',
		'system-design'                                 => 'systemauslegung',
		'battery-storage-blog'                          => 'batteriespeicher',
		'installation-commissioning'                    => 'installation-inbetriebnahme',
		'monitoring-energy-management'                  => 'ueberwachung-energiemanagement',
		'applications-blog'                             => 'anwendungen',
		'all-in-one-systeme'                            => 'komplettsysteme',
		'ems-monitoring'                                => 'ems-ueberwachung',
		'gateway-zaehler-cloud-ueberwachung-datenebene' => 'kommunikationsschnittstelle-zaehler-fernueberwachung-datenebene',
	);

	/** Descriptive phrases found by the live audit; longest phrases come first. */
	private const PHRASES = array(
		'battery-stack-bridge'         => 'verbinder-fuer-batteriestapel',
		'lfp-battery-base'             => 'lfp-batteriesockel',
		'three-phase-hybrid-inverter'  => 'dreiphasiger-hybridwechselrichter',
		'single-phase-hybrid-inverter' => 'einphasiger-hybridwechselrichter',
		'three-phase-all-in-one'       => 'dreiphasiges-komplettsystem',
		'three-phase-power-module'     => 'dreiphasiges-leistungsmodul',
		'single-phase-power-module'    => 'einphasiges-leistungsmodul',
		'three-phase-ev-charger'       => 'dreiphasige-ladestation',
		'single-phase-ev-charger'      => 'einphasige-ladestation',
		'three-phase-hybrid'           => 'dreiphasiger-hybridwechselrichter',
		'single-phase-hybrid'          => 'einphasiger-hybridwechselrichter',
		'smart-energy-controller'      => 'intelligente-energiesteuerung',
		'residential-energy-manager'   => 'heim-energiemanager',
		'data-collector'               => 'datensammler',
		'battery-module'               => 'batteriemodul',
		'ev-charger'                   => 'ladestation',
		'battery'                      => 'batterie',
		'flagship'                     => 'spitzenmodell',
		'gateway'                      => 'kommunikationsschnittstelle',
	);

	/**
	 * Translates a stored descriptive slug, leaving model-only slugs alone.
	 *
	 * @param string $slug Current slug.
	 */
	public static function translated( string $slug ): string {
		return self::EXACT[ $slug ] ?? strtr( $slug, self::PHRASES );
	}

	/**
	 * Creates a new address from German copy using German ASCII transliteration.
	 *
	 * @param string $title German title.
	 */
	public static function from_title( string $title ): string {
		return sanitize_title(
			strtr(
				$title,
				array(
					'ä' => 'ae',
					'ö' => 'oe',
					'ü' => 'ue',
					'Ä' => 'Ae',
					'Ö' => 'Oe',
					'Ü' => 'Ue',
					'ß' => 'ss',
				)
			)
		);
	}
}
