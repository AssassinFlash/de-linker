<?php
/**
 * The single product page as the live site renders it: a byte-faithful port
 * of the live renderer (product-page-storefront.php of the live plugin,
 * snapshot 20261010-0033) into the LiveCanvas channel. The markup, the class
 * names and the data derivations are the live ones; the data comes from the
 * same registry JSONs (LiveCatalog) and the same WooCommerce fields.
 *
 * Recorded deviation (the tool rename, #13): the assistant button's label
 * reads "Ask Genie" where the live page says "Ask Linker Advisor"; the markup
 * around it is unchanged.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

use Linker\Commerce\Gating\CommerceState;
use WC_Product;

/**
 * Renders the product page's markup. One public method, called by the
 * [linker_pdp] shortcode of the LiveCanvas single-product template.
 */
final class ProductPage {

	/**
	 * Who sees the product's price.
	 */
	private CommerceState $state;

	/**
	 * Sets up the renderer.
	 */
	public function __construct( CommerceState $state = new CommerceState() ) {
		$this->state = $state;
	}

	/**
	 * The whole page under (and including) #tv-storefront-pdp.
	 *
	 * @param WC_Product $product The product.
	 */
	public function render( WC_Product $product ): string {
		$product_id = (int) $product->get_id();
		$identity   = LiveCatalog::identity( $product );
		$brand      = \trim( (string) $identity['brand'] );
		$model      = \trim( (string) $identity['model'] );
		$name       = self::display_name( $product );
		$headline   = '' !== $model ? $model : $name;
		$designation = self::designation( $name, $brand, $model );
		$sku        = (string) $product->get_sku();
		$acf        = LiveCatalog::acf( $product_id );
		$specs      = LiveCatalog::specs( $product );
		$pdp_type   = LiveCatalog::contract_type( (string) $identity['kind'] );
		$stat_keys  = self::pdp_keys( $pdp_type );

		$can_view_prices = $this->state->visitor_sees_prices();
		$sellable        = ! $this->state->is_rfq_only( $product );
		$can_purchase    = $sellable && $can_view_prices && $product->is_purchasable() && $product->is_in_stock();
		$unit_price      = $can_view_prices && $this->state->shows_price( $product ) && $product->get_price() !== ''
			? (float) $product->get_price()
			: null;
		$availability    = LiveCatalog::availability_text( $product, $sellable );
		$account_url     = self::account_url( $product );
		$shop_url        = (string) \wc_get_page_permalink( 'shop' );
		$cart_url        = (string) \wc_get_cart_url();

		$buy_specs = array();
		foreach ( $stat_keys as $key ) {
			if ( \count( $buy_specs ) >= 4 ) {
				break;
			}
			if ( \in_array( $key, array( 'weight', 'dimensions', 'temp' ), true ) ) {
				continue;
			}
			if ( empty( $specs[ $key ]['value'] ) ) {
				continue;
			}
			$buy_specs[] = $specs[ $key ] + array( 'icon' => self::stat_icon( $key ), 'key' => $key );
		}

		$gallery_ids = LiveCatalog::gallery_ids( $product, $acf );
		if ( ! $gallery_ids && $product->get_image_id() ) {
			$gallery_ids = array( (int) $product->get_image_id() );
		}
		$gallery_captions = array();
		foreach ( \is_array( $acf['product_gallery'] ?? null ) ? $acf['product_gallery'] : array() as $row ) {
			$gid = (int) ( $row['gallery_image'] ?? 0 );
			if ( $gid ) {
				$gallery_captions[ $gid ] = (string) ( $row['gallery_caption'] ?? '' );
			}
		}
		$gallery_urls = array();
		foreach ( $gallery_ids as $gid ) {
			$url = \wp_get_attachment_image_url( (int) $gid, 'large' );
			if ( $url ) {
				$gallery_urls[] = array(
					'id' => (int) $gid,
					'url' => $url,
					'caption' => $gallery_captions[ (int) $gid ] ?? '',
				);
			}
		}
		$selected = $gallery_urls ? $gallery_urls[0] : null;

		$freight   = LiveCatalog::freight_outcome( LiveCatalog::logistics( $product_id, $product ) );
		$delivery  = (string) ( $freight['headline'] ?? '' );
		if ( 'exact' === ( $freight['kind'] ?? '' ) && ! empty( $freight['detail'] ) ) {
			$delivery = (string) $freight['detail'];
		} elseif ( 'estimate' === ( $freight['kind'] ?? '' ) && ! empty( $freight['detail'] ) ) {
			$delivery = '' !== $delivery ? $delivery . ' · ' . (string) $freight['detail'] : (string) $freight['detail'];
		}
		if ( ! $sellable ) {
			$delivery = '';
		}
		$max_qty = \method_exists( $product, 'get_max_purchase_quantity' ) ? (int) $product->get_max_purchase_quantity() : -1;

		$value   = \is_array( $acf['value_prop'] ?? null ) ? $acf['value_prop'] : array();
		$details = \is_array( $acf['description_media'] ?? null ) ? $acf['description_media'] : array();
		$intro   = \trim( (string) ( $value['intro'] ?? '' ) );
		if ( '' === $intro ) {
			$intro = \trim( (string) ( $acf['product_short_intro'] ?? '' ) );
		}
		if ( '' === $intro ) {
			$intro = \wp_strip_all_tags( (string) ( $product->get_short_description() ?: $product->get_description() ) );
		}
		$desc_heading = \trim( (string) ( $value['headline'] ?? '' ) );
		if ( '' === $desc_heading ) {
			$desc_heading = \trim( (string) ( $details['title'] ?? '' ) );
		}
		if ( '' === $desc_heading ) {
			$desc_heading = $name;
		}
		$desc_image_id = (int) ( $details['image'] ?? 0 );
		$desc_image    = $desc_image_id ? \wp_get_attachment_image_url( $desc_image_id, 'large' ) : '';
		$desc_image_2  = (int) ( $details['image_2'] ?? 0 );
		$desc_image_2_url = $desc_image_2 ? \wp_get_attachment_image_url( $desc_image_2, 'large' ) : '';
		$benefits = array();
		foreach ( \is_array( $value['benefit_bullets'] ?? null ) ? $value['benefit_bullets'] : array() as $bullet ) {
			$bullet = \trim( (string) $bullet );
			if ( '' !== $bullet ) {
				$benefits[] = $bullet;
			}
		}
		$feature_cards = \is_array( $acf['feature_cards'] ?? null ) ? $acf['feature_cards'] : array();
		$spec_groups   = \is_array( $acf['spec_groups'] ?? null ) ? $acf['spec_groups'] : array();
		$stats_claim   = \is_array( $acf['stats_claim'] ?? null ) ? $acf['stats_claim'] : array();
		$faqs          = \is_array( $acf['faqs'] ?? null ) ? $acf['faqs'] : array();
		$wits          = \is_array( $acf['whats_in_the_system'] ?? null ) ? $acf['whats_in_the_system'] : array();
		$documents     = LiveCatalog::documents( $product );

		$related_ids = array();
		foreach ( \is_array( $acf['related_products'] ?? null ) ? $acf['related_products'] : array() as $rid ) {
			$rid = (int) $rid;
			if ( $rid > 0 && $rid !== $product_id ) {
				$related_ids[] = $rid;
			}
		}

		$scene_media = array();
		foreach ( \is_array( $acf['product_gallery'] ?? null ) ? $acf['product_gallery'] : array() as $row ) {
			$label = \strtolower( (string) ( $row['gallery_label'] ?? '' ) );
			if ( \in_array( $label, array( 'product', 'produkt', 'diagram', 'diagramm' ), true ) ) {
				continue;
			}
			$scene_media[] = $row;
		}

		$has_description = '' !== $intro || $benefits || '' !== $desc_image_2_url || ! empty( $details['body'] ) || ! empty( $details['hairlines'] ) || ! empty( $acf['official_highlights'] );
		$has_specs  = $spec_groups || ! empty( $stats_claim['cards'] ) || ! empty( $stats_claim['title'] ) || ! empty( $stats_claim['label'] ) || ! empty( $stats_claim['body'] );
		$scenarios  = self::scenario_rows( $acf );
		$has_scenes = $scene_media && ! $scenarios;
		$has_fit    = $scenarios || $has_scenes;
		$has_docs   = (bool) $documents;

		$family = self::family_articles( $product );
		$compare_cols = \count( $family ) >= 2 ? self::family_compare_columns( $family, $product_id ) : array();
		$compare_keys = array();
		$compare_data = array();
		$compare_labels = array();
		if ( \count( $compare_cols ) >= 2 ) {
			$compare_keys = self::pdp_keys( $pdp_type );
			foreach ( $compare_cols as $col ) {
				$cid    = (int) $col['id'];
				$cprod  = \wc_get_product( $cid );
				$cspecs = $cprod instanceof WC_Product ? LiveCatalog::specs( $cprod ) : array();
				foreach ( $compare_keys as $key ) {
					$compare_data[ $cid ][ $key ] = isset( $cspecs[ $key ]['value'] ) ? self::spec_figures( $cspecs[ $key ] ) : '';
					if ( '' !== $compare_data[ $cid ][ $key ] && isset( $cspecs[ $key ]['label'] ) ) {
						$compare_labels[ $key ][ (string) $cspecs[ $key ]['label'] ] = true;
					}
				}
			}
			$compare_keys = \array_values( \array_filter( $compare_keys, static function ( $key ) use ( $compare_cols, $compare_data ) {
				$filled = 0;
				foreach ( $compare_cols as $col ) {
					if ( '' !== $compare_data[ (int) $col['id'] ][ $key ] ) {
						$filled++;
					}
				}
				return $filled >= 2;
			} ) );
		}
		$has_compare = \count( $compare_cols ) >= 2 && $compare_keys;

		$nav = array();
		if ( $has_description ) {
			$nav[] = array( 'description', __( 'Description', 'linker-commerce' ) );
		}
		if ( $has_compare ) {
			$nav[] = array( 'compare', __( 'Compare models', 'linker-commerce' ) );
		}
		if ( $has_specs ) {
			$nav[] = array( 'stats', __( 'Technical data', 'linker-commerce' ) );
		}
		if ( $has_fit ) {
			$nav[] = array( 'fit', __( 'Applications', 'linker-commerce' ) );
		}
		if ( $has_docs ) {
			$nav[] = array( 'downloads', __( 'Documents', 'linker-commerce' ) );
		}
		$confirm = 'exact' !== ( $freight['kind'] ?? '' ) && '' !== $availability;
		$series_name = \trim( (string) ( $acf['product_series'] ?? '' ) ) ?: $brand;
		$brand_logo_ids = array( 'ecoflow' => 2794, 'goodwe' => 2788 );
		$brand_logo_id = $brand_logo_ids[ \strtolower( $brand ) ] ?? 0;
		$brand_logo = $brand_logo_id
			? (string) \wp_get_attachment_image( $brand_logo_id, 'full', false, array(
				'class' => 'pdp-brand-logo',
				'alt' => $brand,
				'loading' => 'eager',
				'decoding' => 'async',
			) )
			: '';

		\ob_start();
		?>
		<div id="tv-storefront-pdp" class="sf-pdp<?php echo \strtolower( $brand ) === 'goodwe' ? ' pdp-brand-goodwe' : ''; ?>">
			<div class="sf-container">
				<nav class="pdp-crumbs" aria-label="<?php echo \esc_attr__( 'Breadcrumb', 'linker-commerce' ); ?>">
					<a href="<?php echo \esc_url( $shop_url ); ?>"><?php echo \esc_html__( 'Products', 'linker-commerce' ); ?></a>
					<span aria-hidden="true">/</span>
					<?php if ( '' !== $brand ) : ?><span><?php echo \esc_html( $brand ); ?></span><span aria-hidden="true">/</span><?php endif; ?>
					<span><?php echo \esc_html( $headline ); ?></span>
				</nav>
				<div class="pdp-layout">
					<div class="pdp-gallery">
						<?php if ( $selected ) : ?>
						<div class="pdp-gallery-pair">
							<button type="button" class="pdp-gallery-main-wrap" data-pdp-image data-pdp-main data-src="<?php echo \esc_url( $selected['url'] ); ?>" data-caption="<?php echo \esc_attr( $selected['caption'] ); ?>">
								<img class="pdp-gallery-main" src="<?php echo \esc_url( $selected['url'] ); ?>" alt="<?php echo \esc_attr( $name ); ?>">
							</button>
							<?php if ( isset( $gallery_urls[1] ) ) : ?>
							<button type="button" class="pdp-gallery-secondary" data-pdp-image data-src="<?php echo \esc_url( $gallery_urls[1]['url'] ); ?>" data-caption="<?php echo \esc_attr( $gallery_urls[1]['caption'] ); ?>" aria-label="<?php echo \esc_attr( \sprintf( /* translators: %d: gallery position */ \__( 'Product image %d', 'linker-commerce' ), 2 ) ); ?>">
								<img src="<?php echo \esc_url( $gallery_urls[1]['url'] ); ?>" alt="">
							</button>
							<?php endif; ?>
						</div>
						<?php if ( \count( $gallery_urls ) > 1 ) : ?>
						<div class="pdp-thumbs">
							<?php foreach ( $gallery_urls as $index => $image ) : ?>
							<button type="button" data-pdp-thumb data-src="<?php echo \esc_url( $image['url'] ); ?>" data-caption="<?php echo \esc_attr( $image['caption'] ); ?>" aria-label="<?php echo \esc_attr( \sprintf( /* translators: %d: gallery position */ \__( 'Product image %d', 'linker-commerce' ), $index + 1 ) ); ?>" aria-pressed="<?php echo 0 === $index ? 'true' : 'false'; ?>" class="pdp-thumb">
								<?php
								// 'medium' is scaled, not cropped: the thumb shows the whole image (object-fit: contain), as the pairing cards do.
								echo \wp_get_attachment_image( (int) $image['id'], 'medium', false, array( 'alt' => '', 'sizes' => '72px' ) );
								?>
							</button>
							<?php endforeach; ?>
						</div>
						<?php endif; ?>
						<?php else : ?>
						<div class="pdp-empty-visual"><?php echo \esc_html__( 'No product image', 'linker-commerce' ); ?></div>
						<?php endif; ?>
					</div>
					<aside class="pdp-purchase">
						<div class="pdp-buy-inner">
							<?php if ( '' !== $brand_logo ) : ?>
							<div class="pdp-brand pdp-brand--logo"><?php echo $brand_logo; ?></div>
							<?php elseif ( '' !== $brand ) : ?><p class="pdp-brand"><?php echo \esc_html( $brand ); ?></p><?php endif; ?>
							<h1 class="pdp-h1"><?php echo \esc_html( $headline ); ?></h1>
							<?php if ( '' !== $designation && 0 !== \strcasecmp( $designation, $headline ) ) : ?>
							<p class="pdp-designation"><?php echo \esc_html( $designation ); ?></p>
							<?php endif; ?>
							<?php if ( '' !== $sku ) : ?><p class="pdp-sku"><?php echo \esc_html__( 'Item number', 'linker-commerce' ); ?>: <?php echo \esc_html( $sku ); ?></p><?php endif; ?>
							<div class="pdp-price">
								<?php if ( null !== $unit_price ) : ?>
								<p class="pdp-price-value"><?php echo \wp_kses_post( \wc_price( $unit_price ) ); ?></p>
								<p class="pdp-price-note"><?php echo \esc_html__( 'Net, excl. VAT and shipping', 'linker-commerce' ); ?></p>
								<?php elseif ( ! $can_view_prices ) : ?>
								<a class="pdp-price-login" href="<?php echo \esc_url( $account_url ); ?>"><?php echo \esc_html( self::price_prompt_label( 'pdp' ) ); ?></a>
								<?php else : ?>
								<p class="pdp-price-value"><?php echo \esc_html( self::state_label( $product ) ); ?></p>
								<?php endif; ?>
							</div>
							<?php if ( $buy_specs ) : ?>
							<dl class="pdp-spec-list">
								<?php foreach ( $buy_specs as $row ) : ?>
								<div><?php echo $row['icon']; ?><dt><?php echo \esc_html( $row['label'] ); ?></dt><dd><?php echo \esc_html( self::spec_figures( $row ) ); ?></dd></div>
								<?php endforeach; ?>
							</dl>
							<?php endif; ?>
							<?php if ( \count( $family ) >= 2 ) : ?>
							<div class="pdp-model">
								<label for="product-model"><?php echo \esc_html__( 'Model', 'linker-commerce' ); ?></label>
								<select id="product-model" data-product-model>
									<?php foreach ( $family as $row ) : ?>
									<option value="<?php echo \esc_url( (string) $row['url'] ); ?>" <?php echo \selected( ! empty( $row['current'] ) ); ?>><?php echo \esc_html( (string) $row['label'] ); ?></option>
									<?php endforeach; ?>
								</select>
								<?php if ( $has_compare ) : ?>
								<a class="pdp-inline-link" href="#compare"><?php echo \esc_html__( 'Compare different models', 'linker-commerce' ); ?><?php echo self::icon( 'arrow' ); ?></a>
								<?php endif; ?>
							</div>
							<?php endif; ?>
							<div class="pdp-avail">
								<p class="pdp-avail-label"><span class="pdp-dot<?php echo $confirm ? ' is-wait' : ''; ?>"></span><?php echo \esc_html( $availability ); ?></p>
								<?php if ( '' !== $delivery ) : ?><p class="pdp-avail-note"><?php echo \esc_html( $delivery ); ?></p><?php endif; ?>
							</div>
							<?php if ( $can_purchase ) : ?>
							<form class="pdp-atc" method="post" action="<?php echo \esc_url( $cart_url ); ?>">
								<label class="pdp-qty-lab" for="pdp-qty"><?php echo \esc_html__( 'Quantity', 'linker-commerce' ); ?></label>
								<div class="pdp-buy-row">
									<div class="pdp-qty">
										<button type="button" class="pdp-qty-step" data-qstep="-1" aria-label="<?php echo \esc_attr__( 'Decrease quantity', 'linker-commerce' ); ?>"><?php echo self::icon( 'minus' ); ?></button>
										<input id="pdp-qty" class="pdp-qty-in" name="quantity" type="number" value="1" min="1"<?php echo $max_qty > 0 ? ' max="' . \esc_attr( (string) $max_qty ) . '"' : ''; ?> step="1" inputmode="numeric" autocomplete="off" aria-label="<?php echo \esc_attr__( 'Quantity', 'linker-commerce' ); ?>">
										<button type="button" class="pdp-qty-step" data-qstep="1" aria-label="<?php echo \esc_attr__( 'Increase quantity', 'linker-commerce' ); ?>"><?php echo self::icon( 'plus' ); ?></button>
									</div>
									<button type="submit" class="pdp-btn pdp-btn-dark pdp-atc-btn" name="add-to-cart" value="<?php echo \esc_attr( (string) $product_id ); ?>"><?php echo \esc_html__( 'Add to cart', 'linker-commerce' ); ?></button>
								</div>
							</form>
							<?php elseif ( ! $can_view_prices ) : ?>
							<a class="pdp-btn pdp-btn-dark" href="<?php echo \esc_url( $account_url ); ?>"><?php echo \esc_html( self::price_prompt_label( 'cta' ) ); ?></a>
							<?php else : ?>
							<span class="pdp-btn pdp-btn-off" aria-disabled="true"><?php echo \esc_html( self::state_label( $product ) ); ?></span>
							<?php endif; ?>
							<a class="pdp-btn pdp-btn-secondary" <?php echo self::contact_entry_attributes( $product ); ?>><?php echo \esc_html__( 'Ask about this product', 'linker-commerce' ); ?></a>
							<div class="pdp-product-tools">
								<button type="button" class="pdp-tool" data-compare-article="<?php echo \esc_attr( (string) $product_id ); ?>" aria-pressed="false"><?php echo self::icon( 'compare' ); ?><span data-compare-label><?php echo \esc_html__( 'Compare', 'linker-commerce' ); ?></span></button>
								<button type="button" class="pdp-tool" onclick="window.dispatchEvent(new CustomEvent('lia:ask',{detail:{message:'<?php echo \esc_js( self::article_question_prompt( $product ) ); ?>',trigger:this}}))"><?php echo self::icon( 'ask' ); ?><?php echo \esc_html__( 'Ask Genie', 'linker-commerce' ); ?></button>
								<?php if ( $has_docs ) : ?>
								<a class="pdp-tool" href="#downloads"><?php echo self::icon( 'file' ); ?><?php echo \esc_html__( 'Documents', 'linker-commerce' ); ?></a>
								<?php endif; ?>
								<?php echo self::compare_chip_html(); ?>
							</div>
							<details class="pdp-project-check" data-linker-project-product-context aria-label="<?php echo \esc_attr__( 'Check this model for the project', 'linker-commerce' ); ?>">
								<summary>
									<h2><?php echo \esc_html( \sprintf( /* translators: %s: model name */ \__( 'Plan with %s', 'linker-commerce' ), '' !== $model ? $model : $name ) ); ?></h2>
								</summary>
								<div class="pdp-project-check__body">
									<p><?php echo \esc_html__( 'New system, extension or replacement? Linker Advisor starts from this model and asks only for what is still open (existing model, quantity, postcode, installation date).', 'linker-commerce' ); ?></p>
									<div class="pdp-project-choices">
										<?php foreach ( array( 'new' => __( 'New system', 'linker-commerce' ), 'extension' => __( 'Extend an existing system', 'linker-commerce' ), 'replacement' => __( 'Replace an existing unit', 'linker-commerce' ) ) as $stage => $label ) : ?>
										<button type="button" class="pdp-project-choice" onclick="window.dispatchEvent(new CustomEvent('lia:ask',{detail:{message:'<?php echo \esc_js( self::project_check_prompt( $product, $stage ) ); ?>',trigger:this}}))"><?php echo \esc_html( $label ); ?></button>
										<?php endforeach; ?>
									</div>
									<p data-linker-project-product-feedback aria-live="polite"></p>
								</div>
							</details>
						</div>
					</aside>
					<div class="pdp-content">
						<?php if ( $nav ) : ?>
						<nav id="product-sections" class="pdp-section-nav" aria-label="<?php echo \esc_attr__( 'Product sections', 'linker-commerce' ); ?>">
							<?php foreach ( $nav as $item ) : ?>
							<a class="pdp-section-link" href="#<?php echo \esc_attr( (string) $item[0] ); ?>"><?php echo \esc_html( (string) $item[1] ); ?></a>
							<?php endforeach; ?>
						</nav>
						<?php endif; ?>
						<?php if ( $has_description ) : ?>
						<section id="description" class="pdp-block">
							<div class="pdp-overview">
								<div class="pdp-overview-copy">
									<p class="pdp-kicker"><?php echo \esc_html__( 'Description', 'linker-commerce' ); ?></p>
									<h2 class="pdp-section-title"><?php echo \esc_html( $desc_heading ); ?></h2>
									<?php if ( '' !== $intro ) : ?><div class="pdp-overview-intro pdp-reading"><?php echo self::paragraphs( $intro ); ?></div><?php endif; ?>
								</div>
								<?php if ( $desc_image ) : ?><img class="pdp-overview-image" src="<?php echo \esc_url( $desc_image ); ?>" alt="<?php echo \esc_attr( $name ); ?>" loading="lazy"><?php endif; ?>
							</div>
							<?php if ( $benefits ) : ?>
							<ul class="pdp-benefits">
								<?php foreach ( $benefits as $bullet ) :
									$split = \strpos( $bullet, ': ' );
									?>
								<li class="pdp-benefit"><?php echo self::icon( 'check' ); ?><div><?php
									if ( false !== $split && $split > 0 && $split < 110 ) {
										echo '<h3>' . \esc_html( \substr( $bullet, 0, $split ) ) . '</h3><p>' . \esc_html( \substr( $bullet, $split + 2 ) ) . '</p>';
									} else {
										echo '<p>' . \esc_html( $bullet ) . '</p>';
									}
								?></div></li>
								<?php endforeach; ?>
							</ul>
							<?php endif; ?>
							<?php
							$more_title = ( ! empty( $value['headline'] ) && ! empty( $details['title'] ) )
								? (string) $details['title']
								: __( 'More product details', 'linker-commerce' );
							$more_body = self::paragraphs( (string) ( $details['body'] ?? '' ) );
							$hair = array();
							foreach ( \is_array( $details['hairlines'] ?? null ) ? $details['hairlines'] : array() as $line ) {
								$line = \trim( (string) $line );
								if ( '' !== $line ) {
									$hair[] = $line;
								}
							}
							if ( $hair ) {
								$more_body .= '<ul>';
								foreach ( $hair as $line ) {
									$more_body .= '<li>' . \esc_html( $line ) . '</li>';
								}
								$more_body .= '</ul>';
							}
							if ( $desc_image_2_url ) {
								echo '<div class="pdp-overview pdp-overview-secondary pdp-block">';
								echo '<div class="pdp-overview-copy"><h3 class="pdp-section-title">' . \esc_html( $more_title ) . '</h3><div class="pdp-reading pdp-muted">' . $more_body . '</div></div>';
								echo '<img class="pdp-overview-image" src="' . \esc_url( $desc_image_2_url ) . '" alt="" loading="lazy">';
								echo '</div>';
							} elseif ( '' !== $more_body ) {
								echo self::disclosure( \esc_html( $more_title ), $more_body );
							}
							$highlights = array();
							foreach ( \is_array( $acf['official_highlights'] ?? null ) ? $acf['official_highlights'] : array() as $item ) {
								if ( \is_string( $item ) ) {
									$highlights[] = $item;
								} elseif ( \is_array( $item ) ) {
									$highlights[] = (string) ( $item['title'] ?? $item['text'] ?? '' );
								}
							}
							$highlights = \array_values( \array_filter( \array_map( 'trim', $highlights ) ) );
							if ( $highlights ) {
								$list = '<ul>';
								foreach ( $highlights as $item ) {
									$list .= '<li>' . \esc_html( $item ) . '</li>';
								}
								$list .= '</ul>';
								echo self::disclosure( \esc_html__( 'Product highlights', 'linker-commerce' ), $list );
							}
							?>
						</section>
						<?php endif; ?>

						<?php if ( $has_compare ) :
							$cmp_n = \count( $compare_cols );
							?>
						<section id="compare" class="pdp-family-comparison">
							<div class="pdp-family-head">
								<div>
									<?php if ( '' !== $series_name ) : ?><p class="pdp-kicker"><?php echo \esc_html( $series_name ); ?></p><?php endif; ?>
									<h2 class="pdp-section-title"><?php echo \esc_html__( 'Compare different models', 'linker-commerce' ); ?></h2>
								</div>
								<label class="pdp-diff"><input type="checkbox" data-family-diff> <?php echo \esc_html__( 'Show differences only', 'linker-commerce' ); ?></label>
							</div>
							<p class="pdp-comparison-hint"><?php echo \esc_html__( 'Scroll sideways to compare every model.', 'linker-commerce' ); ?></p>
							<div class="pdp-family-scroll" role="region" tabindex="0" aria-label="<?php echo \esc_attr__( 'Model comparison table', 'linker-commerce' ); ?>">
								<div class="pdp-family-grid" style="--cmp-cols: <?php echo \esc_attr( (string) $cmp_n ); ?>">
									<div class="pdp-family-row pdp-family-row--head">
										<div class="pdp-family-cell pdp-family-lab"><?php echo \esc_html( \sprintf( /* translators: %d: number of models in the comparison */ \_n( '%d model', '%d models', $cmp_n, 'linker-commerce' ), $cmp_n ) ); ?></div>
										<?php foreach ( $compare_cols as $col ) :
											$cid = (int) $col['id'];
											$cp = \wc_get_product( $cid );
											if ( ! $cp ) {
												continue;
											}
											$cur = $cid === $product_id;
											$cimg = \wp_get_attachment_image_url( $cp->get_image_id(), 'medium' );
											?>
										<div class="pdp-family-cell<?php echo $cur ? ' pdp-current-model' : ''; ?>">
											<?php if ( $cimg ) : ?><img class="pdp-family-fig" src="<?php echo \esc_url( (string) $cimg ); ?>" alt="" loading="lazy"><?php endif; ?>
											<a class="pdp-family-name" href="<?php echo \esc_url( (string) \get_permalink( $cid ) ); ?>"><?php echo \esc_html( self::display_name( $cp ) ); ?></a>
											<div class="pdp-model-status"><?php if ( $cur ) : ?><span class="pdp-pill"><?php echo \esc_html__( 'This model', 'linker-commerce' ); ?></span><?php endif; ?></div>
											<?php if ( $can_view_prices && '' !== $cp->get_price() ) : ?>
											<p class="pdp-family-price"><?php echo \wp_kses_post( \wc_price( (float) $cp->get_price() ) ); ?></p>
											<?php else : ?>
											<p class="pdp-doc-meta"><?php echo \esc_html( self::price_prompt_label() ); ?></p>
											<?php endif; ?>
											<?php if ( $can_view_prices && $cp->is_purchasable() && $cp->is_in_stock() && ! $this->state->is_rfq_only( $cp ) ) : ?>
											<a class="pdp-btn pdp-btn-dark pdp-family-add" href="<?php echo \esc_url( \add_query_arg( 'add-to-cart', $cid, $cart_url ) ); ?>"><?php echo \esc_html__( 'Add to cart', 'linker-commerce' ); ?></a>
											<?php else : ?>
											<span class="pdp-btn pdp-btn-off pdp-family-add" aria-disabled="true"><?php echo \esc_html( self::price_prompt_label() ); ?></span>
											<?php endif; ?>
										</div>
										<?php endforeach; ?>
									</div>
									<?php foreach ( $compare_keys as $key ) :
										$values = array();
										foreach ( $compare_cols as $col ) {
											$values[] = $compare_data[ (int) $col['id'] ][ $key ];
										}
										$same = \count( \array_unique( $values ) ) <= 1;
										?>
									<div class="pdp-family-row" data-same="<?php echo $same ? '1' : '0'; ?>">
										<div class="pdp-family-cell pdp-family-lab"><?php echo \esc_html( isset( $compare_labels[ $key ] ) && 1 === \count( $compare_labels[ $key ] )
											? (string) \key( $compare_labels[ $key ] )
											: LiveCatalog::key_label( $key ) ); ?></div>
										<?php foreach ( $compare_cols as $i => $col ) :
											$cid = (int) $col['id'];
											$val = $values[ $i ];
											?>
										<div class="pdp-family-cell<?php echo $cid === $product_id ? ' pdp-current-model' : ''; ?>"><?php echo '' === $val ? '<span class="pdp-gap">—</span>' : \esc_html( $val ); ?></div>
										<?php endforeach; ?>
									</div>
									<?php endforeach; ?>
								</div>
							</div>
							<?php if ( $has_specs ) : ?>
							<a class="pdp-inline-link" href="#stats"><?php echo \esc_html__( 'View full technical data', 'linker-commerce' ); ?><?php echo self::icon( 'arrow' ); ?></a>
							<?php endif; ?>
						</section>
						<?php endif; ?>
						<?php
						$feature_i = 0;
						foreach ( $feature_cards as $card ) {
							if ( ! \is_array( $card ) || '' === \trim( (string) ( $card['feature_title'] ?? '' ) ) ) {
								continue;
							}
							$img_id = (int) ( $card['feature_image'] ?? 0 );
							$img = $img_id ? \wp_get_attachment_image_url( $img_id, 'large' ) : '';
							$title = (string) $card['feature_title'];
							$body = self::paragraphs( (string) ( $card['feature_body'] ?? '' ) );
							if ( $img ) {
								$rev = $feature_i % 2 ? ' is-rev' : '';
								echo '<section class="pdp-feature' . $rev . '">';
								echo '<div class="pdp-feature-media"><img class="pdp-feature-image" src="' . \esc_url( $img ) . '" alt="' . \esc_attr( $title ) . '" loading="lazy"></div>';
								echo '<div class="pdp-feature-copy"><h3 class="pdp-section-title">' . \esc_html( $title ) . '</h3><div class="pdp-reading pdp-muted" style="margin-top:12px">' . $body . '</div></div>';
								echo '</section>';
								$feature_i++;
							} else {
								echo self::disclosure( \esc_html( $title ), $body );
							}
						}
						?>
						<?php if ( $has_specs ) : ?>
						<section id="stats" class="pdp-block">
							<h2 class="pdp-section-title"><?php echo \esc_html__( 'Technical data', 'linker-commerce' ); ?></h2>
							<?php if ( ! empty( $stats_claim['label'] ) ) : ?><p class="pdp-kicker" style="margin-top:12px"><?php echo \esc_html( (string) $stats_claim['label'] ); ?></p><?php endif; ?>
							<?php if ( ! empty( $stats_claim['title'] ) ) : ?><h3 class="pdp-section-title" style="margin-top:12px"><?php echo \esc_html( (string) $stats_claim['title'] ); ?></h3><?php endif; ?>
							<?php if ( ! empty( $stats_claim['body'] ) ) : ?><div class="pdp-reading pdp-muted" style="margin-top:12px"><?php echo self::paragraphs( (string) $stats_claim['body'] ); ?></div><?php endif; ?>
							<?php if ( ! empty( $stats_claim['cards'] ) && \is_array( $stats_claim['cards'] ) ) : ?>
							<dl class="pdp-stat-wrap">
								<?php foreach ( $stats_claim['cards'] as $card ) :
									if ( ! \is_array( $card ) ) { continue; }
									$cv = \trim( (string) ( $card['value'] ?? '' ) );
									$cl = \trim( (string) ( $card['label'] ?? '' ) );
									if ( '' === $cv || '' === $cl ) { continue; }
									?>
								<div class="pdp-stat-row"><dt><?php echo \esc_html( $cl ); ?></dt><dd><?php echo \esc_html( $cv ); ?></dd></div>
								<?php endforeach; ?>
							</dl>
							<?php endif; ?>
							<?php
							$group_i = 0;
							foreach ( $spec_groups as $group ) {
								if ( ! \is_array( $group ) ) {
									continue;
								}
								$rows = \is_array( $group['spec_rows'] ?? null ) ? $group['spec_rows'] : array();
								if ( ! $rows ) {
									continue;
								}
								$dl = '<dl class="pdp-stat-wrap">';
								foreach ( $rows as $row ) {
									$sv = (string) ( $row['spec_value'] ?? '' );
									$power = LiveCatalog::is_power_field( (string) ( $row['spec_label'] ?? '' ), (string) ( $row['spec_unit'] ?? '' ) );
									$sv = LiveCatalog::customer_power( $sv, $power );
									$sv = LiveCatalog::value_with_unit( $sv, LiveCatalog::unit_label( (string) ( $row['spec_unit'] ?? '' ) ) );
									$note = \trim( (string) ( $row['spec_note'] ?? '' ) );
									$note_html = '' !== $note
										? '<div class="pdp-reading pdp-muted">' . \esc_html( $note ) . '</div>'
										: '';
									$dl .= '<div class="pdp-stat-row"><dt>' . \esc_html( (string) ( $row['spec_label'] ?? '' ) ) . '</dt><dd>' . \esc_html( $sv ) . $note_html . '</dd></div>';
								}
								$dl .= '</dl>';
								echo self::disclosure( \esc_html( (string) ( $group['spec_group_title'] ?? \__( 'Specifications', 'linker-commerce' ) ) ), $dl, 0 === $group_i );
								$group_i++;
							}
							?>
						</section>
						<?php endif; ?>
						<?php echo self::scenario_section( $product, $acf, $scene_media ); ?>
						<?php if ( $has_docs ) : ?>
						<section id="downloads" class="pdp-block">
							<h2 class="pdp-section-title"><?php echo \esc_html__( 'Documents', 'linker-commerce' ); ?></h2>
							<?php
							foreach ( $documents as $doc ) :
								$url = (string) ( $doc['url'] ?? '' );
								if ( '' === $url ) {
									continue;
								}
								$kind_label = self::document_type_label( (string) ( $doc['kind'] ?? '' ) );
								$path = (string) ( \wp_parse_url( $url, \PHP_URL_PATH ) ?: '' );
								$ext = \strtoupper( (string) \pathinfo( $path, \PATHINFO_EXTENSION ) );
								$meta = \array_values( \array_filter( array(
									$kind_label,
									$ext,
									'MUL' === \strtoupper( (string) ( $doc['language'] ?? '' ) ) ? __( 'Multilingual', 'linker-commerce' ) : (string) ( $doc['language'] ?? '' ),
								) ) );
								?>
							<a class="pdp-doc" href="<?php echo \esc_url( $url ); ?>" target="_blank" rel="noopener">
								<span class="pdp-doc-icon"><?php echo self::icon( 'file' ); ?></span>
								<span class="grow"><?php echo \esc_html( (string) ( $doc['title'] ?? \__( 'Document', 'linker-commerce' ) ) ); ?>
									<?php if ( $meta ) : ?><span class="pdp-doc-meta"><?php echo \esc_html( \implode( ' · ', $meta ) ); ?></span><?php endif; ?>
								</span>
								<?php echo self::icon( 'download' ); ?>
							</a>
							<?php endforeach; ?>
						</section>
						<?php endif; ?>
						<?php
						$faq_items = array();
						foreach ( $faqs as $faq ) {
							if ( empty( $faq['faq_question'] ) ) {
								continue;
							}
							$answer = (string) ( $faq['faq_answer'] ?? '' );
							$item = self::disclosure( \esc_html( (string) $faq['faq_question'] ), self::paragraphs( $answer ) );
							if ( '' !== $item ) {
								$faq_items[] = $item;
							}
						}
						if ( $faq_items ) : ?>
						<section class="pdp-block pdp-faqs" data-faq-count="<?php echo (int) \count( $faq_items ); ?>">
							<h2 class="pdp-section-title"><?php echo \esc_html__( 'Product questions', 'linker-commerce' ); ?></h2>
							<?php echo \implode( '', $faq_items ); ?>
						</section>
						<?php endif; ?>
						<?php
						$system_labels = array(
							'required_bos' => __( 'Required components', 'linker-commerce' ),
							'recommended' => __( 'Recommended components', 'linker-commerce' ),
							'optional' => __( 'Optional components', 'linker-commerce' ),
						);
						$has_system = false;
						foreach ( $system_labels as $key => $label ) {
							if ( ! empty( $wits[ $key ] ) && \is_array( $wits[ $key ] ) ) {
								$has_system = true;
								break;
							}
						}
						if ( $has_system ) : ?>
						<section class="pdp-block">
							<h2 class="pdp-section-title"><?php echo \esc_html__( 'System components', 'linker-commerce' ); ?></h2>
							<?php foreach ( $system_labels as $key => $label ) :
								if ( empty( $wits[ $key ] ) || ! \is_array( $wits[ $key ] ) ) {
									continue;
								}
								$body = '';
								foreach ( $wits[ $key ] as $item ) {
									if ( ! \is_array( $item ) ) {
										$body .= self::paragraphs( (string) $item );
										continue;
									}
									$pid = isset( $item['product_id'] ) ? (int) $item['product_id'] : 0;
									if ( ! $pid && ! empty( $item['sku_ref'] ) ) {
										$pid = (int) \wc_get_product_id_by_sku( (string) $item['sku_ref'] );
									}
									if ( $pid && 'publish' !== \get_post_status( $pid ) ) {
										continue;
									}
									$body .= '<div class="pdp-comp-item">';
									$body .= '<p class="pdp-pairing-name">' . \esc_html( (string) ( $item['label'] ?? $item['title'] ?? $item['name'] ?? '' ) ) . '</p>';
									if ( ! empty( $item['sku_ref'] ) ) {
										$body .= '<p class="pdp-pairing-sku">' . \esc_html__( 'Item number', 'linker-commerce' ) . ': ' . \esc_html( (string) $item['sku_ref'] ) . '</p>';
									}
									if ( ! empty( $item['why'] ) ) {
										$body .= '<div class="pdp-reading">' . self::paragraphs( (string) $item['why'] ) . '</div>';
									}
									if ( $pid && 'publish' === \get_post_status( $pid ) ) {
										$body .= '<a class="pdp-inline-link" href="' . \esc_url( (string) \get_permalink( $pid ) ) . '">' . \esc_html__( 'View product', 'linker-commerce' ) . self::icon( 'arrow' ) . '</a>';
									}
									$body .= '</div>';
								}
								echo self::disclosure( \esc_html( $label ), $body );
							endforeach; ?>
						</section>
						<?php endif; ?>
						<?php echo self::pairings_section( $product_id ); ?>
						<?php
						$related_html = '';
						foreach ( $related_ids as $rid ) {
							$rp = \wc_get_product( $rid );
							if ( ! $rp || 'publish' !== $rp->get_status() ) {
								continue;
							}
							$related_html .= '<article><a href="' . \esc_url( (string) \get_permalink( $rid ) ) . '">';
							$rp_name = self::display_name( $rp );
							$related_html .= \wp_get_attachment_image( $rp->get_image_id(), 'medium', false, array( 'alt' => $rp_name, 'loading' => 'lazy' ) );
							$related_html .= '<p class="pdp-pairing-name" style="margin-top:8px">' . \esc_html( $rp_name ) . '</p>';
							$related_html .= '</a></article>';
						}
						if ( '' !== $related_html ) : ?>
						<section class="pdp-block">
							<h2 class="pdp-section-title"><?php echo \esc_html__( 'Related products', 'linker-commerce' ); ?></h2>
							<div class="pdp-related"><?php echo $related_html; ?></div>
						</section>
						<?php endif; ?>

					</div>
				</div>
			</div>
			<dialog id="pdp-image-viewer">
				<button type="button" class="pdp-viewer-close" data-pdp-close-image aria-label="<?php echo \esc_attr__( 'Close', 'linker-commerce' ); ?>">&times;</button>
				<img alt="">
				<p data-viewer-caption></p>
			</dialog>
		</div>
		<?php
		return (string) \ob_get_clean();
	}

