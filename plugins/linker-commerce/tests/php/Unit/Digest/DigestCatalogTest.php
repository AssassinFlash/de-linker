<?php
/**
 * The digest speaks the team's language.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Digest;

use Linker\Commerce\Tests\TestCase;

/**
 * Every string the digest can print resolves in the language the team reads.
 *
 * Production reads linker_commerce_team_locale back as zh_CN while the site
 * runs en_US, so the digest is composed and sent in Chinese. A block string
 * without a Chinese translation therefore arrives as English inside a Chinese
 * email — worst of all in an incident alert, which is what the operations
 * health block is.
 *
 * Two rounds shipped strings no check covered: the i18n-coverage gate reads
 * the catalogs' contents rather than the sources, and it covers de_DE_formal
 * only. The coverage is asserted against the compiled catalog because that is
 * what WordPress reads at send time: a .po that carries a translation while
 * the shipped .mo does not is exactly the state that produced the English
 * digest, and it is invisible to every check that stops at the .po.
 *
 * @coversNothing
 */
final class DigestCatalogTest extends TestCase {

	/**
	 * The catalogs that must answer for every digest string: the team's
	 * language, and German, which carries the same digest for staff who read
	 * the German interface. `i18n-coverage` checks only de_DE_formal and only
	 * entries already present in the .po, so a block absent from the German
	 * catalog stayed invisible until the next POT regeneration would have
	 * shipped English alert lines.
	 */
	private const CATALOGS = array(
		'zh_CN'        => 'languages/linker-commerce-zh_CN.mo',
		'de_DE_formal' => 'languages/linker-commerce-de_DE_formal.mo',
	);

	/**
	 * Files that contribute a string to the digest email, relative to the
	 * plugin root: the blocks, the email, the approval ticket's block the
	 * Blocks filter adds, and the template.
	 */
	private const SOURCES = array(
		'includes/Digest',
		'includes/Health/InternalMail.php',
		'includes/Health/PendingReviews.php',
		'includes/Health/OperationsHealth.php',
		'includes/Registration/PendingApprovals.php',
		'templates/emails/linker-digest.php',
	);

	/**
	 * Every msgid the digest's sources pass through __() or _n() resolves in
	 * each catalog the digest can be sent in.
	 */
	public function test_every_digest_string_resolves_in_every_digest_language(): void {
		$sources = $this->digest_sources( $this->plugin_dir() );

		$this->assertNotSame( array(), $sources, 'The digest sources yielded no translatable strings; the extractor is broken.' );
		// One title per digest block: without these the extractor has stopped
		// reading a file, and the check below would pass by finding nothing.
		foreach ( array( 'Inquiries waiting for your follow-up', 'Quotations in preparation for more than 3 days', 'Emails that could not be delivered', 'Internal mail authentication', 'Inquiries awaiting staff review', 'Operations health', 'Accounts waiting for approval' ) as $title ) {
			$this->assertArrayHasKey( $title, $sources, 'The extractor no longer reads the block that prints: ' . $title );
		}

		foreach ( self::CATALOGS as $language => $relative ) {
			$catalog      = $this->catalog( $this->plugin_dir() . '/' . $relative );
			$untranslated = array();
			foreach ( $sources as $msgid => $where ) {
				$translation = $catalog[ $msgid ] ?? '';
				if ( '' === trim( $translation ) ) {
					$untranslated[] = $msgid . '  (' . $where . ')';
				}
			}

			$this->assertSame(
				array(),
				$untranslated,
				'The digest is sent in the team language (linker_commerce_team_locale = zh_CN) and in German for staff who read German; these ' . $language . ' strings would arrive in English. Translate them and recompile ' . $relative . ':'
				. "\n  " . implode( "\n  ", $untranslated )
			);
		}
	}

	/**
	 * Both compiled catalogs answer for the blocks that shipped before this
	 * test existed: a stale or half-written .mo fails here rather than passing
	 * the check above with an empty catalog, and each catalog is checked in its
	 * own language so a copy-pasted block cannot satisfy both.
	 */
	public function test_the_catalogs_are_the_compiled_ones_the_digest_reads(): void {
		$zh = $this->catalog( $this->plugin_dir() . '/' . self::CATALOGS['zh_CN'] );
		$this->assertSame( '每日业务简报', $zh['Daily digest'] ?? '' );
		$this->assertSame( '运行健康', $zh['Operations health'] ?? '' );
		$this->assertSame( '待跟进的询盘', $zh['Inquiries waiting for your follow-up'] ?? '' );
		$this->assertSame( '暂无报价单超过 3 天未收到回复。', $zh['No Quotation has waited more than 3 days for a reply.'] ?? '' );

		$de = $this->catalog( $this->plugin_dir() . '/' . self::CATALOGS['de_DE_formal'] );
		$this->assertSame( 'Tagesübersicht', $de['Daily digest'] ?? '' );
		$this->assertSame( 'Betriebsstatus', $de['Operations health'] ?? '' );
		$this->assertSame( 'Anfragen warten auf Ihre Bearbeitung', $de['Inquiries waiting for your follow-up'] ?? '' );
		$this->assertSame( 'Kein Angebot wartet seit mehr als 3 Tagen auf eine Antwort.', $de['No Quotation has waited more than 3 days for a reply.'] ?? '' );
	}

