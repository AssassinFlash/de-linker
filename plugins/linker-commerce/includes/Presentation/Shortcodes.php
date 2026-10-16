<?php
/**
 * Shortcodes that feed LiveCanvas templates with B2B data.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Products\Faqs;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Settings\Options;
use WC_Product;

/**
 * The empty Proforma-request gate, the contact band and its link, the product
 * FAQ rows and the site's own origin: the shortcodes the exported LiveCanvas
 * templates consume. The B2B price gate is not a shortcode — prices are hidden
 * at their source (Gating\PriceDisplay).
 */
final class Shortcodes {

	/**
	 * Sets up the shortcodes.
	 *
	 * @param LoginGate $gate     The empty Proforma-request page.
	 * @param Approval  $approval The account approval rule.
	 */
	public function __construct( private readonly LoginGate $gate, private readonly Approval $approval = new Approval() ) {}

	/**
	 * Registers the shortcodes.
	 */
	public function register(): void {
		add_shortcode( 'linker_checkout', array( $this, 'checkout' ) );
		add_shortcode( 'linker_draft_empty', array( $this, 'draft_empty' ) );
		add_shortcode( 'linker_faqs', array( $this, 'faqs' ) );
		add_shortcode( 'linker_contact_link', array( $this, 'contact_link' ) );
		add_shortcode( 'linker_contact_invitation', array( $this, 'contact_invitation' ) );
		add_shortcode( 'linker_site_url', array( $this, 'site_url' ) );
		// The cart template's [lc_if] conditions are the global functions in
		// template-functions.php (linker_commerce_draft_empty/_filled):
		// LiveCanvas resolves a condition with function_exists(), never a
		// filter under the condition's name.
	}

	/**
	 * The contact page in the page's language; every contact entry (the site
	 * chrome's, the product list's invitation) resolves its target here.
	 */
	public static function contact_page_url(): string {
		$translated = PageUrls::translated( 'contact' );
		return '' === $translated ? (string) home_url( '/contact/' ) : $translated;
	}

	/**
	 * The site chrome's contact entry: the contact page in the page's
	 * language, carrying the product on display as the request's subject.
	 * Placement selects the chrome's own class (header, mobile header,
	 * footer).
	 *
	 * The site chrome prints the default words. The blog templates call the
	 * same shortcode for their own contact button and pass the words the live
	 * band carries: `label` for English, `label_de` for German — the pair is
	 * how one template that both languages render (the search face's) reaches
	 * both. A call that passes no label keeps the chrome's default, so the
	 * header and footer partials are unaffected.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function contact_link( $atts = array() ): string {
		$attributes = shortcode_atts(
			array(
				'placement' => 'header',
				'class'     => '',
				'label'     => '',
				'label_de'  => '',
			),
			(array) $atts
		);
		$classes    = '' !== trim( (string) $attributes['class'] )
			? trim( (string) $attributes['class'] )
			: ( 'mobile' === $attributes['placement'] ? 'tv-header-cta tv-mobile-cta' : 'tv-header-cta' );
		$url        = self::contact_page_url();
		if ( function_exists( 'is_product' ) && is_product() ) {
			$product = wc_get_product( (int) get_the_ID() );
			if ( $product instanceof WC_Product ) {
				$url = (string) add_query_arg(
					array(
						'intent'     => 'product',
						'kind'       => 'product',
						'title'      => rawurlencode( $product->get_name() ),
						'source_id'  => $product->get_id(),
						'product_id' => $product->get_id(),
						'source'     => $product->get_permalink(),
					),
					$url
				);
			}
		}
		return '<a class="' . esc_attr( $classes ) . '" href="' . esc_url( $url ) . '">' . esc_html( self::contact_link_label( (string) $attributes['label'], (string) $attributes['label_de'] ) ) . '</a>';
	}

	/**
	 * A contact link's words: the German label on a German page, the English
	 * one otherwise, the chrome's default when the call passes neither.
	 *
	 * The attributes arrive as the stored template wrote them; LiveCanvas
	 * renders the template's HTML through wptexturize, so an arrow reaches
	 * this method as `&rarr;` and is decoded before it is printed.
	 *
	 * @param string $label    The English label, empty when the call has none.
	 * @param string $label_de The German label, empty when the call has none.
	 */
	private static function contact_link_label( string $label, string $label_de ): string {
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$chosen = trim( $german ? $label_de : $label );
		if ( '' === $chosen ) {
			// A call that passes only one of the two words still speaks: the
			// one it passed.
			$chosen = '' !== trim( $label ) ? trim( $label ) : trim( $label_de );
		}
		if ( '' === $chosen ) {
			return (string) __( 'Contact Linker', 'linker-commerce' );
		}
		return html_entity_decode( $chosen, ENT_QUOTES, 'UTF-8' );
	}

