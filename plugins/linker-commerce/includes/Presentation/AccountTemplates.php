<?php
/**
 * Woo account data for LiveCanvas's account fragments.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Presentation;

use Linker\Commerce\Account\DocumentDownload;
use Linker\Commerce\Account\InquiryList;
use Linker\Commerce\Account\SavedSolutions;
use Linker\Commerce\Inquiry\Statuses;
use Linker\Commerce\Proforma\Issuer;
use Linker\Commerce\Registration\Approval;
use Linker\Commerce\Vocabulary\LocaleFormat;
use WC_Order;

/**
 * Woo retains endpoint dispatch, permissions and forms. Only its content
 * templates hand their already-authorised arguments to LC HTML. LC has no
 * WC_Order/HPOS or private-document array loop; the narrow rows tag supplies
 * those values without emitting layout or deciding their appearance.
 */
final class AccountTemplates {

	/**
	 * Woo template to LC fragment.
	 *
	 * @var array<string, string>
	 */
	private const FILES = array(
		'myaccount/my-account.php'             => 'workspace',
		'myaccount/dashboard.php'              => 'overview',
		'myaccount/orders.php'                 => 'inquiries',
		'myaccount/view-order.php'             => 'inquiry',
		'myaccount/linker-documents.php'       => 'documents',
		'myaccount/linker-saved-solutions.php' => 'solutions',
	);

	/**
	 * Registered adapter for Woo's data-only include.
	 *
	 * @var self|null
	 */
	private static ?self $adapter = null;

	/**
	 * Woo arguments, restored after nested templates.
	 *
	 * @var array<string, mixed>
	 */
	private array $args = array();

	/**
	 * Current LC data row.
	 *
	 * @var array<string, mixed>
	 */
	private array $row = array();

	/**
	 * One dashboard read per render.
	 *
	 * @var list<WC_Order>|null
	 */
	private ?array $overview = null;

	/**
	 * The documents page, built once: the dashboard reads the same list.
	 *
	 * @var \Linker\Commerce\Account\Documents|null
	 */
	private ?\Linker\Commerce\Account\Documents $documents = null;

	/**
	 * Takes the account documents assembly #11 owns when production wires it
	 * (Plugin.php); a bare construction (tests) keeps the local assembly in
	 * documents() as its fallback.
	 *
	 * @param \Linker\Commerce\Account\Documents|null $documents The shared assembly.
	 */
	public function __construct( ?\Linker\Commerce\Account\Documents $documents = null ) {
		$this->documents = $documents;
	}

	/** Registers the content adapter and its data tags. */
	public function register(): void {
		self::$adapter = $this;
		add_filter( 'wc_get_template', array( $this, 'template' ), 20, 2 );
		add_shortcode( 'linker_account_field', array( $this, 'field' ) );
		add_shortcode( 'linker_account_rows', array( $this, 'rows' ) );
		add_shortcode( 'linker_account_hook', array( $this, 'hook' ) );
		add_shortcode( 'linker_account_text', array( $this, 'text' ) );
		add_shortcode( 'linker_account_url', array( $this, 'url' ) );
		add_shortcode( 'linker_account_nav', array( $this, 'nav' ) );
		add_filter( 'woocommerce_my_account_my_orders_query', array( $this, 'orders_query' ) );
	}

	/**
	 * Only account content; never affects checkout, emails or the native forms.
	 *
	 * @param string $path Located template.
	 * @param string $name Woo template name.
	 */
	public function template( string $path, string $name ): string {
		return is_account_page() && is_user_logged_in() && isset( self::FILES[ $name ] ) && shortcode_exists( 'lc_if' )
			? dirname( __DIR__, 2 ) . '/templates/myaccount/livecanvas.php' : $path;
	}

