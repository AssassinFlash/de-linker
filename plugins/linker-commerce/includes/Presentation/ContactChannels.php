<?php
/**
 * Public contact channels shared by the storefront, Genie and planner.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

/** The two public desks and their click-to-chat link. */
final class ContactChannels {
	public const OFFICIAL_YOUTUBE       = 'https://www.youtube.com/@linkerenergystorage';
	public const OFFICIAL_FACEBOOK      = 'https://www.facebook.com/profile.php?id=61596580037537';
	public const DIRECTORY_EUROPAGES    = 'https://www.europages.de/de/firma/linker-technology-gmbh-22436516';
	public const DIRECTORY_WLW          = 'https://www.wlw.de/de/firma/linker-technology-gmbh-22436518';
	public const DIRECTORY_PROVENEXPERT = 'https://www.provenexpert.com/de-de/linker-technology-gmbh/';
	public const DIRECTORY_MARKTPLATZ   = 'https://www.marktplatz-mittelstand.de/barleben/linker-technology-gmbh-aYGE9H.html';
	public const DIRECTORY_TRUSTPILOT   = 'https://de.trustpilot.com/review/de-linker.com';
	public const DIRECTORY_NORTHDATA    = 'https://www.northdata.de/Linker%20Technology%20GmbH,%20Barleben/Amtsgericht%20Stendal%20HRB%2033824';
	public const DIRECTORY_11880        = 'https://www.11880.com/branchenbuch/barleben/250424085B114309018/linker-technology-gmbh.html';
	public const DIRECTORY_HOTFROG      = 'https://www.hotfrog.de/company/AaIcwgYnceK8KVPjsAyONQ/linker-technology-gmbh/barleben/electrical-supplies-services';
	public const CHESTER_LINKEDIN       = 'https://www.linkedin.com/in/johnchestersr/';
	public const CHESTER_YOUTUBE        = 'https://www.youtube.com/@chesterjohn.linker';
	public const CHESTER_X              = 'https://x.com/chester_linker';
	public const CHESTER_FACEBOOK       = 'https://www.facebook.com/chesterjohn.linker/';
	public const CHESTER_INSTAGRAM      = 'https://www.instagram.com/chesterjohn.linker/';
	public const CHESTER_TIKTOK         = 'https://www.tiktok.com/@chesterjohn.linker';

	public const DIRECT_EMAIL  = 'chester@de-linker.com';
	public const GERMANY_PHONE = '+49 174 4276991';
	public const DIRECT_PHONE  = '+86 133 1289 2178';
	public const WHATSAPP_BASE = 'https://wa.me/8613312892178';

	/**
	 * Official profiles for the company and publisher.
	 *
	 * @return list<string>
	 */
	public static function company_same_as(): array {
		return array(
			self::OFFICIAL_YOUTUBE,
			self::OFFICIAL_FACEBOOK,
			self::DIRECTORY_EUROPAGES,
			self::DIRECTORY_WLW,
			self::DIRECTORY_PROVENEXPERT,
			self::DIRECTORY_MARKTPLATZ,
			self::DIRECTORY_TRUSTPILOT,
			self::DIRECTORY_NORTHDATA,
			self::DIRECTORY_11880,
			self::DIRECTORY_HOTFROG,
		);
	}

	/**
	 * Verified profiles belonging to Chester John.
	 *
	 * @return list<string>
	 */
	public static function chester_same_as(): array {
		return array( self::CHESTER_LINKEDIN, self::CHESTER_YOUTUBE, self::CHESTER_X, self::CHESTER_FACEBOOK, self::CHESTER_INSTAGRAM, self::CHESTER_TIKTOK );
	}

	/**
	 * Social profile links used by public templates.
	 *
	 * @param array<string,string>|string $attributes Shortcode attributes.
	 */
	public static function social_shortcode( $attributes ): string {
		return self::social_links( $attributes['scope'] ?? 'company', $attributes['class'] ?? '' );
	}

	/**
	 * The public channels presented together for one identity.
	 *
	 * @param string $scope Company or Chester.
	 * @param string $classes Layout class supplied by the calling template.
	 */
	public static function social_links( string $scope = 'company', string $classes = '' ): string {
		$links = match ( $scope ) {
			'company' => array(
				'youtube'  => array( self::OFFICIAL_YOUTUBE, __( 'Linker Energy Storage on YouTube', 'linker-commerce' ) ),
				'facebook' => array( self::OFFICIAL_FACEBOOK, __( 'Linker Energy Storage on Facebook', 'linker-commerce' ) ),
			),
			'chester' => array(
				'linkedin' => array( self::CHESTER_LINKEDIN, __( 'Chester John on LinkedIn', 'linker-commerce' ) ),
				'youtube'  => array( self::CHESTER_YOUTUBE, __( 'Chester John on YouTube', 'linker-commerce' ) ),
				'x'        => array( self::CHESTER_X, __( 'Chester John on X', 'linker-commerce' ) ),
			),
			default => array(),
		};
		if ( ! $links ) {
			return '';
		}
		$html = '<div class="' . esc_attr( $classes ) . '">';
		foreach ( $links as $network => list( $url, $label ) ) {
			$html .= '<a href="' . esc_url( $url ) . '" target="_blank" rel="noopener noreferrer" aria-label="' . esc_attr( $label ) . '" title="' . esc_attr( $label ) . '">' . self::social_icon( $network ) . '</a>';
		}
		return $html . '</div>';
	}

