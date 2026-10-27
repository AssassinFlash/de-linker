import type { Vec2 } from "../domain/geometry.ts";
import type { MapDrawingTransaction } from "./MapDrawingController.ts";

/** Live callbacks do not own persistence or change metric project geometry. */
export interface MapInteraction {
	readonly key: string;
	readonly phase: "collecting" | "staged";
	readonly vertices: readonly Vec2[];
	readonly referencePosition: Vec2 | null;
	readonly append: (point: Vec2) => void;
	readonly transaction: (change: MapDrawingTransaction) => void;
	readonly failed: () => void;
	readonly interrupted: () => void;
}
