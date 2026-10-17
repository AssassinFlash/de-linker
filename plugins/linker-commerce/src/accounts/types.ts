export type Decision = 'approved' | 'restricted' | 'rejected';
export type Status = 'pending' | Decision;
export type Counts = Record< Status, number >;
export interface Account {
	id: number;
	company: string;
	country: string;
	businessType: string;
	contact: string;
	email: string;
	registered: string;
	status: Status;
	statusLabel: string;
	reason: string;
	audit: string;
	fields: { key: string; label: string; value: string; website: boolean }[];
	signals: { tone: string; text: string }[];
	links: { label: string; url: string }[];
	switchUrl: string;
	switchNote: string;
}
export interface Collection {
	accounts: Account[];
	counts: Counts;
}
export interface SavedDecision {
	account: Account;
	counts: Counts;
}
