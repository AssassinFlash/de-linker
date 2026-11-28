<?php
/**
 * Plugin Name: Linker origin crawler telemetry
 * Description: Reports aggregate crawler requests that reach PHP.
 *
 * @package Linker\Mu
 */

declare( strict_types = 1 );

namespace Linker\Mu;

defined( 'ABSPATH' ) || exit;

// Local file locks protect counters shared by LSAPI workers. A missing bucket is an empty day.
// phpcs:disable WordPress.WP.AlternativeFunctions, WordPress.PHP.NoSilencedErrors.Discouraged
// phpcs:disable WordPress.Security.ValidatedSanitizedInput -- Only the normalized family, URL path and numeric response status enter the counters.

/** Whitelisted crawler counters for the operations dashboard. */
final class CrawlerTelemetry {
	private const ROUTE = '/linker/v1/crawler-telemetry';
	private const CRON  = 'linker_crawler_refresh_cidrs';

	private const FAMILIES = array(
		'Googlebot'     => 'search',
		'bingbot'       => 'search',
		'OAI-SearchBot' => 'ai',
		'ChatGPT-User'  => 'ai',
		'GPTBot'        => 'ai',
		'PerplexityBot' => 'ai',
		'ClaudeBot'     => 'ai',
		'Applebot'      => 'search',
	);
	private const ALIASES  = array(
		'Perplexity-User'  => 'PerplexityBot',
		'Claude-SearchBot' => 'ClaudeBot',
		'Claude-User'      => 'ClaudeBot',
	);
	private const FEEDS    = array(
		'Googlebot'       => 'https://developers.google.com/crawling/ipranges/common-crawlers.json',
		'bingbot'         => 'https://www.bing.com/toolbox/bingbot.json',
		'Applebot'        => 'https://search.developer.apple.com/applebot.json',
		'OAI-SearchBot'   => 'https://openai.com/searchbot.json',
		'ChatGPT-User'    => 'https://openai.com/chatgpt-user.json',
		'GPTBot'          => 'https://openai.com/gptbot.json',
		'PerplexityBot'   => 'https://www.perplexity.ai/perplexitybot.json',
		'Perplexity-User' => 'https://www.perplexity.ai/perplexity-user.json',
		'ClaudeBot'       => 'https://claude.com/crawling/bots.json',
	);
	private const SUFFIXES = array(
		'Googlebot' => array( '.googlebot.com', '.google.com' ),
		'bingbot'   => array( '.search.msn.com' ),
		'Applebot'  => array( '.applebot.apple.com' ),
		'ClaudeBot' => array( '.anthropic.com' ),
	);
	private const CODES    = array( 200, 206, 301, 404, 410, 429, '5xx', 'other' );

	/** Attach only in-memory hooks until a crawler, cron or dashboard requests data. */
	public static function register(): void {
		add_action( 'rest_api_init', array( self::class, 'routes' ) );
		add_action( self::CRON, static fn () => self::refresh( WP_CONTENT_DIR . '/linker-crawler-telemetry' ) );
		add_filter( 'rest_post_dispatch', array( self::class, 'headers' ), 99, 3 );
		$agent = self::agent( (string) ( $_SERVER['HTTP_USER_AGENT'] ?? '' ) );
		if ( '' === $agent || ( defined( 'WP_CLI' ) && WP_CLI ) || is_admin() || wp_doing_cron() || wp_doing_ajax() ) {
			return;
		}
		$start = hrtime( true );
		register_shutdown_function(
			static function () use ( $agent, $start ): void {
				global $wp;
				if ( isset( $wp->query_vars['rest_route'] ) && self::ROUTE === rtrim( (string) $wp->query_vars['rest_route'], '/' ) ) {
					return;
				}
				$ms       = (int) round( ( hrtime( true ) - $start ) / 1000000 );
				$status   = (int) http_response_code();
				$detached = false;
				if ( function_exists( 'litespeed_finish_request' ) ) {
					$detached = (bool) litespeed_finish_request();
				} elseif ( function_exists( 'fastcgi_finish_request' ) ) {
					$detached = fastcgi_finish_request();
				}
				self::record( WP_CONTENT_DIR . '/linker-crawler-telemetry', $agent, (string) ( $_SERVER['REQUEST_URI'] ?? '/' ), (string) ( $_SERVER['REMOTE_ADDR'] ?? '' ), $status, $ms, $detached );
			}
		);
	}