	/**
	 * Called by the Woo include. No markup is produced outside the LC files.
	 *
	 * @param array{template_name: string, args: array<string, mixed>} $context Woo include context.
	 */
	public static function output( array $context ): void {
		if ( null === self::$adapter || ! isset( self::FILES[ $context['template_name'] ] ) ) {
			return;
		}
		$adapter       = self::$adapter;
		$previous      = $adapter->args;
		$adapter->args = $context['args'];
		try {
			// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- LC markup; all dynamic fields escaped by field().
			echo $adapter->fragment( self::FILES[ $context['template_name'] ] );
		} finally {
			$adapter->args = $previous;
		}
	}

	/**
	 * A repository LC fragment; filename is never supplied by a request.
	 *
	 * @param string               $name Fragment name.
	 * @param array<string, mixed> $row  Row data.
	 */
	private function fragment( string $name, array $row = array() ): string {
		$previous  = $this->row;
		$this->row = $row;
		try {
			return do_shortcode( Tokens::read( dirname( __DIR__, 2 ) . '/content/livecanvas/account/' . $name . '.html' ) );
		} finally {
			$this->row = $previous;
		}
	}

	/**
	 * Escaped scalar row values; only Woo's formatted totals and the fragments'
	 * own assembled markup are HTML (sanitised against the post allowlist plus
	 * the sidebar icons' SVG, which wp_kses's post list does not carry).
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function field( $atts = array() ): string {
		$key   = (string) ( $atts['key'] ?? '' );
		$value = $this->row[ $key ] ?? '';
		if ( in_array( $key, array( 'customer-name', 'customer-initials' ), true ) ) {
			$user  = wp_get_current_user();
			$name  = '' !== (string) $user->first_name ? (string) $user->first_name : (string) $user->display_name;
			$value = 'customer-initials' === $key ? mb_strtoupper( mb_substr( $name, 0, 1 ) ) : $name;
		} elseif ( 'page-title' === $key ) {
			$value = is_wc_endpoint_url() ? WC()->query->get_endpoint_title( WC()->query->get_current_endpoint() ) : __( 'Overview', 'linker-commerce' );
			if ( is_wc_endpoint_url( 'orders' ) && in_array( $this->selected_status(), $this->statuses(), true ) ) {
				$value .= ' · ' . wc_get_order_status_name( $this->selected_status() );
			}
		} elseif ( 'open-url' === $key ) {
			$value = add_query_arg( 'inquiry-status', 'open', wc_get_account_endpoint_url( 'orders' ) );
		} elseif ( 'products-url' === $key ) {
			$value = (string) get_permalink( (int) wc_get_page_id( 'shop' ) );
		} elseif ( 'configurator-url' === $key ) {
			$value = $this->translated_page_url( 'solution-configurator' );
		} elseif ( in_array( $key, array( 'all-current', 'open-current' ), true ) ) {
			$value = ( 'open-current' === $key ? $this->open_only() : '' === $this->selected_status() ) ? 'page' : 'false';
		}
		if ( in_array( $key, array( 'icon', 'total', 'items', 'nonce', 'tiles', 'rows' ), true ) ) {
			// 'icon' is fixed markup from nav_icon()/document_icon(), never request
			// data; the allowlist carries the SVG elements either way.
			return 'nonce' === $key ? (string) $value : wp_kses( (string) $value, self::allowed_html() );
		}
		return in_array( $key, array( 'url', 'open-url', 'products-url', 'configurator-url', 'report' ), true ) ? esc_url( (string) $value ) : esc_attr( (string) $value );
	}

	/**
	 * One of the site's own pages in the reader's language; without the page or
	 * its address, the English path stands (the workspace always shows a link).
	 *
	 * @param string $slug The page's path.
	 */
	private function translated_page_url( string $slug ): string {
		$translated = PageUrls::translated( $slug );
		return '' === $translated ? (string) home_url( '/' . $slug . '/' ) : $translated;
	}

