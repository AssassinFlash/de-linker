<?php
/**
 * The staff diagnostic for a held inquiry preserves the authenticated classification evidence.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Tests\Unit\Inquiry;

use Linker\Commerce\Inquiry\Assessment\SendVerdict;
use PHPUnit\Framework\TestCase;

/**
 * Staff observations of bound classifier responses.
 *
 * @covers \Linker\Commerce\Inquiry\Assessment\SendVerdict
 */
final class SendVerdictTest extends TestCase {

	/** A low-confidence business reading retains its choices without authorizing mail. */
	public function test_unknown_keeps_typed_readings_for_staff(): void {
		$wire             = json_decode( (string) file_get_contents( dirname( __DIR__, 3 ) . '/fixtures/pre-send/normal-escalated.json' ), true );
		$wire['decision'] = 'unknown';
		$wire['reason']   = 'insufficient_confidence';
		$wire['raw']['escalation']['answers']['classification']['confidence'] = 0.7;
		$readings = $wire['raw'];
		$wire['raw']['escalation']['answers']['classification']['comment'] = 'Free text stays out of diagnostics.';

		$observed = SendVerdict::validate( $wire, $wire['binding'] );

		self::assertSame( 'unknown', $observed['decision'] );
		self::assertSame( $wire['reason'], $observed['reason'] );
		self::assertSame( $wire['basis'], $observed['basis'] );
		self::assertSame( $readings, $observed['raw'] );

		$wire['raw']['escalation'] = null;
		$wire['reason']            = 'escalation_transport_error';
		$partial                   = SendVerdict::validate( $wire, $wire['binding'] );
		self::assertSame( $readings['primary'], $partial['raw']['primary'] );
		self::assertNull( $partial['raw']['escalation'] );

		$wire['raw']['primary']['answers']['basis']['confidence'] = 'unexpected text';
		self::assertSame( SendVerdict::unknown( 'invalid_response' ), SendVerdict::validate( $wire, $wire['binding'] ) );

		unset( $wire['raw'] );
		$unobserved = SendVerdict::validate( $wire, $wire['binding'] );
		self::assertSame( 'unknown', $unobserved['decision'] );
		self::assertArrayNotHasKey( 'raw', $unobserved );
	}
}