	/**
	 * The designed contact band the marketing pages and the article template
	 * print as `[linker_contact_invitation surface="…"]`.
	 *
	 * The words are the live band's, read off the old live pages (utility
	 * solution, EPC, the EPC intake, services, article; EN and DE,
	 * 2026-10-12/13 captures). An unknown surface prints nothing: it must
	 * not borrow another surface's words. Four of the five surfaces get
	 * their shape from the page's own rule (the intake's sits on
	 * `.lk-bottom-cta`); the article surface has no page rule, so its shape
	 * is in the band's stylesheet. The markup carries no shape class beyond
	 * the surface. Styles stay in WindPress
	 * (content/windpress/contact-invitation.css).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function contact_invitation( $atts = array() ): string {
		$attributes = shortcode_atts(
			array(
				'surface' => '',
			),
			(array) $atts,
			'linker_contact_invitation'
		);
		// Decode before sanitize_html_class. An unregistered tag is
		// wptexturized to &#8221; (current /services-support/ and
		// /solution/utility-storage/ HTML, 2026-10-14). A stored entity is
		// not a quote to shortcode_parse_atts, so the value arrives as
		// &#8221;services&#8221; and sanitizes to 8221services8221, which
		// matches no surface and prints no band. WordPress's own
		// shortcode_parse_atts / sanitize_html_class.
		$surface = html_entity_decode( (string) $attributes['surface'], ENT_QUOTES, 'UTF-8' );
		$surface = trim( $surface, "\"\'\xE2\x80\x9C\xE2\x80\x9D" );
		$surface = sanitize_html_class( $surface );
		$copy    = self::invitation_copy();
		if ( ! isset( $copy[ $surface ] ) ) {
			return '';
		}
		$row     = $copy[ $surface ];
		$intent  = self::invitation_intent( $surface );
		$email   = ( new Options() )->team_to();
		$context = $this->invitation_context( $intent );
		$url     = (string) add_query_arg(
			array(
				'intent'    => $intent,
				'kind'      => (string) $context['kind'],
				'title'     => (string) $context['title'],
				'source'    => (string) $context['url'],
				'source_id' => (int) $context['source_id'],
			),
			self::contact_page_url()
		);
		$classes = 'linker-contact-invitation linker-contact-' . $surface;

		$html  = '<section class="' . esc_attr( $classes ) . '">';
		$html .= '<div>';
		if ( '' !== $row['eyebrow'] ) {
			$html .= '<span class="linker-contact-eyebrow">' . esc_html( $row['eyebrow'] ) . '</span>';
		}
		$html .= '<h2>' . esc_html( $row['heading'] ) . '</h2>';
		$html .= '<p>' . esc_html( $row['note'] ) . '</p>';
		$html .= '</div>';
		$html .= '<div class="linker-contact-invitation-actions">';
		$html .= '<a class="linker-contact-primary" href="' . esc_url( $url ) . '" data-linker-contact="' . esc_attr( (string) wp_json_encode( $context ) ) . '">' . esc_html( $row['button'] ) . '</a>';
		$html .= '<a class="linker-contact-email" href="mailto:' . esc_attr( $email ) . '">' . esc_html( $email ) . '</a>';
		$html .= '</div>';
		return $html . '</section>';
	}

	/**
	 * Which request the band opens. The article band is about the product
	 * the piece discusses; the others are about the project on the page.
	 *
	 * @param string $surface A known surface.
	 */
	private static function invitation_intent( string $surface ): string {
		return 'article' === $surface ? 'product' : 'project';
	}