	/**
	 * The compatibility records section: the pairing cards and their
	 * footnotes, from the registry's relationships and the contract's cells.
	 */
	public static function pairings_section( int $product_id ): string {
		$locale = LiveCatalog::locale();
		$cards  = array();
		foreach ( LiveCatalog::relationships( $product_id ) as $pt ) {
			$pid = isset( $pt['target_product_id'] ) ? (int) $pt['target_product_id'] : 0;
			$pp = $pid ? \wc_get_product( $pid ) : null;
			if ( ! $pp || 'publish' !== $pp->get_status() ) {
				continue;
			}
			$stack = '';
			if ( ! empty( $pt['stack_range'] ) && \is_array( $pt['stack_range'] ) && 2 === \count( $pt['stack_range'] ) ) {
				$stack = \esc_html( $pt['stack_range'][0] . '-' . $pt['stack_range'][1] . ' ' . LiveCatalog::unit_label( 'modules' ) );
			}
			$cell_id = LiveCatalog::relationship_cell_id( $pt );
			$cell    = '' !== $cell_id ? LiveCatalog::contract()['cells'][ $cell_id ] ?? null : null;
			$cards[] = \array_merge(
				array(
					'href' => \get_permalink( $pid ),
					'image' => \wp_get_attachment_image( $pp->get_image_id(), 'medium', false, array( 'alt' => self::display_name( $pp ), 'loading' => 'lazy' ) ),
					'name' => self::display_name( $pp ),
					'sku' => (string) $pp->get_sku(),
					'stack' => $stack,
					'status' => self::pairing_status( $pt, $locale ),
					'constraint' => LiveCatalog::localized_text( $pt, 'constraint', $locale ),
					'cell' => $cell_id,
					'cell_constraint' => \is_array( $cell ) ? LiveCatalog::localized_text( $cell, 'constraint', $locale ) : '',
				)
			);
		}
		\usort( $cards, static function ( $a, $b ) {
			return \strnatcasecmp( (string) $a['name'], (string) $b['name'] );
		} );
		if ( ! $cards ) {
			return '';
		}
		$html  = '<section class="pdp-block">';
		$html .= '<h2 class="pdp-section-title">' . \esc_html__( 'Compatibility records', 'linker-commerce' ) . '</h2>';
		$html .= self::pairings_html( $cards );
		$html .= '</section>';
		return $html;
	}

