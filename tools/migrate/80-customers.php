<?php
/**
 * The WordPress side of tools/migrate/80-customers.py: reads the accounts that
 * existed before the cutover, or gives them their approval state.
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
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

( static function ( string $payload ): void {
	// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- base64 lets any request JSON sit in the single-quoted literal 80-customers.py writes into this file.
	$request = json_decode( base64_decode( $payload ), true, 512, JSON_THROW_ON_ERROR );
	$meta    = (string) $request['meta_key'];
	$value   = (string) $request['value'];

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

	// Every customer with its current state, sorted by login.
	$accounts = static function () use ( $customer_ids, $meta ): array {
		$accounts = array();
		foreach ( $customer_ids() as $id ) {
			$user = get_userdata( $id );
			if ( false === $user ) {
				continue;
			}
			$current         = get_user_meta( $id, $meta, true );
			$accounts[ $id ] = array(
				'id'    => $id,
				'login' => (string) $user->user_login,
				'state' => is_string( $current ) ? $current : '',
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
			foreach ( $accounts() as $account ) {
				if ( $account['state'] === $value ) {
					continue;
				}
				update_user_meta( (int) $account['id'], $meta, $value );
				++$written;
			}
			$answer = array( 'written' => $written ) + $by_state( $accounts() );
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