	/**
	 * Return the matching crawler product token.
	 *
	 * @param string $ua Incoming browser user agent.
	 */
	public static function agent( string $ua ): string {
		if ( ! preg_match( '~(?<![a-z0-9_-])(Googlebot|bingbot|Applebot|OAI-SearchBot|ChatGPT-User|GPTBot|PerplexityBot|Perplexity-User|ClaudeBot|Claude-SearchBot|Claude-User)(?=[/;\s)]|$)~i', $ua, $match ) ) {
			return '';
		}
		foreach ( array_keys( self::FAMILIES + self::ALIASES ) as $agent ) {
			if ( 0 === strcasecmp( $match[1], $agent ) ) {
				return $agent;
			}
		}
		return '';
	}

	/** Register the protected dashboard resource. */
	public static function routes(): void {
		register_rest_route(
			'linker/v1',
			'/crawler-telemetry',
			array(
				'methods'             => 'GET',
				'permission_callback' => array( self::class, 'permission' ),
				'callback'            => array( self::class, 'serve' ),
			)
		);
	}

	/**
	 * Authorize against the private site configuration.
	 *
	 * @param \WP_REST_Request $request WordPress REST request.
	 */
	public static function permission( \WP_REST_Request $request ): bool|\WP_Error {
		$key = defined( 'LINKER_CRAWLER_TELEMETRY_KEY' ) ? constant( 'LINKER_CRAWLER_TELEMETRY_KEY' ) : '';
		return is_string( $key ) && strlen( $key ) >= 32 && hash_equals( $key, (string) $request->get_header( 'x-linker-telemetry-key' ) )
			? true : new \WP_Error( 'linker_telemetry_forbidden', 'Access denied.', array( 'status' => 403 ) );
	}

	/**
	 * Apply the same cache policy to success and permission errors.
	 *
	 * @param \WP_HTTP_Response $response Dispatched response, including converted permission errors.
	 * @param \WP_REST_Server   $server Current REST server.
	 * @param \WP_REST_Request  $request WordPress REST request.
	 */
	public static function headers( \WP_HTTP_Response $response, \WP_REST_Server $server, \WP_REST_Request $request ): \WP_HTTP_Response {
		unset( $server );
		if ( self::ROUTE === rtrim( $request->get_route(), '/' ) ) {
			do_action( 'litespeed_control_set_nocache', 'crawler telemetry' ); // phpcs:ignore WordPress.NamingConventions.PrefixAllGlobals.NonPrefixedHooknameFound, WooCommerce.Commenting.CommentHooks.MissingHookComment -- LiteSpeed Cache public API.
			$response->header( 'Cache-Control', 'no-store, private, max-age=0' );
			$response->header( 'X-LiteSpeed-Cache-Control', 'no-cache' );
			$response->header( 'X-Robots-Tag', 'noindex, nofollow' );
		}
		return $response;
	}

	/**
	 * Read the authorized UTC window and initialize maintenance on first use.
	 *
	 * @param \WP_REST_Request $request WordPress REST request.
	 */
	public static function serve( \WP_REST_Request $request ): \WP_REST_Response|\WP_Error {
		$dir = WP_CONTENT_DIR . '/linker-crawler-telemetry';
		if ( ! self::protect( $dir ) ) {
			return new \WP_Error( 'linker_telemetry_storage', 'Telemetry storage unavailable.', array( 'status' => 503 ) );
		}
		self::schedule();
		$days = filter_var( $request->get_param( 'days' ), FILTER_VALIDATE_INT );
		return new \WP_REST_Response( self::report( $dir, false === $days ? 15 : max( 1, min( 30, $days ) ), time() ) );
	}

	/**
	 * Install the HTTP deny rule before creating data files.
	 *
	 * @param string $dir Protected telemetry directory.
	 */
	private static function protect( string $dir ): bool {
		if ( ! is_dir( $dir ) && ! @mkdir( $dir, 0755 ) && ! is_dir( $dir ) ) {
			return false;
		}
		foreach ( array(
			'.htaccess'  => "Require all denied\n<IfModule !mod_authz_core.c>\nDeny from all\n</IfModule>\n",
			'index.html' => '',
		) as $file => $content ) {
			if ( ! is_file( "$dir/$file" ) && strlen( $content ) !== file_put_contents( "$dir/$file", $content, LOCK_EX ) ) {
				return false;
			}
		}
		return true;
	}

