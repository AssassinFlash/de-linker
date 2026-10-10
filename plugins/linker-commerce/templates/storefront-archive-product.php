<?php
/**
 * The product archive template: the shop page and the product categories
 * (#12, docs/specs/12-site-chrome.md item 5). The rail's facets and the
 * cards' data derive from the selection facts (#7); the layout is the
 * catalogue the site serves today.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

get_header();

$filters  = new Linker\Commerce\Storefront\CatalogFilters();
$view     = new Linker\Commerce\Storefront\ProductView();
$products = array();

if ( have_posts() ) {
	while ( have_posts() ) {
		the_post();
		$products[] = get_the_ID();
	}
}

$facets     = $filters->facet_counts( $filters->archive_product_ids() );
$selected   = $filters->requested();
$sort       = $filters->requested_sort();
$queried    = get_queried_object();
$selected_n = count( $selected );

/**
 * A filter link: the current request's address with one facet set.
 *
 * @param string $facet The facet's query parameter.
 * @param string $value The facet's value.
 */
function linker_filter_url( string $facet, string $value ): string {
	// phpcs:ignore WordPress.Security.NonceVerification.Recommended -- plain GET navigation.
	$params = wp_unslash( $_GET );
	unset( $params[ $facet ], $params['sort'] );
	$params[ $facet ] = $value;
	return add_query_arg( $params );
}