	/**
	 * Brand glyph for a social channel or an article share action.
	 *
	 * @param 'youtube'|'facebook'|'linkedin'|'x' $network Social network.
	 * @param int                                 $size Icon width and height in pixels.
	 */
	public static function social_icon( string $network, int $size = 18 ): string {
		list( $view, $path ) = match ( $network ) {
			'youtube' => array( '0 0 24 24', 'M23.5 6.2a3 3 0 0 0-2.1-2.1C19.5 3.6 12 3.6 12 3.6s-7.5 0-9.4.5A3 3 0 0 0 .5 6.2 31 31 0 0 0 0 12a31 31 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.9.5 9.4.5 9.4.5s7.5 0 9.4-.5a3 3 0 0 0 2.1-2.1A31 31 0 0 0 24 12a31 31 0 0 0-.5-5.8ZM9.6 15.6V8.4l6.3 3.6-6.3 3.6Z' ),
			'facebook' => array( '0 0 320 512', 'M279.14 288l14.22-92.66h-88.91v-60.13c0-25.35 12.42-50.06 52.24-50.06h40.42V6.26S260.43 0 225.36 0c-73.22 0-121.08 44.38-121.08 124.72v70.62H22.89V288h81.39v224h100.17V288z' ),
			'linkedin' => array( '0 0 448 512', 'M100.28 448H7.4V148.9h92.88zM53.79 108.1C24.09 108.1 0 83.5 0 53.8a53.79 53.79 0 0 1 107.58 0c0 29.7-24.1 54.3-53.79 54.3zM447.9 448h-92.68V302.4c0-34.7-.7-79.2-48.29-79.2-48.29 0-55.69 37.7-55.69 76.7V448h-92.78V148.9h89.08v40.8h1.3c12.4-23.5 42.69-48.3 87.88-48.3 94 0 111.28 61.9 111.28 142.3V448z' ),
			'x' => array( '0 0 24 24', 'M18.9 2H22l-6.8 7.8L23.2 22h-6.3L12 14.5 5.4 22H2.2l8.3-9.5L2.7 2h6.4l4.5 6.7L18.9 2Zm-1.1 18h1.7L8.1 3.9H6.3L17.8 20Z' ),
		};
		return '<svg aria-hidden="true" focusable="false" width="' . $size . '" height="' . $size . '" viewBox="' . $view . '" fill="currentColor"><path d="' . $path . '"/></svg>';
	}

	/**
	 * Display or dial value for LiveCanvas contact rows.
	 *
	 * @param array<string,string>|string $attributes Shortcode attributes.
	 */
	public static function value( $attributes ): string {
		return match ( $attributes['channel'] ?? '' ) {
			'direct_email'  => self::DIRECT_EMAIL,
			'germany_phone' => self::GERMANY_PHONE,
			'direct_phone'  => self::DIRECT_PHONE,
			'germany_tel'   => str_replace( ' ', '', self::GERMANY_PHONE ),
			'direct_tel'    => str_replace( ' ', '', self::DIRECT_PHONE ),
			default         => '',
		};
	}

	/** Localized, editable message shown by WhatsApp when the customer opens it. */
	public static function message(): string {
		return __( 'Hello Linker team, I would like to discuss a solar storage inquiry.', 'linker-commerce' );
	}

	/**
	 * Public chat URL with a localized message.
	 *
	 * @param string $message Product or project message, or the general greeting.
	 */
	public static function url( string $message = '' ): string {
		return self::WHATSAPP_BASE . '?text=' . rawurlencode( '' === $message ? self::message() : $message );
	}

	/**
	 * Secondary link for a page or tool row.
	 *
	 * @param string $label   Visible label.
	 * @param string $message Contextual prefill.
	 * @param string $classes   Surface-specific styling.
	 */
	public static function link( string $label = 'WhatsApp', string $message = '', string $classes = '' ): string {
		return '<a class="' . esc_attr( trim( 'linker-whatsapp ' . $classes ) ) . '" href="' . esc_url( self::url( $message ) )
			. '" target="_blank" rel="noopener noreferrer"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20.7 11.6a8.8 8.8 0 0 1-13.1 7.7L3 20.6l1.3-4.4a8.8 8.8 0 1 1 16.4-4.6Z"/><path d="m8.9 7.5 1.1 2.3-.8 1.2a8.5 8.5 0 0 0 3.8 3.5l1.1-1.3 2.4 1.2c-.2 1.4-1 2.1-2.3 2-3.6-.5-7.2-4.1-7.4-7.2 0-1.1.7-1.8 2.1-1.7Z"/></svg>'
			. esc_html( $label ) . '</a>';
	}

	/**
	 * Page-authored contact link.
	 *
	 * @param array<string,string>|string $attributes Shortcode attributes.
	 */
	public static function shortcode( $attributes ): string {
		return self::link( classes: 'outline' === ( $attributes['style'] ?? '' ) ? 'linker-whatsapp-outline' : '' );
	}
}
