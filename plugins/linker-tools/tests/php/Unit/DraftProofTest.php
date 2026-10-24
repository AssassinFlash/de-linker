<?php
/**
 * Exact current Genie action tokens, including all candidates and file bytes.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );
namespace Linker\Tools\Tests\Unit;

use Linker\Tools\Genie\DraftProof;
use WP_Error;
use WP_Mock;
use WP_Mock\Tools\TestCase;

require_once dirname( __DIR__, 4 ) . '/linker-commerce/vendor/autoload.php';

/** Exact current signed actions.
 *
 * @covers \Linker\Tools\Genie\DraftProof
 */
final class DraftProofTest extends TestCase {
	/** Current fixture authority.
	 *
	 * @var array<string,mixed>
	 */
	private array $manifest;
	/** Existing private browser/account binding.
	 *
	 * @var string
	 */
	private string $owner = 'browser-and-account';
	/** Fixed fixture time.
	 *
	 * @var int
	 */
	private int $now = 1000;

	/** Existing source identity, with no real service or private raw cookie. */
	public function setUp(): void {
		parent::setUp();
		WP_Mock::userFunction( '__', array( 'return' => static fn( string $v ): string => $v ) );
		WP_Mock::userFunction( 'wp_salt', array( 'return' => 'fixture-only-salt' ) );
		// phpcs:ignore WordPress.WP.AlternativeFunctions.json_encode_json_encode -- Fixture implementation of wp_json_encode.
		WP_Mock::userFunction( 'wp_json_encode', array( 'return' => static fn( mixed $v ): string|false => json_encode( $v ) ) );
		$this->manifest = array(
			'source_revision'        => 'source-1',
			'compatibility_revision' => 'rules-1',
			'products'               => array(
				array(
					'product_id'           => 5,
					'product_revision'     => 'p5',
					'published_locale_ids' => array( 5, 105 ),
					'brand'                => 'SAJ',
					'model'                => 'A',
				),
				array(
					'product_id'           => 6,
					'product_revision'     => 'p6',
					'published_locale_ids' => array( 6 ),
					'brand'                => 'SAJ',
					'model'                => 'B',
				),
			),
			'documents'              => array(
				array(
					'document_id'       => 'd1',
					'document_revision' => 'bytes-1',
					'product_ids'       => array( 5, 6 ),
				),
			),
		);
	}

	/** The browser gets a signed whole list, never an editable subset. */
	public function test_exact_parts_list_and_all_candidates_survive_verification(): void {
		$proof  = $this->proof();
		$token  = $this->token( $proof );
		$result = $proof->verify( $token );
		$this->assertIsArray( $result );
		$this->assertSame( array( 2, 1 ), array_column( $result['selected']['lines'], 'quantity' ) );
		$this->assertCount( 2, $result['publication']['products'] );
		$this->assertSame( 'bytes-1', $result['publication']['documents'][0]['document_revision'] );
		$this->assertSame( 'genie', $result['kind'] );
	}

	/** Removing B or altering its quantity makes the HMAC invalid. */
	public function test_browser_cannot_drop_a_line_or_change_quantity(): void {
		$proof = $this->proof();
		$parts = explode( '.', $this->token( $proof ) );
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_decode -- Decode only a fixture's authenticated JSON for deliberate tampering.
		$decoded = base64_decode( strtr( $parts[0], '-_', '+/' ), true );
		$this->assertIsString( $decoded );
		$data = json_decode( $decoded, true );
		array_pop( $data['result']['selected']['lines'] );
		$data['result']['selected']['lines'][0]['quantity'] = 40;
		// phpcs:ignore WordPress.PHP.DiscouragedPHPFunctions.obfuscation_base64_encode -- Deliberately forged fixture token.
		$body = rtrim( strtr( base64_encode( (string) wp_json_encode( $data ) ), '+/', '-_' ), '=' );
		$this->assertInstanceOf( WP_Error::class, $proof->verify( $body . '.' . $parts[1] ) );
	}