	/**
	 * Native Woo hooks that LC places; cannot call arbitrary PHP actions.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function hook( $atts = array() ): string {
		$name = (string) ( $atts['name'] ?? '' );
		ob_start();
		switch ( $name ) {
			case 'content':
				do_action( 'woocommerce_account_content' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo account templates.
				break;
			case 'details':
				$order = $this->args['order'] ?? null;
				// phpcs:ignore WordPress.WP.Capabilities.Unknown -- Woo's per-order meta capability.
				if ( $order instanceof WC_Order && current_user_can( 'view_order', $order->get_id() ) ) {
					do_action( 'woocommerce_view_order', $order->get_id() ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo account templates.
				}
				break;
			case 'before-orders':
				do_action( 'woocommerce_before_account_orders', (bool) ( $this->args['has_orders'] ?? false ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo account templates.
				break;
			case 'after-orders':
				do_action( 'woocommerce_after_account_orders', (bool) ( $this->args['has_orders'] ?? false ) ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo account templates.
				break;
			case 'pagination':
				do_action( 'woocommerce_before_account_orders_pagination' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Native hook documented in Woo account templates.
				break;
			case 'after-content':
				// The sidebar's own slot (the contact person). Pending accounts
				// read the review page, so — like nav() — they get nothing here.
				$user_id = get_current_user_id();
				if ( $user_id > 0 && Approval::PENDING !== ( new Approval() )->status( $user_id ) ) {
					// phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound,WooCommerce.Commenting.CommentHooks -- Account module's existing contact slot.
					do_action( 'linker_account_after_content' );
				}
				break;
		}
		return (string) ob_get_clean();
	}

	/**
	 * Context links remain Woo's URLs, including locale and endpoint slugs.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function url( $atts = array() ): string {
		$endpoint = (string) ( $atts['endpoint'] ?? 'dashboard' );
		return esc_url( wc_get_account_endpoint_url( $endpoint ) );
	}

	/**
	 * The dashboard's grouped navigation: the same menu the header dropdown
	 * reads (Menu::items), split into the groups a dashboard sidebar shows —
	 * the workplace, then the account's own records with sign-out last.
	 * Current page is Woo's own endpoint, so the highlight follows the
	 * request. A pending account reads the review page instead of the
	 * workplace, so it gets no navigation.
	 *
	 * @param array<string, string>|string $atts Optional mobile navigation form.
	 */
	public function nav( $atts = array() ): string {
		$user_id = get_current_user_id();
		if ( $user_id <= 0 || Approval::PENDING === ( new Approval() )->status( $user_id ) ) {
			return '';
		}
		$items = wc_get_account_menu_items();
		$html  = '';
		if ( 'mobile' === ( $atts['type'] ?? '' ) ) {
			foreach ( array( 'dashboard', 'orders', 'documents', 'edit-account' ) as $endpoint ) {
				if ( isset( $items[ $endpoint ] ) ) {
					$current = 'orders' === $endpoint && is_wc_endpoint_url( 'view-order' ) ? 'page' : $this->endpoint_current( $endpoint );
					if ( 'edit-account' === $endpoint && is_wc_endpoint_url( 'edit-address' ) ) {
						$current = 'page';
					}
					$html .= $this->fragment(
						'nav-item',
						array(
							// The tab bar's four entries carry no sign-out; that
							// lives in the sidebar and the header menu.
							'url'     => wc_get_account_endpoint_url( $endpoint ),
							'label'   => 'edit-account' === $endpoint ? __( 'Account', 'linker-commerce' ) : $items[ $endpoint ],
							'current' => $current,
							'icon'    => $this->nav_icon( $endpoint ),
						)
					);
				}
			}
			return $this->fragment( 'mobile-nav', array( 'items' => $html ) );
		}
		foreach ( $this->nav_groups() as $group => $endpoints ) {
			$links = '';
			foreach ( $endpoints as $endpoint ) {
				if ( ! isset( $items[ $endpoint ] ) ) {
					continue;
				}
				$links .= $this->fragment(
					'nav-item',
					array(
						'url'     => 'customer-logout' === $endpoint ? linker_commerce_logout_url() : wc_get_account_endpoint_url( $endpoint ),
						'label'   => $items[ $endpoint ],
						'current' => $this->endpoint_current( $endpoint ),
						'icon'    => $this->nav_icon( $endpoint ),
					)
				);
			}
			if ( '' === $links ) {
				continue;
			}
			$html .= $this->fragment(
				'nav-group',
				array(
					'label' => $this->nav_group_label( $group ),
					'items' => $links,
				)
			);
		}
		if ( '' === $html ) {
			return '';
		}
		return sprintf(
			'<nav class="linker-account-nav" aria-label="%s">%s</nav>',
			esc_attr__( 'Account menu', 'linker-commerce' ),
			$html
		);
	}