	/**
	 * The pairing card grids with their footnotes
	 * (tv_b2b_pdp_pairings_html).
	 *
	 * @param list<array<string, mixed>> $cards The cards.
	 */
	private static function pairings_html( array $cards ): string {
		$constraints = array();
		foreach ( $cards as $card ) {
			$constraints[] = (string) ( $card['constraint'] ?? '' );
		}
		$shared = self::shared_constraint( $constraints );
		$segments = array();
		if ( \is_string( $shared ) && '' !== $shared ) {
			$html = '';
			foreach ( $cards as $card ) {
				$html .= self::pairing_card( $card, '' );
			}
			$segments[] = array( 'cards' => $html, 'note' => $shared );
		} else {
			$rests = array();
			foreach ( $cards as $i => $card ) {
				$cell = (string) ( $card['cell'] ?? '' );
				$cell_text = \trim( (string) ( $card['cell_constraint'] ?? '' ) );
				$text = \trim( (string) ( $card['constraint'] ?? '' ) );
				if ( '' === $cell || '' === $cell_text ) {
					continue;
				}
				if ( $text === $cell_text ) {
					$rests[ $cell ][ $i ] = '';
				} elseif ( \str_starts_with( $text, $cell_text . ' ' ) ) {
					$rests[ $cell ][ $i ] = \trim( \substr( $text, \strlen( $cell_text ) ) );
				}
			}
			$placed = array();
			foreach ( $cards as $i => $card ) {
				$cell = (string) ( $card['cell'] ?? '' );
				if ( isset( $rests[ $cell ][ $i ] ) && \count( $rests[ $cell ] ) > 1 ) {
					if ( isset( $placed[ $cell ] ) ) {
						continue;
					}
					$placed[ $cell ] = true;
					$html = '';
					$notes = array( \trim( (string) $cards[ $i ]['cell_constraint'] ) );
					foreach ( $rests[ $cell ] as $j => $rest ) {
						$html .= self::pairing_card( $cards[ $j ], '' );
						if ( '' !== $rest && ! \in_array( $rest, $notes, true ) ) {
							$notes[] = $rest;
						}
					}
					$segments[] = array( 'cards' => $html, 'note' => \implode( ' ', $notes ) );
					continue;
				}
				$html = self::pairing_card( $card, self::paragraphs( (string) ( $card['constraint'] ?? '' ) ) );
				$last = \count( $segments ) - 1;
				if ( $last >= 0 && '' === $segments[ $last ]['note'] ) {
					$segments[ $last ]['cards'] .= $html;
				} else {
					$segments[] = array( 'cards' => $html, 'note' => '' );
				}
			}
		}
		$html = '';
		foreach ( $segments as $segment ) {
			$html .= '<div class="pdp-pairings">' . $segment['cards'] . '</div>';
			$note = self::paragraphs( $segment['note'] );
			if ( '' !== $note ) {
				$html .= '<div class="pdp-pairing-footnote pdp-reading pdp-muted">' . $note . '</div>';
			}
		}
		return $html;
	}

