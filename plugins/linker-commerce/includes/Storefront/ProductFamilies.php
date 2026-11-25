<?php
/**
 * Reciprocal Woo model families used by catalogue cards and facet counts.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Storefront;

/** A family of models is one visible card in the current catalogue language. */
final class ProductFamilies {
	/**
	 * Manufacturer model lists keyed by the product's locale ID.
	 *
	 * @var array<int,list<int>>
	 */
	private array $variants = array();

	/**
	 * Read the English model lists once for this archive.
	 *
	 * @param int[] $ids Archive product IDs.
	 */
	public function __construct( array $ids ) {
		$lang = function_exists( 'pll_current_language' ) ? (string) pll_current_language() : '';
		$pair = '' !== $lang && function_exists( 'pll_get_post' );
		foreach ( $ids as $id ) {
			$source = $pair ? (int) pll_get_post( $id, 'en' ) : $id;
			$data   = json_decode( (string) get_post_meta( $source > 0 ? $source : $id, '_tv_legacy_acf_json', true ), true );
			$list   = array();
			$terms  = $data['family_variants'] ?? array();
			foreach ( is_array( $terms ) ? $terms : array() as $variant ) {
				$member = (int) ( $variant['id'] ?? 0 );
				if ( $member > 0 ) {
					$twin   = $pair ? (int) pll_get_post( $member, $lang ) : 0;
					$list[] = $twin > 0 ? $twin : $member;
				}
			}
			$this->variants[ $id ] = array_values( array_unique( $list ) );
		}
	}

	/**
	 * Group only matching IDs in display order, with their lead model first.
	 *
	 * @param int[] $ids Matching archive models.
	 * @return list<array{lead:int,ids:list<int>}>
	 */
	public function rows( array $ids ): array {
		$present = array_fill_keys( $ids, true );
		$seen    = array();
		$rows    = array();
		foreach ( $ids as $id ) {
			if ( isset( $seen[ $id ] ) ) {
				continue;
			}
			$members = array( $id );
			foreach ( $this->variants[ $id ] as $member ) {
				if ( $id !== $member && isset( $present[ $member ] ) && in_array( $id, $this->variants[ $member ], true ) ) {
					$members[] = $member;
				}
			}
			$seen  += array_fill_keys( $members, true );
			$rows[] = array(
				'lead' => $id,
				'ids'  => $members,
			);
		}
		return $rows;
	}
}