	/**
	 * Schedule one daily refresh from a crawler or authenticated dashboard visit.
	 */
	private static function schedule(): void {
		if ( ! wp_next_scheduled( self::CRON ) ) {
			wp_schedule_event( time(), 'daily', self::CRON );
		}
	}

	/**
	 * Refresh the official feeds in cron, preserving each feed on failure.
	 *
	 * @param string $dir Protected telemetry directory.
	 */
	public static function refresh( string $dir ): void {
		if ( ! self::protect( $dir ) ) {
			return;
		}
		$file = "$dir/cidrs.json";
		$lock = fopen( "$dir/cidrs.lock", 'c' );
		if ( false === $lock ) {
			return;
		}
		try {
			if ( ! flock( $lock, LOCK_EX | LOCK_NB ) || ( is_file( $file ) && filemtime( $file ) > time() - DAY_IN_SECONDS ) ) {
				return;
			}
			self::rotate( $dir );
			$ranges = self::read( $file );
			foreach ( self::FEEDS as $agent => $url ) {
				$response = wp_remote_get( $url, array( 'timeout' => 5 ) );
				if ( 200 !== (int) wp_remote_retrieve_response_code( $response ) ) {
					continue;
				}
				$json   = json_decode( wp_remote_retrieve_body( $response ), true );
				$parsed = array();
				if ( ! is_array( $json['prefixes'] ?? null ) ) {
					continue;
				}
				foreach ( $json['prefixes'] as $row ) {
					$cidr = $row['ipv4Prefix'] ?? $row['ipv6Prefix'] ?? '';
					if ( ! is_string( $cidr ) || ! self::valid_prefix( $cidr ) ) {
						continue 2;
					}
					$parsed[] = $cidr;
				}
				if ( $parsed ) {
					$ranges[ $agent ] = $parsed;
				}
			}
			$bytes = wp_json_encode( $ranges );
			if ( false !== $bytes && strlen( $bytes ) === file_put_contents( "$file.next", $bytes ) ) {
				rename( "$file.next", $file );
			}
		} finally {
			fclose( $lock );
		}
	}

	/**
	 * Validate the address family and prefix length.
	 *
	 * @param string $cidr Published address prefix.
	 */
	private static function valid_prefix( string $cidr ): bool {
		$parts = explode( '/', $cidr );
		if ( 2 !== count( $parts ) || ! ctype_digit( $parts[1] ) ) {
			return false;
		}
		$ip = inet_pton( $parts[0] );
		return false !== $ip && (int) $parts[1] <= strlen( $ip ) * 8;
	}

	/**
	 * Match an IPv4 or IPv6 peer against its provider’s prefixes.
	 *
	 * @param string   $ip Original peer address, used only in memory.
	 * @param string[] $ranges Official prefixes for the claimed crawler.
	 */
	public static function matches( string $ip, array $ranges ): bool {
		$packed = inet_pton( $ip );
		if ( false === $packed ) {
			return false;
		}
		foreach ( $ranges as $cidr ) {
			list( $net, $bits ) = explode( '/', $cidr );
			$net                = inet_pton( $net );
			if ( false === $net || strlen( $net ) !== strlen( $packed ) ) {
				continue;
			}
			$bytes = intdiv( (int) $bits, 8 );
			$rest  = (int) $bits % 8;
			if ( 0 === strncmp( $net, $packed, $bytes ) && ( 0 === $rest || ( ( ord( $net[ $bytes ] ) ^ ord( $packed[ $bytes ] ) ) >> ( 8 - $rest ) ) === 0 ) ) {
				return true;
			}
		}
		return false;
	}

