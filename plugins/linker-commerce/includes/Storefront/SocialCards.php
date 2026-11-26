<?php
/**
 * Share artwork for the site's Open Graph and Twitter previews.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/** SEOPress renders Open Graph before Twitter in the same page head. */
final class SocialCards {

	public const ARTWORK = array(
		'default' => 'Linker Technology GmbH — Residential and C&I energy storage systems, Barleben, Germany',
		'blog'    => 'Linker Journal — Technical guidance on PV and energy storage sizing, pairing and commissioning by Chester John',
	);

	/** The Open Graph URL chosen for the current page head.
	 *
	 * @var string
	 */
	private string $image_url = '';

	/** Register the native SEOPress meta filters. */
	public function register(): void {
		add_filter( 'seopress_social_twitter_card_summary', array( $this, 'summary' ), 10, 0 );
		add_filter( 'seopress_social_og_thumb', array( $this, 'open_graph' ) );
		add_filter( 'seopress_social_twitter_card_thumb', array( $this, 'twitter_image' ) );
	}

	/** Always request a large Twitter/X preview. */
	public function summary(): string {
		return '<meta name="twitter:card" content="summary_large_image">';
	}

	/**
	 * Preserve a dedicated share image or choose the artwork for this surface.
	 *
	 * @param string $html Image meta tags, or a raw URL in SEOPress's image service.
	 */
	public function open_graph( string $html ): string {
		if ( '' !== $html && ! str_starts_with( ltrim( $html ), '<' ) ) {
			return $html;
		}
		if ( is_home() || is_category() ) {
			return $this->artwork( 'blog' );
		}

		$url       = self::meta_content( $html, 'og:image' );
		$dedicated = '' !== $url && ! str_contains( $url, '/linker-logo-full.png' ) && ! str_contains( $url, '/og-linker-default-1200x630.jpg' )
			&& ! str_ends_with( $url, '/linker-social/og-linker-default.jpg' );
		$story     = is_singular( 'post' );
		if ( $story || is_singular( 'product' ) ) {
			if ( ! $dedicated ) {
				// SEOPress's global default otherwise masks the post or product's own cover.
				$id  = (int) get_post_thumbnail_id( get_queried_object_id() );
				$src = $id ? wp_get_attachment_image_src( $id, 'full' ) : false;
				if ( $src ) {
					return $this->image_tags( $src[0], $src[1], $src[2], (string) get_post_meta( $id, '_wp_attachment_image_alt', true ) );
				}
				return $this->artwork( $story ? 'blog' : 'default' );
			}
		} else {
			$width  = (int) self::meta_content( $html, 'og:image:width' );
			$height = (int) self::meta_content( $html, 'og:image:height' );
			if ( ! $dedicated || $width < 1200 || $height < 1 || $width <= $height ) {
				return $this->artwork( 'default' );
			}
		}
		$this->image_url = $url;
		return $html;
	}

	/**
	 * Use the same preview as Open Graph.
	 *
	 * @param string $html Twitter tag, or a raw URL from SEOPress.
	 */
	public function twitter_image( string $html ): string {
		if ( '' === $this->image_url || ( '' !== $html && ! str_starts_with( ltrim( $html ), '<' ) ) ) {
			return $html;
		}
		return '<meta name="twitter:image" content="' . esc_url( $this->image_url ) . '">';
	}

	/**
	 * SEOPress emits a property and an escaped content attribute for each tag.
	 *
	 * @param string $html     Open Graph tags.
	 * @param string $property SEOPress property name.
	 */
	private static function meta_content( string $html, string $property ): string {
		return preg_match( '/<meta property="' . preg_quote( $property, '/' ) . '" content="([^"]*)"/', $html, $matches ) ? html_entity_decode( $matches[1], ENT_QUOTES | ENT_HTML5, 'UTF-8' ) : '';
	}

	/**
	 * Resolve the registered artwork, including the interval before media import.
	 *
	 * @param string $kind Site or journal artwork.
	 */
	private function artwork( string $kind ): string {
		$id  = (int) get_option( 'linker_social_' . $kind . '_og_attachment_id' );
		$url = $id ? wp_get_attachment_url( $id ) : false;
		if ( ! $url ) {
			$url = plugins_url( 'assets/social/og-linker-' . $kind . '-1200x630.jpg', dirname( __DIR__, 2 ) . '/linker-commerce.php' );
		}
		return $this->image_tags( $url, 1200, 630, self::ARTWORK[ $kind ] );
	}

	/**
	 * Build the image group from one source so URL, dimensions and alt match.
	 *
	 * @param string $url    Public image URL.
	 * @param int    $width  Actual pixel width.
	 * @param int    $height Actual pixel height.
	 * @param string $alt    Attachment or card description.
	 */
	private function image_tags( string $url, int $width, int $height, string $alt ): string {
		$this->image_url = $url;
		$tags            = array( '<meta property="og:image" content="' . esc_url( $url ) . '">' );
		if ( str_starts_with( $url, 'https://' ) ) {
			$tags[] = '<meta property="og:image:secure_url" content="' . esc_url( $url ) . '">';
		}
		$tags[] = '<meta property="og:image:width" content="' . $width . '">';
		$tags[] = '<meta property="og:image:height" content="' . $height . '">';
		if ( '' !== $alt ) {
			$tags[] = '<meta property="og:image:alt" content="' . esc_attr( $alt ) . '">';
		}
		return implode( "\n", $tags ) . "\n";
	}
}