	/**
	 * The plugin root, from this test's own location.
	 */
	private function plugin_dir(): string {
		return dirname( __DIR__, 4 );
	}

	/**
	 * The translatable messages of the digest's sources, msgid => first file.
	 *
	 * @param string $plugin Plugin root.
	 * @return array<string, string>
	 */
	private function digest_sources( string $plugin ): array {
		$paths = array();
		foreach ( self::SOURCES as $relative ) {
			$absolute = $plugin . '/' . $relative;
			if ( is_dir( $absolute ) ) {
				foreach ( (array) glob( $absolute . '/*.php' ) as $file ) {
					if ( is_string( $file ) ) {
						$paths[] = $file;
					}
				}
				continue;
			}
			if ( is_file( $absolute ) ) {
				$paths[] = $absolute;
			}
		}
		sort( $paths );

		$messages = array();
		foreach ( $paths as $path ) {
			$source = file_get_contents( $path );
			if ( ! is_string( $source ) ) {
				continue;
			}
			foreach ( $this->gettext_calls( $source ) as $msgid ) {
				$messages[ $msgid ] ??= str_replace( $plugin . '/', '', $path );
			}
		}
		return $messages;
	}

	/**
	 * The msgids of one file's __() and _n() calls in this plugin's domain.
	 *
	 * The tokenizer is used rather than a regex so comments, unrelated strings
	 * and a call split over several lines are read the way PHP reads them.
	 *
	 * @param string $source PHP source.
	 * @return list<string>
	 */
	private function gettext_calls( string $source ): array {
		$tokens = token_get_all( $source );
		$count  = count( $tokens );
		$msgids = array();

		for ( $index = 0; $index < $count; $index++ ) {
			$token = $tokens[ $index ];
			if ( ! is_array( $token ) || T_STRING !== $token[0] ) {
				continue;
			}
			$function = strtolower( $token[1] );
			if ( '__' !== $function && '_n' !== $function ) {
				continue;
			}
			$open = $this->next_significant( $tokens, $index + 1 );
			if ( null === $open || '(' !== $tokens[ $open ] ) {
				continue;
			}
			$arguments = $this->arguments( $tokens, $open );
			if ( null === $arguments || array() === $arguments ) {
				continue;
			}
			// Both take the text domain as their last argument.
			$domain = end( $arguments );
			if ( ! is_array( $domain ) || T_CONSTANT_ENCAPSED_STRING !== $domain[0] ) {
				continue;
			}
			if ( 'linker-commerce' !== $this->unquote( $domain[1] ) ) {
				continue;
			}
			// __( text ) and _n( single, plural ): the singular is the msgid.
			$first = $arguments[0];
			if ( is_array( $first ) && T_CONSTANT_ENCAPSED_STRING === $first[0] ) {
				$msgids[] = $this->unquote( $first[1] );
			}
		}

		return $msgids;
	}

	/**
	 * The arguments of the call whose opening parenthesis is at $open, or null
	 * when the parentheses do not close.
	 *
	 * @param list<array{int, string, int}|string> $tokens Tokens.
	 * @param int                                  $open   Index of the opening parenthesis.
	 * @return list<array{int, string, int}|string>|null
	 */
	private function arguments( array $tokens, int $open ): ?array {
		$arguments = array();
		$current   = array();
		$depth     = 0;
		$count     = count( $tokens );
		for ( $index = $open; $index < $count; $index++ ) {
			$token = $tokens[ $index ];
			if ( is_array( $token ) ) {
				if ( $depth >= 1 ) {
					$current[] = $token;
				}
				continue;
			}
			if ( '(' === $token ) {
				++$depth;
				if ( $depth >= 2 ) {
					$current[] = $token;
				}
				continue;
			}
			if ( ')' === $token ) {
				--$depth;
				if ( 0 === $depth ) {
					$arguments[] = $this->literal( $current );
					return $arguments;
				}
				$current[] = $token;
				continue;
			}
			if ( ',' === $token && 1 === $depth ) {
				$arguments[] = $this->literal( $current );
				$current     = array();
				continue;
			}
			if ( $depth >= 1 ) {
				$current[] = $token;
			}
		}
		return null;
	}