	/**
	 * The digest cache expires at UTC midnight. A busy resolver never holds the counter lock.
	 *
	 * @param string $dir Protected telemetry directory.
	 * @param string $agent Claimed crawler product token.
	 * @param string $ip Original peer address, used only in memory.
	 * @param bool   $detached Whether LSAPI or FastCGI has already released the client.
	 */
	private static function verified( string $dir, string $agent, string $ip, bool $detached ): bool {
		$family = self::ALIASES[ $agent ] ?? $agent;
		$feeds  = self::read( "$dir/cidrs.json" );
		$ranges = $feeds[ 'Perplexity-User' === $agent ? $agent : $family ] ?? array();
		if ( self::matches( $ip, $ranges ) ) {
			return true;
		}
		if ( ! $detached || ! isset( self::SUFFIXES[ $family ] ) || ! filter_var( $ip, FILTER_VALIDATE_IP, FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE ) ) {
			return false;
		}
		$file = fopen( "$dir/rdns.json", 'c+' );
		if ( false === $file ) {
			return false;
		}
		try {
			if ( ! flock( $file, LOCK_EX | LOCK_NB ) ) {
				return false;
			}
			$data = json_decode( (string) stream_get_contents( $file ), true );
			$day  = gmdate( 'Y-m-d' );
			if ( ( $data['date'] ?? '' ) !== $day ) {
				$data = array(
					'date'    => $day,
					'salt'    => bin2hex( random_bytes( 32 ) ),
					'results' => array(),
				);
			}
			$key = hash_hmac( 'sha256', $family . '|' . $ip, $data['salt'] );
			if ( isset( $data['results'][ $key ] ) ) {
				return $data['results'][ $key ];
			}
			if ( count( $data['results'] ) >= 50 ) {
				return false;
			}
			$result                  = self::dns_verdict( $family, $ip, self::dig( ... ) );
			$data['results'][ $key ] = $result;
			self::write( $file, $data );
			return $result;
		} finally {
			fclose( $file );
		}
	}

	/**
	 * Confirm an official reverse hostname by resolving it back to the original address.
	 *
	 * @param string   $family Canonical crawler family.
	 * @param string   $ip Original peer address, used only in memory.
	 * @param callable $lookup Bounded system resolver.
	 * @phpstan-param callable(list<string>):string[] $lookup
	 */
	private static function dns_verdict( string $family, string $ip, callable $lookup ): bool {
		foreach ( $lookup( array( '-x', $ip ) ) as $answer ) {
			$name = strtolower( rtrim( $answer, '.' ) );
			foreach ( self::SUFFIXES[ $family ] as $suffix ) {
				if ( str_ends_with( $name, $suffix ) && filter_var( $name, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME ) ) {
					foreach ( $lookup( array( $name . '.', str_contains( $ip, ':' ) ? 'AAAA' : 'A' ) ) as $address ) {
						if ( inet_pton( $address ) === inet_pton( $ip ) ) {
							return true;
						}
					}
					return false;
				}
			}
		}
		return false;
	}

	/**
	 * Use the host resolver with a one-second timeout per query (at most one PTR, one A/AAAA).
	 *
	 * @param string[] $args Validated DNS question.
	 * @phpstan-param list<string> $args
	 * @return string[]
	 */
	private static function dig( array $args ): array {
		if ( ! function_exists( 'proc_open' ) || ! is_executable( '/usr/bin/dig' ) ) {
			return array();
		}
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.system_calls_proc_open -- Required for bounded DNS on Hostinger; the command is an argument vector.
		$process = proc_open(
			array_merge( array( '/usr/bin/dig', '+short', '+timeout=1', '+tries=1', '+nosearch' ), $args ),
			array(
				1 => array( 'pipe', 'w' ),
				2 => array( 'file', '/dev/null', 'w' ),
			),
			$pipes
		);
		if ( ! is_resource( $process ) ) {
			return array();
		}
		$output = stream_get_contents( $pipes[1] );
		fclose( $pipes[1] );
		return 0 === proc_close( $process ) && is_string( $output ) ? explode( "\n", trim( $output ) ) : array();
	}

	/**
	 * Read a consistent snapshot of one JSON file.
	 *
	 * @param string $file Local JSON file.
	 * @return array<mixed>
	 */
	private static function read( string $file ): array {
		if ( ! is_file( $file ) ) {
			return array();
		}
		$stream = fopen( $file, 'r' );
		if ( false === $stream ) {
			return array();
		}
		try {
			flock( $stream, LOCK_SH );
			$data = json_decode( (string) stream_get_contents( $stream ), true );
			return is_array( $data ) ? $data : array();
		} finally {
			fclose( $stream );
		}
	}

