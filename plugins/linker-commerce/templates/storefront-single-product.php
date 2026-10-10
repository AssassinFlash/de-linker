<?php
/**
 * The single product template: what a maintainer edits in the standard
 * editor is what this page shows the moment it is saved (#12,
 * docs/specs/12-site-chrome.md item 6). The words and images come from the
 * WooCommerce product's own fields, the key numbers from the selection
 * facts (#7), the technical table from linker_specs (the legacy ACF JSON
 * until #8 writes it), the documents from the product's download entries.
 * The look is the product page the site serves today.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

defined( 'ABSPATH' ) || exit;

get_header();

$view = ( new Linker\Commerce\Storefront\ProductView() )->fields( (int) get_the_ID() );
if ( array() === $view ) {
	return;
}

$gallery = $view['gallery'];
$main    = \array_slice( $gallery, 0, 2 );
$thumbs  = $gallery;
?>
<div id="tv-storefront-pdp" class="sf-pdp pdp-brand-<?php echo esc_attr( $view['brand_slug'] ); ?>">
	<div class="sf-container">
		<nav class="pdp-crumbs" aria-label="<?php esc_attr_e( 'Breadcrumb', 'linker-commerce' ); ?>">
			<?php foreach ( $view['crumbs'] as $crumb ) : ?>
				<?php if ( $crumb['url'] ) : ?>
					<a href="<?php echo esc_url( $crumb['url'] ); ?>"><?php echo esc_html( $crumb['label'] ); ?></a>
				<?php else : ?>
					<span><?php echo esc_html( $crumb['label'] ); ?></span>
				<?php endif; ?>
			<?php endforeach; ?>
		</nav>

		<div class="pdp-layout">
			<div class="pdp-gallery">
				<?php if ( $gallery ) : ?>
					<div class="pdp-gallery-pair">
						<button class="pdp-gallery-main-wrap" type="button" data-pdp-viewer-open>
							<?php
							echo wp_get_attachment_image(
								$main[0],
								'large',
								false,
								array(
									'class'         => 'pdp-gallery-main',
									'loading'       => 'eager',
									'fetchpriority' => 'high',
								)
							);
							?>
						</button>
						<?php if ( isset( $main[1] ) ) : ?>
							<button class="pdp-gallery-secondary" type="button" data-pdp-viewer-open>
								<?php
								echo wp_get_attachment_image(
									$main[1],
									'medium_large',
									false,
									array(
										'class'   => 'pdp-gallery-secondary-img',
										'loading' => 'lazy',
									)
								);
								?>
							</button>
						<?php endif; ?>
					</div>
					<?php if ( count( $gallery ) > 2 ) : ?>
						<div class="pdp-thumbs">
							<?php foreach ( $thumbs as $image_id ) : ?>
								<button class="pdp-thumb" type="button" data-pdp-viewer-open>
									<?php echo wp_get_attachment_image( $image_id, 'thumbnail', false, array( 'loading' => 'lazy' ) ); ?>
								</button>
							<?php endforeach; ?>
						</div>
					<?php endif; ?>
				<?php else : ?>
					<div class="pdp-gallery-pair">
						<div class="pdp-gallery-main-wrap pdp-gallery-empty">
							<p class="tv-empty-state"><?php esc_html_e( 'Product photography for this model is in preparation.', 'linker-commerce' ); ?></p>
						</div>
					</div>
				<?php endif; ?>
			</div>

			<aside class="pdp-purchase">
				<div class="pdp-buy-inner">
					<?php if ( $view['brand_logo'] ) : ?>
						<div class="pdp-brand pdp-brand--logo">
							<img class="pdp-brand-logo" src="<?php echo esc_url( $view['brand_logo']['src'] ); ?>" srcset="<?php echo esc_attr( $view['brand_logo']['srcset'] ); ?>" alt="<?php echo esc_attr( $view['brand_logo']['alt'] ); ?>" loading="eager" decoding="async" />
						</div>
					<?php elseif ( '' !== $view['brand'] ) : ?>
						<div class="pdp-brand"><span class="pdp-brand-text"><?php echo esc_html( $view['brand'] ); ?></span></div>
					<?php endif; ?>

					<h1 class="pdp-h1"><?php echo esc_html( $view['model'] ); ?></h1>
					<?php if ( '' !== $view['designation'] ) : ?>
						<p class="pdp-designation"><?php echo esc_html( $view['designation'] ); ?></p>
					<?php endif; ?>
					<?php if ( '' !== $view['sku'] ) : ?>
						<p class="pdp-sku"><?php esc_html_e( 'Item number:', 'linker-commerce' ); ?> <?php echo esc_html( $view['sku'] ); ?></p>
					<?php endif; ?>

					<div class="pdp-price">
						<?php if ( $view['price']['url'] ) : ?>
							<a class="pdp-price-login" href="<?php echo esc_url( $view['price']['url'] ); ?>"><?php echo esc_html( $view['price']['html'] ); ?></a>
						<?php else : ?>
							<span class="pdp-price-net"><?php echo wp_kses_post( $view['price']['html'] ); ?></span>
						<?php endif; ?>
					</div>

					<?php if ( $view['stats'] ) : ?>
						<dl class="pdp-spec-list">
							<?php foreach ( $view['stats'] as $stat ) : ?>
								<div>
									<dt><?php echo esc_html( $stat['label'] ); ?></dt>
									<dd><?php echo esc_html( $stat['value'] ); ?></dd>
								</div>
							<?php endforeach; ?>
						</dl>
					<?php endif; ?>

					<div class="pdp-avail">
						<p class="pdp-avail-label"><span class="pdp-dot is-ok" aria-hidden="true"></span><?php echo esc_html( $view['availability'] ); ?></p>
					</div>

					<a class="pdp-btn pdp-btn-dark" href="<?php echo esc_url( $view['cta_url'] ); ?>"><?php echo esc_html( $view['cta_label'] ); ?></a>
					<a class="pdp-btn pdp-btn-secondary" href="<?php echo esc_url( $view['ask_url'] ); ?>"><?php esc_html_e( 'Ask about this product', 'linker-commerce' ); ?></a>

					<div class="pdp-product-tools">
						<a class="pdp-tool" href="#downloads"><?php esc_html_x( 'Documents', 'product attachments', 'linker-commerce' ); ?></a>
					</div>
				</div>
			</aside>

			<div class="pdp-content">
				<nav id="product-sections" aria-label="<?php esc_attr_e( 'Product sections', 'linker-commerce' ); ?>">
					<a class="pdp-section-link" href="#description"><?php esc_html_e( 'Description', 'linker-commerce' ); ?></a>
					<a class="pdp-section-link" href="#stats"><?php esc_html_e( 'Technical data', 'linker-commerce' ); ?></a>
					<a class="pdp-section-link" href="#downloads"><?php esc_html_x( 'Documents', 'product attachments', 'linker-commerce' ); ?></a>
				</nav>

				<section id="description" class="pdp-block">
					<div class="pdp-overview">
						<div class="pdp-overview-copy">
							<h2 class="pdp-section-title"><?php echo esc_html( $view['title'] ); ?></h2>
							<div class="pdp-overview-intro pdp-reading">
								<?php if ( '' !== $view['intro'] ) : ?>
									<p><?php echo esc_html( $view['intro'] ); ?></p>
								<?php elseif ( '' !== $view['body'] ) : ?>
									<?php echo wp_kses_post( wpautop( $view['body'] ) ); ?>
								<?php else : ?>
									<p class="tv-empty-state"><?php esc_html_e( 'Introduction in preparation. The specification below carries the values from the datasheet on file.', 'linker-commerce' ); ?></p>
								<?php endif; ?>
							</div>
						</div>
					</div>

					<?php if ( $view['features'] ) : ?>
						<?php foreach ( $view['features'] as $feature ) : ?>
							<details class="pdp-disclose"<?php echo $feature['priority'] ? ' open' : ''; ?>>
								<summary><?php echo esc_html( $feature['title'] ); ?></summary>
								<div class="pdp-disclose-body pdp-reading">
									<?php if ( '' !== $feature['body'] ) : ?>
										<p><?php echo esc_html( $feature['body'] ); ?></p>
									<?php endif; ?>
								</div>
							</details>
						<?php endforeach; ?>
					<?php endif; ?>
				</section>

				<section id="stats" class="pdp-block">
					<h2 class="pdp-section-title"><?php esc_html_e( 'Technical data', 'linker-commerce' ); ?></h2>
					<?php if ( $view['spec_groups'] ) : ?>
						<?php foreach ( $view['spec_groups'] as $group ) : ?>
							<details class="pdp-disclose" open>
								<summary><?php echo esc_html( $group['title'] ); ?><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
								<div class="pdp-disclose-body pdp-reading">
									<dl class="pdp-stat-wrap">
										<?php foreach ( $group['rows'] as $row ) : ?>
											<div class="pdp-stat-row">
												<dt><?php echo esc_html( $row['label'] ); ?></dt>
												<dd><?php echo esc_html( $row['value'] ); ?>
												<?php
												if ( '' !== $row['unit'] ) :
													?>
													<span class="pdp-stat-unit"><?php echo esc_html( $row['unit'] ); ?></span><?php endif; ?>
													<?php if ( '' !== $row['note'] ) : ?>
														<div class="pdp-reading pdp-muted"><?php echo esc_html( $row['note'] ); ?></div>
													<?php endif; ?>
												</dd>
											</div>
										<?php endforeach; ?>
									</dl>
								</div>
							</details>
						<?php endforeach; ?>
					<?php elseif ( $view['attributes'] ) : ?>
						<details class="pdp-disclose" open>
							<summary><?php esc_html_e( 'Specifications', 'linker-commerce' ); ?><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg></summary>
							<div class="pdp-disclose-body pdp-reading">
								<dl class="pdp-stat-wrap">
									<?php foreach ( $view['attributes'] as $row ) : ?>
										<div class="pdp-stat-row">
											<dt><?php echo esc_html( $row['label'] ); ?></dt>
											<dd><?php echo esc_html( $row['value'] ); ?></dd>
										</div>
									<?php endforeach; ?>
								</dl>
							</div>
						</details>
					<?php else : ?>
						<p class="tv-empty-state"><?php esc_html_e( 'The specification table for this product is in preparation. Ask us for the datasheet.', 'linker-commerce' ); ?></p>
					<?php endif; ?>
				</section>

				<section id="downloads" class="pdp-block">
					<h2 class="pdp-section-title"><?php esc_html_x( 'Documents', 'product attachments', 'linker-commerce' ); ?></h2>
					<?php if ( $view['downloads'] ) : ?>
						<?php foreach ( $view['downloads'] as $download ) : ?>
							<a class="pdp-doc" href="<?php echo esc_url( $download['url'] ); ?>" target="_blank" rel="noopener noreferrer">
								<span class="pdp-doc-name"><?php echo esc_html( $download['title'] ); ?></span>
								<span class="pdp-doc-meta"><?php echo esc_html( $download['type'] ); ?> · <?php echo esc_html( $download['language'] ); ?></span>
							</a>
						<?php endforeach; ?>
					<?php else : ?>
						<p class="tv-empty-state"><?php esc_html_e( 'No documents are attached to this product yet. Ask us and we will add them.', 'linker-commerce' ); ?></p>
					<?php endif; ?>
				</section>

				<?php if ( $view['faqs'] ) : ?>
					<section class="pdp-block pdp-faqs">
						<h2 class="pdp-section-title"><?php esc_html_e( 'FAQs', 'linker-commerce' ); ?></h2>
						<?php foreach ( $view['faqs'] as $faq ) : ?>
							<details class="pdp-disclose">
								<summary><?php echo esc_html( $faq['question'] ); ?></summary>
								<div class="pdp-disclose-body pdp-reading">
									<p><?php echo esc_html( $faq['answer'] ); ?></p>
								</div>
							</details>
						<?php endforeach; ?>
					</section>
				<?php endif; ?>

				<?php if ( $view['pairings'] ) : ?>
					<section class="pdp-block">
						<h2 class="pdp-section-title"><?php esc_html_e( 'Compatible products', 'linker-commerce' ); ?></h2>
						<div class="pdp-pairings">
							<?php foreach ( $view['pairings'] as $pairing ) : ?>
								<a class="pdp-pairing" href="<?php echo esc_url( $pairing['url'] ); ?>">
									<?php if ( '' !== $pairing['image'] ) : ?>
										<img loading="lazy" src="<?php echo esc_url( $pairing['image'] ); ?>" alt="<?php echo esc_attr( $pairing['title'] ); ?>" />
									<?php endif; ?>
									<span class="pdp-pairing-name"><?php echo esc_html( $pairing['title'] ); ?></span>
								</a>
							<?php endforeach; ?>
						</div>
					</section>
				<?php endif; ?>
			</div>
		</div>
	</div>

	<dialog id="pdp-image-viewer" aria-label="<?php esc_attr_e( 'Product image', 'linker-commerce' ); ?>">
		<button class="pdp-viewer-close" type="button" data-pdp-viewer-close aria-label="<?php esc_attr_e( 'Close image viewer', 'linker-commerce' ); ?>">&times;</button>
		<img class="pdp-viewer-img" src="" alt="" />
	</dialog>
</div>
<?php
get_footer();
