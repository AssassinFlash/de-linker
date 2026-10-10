/**
 * A product in a proposal: what it is, how many, why it is there, and the
 * feedback of an action on it, all inside the card.
 *
 * Shared by the Solution Configurator and Genie (docs/specs/13-genie.md:
 * pending / added / unverified / retry shown in the card, the card's height
 * stable). The caller supplies every text, so the card carries no wording of
 * its own and serves both apps' translations.
 */

/**
 * External dependencies
 */
import type { ReactNode } from 'react';

/**
 * Internal dependencies
 */
import './product-card.css';

export type CardState = 'idle' | 'pending' | 'added' | 'unverified' | 'retry';

export interface CardBadge {
	tone: 'ok' | 'info' | 'warn';
	text: string;
}

export interface ProductCardProps {
	/** Stable id for labelling, unique on the page. */
	id: string;
	/** What the item is in the proposal ("Hybrid inverter"). */
	role: string;
	title: string;
	/** Already worded, for example "Model GW10K-ETA-G20"; empty hides the line. */
	model: string;
	url?: string;
	image?: { src: string; alt: string };
	/** Already worded, for example "2 pcs". */
	quantity?: string;
	facts?: { label: string; value: string }[];
	badges?: CardBadge[];
	/** Feedback of the last action; the region keeps its height when empty. */
	status?: { state: CardState; text: string };
	actions?: ReactNode;
	children?: ReactNode;
}

export function ProductCard( {
	id,
	role,
	title,
	model,
	url,
	image,
	quantity,
	facts = [],
	badges = [],
	status,
	actions,
	children,
}: ProductCardProps ) {
	const titleId = `${ id }-title`;
	const state = status?.state ?? 'idle';
	return (
		<article
			className="linker-card"
			aria-labelledby={ titleId }
			data-state={ state }
		>
			<div className="linker-card__media" aria-hidden={ ! image }>
				{ image ? (
					<img src={ image.src } alt={ image.alt } loading="lazy" />
				) : null }
			</div>
			<div className="linker-card__body">
				<p className="linker-card__role">{ role }</p>
				<h3 className="linker-card__title" id={ titleId }>
					{ url ? <a href={ url }>{ title }</a> : title }
				</h3>
				{ model || quantity ? (
					<p className="linker-card__model">
						{ model }
						{ quantity ? (
							<span className="linker-card__quantity">
								{ quantity }
							</span>
						) : null }
					</p>
				) : null }
				{ badges.length > 0 ? (
					<ul className="linker-card__badges">
						{ badges.map( ( badge ) => (
							<li
								key={ badge.text }
								className={ `linker-card__badge linker-card__badge--${ badge.tone }` }
							>
								{ badge.text }
							</li>
						) ) }
					</ul>
				) : null }
				{ facts.length > 0 ? (
					<dl className="linker-card__facts">
						{ facts.map( ( fact ) => (
							<div key={ fact.label }>
								<dt>{ fact.label }</dt>
								<dd>{ fact.value }</dd>
							</div>
						) ) }
					</dl>
				) : null }
				{ children }
				{ actions ? (
					<div className="linker-card__actions">{ actions }</div>
				) : null }
				<p
					className={ `linker-card__status linker-card__status--${ state }` }
					role="status"
					aria-live="polite"
				>
					{ status?.text ?? '' }
				</p>
			</div>
		</article>
	);
}