	/**
	 * One pairing card (tv_b2b_pdp_pairing_card).
	 */
	private static function pairing_card( array $card, string $constraint_html ): string {
		$html = '<a class="pdp-pairing" href="' . \esc_url( (string) ( $card['href'] ?? '' ) ) . '">';
		$image = (string) ( $card['image'] ?? '' );
		$html .= '' !== $image ? $image : '<span class="pdp-empty-visual"></span>';
		$html .= '<span class="pdp-pairing-copy">';
		$html .= '<span class="pdp-pairing-name">' . \esc_html( (string) ( $card['name'] ?? '' ) ) . '</span>';
		$sku = \trim( (string) ( $card['sku'] ?? '' ) );
		if ( '' !== $sku ) {
			$html .= '<span class="pdp-pairing-sku">' . \esc_html__( 'Item number', 'linker-commerce' ) . ' ' . \esc_html( $sku ) . '</span>';
		}
		$status = (string) ( $card['status'] ?? '' );
		$stack = (string) ( $card['stack'] ?? '' );
		if ( '' !== $status || '' !== $stack ) {
			$html .= '<span class="pdp-pairing-chips">';
			if ( '' !== $status ) {
				$html .= '<span class="pdp-doc-meta">' . $status . '</span>';
			}
			if ( '' !== $stack ) {
				$html .= '<span class="pdp-doc-meta">' . $stack . '</span>';
			}
			$html .= '</span>';
		}
		if ( '' !== $constraint_html ) {
			$html .= '<div class="pdp-pairing-note pdp-reading pdp-muted">' . $constraint_html . '</div>';
		}
		$html .= '</span></a>';
		return $html;
	}