	/**
	 * Sidebar groups, in order. Endpoints the menu does not carry are skipped,
	 * and an endpoint another plugin added falls into the account group so it
	 * stays reachable.
	 *
	 * @return array<string, list<string>>
	 */
	private function nav_groups(): array {
		$known   = array(
			'workplace' => array( 'dashboard', 'orders', 'saved-solutions', 'documents' ),
			'account'   => array( 'edit-address', 'edit-account', 'customer-logout' ),
		);
		$account = $known['account'];
		foreach ( array_keys( wc_get_account_menu_items() ) as $endpoint ) {
			if ( ! in_array( $endpoint, array_merge( ...array_values( $known ) ), true ) ) {
				$account[] = $endpoint;
			}
		}
		$known['account'] = $account;
		return $known;
	}

	/**
	 * The group's heading.
	 *
	 * @param string $group Group key.
	 */
	private function nav_group_label( string $group ): string {
		$labels = array(
			'workplace' => __( 'Workplace', 'linker-commerce' ),
			'account'   => __( 'Account', 'linker-commerce' ),
		);
		return $labels[ $group ] ?? $labels['account'];
	}

	/**
	 * The endpoint's sidebar icon: a fixed Lucide outline per endpoint, stroked
	 * in currentColor so the active state recolours it from CSS. An endpoint
	 * another plugin added gets the generic dot.
	 *
	 * @param string $endpoint Endpoint.
	 */
	private function nav_icon( string $endpoint ): string {
		$paths = array(
			'dashboard'       => '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
			'orders'          => '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
			'saved-solutions' => '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/>',
			'documents'       => '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
			'edit-address'    => '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
			'edit-account'    => '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
			'customer-logout' => '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/>',
		);
		$path  = $paths[ $endpoint ] ?? '<circle cx="12" cy="12" r="9"/>';
		return sprintf(
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="linker-account-nav-icon" aria-hidden="true">%s</svg>',
			$path // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup from the map above.
		);
	}

	/**
	 * WordPress's post allowlist plus the SVG elements of the sidebar icons, so
	 * the assembled fragment markup (the nav's items) keeps them. Leaf values
	 * are escaped before assembly, so the icons' fixed markup is the only SVG
	 * that can ever arrive here.
	 *
	 * @return array<string, array<string, bool>>
	 */
	private static function allowed_html(): array {
		$svg = array(
			'svg'      => array(
				'xmlns'           => true,
				'viewbox'         => true,
				'fill'            => true,
				'stroke'          => true,
				'stroke-width'    => true,
				'stroke-linecap'  => true,
				'stroke-linejoin' => true,
				'class'           => true,
				'aria-hidden'     => true,
				'width'           => true,
				'height'          => true,
			),
			'rect'     => array(
				'width'  => true,
				'height' => true,
				'x'      => true,
				'y'      => true,
				'rx'     => true,
			),
			'path'     => array( 'd' => true ),
			'circle'   => array(
				'cx' => true,
				'cy' => true,
				'r'  => true,
			),
			'line'     => array(
				'x1' => true,
				'x2' => true,
				'y1' => true,
				'y2' => true,
			),
			'polyline' => array( 'points' => true ),
		);
		return array_merge( wp_kses_allowed_html( 'post' ), $svg );
	}