	/** Owner changes and receipt expiry require a new current turn. */
	public function test_other_browser_account_and_expired_token_are_refused(): void {
		$proof       = $this->proof();
		$token       = $this->token( $proof );
		$this->owner = 'different-account';
		$this->assertInstanceOf( WP_Error::class, $proof->verify( $token ) );
		$this->owner = 'browser-and-account';
		$this->now  += DAY_IN_SECONDS;
		$this->assertInstanceOf( WP_Error::class, $proof->verify( $token ) );
	}

	/** Same URL's new bytes invalidate the complete artifact. */
	public function test_changed_document_bytes_or_withdrawn_candidate_refuse_the_whole_list(): void {
		$proof = $this->proof();
		$token = $this->token( $proof );
		$this->manifest['documents'][0]['document_revision'] = 'bytes-2';
		$this->assertInstanceOf( WP_Error::class, $proof->verify( $token ) );
		$this->manifest['documents'][0]['document_revision'] = 'bytes-1';
		array_pop( $this->manifest['products'] );
		$this->assertInstanceOf( WP_Error::class, $proof->verify( $token ) );
	}

	/** An old transcript is never offered to stream() for token minting. */
	public function test_current_product_cards_get_only_their_own_exact_action(): void {
		$proof  = $this->proof();
		$stream = $proof->stream( "event: block\ndata: {\"type\":\"cards\",\"product_ids\":[5,999]}\n\nevent: done\ndata: {}\n\n", $this->dependencies() );
		if ( ! is_string( $stream ) || 1 !== preg_match( '/^data: (.+)$/m', $stream, $data ) ) {
			$this->fail( 'The live fixture did not produce its artifact.' );
		}
		$block = json_decode( $data[1], true );
		$this->assertArrayHasKey( '5', $block['draft_proofs'] );
		$this->assertArrayNotHasKey( '999', $block['draft_proofs'] );
	}

	/** Engineering reference records cannot become sale-oriented Genie actions. */
	public function test_reference_module_cannot_mint_a_card_or_partial_parts_list(): void {
		$this->manifest['products'][1]['engineering_role'] = 'reference_pv_module';
		$proof = $this->proof();
		$this->assertSame( '', $this->token( $proof ) );
		$stream = $proof->stream( "event: block\ndata: {\"type\":\"cards\",\"product_ids\":[5,6]}\n\n", $this->dependencies() );
		if ( ! is_string( $stream ) || 1 !== preg_match( '/^data: (.+)$/m', $stream, $data ) ) {
			$this->fail( 'The live fixture did not produce its artifact.' );
		}
		$block = json_decode( $data[1], true );
		$this->assertArrayHasKey( '5', $block['draft_proofs'] );
		$this->assertArrayNotHasKey( '6', $block['draft_proofs'] );
	}

	/** Complete current candidate and evidence set.
	 *
	 * @return array<string,mixed>
	 */
	private function dependencies(): array {
		return array(
			'products'               => array(
				array(
					'product_id'       => 5,
					'product_revision' => 'p5',
				),
				array(
					'product_id'       => 6,
					'product_revision' => 'p6',
				),
			),
			'documents'              => array(
				array(
					'document_id'       => 'd1',
					'document_revision' => 'bytes-1',
					'product_id'        => 5,
				),
			),
			'compatibility_revision' => 'rules-1',
		);
	}

	/** Create the fixture authority and owner reader. */
	private function proof(): DraftProof {
		return new DraftProof( fn(): array => $this->manifest, fn(): string => $this->owner, fn(): int => $this->now );
	}

	/** Mint the complete list.
	 *
	 * @param DraftProof $proof Current signer.
	 */
	private function token( DraftProof $proof ): string {
		$stream = $proof->stream( "event: block\ndata: {\"type\":\"parts\",\"add\":{\"items\":[{\"product_id\":5,\"quantity\":2},{\"product_id\":6,\"quantity\":1}]}}\n\nevent: done\ndata: {}\n\n", $this->dependencies() );
		if ( ! is_string( $stream ) || 1 !== preg_match( '/^data: (.+)$/m', $stream, $data ) ) {
			$this->fail( 'The live fixture did not produce its artifact.' );
		}
		return json_decode( $data[1], true )['add']['proof'];
	}
}