	/**
	 * The page the band sits on, so the request keeps that page as context.
	 *
	 * @param string $intent `project` or `product`.
	 * @return array{kind: string, title: string, url: string, source_id: int, intent: string}
	 */
	private function invitation_context( string $intent ): array {
		$id    = function_exists( 'get_queried_object_id' ) ? (int) get_queried_object_id() : 0;
		$title = $id > 0 ? wp_strip_all_tags( (string) get_the_title( $id ) ) : '';
		$url   = $id > 0 ? (string) get_permalink( $id ) : '';
		$kind  = function_exists( 'is_singular' ) && is_singular( 'post' ) ? 'article' : 'page';
		if ( '' === $title ) {
			$title = 'Linker';
		}
		if ( '' === $url ) {
			$url = home_url( '/' );
		}
		return array(
			'kind'      => $kind,
			'title'     => $title,
			'url'       => $url,
			'source_id' => $id,
			'intent'    => $intent,
		);
	}

	/**
	 * The live band's words, in the page's language.
	 *
	 * German is the page's own wording (Polylang `de`), not a translation of
	 * the English string. The intake band has no eyebrow.
	 *
	 * @return array<string, array{eyebrow: string, heading: string, note: string, button: string}>
	 */
	private static function invitation_copy(): array {
		if ( function_exists( 'pll_current_language' ) && 'de' === pll_current_language() ) {
			return array(
				'solution'   => array(
					'eyebrow' => __( 'LÖSUNGEN FÜR GROSSSPEICHER', 'linker-commerce' ),
					'heading' => __( 'Ihr Großspeicherprojekt als Gesamtlösung gedacht.', 'linker-commerce' ),
					'note'    => __( 'Gemeinsam mit Projektentwicklern und EPC-Teams richten wir Batteriespeicher an Energiezielen, Standort und Einbindung aus. Dabei verbinden wir die Systemauswahl mit einer umsetzbaren Planung für die Lieferung.', 'linker-commerce' ),
					'button'  => __( 'Ihr Projekt gemeinsam entwickeln', 'linker-commerce' ),
				),
				'epc'        => array(
					'eyebrow' => __( 'KONTAKT ZU LINKER', 'linker-commerce' ),
					'heading' => __( 'Das Projekt vor dem vollständigen Briefing besprechen.', 'linker-commerce' ),
					'note'    => __( 'Ihre Frage enthält den Bezug zu dieser Seite. Sie können ihn vor dem Senden entfernen.', 'linker-commerce' ),
					'button'  => __( 'EPC-Anforderung besprechen', 'linker-commerce' ),
				),
				'services'   => array(
					'eyebrow' => __( 'TECHNISCHE ZUSAMMENARBEIT', 'linker-commerce' ),
					'heading' => __( 'Ein technischer Partner in jeder Projektphase.', 'linker-commerce' ),
					'note'    => __( 'Unser Team arbeitet mit Ihrem Team an Systementscheidungen, Installationsfragen und der Inbetriebnahme. Auch nach der Lieferung bleiben wir bei technischen Fragen an Ihrer Seite.', 'linker-commerce' ),
					'button'  => __( 'Mit unserem Technikteam sprechen', 'linker-commerce' ),
				),
				'article'    => array(
					'eyebrow' => __( 'IHR PROJEKT IN DER PRAXIS', 'linker-commerce' ),
					'heading' => __( 'Was kann die passende Speicherlösung an Ihrem Standort leisten?', 'linker-commerce' ),
					'note'    => __( 'Gemeinsam betrachten wir, wie ein Hybrid- oder AC-gekoppelter Speicher zu Ihrer Anlage, Ihrem Energieverbrauch und Ihren Zielen passt.', 'linker-commerce' ),
					'button'  => __( 'Ihre Speicheroptionen besprechen', 'linker-commerce' ),
				),
				'epc-intake' => array(
					'eyebrow' => '',
					'heading' => __( 'Eine frühe Frage reicht aus.', 'linker-commerce' ),
					'note'    => __( 'Teilen Sie mit, was bereits feststeht. Projektstandort und Zeitraum sind im Kurzformular optional.', 'linker-commerce' ),
					'button'  => __( 'Projekt besprechen', 'linker-commerce' ),
				),
			);
		}
		return array(
			'solution'   => array(
				'eyebrow' => __( 'UTILITY-SCALE SOLUTIONS', 'linker-commerce' ),
				'heading' => __( 'A storage solution built around the whole project.', 'linker-commerce' ),
				'note'    => __( 'We work alongside developers and EPC teams to shape battery storage around the project’s energy goals, site conditions and integration needs. Together, we connect system choices with a practical plan for delivery.', 'linker-commerce' ),
				'button'  => __( 'Explore your project with us', 'linker-commerce' ),
			),
			'epc'        => array(
				'eyebrow' => __( 'CONTACT LINKER', 'linker-commerce' ),
				'heading' => __( 'Discuss the project before preparing the full brief.', 'linker-commerce' ),
				'note'    => __( 'Your question includes this page as context. You can remove it before sending.', 'linker-commerce' ),
				'button'  => __( 'Discuss an EPC requirement', 'linker-commerce' ),
			),
			'services'   => array(
				'eyebrow' => __( 'TECHNICAL PARTNERSHIP', 'linker-commerce' ),
				'heading' => __( 'A technical partner, wherever your project stands.', 'linker-commerce' ),
				'note'    => __( 'Our team works with yours on system choices, installation questions and commissioning, and stays involved when support is needed after delivery.', 'linker-commerce' ),
				'button'  => __( 'Talk to our technical team', 'linker-commerce' ),
			),
			'article'    => array(
				'eyebrow' => __( 'YOUR PROJECT, IN PRACTICE', 'linker-commerce' ),
				'heading' => __( 'What could the right storage solution do for your site?', 'linker-commerce' ),
				'note'    => __( 'We’ll explore how hybrid or AC-coupled storage could work with your installation, your energy use and the outcome you want to achieve.', 'linker-commerce' ),
				'button'  => __( 'Talk through your storage options', 'linker-commerce' ),
			),
			'epc-intake' => array(
				'eyebrow' => '',
				'heading' => __( 'An early question is enough.', 'linker-commerce' ),
				'note'    => __( 'Share what you already know. Project location and timing are optional in the short form.', 'linker-commerce' ),
				'button'  => __( 'Discuss your project', 'linker-commerce' ),
			),
		);
	}