$sort_labels = array(
	'recommended' => __( 'Recommended', 'linker-commerce' ),
	'newest'      => __( 'Newest first', 'linker-commerce' ),
	'name'        => __( 'Name A-Z', 'linker-commerce' ),
	'power-desc'  => __( 'Power high-low', 'linker-commerce' ),
	'power-asc'   => __( 'Power low-high', 'linker-commerce' ),
);
?>
<div id="tv-woo-b2b-catalog" class="sf-catalog">
	<section class="catalog-section">
		<div class="container catalog-layout">
			<aside class="sidebar-filters" id="sidebar-filters" data-linker-catalog-filter aria-label="<?php esc_attr_e( 'Product filters', 'linker-commerce' ); ?>">
				<button type="button" class="catalog-filter-close" id="catalog-filter-close" aria-label="<?php esc_attr_e( 'Close filters', 'linker-commerce' ); ?>">&times;</button>
				<details class="rail-fold" open>
					<summary class="rail-summary"><span><?php echo esc_html( sprintf( /* translators: %d: number of selected filters. */ _n( 'Filters (%d)', 'Filters (%d)', $selected_n, 'linker-commerce' ), $selected_n ) ); ?></span><span class="rail-summary-mark" aria-hidden="true"></span></summary>
					<div class="rail-body">
						<div class="rail-head"><span class="rail-head-label"><?php esc_html_e( 'Filters', 'linker-commerce' ); ?></span></div>

						<?php
						$categories = get_terms(
							array(
								'taxonomy'   => 'product_cat',
								'hide_empty' => true,
								'parent'     => 0,
								'exclude'    => array( (int) get_option( 'default_product_cat' ) ),
							)
						);
						?>
						<?php if ( \is_array( $categories ) && $categories ) : ?>
							<details class="filter-section fgroup rail-nav" open>
								<summary class="filter-title"><?php esc_html_e( 'Category', 'linker-commerce' ); ?></summary>
								<div class="filter-options">
									<a class="family-link" href="<?php echo esc_url( (string) wc_get_page_permalink( 'shop' ) ); ?>"><span><?php esc_html_e( 'All products', 'linker-commerce' ); ?></span></a>
									<?php foreach ( $categories as $category ) : ?>
										<a class="family-link<?php echo $queried instanceof WP_Term && $queried->term_id === $category->term_id ? ' is-current' : ''; ?>" href="<?php echo esc_url( (string) get_term_link( $category ) ); ?>"<?php echo $queried instanceof WP_Term && $queried->term_id === $category->term_id ? ' aria-current="page"' : ''; ?>><span><?php echo esc_html( $category->name ); ?></span></a>
									<?php endforeach; ?>
								</div>
							</details>
						<?php endif; ?>

						<?php
						foreach ( array(
							'application' => __( 'Application', 'linker-commerce' ),
							'brand'       => __( 'Brand', 'linker-commerce' ),
							'phase'       => __( 'Phase', 'linker-commerce' ),
							'power'       => __( 'Power', 'linker-commerce' ),
						) as $facet => $facet_title ) :
							?>
							<?php
							if ( empty( $facets[ $facet ] ) ) {
								continue; }
							?>
							<details class="filter-section fgroup<?php echo 'power' === $facet ? ' rail-pills' : ''; ?>" open>
								<summary class="filter-title"><?php echo esc_html( $facet_title ); ?></summary>
								<div class="filter-options">
									<?php foreach ( $facets[ $facet ] as $value => $option ) : ?>
										<?php if ( $option['count'] > 0 ) : ?>
											<a class="filter-option<?php echo isset( $selected[ $facet ] ) && $selected[ $facet ] === (string) $value ? ' active' : ''; ?>" href="<?php echo esc_url( linker_filter_url( $facet, (string) $value ) ); ?>" rel="nofollow">
												<span class="filter-checkbox-wrap"><span class="filter-checkbox"></span><span><?php echo esc_html( $option['label'] ); ?></span></span>
												<span class="filter-count"><?php echo esc_html( (string) $option['count'] ); ?></span>
											</a>
										<?php else : ?>
											<span class="filter-option is-disabled" aria-disabled="true">
												<span class="filter-checkbox-wrap"><span class="filter-checkbox"></span><span><?php echo esc_html( $option['label'] ); ?></span></span>
												<span class="filter-count">0</span>
											</span>
										<?php endif; ?>
									<?php endforeach; ?>
								</div>
							</details>
						<?php endforeach; ?>

						<details class="filter-section fgroup" open>
							<summary class="filter-title"><?php esc_html_e( 'AC power', 'linker-commerce' ); ?></summary>
							<div class="filter-options">
								<form class="frange" method="get" action="">
									<?php foreach ( $selected as $key => $value ) : ?>
										<input type="hidden" name="<?php echo esc_attr( (string) $key ); ?>" value="<?php echo esc_attr( (string) $value ); ?>" />
									<?php endforeach; ?>

									<span class="frange-row">
										<input type="number" name="kw_min" inputmode="decimal" step="0.1" min="0" placeholder="min" value="<?php echo esc_attr( (string) ( $selected['kw_min'] ?? '' ) ); ?>" aria-label="<?php esc_attr_e( 'Minimum AC power in kilowatts', 'linker-commerce' ); ?>" /><i>&ndash;</i>
										<input type="number" name="kw_max" inputmode="decimal" step="0.1" min="0" placeholder="max" value="<?php echo esc_attr( (string) ( $selected['kw_max'] ?? '' ) ); ?>" aria-label="<?php esc_attr_e( 'Maximum AC power in kilowatts', 'linker-commerce' ); ?>" /><b>kW</b>
										<button type="submit" class="frange-go"><?php esc_html_e( 'Set', 'linker-commerce' ); ?></button>
									</span>
								</form>
							</div>
						</details>

						<details class="filter-section fgroup" open>
							<summary class="filter-title"><?php esc_html_e( 'Usable energy', 'linker-commerce' ); ?></summary>
							<div class="filter-options">
								<form class="frange" method="get" action="">
									<?php foreach ( $selected as $key => $value ) : ?>
										<input type="hidden" name="<?php echo esc_attr( (string) $key ); ?>" value="<?php echo esc_attr( (string) $value ); ?>" />
									<?php endforeach; ?>

									<span class="frange-row">
										<input type="number" name="kwh_min" inputmode="decimal" step="0.1" min="0" placeholder="min" value="<?php echo esc_attr( (string) ( $selected['kwh_min'] ?? '' ) ); ?>" aria-label="<?php esc_attr_e( 'Minimum usable energy in kilowatt hours', 'linker-commerce' ); ?>" /><i>&ndash;</i>
										<input type="number" name="kwh_max" inputmode="decimal" step="0.1" min="0" placeholder="max" value="<?php echo esc_attr( (string) ( $selected['kwh_max'] ?? '' ) ); ?>" aria-label="<?php esc_attr_e( 'Maximum usable energy in kilowatt hours', 'linker-commerce' ); ?>" /><b>kWh</b>
										<button type="submit" class="frange-go"><?php esc_html_e( 'Set', 'linker-commerce' ); ?></button>
									</span>
								</form>
							</div>
						</details>
					</div>
				</details>

				<div class="rail-help">
					<b><?php esc_html_e( 'Plan with the Solution Configurator', 'linker-commerce' ); ?></b>
					<p><?php esc_html_e( 'Configure a storage system from your site data; the result is a solution draft you can send as an inquiry.', 'linker-commerce' ); ?></p>
					<a class="rail-help-btn" href="<?php echo esc_url( (string) get_permalink( get_page_by_path( 'linker-planner' ) ) ); ?>"><?php esc_html_e( 'Open the Solution Configurator', 'linker-commerce' ); ?></a>
				</div>

				<div class="catalog-filter-actions">
					<a href="<?php echo esc_url( $queried instanceof WP_Term ? (string) get_term_link( $queried ) : (string) wc_get_page_permalink( 'shop' ) ); ?>"><?php esc_html_e( 'Clear', 'linker-commerce' ); ?></a>
					<button type="button" id="catalog-filter-apply"><?php esc_html_e( 'Show products', 'linker-commerce' ); ?></button>
				</div>
			</aside>

			<div class="catalog-results">
				<div class="wb-strip">
					<div class="wbc"></div>
					<span class="wbcount"><b><?php echo esc_html( (string) count( $products ) ); ?></b> <?php echo esc_html( _n( 'product', 'products', count( $products ), 'linker-commerce' ) ); ?></span>
					<form class="wbsort" method="get" action="">
						<?php foreach ( $selected as $key => $value ) : ?>
							<input type="hidden" name="<?php echo esc_attr( (string) $key ); ?>" value="<?php echo esc_attr( (string) $value ); ?>" />
						<?php endforeach; ?>
						<select class="select-dropdown" id="sort-select" name="sort" aria-label="<?php esc_attr_e( 'Sort products', 'linker-commerce' ); ?>">
							<?php foreach ( $sort_labels as $value => $label ) : ?>
								<option value="<?php echo esc_attr( $value ); ?>"<?php selected( $sort, $value ); ?>><?php echo esc_html( $label ); ?></option>
							<?php endforeach; ?>
						</select>
					</form>
				</div>

				<?php if ( $products ) : ?>
					<div class="catalog-grid" id="catalog-grid">
						<?php foreach ( $products as $product_id ) : ?>
							<?php
							$card  = $view->fields( (int) $product_id );
							$facts = Linker\Commerce\Catalog\SelectionFacts::for_product( (int) $product_id );
							if ( array() === $card ) {
								continue;
							}
							$data = array(
								'data-product-id="' . esc_attr( (string) $product_id ) . '"',
								'data-sku="' . esc_attr( $card['sku'] ) . '"',
								'data-brand="' . esc_attr( $card['brand_slug'] ) . '"',
								'data-phase="' . esc_attr( (string) $facts->phase ) . '"',
								'data-power="' . esc_attr( \is_float( $facts->ac_power_kw ) ? (string) $facts->ac_power_kw : '0' ) . '"',
								'data-application="' . esc_attr( (string) $facts->application ) . '"',
							);
							?>
							<article class="sf-card product-card" data-linker-product-card <?php echo implode( ' ', $data ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- every attribute above escapes its value. ?>>
								<div class="sf-card-media card-media">
									<a data-card-media-link href="<?php echo esc_url( (string) get_permalink( $product_id ) ); ?>" aria-label="<?php echo esc_attr( $card['title'] ); ?>">
										<?php if ( $card['gallery'] ) : ?>
											<?php
											echo wp_get_attachment_image(
												$card['gallery'][0],
												'medium',
												false,
												array(
													'loading' => 'lazy',
													'alt' => $card['title'],
												)
											);
											?>
										<?php endif; ?>
									</a>
								</div>
								<div class="card-identity">
									<?php if ( '' !== $card['brand'] ) : ?>
										<p class="sf-card-brand"><?php echo esc_html( $card['brand'] ); ?></p>
									<?php endif; ?>
									<a class="sf-card-title" data-card-title href="<?php echo esc_url( (string) get_permalink( $product_id ) ); ?>"><?php echo esc_html( $card['model'] ); ?></a>
									<?php if ( '' !== $card['designation'] ) : ?>
										<p class="sf-card-designation"><?php echo esc_html( $card['designation'] ); ?></p>
									<?php endif; ?>
									<?php if ( '' !== $card['sku'] ) : ?>
										<p class="sf-card-sku"><?php esc_html_e( 'Item no.', 'linker-commerce' ); ?> <span data-card-sku><?php echo esc_html( $card['sku'] ); ?></span></p>
									<?php endif; ?>
								</div>
								<?php if ( $card['stats'] ) : ?>
									<dl class="card-facts" data-card-facts aria-label="<?php esc_attr_e( 'Key product data', 'linker-commerce' ); ?>">
										<?php foreach ( array_slice( $card['stats'], 0, 4 ) as $stat ) : ?>
											<div><dt><?php echo esc_html( $stat['label'] ); ?></dt><dd><?php echo esc_html( $stat['value'] ); ?></dd></div>
										<?php endforeach; ?>
									</dl>
								<?php endif; ?>
								<div class="sf-card-price" data-card-price>
									<?php if ( $card['price']['url'] ) : ?>
										<a class="sf-card-price-login" href="<?php echo esc_url( $card['price']['url'] ); ?>"><?php echo esc_html( $card['price']['html'] ); ?></a>
									<?php else : ?>
										<span class="sf-card-price-net"><?php echo wp_kses_post( $card['price']['html'] ); ?></span>
									<?php endif; ?>
								</div>
								<p class="sf-card-availability" data-card-availability><?php echo esc_html( $card['availability'] ); ?></p>
								<div class="sf-card-actions">
									<a class="sf-card-view tv-woo-card-action tv-woo-card-action--primary" data-card-view href="<?php echo esc_url( (string) get_permalink( $product_id ) ); ?>"><?php esc_html_e( 'View product', 'linker-commerce' ); ?></a>
								</div>
							</article>
						<?php endforeach; ?>
					</div>
				<?php else : ?>
					<div class="catalog-grid" id="catalog-grid">
						<p class="tv-empty-state"><?php esc_html_e( 'No product matches these filters. Clear one to see more.', 'linker-commerce' ); ?></p>
					</div>
				<?php endif; ?>
			</div>
		</div>
	</section>
</div>
<?php
get_footer();