	/**
	 * Replace the contents under the existing exclusive lock.
	 *
	 * @param resource     $file Locked bucket.
	 * @param array<mixed> $data Aggregate data.
	 */
	private static function write( $file, array $data ): void {
		$bytes = wp_json_encode( $data, JSON_INVALID_UTF8_SUBSTITUTE );
		if ( false !== $bytes ) {
			rewind( $file );
			ftruncate( $file, 0 );
			fwrite( $file, $bytes );
			fflush( $file );
		}
	}

	/**
	 * Record a completed origin response, keeping only method-independent aggregates.
	 *
	 * @param string $dir Protected telemetry directory.
	 * @param string $agent Claimed crawler product token.
	 * @param string $uri Request target before query removal.
	 * @param string $ip Original peer address, used only in memory.
	 * @param int    $status Final HTTP response code.
	 * @param int    $ms Server duration in milliseconds.
	 * @param bool   $detached Whether LSAPI or FastCGI has already released the client.
	 */
	public static function record( string $dir, string $agent, string $uri, string $ip, int $status, int $ms, bool $detached ): void {
		$family = self::ALIASES[ $agent ] ?? $agent;
		if ( ! isset( self::FAMILIES[ $family ] ) || ! self::protect( $dir ) ) {
			return;
		}
		$path = substr( (string) wp_parse_url( $uri, PHP_URL_PATH ), 0, 200 );
		$path = '' === $path ? '/' : $path;
		if ( '' !== $ip && str_contains( rawurldecode( $path ), $ip ) ) {
			$path = '/[redacted]';
		}
		$verified = self::verified( $dir, $agent, $ip, $detached );
		$day      = gmdate( 'Y-m-d' );
		$file     = fopen( "$dir/$day.json", 'c+' );
		if ( false === $file ) {
			return;
		}
		try {
			if ( ! flock( $file, LOCK_EX | LOCK_NB ) ) {
				return;
			}
			$previous = (string) stream_get_contents( $file );
			$bucket   = '' === $previous ? array() : json_decode( $previous, true );
			if ( ! is_array( $bucket ) ) {
				return;
			}
			$row = $bucket['families'][ $family ] ?? self::empty_counts();
			++$row['requests'];
			$row['verifiedRequests'] += (int) $verified;
			$code                     = in_array( $status, self::CODES, true ) ? $status : ( $status >= 500 && $status < 600 ? '5xx' : 'other' );
			++$row['statusBuckets'][ $code ];
			$row['durations'][]            = $ms;
			$row['durations']              = array_slice( $row['durations'], -256 );
			$bucket['families'][ $family ] = $row;
			$bucket['paths']             ??= array();
			$bucket['errors']            ??= array();
			self::path_hit( $bucket['paths'], $path, $family, $verified, $ms, $status, 150, false );
			if ( $status >= 400 ) {
				self::path_hit( $bucket['errors'], $path, $family, $verified, $ms, $status, 100, true );
			}
			self::write( $file, $bucket );
		} finally {
			fclose( $file );
		}
		if ( '' === $previous ) {
			self::rotate( $dir );
			self::schedule();
		}
	}

