<?php
/**
 * Plugin Name: Linker deploy cache reset
 * Description: Clears the PHP opcode cache once, when the deploy asks right after its switch.
 *
 * The deploy switches every file in one rename (#298), but PHP keeps the
 * compiled old files: the host revalidates them every 2 s
 * (`opcache.validate_timestamps=1`, `opcache.revalidate_freq=2`, read on the
 * host 2026-10-18). For those seconds a request can run an old file against
 * new ones and autoload a class the release deleted. The first atomic deploy
 * logged two such fatals at the switch second (#308). The CLI's opcode cache
 * is another process, so the reset has to run in a web request.
 *
 * Only the deploy can ask: it writes a one-time token into a file outside the
 * web root on the host, posts it in a header, and this plugin compares,
 * deletes the file and resets. The token never leaves the host. A must-use
 * plugin, so it answers even when a regular plugin of the new release fails.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu;

// phpcs:disable WordPress.WP.AlternativeFunctions -- the token is a plain file outside WordPress, read once and removed.

/**
 * Decides and performs one reset request.
 */
final class DeployReset {

	/**
	 * The request header that carries the token.
	 */
	public const HEADER = 'HTTP_X_LINKER_OPCACHE_RESET';

	/**
	 * The token file, under the private configuration directory the site
	 * already reads secrets from ($HOME is set in wp-config for web PHP).
	 */
	public const TOKEN = '/.config/terravolt-builder/opcache-reset.token';

	/**
	 * What a request asks and what happened: null when it is not a valid reset
	 * request (nothing done), otherwise 'done' or 'unavailable'.
	 *
	 * @param array<string, mixed> $server The request's server values.
	 * @param string               $file   The token file.
	 * @param callable(): bool     $reset  The reset itself.
	 */
	public static function decide( array $server, string $file, callable $reset ): ?string {
		$given = $server[ self::HEADER ] ?? '';
		if ( 'POST' !== ( $server['REQUEST_METHOD'] ?? '' ) || ! is_string( $given ) || '' === $given ) {
			return null;
		}
		$expected = is_readable( $file ) ? trim( (string) file_get_contents( $file ) ) : '';
		if ( '' === $expected || ! hash_equals( $expected, $given ) ) {
			return null;
		}
		unlink( $file );
		return $reset() ? 'done' : 'unavailable';
	}

	/**
	 * Answers a reset request and ends it; any other request passes through.
	 */
	public static function handle(): void {
		$home = getenv( 'HOME' );
		if ( ! is_string( $home ) || '' === $home ) {
			return;
		}
		$outcome = self::decide(
			$_SERVER, // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotValidated -- compared with hash_equals only, never output or stored.
			$home . self::TOKEN,
			static fn(): bool => function_exists( 'opcache_reset' ) && opcache_reset()
		);
		if ( null === $outcome ) {
			return;
		}
		http_response_code( 204 );
		header( 'X-Linker-Opcache-Reset: ' . $outcome );
		exit;
	}
}

if ( 'cli' !== PHP_SAPI ) {
	DeployReset::handle();
}
