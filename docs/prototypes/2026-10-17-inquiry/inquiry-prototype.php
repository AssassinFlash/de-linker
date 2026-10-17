<?php
/**
 * PROTOTYPE — throwaway (map #220, tickets #246 / Q1–Q3 of 2026-10-17).
 *
 * 1. The Proforma request page as everyone would see it once inquiries are open
 *    to all: /proforma-request/?iq=A|B|C (A and B = a guest, C = a signed-in
 *    customer with details already known). Products come from the visitor's
 *    real solution draft (Store API, read-only). Sending does nothing.
 * 2. "Two doors, one record": wp-admin → Inquiries (prototype) lists contact
 *    messages and product inquiries together. Sample data.
 * Local instance only; never shipped.
 *
 * @package Linker\Prototype
 */

defined( 'ABSPATH' ) || exit;

add_action(
	'wp_footer',
	static function (): void {
		if ( ! isset( $_GET['iq'] ) || ! function_exists( 'is_checkout' ) || ! is_checkout() ) { // phpcs:ignore -- prototype.
			return;
		}
		echo '<style>' . file_get_contents( __DIR__ . '/inquiry-prototype.css' ) . '</style>'; // phpcs:ignore -- prototype.
		echo '<script>' . file_get_contents( __DIR__ . '/inquiry-prototype.js' ) . '</script>'; // phpcs:ignore -- prototype.
	},
	120
);

add_action(
	'admin_menu',
	static function (): void {
		add_menu_page(
			'Inquiries',
			'Inquiries (prototype) <span class="awaiting-mod">3</span>',
			'edit_users',
			'linker-inquiries-prototype',
			static function (): void {
				$rows = array(
					array( '1618', 'Inquiry', '2 products: SAJ H2-10K-T3 ×1, GoodWe GW5.1-BAT-D-G21 ×1', 'Markus Huber · Solartechnik Huber GmbH', 'm.huber@solartechnik-huber.de', 'Guest', 'Inquiry received', '20 min ago' ),
					array( '1617', 'Message · Discuss a project', '"We plan 40 kWp on a farm roof with storage, can you help with sizing?"', 'Lisa Gruber', 'office@alpen-energie.at', 'Guest', 'Inquiry received', '2 h ago' ),
					array( '1616', 'Inquiry', '4 products: Pylontech US5000 ×4', 'Example Company 18', 'customer-18@example.test', 'Approved partner', 'Proforma invoice issued', 'yesterday' ),
					array( '1615', 'Message · A question', '"Do you deliver to Austria?"', 'Tom Fletcher', 'tom@brightwatt.co.uk', 'Pending account', 'Inquiry received', 'yesterday' ),
					array( '1614', 'Message · Work with Linker', '"Application: technical sales, Munich"', 'Anna Weber', 'anna.weber@web.de', 'Guest', 'Completed', '3 days ago' ),
				);
				echo '<div class="wrap"><h1 class="wp-heading-inline">Inquiries</h1>';
				echo '<p style="background:#fff8e5;border:1px solid #f0c33c;padding:6px 10px;border-radius:4px;font-size:12px">PROTOTYPE · 两扇门、一份记录：联系表单的留言（没有产品）和 Proforma 请求页的询盘（带产品）进同一张列表、同样的状态、同样的"已收到"邮件与一个工作日回复承诺。示例数据。</p>';
				echo '<table class="wp-list-table widefat fixed striped"><thead><tr><th style="width:70px">#</th><th style="width:190px">Type</th><th>What they sent</th><th style="width:230px">From</th><th style="width:130px">Account</th><th style="width:170px">Status</th><th style="width:100px">Received</th></tr></thead><tbody>';
				foreach ( $rows as $r ) {
					$badge = 0 === strpos( $r[1], 'Inquiry' ) ? '#e7f3f1;color:#0c6e64' : '#f0f0f1;color:#3c434a';
					printf(
						'<tr><td><strong>#%1$s</strong></td><td><span style="background:%2$s;padding:2px 8px;border-radius:3px;font-size:12px;font-weight:600">%3$s</span></td><td>%4$s</td><td>%5$s<br><span style="color:#646970;font-size:12px">%6$s</span></td><td>%7$s</td><td>%8$s</td><td>%9$s</td></tr>',
						esc_html( $r[0] ),
						esc_attr( $badge ),
						esc_html( $r[1] ),
						esc_html( $r[2] ),
						esc_html( $r[3] ),
						esc_html( $r[4] ),
						esc_html( $r[5] ),
						esc_html( $r[6] ),
						esc_html( $r[7] )
					);
				}
				echo '</tbody></table></div>';
			},
			'dashicons-email-alt',
			4
		);
	}
);