	/**
	 * The constraint every card shares, null when they differ.
	 */
	private static function shared_constraint( array $constraints ): ?string {
		$shared = null;
		foreach ( $constraints as $text ) {
			$text = \trim( (string) $text );
			if ( null === $shared ) {
				$shared = $text;
				continue;
			}
			if ( $text !== $shared ) {
				return null;
			}
		}
		return null === $shared ? '' : $shared;
	}

	/**
	 * A compatibility card's status chip (tv_b2b_pdp_pairing_status).
	 */
	private static function pairing_status( array $pt, string $locale ): string {
		if ( ( $pt['status'] ?? '' ) === 'listed' ) {
			$by = $pt['listed_by'] ?? null;
			return null === $by
				? \esc_html__( 'On the compatibility list on file', 'linker-commerce' )
				: \esc_html( \sprintf( /* translators: %s: manufacturer */ \__( "On %s's compatibility list", 'linker-commerce' ), (string) $by ) );
		}
		$sides = LiveCatalog::one_way_documents( $pt );
		if ( null !== $sides ) {
			$listing = LiveCatalog::document_names( $sides['listing'], $locale );
			$absent = LiveCatalog::document_names( $sides['not_listing'], $locale );
			if ( $listing && $absent ) {
				return \esc_html( \sprintf(
					/* translators: 1: document(s) that list the pair, 2: document(s) of the same manufacturer that do not */
					\__( 'Listed only in the %1$s; not in the %2$s', 'linker-commerce' ),
					\implode( ', ', $listing ),
					\implode( ', ', $absent )
				) );
			}
		}
		$only = (string) ( $pt['listed_by'] ?? '' );
		return '' === $only
			? \esc_html__( 'Listed on one side only', 'linker-commerce' )
			: \esc_html( \sprintf( /* translators: %s: manufacturer */ \__( 'Listed by %s only', 'linker-commerce' ), $only ) );
	}

