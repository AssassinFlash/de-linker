<?php
/**
 * The abilities' narrow view of the shared Woo publication authority.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );
namespace Linker\Commerce\Abilities;

use Linker\Commerce\Products\Compatibility;
use Linker\Commerce\Products\Publication;
use Linker\Commerce\Products\SelectionFacts;
use Linker\Commerce\Products\SelectionFactSet;

/** A request snapshot, followed by a fresh source read before release. */
final class PublicationData {
	/**
	 * Fresh Woo authority reader.
	 *
	 * @var callable():array<string,mixed>
	 */
	private $read;

	/**
	 * Use the native authority or an explicit fixture transport.
	 *
	 * @param callable():array<string,mixed>|null $read Current authority reader, injected by fixtures.
	 */
	public function __construct( ?callable $read = null ) {
		$this->read = $read ?? array( Publication::class, 'manifest' );
	}

	/**
	 * Read the current source.
	 *
	 * @return array<string,mixed>
	 */
	public function manifest(): array {
		return ( $this->read )();
	}

	/**
	 * Restrict all candidates to current source permission.
	 *
	 * @param int[]               $ids Requested candidates.
	 * @param array<string,mixed> $manifest Current snapshot.
	 * @param 'en'|'de'|null      $lang Requested product locale, when present.
	 * @return list<int>
	 */
	public function published( array $ids, array $manifest, ?string $lang = null ): array {
		$out = array();
		foreach ( $ids as $id ) {
			if ( ! Publication::is_published( $id ) || ( null !== $lang && 0 === ProductText::translated_id( $id, $lang ) ) ) {
				continue;
			}
			foreach ( $manifest['products'] as $product ) {
				if ( $id === $product['product_id'] || in_array( $id, $product['published_locale_ids'], true ) ) {
					if ( '' === ( $product['engineering_role'] ?? '' ) ) {
						$out[] = $id;
					}
					break;
				}
			}
		}
		return array_values( array_unique( $out ) );
	}

	/**
	 * Read cited figures through the same source authority.
	 *
	 * @param int                 $id Product ID.
	 * @param array<string,mixed> $manifest Current snapshot.
	 * @return array<string,array<string,mixed>>
	 */
	public function figures( int $id, array $manifest ): array {
		return Publication::figures_for( $id, $manifest );
	}

	/**
	 * Derive facts only from authorized evidence.
	 *
	 * @param int                 $id Product ID.
	 * @param array<string,mixed> $manifest Current snapshot.
	 */
	public function facts( int $id, array $manifest ): SelectionFactSet {
		return SelectionFacts::from_figures( Publication::canonical_id( $id ), $this->figures( $id, $manifest ) );
	}

	/**
	 * Use current document associations for this product.
	 *
	 * @param int                 $id Product ID.
	 * @param array<string,mixed> $manifest Current snapshot.
	 * @return list<array<string,mixed>>
	 */
	public function documents( int $id, array $manifest ): array {
		$canonical = Publication::canonical_id( $id );
		return array_values( array_filter( $manifest['documents'], static fn( array $document ): bool => in_array( $canonical, $document['product_ids'], true ) ) );
	}

	/**
	 * Capture the entire candidate and evidence dependency set.
	 *
	 * @param int[]               $ids Complete candidate set.
	 * @param array<string,mixed> $manifest Current snapshot.
	 * @return array<string,mixed>
	 */
	public function dependencies( array $ids, array $manifest ): array {
		$canonical = array_map( array( Publication::class, 'canonical_id' ), $ids );
		$products  = array();
		$documents = array();
		foreach ( $manifest['products'] as $product ) {
			if ( in_array( $product['product_id'], $canonical, true ) ) {
				$products[] = array(
					'product_id'       => $product['product_id'],
					'product_revision' => $product['product_revision'],
				);
			}
		}
		foreach ( $manifest['documents'] as $document ) {
			foreach ( array_intersect( $document['product_ids'], $canonical ) as $id ) {
				$documents[] = array(
					'document_id'       => $document['document_id'],
					'document_revision' => $document['document_revision'],
					'product_id'        => $id,
				);
			}
		}
		return array(
			'products'               => $products,
			'documents'              => $documents,
			'compatibility_revision' => $manifest['compatibility_revision'],
		);
	}

	/**
	 * Revalidate before releasing any current result.
	 *
	 * @param array<string,mixed> $dependencies Original complete dependencies.
	 */
	public function unchanged( array $dependencies ): bool {
		return true === Publication::validate_manifest( $dependencies, $this->manifest() )['valid'];
	}

	/**
	 * A release is usable only while its products and every cited file are current.
	 *
	 * @param int                 $inverter Inverter ID.
	 * @param int                 $battery Battery ID.
	 * @param array<string,mixed> $manifest Current snapshot.
	 * @return array{verdict:string,conditions:list<array{en:string,de:string}>,documents:list<array{url:string,page?:int}>,accessories:list<array{model:string,quantity:int,per:string,product_id:int}>}|null
	 */
	public function pairing( int $inverter, int $battery, array $manifest ): ?array {
		if ( count( $this->published( array( $inverter, $battery ), $manifest ) ) !== 2 ) {
			return null;
		}
		$answer = Compatibility::for_products( $inverter, $battery, $manifest );
		if ( null === $answer || array() === $answer['documents'] ) {
			return null;
		}
		foreach ( $answer['accessories'] as $accessory ) {
			$known = false;
			foreach ( $manifest['products'] as $product ) {
				$product_id = (int) ( $product['product_id'] ?? 0 );
				if ( $accessory['product_id'] === $product_id ) {
					$known = true;
					break;
				}
			}
			if ( ! $known ) {
				return null;
			}
		}
		$allowed = array();
		foreach ( array_merge( $this->documents( $inverter, $manifest ), $this->documents( $battery, $manifest ) ) as $document ) {
			foreach ( array_merge( array( $document['url'] ), $document['aliases'] ) as $url ) {
				$allowed[ $url ] = true;
			}
		}
		foreach ( $answer['documents'] as $document ) {
			if ( ! isset( $allowed[ $document['url'] ] ) ) {
				return null;
			}
		}
		return $answer;
	}
}
