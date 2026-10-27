/** A map handler gate stays blocked until a later physical pointerdown. That
 * reset belongs to the viewport, which outlives the drawing controller. */
export class MapPickGate {
	blocked = false;
	beginPointer = () => {
		this.blocked = false;
	};
	block = () => {
		this.blocked = true;
	};
}