	/**
	 * The Proforma request: the gate when the draft is empty or the account
	 * may not send, otherwise WooCommerce's checkout. A guest never reaches
	 * the checkout — the request belongs to a partner account, so guests read
	 * the gate: with products in the draft it names the draft, without them
	 * the Proforma request itself (ticket #184).
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function checkout( $atts = array() ): string {
		unset( $atts );
		$user_id = get_current_user_id();
		if ( $user_id <= 0 || $this->is_empty_request() || ! $this->approval->sees_prices( $user_id ) ) {
			return $this->gate->html();
		}
		return do_shortcode( '[woocommerce_checkout]' );
	}

		/**
		 * The empty solution draft: icon, title, the review note, and the two
		 * ways back that still have a page. The LiveCanvas cart template
		 * prints this when the draft is empty; a filled draft keeps
		 * WooCommerce's cart.
		 *
		 * @param array<string, string>|string $atts Shortcode attributes.
		 */
	public function draft_empty( $atts = array() ): string {
		unset( $atts );
		return $this->empty_draft_html();
	}

	/**
	 * The site's own origin, for the templates whose markup has to print an
	 * absolute URL.
	 *
	 * One place needs it: the blog posts index's `CollectionPage` JSON-LD
	 * carries `"url"` and `"isPartOf.url"`, and a JSON-LD block is inside a
	 * `<script>`, where neither a LiveCanvas/Tangible tag nor a data field
	 * resolves (the template engine leaves script contents alone — measured
	 * 2026-10-16: `<site url />` inside the block renders literally). The live
	 * template carried the host it was authored on, which a repository file
	 * cannot; this is the data the two templates compose, not a design
	 * decision.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function site_url( $atts = array() ): string {
		unset( $atts );
		return esc_url( home_url( '/' ) );
	}

		/**
		 * Markup of the empty solution draft.
		 *
		 * The live empty cart had three actions. The middle one opened a
		 * batch item-number import the owner ruled out on 2026-10-11
		 * (docs/audit/2026-10-11-surface-inventory.md GAP-11: not built), so
		 * the note does not promise one either. This page keeps the two
		 * actions that still have a page: browse products, and sign in.
		 * The heading names the solution draft. Classes only; the look
		 * lives in the storefront volume.
		 */
	private function empty_draft_html(): string {
		$products = (string) get_permalink( wc_get_page_id( 'shop' ) );
		$account  = (string) wc_get_page_permalink( 'myaccount' );
		$icon     = '<svg class="sf-cart-empty__icon" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="20" r="1"/><circle cx="18" cy="20" r="1"/><path d="M3 4h2l2.2 11.2a1 1 0 0 0 1 .8h9.6a1 1 0 0 0 1-.8L21 8H7"/></svg>';
		return sprintf(
			'<section class="sf-cart-empty" aria-label="%1$s">%2$s<h1>%3$s</h1><p>%4$s</p><div class="sf-cart-empty__actions"><a class="sf-cart-btn" href="%5$s">%6$s</a><a class="sf-cart-btn sf-cart-btn--ghost" href="%7$s">%8$s</a></div></section>',
			esc_attr__( 'Empty solution draft', 'linker-commerce' ),
			$icon,
			esc_html__( 'Your solution draft is empty.', 'linker-commerce' ),
			esc_html__( 'Browse the products now. Adding to the solution draft is possible only after your account has been reviewed.', 'linker-commerce' ),
			esc_url( $products ),
			esc_html__( 'Browse products', 'linker-commerce' ),
			esc_url( $account ),
			esc_html__( 'Sign in or register', 'linker-commerce' )
		);
	}

