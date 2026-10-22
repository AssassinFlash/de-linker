<?php
/** Versioned authenticated classifier response, never an observation-label permit.
 *
 * @package Linker\Commerce
 */
declare( strict_types = 1 );
namespace Linker\Commerce\Inquiry\Assessment;

/** Binding and typed evidence are checked independently of the model's decision text. */
final class SendVerdict {
	public const POLICY = 'inquiry-mail-v1';
	/**
	 * @param string $reason Fixed diagnosis.
	 * @return array<string,mixed> */
	public static function unknown( string $reason ): array {
		return array(
			'decision' => 'unknown',
			'reason'   => $reason,
			'basis'    => 'insufficient_context',
			'rubric'   => self::POLICY,
			'model'    => Result::MODEL,
		);}
	/**
	 * @param mixed               $value Service body.
	 * @param array<string,mixed> $binding Expected server binding.
	 * @return array<string,mixed> */
	public static function validate( mixed $value, array $binding ): array {
		if ( ! is_array( $value ) || ! self::binding( $value['binding'] ?? null, $binding ) || self::POLICY !== ( $value['rubric'] ?? null ) || ! is_string( $value['model'] ?? null ) || 1 !== preg_match( '~\Atypesafe/jev-1\.13(?:-[0-9]{8})?\z~D', $value['model'] ) ) {
			return self::unknown( 'invalid_response' );}
		$decision = $value['decision'] ?? '';
		$basis    = $value['basis'] ?? '';
		$reason   = $value['reason'] ?? '';
		if ( ! in_array( $decision, array( 'normal', 'malicious', 'unknown' ), true ) || ! in_array( $basis, Result::BASES, true ) || ! is_string( $reason ) ) {
			return self::unknown( 'invalid_response' );}
		if ( 'unknown' === $decision ) {
			return self::unknown( 1 === preg_match( '/^(conflict|insufficient_confidence|insufficient_context|missing_credentials|invalid_model|invalid_response|transport_error|deadline|provider_http_[0-9]{3}|provider_budget_(quota|unavailable|configuration|permissions|replayed|provider|attempt)|escalation_(conflict|insufficient_confidence|insufficient_context|missing_credentials|invalid_model|invalid_response|transport_error|deadline|provider_http_[0-9]{3}|provider_budget_(quota|unavailable|configuration|permissions|replayed|provider|attempt)))$/D', $reason ) ? $reason : 'invalid_response' );}
		if ( ! in_array( $reason, array( 'classified', 'escalated' ), true ) || ( 'normal' === $decision && ! in_array( $basis, array( 'business_request', 'service_or_complaint', 'reporting_abuse' ), true ) ) || ( 'malicious' === $decision && ! in_array( $basis, Result::ABUSE, true ) ) ) {
			return self::unknown( 'invalid_response' );}
		$raw    = $value['raw'] ?? null;
		$answer = is_array( $raw ) ? ( 'escalated' === $reason ? ( $raw['escalation'] ?? null ) : ( $raw['primary'] ?? null ) ) : null;
		if ( ! is_array( $answer ) || ! is_array( $raw['primary'] ?? null ) || ! self::reading( $raw['primary'], false ) || ! self::numeric_wire( $raw['primary'] ) || ! self::reading( $answer, 'escalated' === $reason ) || ! self::answers( $answer, $decision, $basis ) || ! self::confident( $answer ) ) {
			return self::unknown( 'invalid_response' );}
		return $value;
	}
	/**
	 * @param mixed               $actual Echoed binding.
	 * @param array<string,mixed> $expected Server binding. */
	private static function binding( mixed $actual, array $expected ): bool {
		if ( ! is_array( $actual ) || count( $actual ) !== count( $expected ) ) {
			return false; }
		foreach ( $expected as $key => $value ) {
			if ( ! array_key_exists( $key, $actual ) || $value !== $actual[ $key ] ) {
					return false;}
		}
		return true;
	}
	/**
	 * @param array<string,mixed> $reading Typed stage.
	 * @param bool                $escalated Official judge. */
	private static function reading( array $reading, bool $escalated ): bool {
		$model = $reading['model'] ?? null;
		if ( ! is_string( $model ) || ( $escalated ? 'deepseek-flash' !== $model : 1 !== preg_match( '~\Atypesafe/jev-1\.13(?:-[0-9]{8})?\z~D', $model ) ) ) {
			return false;}
		foreach ( array(
			'classification' => array( 'normal', 'malicious', 'unknown' ),
			'basis'          => Result::BASES,
		)as$key => $choices ) {
			$answer = $reading['answers'][ $key ] ?? null;
			if ( ! is_array( $answer ) || 'choice' !== ( $answer['type'] ?? null ) || ! in_array( $answer['choice'] ?? '', $choices, true ) ) {
				return false;}
		}
		return true;
	}
	/**
	 * @param array<string,mixed> $value Typed source.
	 * @param string              $decision Expected choice.
	 * @param string              $basis Expected basis. */
	private static function answers( array $value, string $decision, string $basis ): bool {
		$a = $value['answers'] ?? null;
		return is_array( $a ) && 'choice' === ( $a['classification']['type'] ?? null ) && $decision === ( $a['classification']['choice'] ?? null ) && 'choice' === ( $a['basis']['type'] ?? null ) && $basis === ( $a['basis']['choice'] ?? null );
	}
	/** Low confidence can escalate; malformed numeric evidence cannot.
	 *
	 * @param array<string,mixed> $value Original typed primary reading.
	 */
	private static function numeric_wire( array $value ): bool {
		foreach ( array(
			'classification' => array( 'normal', 'malicious', 'unknown' ),
			'basis'          => Result::BASES,
		)as$key => $choices ) {
			$answer = $value['answers'][ $key ] ?? array();
			$number = $answer['confidence'] ?? null;
			if ( null !== $number && ( ( ! is_int( $number ) && ! is_float( $number ) ) || ! is_finite( (float) $number ) || (float) $number < 0 || (float) $number > 1 ) ) {
				return false;}
			$probs = $answer['probabilities'] ?? null;
			if ( ! is_array( $probs ) ) {
				return false;}
			if ( array() !== $probs ) {
				$keys = array_keys( $probs );
				sort( $keys );
				$expected = $choices;
				sort( $expected );
				if ( $keys !== $expected ) {
					return false;
				}$sum = 0.0;
				foreach ( $probs as$p ) {
					if ( ( ! is_int( $p ) && ! is_float( $p ) ) || ! is_finite( (float) $p ) || (float) $p < 0 || (float) $p > 1 ) {
						return false;
					}$sum += (float) $p;
				}if ( $sum <= 0.0 ) {
					return false;}
			}
		}
		return true;
	}
	/** Initial operating point is frozen in docs/specs/533-pre-send-verdict-contract.md; not an accuracy claim.
	 *
	 * @param array<string,mixed> $value Typed selected-stage answers.
	 */
	private static function confident( array $value ): bool {
		foreach ( array(
			'classification' => array( 'normal', 'malicious', 'unknown' ),
			'basis'          => Result::BASES,
		)as$key => $choices ) {
			$answer        = $value['answers'][ $key ] ?? array();
			$confidence    = $answer['confidence'] ?? null;
			$probabilities = $answer['probabilities'] ?? null;
			if ( null !== $confidence && ( ! is_int( $confidence ) && ! is_float( $confidence ) || ! is_finite( (float) $confidence ) || (float) $confidence < 0 || (float) $confidence > 1 ) ) {
				return false;}
			if ( ! is_array( $probabilities ) ) {
				return false;}
			if ( array() !== $probabilities ) {
				$keys = array_keys( $probabilities );
				sort( $keys );
				$expected = $choices;
				sort( $expected );
				if ( $keys !== $expected ) {
							return false;}
				$sum      = 0.0;
				$selected = $probabilities[ $answer['choice'] ] ?? null;
				foreach ( $probabilities as $probability ) {
					if ( ( ! is_int( $probability ) && ! is_float( $probability ) ) || ! is_finite( (float) $probability ) || (float) $probability < 0 || (float) $probability > 1 ) {
						return false;
					}$sum += (float) $probability;}
				// The frozen unshipped contract never boosts underfilled mass; overshoot only lowers confidence.
				if ( $sum <= 0.0 || ! is_numeric( $selected ) || (float) $selected < max( $probabilities ) ) {
					return false;}
				$effective = min( (float) $selected, (float) $selected / max( 1.0, $sum ) );
				$confidence = null === $confidence ? $effective : min( (float) $confidence, $effective );
			}
			if ( null === $confidence || (float) $confidence < 0.90 ) {
				return false;}
		}
		return true;
	}
}
