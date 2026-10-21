<?php
/**
 * Snapshot only the submitting visitor's existing, relevant Genie material.
 *
 * @package Linker\Tools
 */

declare( strict_types = 1 );

namespace Linker\Tools\Genie;

/** No generated summary, network call, new thread, or arbitrary history lookup. */
final class InquiryAssessmentContext {
	/** Register the commerce snapshot seam. */
	public function register(): void {
		add_filter( 'linker_commerce_inquiry_assessment_context', array( $this, 'read' ), 10, 3 );
	}

	/**
	 * Reads all currently retained messages/readings, enforcing ownership.
	 *
	 * @param array<string, mixed> $evidence Default unavailable evidence.
	 * @param array<string, mixed> $context Trusted source link.
	 * @param bool                 $contact Plain contact has no implicit thread.
	 * @return array<string, mixed>
	 */
	public function read( array $evidence, array $context, bool $contact ): array {
		$locator       = $context['conversation'] ?? 0;
		$id            = is_array( $locator ) ? (int) ( $locator['id'] ?? 0 ) : (int) $locator;
		$conversations = new Conversations();
		if ( $id < 1 && ! $contact ) {
			$id = $conversations->existing_id();
		}
		if ( $id < 1 ) {
			return array(
				'status'       => 'not_present',
				'conversation' => array(),
				'attachments'  => array(),
			);
		}
		if ( ! $conversations->may_use( $id ) ) {
			return array(
				'status'       => 'unavailable',
				'conversation' => array(),
				'attachments'  => array(),
			);
		}
		$thread = new Thread();
		return array(
			'status'          => 'available',
			'conversation_id' => $id,
			'conversation'    => $thread->transcript( $id ),
			'attachments'     => $thread->readings( $id ),
			'page'            => $context['page'] ?? array(),
			'scope'           => 'retained_current_conversation_only',
		);
	}
}