	/**
	 * Keep rolling heavy-hitter candidates; reported hits count only observations for that path.
	 *
	 * @param array<mixed> $rows Daily path candidates.
	 * @param string       $path Query-free, bounded URL path.
	 * @param string       $family Canonical crawler family.
	 * @param bool         $verified Whether the origin matched the provider.
	 * @param int          $ms Server duration in milliseconds.
	 * @param int          $status Final HTTP response code.
	 * @param int          $limit Maximum candidates in this bucket.
	 * @param bool         $error Whether the key includes an HTTP error code.
	 */
	private static function path_hit( array &$rows, string $path, string $family, bool $verified, int $ms, int $status, int $limit, bool $error ): void {
		$key = $error ? $status . '|' . $path : $path;
		if ( ! isset( $rows[ $key ] ) ) {
			$weight = 0;
			if ( count( $rows ) >= $limit ) {
				$victim = array_key_first( $rows );
				foreach ( $rows as $candidate => $item ) {
					if ( $item['weight'] < $rows[ $victim ]['weight'] ) {
						$victim = $candidate;
					}
				}
				$weight = $rows[ $victim ]['weight'];
				unset( $rows[ $victim ] );
			}
			$rows[ $key ] = array(
				'path'         => $path,
				'hits'         => 0,
				'verifiedHits' => 0,
				'families'     => array(),
				'durations'    => array(),
				'weight'       => $weight,
			);
		}
		$row = &$rows[ $key ];
		++$row['weight'];
		++$row['hits'];
		$row['verifiedHits']       += (int) $verified;
		$row['families'][ $family ] = ( $row['families'][ $family ] ?? 0 ) + 1;
		$row['durations'][]         = $ms;
		$row['durations']           = array_slice( $row['durations'], -32 );
		$row['lastStatus']          = $status;
		if ( $error ) {
			$row['lastSeenUtc'] = gmdate( 'c' );
		}
	}

	/**
	 * Retain the current day and the preceding 34 UTC buckets.
	 *
	 * @param string $dir Protected telemetry directory.
	 */
	private static function rotate( string $dir ): void {
		$cutoff = gmdate( 'Y-m-d', time() - 34 * DAY_IN_SECONDS );
		$files  = glob( "$dir/????-??-??.json" );
		foreach ( false === $files ? array() : $files as $file ) {
			if ( basename( $file, '.json' ) < $cutoff ) {
				unlink( $file );
			}
		}
	}

	/**
	 * Initialize counters for every published status bucket.
	 *
	 * @return array<mixed>
	 */
	private static function empty_counts(): array {
		return array(
			'requests'         => 0,
			'verifiedRequests' => 0,
			'statusBuckets'    => array_fill_keys( self::CODES, 0 ),
			'durations'        => array(),
		);
	}

	/**
	 * Sum one day’s counters and combine its duration samples.
	 *
	 * @param array<mixed> $into Window accumulator.
	 * @param array<mixed> $row  Daily family counters.
	 */
	private static function merge_counts( array &$into, array $row ): void {
		$into['requests']         += $row['requests'];
		$into['verifiedRequests'] += $row['verifiedRequests'];
		foreach ( $row['statusBuckets'] as $code => $count ) {
			$into['statusBuckets'][ $code ] += $count;
		}
		array_push( $into['durations'], ...$row['durations'] );
	}

	/**
	 * Nearest-rank percentiles of the retained samples.
	 *
	 * @param int[] $samples Response durations in milliseconds.
	 * @return array{p50Ms:int,p95Ms:int}
	 */
	private static function latency( array $samples ): array {
		sort( $samples, SORT_NUMERIC );
		$n = count( $samples );
		return array(
			'p50Ms' => $samples[ (int) ceil( $n * 0.50 ) - 1 ] ?? 0,
			'p95Ms' => $samples[ (int) ceil( $n * 0.95 ) - 1 ] ?? 0,
		);
	}

	/**
	 * Build the consumer’s request and verification metrics.
	 *
	 * @param array<mixed> $row Accumulated family or site metrics.
	 * @return array<mixed>
	 */
	private static function metrics( array $row ): array {
		$row['unverifiedRequests'] = $row['requests'] - $row['verifiedRequests'];
		$row['verifiedRatioPct']   = $row['requests'] > 0 ? round( 100 * $row['verifiedRequests'] / $row['requests'], 1 ) : 0.0;
		$row                      += self::latency( $row['durations'] );
		unset( $row['durations'] );
		return $row;
	}

	/**
	 * Accumulate a day’s candidates in chronological order.
	 *
	 * @param array<mixed> $into Window path totals.
	 * @param array<mixed> $rows Path counters for a single day.
	 */
	private static function merge_paths( array &$into, array $rows ): void {
		foreach ( $rows as $key => $row ) {
			unset( $row['weight'] );
			if ( ! isset( $into[ $key ] ) ) {
				$into[ $key ] = $row;
				continue;
			}
			$total                  = &$into[ $key ];
			$total['hits']         += $row['hits'];
			$total['verifiedHits'] += $row['verifiedHits'];
			$total['lastStatus']    = $row['lastStatus'];
			foreach ( $row['families'] as $family => $count ) {
				$total['families'][ $family ] = ( $total['families'][ $family ] ?? 0 ) + $count;
			}
			array_push( $total['durations'], ...$row['durations'] );
			if ( isset( $row['lastSeenUtc'] ) ) {
				$total['lastSeenUtc'] = $row['lastSeenUtc'];
			}
			unset( $total );
		}
	}

