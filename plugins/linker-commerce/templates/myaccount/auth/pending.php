<?php
/**
 * The account page of an account still under review: one card, no workplace
 * (ticket #184). Woo loads this template in place of my-account.php while the
 * account is pending; PendingGate owns the markup.
 *
 * @package Linker\Commerce
 */

defined( 'ABSPATH' ) || exit;

Linker\Commerce\Account\PendingGate::output();