	/**
	 * The single token of an argument that is one string literal, else the
	 * argument as one non-literal token.
	 *
	 * @param list<array{int, string, int}|string> $tokens Argument tokens.
	 * @return array{int, string, int}|string
	 */
	private function literal( array $tokens ): array|string {
		$significant = array();
		foreach ( $tokens as $token ) {
			if ( is_array( $token ) && ( T_WHITESPACE === $token[0] || T_COMMENT === $token[0] || T_DOC_COMMENT === $token[0] ) ) {
				continue;
			}
			$significant[] = $token;
		}
		if ( 1 === count( $significant ) ) {
			return $significant[0];
		}
		return array(
			T_STRING,
			implode( '', array_map( static fn ( $token ): string => is_array( $token ) ? $token[1] : $token, $significant ) ),
			0,
		);
	}

	/**
	 * The next token that is not whitespace or a comment.
	 *
	 * @param list<array{int, string, int}|string> $tokens Tokens.
	 * @param int                                  $from   Index to start at.
	 */
	private function next_significant( array $tokens, int $from ): ?int {
		$count = count( $tokens );
		for ( $index = $from; $index < $count; $index++ ) {
			$token = $tokens[ $index ];
			if ( is_array( $token ) && ( T_WHITESPACE === $token[0] || T_COMMENT === $token[0] || T_DOC_COMMENT === $token[0] ) ) {
				continue;
			}
			return $index;
		}
		return null;
	}

	/**
	 * A PHP string literal without its quotes and escapes.
	 *
	 * @param string $literal Quoted literal as written in the source.
	 */
	private function unquote( string $literal ): string {
		if ( "'" === ( $literal[0] ?? '' ) ) {
			return str_replace( array( "\\'", '\\\\' ), array( "'", '\\' ), substr( $literal, 1, -1 ) );
		}
		return stripcslashes( substr( $literal, 1, -1 ) );
	}

	/**
	 * A compiled catalog as msgid => msgstr.
	 *
	 * The binary .mo layout is fixed by the gettext ABI: magic, revision,
	 * count, then the offsets of the original and translated string tables,
	 * each entry a length/offset pair. WordPress reads the same tables in
	 * wp-includes/pomo/mo.php. Plural entries carry their singular msgid plus
	 * a NUL and the plural form; the singular is the key here, and its first
	 * translated form answers whether the entry is translated.
	 *
	 * @param string $path Compiled catalog path.
	 * @return array<string, string>
	 */
	private function catalog( string $path ): array {
		$this->assertFileExists( $path );
		$bytes = (string) file_get_contents( $path );
		$this->assertGreaterThanOrEqual( 20, strlen( $bytes ), 'The compiled catalog is too short to hold a header.' );

		$first_word = unpack( 'V', substr( $bytes, 0, 4 ) );
		$magic      = is_array( $first_word ) ? (int) $first_word[1] : 0;
		// 0x950412de little-endian, 0xde120495 big-endian.
		$big_endian = 0xde120495 === $magic;
		$this->assertTrue( 0x950412de === $magic || $big_endian, 'The compiled catalog has no gettext magic number.' );
		$read = static function ( int $offset ) use ( $bytes, $big_endian ): int {
			$unpacked = unpack( $big_endian ? 'N' : 'V', substr( $bytes, $offset, 4 ) );
			return is_array( $unpacked ) ? (int) $unpacked[1] : 0;
		};

		$count      = $read( 8 );
		$originals  = $read( 12 );
		$translated = $read( 16 );
		$this->assertGreaterThan( 0, $count, 'The compiled catalog holds no entries.' );

		$entries = array();
		for ( $index = 0; $index < $count; $index++ ) {
			$original_length   = $read( $originals + $index * 8 );
			$original_offset   = $read( $originals + $index * 8 + 4 );
			$translated_length = $read( $translated + $index * 8 );
			$translated_offset = $read( $translated + $index * 8 + 4 );
			// Plural entries join the singular msgid and the plural form with NUL.
			$original = explode( "\0", substr( $bytes, $original_offset, $original_length ) )[0];
			if ( '' === $original ) {
				continue; // The header.
			}
			// Plural translations join their forms with NUL; the first form is
			// what a count of one selects and is enough to tell translated from not.
			$entries[ $original ] = explode( "\0", substr( $bytes, $translated_offset, $translated_length ) )[0];
		}

		return $entries;
	}
}