	/**
	 * The scenario section (product-scenarios.php's rows and markup).
	 *
	 * @param WC_Product           $product The product.
	 * @param array<string, mixed> $acf The ACF JSON.
	 * @param list<array<string, mixed>> $scene_media The non-product gallery rows.
	 */
	private static function scenario_section( WC_Product $product, array $acf, array $scene_media ): string {
		$rows = self::scenario_rows( $acf );
		if ( $rows ) {
			$html = '<section id="fit" class="pdp-block"><h2 class="pdp-section-title">' . \esc_html__( 'Applications', 'linker-commerce' ) . '</h2>';
			foreach ( $rows as $row ) {
				$body = '';
				if ( '' !== (string) ( $row['situation'] ?? '' ) ) {
					$body .= self::paragraphs( (string) $row['situation'] );
				}
				if ( '' !== (string) ( $row['fit'] ?? '' ) ) {
					$body .= $body === '' ? '' : '';
					$body .= '<p>' . \esc_html( (string) $row['fit'] ) . '</p>';
				}
				if ( ! empty( $row['checklist'] ) ) {
					$body .= '<ul>';
					foreach ( $row['checklist'] as $check ) {
						$body .= '<li>' . \esc_html( (string) $check ) . '</li>';
					}
					$body .= '</ul>';
				}
				if ( '' !== (string) ( $row['verdict'] ?? '' ) ) {
					$body .= '<p>' . \esc_html( (string) $row['verdict'] ) . '</p>';
				}
				$html .= self::disclosure( \esc_html( (string) $row['title'] ), $body, false );
			}
			$html .= '</section>';
			return $html;
		}
		if ( ! $scene_media ) {
			return '';
		}
		$html = '<section id="fit" class="pdp-block"><h2 class="pdp-section-title">' . \esc_html__( 'Applications', 'linker-commerce' ) . '</h2><div class="pdp-scene-reel">';
		foreach ( $scene_media as $row ) {
			$gid = (int) ( $row['gallery_image'] ?? 0 );
			if ( ! $gid ) {
				continue;
			}
			$caption = (string) ( $row['gallery_caption'] ?? '' );
			$html .= '<figure class="pdp-scene-card">';
			$html .= \wp_get_attachment_image( $gid, 'large', false, array( 'loading' => 'lazy', 'alt' => $caption ) );
			$html .= '<figcaption><span class="pdp-kicker">' . \esc_html( $caption ) . '</span></figcaption>';
			$html .= '</figure>';
		}
		$html .= '</div></section>';
		return $html;
	}

	/**
	 * The scenario rows of the ACF JSON (tv_b2b_scenario_rows): the rich
	 * shape (situation, fit, checklist, verdict) and the plain one (body).
	 *
	 * @param array<string, mixed> $acf The ACF JSON.
	 * @return list<array<string, mixed>>
	 */
	private static function scenario_rows( array $acf ): array {
		$rows = \is_array( $acf['application_scenarios'] ?? null ) ? $acf['application_scenarios'] : array();
		$parsed = array();
		foreach ( $rows as $row ) {
			if ( ! \is_array( $row ) || ! isset( $row['scenario_title'] ) ) {
				continue;
			}
			$checks = \array_values( \array_filter( \array_map(
				static fn( $check ): string => \is_array( $check ) ? \trim( (string) ( $check['check_text'] ?? '' ) ) : \trim( (string) $check ),
				\is_array( $row['scenario_checklist'] ?? null ) ? $row['scenario_checklist'] : array()
			) ) );
			$parsed[] = array(
				'title' => (string) $row['scenario_title'],
				'situation' => (string) ( $row['scenario_situation'] ?? '' ),
				'fit' => (string) ( $row['scenario_fit'] ?? '' ),
				'verdict' => (string) ( $row['scenario_verdict'] ?? '' ),
				'checklist' => $checks,
				'image' => (int) ( $row['scenario_image'] ?? 0 ),
			);
		}
		return $parsed;
	}

