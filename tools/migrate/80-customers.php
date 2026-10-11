<?php
/**
 * The WordPress side of tools/migrate/80-customers.py: reads the accounts that
 * existed before the cutover, or gives them their approval state and the
 * language of their latest inquiry.
 *
 * 80-customers.py hands this file to `wp eval-file -` with its request (JSON,
 * base64) in place of the placeholder argument at the end. WP-CLI evaluates
 * the file, and evaluated code cannot start with a strict_types declaration,
 * so this file has none. The answer is one JSON line after the request's
 * marker on stdout; a failure is an exception, which WP-CLI reports with a
 * non-zero exit status.
 *
 * The state is the user meta `linker_approval_status`: the account approval of
 * the accounts, whose untaken state is `pending` for every registration the
 * site itself takes. The cutover run sets the accounts that were already here
 * to `approved` (docs/specs/17-cutover.md step 4), and `rollback` removes the
 * meta again, which is exactly the state the site had before the run.
 *
 * The same run fills the user `locale` from the customer's latest inquiry
 * (`_linker_locale` on the order) where it is empty: the accounts that were
 * here before the approval feature never had a registration write it, and it
 * is the language their approval emails are written in (docs/specs/11-commerce.md,
 * the status contract — ticket #73's backfill, merged into this migration).
 * The fill only fills: a locale that is already set stays. `rollback` leaves
 * the filled locales in place, because a locale is the value the site's own
 * registration would have written, not a decision of this run.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets any request JSON sit in the single-quoted literal 80-customers.py writes into this file.
	$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
	$meta         = (string) $request['meta_key'];
	$value        = (string) $request['value'];
	$locale_meta  = (string) $request['locale_meta'];
	$inquiry_meta = (string) $request['inquiry_locale_meta'];

	// The accounts the site calls customers: WooCommerce's customer role, which
	// the live site's registrations carry (measured on the snapshot: every
	// non-staff account has it).
	$customer_ids = static function (): array {
		$ids = get_users(
			array(
				'role'   => 'customer',
				'fields' => 'ID',
			)
		);

		return array_values( array_map( 'intval', $ids ) );
	};

	// The language of the customer's latest inquiry, '' when there is none:
	// what the locale backfill would fill an empty user locale with. Woo's own
	// order query, so HPOS and the posts table answer alike.
	$inquiry_locale = static function ( int $id ) use ( $inquiry_meta ): string {
		if ( ! function_exists( 'wc_get_orders' ) ) {
			return '';
		}
		$orders = wc_get_orders(
			array(
				'customer_id' => $id,
				'type'        => 'shop_order',
				'limit'       => 1,
				'orderby'     => 'date',
				'order'       => 'DESC',
			)
		);
		$order = reset( $orders );
		if ( ! $order instanceof WC_Order ) {
			return '';
		}
		$locale = $order->get_meta( $inquiry_meta );

		return is_string( $locale ) ? $locale : '';
	};

	// Every customer with its current state and locale, sorted by login. The
	// inquiry locale is read only where the user locale is missing — exactly
	// what the run would fill in.
	$accounts = static function () use ( $customer_ids, $meta, $locale_meta, $inquiry_locale ): array {
		$accounts = array();
		foreach ( $customer_ids() as $id ) {
			$user = get_userdata( $id );
			if ( false === $user ) {
				continue;
			}
			$current = get_user_meta( $id, $meta, true );
			$locale  = get_user_meta( $id, $locale_meta, true );
			$locale  = is_string( $locale ) ? $locale : '';
			$accounts[ $id ] = array(
				'id'      => $id,
				'login'   => (string) $user->user_login,
				'state'   => is_string( $current ) ? $current : '',
				'locale'  => $locale,
				'inquiry' => '' === $locale ? $inquiry_locale( $id ) : '',
			);
		}
		uasort(
			$accounts,
			static fn( array $left, array $right ): int => strcmp( $left['login'], $right['login'] )
		);

		return $accounts;
	};

	// Their ids by state, e.g. array( 'approved' => array( 2 ), '' => array( 3 ) ).
	$by_state = static function ( array $accounts ): array {
		$states = array();
		foreach ( $accounts as $account ) {
			$states[ $account['state'] ][] = $account['id'];
		}
		ksort( $states );

		return $states;
	};

	$answer = array();
	switch ( (string) $request['action'] ) {
		case 'write':
			$written = 0;
			$filled  = 0;
			foreach ( $accounts() as $account ) {
				if ( $account['state'] !== $value ) {
					update_user_meta( (int) $account['id'], $meta, $value );
					++$written;
				}
				if ( '' === $account['locale'] && '' !== $account['inquiry'] ) {
					update_user_meta( (int) $account['id'], $locale_meta, $account['inquiry'] );
					++$filled;
				}
			}
			$answer = array( 'written' => $written, 'locales' => $filled ) + $by_state( $accounts() );
			break;

		case 'rollback':
			$removed = 0;
			foreach ( $accounts() as $account ) {
				if ( '' === $account['state'] ) {
					continue;
				}
				delete_user_meta( (int) $account['id'], $meta );
				++$removed;
			}
			$answer = array( 'removed' => $removed ) + $by_state( $accounts() );
			break;

		case 'verify':
			$wrong   = array();
			$account = $accounts();
			foreach ( $account as $entry ) {
				if ( $entry['state'] !== $value ) {
					$wrong[] = $entry['login'] . ' (' . ( '' === $entry['state'] ? 'none' : $entry['state'] ) . ')';
				}
			}
			$answer = array(
				'ok'        => array() === $wrong,
				'customers' => count( $account ),
				'wrong'     => $wrong,
			);
			break;

		default:
			$account = $accounts();
			$answer  = array(
				'customers' => count( $account ),
				'accounts'  => array_values( $account ),
			) + $by_state( $account );
	}
	// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped -- JSON for 80-customers.py on the command line, not HTML.
	echo "\n" . $request['marker'] . wp_json_encode( $answer ) . "\n";
} )( '80-customers-payload' );