	/**
	 * Whether this is an empty Proforma request (not a confirmation or pay page).
	 * The cart template's own condition function, so the gate and the branch
	 * the visitor sees can never disagree.
	 */
	private function is_empty_request(): bool {
		return linker_commerce_draft_empty();
	}

	/**
	 * The current product's FAQ rows from `_linker_faqs` (docs/specs/15-faq.md),
	 * as the live page's accordion rows. German requests (Polylang `de`) use
	 * question_de / answer_de. The section frame and its title live in the
	 * template; this carries the rows.
	 *
	 * @param array<string, string>|string $atts Shortcode attributes.
	 */
	public function faqs( $atts = array() ): string {
		unset( $atts );
		$product = $GLOBALS['product'] ?? null;
		if ( ! $product instanceof WC_Product ) {
			$product = wc_get_product( (int) get_the_ID() );
		}
		if ( ! $product instanceof WC_Product ) {
			return '';
		}
		$items = Faqs::of( $product->get_id() );
		if ( array() === $items ) {
			return '';
		}
		$german = function_exists( 'pll_current_language' ) && 'de' === pll_current_language();
		$html   = '';
		foreach ( $items as $item ) {
			$question = $german && '' !== $item['question_de'] ? $item['question_de'] : $item['question'];
			$answer   = $german && '' !== $item['answer_de'] ? $item['answer_de'] : $item['answer'];
			$html    .= '<details class="pdp-disclose"><summary>' . esc_html( $question ) . ProductShortcodes::icon( 'chevron' ) . '</summary>'
				. '<div class="pdp-disclose-body pdp-reading">' . wp_kses_post( wpautop( $answer ) ) . '</div></details>';
		}
		return $html;
	}
}