	/**
	 * The family articles of a product (tv_woo_b2b_family_articles).
	 *
	 * @return list<array{id: int, label: string, sku: string, url: string, current: bool}>
	 */
	private static function family_articles( WC_Product $product ): array {
		$current_id = (int) $product->get_id();
		$acf        = LiveCatalog::acf( $current_id );
		$variants   = \is_array( $acf['family_variants'] ?? null ) ? $acf['family_variants'] : array();
		$ids        = array();
		$has_current = false;
		foreach ( $variants as $variant ) {
			$variant_id = (int) ( $variant['id'] ?? 0 );
			if ( ! $variant_id ) {
				continue;
			}
			if ( $variant_id === $current_id ) {
				$ids[] = $variant_id;
				$has_current = true;
				continue;
			}
			if ( 'publish' !== \get_post_status( $variant_id ) ) {
				continue;
			}
			$ids[] = $variant_id;
		}
		if ( ! $has_current ) {
			\array_unshift( $ids, $current_id );
		}
		$ids = \array_values( \array_unique( $ids ) );
		$rows = array();
		foreach ( $ids as $id ) {
			$item = ( (int) $id === $current_id ) ? $product : \wc_get_product( $id );
			if ( ! $item instanceof WC_Product ) {
				continue;
			}
			$identity = LiveCatalog::identity( $item );
			$label = \trim( (string) $identity['model'] );
			if ( '' === $label ) {
				$label = (string) $item->get_name();
			}
			$rows[] = array(
				'id' => (int) $id,
				'label' => $label,
				'sku' => (string) $item->get_sku(),
				'url' => (string) \get_permalink( $id ),
				'current' => ( (int) $id === $current_id ),
			);
		}
		return $rows;
	}

	/**
	 * The comparison columns: the current product first
	 * (tv_woo_b2b_family_compare_columns).
	 */
	private static function family_compare_columns( array $rows, int $current_id ): array {
		$lead = array();
		$rest = array();
		foreach ( $rows as $row ) {
			if ( (int) ( $row['id'] ?? 0 ) === $current_id ) {
				$lead[] = $row;
			} else {
				$rest[] = $row;
			}
		}
		return \array_values( \array_merge( $lead, $rest ) );
	}

