import type { ComponentProps } from 'react';
import type { TurnMessage } from '../api/turn';
import type { GenieConfig } from '../config';
import { Compare } from './Compare';
import { GenieCards } from './GenieCard';

const readonlyStatus = () => ( { state: 'idle' as const, text: '' } );
const noAction = () => undefined;

export function HistoricalComparisons( {
	message,
	config,
	store,
}: {
	message: TurnMessage;
	config: GenieConfig;
	store: ComponentProps< typeof GenieCards >[ 'store' ];
} ) {
	return (
		<>
			{ message.comparisons?.map( ( block, index ) =>
				block.type === 'cards' ? (
					<GenieCards
						key={ index }
						products={ block.product_ids }
						store={ store }
						locale={ config.locale }
						prices={ block.prices ?? undefined }
						statusFor={ readonlyStatus }
						onAdd={ noAction }
						onSave={ noAction }
					/>
				) : (
					<Compare
						key={ index }
						products={ block.product_ids }
						restUrl={ config.restUrl }
						nonce={ config.restNonce }
						locale={ config.locale }
						proofs={ {} }
						quantities={ {} }
						statusFor={ readonlyStatus }
						onAdd={ noAction }
					/>
				)
			) }
		</>
	);
}
