export type Locale = 'en' | 'de';

export interface StoreProduct {
	attributes?: Array< {
		taxonomy: string;
		terms: Array< { name: string } >;
	} >;
	id: number;
	name: string;
	permalink: string;
	images: { src: string; alt: string }[];
	is_in_stock: boolean;
}