	/**
	 * The spec keys a product type's buy box and comparison read
	 * (tv_woo_b2b_pdp_keys).
	 *
	 * @return list<string>
	 */
	private static function pdp_keys( string $type ): array {
		$sets = array(
			'inverter'  => array( 'ac_power', 'phase', 'mppt', 'efficiency', 'batt_voltage', 'ip', 'weight', 'dimensions' ),
			'system'    => array( 'ac_power', 'nominal_kwh', 'phase', 'chemistry', 'ip', 'temp', 'weight', 'dimensions' ),
			'battery'   => array( 'usable_kwh', 'nominal_kwh', 'nom_voltage', 'chemistry', 'charge_a', 'discharge_a', 'ip', 'weight' ),
			'meter'     => array( 'accuracy', 'ratio', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'ct'        => array( 'ratio', 'accuracy', 'burden', 'temp', 'weight', 'dimensions' ),
			'ems'       => array( 'devices', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'accessory' => array( 'ac_power', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
			'other'     => array( 'nom_voltage', 'interface', 'ip', 'temp', 'weight', 'dimensions' ),
		);
		return $sets[ $type ] ?? $sets['other'];
	}

	/**
	 * The product's display name in the page's language.
	 */
	public static function display_name( WC_Product $product ): string {
		$name = \trim( (string) $product->get_name() );
		return \html_entity_decode( $name, \ENT_QUOTES | \ENT_HTML5, 'UTF-8' );
	}

	/**
	 * What the product name says besides brand and model
	 * (tv_b2b_pdp_designation).
	 */
	public static function designation( string $name, string $brand, string $model ): string {
		$designation = \preg_replace( '/\(\s*\)/u', '', \str_replace( array( (string) $brand, (string) $model ), '', (string) $name ) );
		$designation = \trim( (string) \preg_replace( '/\s+/u', ' ', (string) $designation ), " \t\n·–-" );
		if ( \preg_match( '/^\((.*)\)$/u', (string) $designation, $wrapped ) && \strpos( $wrapped[1], '(' ) === false ) {
			$designation = \trim( $wrapped[1] );
		}
		return self::initial_cap( (string) $designation );
	}

	/**
	 * A string with its first character uppercased.
	 */
	private static function initial_cap( string $text ): string {
		$first = \mb_substr( $text, 0, 1 );
		return '' === $text ? $text : \mb_strtoupper( $first ) . \mb_substr( $text, 1 );
	}

	/**
	 * The icons of the product page (tv_b2b_pdp_icon).
	 */
	public static function icon( string $name ): string {
		$shapes = array(
			'arrow' => '<path d="M5 12h14m-6-6 6 6-6 6"/>',
			'chevron' => '<path d="m6 9 6 6 6-6"/>',
			'check' => '<path d="m5 12 4 4L19 6"/>',
			'close' => '<path d="m6 6 12 12M6 18 18 6"/>',
			'file' => '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8ZM14 2v6h6M8 13h8M8 17h6"/>',
			'plus' => '<path d="M12 5v14M5 12h14"/>',
			'minus' => '<path d="M5 12h14"/>',
			'download' => '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
			'compare' => '<path d="M5 4v16M12 4v16M19 4v16M3 8h4M10 15h4M17 10h4"/>',
			'ask' => '<path d="M21 15a4 4 0 0 1-4 4H8l-5 4V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>',
		);
		$path = $shapes[ $name ] ?? $shapes['file'];
		return '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' . $path . '</svg>';
	}

	/**
	 * The symbol above a key figure on the phone first screen
	 * (tv_b2b_pdp_stat_icon).
	 */
	private static function stat_icon( string $key ): string {
		$shapes = array(
			'power' => '<path d="m13 2-8 12h6l-1 8 9-12h-6z"/>',
			'grid' => '<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>',
			'energy' => '<rect x="3" y="6" width="17" height="12" rx="3"/><path d="M22 10v4M7 10v4m4-4v4m4-4v4"/>',
			'gauge' => '<path d="M4 18a9 9 0 1 1 16 0M12 12l5-5M5 18h14"/>',
		);
		$by_key = array(
			'phase' => 'grid', 'mppt' => 'grid',
			'usable_kwh' => 'energy', 'nominal_kwh' => 'energy',
			'efficiency' => 'gauge',
		);
		$shape = $shapes[ $by_key[ $key ] ?? 'power' ];
		return '<span class="pdp-app-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' . $shape . '</svg></span>';
	}

	/**
	 * Text as the page prints saved HTML: paragraphs from blank-line splits,
	 * saved markup cleaned and closed (tv_b2b_pdp_paragraphs).
	 */
	public static function paragraphs( string $text ): string {
		$text = \trim( $text );
		if ( '' === $text ) {
			return '';
		}
		if ( \preg_match( '/<(?=[A-Za-z!]|\\/)/', $text ) ) {
			return self::close_open_tags( (string) \wp_kses( $text, self::kses_tags() ) );
		}
		$parts = \preg_split( "/\n\s*\n/", $text );
		$html = '';
		foreach ( \is_array( $parts ) ? $parts : array() as $part ) {
			$part = \trim( $part );
			if ( '' === $part ) {
				continue;
			}
			$html .= '<p>' . \nl2br( \esc_html( $part ), false ) . '</p>';
		}
		return $html;
	}

	/**
	 * The tags saved product text may carry (tv_b2b_pdp_kses_tags).
	 *
	 * @return array<string, array<string>>
	 */
	private static function kses_tags(): array {
		return array(
			'p' => array(), 'ul' => array(), 'ol' => array(), 'li' => array(),
			'strong' => array(), 'b' => array(), 'em' => array(), 'br' => array(),
			'h4' => array(), 'table' => array(), 'thead' => array(), 'tbody' => array(),
			'tr' => array(), 'th' => array(), 'td' => array(), 'blockquote' => array(),
		);
	}

	/**
	 * Closes the tags a truncated HTML fragment left open
	 * (tv_b2b_pdp_close_open_tags).
	 */
	private static function close_open_tags( string $html ): string {
		$void = array( 'br' => true );
		$stack = array();
		$out = '';
		$len = \strlen( $html );
		$i = 0;
		while ( $i < $len ) {
			if ( '<' !== $html[ $i ] ) {
				$out .= $html[ $i ];
				$i++;
				continue;
			}
			if ( '<!--' === \substr( $html, $i, 4 ) ) {
				$end = \strpos( $html, '-->', $i + 4 );
				if ( false === $end ) {
					$out .= \substr( $html, $i );
					break;
				}
				$end += 3;
				$out .= \substr( $html, $i, $end - $i );
				$i = $end;
				continue;
			}
			$end = \strpos( $html, '>', $i );
			if ( false === $end ) {
				$out .= \substr( $html, $i );
				break;
			}
			$raw = \substr( $html, $i, $end - $i + 1 );
			$i = $end + 1;
			if ( ! \preg_match( '/^<\/?([A-Za-z][A-Za-z0-9]*)\b/', $raw, $m ) ) {
				$out .= $raw;
				continue;
			}
			$name = \strtolower( $m[1] );
			$is_close = isset( $raw[1] ) && '/' === $raw[1];
			if ( isset( $void[ $name ] ) || \preg_match( '#/\s*>$#', $raw ) ) {
				$out .= $raw;
				continue;
			}
			if ( $is_close ) {
				$found = null;
				for ( $j = \count( $stack ) - 1; $j >= 0; $j-- ) {
					if ( $stack[ $j ] === $name ) {
						$found = $j;
						break;
					}
				}
				if ( null === $found ) {
					$out .= $raw;
					continue;
				}
				while ( \count( $stack ) - 1 > $found ) {
					$out .= '</' . \array_pop( $stack ) . '>';
				}
				\array_pop( $stack );
				$out .= $raw;
				continue;
			}
			$stack[] = $name;
			$out .= $raw;
		}
		while ( $stack ) {
			$out .= '</' . \array_pop( $stack ) . '>';
		}
		return $out;
	}

	/**
	 * A collapsible disclosure (tv_b2b_pdp_disclosure).
	 */
	public static function disclosure( string $title, string $body, bool $open = false ): string {
		if ( '' === \trim( \wp_strip_all_tags( $body ) ) ) {
			return '';
		}
		return '<details class="pdp-disclose"' . ( $open ? ' open' : '' ) . '>'
			. '<summary>' . $title . self::icon( 'chevron' ) . '</summary>'
			. '<div class="pdp-disclose-body pdp-reading">' . $body . '</div>'
			. '</details>';
	}

	/**
	 * A spec row's value with its figures in the page's decimal style
	 * (tv_woo_b2b_spec_figures).
	 */
	private static function spec_figures( array $row ): string {
		$text = (string) ( $row['card'] ?? '' );
		if ( ! empty( $row['localised'] ) ) {
			return $text;
		}
		$de = LiveCatalog::locale() === 'de';
		if ( ! $de ) {
			return $text;
		}
		return (string) \preg_replace_callback(
			'/(\d+)\.(\d+)/',
			static fn( $m ): string => $m[1] . ',' . $m[2],
			$text
		);
	}

	/**
	 * The document kind's label (tv_b2b_pdp_document_type_label).
	 */
	private static function document_type_label( string $kind ): string {
		switch ( $kind ) {
			case 'datasheet':
				return __( 'Datasheet', 'linker-commerce' );
			case 'manual':
				return __( 'Manual', 'linker-commerce' );
			case 'warranty':
				return __( 'Warranty', 'linker-commerce' );
			case 'certificate':
				return __( 'Certificate', 'linker-commerce' );
			case 'compatibility':
				return __( 'Compatibility list', 'linker-commerce' );
			case 'document':
				return __( 'Document', 'linker-commerce' );
		}
		return '';
	}

	/**
	 * The account URL with the return to this product.
	 */
	private static function account_url( WC_Product $product ): string {
		$url = (string) \wc_get_page_permalink( 'myaccount' );
		return \add_query_arg( 'redirect_to', (string) \get_permalink( (int) $product->get_id() ), $url );
	}

	/**
	 * The price prompt's label by variant (tv_b2b_price_prompt_label).
	 */
	private static function price_prompt_label( string $variant = 'default' ): string {
		$signed_in = \is_user_logged_in();
		switch ( $variant ) {
			case 'pdp':
				return $signed_in
					? __( 'Net price after account review', 'linker-commerce' )
					: __( 'Net price after partner sign-in', 'linker-commerce' );
			case 'cta':
				return $signed_in
					? __( 'Account under review — view status', 'linker-commerce' )
					: __( 'Sign in for partner pricing', 'linker-commerce' );
			default:
				return $signed_in
					? __( 'Net prices after account review', 'linker-commerce' )
					: __( 'Log in for pricing', 'linker-commerce' );
		}
	}

	/**
	 * The commerce state's label (tv_woo_b2b_state_label).
	 */
	private static function state_label( WC_Product $product ): string {
		$de = LiveCatalog::locale() === 'de';
		if ( $this->state->is_rfq_only( $product ) ) {
			return $de ? 'Online nicht bestellbar' : 'Not available online';
		}
		if ( '' === $product->get_price() ) {
			return $de ? 'Nettopreis noch nicht veröffentlicht' : 'Net price not published';
		}
		if ( ! $product->is_in_stock() ) {
			return $de ? 'Auf Anfrage' : 'On request';
		}
		return $de ? 'Nicht verfügbar' : 'Unavailable';
	}

	/**
	 * The "ask about this product" button's attributes
	 * (tv_b2b_contact_entry_attributes for the product context).
	 */
	private static function contact_entry_attributes( WC_Product $product ): string {
		$product_id = (int) $product->get_id();
		$context    = array(
			'intent' => 'product',
			'kind' => 'product',
			'title' => self::display_name( $product ),
			'source_id' => (string) $product_id,
			'product_id' => $product_id,
			'url' => (string) \get_permalink( $product_id ),
		);
		$args = array( 'intent' => (string) $context['intent'] );
		foreach ( array( 'kind', 'title', 'source_id', 'product_id' ) as $key ) {
			if ( isset( $context[ $key ] ) && \is_scalar( $context[ $key ] ) ) {
				$args[ $key ] = (string) $context[ $key ];
			}
		}
		$args['source'] = (string) $context['url'];
		$contact = (string) \get_permalink( \get_page_by_path( 'contact' ) );
		if ( '' === $contact ) {
			$contact = \home_url( '/contact/' );
		}
		return 'href="' . \esc_url( \add_query_arg( \array_map( 'rawurlencode', $args ), $contact ) ) . '" data-linker-contact="'
			. \esc_attr( (string) \wp_json_encode( $context, \JSON_UNESCAPED_UNICODE | \JSON_UNESCAPED_SLASHES ) ) . '"';
	}

	/**
	 * The hidden compare chip (tv_b2b_compare_chip_html).
	 */
	private static function compare_chip_html(): string {
		$label = \esc_html__( 'Compare', 'linker-commerce' );
		$page = \get_page_by_path( 'compare-products' );
		$url = $page ? (string) \get_permalink( (int) $page->ID ) : \home_url( '/compare-products/' );
		$url = \trailingslashit( (string) \preg_replace( '#\?.*$#', '', $url ) );
		return '<a class="sf-compare-chip" id="compare-chip" hidden href="' . \esc_url( $url ) . '" aria-label="' . \esc_attr__( 'Compare', 'linker-commerce' ) . '">'
			. self::icon( 'compare' )
			. '<span class="sf-compare-chip-label">' . $label . '</span>'
			. ' <span class="sf-compare-chip-n" data-compare-count>0</span>'
			. '</a>';
	}

	/**
	 * The prompt the assistant button dispatches
	 * (tv_woo_b2b_article_question_prompt).
	 */
	private static function article_question_prompt( WC_Product $product ): string {
		$name = self::display_name( $product );
		$sku = \trim( (string) $product->get_sku() );
		$article = $name . ( '' !== $sku ? ' (' . $sku . ')' : '' );
		return \sprintf(
			/* translators: %s is an Article name followed by its Item number in brackets, e.g. "SAJ H2 (DLK-INV-0042)". */
			__( 'About the %s: give me the key specs, which batteries or inverters it pairs with, and whether it fits my project.', 'linker-commerce' ),
			$article
		);
	}

	/**
	 * The prompt a project-check choice dispatches
	 * (tv_woo_b2b_project_check_prompt).
	 */
	private static function project_check_prompt( WC_Product $product, string $stage ): string {
		$de = LiveCatalog::locale() === 'de';
		$name = self::display_name( $product );
		$sku = \trim( (string) $product->get_sku() );
		$article = $name . ( '' !== $sku ? ' (' . $sku . ')' : '' );
		$stage = \in_array( $stage, array( 'new', 'extension', 'replacement' ), true ) ? $stage : '';
		if ( $de ) {
			$stage_text = array(
				'new' => 'Ich plane ein neues System',
				'extension' => 'Ich erweitere ein bestehendes System',
				'replacement' => 'Ich ersetze ein Gerät in einem bestehenden System',
			);
			$start = '' !== $stage
				? $stage_text[ $stage ] . ' mit ' . $article . '.'
				: 'Ich plane mit ' . $article . '. Frage zuerst, ob es um ein neues System, eine Erweiterung oder einen Austausch geht.';
			return $start . ' Frage danach immer nur nach der nächsten fehlenden Angabe (Bestandsmodell, Menge, Installations-PLZ, Montagetermin) und prüfe Kompatibilität, fehlende Systemkomponenten und Lieferfenster anhand aktueller Linker-Daten.';
		}
		$stage_text = array(
			'new' => 'I am planning a new system',
			'extension' => 'I am extending an existing system',
			'replacement' => 'I am replacing a unit in an existing system',
		);
		$start = '' !== $stage
			? $stage_text[ $stage ] . ' with ' . $article . '.'
			: 'I am planning with ' . $article . '. First ask whether this is a new system, an extension or a replacement.';
		return $start . ' Then ask one question at a time for what you still need (existing model, quantity, installation postcode, installation date) and check compatibility, missing system components and delivery windows against current Linker data.';
	}
}