	/**
	 * Whether the endpoint is the page being read: "page" or "false", the
	 * values the fragments' aria-current attribute takes.
	 *
	 * @param string $endpoint Endpoint.
	 */
	private function endpoint_current( string $endpoint ): string {
		if ( 'dashboard' === $endpoint ) {
			return is_wc_endpoint_url() ? 'false' : 'page';
		}
		return is_wc_endpoint_url( $endpoint ) ? 'page' : 'false';
	}

	/**
	 * Account-specific labels only; the existing domain remains the word source.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function text( $atts = array() ): string {
		$labels = array(
			'welcome'         => __( 'Welcome back', 'linker-commerce' ),
			'workspace'       => __( 'Your account workspace', 'linker-commerce' ),
			'menu'            => __( 'Account menu', 'linker-commerce' ),
			'overview'        => __( 'Overview', 'linker-commerce' ),
			'inquiries'       => __( 'Inquiries', 'linker-commerce' ),
			'all'             => __( 'All inquiries', 'linker-commerce' ),
			'open'            => __( 'Open inquiries', 'linker-commerce' ),
			'status'          => __( 'Status', 'linker-commerce' ),
			'number'          => __( 'Inquiry', 'linker-commerce' ),
			'date'            => __( 'Date', 'linker-commerce' ),
			'amount'          => __( 'Amount', 'linker-commerce' ),
			'actions'         => __( 'Actions', 'linker-commerce' ),
			'view'            => __( 'View', 'linker-commerce' ),
			'document'        => __( 'Document', 'linker-commerce' ),
			'download'        => __( 'Download (PDF)', 'linker-commerce' ),
			'saved'           => __( 'Saved on', 'linker-commerce' ),
			'add'             => __( 'Add to solution draft', 'linker-commerce' ),
			'report'          => __( 'Design report (PDF)', 'linker-commerce' ),
			'previous'        => __( 'Previous', 'woocommerce' ), /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */
			'next'            => __( 'Next', 'woocommerce' ), /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */
			'empty'           => __( 'No inquiries yet.', 'linker-commerce' ),
			'browse'          => __( 'Browse products', 'linker-commerce' ),
			'configurator'    => __( 'Open the Solution Configurator', 'linker-commerce' ),
			'empty-documents' => __( 'Your Proforma invoices and the design reports of your saved solutions will appear here.', 'linker-commerce' ),
			'empty-solutions' => __( 'Solutions you save in the Solution Configurator appear here, with their design report.', 'linker-commerce' ),
			'recent'          => __( 'Recent inquiries', 'linker-commerce' ),
			'view-all'        => __( 'View all', 'linker-commerce' ),
			'documents'       => __( 'Documents', 'linker-commerce' ),
		);
			return esc_html( $labels[ (string) ( $atts['key'] ?? '' ) ] ?? '' );
	}

	/**
	 * LC data loops, limited to the existing account's records and actions.
	 *
	 * @param array<string, string>|string $atts Attributes.
	 */
	public function rows( $atts = array() ): string {
		if ( get_current_user_id() <= 0 ) {
			return '';
		}
		$type = (string) ( $atts['type'] ?? '' );
		$html = '';
		switch ( $type ) {
			case 'dashboard':
				return $this->dashboard();
			case 'inquiries':
				$orders = $this->row['orders'] ?? ( $this->args['customer_orders']->orders ?? array() );
				foreach ( $orders as $order ) {
					$order = wc_get_order( $order );
					if ( $order instanceof WC_Order && $order->get_customer_id() === get_current_user_id() ) {
						$html .= $this->fragment( 'inquiry-card', $this->order_row( $order ) );
					}
				}
				return '' === $html ? $this->fragment( 'empty-inquiries' ) : $html;
			case 'summary':
				$order = $this->args['order'] ?? null;
				// phpcs:ignore WordPress.WP.Capabilities.Unknown -- Woo's per-order meta capability.
				return $order instanceof WC_Order && current_user_can( 'view_order', $order->get_id() ) ? $this->fragment( 'summary', $this->order_row( $order ) ) : '';
			case 'proforma':
				$order = $this->row['order'] ?? null;
				if ( ! $order instanceof WC_Order || ! InquiryList::has_proforma( $order ) ) {
					return '';
				}
				return $this->fragment(
					'proforma',
					array(
						'number' => InquiryList::proforma_number( $order ),
						'url'    => DocumentDownload::proforma_url( $order ),
						'name'   => __( 'Proforma invoice (PDF)', 'linker-commerce' ),
					)
				);
			case 'stages':
				$order = $this->row['order'] ?? null;
				if ( $order instanceof WC_Order ) {
					// Only the stored status is current; no invented transition
					// history. A stage is reached when the record says so: the
					// inquiry arrived, its Proforma number is stored, its status
					// is completed or it was cancelled.
					$reached = array(
						Statuses::RECEIVED => true,
						Statuses::PROFORMA => InquiryList::has_proforma( $order ),
						'completed'        => $order->has_status( 'completed' ),
						'cancelled'        => $order->has_status( 'cancelled' ),
					);
					foreach ( $this->statuses() as $status ) {
						$current = $order->has_status( $status );
						$html   .= $this->fragment(
							'stage',
							array(
								'label'   => wc_get_order_status_name( $status ),
								'current' => $current ? 'step' : 'false',
								'status'  => $status,
								'state'   => $current ? 'now' : ( ( $reached[ $status ] ?? false ) ? 'done' : 'todo' ),
							)
						);
					}
				}
				return $html;
			case 'documents':
				foreach ( $this->args['documents'] ?? array() as $document ) {
					$html .= $this->fragment( 'document-row', $this->document_row( $document ) );
				}
				return '' === $html ? $this->fragment( 'empty-documents' ) : $html;
			case 'solutions':
				$saved = $this->args['saved'] ?? null;
				if ( $saved instanceof SavedSolutions ) {
					foreach ( $this->args['solutions'] ?? array() as $solution ) {
						if ( get_current_user_id() !== (int) $solution->post_author ) {
							continue;
						}
						$items = '';
						foreach ( $saved->items( $solution->ID ) as $item ) {
							$product = wc_get_product( $item['product_id'] );
							if ( $product ) {
								$items .= $this->fragment(
									'product-line',
									array(
										'quantity' => $item['quantity'],
										'name'     => $product->get_name(),
									)
								);
							}
						}
						$html .= $this->fragment(
							'solution-card',
							array(
								'id'     => $solution->ID,
								'title'  => $solution->post_title,
								'date'   => wp_date( LocaleFormat::date_format(), (int) get_post_timestamp( $solution ) ),
								'items'  => $items,
								'nonce'  => wp_nonce_field( SavedSolutions::ADD_ACTION . '_' . $solution->ID, '_wpnonce', true, false ),
								'report' => '' !== $saved->report_path( $solution->ID ) ? DocumentDownload::report_url( $solution->ID ) : '',
							)
						);
					}
				}
				return '' === $html ? $this->fragment( 'empty-solutions' ) : $html;
			case 'report':
				return '' !== (string) ( $this->row['report'] ?? '' ) ? $this->fragment(
					'action',
					array(
						'kind' => 'report',
						'url'  => $this->row['report'],
						'name' => __( 'Design report (PDF)', 'linker-commerce' ),
					)
				) : '';
			case 'pagination':
				$pages   = (int) ( $this->args['customer_orders']->max_num_pages ?? 1 );
				$current = (int) ( $this->args['current_page'] ?? 1 );
				if ( $current > 1 ) {
					$html .= $this->fragment(
						'page-link',
						array(
							'url'  => $this->page_url( $current - 1 ),
							'name' => __( 'Previous', 'woocommerce' ), /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */
						)
					);
				}
				if ( $current < $pages ) {
					$html .= $this->fragment(
						'page-link',
						array(
							'url'  => $this->page_url( $current + 1 ),
							'name' => __( 'Next', 'woocommerce' ), /* phpcs:ignore WordPress.WP.I18n.TextDomainMismatch -- Woo native label. */
						)
					);
				}
				return $html;
		}
		return '';
	}

	/**
	 * The dashboard: one tile per inquiry state with its count, the newest
	 * inquiries as rows, and the newest documents. Every value comes from the
	 * records the account already reads — the customer's own inquiries and
	 * Documents' own list — so the dashboard adds no query and no rule.
	 */
	private function dashboard(): string {
		$customer = get_current_user_id();
		$orders   = $this->overview_orders();
		$tiles    = '';
		foreach ( $this->statuses() as $status ) {
			$of_status = array_values( array_filter( $orders, static fn ( WC_Order $order ): bool => $order->has_status( $status ) ) );
			$tiles    .= $this->fragment(
				'tile',
				array(
					'status' => $status,
					'title'  => wc_get_order_status_name( $status ),
					'count'  => count( $of_status ),
					'url'    => add_query_arg( array( 'inquiry-status' => $status ), wc_get_account_endpoint_url( 'orders' ) ),
				)
			);
		}
		$recent = '';
		foreach ( array_slice( $orders, 0, 5 ) as $order ) {
			$recent .= $this->fragment( 'inquiry-row', $this->order_row( $order ) );
		}
		$documents = '';
		foreach ( array_slice( $this->documents()->for_customer( $customer ), 0, 3 ) as $document ) {
			$documents .= $this->fragment( 'document-row', $this->document_row( $document ) );
		}
		return $this->fragment( 'tiles', array( 'tiles' => $tiles ) )
			. $this->fragment(
				'recent',
				array(
					'rows' => '' === $recent ? $this->fragment( 'empty' ) : $recent,
				)
			)
			. $this->fragment(
				'documents-entry',
				array(
					'rows' => '' === $documents ? $this->fragment( 'empty-documents' ) : $documents,
				)
			);
	}

	/**
	 * The four inquiry states, in the order the account reads them.
	 *
	 * @return list<string>
	 */
	private function statuses(): array {
		return array( Statuses::RECEIVED, Statuses::PROFORMA, 'completed', 'cancelled' );
	}

	/**
	 * The documents list the Documents page reads, so the dashboard's entry
	 * and the page can never disagree about what a document is.
	 */
	private function documents(): \Linker\Commerce\Account\Documents {
		if ( null === $this->documents ) {
			$this->documents = new \Linker\Commerce\Account\Documents(
				new \Linker\Commerce\Account\SavedSolutions( new \Linker\Commerce\Account\PrivateFiles( \Linker\Commerce\Account\SavedSolutions::REPORTS_DIRECTORY ), '' ),
				''
			);
		}
		return $this->documents;
	}

	/**
	 * The open tab changes only Woo's query, retaining its customer and paging.
	 *
	 * @param array<string, mixed> $query Woo's account query.
	 * @return array<string, mixed>
	 */
	/**
	 * Adds the selected status to the query Woo runs, if there is a valid
	 * selection; anything unselected or invalid leaves the query untouched.
	 *
	 * @param array<string, mixed> $query Query as passed to wc_get_orders().
	 * @return array<string, mixed>
	 */
	public function orders_query( array $query ): array {
		if ( $this->open_only() ) {
			$query['status'] = array( Statuses::RECEIVED, Statuses::PROFORMA );
		} else {
			$status = $this->selected_status();
			if ( in_array( $status, $this->statuses(), true ) ) {
				$query['status'] = array( $status );
			}
		}
		return $query;
	}

	/** Read-only list selection, never an action or a mutation. */
	private function open_only(): bool {
		return 'open' === $this->selected_status();
	}

	/** Validated selection shared by the heading, tabs, query and pagination. */
	private function selected_status(): string {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- Read-only filter.
		$status = isset( $_GET['inquiry-status'] ) && is_string( $_GET['inquiry-status'] ) ? sanitize_key( wp_unslash( $_GET['inquiry-status'] ) ) : '';
		return in_array( $status, array_merge( $this->statuses(), array( 'open' ) ), true ) ? $status : '';
	}

	/**
	 * Woo page URL, retaining the current status selection.
	 *
	 * @param int $page Page number.
	 */
	private function page_url( int $page ): string {
		$url = wc_get_endpoint_url( 'orders', (string) $page );
		return '' === $this->selected_status() ? $url : add_query_arg( array( 'inquiry-status' => $this->selected_status() ), $url );
	}

	/**
	 * Dashboard data from Woo's storage-independent customer query.
	 *
	 * @return list<WC_Order>
	 */
	private function overview_orders(): array {
		if ( null !== $this->overview ) {
			return $this->overview;
		}
		$orders         = wc_get_orders(
			array(
				'customer_id' => get_current_user_id(),
				'status'      => array( Statuses::RECEIVED, Statuses::PROFORMA, 'completed', 'cancelled' ),
				'limit'       => -1,
			)
		);
		$this->overview = is_array( $orders ) ? array_values( $orders ) : array();
		return $this->overview;
	}

	/**
	 * Inquiry values the account fragments read, including the Proforma number
	 * and its download link once the inquiry is issued.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return array<string, mixed>
	 */
	public function inquiry_row( WC_Order $order ): array {
		return $this->order_row( $order );
	}

	/**
	 * Inquiry values from the one Woo order.
	 *
	 * @param WC_Order $order Inquiry.
	 * @return array<string, mixed>
	 */
	private function order_row( WC_Order $order ): array {
		$count = 0;
		foreach ( $order->get_items() as $item ) {
			$count += $item->get_quantity();
		}
			return array(
				'order'           => $order,
				'id'              => $order->get_id(),
				'number'          => $order->get_order_number(),
				'status'          => wc_get_order_status_name( $order->get_status() ),
				'status-slug'     => $order->get_status(),
				'date'            => $order->get_date_created() ? wc_format_datetime( $order->get_date_created() ) : '',
				'total'           => $order->get_formatted_order_total(),
				'url'             => $order->get_view_order_url(),
				'items-summary'   => self::items_summary( $count ),
				/* translators: %s: inquiry number. */
				'view-aria'       => sprintf( __( 'View inquiry %s', 'linker-commerce' ), '#' . $order->get_order_number() ),
				'proforma'        => InquiryList::has_proforma( $order ) ? '1' : '',
				'proforma_number' => InquiryList::proforma_number( $order ),
				'proforma_url'    => InquiryList::has_proforma( $order ) ? DocumentDownload::proforma_url( $order ) : '',
			);
	}

	/**
	 * How many products an inquiry holds, as the list reads it: "3 products",
	 * "1 product".
	 *
	 * @param int $count The inquiry's product quantity.
	 */
	private static function items_summary( int $count ): string {
		return sprintf(
			/* translators: %s: number of products in the inquiry. */
			_n( '%s product', '%s products', $count, 'linker-commerce' ),
			number_format_i18n( $count )
		);
	}

	/**
	 * A document row: the stored values plus the date and the icon its kind
	 * carries. The Documents assembly reads the same rows for the Documents
	 * page and for the overview's entry, so the two can never disagree.
	 *
	 * @param array{title: string, date: int, url: string, kind?: string} $document Document.
	 * @return array<string, mixed>
	 */
	private function document_row( array $document ): array {
		$document['date'] = wp_date( LocaleFormat::date_format(), $document['date'] );
		$document['icon'] = self::document_icon( (string) ( $document['kind'] ?? '' ) );
		return $document;
	}

	/**
	 * The document's own mark: the receipt for a Proforma invoice, the report
	 * sheet for a design report, a download sheet when the kind is not one of
	 * the two.
	 *
	 * @param string $kind proforma or report.
	 */
	private static function document_icon( string $kind ): string {
		$paths = array(
			'proforma' => '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4"/>',
			'report'   => '<path d="M4 19V5a2 2 0 0 1 2-2h9l5 5v11a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2Z"/><path d="M8 15l3-3 2 2 3-4"/>',
		);
		$path  = $paths[ $kind ] ?? '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>';
		return sprintf(
			'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">%s</svg>',
			$path // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- fixed markup from the map above.
		);
	}
}