	/**
	 * Return at most 25 paths in descending hit count.
	 *
	 * @param array<mixed> $rows Window path totals.
	 * @return array<mixed>
	 */
	private static function ranked( array $rows ): array {
		usort( $rows, static fn ( array $a, array $b ): int => array( $b['hits'], $a['path'] ) <=> array( $a['hits'], $b['path'] ) );
		$top = array_slice( $rows, 0, 25 );
		foreach ( $top as &$row ) {
			$row += self::latency( $row['durations'] );
			unset( $row['durations'] );
			if ( isset( $row['lastSeenUtc'] ) ) {
				$row['status'] = $row['lastStatus'];
				unset( $row['lastStatus'], $row['verifiedHits'], $row['p50Ms'] );
			}
		}
		return $top;
	}

	/**
	 * Crawler Telemetry Contract v1, including dates and families with zero observations.
	 *
	 * @param string $dir Protected telemetry directory.
	 * @param int    $days Requested window in UTC dates.
	 * @param int    $now Unix time of the end date.
	 * @return array<mixed>
	 */
	public static function report( string $dir, int $days, int $now ): array {
		$families = array_fill_keys( array_keys( self::FAMILIES ), self::empty_counts() );
		$totals   = self::empty_counts();
		$daily    = array();
		$paths    = array();
		$errors   = array();
		for ( $i = $days - 1; $i >= 0; --$i ) {
			$date   = gmdate( 'Y-m-d', $now - $i * DAY_IN_SECONDS );
			$bucket = self::read( "$dir/$date.json" );
			$day    = self::empty_counts();
			$by     = array_fill_keys( array_keys( self::FAMILIES ), 0 );
			$search = 0;
			foreach ( $bucket['families'] ?? array() as $family => $row ) {
				self::merge_counts( $day, $row );
				self::merge_counts( $families[ $family ], $row );
				$by[ $family ] = $row['requests'];
				if ( 'search' === self::FAMILIES[ $family ] ) {
					$search += $row['requests'];
				}
			}
			self::merge_counts( $totals, $day );
			$codes   = $day['statusBuckets'];
			$daily[] = array(
				'date'             => $date,
				'totalRequests'    => $day['requests'],
				'verifiedRequests' => $day['verifiedRequests'],
				'searchRequests'   => $search,
				'aiRequests'       => $day['requests'] - $search,
				'error4xx5xx'      => $codes[404] + $codes[410] + $codes[429] + $codes['5xx'],
				'rateLimited429'   => $codes[429],
				'byFamily'         => $by,
				'statusBuckets'    => $codes,
			) + self::latency( $day['durations'] );
			self::merge_paths( $paths, $bucket['paths'] ?? array() );
			self::merge_paths( $errors, $bucket['errors'] ?? array() );
		}
		$by_family = array();
		foreach ( $families as $family => $row ) {
			$by_family[] = array(
				'family'   => $family,
				'category' => self::FAMILIES[ $family ],
			) + self::metrics( $row );
		}
		return array(
			'contractVersion'   => '1.0',
			'site'              => 'https://de-linker.com/',
			'generatedAtUtc'    => gmdate( 'c', $now ),
			'dateRange'         => array(
				'start' => $daily[0]['date'],
				'end'   => gmdate( 'Y-m-d', $now ),
			),
			'windowDays'        => $days,
			'privacyGuarantees' => array(
				'storesVisitorIp'      => false,
				'humanRequestOverhead' => 'zero_io_fast_exit',
				'observationScope'     => 'php_origin_requests',
			),
			'totals'            => self::metrics( $totals ),
			'byFamily'          => $by_family,
			'daily'             => $daily,
			'topErrorPaths'     => self::ranked( $errors ),
			'topCrawledPaths'   => self::ranked( $paths ),
		);
	}
}

CrawlerTelemetry::register();
