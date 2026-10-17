<?php
/**
 * One conversation, as the email shows it.
 *
 * @package Linker\Commerce
 */

declare( strict_types = 1 );

namespace Linker\Commerce\Genie;

use Linker\Commerce\Abilities\ProductText;

/**
 * The conversation linker-tools hands over: where it goes, in which
 * language, and its messages, each answer with the products its cards
 * showed (name, model and page, in the email's language). Built only from a
 * complete, well-formed array; anything else is no conversation and nothing
 * is sent.
 */
final class Conversation {

	/**
	 * Sets up the conversation.
	 *
	 * @param string                                                                                                                   $to       The visitor's address.
	 * @param string                                                                                                                   $locale   WordPress locale of the email.
	 * @param list<array{role: 'user'|'assistant', content: string, products: list<array{title: string, model: string, url: string}>}> $messages Oldest first.
	 */
	private function __construct(
		public readonly string $to,
		public readonly string $locale,
		public readonly array $messages
	) {}

	/**
	 * The conversation an array describes, or null.
	 *
	 * The tools plugin sends roles as `user` or `assistant` (its Thread::role());
	 * a message with any other role, or without text, is not part of it.
	 *
	 * @param array<string, mixed> $email to, locale, messages.
	 */
	public static function from_array( array $email ): ?self {
		$to = isset( $email['to'] ) && is_string( $email['to'] ) ? $email['to'] : '';
		if ( ! is_email( $to ) ) {
			return null;
		}
		$lang     = isset( $email['locale'] ) && is_string( $email['locale'] ) ? ProductText::lang( $email['locale'] ) : 'en';
		$messages = array();
		foreach ( is_array( $email['messages'] ?? null ) ? $email['messages'] : array() as $message ) {
			if ( ! is_array( $message ) || ! is_string( $message['content'] ?? null ) || '' === $message['content'] || ! in_array( $message['role'] ?? null, array( 'user', 'assistant' ), true ) ) {
				continue;
			}
			$messages[] = array(
				'role'     => $message['role'],
				'content'  => $message['content'],
				'products' => 'assistant' === $message['role'] ? self::products( $message['products'] ?? array(), $lang ) : array(),
			);
		}
		if ( array() === $messages ) {
			return null;
		}
		return new self( $to, 'de' === $lang ? 'de_DE_formal' : 'en_US', $messages );
	}

	/**
	 * The published products among the ids, as the email names them.
	 *
	 * @param mixed     $ids  Product ids.
	 * @param 'en'|'de' $lang The email's language.
	 * @return list<array{title: string, model: string, url: string}>
	 */
	private static function products( mixed $ids, string $lang ): array {
		$products = array();
		foreach ( is_array( $ids ) ? $ids : array() as $id ) {
			$id = (int) $id;
			if ( $id < 1 || 'product' !== get_post_type( $id ) || 'publish' !== get_post_status( $id ) ) {
				continue;
			}
			$products[] = array(
				'title' => ProductText::title( $id, $lang ),
				'model' => (string) ProductText::term_name( $id, 'pa_model' ),
				'url'   => ProductText::url( $id, $lang ),
			);
		}
		return $products;
	}
}
